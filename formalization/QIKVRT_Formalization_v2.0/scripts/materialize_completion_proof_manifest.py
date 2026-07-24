#!/usr/bin/env python3
"""Materialize proof-object coverage for the manuscript-completion tranche.

The persistent object set is intentionally scoped to the twenty definition
bindings, the ten theorem-completion bindings, and the pre-existing
``ESC-003A`` proof object. Older source-claim bindings remain authoritative in
the claim graph and their original registries; duplicating them here would
create a parallel proof-object persistence contract instead of reusing their
established authorities.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath

import materialize_completion as completion

ROOT = completion.PROJECT_ROOT
MANIFEST = ROOT / "proofs" / "PROOF_OBJECT_MANIFEST.json"
STATUS = "KERNEL_CHECK_REQUIRED_ON_EVERY_DISTINCT_INPUT_SET"
PRESERVED_LEGACY_CLAIMS = {"ESC-003A"}
PROOF_BINDINGS = {
    **completion.DEFINITION_BINDINGS,
    **completion.THEOREM_BINDINGS,
}
EXPECTED_OBJECT_COUNT = len(PRESERVED_LEGACY_CLAIMS) + len(PROOF_BINDINGS)


def compiled_object(source_path: str) -> str:
    source = PurePosixPath(source_path)
    return str(
        PurePosixPath(".lake/build/lib/lean").joinpath(
            source.with_suffix(".olean")
        )
    )


def materialized() -> dict:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    current = {
        item["claimId"]: item
        for item in value.get("objects", [])
        if isinstance(item, dict) and isinstance(item.get("claimId"), str)
    }
    missing_legacy = PRESERVED_LEGACY_CLAIMS - set(current)
    if missing_legacy:
        raise ValueError(
            f"required pre-existing proof objects are absent: {sorted(missing_legacy)}"
        )
    objects = {
        claim_id: current[claim_id]
        for claim_id in PRESERVED_LEGACY_CLAIMS
    }
    for claim_id, binding in PROOF_BINDINGS.items():
        objects[claim_id] = {
            "claimId": claim_id,
            "statementConstant": binding["statementConstant"],
            "proofConstant": binding["proofConstant"],
            "registryConstant": binding["registryConstant"],
            "sourcePath": binding["sourcePath"],
            "registrySourcePath": binding["registrySourcePath"],
            "compiledObject": compiled_object(binding["sourcePath"]),
            "status": STATUS,
        }
    value["objects"] = [objects[key] for key in sorted(objects)]
    if len(value["objects"]) != EXPECTED_OBJECT_COUNT:
        raise ValueError(
            f"expected {EXPECTED_OBJECT_COUNT} proof objects, got {len(value['objects'])}"
        )
    return value


def serialize(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        expected = serialize(materialized())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot materialize completion proof-object manifest: {exc}") from exc
    if args.check:
        if not args.manifest.is_file() or args.manifest.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"stale completion proof-object manifest: {args.manifest}")
        print(
            "PASS completion proof-object manifest current: "
            f"{EXPECTED_OBJECT_COUNT} manuscript proof bindings"
        )
        return 0
    args.manifest.write_text(expected, encoding="utf-8")
    print(
        "PASS wrote completion proof-object manifest: "
        f"{EXPECTED_OBJECT_COUNT} manuscript proof bindings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
