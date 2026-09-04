#!/usr/bin/env python3
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

EXECUTION_HEAD = "0cc8e5fe667a85bf4c0f112868dc43f47a4829dc"
MANIFEST_REL = "release/relational-time-monotonic-evidence-sphere-zenodo-v1/publish-request.json"
MANIFEST_SHA256 = "fbb9c4f4e3369c199a0fe542ce345069100d03fc50c098f8b1e200dee67cc648"
AUTHORIZATION_ID = "qikvrt-relational-time-evidence-sphere-v1-20260831-2f5a9b9aa7cc4f92"
PUBLICATION_ID = "qikvrt-relational-time-monotonic-evidence-sphere-v1"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: probe SOURCE_ROOT")
    root = pathlib.Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(root / "tools"))
    import qikvrt_zenodo_publish as publish

    token = os.environ.get("ZENODO_ACCESS_TOKEN", "")
    if len(token) < 20 or any(ch.isspace() for ch in token):
        raise SystemExit("BLOCK: zenodo-production token missing or structurally invalid")

    manifest_path = root / MANIFEST_REL
    manifest = publish.load_manifest(manifest_path, root)
    if manifest.get("repository") != "Goldkelch/qik-vrt":
        raise SystemExit("BLOCK: manifest repository differs")
    if manifest.get("manifest_sha256") != MANIFEST_SHA256:
        raise SystemExit("BLOCK: manifest digest differs")
    authorization = manifest.get("owner_authorization")
    if not isinstance(authorization, dict):
        raise SystemExit("BLOCK: owner authorization missing")
    if authorization.get("authorization_id") != AUTHORIZATION_ID:
        raise SystemExit("BLOCK: authorization id differs")
    if authorization.get("publication_id") != PUBLICATION_ID:
        raise SystemExit("BLOCK: publication id differs")

    def public_get_json(url: str):
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "qik-vrt-zenodo-readonly-recovery",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 200 or response.geturl() != url:
                raise RuntimeError("public GitHub lock readback rejected")
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise RuntimeError("public GitHub lock readback exceeded byte bound")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("public GitHub lock readback was not an object")
        return value

    ref = authorization["remote_consumption_ref"]
    if not ref.startswith("refs/tags/"):
        raise SystemExit("BLOCK: consumption lock is not a tag ref")
    suffix = ref.removeprefix("refs/")
    ref_url = (
        "https://api.github.com/repos/Goldkelch/qik-vrt/git/ref/"
        + urllib.parse.quote(suffix, safe="/")
    )
    ref_value = public_get_json(ref_url)
    target = ref_value.get("object")
    tag_object = target.get("sha") if isinstance(target, dict) else None
    if not isinstance(tag_object, str):
        raise SystemExit("BLOCK: consumed lock lacks annotated tag object")
    publish._validate_github_ref_response(ref_value, ref, tag_object)
    tag_value = public_get_json(
        "https://api.github.com/repos/Goldkelch/qik-vrt/git/tags/" + tag_object
    )
    publish._validate_github_tag_response(
        tag_value,
        publish._expected_consumption_tag(manifest, EXECUTION_HEAD),
        tag_object,
    )

    OriginalRequest = urllib.request.Request

    class GetOnlyRequest(OriginalRequest):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.get_method() != "GET":
                raise RuntimeError(
                    "BLOCK: non-GET network method attempted during read-only recovery inventory"
                )

    urllib.request.Request = GetOnlyRequest
    base_url = publish.zenodo.validate_base_url(
        os.environ.get("ZENODO_API_BASE", "https://zenodo.org/api")
    )
    client = publish.zenodo.ZenodoClient(token, base_url)
    metadata = manifest["metadata"]
    entries = publish._shared_entries(manifest["files"])

    inventory = publish._list_all_owned_depositions(client, token)
    identity_candidates = []
    canonical_matches = []
    divergent_candidates = []

    for item in inventory:
        if not publish._inventory_publication_identity_candidate(item, metadata):
            continue
        record_id = publish.zenodo._record_id(item, "read-only recovery inventory")
        state, current = client.get_deposition_or_record(record_id)
        doi = publish.zenodo._doi_from_deposition(current, "read-only recovery record")
        identity_candidates.append({"record_id": record_id, "doi": doi, "state": state})
        try:
            if state == "published":
                if not publish.zenodo._published_metadata_matches(current.get("metadata"), metadata):
                    raise publish.zenodo.ZenodoError(
                        "publication-identity candidate has divergent public metadata"
                    )
                public = client.wait_for_gated_record(
                    record_id,
                    metadata,
                    entries,
                    doi,
                    published=True,
                    initial=current,
                )
                canonical_matches.append(
                    {"record_id": record_id, "doi": doi, "public": True}
                )
            else:
                expected_metadata = dict(metadata)
                expected_metadata.pop("prereserve_doi", None)
                if not publish.zenodo._metadata_matches(
                    current.get("metadata"), expected_metadata
                ):
                    raise publish.zenodo.ZenodoError(
                        "publication-identity candidate has divergent draft metadata"
                    )
                server_files = client._server_files(current)
                if server_files:
                    client.gate_record(
                        current,
                        record_id,
                        metadata,
                        entries,
                        doi,
                        published=False,
                    )
                canonical_matches.append(
                    {"record_id": record_id, "doi": doi, "public": False}
                )
        except Exception as exc:
            message = str(exc).replace(token, "<redacted>") if token else str(exc)
            divergent_candidates.append(
                {
                    "record_id": record_id,
                    "doi": doi,
                    "state": state,
                    "reason_type": type(exc).__name__,
                    "reason": message,
                }
            )

    count = len(canonical_matches)
    if divergent_candidates:
        disposition = "HOLD"
        disposition_reason = "DIVERGENT_PUBLICATION_IDENTITY_CANDIDATE"
    elif count == 0:
        disposition = "CREATE_ALLOWED"
        disposition_reason = "ZERO_CANONICAL_MATCHES"
    elif count == 1:
        disposition = "RECOVER"
        disposition_reason = "EXACTLY_ONE_CANONICAL_MATCH"
    else:
        disposition = "HOLD"
        disposition_reason = "MULTIPLE_CANONICAL_MATCHES"

    result = {
        "schema": "qikvrt_zenodo_readonly_recovery_inventory_v2",
        "repository": manifest["repository"],
        "execution_head": EXECUTION_HEAD,
        "source_head": manifest["source_head"],
        "manifest_sha256": manifest["manifest_sha256"],
        "authorization_id": AUTHORIZATION_ID,
        "publication_id": PUBLICATION_ID,
        "remote_consumption_ref": ref,
        "remote_consumption_tag_object": tag_object,
        "zenodo_api_base": base_url,
        "network_policy": "GET_ONLY",
        "stable_inventory_passes": 2,
        "owned_inventory_count": len(inventory),
        "publication_identity_candidate_count": len(identity_candidates),
        "publication_identity_candidates": identity_candidates,
        "canonical_match_count": count,
        "canonical_matches": canonical_matches,
        "divergent_identity_candidate_count": len(divergent_candidates),
        "divergent_identity_candidates": divergent_candidates,
        "disposition": disposition,
        "disposition_reason": disposition_reason,
    }
    print(
        "QIKVRT_READONLY_RECOVERY_INVENTORY="
        + json.dumps(result, sort_keys=True, separators=(",", ":"))
    )
    if disposition == "HOLD":
        raise SystemExit("HOLD: read-only recovery inventory is not uniquely actionable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
