#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "proofs" / "PROOF_OBJECT_MANIFEST.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"BLOCK PROOF_OBJECT_MANIFEST_INVALID: {message}")


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(data.get("schema") == "qikvrt_proof_object_manifest_v1", "unknown schema")
    policy = data.get("policy", {})
    require(policy.get("cacheMayReplaceKernelVerification") is False,
            "cache must never replace kernel verification")
    require(policy.get("cacheMissRequiresRebuild") is True,
            "cache miss must require rebuild")

    objects = data.get("objects")
    require(isinstance(objects, list) and objects, "objects must be non-empty")
    seen: set[str] = set()
    for item in objects:
        claim_id = item.get("claimId")
        require(isinstance(claim_id, str) and claim_id, "claimId missing")
        require(claim_id not in seen, f"duplicate claimId {claim_id}")
        seen.add(claim_id)
        for key in ("statementConstant", "proofConstant", "registryConstant",
                    "sourcePath", "registrySourcePath", "compiledObject"):
            require(isinstance(item.get(key), str) and item[key],
                    f"{claim_id}: {key} missing")
        for key in ("sourcePath", "registrySourcePath"):
            require((ROOT / item[key]).is_file(), f"{claim_id}: missing {item[key]}")

        source = (ROOT / item["sourcePath"]).read_text(encoding="utf-8")
        registry = (ROOT / item["registrySourcePath"]).read_text(encoding="utf-8")
        require(item["proofConstant"].split(".")[-1] in source,
                f"{claim_id}: proof constant not found in source")
        require(item["registryConstant"].split(".")[-1] in registry,
                f"{claim_id}: registry constant not found")

    print(json.dumps({
        "schema": "qikvrt_proof_object_manifest_verification_v1",
        "status": "PASS",
        "claims": sorted(seen),
        "count": len(seen),
        "cache_replaces_kernel": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
