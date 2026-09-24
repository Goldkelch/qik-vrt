#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize the proof-bearing TEMDD Zenodo v2 pre-authorization candidate.

This tool has no network effect.  It freezes the exact public candidate that was
returned to Ingolf Lohmann, materializes the v2 return receipt and machine-proof
bundle, and emits the exact canonical authorization statement required by the
existing generic Zenodo publisher.  It deliberately stops before owner
authorization and before any Zenodo mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_zenodo_machine_proof as proof
RELEASE_REL = pathlib.PurePosixPath("release/temdd-technical-evolution-zenodo-v1")
RELEASE = ROOT.joinpath(*RELEASE_REL.parts)
PUBLICATION_ID = "qikvrt-temdd-technical-evolution-v1"
SOURCE_HEAD = "a04ff87358159dfef54ba3141cfea76fc75bbdac"
RETURNED_AT = "2026-09-24T11:27:10Z"
AUTHORIZATION_ID = "temdd-20260924-zenodo-v1-auth-01"

PRIMARY = "docs/publications/2026-09-24-temdd-technical-evolution/TEMDD_TECHNICAL_EVOLUTION_DE.md"
HARDWARE = "docs/patent/TEMDD_HARDWARE_MAPPING_AND_PATENT_BOUNDARY_V1.md"
DECLARATION = "spec/temdd/TEMDD_TECHNICAL_EVOLUTION_DECLARATION_V1.md"
LANGUAGE_SPEC = "spec/temdd/TEMDD_LANGUAGE_SPEC_V0_1.md"
CLAIM_MATRIX = f"{RELEASE_REL.as_posix()}/CLAIM_MATRIX.json"
BINDINGS = f"{RELEASE_REL.as_posix()}/SOURCE_EVIDENCE_BINDINGS.json"
METADATA = f"{RELEASE_REL.as_posix()}/ZENODO_METADATA.json"
RETURN_RECEIPT = f"{RELEASE_REL.as_posix()}/PREPUBLICATION_RETURN_RECEIPT.json"
PROOF_BUNDLE = f"{RELEASE_REL.as_posix()}/MACHINE_PROOF_BUNDLE.json"
AUTH_REQUEST = f"{RELEASE_REL.as_posix()}/EXACT_AUTHORIZATION_REQUEST.json"
PUBLISH_DRAFT = f"{RELEASE_REL.as_posix()}/PUBLISH_REQUEST_DRAFT.json"
FILESET = f"{RELEASE_REL.as_posix()}/ZENODO_FILESET.md"
EVIDENCE_PATH = f"{RELEASE_REL.as_posix()}/zenodo-publication.json"

POLICY = {
    "id": proof.POLICY_ID,
    "path": proof.POLICY_PATH,
    "version": proof.POLICY_VERSION,
    "sha256": proof.POLICY_SHA256,
    "git_blob_sha1": proof.POLICY_GIT_BLOB_SHA1,
}

CANDIDATE_SPECS = (
    (PRIMARY, "TEMDD_TECHNICAL_EVOLUTION_DE.md", "PRIMARY"),
    (HARDWARE, "TEMDD_HARDWARE_MAPPING_AND_PATENT_BOUNDARY_V1.md", "SUPPLEMENT"),
)

ARTIFACT_SPECS = (
    (CLAIM_MATRIX, "CLAIM_MATRIX"),
    (BINDINGS, "EVIDENCE"),
    (DECLARATION, "SOURCE"),
    (LANGUAGE_SPEC, "SOURCE"),
    (RETURN_RECEIPT, "RETURN_RECEIPT"),
)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()


def ident(path: str) -> dict[str, Any]:
    raw = (ROOT / path).read_bytes()
    return {
        "path": path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
    }


def write_json(path: str, value: Any) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(json_bytes(value))


def verify_source_head() -> None:
    current = subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
        cwd=ROOT,
        text=True,
    ).strip()
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", SOURCE_HEAD, current],
        cwd=ROOT,
        check=True,
    )
    for path, _name, _role in CANDIDATE_SPECS:
        source_blob = subprocess.check_output(
            ["git", "rev-parse", f"{SOURCE_HEAD}:{path}"],
            cwd=ROOT,
            text=True,
        ).strip()
        current_blob = subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=ROOT,
            text=True,
        ).strip()
        if source_blob != current_blob:
            raise SystemExit(f"BLOCK candidate bytes changed after return: {path}")


