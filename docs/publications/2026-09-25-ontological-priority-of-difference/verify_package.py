#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify the ontological-priority scientific/Zenodo candidate fail-closed."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
PUB = ROOT / "docs/publications/2026-09-25-ontological-priority-of-difference"
REL = ROOT / "release/ontological-priority-of-difference-zenodo-v1"
FORMAL = ROOT / "formalization/QIKVRT_Formalization_v2.0"

STATEMENT = "Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts."
PROOF_CONSTANTS = (
    "QIKVRT.UniversalOntology.determinateReality_requires_difference",
    "QIKVRT.UniversalOntology.noDifference_excludes_determinateReality",
    "QIKVRT.UniversalOntology.noDifference_excludes_information",
)
CORE_COUNT = 35
EXTENDED_COUNT = 74
ALLOWED_FOUNDATIONAL_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

AXIOM_LINE = re.compile(
    r"^'(?P<name>[^']+)' (?:does not depend on any axioms|"
    r"depends on axioms: \[(?P<axioms>[^]]*)\])$"
)


class CandidateError(ValueError):
    pass


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: pathlib.Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
    ).strip()


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def parse_axioms(path: pathlib.Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    unexpected: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = AXIOM_LINE.fullmatch(line)
        if match is None:
            unexpected.append(line)
            continue
        axioms = {
            item.strip()
            for item in (match.group("axioms") or "").split(",")
            if item.strip()
        }
        if match.group("name") in result:
            raise CandidateError(f"duplicate axiom record: {match.group('name')}")
        result[match.group("name")] = axioms
    if unexpected:
        raise CandidateError(f"unexpected axiom output: {unexpected[:5]}")
    return result


def verify_content_freeze() -> dict:
    freeze = load_json(REL / "CONTENT_CANDIDATE_FREEZE.json")
    if freeze.get("schema") != "qikvrt_ontological_priority_content_candidate_freeze_v1":
        raise CandidateError("content freeze schema mismatch")
    files = freeze.get("files")
    if not isinstance(files, list) or len(files) != 16:
        raise CandidateError("content freeze must contain exactly 16 files")
    seen = set()
    lines = []
    total = 0
    for item in files:
        path_text = item.get("path")
        if not isinstance(path_text, str) or path_text in seen:
            raise CandidateError("invalid/duplicate content path")
        seen.add(path_text)
        path = ROOT / path_text
        if not path.is_file():
            raise CandidateError(f"missing content file: {path_text}")
        raw = path.read_bytes()
        observed_sha = hashlib.sha256(raw).hexdigest()
        observed_blob = git_blob(path)
        if len(raw) != item.get("bytes"):
            raise CandidateError(f"byte length mismatch: {path_text}")
        if observed_sha != item.get("sha256"):
            raise CandidateError(f"sha256 mismatch: {path_text}")
        if observed_blob != item.get("git_blob_sha1"):
            raise CandidateError(f"git blob mismatch: {path_text}")
        total += len(raw)
        lines.append(f"{observed_sha}  {path_text}\n")
    required_leibniz = {\n        "docs/publications/2026-09-25-leibniz-qikvrt/PROSA_VOM_UNTERSCHIED_ZU_QIKVRT_DE.md",\n        "docs/publications/2026-09-25-leibniz-qikvrt/SCIENTIFIC_ARTICLE_LEIBNIZ_QIKVRT_DE.md",\n        "docs/publications/2026-09-25-leibniz-qikvrt/Leibniz_QIK-VRT_Monaden_und_evidenzgebundener_Unterschied.pdf",\n    }\n    if not required_leibniz.issubset(seen):\n        raise CandidateError("Leibniz/QIK-VRT prose or scientific PDF missing from candidate")\n    pdf_path = ROOT / "docs/publications/2026-09-25-leibniz-qikvrt/Leibniz_QIK-VRT_Monaden_und_evidenzgebundener_Unterschied.pdf"\n    pdf = pdf_path.read_bytes()\n    if not pdf.startswith(b"%PDF-1.4") or not pdf.rstrip().endswith(b"%%EOF"):\n        raise CandidateError("Leibniz scientific PDF structure is invalid")\n    aggregate = hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest()
    if aggregate != freeze.get("exact_content_aggregate_sha256"):
        raise CandidateError("content aggregate mismatch")
    if total != freeze.get("total_bytes"):
        raise CandidateError("content total byte mismatch")
    return {
        "file_count": len(files),
        "total_bytes": total,
        "aggregate_sha256": aggregate,
    }


def verify_claims_and_sources() -> None:
    scientific = (PUB / "SCIENTIFIC_ARTICLE_DE.md").read_text(encoding="utf-8")
    general = (ROOT / "docs/QIKVRT_UNIVERSAL_PROOF_AND_THOUGHT_SCHEMA_DE.md").read_text(
        encoding="utf-8"
    )
    proof = (ROOT / "docs/ONTOLOGICAL_ORIGIN_OF_DIFFERENCE_DE.md").read_text(
        encoding="utf-8"
    )
    core = (FORMAL / "QIKVRTUniversalOntology/Core.lean").read_text(encoding="utf-8")
    audit = (FORMAL / "QIKVRTUniversalOntology/AxiomAudit.lean").read_text(encoding="utf-8")

    for label, text in (("scientific", scientific), ("general", general), ("proof", proof)):
        if STATEMENT not in text:
            raise CandidateError(f"canonical statement missing from {label} article")

    for constant in PROOF_CONSTANTS:
        short = constant.rsplit(".", 1)[1]
        if f"theorem {short}" not in core:
            raise CandidateError(f"Lean theorem missing: {short}")
        if f"#print axioms {constant}" not in audit:
            raise CandidateError(f"axiom audit binding missing: {constant}")

    claims = load_json(PUB / "CLAIM_MATRIX.json")
    by_id = {row["claim_id"]: row for row in claims["claims"]}
    expected = {
        "OPD-001": PROOF_CONSTANTS[0],
        "OPD-002": PROOF_CONSTANTS[1],
        "OPD-003": PROOF_CONSTANTS[2],
    }
    for claim_id, constant in expected.items():
        row = by_id.get(claim_id)
        if not row or row.get("classification") != "FORMAL_THEOREM":
            raise CandidateError(f"formal claim missing: {claim_id}")
        if row.get("proof_constant") != constant:
            raise CandidateError(f"proof binding mismatch: {claim_id}")
    if by_id["OPD-004"].get("classification") != "INTERPRETATION":
        raise CandidateError("natural-language synthesis must remain interpretative")
    if by_id["OPD-005"].get("status") != "NOT_CLAIMED":
        raise CandidateError("physical-first-instant claim must remain NOT_CLAIMED")

    evidence = load_json(PUB / "SOURCE_EVIDENCE_BINDINGS.json")
    prior = [x for x in evidence.get("sources", []) if x.get("id") == "SRC-PRIOR-ZENODO"]
    if len(prior) != 1 or prior[0].get("doi") != "10.5281/zenodo.21582781":
        raise CandidateError("prior Zenodo DOI binding missing")

    returned = load_json(REL / "PREPUBLICATION_RETURN_RECEIPT.json")
    if returned.get("schema") != "qikvrt_prepublication_return_receipt_v2":
        raise CandidateError("return receipt schema mismatch")
    if returned["return"].get("candidate_returned_to_owner") is not True:
        raise CandidateError("candidate has not been returned to owner")
    if returned["authorization"].get("exact_upload_authorized") is not False:
        raise CandidateError("return receipt must not synthesize upload authorization")


def verify_axiom_outputs(core_path: pathlib.Path, extended_path: pathlib.Path) -> dict:
    core = parse_axioms(core_path)
    extended = parse_axioms(extended_path)
    if len(core) != CORE_COUNT:
        raise CandidateError(f"core axiom count {len(core)} != {CORE_COUNT}")
    if len(extended) != EXTENDED_COUNT:
        raise CandidateError(
            f"extended axiom count {len(extended)} != {EXTENDED_COUNT}"
        )
    for constant in PROOF_CONSTANTS:
        if constant not in core:
            raise CandidateError(f"origin theorem absent from core receipt: {constant}")
        if core[constant]:
            raise CandidateError(
                f"origin theorem unexpectedly depends on axioms: "
                f"{constant} -> {sorted(core[constant])}"
            )
    forbidden = {
        name: sorted(axioms - ALLOWED_FOUNDATIONAL_AXIOMS)
        for name, axioms in extended.items()
        if axioms - ALLOWED_FOUNDATIONAL_AXIOMS
    }
    if forbidden:
        raise CandidateError(f"forbidden extended axioms: {forbidden}")
    return {
        "core_constants": len(core),
        "extended_constants": len(extended),
        "origin_theorems_axiom_free": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-axiom-output", type=pathlib.Path, required=True)
    parser.add_argument("--extended-axiom-output", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    content = verify_content_freeze()
    verify_claims_and_sources()
    axioms = verify_axiom_outputs(
        args.core_axiom_output.resolve(),
        args.extended_axiom_output.resolve(),
    )

    receipt = {
        "schema": "qikvrt_ontological_priority_prepublication_gate_receipt_v1",
        "publication_id": "qikvrt-ontological-priority-of-difference-2026-v1",
        "repository": "Goldkelch/qik-vrt",
        "source_head": git_value("rev-parse", "HEAD"),
        "source_tree": git_value("rev-parse", "HEAD^{tree}"),
        "content": content,
        "formal": axioms,
        "proof_constants": list(PROOF_CONSTANTS),
        "prepublication_return_complete": True,
        "owner_exact_upload_authorization": False,
        "zenodo_effect_executed": False,
        "status": "PASS_PREPUBLICATION_GATES_UPLOAD_STILL_BLOCKED",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
