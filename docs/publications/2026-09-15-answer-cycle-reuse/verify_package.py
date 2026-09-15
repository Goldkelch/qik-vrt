#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Reproduce this publication's kernel and boundary evidence.

Reuses the existing Lake project, axiom policy, proof-escape scanner and source
identity functions. The older publication receipt tools have fixed publication
IDs; this adapter only binds the new scope and its negative controls. It never
publishes, promotes claims to Main, or manufactures review/effect evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "formalization/QIKVRT_Formalization_v2.0"
PUBLICATION = Path(__file__).resolve().parent
SOURCE = PROJECT / "QIKVRTFormalization/Decision/AnswerReuse.lean"
AUDIT = PROJECT / "QIKVRTFormalization/Decision/AnswerReuseAxiomAudit.lean"
PUBLICATION_ID = "qikvrt-answer-cycle-reuse-v1"
sys.path.insert(0, str(ROOT / "tools"))
from qikvrt_survival_connectability_kernel_evidence import (  # noqa: E402
    ALLOWED_AXIOMS, AXIOM_REPORT, identity, strip_lean_comments_and_strings,
)

THEOREMS = [
    "answer_reuse_iff", "question_family_iff", "refinement_preserves_answers",
    "shortcuts_compose", "every_question_iff_injective",
    "collapsed_bool_cannot_preserve_identity", "contextual_reuse",
    "changed_head_rejects", "unchecked_receipt_rejects",
    "finite_cycle_preserves", "invariant_does_not_imply_completion",
    "reuse_cost_strictly_less", "completion_of_decreasing_rank",
]
PREFIX = "QIKVRT.V2.AnswerReuse."
NEGATIVES = {
    "false_statement": "example : False := by exact True.intro\n",
    "proof_hole": "example : False := by sorry\n",
    "missing_applicability": (
        "import QIKVRTFormalization.Decision.AnswerReuse\n"
        "open QIKVRT.V2.AnswerReuse\n"
        "example (c : ConditionalCertificate Bool) (s : Bool) : c.conclusion s := by\n"
        "  exact contextual_reuse c s\n"
    ),
    "missing_progress": (
        "import QIKVRTFormalization.Decision.AnswerReuse\n"
        "open QIKVRT.V2.AnswerReuse\n"
        "example (s : Bool) : Exists (fun n => iterate id n s = true) := by\n"
        "  exact completion_of_decreasing_rank id (fun b => b = true) (fun _ => 1)\n"
    ),
}


def invoke(argv: list[str], target: Path, expect_success: bool = True) -> dict:
    result = subprocess.run(argv, cwd=PROJECT, text=True, capture_output=True,
                            timeout=180, check=False)
    output = result.stdout + result.stderr
    target.write_text(output, encoding="utf-8")
    if (result.returncode == 0) != expect_success:
        raise RuntimeError(f"unexpected exit {result.returncode}: {' '.join(argv)}\n{output[-6000:]}")
    if not expect_success and not re.search(r"error:|unsolved goals", output):
        raise RuntimeError("negative control failed for an unrelated execution reason")
    return {"argv": argv, "exit_code": result.returncode,
            "log": target.name, "output_sha256": hashlib.sha256(output.encode()).hexdigest()}