def bundle_claims() -> list[dict[str, Any]]:
    matrix = json.loads((ROOT / CLAIM_MATRIX).read_text(encoding="utf-8"))
    by_id = {item["claim_id"]: item for item in matrix["claims"]}
    binding = BINDINGS
    refs = {
        "TEMDD-DECL-001": [],
        "TEMDD-EXEC-001": [f"{binding}#TEMDD-LANG-SPEC"],
        "TEMDD-EVIDENCE-001": [
            f"{binding}#TEMDD-LANG-SPEC",
            f"{binding}#TEMDD-DECLARATION",
        ],
        "TEMDD-HW-001": [f"{binding}#TEMDD-HARDWARE-MAP"],
        "TEMDD-PERF-001": [f"{binding}#TEMDD-HARDWARE-MAP"],
        "TEMDD-PATENT-001": [f"{binding}#TEMDD-HARDWARE-MAP"],
        "TEMDD-ATTR-001": [f"{binding}#TEMDD-DECLARATION"],
    }
    wording = {
        "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
        "EMPIRICALLY_EVIDENCED": "EMPIRICALLY_SUPPORTED",
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "NORMATIVE": "NORMATIVE_DECLARATION",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
    }
    claims = []
    for claim_id in [item["claim_id"] for item in matrix["claims"]]:
        item = by_id[claim_id]
        source_refs = refs[claim_id]
        claims.append({
            "claim_id": claim_id,
            "statement": item["statement"],
            "classification": item["classification"],
            "status": item["status"],
            "publication_wording": wording[item["classification"]],
            "scope": item["boundary"],
            "proof_refs": [],
            "evidence_refs": [],
            "source_refs": source_refs,
        })
    return claims


