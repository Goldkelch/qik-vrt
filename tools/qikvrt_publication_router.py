#!/usr/bin/env python3
"""Fail-closed publication router for QIK-VRT publication bundles."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args()
    root = ns.bundle
    manifest = json.loads((root / "PUBLICATION_ROUTING.json").read_text(encoding="utf-8"))
    required = {"schema","bundle_id","title","author","repository_scope","artifacts","routes","automation","release_claims"}
    if set(manifest) != required:
        raise SystemExit("BLOCK: routing manifest shape mismatch")
    if manifest["schema"] != "qikvrt_publication_routing_manifest_v1":
        raise SystemExit("BLOCK: unsupported routing schema")
    for item in manifest["artifacts"]:
        path = root / item["path"]
        if not path.is_file():
            raise SystemExit(f"BLOCK: missing artifact {item['path']}")
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise SystemExit(f"BLOCK: artifact digest mismatch {item['path']}")
    routes = manifest["routes"]
    if routes["repository"]["disposition"] != "CANDIDATE_REQUIRED":
        raise SystemExit("BLOCK: repository route must remain candidate-gated")
    if routes["zenodo"]["effect_gate"] != "EXPLICIT_HASH_BOUND_PUBLICATION_REQUEST_REQUIRED":
        raise SystemExit("BLOCK: Zenodo route is not explicitly gated")
    if routes["ietf"]["protocol_change_required"] is not False:
        raise SystemExit("BLOCK: unexpected IETF protocol change")
    if any(manifest["release_claims"].values()):
        raise SystemExit("BLOCK: completion claim inflation")
    result = {
      "schema":"qikvrt_publication_routing_result_v1",
      "bundle_id":manifest["bundle_id"],
      "repository":"CANDIDATE",
      "zenodo":"STAGED_REQUIRES_EXPLICIT_REQUEST",
      "ietf":"NO_SUBMISSION_SCOPE_NOTE_ONLY",
      "external_effect_performed":False
    }
    print(json.dumps(result,ensure_ascii=False,sort_keys=True) if ns.json else "\n".join(f"{k}={v}" for k,v in result.items()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