def local_sources(path: Path, seen: set[Path] | None = None) -> list[Path]:
    seen = seen if seen is not None else set()
    if path in seen:
        return []
    seen.add(path)
    result = [path]
    for module in re.findall(r"^import (QIKVRT[A-Za-z0-9_.]+)$", path.read_text(), re.M):
        result.extend(local_sources(PROJECT / (module.replace(".", "/") + ".lean"), seen))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=PROJECT / ".lake/build/answer-reuse-evidence")
    args = parser.parse_args()
    target = args.output_dir.resolve()
    target.mkdir(parents=True, exist_ok=True)
    run_records: list[dict] = []
    try:
        sources = local_sources(SOURCE)
        for source in sources:
            clean = strip_lean_comments_and_strings(source.read_text())
            if re.search(r"\b(sorry|admit|axiom|unsafe|native_decide)\b", clean):
                raise RuntimeError(f"proof escape in source closure: {source}")
        actual_names = re.findall(r"^theorem ([A-Za-z0-9_]+)", SOURCE.read_text(), re.M)
        if actual_names != THEOREMS:
            raise RuntimeError("theorem inventory drift")
        audit_names = re.findall(r"^#print axioms (\S+)$", AUDIT.read_text(), re.M)
        if audit_names != [PREFIX + name for name in THEOREMS]:
            raise RuntimeError("axiom audit inventory drift")
        run_records.append(invoke(["lake", "env", "lean", "--version"], target / "lean-version.log"))
        if "version 4.19.0," not in (target / "lean-version.log").read_text():
            raise RuntimeError("Lean version differs from lock")
        run_records.append(invoke(["lake", "build", "QIKVRTFormalization.Decision.AnswerReuse"],
                                  target / "kernel-build.log"))
        run_records.append(invoke(["lake", "env", "lean", "-E", "hasSorry",
                                  str(AUDIT.relative_to(PROJECT))], target / "axioms.log"))
        reports = list(AXIOM_REPORT.finditer((target / "axioms.log").read_text()))
        axioms = {m.group("name"): sorted(a.strip() for a in (m.group("axioms") or "").split(",")
                                        if a.strip()) for m in reports}
        if len(reports) != 13 or set(axioms) != set(audit_names):
            raise RuntimeError("missing or duplicate kernel axiom reports")
        if any(set(value) - ALLOWED_AXIOMS for value in axioms.values()):
            raise RuntimeError("undeclared kernel axiom")
        negative_results = []
        with tempfile.TemporaryDirectory(prefix="qikvrt-answer-reuse-") as temp:
            for name, source in NEGATIVES.items():
                case = Path(temp) / f"{name}.lean"
                case.write_text(source)
                record = invoke(["lake", "env", "lean", "-E", "hasSorry", str(case)],
                                target / f"negative-{name}.log", False)
                negative_results.append({"name": name,
                    "source": source, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    **record})
        try:
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                           text=True, stderr=subprocess.DEVNULL).strip()
            tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT,
                                           text=True, stderr=subprocess.DEVNULL).strip()
            dirty = bool(subprocess.check_output(["git", "status", "--porcelain"],
                         cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip())
        except (OSError, subprocess.CalledProcessError):
            # An extracted proof package can reproduce source-bound theorems.
            # It cannot attest a Git checkout or inherit the exporting head.
            head, tree, dirty = None, None, True
        # GitHub runner environment supplies provenance, not proof of API authenticity.
        event_sha = os.environ.get("GITHUB_SHA")
        run_id = os.environ.get("GITHUB_RUN_ID")
        receipt = {
            "schema": "qikvrt_answer_reuse_kernel_receipt_v1",
            "publication_id": PUBLICATION_ID, "state": "KERNEL_VERIFIED",
            "scope": "13 named Lean propositions at the bound source closure",
            "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "checkout": {"head": head, "tree": tree, "clean": not dirty,
                         "head_is_source_validation_subject": not dirty},
            "source": identity(SOURCE, ROOT), "audit": identity(AUDIT, ROOT),
            "source_closure": [identity(p, ROOT) for p in sorted(sources)],
            "toolchain": identity(PROJECT / "lean-toolchain", ROOT),
            "lakefile": identity(PROJECT / "lakefile.toml", ROOT),
            "lake_manifest": identity(PROJECT / "lake-manifest.json", ROOT),
            "theorems": audit_names, "theorem_count": len(audit_names),
            "axioms_by_theorem": axioms, "project_axioms": [],
            "commands": run_records,
            "runtime_path_compatibility_used": bool(os.environ.get("LD_PRELOAD")),
            "runner_observation": {"run_id": run_id, "event_sha": event_sha,
                "matches_local_head": bool(event_sha and event_sha == head and not dirty),
                "independently_reobserved_workflow_success": False},
            "workflow": None,
            "boundaries": ["No empirical truth theorem", "No measured speedup",
                "No automatic discovery theorem", "No native review or Main adoption",
                "No universal termination theorem", "No external EFFECT_ACK_DONE"],
        }
        boundary = {"schema": "qikvrt_answer_reuse_boundary_report_v1",
                    "publication_id": PUBLICATION_ID, "state": "VERIFIED",
                    "negative_controls": negative_results,
                    "formal_countermodels": [PREFIX + THEOREMS[5], PREFIX + THEOREMS[10]]}
        (target / "KERNEL_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (target / "BOUNDARY_TEST_REPORT.json").write_text(json.dumps(boundary, indent=2) + "\n")
        print(f"KERNEL_VERIFIED: 13 source-bound theorems; 4 rejected negative controls; checkout_clean={not dirty}")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        (target / "FAILURE.json").write_text(json.dumps({"state": "BLOCK", "reason": str(exc)}, indent=2) + "\n")
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
