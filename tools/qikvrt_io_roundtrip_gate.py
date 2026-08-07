#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate repository-persisted I/O work units and deterministically route claims.

This tool is deliberately fail-closed. It validates persistence/provenance structure,
prevents proof inflation, and emits a machine-readable routing decision. It does not
perform credentialed Zenodo or IETF writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/UNIVERSAL_IO_EVIDENCE_ROUNDTRIP_V1.json"
WORK_UNITS = ROOT / "state/io_work_units"
REQUIRED = {
    "schema", "work_unit_id", "observed_at", "direction", "kind", "provenance",
    "payload_binding", "epistemic_class", "persistence", "derivation", "publication",
}
EPISTEMIC = {
    "FORMAL_THEOREM_CANDIDATE", "FORMAL_CONDITIONAL_CANDIDATE", "EMPIRICAL_CLAIM",
    "INTERPRETIVE_CLAIM", "NORMATIVE_CLAIM", "PROVENANCE_ONLY", "UNRESOLVED",
}
DIRECTIONS = {"INPUT", "OUTPUT", "INTERNAL_TOOL_RESULT", "EXTERNAL_EFFECT"}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return value


def validate_unit(path: Path) -> dict[str, Any]:
    unit = load_json(path)
    missing = sorted(REQUIRED - set(unit))
    if missing:
        raise ValueError(f"{path}: missing required fields: {', '.join(missing)}")
    if unit["direction"] not in DIRECTIONS:
        raise ValueError(f"{path}: invalid direction {unit['direction']!r}")
    if unit["epistemic_class"] not in EPISTEMIC:
        raise ValueError(f"{path}: invalid epistemic_class {unit['epistemic_class']!r}")

    binding = unit["payload_binding"]
    if not isinstance(binding, dict) or not binding.get("sha256"):
        raise ValueError(f"{path}: payload_binding.sha256 is required")
    digest = str(binding["sha256"]).lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError(f"{path}: payload_binding.sha256 must be a lowercase SHA-256 hex digest")

    persistence = unit["persistence"]
    if not isinstance(persistence, dict) or persistence.get("repository") != "Goldkelch/qik-vrt":
        raise ValueError(f"{path}: persistence.repository must bind Goldkelch/qik-vrt for Authority work units")
    if persistence.get("path") != path.relative_to(ROOT).as_posix():
        raise ValueError(f"{path}: persistence.path must equal repository-relative work-unit path")

    derivation = unit["derivation"]
    publication = unit["publication"]
    if not isinstance(derivation, dict) or not isinstance(publication, dict):
        raise ValueError(f"{path}: derivation and publication must be objects")

    proof_status = derivation.get("machine_proof_status", "NOT_APPLICABLE")
    formal = unit["epistemic_class"] in {"FORMAL_THEOREM_CANDIDATE", "FORMAL_CONDITIONAL_CANDIDATE"}
    if proof_status == "PROVED" and not formal:
        raise ValueError(f"{path}: non-formal epistemic class cannot claim machine_proof_status=PROVED")
    if proof_status == "PROVED":
        receipt = derivation.get("execution_bound_receipt")
        if not isinstance(receipt, dict) or not all(receipt.get(k) for k in ("proof_system", "toolchain", "source_sha256", "receipt_sha256")):
            raise ValueError(f"{path}: PROVED requires an execution-bound proof receipt")

    connectable = bool(publication.get("connectable"))
    zenodo = "BUILD_CANDIDATE" if connectable and proof_status in {"PROVED", "NOT_APPLICABLE", "EVIDENCE_BOUND"} else "HOLD"
    ietf_relevant = bool(publication.get("ietf_relevant"))
    ietf = "BUILD_CANDIDATE" if zenodo == "BUILD_CANDIDATE" and ietf_relevant else "NOT_APPLICABLE"

    return {
        "path": path.relative_to(ROOT).as_posix(),
        "work_unit_id": unit["work_unit_id"],
        "canonical_record_sha256": sha256_bytes(canonical_bytes(unit)),
        "machine_proof_status": proof_status,
        "zenodo_route": zenodo,
        "ietf_route": ietf,
        "external_effect": "SEPARATE_AUTHORIZATION_REQUIRED",
    }


def run(paths: list[Path]) -> dict[str, Any]:
    policy = load_json(POLICY)
    if policy.get("schema") != "qikvrt_universal_io_evidence_roundtrip_v1":
        raise ValueError("unexpected universal I/O policy schema")
    results = [validate_unit(path) for path in sorted(paths)]
    return {
        "schema": "qikvrt_io_roundtrip_gate_receipt_v1",
        "policy_sha256": sha256_bytes(POLICY.read_bytes()),
        "work_units_checked": len(results),
        "results": results,
        "status": "PASS",
        "publication_effect_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="Repository-relative work-unit JSON paths; defaults to state/io_work_units/*.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    paths = [ROOT / p for p in args.paths] if args.paths else list(WORK_UNITS.glob("*.json"))
    try:
        receipt = run(paths)
    except Exception as exc:
        if args.json:
            print(json.dumps({"schema": "qikvrt_io_roundtrip_gate_receipt_v1", "status": "BLOCK", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        else:
            print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    else:
        print(f"PASS: {receipt['work_units_checked']} I/O work unit(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
