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
    candidate_path = root / "ZENODO_CANDIDATE.json"
    request_path = root / "ZENODO_PUBLICATION_REQUEST.json"
    authorization = "ABSENT"
    if candidate_path.is_file():
        candidate_raw = candidate_path.read_bytes()
        candidate = json.loads(candidate_raw.decode("utf-8"))
        candidate_required = {
            "schema","bundle_id","title","creators","language","license",
            "keywords","status","publication_preconditions","zenodo_mutation_performed"
        }
        candidate_optional = {"contributors"}
        if not candidate_required.issubset(candidate) or set(candidate) - candidate_required - candidate_optional:
            raise SystemExit("BLOCK: Zenodo candidate shape mismatch")
        if candidate["schema"] != "qikvrt_zenodo_candidate_v1":
            raise SystemExit("BLOCK: unsupported Zenodo candidate schema")
        if candidate["bundle_id"] != manifest["bundle_id"]:
            raise SystemExit("BLOCK: Zenodo candidate bundle mismatch")
        if candidate["status"] != "STAGED_NOT_PUBLISHED" or candidate["zenodo_mutation_performed"] is not False:
            raise SystemExit("BLOCK: Zenodo candidate is not inert")
        if request_path.is_file():
            request_raw = request_path.read_bytes()
            request = json.loads(request_raw.decode("utf-8"))
            request_keys = {
                "schema","request_id","bundle_id","repository","candidate",
                "state","confirm","external_effects","required_before_authorization"
            }
            if set(request) != request_keys:
                raise SystemExit("BLOCK: Zenodo publication request shape mismatch")
            if request["schema"] != "qikvrt_zenodo_publication_request_v1":
                raise SystemExit("BLOCK: unsupported Zenodo publication request schema")
            if request["bundle_id"] != manifest["bundle_id"] or request["repository"] != manifest["repository_scope"]["authority"]:
                raise SystemExit("BLOCK: Zenodo publication request subject mismatch")
            binding = request["candidate"]
            if set(binding) != {"head","tree","canonical_path","canonical_sha256","routing_sha256","zenodo_candidate_sha256"}:
                raise SystemExit("BLOCK: Zenodo publication request binding shape mismatch")
            if not all(isinstance(binding[key], str) and len(binding[key]) == 40 for key in ("head","tree")):
                raise SystemExit("BLOCK: candidate Git identity is invalid")
            artifacts = {item["path"]: item for item in manifest["artifacts"]}
            canonical = artifacts.get(binding["canonical_path"])
            if canonical is None or canonical["sha256"] != binding["canonical_sha256"]:
                raise SystemExit("BLOCK: canonical publication binding mismatch")
            if sha256(root / "PUBLICATION_ROUTING.json") != binding["routing_sha256"]:
                raise SystemExit("BLOCK: routing manifest binding mismatch")
            if hashlib.sha256(candidate_raw).hexdigest() != binding["zenodo_candidate_sha256"]:
                raise SystemExit("BLOCK: Zenodo candidate binding mismatch")
            if request["state"] != "NOT_AUTHORIZED" or request["confirm"] != "NOT_AUTHORIZED":
                raise SystemExit("BLOCK: this router accepts only inert authorization requests")
            if request["external_effects"] != {"zenodo_mutation_authorized": False, "publication_authorized": False}:
                raise SystemExit("BLOCK: external effect authorization inflated")
            authorization = "NOT_AUTHORIZED"
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
      "authorization":authorization,
      "external_effect_performed":False
    }
    print(json.dumps(result,ensure_ascii=False,sort_keys=True) if ns.json else "\n".join(f"{k}={v}" for k,v in result.items()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