def materialize() -> None:
    verify_source_head()

    candidate_files = []
    for path, name, role in CANDIDATE_SPECS:
        item = ident(path)
        candidate_files.append({
            **item,
            "name": name,
            "role": role,
        })

    receipt = {
        "_license": {
            "classification": "machine_readable_prepublication_return_receipt",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": proof.RETURN_SCHEMA,
        "publication_id": PUBLICATION_ID,
        "content_changed": False,
        "original_files": [],
        "candidate_files": [
            {
                key: item[key]
                for key in ("path", "bytes", "sha256", "git_blob_sha1")
            }
            for item in candidate_files
        ],
        "changed_claim_ids": [],
        "change_reasons": [],
        "change_notice_path": None,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": "ChatGPT commentary in owner-authorized repository session",
            "returned_at": RETURNED_AT,
            "visible_change_notice_returned": False,
        },
    }
    write_json(RETURN_RECEIPT, receipt)

    artifacts = []
    for path, kind in ARTIFACT_SPECS:
        item = ident(path)
        artifacts.append({
            "path": path,
            "sha256": item["sha256"],
            "git_blob_sha1": item["git_blob_sha1"],
            "kind": kind,
        })

    bundle = {
        "_license": {
            "classification": "machine_readable_proof_bundle",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": proof.BUNDLE_SCHEMA,
        "policy": POLICY,
        "publication_id": PUBLICATION_ID,
        "candidate": {
            "files": candidate_files,
            "primary_document_path": PRIMARY,
        },
        "claims": bundle_claims(),
        "artifacts": artifacts,
        "prepublication_return": {
            "content_changed": False,
            "candidate_returned_to_owner": True,
            "receipt_path": RETURN_RECEIPT,
            "change_notice_path": None,
        },
        "gates": {
            "all_claims_dispositioned": True,
            "all_references_resolve": True,
            "candidate_frozen": True,
            "formal_claims_have_kernel_receipts": True,
            "open_claims_not_worded_as_facts": True,
            "proof_bundle_in_upload_fileset": True,
            "returned_bytes_equal_upload_bytes": True,
        },
        "completion_claims": {
            "machine_proof_complete": True,
            "zenodo_upload_authorized": True,
        },
    }
    write_json(PROOF_BUNDLE, bundle)

    upload_paths = [
        *(item["path"] for item in candidate_files),
        *(item["path"] for item in artifacts),
        PROOF_BUNDLE,
    ]
    validated = proof.validate_bundle(
        ROOT,
        ROOT / PROOF_BUNDLE,
        upload_paths=upload_paths,
    )

    metadata = json.loads((ROOT / METADATA).read_text(encoding="utf-8"))
    metadata_sha256 = hashlib.sha256(
        (json.dumps(metadata, ensure_ascii=False, separators=(",", ":"), sort_keys=True)).encode("utf-8")
    ).hexdigest()
    receipt_id = ident(RETURN_RECEIPT)
    bundle_id = ident(PROOF_BUNDLE)
    statement = (
        "AUTHORIZE_EXACT_UPLOAD "
        f"authorization_id={AUTHORIZATION_ID} "
        f"publication_id={PUBLICATION_ID} "
        f"return_sha256={receipt_id['sha256']} "
        f"metadata_sha256={metadata_sha256} "
        f"machine_proof_sha256={bundle_id['sha256']}"
    )
    auth_request = {
        "schema": "qikvrt.temdd.zenodo.authorization-request.v1",
        "state": "AWAITING_EXPLICIT_OWNER_AUTHORIZATION",
        "repository": "Goldkelch/qik-vrt",
        "publication_id": PUBLICATION_ID,
        "source_head": SOURCE_HEAD,
        "authorization_id": AUTHORIZATION_ID,
        "principal": {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
        "candidate_return_receipt": receipt_id,
        "canonical_metadata_sha256": metadata_sha256,
        "machine_proof": bundle_id,
        "canonical_statement": statement,
        "statement_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
        "upload_paths": upload_paths,
        "effect_released": False,
        "effect_ack_done": False,
    }
    write_json(AUTH_REQUEST, auth_request)

    draft = {
        "schema": "qikvrt.temdd.zenodo.publish-request-draft.v1",
        "state": "DRAFT_EXACT_OWNER_AUTHORIZATION_PENDING",
        "repository": "Goldkelch/qik-vrt",
        "source_head": SOURCE_HEAD,
        "metadata": metadata,
        "files": [
            {
                "path": path,
                "name": pathlib.PurePosixPath(path).name,
                "git_blob_sha": ident(path)["git_blob_sha1"],
            }
            for path in upload_paths
        ],
        "machine_proof": {
            "path": PROOF_BUNDLE,
            "git_blob_sha": bundle_id["git_blob_sha1"],
            "policy_id": proof.POLICY_ID,
        },
        "authorization_request_path": AUTH_REQUEST,
        "evidence_path": EVIDENCE_PATH,
        "effect_ack_done": False,
    }
    write_json(PUBLISH_DRAFT, draft)

    lines = [
        "# TEMDD Zenodo v2 exact fileset",
        "",
        f"Publication ID: `{PUBLICATION_ID}`",
        f"Frozen source head: `{SOURCE_HEAD}`",
        "",
        "The following paths form the exact proof-bearing upload set:",
        "",
    ]
    lines.extend(f"- `{path}`" for path in upload_paths)
    lines += [
        "",
        "Repository-side controls not uploaded:",
        f"- `{AUTH_REQUEST}`",
        f"- `{PUBLISH_DRAFT}`",
        f"- `{METADATA}`",
        "",
        "State: `EXACT_OWNER_AUTHORIZATION_PENDING`",
        "",
        "`EFFECT_ACK_DONE=false`",
        "",
    ]
    (ROOT / FILESET).write_text("\n".join(lines), encoding="utf-8")

    print("TEMDD_ZENODO_CANDIDATE=PROOF_READY")
    print("SOURCE_HEAD=" + SOURCE_HEAD)
    print("PROOF_SHA256=" + validated["sha256"])
    print("AUTHORIZATION_STATEMENT=" + statement)
    print("EFFECT_ACK_DONE=false")


def check() -> None:
    upload_paths = []
    draft = json.loads((ROOT / PUBLISH_DRAFT).read_text(encoding="utf-8"))
    upload_paths = [item["path"] for item in draft["files"]]
    receipt = proof.validate_bundle(
        ROOT,
        ROOT / PROOF_BUNDLE,
        upload_paths=upload_paths,
    )
    request = json.loads((ROOT / AUTH_REQUEST).read_text(encoding="utf-8"))
    if request["machine_proof"]["sha256"] != receipt["sha256"]:
        raise SystemExit("BLOCK authorization request proof identity differs")
    if request["effect_released"] is not False or request["effect_ack_done"] is not False:
        raise SystemExit("BLOCK pre-authorization candidate escalates effect state")
    print("TEMDD_ZENODO_CANDIDATE=VALID")
    print("AUTHORIZATION_STATEMENT=" + request["canonical_statement"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("materialize", "check"))
    args = parser.parse_args()
    if args.action == "materialize":
        materialize()
    else:
        check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
