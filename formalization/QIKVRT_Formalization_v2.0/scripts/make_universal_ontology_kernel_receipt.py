#!/usr/bin/env python3
"""Create an exact-head receipt for the consolidated 32-theorem kernel."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
MATRICES = (
    ROOT / "universal_ontology/CLAIM_MATRIX.json",
    ROOT / "universal_ontology/WORLD_FORMULA_CLAIM_MATRIX.json",
)
SOURCES = (
    ROOT / "QIKVRTUniversalOntology/Core.lean",
    ROOT / "QIKVRTFormalization/WorldFormula/Relations.lean",
    ROOT / "QIKVRTUniversalOntology/AxiomAudit.lean",
    *MATRICES,
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
LINE = re.compile(
    r"^'(?P<name>[^']+)' (?:does not depend on any axioms|"
    r"depends on axioms: \[(?P<axioms>[^]]*)\])$"
)
FOUNDATIONAL = {"propext", "Classical.choice", "Quot.sound"}


def identity(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
    }


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", required=True)
    parser.add_argument("--axiom-output", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    args = parser.parse_args()
    if HEX40.fullmatch(args.commit) is None or HEX40.fullmatch(args.tree) is None:
        raise SystemExit("BLOCK: commit or tree binding is not a lowercase SHA-1")

    expected: set[str] = set()
    for path in MATRICES:
        matrix = json.loads(path.read_text(encoding="utf-8"))
        for claim in matrix["claims"]:
            if claim.get("kind") == "FORMAL_THEOREM":
                expected.add(claim["proof_constant"])
    if len(expected) != 32:
        raise SystemExit(f"BLOCK: expected exactly 32 theorem constants, observed {len(expected)}")

    observed: dict[str, list[str]] = {}
    unexpected: list[str] = []
    for raw_line in args.axiom_output.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = LINE.fullmatch(line)
        if match is None:
            unexpected.append(line)
            continue
        observed[match.group("name")] = [
            item.strip()
            for item in (match.group("axioms") or "").split(",")
            if item.strip()
        ]
    if unexpected:
        raise SystemExit(f"BLOCK: unexpected axiom output: {unexpected[:5]}")
    if set(observed) != expected:
        raise SystemExit(
            f"BLOCK: axiom inventory differs: missing={sorted(expected-set(observed))} "
            f"extra={sorted(set(observed)-expected)}"
        )
    forbidden = {
        name: sorted(set(axioms) - FOUNDATIONAL)
        for name, axioms in observed.items()
        if set(axioms) - FOUNDATIONAL
    }
    if forbidden:
        raise SystemExit(f"BLOCK: forbidden theorem dependencies: {forbidden}")

    receipt = {
        "_license": {
            "classification": "machine_readable_kernel_receipt",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_universal_ontology_kernel_receipt_v2",
        "state": "KERNEL_VERIFIED_FINITE_AND_RELATIONAL_MODELS",
        "repository": args.repository,
        "source_commit": args.commit,
        "source_tree": args.tree,
        "workflow": {"run_id": str(args.run_id), "run_attempt": str(args.run_attempt)},
        "runtime": {
            "toolchain": "leanprover/lean4:v4.19.0",
            "lean_version": command(args.lean, "--version"),
            "lean_githash": command(args.lean, "--githash"),
            "imports": ["Std"],
        },
        "sources": [identity(path) for path in SOURCES],
        "theorem_count": 32,
        "axioms_by_theorem": observed,
        "foundational_axiom_allowlist": sorted(FOUNDATIONAL),
        "project_axioms": [],
        "scope_boundary": {
            "finite_ontology_model_verified": True,
            "world_formula_relation_model_verified": True,
            "formal_establishment_implies_physical_qualification": False,
            "physical_correspondence": "OPEN_CANDIDATE",
            "quantum_entanglement_in_nature_proved": False,
            "empirical_confirmation": False,
            "independent_reproduction": False,
            "scientific_consensus": False,
        },
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"KERNEL_RECEIPT_CREATED theorems=32 commit={args.commit} tree={args.tree}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
