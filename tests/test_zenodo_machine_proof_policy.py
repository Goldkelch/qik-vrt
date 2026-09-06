#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import concurrent.futures
import copy
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from collections.abc import Callable, Mapping
from typing import Any
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_machine_proof as proof
from tools import qikvrt_zenodo_publish as publish

SOURCE_HEAD = "a" * 40
AUTHORIZATION_NONCE = "b" * 64
TEST_GITHUB_TOKEN = "g" * 32
TEST_REMOTE_RELATIVE = pathlib.Path(".git/test-remotes/owner/repository.git")
FIXTURE_PUBLICATION_ID = "fixture-publication-v2"
FIXTURE_AUTHORIZATION_ID = "fixture-zenodo-authorization-v2"


def blob(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def write(root: pathlib.Path, relative: str, data: bytes) -> pathlib.Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def bound(root: pathlib.Path, relative: str, **extra: object) -> dict[str, object]:
    data = (root / relative).read_bytes()
    return {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": blob(data),
        **extra,
    }


def identity(root: pathlib.Path, relative: str) -> dict[str, object]:
    data = (root / relative).read_bytes()
    return {
        "path": relative,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha": blob(data),
    }


def authorization_statement(
    authorization_id: str,
    publication_id: str,
    return_sha256: str,
    metadata_sha256: str,
    machine_proof_sha256: str,
) -> str:
    return (
        "AUTHORIZE_EXACT_UPLOAD "
        f"authorization_id={authorization_id} "
        f"publication_id={publication_id} "
        f"return_sha256={return_sha256} "
        f"metadata_sha256={metadata_sha256} "
        f"machine_proof_sha256={machine_proof_sha256}"
    )


def expected_consumption_ref(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
) -> str:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    authorization = json.loads(
        (root / manifest["owner_authorization"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    key = publish._authorization_consumption_key(
        authorization["repository"],
        authorization["authorization_id"],
        authorization["publication_id"],
        authorization["authorization_event"]["statement_sha256"],
    )
    return publish.CONSUMPTION_REF_PREFIX + key["value"]


class FakeGitHubGitData:
    def __init__(self) -> None:
        self.refs: dict[str, str] = {}
        self.tags: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.calls: list[tuple[str, str]] = []

    @staticmethod
    def ref_value(ref: str, tag_object: str) -> dict[str, Any]:
        return {
            "ref": ref,
            "object": {"sha": tag_object, "type": "tag"},
        }

    def __call__(
        self,
        method: str,
        path: str,
        token: str,
        *,
        payload: Mapping[str, Any] | None = None,
        accept: tuple[int, ...] = (200,),
    ) -> tuple[int, dict[str, Any]]:
        self.calls.append((method, path))
        if token != TEST_GITHUB_TOKEN:
            raise AssertionError("unexpected GitHub token")
        if method == "GET" and "/git/ref/" in path:
            ref = "refs/" + urllib.parse.unquote(path.split("/git/ref/", 1)[1])
            with self.lock:
                tag_object = self.refs.get(ref)
            return (
                (404, {})
                if tag_object is None
                else (200, self.ref_value(ref, tag_object))
            )
        if method == "POST" and path.endswith("/git/tags"):
            if payload is None:
                raise AssertionError("missing tag payload")
            digest = hashlib.sha1(  # noqa: S324 - fixture Git identity
                zenodo._json_bytes(payload)
            ).hexdigest()
            value = {
                "sha": digest,
                "tag": payload["tag"],
                "message": payload["message"],
                "object": {
                    "sha": payload["object"],
                    "type": payload["type"],
                },
                "tagger": copy.deepcopy(payload["tagger"]),
            }
            with self.lock:
                self.tags[digest] = value
            return 201, value
        if method == "GET" and "/git/tags/" in path:
            digest = path.rsplit("/", 1)[1]
            with self.lock:
                value = copy.deepcopy(self.tags.get(digest))
            return (404, {}) if value is None else (200, value)
        if method == "POST" and path.endswith("/git/refs"):
            if payload is None:
                raise AssertionError("missing ref payload")
            ref = payload["ref"]
            tag_object = payload["sha"]
            with self.lock:
                if ref in self.refs:
                    return 422, {"message": "Reference already exists"}
                self.refs[ref] = tag_object
            return 201, self.ref_value(ref, tag_object)
        raise AssertionError(f"unexpected GitHub API call: {method} {path}")


def rebind_fixture(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
    *,
    source_head: str | None = None,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    authorization_relative = manifest["owner_authorization"]["path"]
    authorization_path = root / authorization_relative
    authorization = json.loads(
        authorization_path.read_text(encoding="utf-8")
    )
    if source_head is not None:
        manifest["source_head"] = source_head
        authorization["source_head"] = source_head

    for item in manifest["files"]:
        item["git_blob_sha"] = blob((root / item["path"]).read_bytes())
    proof_relative = manifest["machine_proof"]["path"]
    manifest["machine_proof"]["git_blob_sha"] = blob(
        (root / proof_relative).read_bytes()
    )
    metadata_sha256 = hashlib.sha256(
        zenodo._json_bytes(manifest["metadata"])
    ).hexdigest()
    return_identity = identity(
        root,
        "proof/PREPUBLICATION_RETURN_RECEIPT.json",
    )
    machine_identity = identity(root, proof_relative)
    authorization["candidate_return_receipt"] = return_identity
    authorization["canonical_metadata_sha256"] = metadata_sha256
    authorization["uploads"] = [
        {
            "path": item["path"],
            "name": item["name"],
            "bytes": (root / item["path"]).stat().st_size,
            "sha256": hashlib.sha256(
                (root / item["path"]).read_bytes()
            ).hexdigest(),
            "git_blob_sha": item["git_blob_sha"],
        }
        for item in manifest["files"]
    ]
    authorization["machine_proof"] = machine_identity
    event = authorization["authorization_event"]
    event["candidate_return_receipt_sha256"] = return_identity["sha256"]
    exact_statement = authorization_statement(
        authorization["authorization_id"],
        authorization["publication_id"],
        return_identity["sha256"],
        metadata_sha256,
        machine_identity["sha256"],
    )
    event["exact_statement"] = exact_statement
    event["statement_sha256"] = hashlib.sha256(
        exact_statement.encode("utf-8")
    ).hexdigest()
    authorization_path.write_text(
        json.dumps(authorization, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["owner_authorization"] = identity(root, authorization_relative)
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def transition_matrix_identity(root: pathlib.Path) -> dict[str, object]:
    bound_identity = identity(root, "proof/CLAIM_MATRIX.json")
    return {
        "path": bound_identity["path"],
        "bytes": bound_identity["bytes"],
        "sha256": bound_identity["sha256"],
        "git_blob_sha1": bound_identity["git_blob_sha"],
    }


def kernel_identity(root: pathlib.Path, relative: str) -> dict[str, object]:
    data = (root / relative).read_bytes()
    return {
        "path": relative,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": blob(data),
    }


def persisted_kernel_evidence_identity(
    root: pathlib.Path,
    relative: str,
) -> dict[str, object]:
    data = (root / relative).read_bytes()
    return {
        "bytes": len(data),
        "git_blob_sha1": blob(data),
        "name": proof.CANONICAL_KERNEL_ARTIFACT_FILE_NAME,
        "persisted_path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def kernel_archive_artifact(
    root: pathlib.Path,
    relative: str,
    *,
    artifact_id: int,
    archive_label: bytes,
    created_at: str,
    expires_at: str,
) -> dict[str, object]:
    return {
        "archive_digest": "sha256:" + hashlib.sha256(archive_label).hexdigest(),
        "archive_size_bytes": len(archive_label),
        "created_at": created_at,
        "expires_at": expires_at,
        "file": persisted_kernel_evidence_identity(root, relative),
        "id": artifact_id,
        "name": proof.CANONICAL_KERNEL_ARTIFACT_NAME,
    }


def enable_canonical_kernel_receipt_v2(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
) -> dict[str, str]:
    branch = "publication/canonical-fixture-v2"
    h0_head = "1" * 40
    h0_tree = "2" * 40
    h1_head = "3" * 40
    h1_tree = "4" * 40
    h0_matrix_relative = "proof/CLAIM_MATRIX_H0_PENDING.json"
    h0_evidence_relative = "proof/KERNEL_EVIDENCE_H0.json"
    h1_evidence_relative = "proof/KERNEL_EVIDENCE_H1.json"
    h1_matrix_relative = "proof/CLAIM_MATRIX.json"
    h1_matrix_value = json.loads(
        (root / h1_matrix_relative).read_text(encoding="utf-8")
    )
    h1_matrix_value["proof_state"] = "KERNEL_VERIFIED"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    matrix_formal_claim = next(
        claim
        for claim in h1_matrix_value["claims"]
        if claim["classification"] == "FORMAL_PROVED"
    )
    second_statement = "The second fixture theorem is kernel checked."
    second_matrix_claim = copy.deepcopy(matrix_formal_claim)
    second_matrix_claim.update(
        {
            "claim_id": "C-FORMAL-SECOND",
            "proof_refs": ["Fixture.second_theorem"],
            "statement": second_statement,
        }
    )
    h1_matrix_value["claims"].append(second_matrix_claim)
    h1_matrix_value["claim_count"] = len(h1_matrix_value["claims"])
    bundle_formal_claim = next(
        claim
        for claim in bundle["claims"]
        if claim["classification"] == "FORMAL_PROVED"
    )
    second_bundle_claim = copy.deepcopy(bundle_formal_claim)
    second_bundle_claim.update(
        {
            "claim_id": "C-FORMAL-SECOND",
            "proof_refs": [
                "proof/KERNEL_RECEIPT.json#Fixture.second_theorem"
            ],
            "statement": second_statement,
        }
    )
    bundle["claims"].append(second_bundle_claim)
    write(
        root,
        h1_matrix_relative,
        (
            json.dumps(h1_matrix_value, sort_keys=True, indent=2) + "\n"
        ).encode(),
    )
    refresh_artifact(root, bundle, h1_matrix_relative, "CLAIM_MATRIX")
    bundle_path.write_text(
        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    formal_claim_ids = [
        claim["claim_id"]
        for claim in h1_matrix_value["claims"]
        if claim["classification"] == "FORMAL_PROVED"
    ]
    h0_matrix_value = copy.deepcopy(h1_matrix_value)
    h0_matrix_value["proof_state"] = "AWAITING_EXACT_HEAD_KERNEL_RECEIPT"
    for claim in h0_matrix_value["claims"]:
        if claim["claim_id"] in formal_claim_ids:
            claim["classification"] = "FORMAL_PENDING_KERNEL"
            claim["status"] = (
                "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_KERNEL_RECEIPT"
            )
    write(
        root,
        h0_matrix_relative,
        (
            json.dumps(h0_matrix_value, sort_keys=True, indent=2) + "\n"
        ).encode(),
    )
    persisted_h0_matrix = kernel_identity(root, h0_matrix_relative)
    h0_matrix = {
        **persisted_h0_matrix,
        "path": h1_matrix_relative,
    }
    h1_matrix = transition_matrix_identity(root)
    source = kernel_identity(root, "proof/SOURCE.txt")
    axioms = {
        "Fixture.theorem": [],
        "Fixture.second_theorem": [],
    }
    plan_relative = "proof/KERNEL_PROOF_PLAN.json"
    compiled_relative = "proof/CanonicalTemporalMemory.olean"
    write(root, plan_relative, b'{"fixture":"kernel-proof-plan"}\n')
    write(root, compiled_relative, b"fixture compiled object\n")
    plan = kernel_identity(root, plan_relative)
    compiled_object = kernel_identity(root, compiled_relative)
    project_prefix = pathlib.PurePosixPath("proof/kernel-project")
    entrypoint_name = "QIKVRTEffectAck.lean"
    entrypoint_local_relative = (project_prefix / entrypoint_name).as_posix()
    toolchain_name = "lean-toolchain"
    toolchain_local_relative = (project_prefix / toolchain_name).as_posix()
    toolchain_value = "leanprover/lean4:v4.19.0"
    write(root, entrypoint_local_relative, b"import Fixture\n")
    write(root, toolchain_local_relative, (toolchain_value + "\n").encode())
    entrypoint = {
        **kernel_identity(root, entrypoint_local_relative),
        "path": entrypoint_name,
    }
    lean_toolchain = {
        **kernel_identity(root, toolchain_local_relative),
        "path": toolchain_name,
        "value": toolchain_value,
    }
    receipt_toolchain = {
        "lean_toolchain": toolchain_value,
        "locked": True,
        "path": toolchain_local_relative,
        "sha256": lean_toolchain["sha256"],
    }
    exact_source_output = hashlib.sha256(b"").hexdigest()
    axiom_audit_output = hashlib.sha256(b"fixture axiom audit").hexdigest()
    evidence_runtime = {
        "cache_replaces_kernel_verification": False,
        "dynamic_axiom_audit": {
            "argv": ["lake", "env", "lean", ".lake/build/FixtureAudit.lean"],
            "exit_code": 0,
            "output_sha256": axiom_audit_output,
        },
        "exact_source_kernel_check": {
            "argv": ["lake", "env", "lean", entrypoint_name],
            "exit_code": 0,
            "output_sha256": exact_source_output,
        },
        "fresh_project_build_required_before_object_binding": True,
    }
    receipt_runtime = {
        "dynamic_axiom_audit_output_sha256": axiom_audit_output,
        "exact_source_kernel_check_exit_code": 0,
        "exact_source_kernel_check_output_sha256": exact_source_output,
    }
    proof_refs_by_claim = {
        claim["claim_id"]: claim["proof_refs"]
        for claim in h1_matrix_value["claims"]
        if claim["claim_id"] in formal_claim_ids
    }
    formal_bindings = []
    for claim_id in formal_claim_ids:
        proof_refs = proof_refs_by_claim[claim_id]
        formal_bindings.append(
            {
                "axioms_by_theorem": {
                    theorem: axioms[theorem] for theorem in proof_refs
                },
                "claim_id": claim_id,
                "compiled_object_sha256": compiled_object["sha256"],
                "proof_refs": proof_refs,
                "source_sha256": source["sha256"],
            }
        )

    def evidence(
        *,
        head: str,
        matrix: dict[str, object],
        run_id: int,
    ) -> dict[str, Any]:
        return {
            "schema": proof.CANONICAL_KERNEL_EVIDENCE_SCHEMA,
            "state": "KERNEL_VERIFIED",
            "publication_id": FIXTURE_PUBLICATION_ID,
            "claim_matrix": matrix,
            "source": source,
            "axioms_by_theorem": axioms,
            "plan": plan,
            "compiled_object": compiled_object,
            "entrypoint": entrypoint,
            "lean_toolchain": lean_toolchain,
            "runtime": evidence_runtime,
            "formal_bindings": formal_bindings,
            "formal_claim_count": len(formal_claim_ids),
            "theorem_count": len(axioms),
            "workflow": {
                "repository": "Goldkelch/qik-vrt",
                "sha": head,
                "ref": "refs/heads/" + branch,
                "event": "push",
                "run_id": str(run_id),
                "run_attempt": "1",
            },
        }

    write(
        root,
        h0_evidence_relative,
        (
            json.dumps(
                evidence(head=h0_head, matrix=h0_matrix, run_id=100),
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode(),
    )
    write(
        root,
        h1_evidence_relative,
        (
            json.dumps(
                evidence(head=h1_head, matrix=h1_matrix, run_id=101),
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode(),
    )

    def candidate(head: str, tree: str) -> dict[str, object]:
        return {
            "branch": branch,
            "head": head,
            "repository": "Goldkelch/qik-vrt",
            "tree": tree,
        }

    def workflow(head: str, run_id: int) -> dict[str, object]:
        return {
            "conclusion": "success",
            "event": "push",
            "exact_head_bound": True,
            "run_attempt": 1,
            "run_id": run_id,
            "sha": head,
        }

    receipt = {
        "schema": proof.CANONICAL_KERNEL_RECEIPT_SCHEMA,
        "state": "KERNEL_VERIFIED",
        "scope_id": FIXTURE_PUBLICATION_ID,
        "receipt_stage": proof.CANONICAL_RECEIPT_STAGE,
        "verification_stage": proof.CANONICAL_VERIFICATION_STAGE,
        "bootstrap_h0": {
            "role": proof.CANONICAL_BOOTSTRAP_ROLE,
            "verified_candidate": candidate(h0_head, h0_tree),
            "claim_matrix": h0_matrix,
            "persisted_claim_matrix": persisted_h0_matrix,
            "workflow": workflow(h0_head, 100),
            "artifact": kernel_archive_artifact(
                root,
                h0_evidence_relative,
                artifact_id=1000,
                archive_label=b"H0 archive fixture",
                created_at="2026-07-30T17:00:09Z",
                expires_at="2026-08-29T17:00:09Z",
            ),
        },
        "verified_candidate": candidate(h1_head, h1_tree),
        "workflow": workflow(h1_head, 101),
        "artifact": kernel_archive_artifact(
            root,
            h1_evidence_relative,
            artifact_id=1001,
            archive_label=b"H1 archive fixture",
            created_at="2026-07-30T18:46:39Z",
            expires_at="2026-08-29T18:46:39Z",
        ),
        "claim_transition": {
            "allowed_changes": {
                "claim_ids": formal_claim_ids,
                "classification": {
                    "from": "FORMAL_PENDING_KERNEL",
                    "to": "FORMAL_PROVED",
                },
                "matrix_proof_state": {
                    "from": "AWAITING_EXACT_HEAD_KERNEL_RECEIPT",
                    "to": "KERNEL_VERIFIED",
                },
                "status": {
                    "from": (
                        "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_"
                        "KERNEL_RECEIPT"
                    ),
                    "to": "KERNEL_VERIFIED",
                },
            },
            "proof_refs_and_statements_unchanged": True,
            "source_claim_matrix": h0_matrix,
            "target_claim_matrix": h1_matrix,
            "target_exact_head_confirmation_required": False,
        },
        "source": source,
        "axioms_by_theorem": axioms,
        "compiled_object": compiled_object,
        "entrypoint": entrypoint,
        "formal_claim_count": len(formal_claim_ids),
        "plan": plan,
        "runtime": receipt_runtime,
        "theorem_count": len(axioms),
        "theorems": list(axioms),
        "toolchain": receipt_toolchain,
        "materialization_boundary": {
            "stage": "H2",
            "required_relation": "SINGLE_PARENT_SUCCESSOR",
            "predecessor_head": h1_head,
            "containing_head_binding": "EXTERNAL_TO_RECEIPT",
            "containing_tree_binding": "EXTERNAL_TO_RECEIPT",
            "self_inclusion_claimed": False,
        },
    }

    def replace(value: dict[str, Any]) -> None:
        value.clear()
        value.update(receipt)

    mutate_kernel_receipt(root, bundle_path, replace)
    return {
        "h0_evidence": h0_evidence_relative,
        "h0_head": h0_head,
        "h1_evidence": h1_evidence_relative,
        "h1_head": h1_head,
    }


def mutate_canonical_kernel_evidence(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
    stage: str,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    relative = (
        "proof/KERNEL_EVIDENCE_H0.json"
        if stage == "H0"
        else "proof/KERNEL_EVIDENCE_H1.json"
    )
    path = root / relative
    evidence = json.loads(path.read_text(encoding="utf-8"))
    mutation(evidence)
    path.write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    def rebind(receipt: dict[str, Any]) -> None:
        artifact = (
            receipt["bootstrap_h0"]["artifact"]
            if stage == "H0"
            else receipt["artifact"]
        )
        artifact["file"] = persisted_kernel_evidence_identity(root, relative)

    mutate_kernel_receipt(root, bundle_path, rebind)


def mutate_canonical_h0_claim_matrix(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    receipt_path = root / "proof/KERNEL_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    persisted_relative = receipt["bootstrap_h0"]["persisted_claim_matrix"][
        "path"
    ]
    persisted_path = root / persisted_relative
    matrix = json.loads(persisted_path.read_text(encoding="utf-8"))
    mutation(matrix)
    persisted_path.write_text(
        json.dumps(matrix, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    persisted_identity = kernel_identity(root, persisted_relative)
    historical_identity = {
        **persisted_identity,
        "path": receipt["claim_transition"]["source_claim_matrix"]["path"],
    }
    receipt["bootstrap_h0"]["persisted_claim_matrix"] = persisted_identity
    receipt["bootstrap_h0"]["claim_matrix"] = historical_identity
    receipt["claim_transition"]["source_claim_matrix"] = historical_identity

    evidence_relative = receipt["bootstrap_h0"]["artifact"]["file"][
        "persisted_path"
    ]
    evidence_path = root / evidence_relative
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["claim_matrix"] = historical_identity
    evidence_path.write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    receipt["bootstrap_h0"]["artifact"][
        "file"
    ] = persisted_kernel_evidence_identity(root, evidence_relative)

    def replace(value: dict[str, Any]) -> None:
        value.clear()
        value.update(receipt)

    mutate_kernel_receipt(root, bundle_path, replace)


def mutate_authorization(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative = manifest["owner_authorization"]["path"]
    authorization_path = root / relative
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    mutation(authorization)
    authorization_path.write_text(
        json.dumps(authorization, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["owner_authorization"] = identity(root, relative)
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def mutate_kernel_receipt(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    receipt_path = root / "proof/KERNEL_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    mutation(receipt)
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    for index, artifact in enumerate(bundle["artifacts"]):
        if artifact["path"] == "proof/KERNEL_RECEIPT.json":
            bundle["artifacts"][index] = bound(
                root,
                "proof/KERNEL_RECEIPT.json",
                kind="KERNEL_RECEIPT",
            )
            break
    else:
        raise AssertionError("fixture lacks its bound kernel receipt")
    bundle_path.write_text(
        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def refresh_artifact(
    root: pathlib.Path,
    bundle: dict[str, Any],
    relative: str,
    kind: str,
) -> None:
    replacement = bound(root, relative, kind=kind)
    for index, artifact in enumerate(bundle["artifacts"]):
        if artifact["path"] == relative:
            bundle["artifacts"][index] = replacement
            return
    bundle["artifacts"].append(replacement)


def mutate_claim_matrix(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    relative = "proof/CLAIM_MATRIX.json"
    matrix_path = root / relative
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    mutation(matrix)
    matrix_path.write_text(
        json.dumps(matrix, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    refresh_artifact(root, bundle, relative, "CLAIM_MATRIX")
    bundle_path.write_text(
        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def mutate_return_receipt(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    relative = "proof/PREPUBLICATION_RETURN_RECEIPT.json"
    receipt_path = root / relative
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    mutation(receipt)
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    refresh_artifact(root, bundle, relative, "RETURN_RECEIPT")
    bundle_path.write_text(
        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def enable_valid_changed_return(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
) -> None:
    original_relative = "proof/ORIGINAL.md"
    notice_relative = "proof/CHANGE_NOTICE.md"
    reason = "The physical integration claim was narrowed to an explicit open boundary."
    write(root, original_relative, b"# Original\n\nPhysical integration is complete.\n")
    write(
        root,
        notice_relative,
        (
            "# Change Notice\n\n"
            f"C-OPEN: {reason}\n"
        ).encode(),
    )
    original_identity = bound(
        root,
        original_relative,
        bytes=(root / original_relative).stat().st_size,
    )
    candidate_identity = bound(
        root,
        "docs/candidate.md",
        bytes=(root / "docs/candidate.md").stat().st_size,
    )

    def mutate(receipt: dict[str, Any]) -> None:
        receipt["content_changed"] = True
        receipt["original_files"] = [original_identity]
        receipt["changed_claim_ids"] = ["C-OPEN"]
        receipt["change_reasons"] = [
            {
                "claim_id": "C-OPEN",
                "reason": reason,
                "original_sha256": original_identity["sha256"],
                "corrected_sha256": candidate_identity["sha256"],
                "exact_candidate_path": "docs/candidate.md",
            }
        ]
        receipt["change_notice_path"] = notice_relative
        receipt["return"]["visible_change_notice_returned"] = True

    mutate_return_receipt(root, bundle_path, mutate)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["prepublication_return"].update(
        {
            "content_changed": True,
            "change_notice_path": notice_relative,
        }
    )
    refresh_artifact(root, bundle, original_relative, "SOURCE")
    refresh_artifact(root, bundle, notice_relative, "CHANGE_NOTICE")
    bundle_path.write_text(
        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def run_git(root: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def materialize_git_history(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
) -> tuple[str, str]:
    run_git(root, "init", "--quiet")
    run_git(root, "config", "gc.auto", "0")
    run_git(root, "config", "gc.autoDetach", "false")
    run_git(root, "config", "user.name", "Fixture Owner")
    run_git(root, "config", "user.email", "fixture@example.invalid")
    run_git(root, "commit", "--quiet", "--allow-empty", "-m", "fixture root")
    run_git(root, "add", "--", "policy", "docs", "proof")
    run_git(root, "commit", "--quiet", "-m", "freeze returned candidate")
    source_head = run_git(root, "rev-parse", "HEAD")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    authorization_relative = manifest["owner_authorization"]["path"]
    authorization_path = root / authorization_relative
    self_contained_authorization = authorization_path.is_file()
    if not self_contained_authorization:
        raise AssertionError("fixture lacks its owner authorization")
    rebind_fixture(root, manifest_path, source_head=source_head)
    run_git(root, "add", "--all")
    run_git(root, "commit", "--quiet", "-m", "bind execution authorization")
    execution_head = run_git(root, "rev-parse", "HEAD")
    remote = root / TEST_REMOTE_RELATIVE
    remote.parent.mkdir(parents=True, exist_ok=True)
    run_git(root, "init", "--quiet", "--bare", str(remote))
    run_git(root, "--git-dir", str(remote), "config", "gc.auto", "0")
    run_git(root, "--git-dir", str(remote), "config", "gc.autoDetach", "false")
    run_git(root, "--git-dir", str(remote), "config", "receive.autogc", "false")
    run_git(root, "--git-dir", str(remote), "symbolic-ref", "HEAD", "refs/heads/main")
    run_git(root, "remote", "add", "origin", str(remote))
    run_git(
        root,
        "push",
        "--quiet",
        "--set-upstream",
        "origin",
        f"{execution_head}:refs/heads/main",
    )
    run_git(
        root,
        "remote",
        "set-url",
        "--push",
        "origin",
        "https://github.com/Goldkelch/qik-vrt.git",
    )
    return source_head, execution_head


class MachineProofBeforeZenodoTests(unittest.TestCase):
    maxDiff = None

    def fixture(self, root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        contract_paths = (
            proof.POLICY_PATH,
            proof.BUNDLE_SCHEMA_PATH,
            proof.RETURN_SCHEMA_PATH,
            proof.LEGACY_POLICY_PATH,
            proof.LEGACY_BUNDLE_SCHEMA_PATH,
            proof.LEGACY_RETURN_SCHEMA_PATH,
        )
        for relative in contract_paths:
            contract_path = write(
                root,
                relative,
                (ROOT / relative).read_bytes(),
            )
            self.assertTrue(contract_path.is_file())
        primary = write(
            root,
            "docs/candidate.md",
            b"# Candidate\n\nAll claims are classified and scope bounded.\n",
        )
        kernel = write(
            root,
            "proof/KERNEL_RECEIPT.json",
            (
                json.dumps(
                    {
                        "schema": "qikvrt_fixture_kernel_receipt_v2",
                        "scope_id": FIXTURE_PUBLICATION_ID,
                        "state": "KERNEL_VERIFIED",
                        "theorems": ["Fixture.theorem"],
                        "workflow": {
                            "conclusion": "success",
                            "exact_head_bound": True,
                        },
                    },
                    sort_keys=True,
                )
                + "\n"
            ).encode(),
        )
        evidence = write(
            root,
            "proof/EVIDENCE.json",
            b'{"id":"observation","state":"EVIDENCED"}\n',
        )
        source = write(
            root,
            "proof/SOURCE.txt",
            b"Primary source fixture identifiers:\nlean-source\nline-1\n",
        )

        candidate_identity = bound(
            root,
            "docs/candidate.md",
            bytes=primary.stat().st_size,
            name="candidate.md",
            role="PRIMARY",
        )
        return_receipt_value = {
            "_license": {
                "classification": "machine_readable_prepublication_return_receipt",
                "copyright": "Copyright 2026 Ingolf Lohmann",
                "license": "CC-BY-NC-ND-4.0",
                "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                "rights_holder": "Ingolf Lohmann",
            },
            "schema": proof.RETURN_SCHEMA,
            "publication_id": FIXTURE_PUBLICATION_ID,
            "content_changed": False,
            "original_files": [],
            "candidate_files": [
                {
                    key: candidate_identity[key]
                    for key in ("path", "bytes", "sha256", "git_blob_sha1")
                }
            ],
            "changed_claim_ids": [],
            "change_reasons": [],
            "change_notice_path": None,
            "return": {
                "candidate_returned_to_owner": True,
                "owner_name": "Ingolf Lohmann",
                "owner_type": "NATURAL_PERSON",
                "return_channel": "ChatGPT conversation",
                "returned_at": "2026-07-28T09:30:00Z",
                "visible_change_notice_returned": False,
            },
        }
        return_receipt = write(
            root,
            "proof/PREPUBLICATION_RETURN_RECEIPT.json",
            (json.dumps(return_receipt_value, sort_keys=True, indent=2) + "\n").encode(),
        )

        claims = [
            {
                "claim_id": "C-FORMAL",
                "statement": "The abstract fixture theorem is checked.",
                "classification": "FORMAL_PROVED",
                "status": "PROVED",
                "publication_wording": "ESTABLISHED_WITHIN_SCOPE",
                "scope": "fixture model",
                "proof_refs": ["proof/KERNEL_RECEIPT.json#Fixture.theorem"],
                "evidence_refs": [],
                "source_refs": ["proof/SOURCE.txt#lean-source"],
            },
            {
                "claim_id": "C-EMPIRICAL",
                "statement": "The fixture observation is recorded.",
                "classification": "EMPIRICALLY_EVIDENCED",
                "status": "EVIDENCED",
                "publication_wording": "EMPIRICALLY_SUPPORTED",
                "scope": "fixture observation",
                "proof_refs": [],
                "evidence_refs": ["proof/EVIDENCE.json#observation"],
                "source_refs": [],
            },
            {
                "claim_id": "C-SOURCE",
                "statement": "The source contains the cited fixture statement.",
                "classification": "SOURCE_BOUND",
                "status": "BOUND",
                "publication_wording": "SOURCE_ATTRIBUTED",
                "scope": "exact source bytes",
                "proof_refs": [],
                "evidence_refs": [],
                "source_refs": ["proof/SOURCE.txt#line-1"],
            },
            {
                "claim_id": "C-NORMATIVE",
                "statement": "Future uploads shall remain fail closed.",
                "classification": "NORMATIVE",
                "status": "DECLARED",
                "publication_wording": "NORMATIVE_DECLARATION",
                "scope": "publication policy",
                "proof_refs": [],
                "evidence_refs": [],
                "source_refs": [],
            },
            {
                "claim_id": "C-INTERPRETATIVE",
                "statement": "The fixture illustrates responsible publication.",
                "classification": "INTERPRETATIVE",
                "status": "DECLARED",
                "publication_wording": "INTERPRETATIVE_DECLARATION",
                "scope": "authorial interpretation",
                "proof_refs": [],
                "evidence_refs": [],
                "source_refs": [],
            },
            {
                "claim_id": "C-OPEN",
                "statement": "A physical integration remains open.",
                "classification": "OPEN",
                "status": "OPEN",
                "publication_wording": "EXPLICITLY_OPEN",
                "scope": "unexecuted physical integration",
                "proof_refs": [],
                "evidence_refs": [],
                "source_refs": [],
            },
        ]
        matrix_claims = [
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "classification": claim["classification"],
                "status": (
                    "KERNEL_VERIFIED"
                    if claim["classification"] == "FORMAL_PROVED"
                    else claim["status"]
                ),
                "boundary": claim["scope"],
                "proof_refs": [
                    reference.split("#", 1)[1]
                    for reference in claim["proof_refs"]
                ],
                "sources": [
                    reference.split("#", 1)[1]
                    for reference in (
                        *claim["evidence_refs"],
                        *claim["source_refs"],
                    )
                ],
            }
            for claim in claims
        ]
        claim_matrix = write(
            root,
            "proof/CLAIM_MATRIX.json",
            (
                json.dumps(
                    {
                        "schema": "qikvrt_fixture_claim_matrix_v2",
                        "publication_id": FIXTURE_PUBLICATION_ID,
                        "claim_count": len(matrix_claims),
                        "claims": matrix_claims,
                    },
                    sort_keys=True,
                    indent=2,
                )
                + "\n"
            ).encode(),
        )
        artifact_specs = [
            (claim_matrix, "CLAIM_MATRIX"),
            (kernel, "KERNEL_RECEIPT"),
            (evidence, "EVIDENCE"),
            (source, "SOURCE"),
            (return_receipt, "RETURN_RECEIPT"),
        ]
        artifacts = [
            bound(root, path.relative_to(root).as_posix(), kind=kind)
            for path, kind in artifact_specs
        ]
        bundle_value = {
            "_license": {
                "classification": "machine_readable_proof_bundle",
                "copyright": "Copyright 2026 Ingolf Lohmann",
                "license": "CC-BY-NC-ND-4.0",
                "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                "rights_holder": "Ingolf Lohmann",
            },
            "schema": proof.BUNDLE_SCHEMA,
            "policy": {
                "id": proof.POLICY_ID,
                "path": proof.POLICY_PATH,
                "version": proof.POLICY_VERSION,
                "sha256": proof.POLICY_SHA256,
                "git_blob_sha1": proof.POLICY_GIT_BLOB_SHA1,
            },
            "publication_id": FIXTURE_PUBLICATION_ID,
            "candidate": {
                "primary_document_path": "docs/candidate.md",
                "files": [candidate_identity],
            },
            "claims": claims,
            "artifacts": artifacts,
            "prepublication_return": {
                "content_changed": False,
                "candidate_returned_to_owner": True,
                "receipt_path": "proof/PREPUBLICATION_RETURN_RECEIPT.json",
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
        bundle_path = write(
            root,
            "proof/MACHINE_PROOF_BUNDLE.json",
            (json.dumps(bundle_value, sort_keys=True, indent=2) + "\n").encode(),
        )

        upload_paths = [
            "docs/candidate.md",
            "proof/CLAIM_MATRIX.json",
            "proof/KERNEL_RECEIPT.json",
            "proof/EVIDENCE.json",
            "proof/SOURCE.txt",
            "proof/PREPUBLICATION_RETURN_RECEIPT.json",
            "proof/MACHINE_PROOF_BUNDLE.json",
        ]
        metadata = {
            "title": "Machine-proved fixture",
            "upload_type": "publication",
            "publication_type": "technicalnote",
            "description": "Proof-bearing fixture",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "version": "2.0.0",
            "access_right": "open",
            "license": "cc-by-nc-nd-4.0",
            "prereserve_doi": True,
        }
        files = [
            {
                "path": relative,
                "name": pathlib.PurePosixPath(relative).name,
                "git_blob_sha": blob((root / relative).read_bytes()),
            }
            for relative in upload_paths
        ]
        evidence_path = "release/fixture/zenodo-publication.json"
        return_identity = identity(
            root,
            "proof/PREPUBLICATION_RETURN_RECEIPT.json",
        )
        machine_identity = identity(
            root,
            "proof/MACHINE_PROOF_BUNDLE.json",
        )
        metadata_sha256 = hashlib.sha256(
            zenodo._json_bytes(metadata)
        ).hexdigest()
        exact_statement = authorization_statement(
            FIXTURE_AUTHORIZATION_ID,
            FIXTURE_PUBLICATION_ID,
            return_identity["sha256"],
            metadata_sha256,
            machine_identity["sha256"],
        )
        authorization_value = {
            "_license": {
                "classification": "owner_effect_authorization",
                "copyright": "Copyright 2026 Ingolf Lohmann",
                "license": "CC-BY-NC-ND-4.0",
                "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                "rights_holder": "Ingolf Lohmann",
            },
            "schema": publish.OWNER_AUTHORIZATION_SCHEMA,
            "authorization_id": FIXTURE_AUTHORIZATION_ID,
            "nonce": AUTHORIZATION_NONCE,
            "single_use": True,
            "single_use_scope": publish.SINGLE_USE_SCOPE,
            "principal": {
                "name": "Ingolf Lohmann",
                "type": "NATURAL_PERSON",
            },
            "publication_id": FIXTURE_PUBLICATION_ID,
            "repository": "Goldkelch/qik-vrt",
            "source_head": SOURCE_HEAD,
            "candidate_return_receipt": return_identity,
            "canonical_metadata_sha256": metadata_sha256,
            "uploads": [
                {
                    "path": item["path"],
                    "name": item["name"],
                    "bytes": (root / item["path"]).stat().st_size,
                    "sha256": hashlib.sha256(
                        (root / item["path"]).read_bytes()
                    ).hexdigest(),
                    "git_blob_sha": item["git_blob_sha"],
                }
                for item in files
            ],
            "machine_proof": machine_identity,
            "authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS),
            "publication_evidence_path": evidence_path,
            "authorization_event": {
                "channel": "ChatGPT conversation",
                "authorized_at": "2026-07-30T18:00:00+02:00",
                "decision": "AUTHORIZE_EXACT_UPLOAD",
                "exact_statement": exact_statement,
                "statement_sha256": hashlib.sha256(
                    exact_statement.encode("utf-8")
                ).hexdigest(),
                "principal": {
                    "name": "Ingolf Lohmann",
                    "type": "NATURAL_PERSON",
                },
                "candidate_return_receipt_sha256": return_identity["sha256"],
            },
        }
        write(
            root,
            "release/fixture/OWNER_ZENODO_AUTHORIZATION.json",
            (
                json.dumps(authorization_value, sort_keys=True, indent=2) + "\n"
            ).encode(),
        )
        manifest = {
            "schema": publish.SCHEMA_V2,
            "state": "publish",
            "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
            "repository": "Goldkelch/qik-vrt",
            "source_head": SOURCE_HEAD,
            "metadata": metadata,
            "files": files,
            "machine_proof": {
                "path": "proof/MACHINE_PROOF_BUNDLE.json",
                "git_blob_sha": blob(bundle_path.read_bytes()),
                "policy_id": proof.POLICY_ID,
            },
            "owner_authorization": {
                **identity(
                    root, "release/fixture/OWNER_ZENODO_AUTHORIZATION.json"
                ),
            },
            "evidence_path": evidence_path,
        }
        manifest_path = write(
            root,
            "release/fixture/publish-request.json",
            (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(),
        )
        return bundle_path, manifest_path

    def assert_publish_blocked_before_lock(
        self,
        root: pathlib.Path,
        manifest_path: pathlib.Path,
        execution_head: str,
        error: str,
        *,
        github_sha: str | None = None,
    ) -> None:
        expected_ref = expected_consumption_ref(root, manifest_path)
        with mock.patch.dict(
            os.environ,
            {
                "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                "GITHUB_SHA": github_sha or execution_head,
                publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
            },
            clear=True,
        ):
            with mock.patch.object(zenodo, "ZenodoClient") as client:
                with self.assertRaisesRegex(zenodo.ZenodoError, error):
                    publish.publish(manifest_path, root)
                client.assert_not_called()
        self.assertFalse(
            (root / "release/fixture/zenodo-publication.json").exists()
        )
        self.assertEqual(
            run_git(
                root,
                "ls-remote",
                "--refs",
                "origin",
                expected_ref,
            ),
            "",
        )

    def test_complete_proof_bundle_and_v2_manifest_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, manifest_path = self.fixture(root)
            receipt = proof.validate_bundle(
                root,
                bundle_path,
                upload_paths=[
                    item["path"]
                    for item in json.loads(manifest_path.read_text())["files"]
                ],
            )
            self.assertEqual(
                receipt["schema"],
                "qikvrt_zenodo_machine_proof_bundle_v2",
            )
            self.assertEqual(
                json.loads(
                    (
                        root / "proof/PREPUBLICATION_RETURN_RECEIPT.json"
                    ).read_text(encoding="utf-8")
                )["schema"],
                "qikvrt_prepublication_return_receipt_v2",
            )
            self.assertTrue(receipt["machine_proof_complete"])
            self.assertEqual(receipt["claim_count"], 6)
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"}):
                manifest = publish.load_manifest(manifest_path, root)
            self.assertEqual(manifest["schema"], publish.SCHEMA_V2)
            self.assertTrue(manifest["machine_proof"]["machine_proof_complete"])
            authorization = manifest["owner_authorization"]
            self.assertEqual(
                authorization["principal"],
                {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
            )
            self.assertEqual(authorization["source_head"], SOURCE_HEAD)
            self.assertTrue(authorization["single_use"])
            self.assertEqual(
                authorization["single_use_scope"],
                publish.SINGLE_USE_SCOPE,
            )
            self.assertEqual(
                authorization["remote_consumption_ref"],
                publish.CONSUMPTION_REF_PREFIX
                + authorization["consumption_key"]["value"],
            )
            self.assertEqual(
                authorization["attestation_scope"],
                "PLATFORM_REPOSITORY_BOUND",
            )
            self.assertEqual(
                authorization["principal_authentication"],
                "NOT_CRYPTOGRAPHICALLY_VERIFIED",
            )
            self.assertEqual(
                authorization["nonce_digest"],
                {
                    "algorithm": "SHA-256",
                    "value": hashlib.sha256(
                        AUTHORIZATION_NONCE.encode("ascii")
                    ).hexdigest(),
                },
            )
            self.assertNotIn("nonce", authorization)
            self.assertEqual(
                authorization["authorization_event"]["decision"],
                "AUTHORIZE_EXACT_UPLOAD",
            )
            self.assertTrue(
                authorization["authorization_event"]["exact_statement"].startswith(
                    "AUTHORIZE_EXACT_UPLOAD authorization_id="
                )
            )
            self.assertEqual(authorization["upload_count"], 7)
            self.assertNotIn(
                authorization["path"],
                {entry["path"] for entry in manifest["files"]},
            )

    def test_consumption_key_is_decision_bound_not_nonce_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY},
                clear=True,
            ):
                before = publish.load_manifest(manifest_path, root)[
                    "owner_authorization"
                ]
            mutate_authorization(
                root,
                manifest_path,
                lambda value: value.update({"nonce": "c" * 64}),
            )
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY},
                clear=True,
            ):
                after = publish.load_manifest(manifest_path, root)[
                    "owner_authorization"
                ]
            self.assertNotEqual(before["nonce_digest"], after["nonce_digest"])
            self.assertEqual(before["consumption_key"], after["consumption_key"])
            self.assertEqual(
                before["remote_consumption_ref"],
                after["remote_consumption_ref"],
            )

    def test_origin_is_exactly_pinned_against_host_and_path_spoofing(self) -> None:
        accepted = (
            "https://github.com/Goldkelch/qik-vrt",
            "https://github.com/Goldkelch/qik-vrt.git",
            "git@github.com:Goldkelch/qik-vrt.git",
            "ssh://git@github.com/Goldkelch/qik-vrt.git",
        )
        for origin in accepted:
            with self.subTest(origin=origin):
                self.assertEqual(
                    publish._origin_repository_identity(origin),
                    publish.PRODUCTION_REPOSITORY,
                )
        rejected = (
            "https://github.com.evil/Goldkelch/qik-vrt.git",
            "https://github.com/other/qik-vrt.git",
            "https://github.com/extra/Goldkelch/qik-vrt.git",
            "https://token@github.com/Goldkelch/qik-vrt.git",
            "https://github.com:444/Goldkelch/qik-vrt.git",
            "ssh://git@github.com.evil/Goldkelch/qik-vrt.git",
            "git@github.com:Goldkelch/qik-vrt.git/extra",
            "file:///tmp/Goldkelch/qik-vrt.git",
        )
        for origin in rejected:
            with self.subTest(origin=origin):
                with self.assertRaises(zenodo.ZenodoError):
                    publish._origin_repository_identity(origin)

    def test_git_subprocess_receives_no_workflow_secret(self) -> None:
        result = mock.Mock(returncode=0, stdout="ok\n", stderr="")
        with mock.patch.dict(
            os.environ,
            {
                "PATH": os.environ.get("PATH", ""),
                publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
                "UNRELATED_SECRET": "do-not-inherit",
            },
            clear=True,
        ), mock.patch.object(subprocess, "run", return_value=result) as runner:
            publish._git(pathlib.Path.cwd(), "status", "--porcelain")
        child_environment = runner.call_args.kwargs["env"]
        self.assertNotIn(publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE, child_environment)
        self.assertNotIn(zenodo.TOKEN_ENVIRONMENT_VARIABLE, child_environment)
        self.assertNotIn("UNRELATED_SECRET", child_environment)
        self.assertNotIn(TEST_GITHUB_TOKEN, child_environment.values())
        self.assertNotIn("z" * 32, child_environment.values())

    def test_github_and_zenodo_tokens_must_be_distinct(self) -> None:
        shared = "s" * 32
        with mock.patch.dict(
            os.environ,
            {
                publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: shared,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: shared,
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "must be distinct capabilities",
            ):
                publish._validated_network_secrets()

    def test_active_v2_policy_binds_exact_schema_contract_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            receipt = proof.validate_bundle(root, bundle_path)
            policy = json.loads(
                (root / proof.POLICY_PATH).read_text(encoding="utf-8")
            )
            self.assertEqual(
                receipt["policy"]["schema_contracts"],
                policy["schema_contracts"],
            )
            for name, schema_name in (
                ("machine_proof_bundle", proof.BUNDLE_SCHEMA),
                ("prepublication_return_receipt", proof.RETURN_SCHEMA),
            ):
                contract = policy["schema_contracts"][name]
                schema_path = root / contract["path"]
                schema_raw = schema_path.read_bytes()
                self.assertEqual(
                    hashlib.sha256(schema_raw).hexdigest(),
                    contract["sha256"],
                )
                self.assertEqual(blob(schema_raw), contract["git_blob_sha1"])
                schema = json.loads(schema_raw.decode("utf-8"))
                self.assertEqual(
                    schema["properties"]["schema"]["const"],
                    schema_name,
                )

        for name, relative in (
            ("bundle", proof.BUNDLE_SCHEMA_PATH),
            ("return", proof.RETURN_SCHEMA_PATH),
        ):
            with self.subTest(schema=name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    schema_path = root / relative
                    schema_path.write_bytes(schema_path.read_bytes() + b" ")
                    with self.assertRaisesRegex(
                        proof.ProofGateError,
                        "exact byte identity differs",
                    ):
                        proof.validate_bundle(root, bundle_path)

    def test_reference_fragments_must_exist_in_bound_artifacts(self) -> None:
        cases = (
            (1, "evidence_refs", "proof/EVIDENCE.json#missing-observation"),
            (2, "source_refs", "proof/SOURCE.txt#missing-line"),
        )
        for claim_index, key, replacement in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                    bundle["claims"][claim_index][key] = [replacement]
                    bundle_path.write_text(
                        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        proof.ProofGateError,
                        "unresolved exact identifier fragment",
                    ):
                        proof.validate_bundle(root, bundle_path)

    def test_bundle_and_return_receipt_licenses_are_exact_v2_contracts(
        self,
    ) -> None:
        bundle_cases = (
            (
                "classification",
                lambda license_value: license_value.update(
                    {"classification": "machine_readable_proof_bundle_v1"}
                ),
                "classification differs from the exact v2 license contract",
            ),
            (
                "rights holder",
                lambda license_value: license_value.update(
                    {"rights_holder": "Someone Else"}
                ),
                "rights_holder differs from the exact v2 license contract",
            ),
            (
                "unknown key",
                lambda license_value: license_value.update({"unbound": True}),
                "invalid machine proof bundle._license keys",
            ),
        )
        for name, mutation, error in bundle_cases:
            with self.subTest(document="bundle", field=name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    bundle = json.loads(
                        bundle_path.read_text(encoding="utf-8")
                    )
                    mutation(bundle["_license"])
                    bundle_path.write_text(
                        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

        return_cases = (
            (
                "license",
                lambda license_value: license_value.update(
                    {"license": "CC-BY-4.0"}
                ),
                "license differs from the exact v2 license contract",
            ),
            (
                "missing rights holder",
                lambda license_value: license_value.pop("rights_holder"),
                "invalid prepublication return receipt._license keys",
            ),
        )
        for name, mutation, error in return_cases:
            with self.subTest(document="return receipt", field=name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    mutate_return_receipt(
                        root,
                        bundle_path,
                        lambda receipt: mutation(receipt["_license"]),
                    )
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_publication_id_colon_is_rejected_by_exact_v2_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["publication_id"] = "fixture:publication-v2"
            bundle_path.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "must match the v2 publication_id schema",
            ):
                proof.validate_bundle(root, bundle_path)

    def test_returned_at_requires_a_valid_rfc3339_date_time(self) -> None:
        for returned_at in (
            "not-a-timestamp",
            "2026-07-28T09:30:00",
            "2026-02-30T09:30:00Z",
            "2026-07-28T09:30:00+24:00",
            "2026-07-28T09:30:00+01:60",
        ):
            with self.subTest(returned_at=returned_at):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    mutate_return_receipt(
                        root,
                        bundle_path,
                        lambda receipt: receipt["return"].update(
                            {"returned_at": returned_at}
                        ),
                    )
                    with self.assertRaisesRegex(
                        proof.ProofGateError,
                        "RFC3339 date-time",
                    ):
                        proof.validate_bundle(root, bundle_path)

    def test_legacy_v1_dispatch_precedes_v2_exact_shape_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            bundle_path.write_text(
                json.dumps(
                    {
                        "schema": proof.LEGACY_BUNDLE_SCHEMA,
                        "v2_only_unknown": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "legacy v1 machine-proof bundles are historical/read-only",
            ):
                proof.validate_bundle(root, bundle_path)

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            return_relative = "proof/PREPUBLICATION_RETURN_RECEIPT.json"
            (root / return_relative).write_text(
                json.dumps(
                    {
                        "schema": proof.LEGACY_RETURN_SCHEMA,
                        "v2_only_unknown": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            refresh_artifact(
                root,
                bundle,
                return_relative,
                "RETURN_RECEIPT",
            )
            bundle_path.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "legacy v1 prepublication return receipts are "
                "historical/read-only",
            ):
                proof.validate_bundle(root, bundle_path)

    def test_legacy_v1_contracts_are_byte_frozen_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            self.fixture(root)
            freeze = proof.validate_legacy_contract_freeze(root)
            self.assertTrue(freeze["historical_read_only"])
            self.assertFalse(freeze["production_mutation_authorized"])
            self.assertEqual(
                freeze["policy"],
                {
                    "id": proof.LEGACY_POLICY_ID,
                    "path": proof.LEGACY_POLICY_PATH,
                    "version": proof.LEGACY_POLICY_VERSION,
                    "sha256": proof.LEGACY_POLICY_SHA256,
                    "git_blob_sha1": proof.LEGACY_POLICY_GIT_BLOB_SHA1,
                },
            )
            self.assertEqual(
                freeze["schema_contracts"],
                {
                    "machine_proof_bundle": {
                        "path": proof.LEGACY_BUNDLE_SCHEMA_PATH,
                        "sha256": proof.LEGACY_BUNDLE_SCHEMA_SHA256,
                        "git_blob_sha1": (
                            proof.LEGACY_BUNDLE_SCHEMA_GIT_BLOB_SHA1
                        ),
                    },
                    "prepublication_return_receipt": {
                        "path": proof.LEGACY_RETURN_SCHEMA_PATH,
                        "sha256": proof.LEGACY_RETURN_SCHEMA_SHA256,
                        "git_blob_sha1": (
                            proof.LEGACY_RETURN_SCHEMA_GIT_BLOB_SHA1
                        ),
                    },
                },
            )

        for name, relative in (
            ("policy", proof.LEGACY_POLICY_PATH),
            ("bundle schema", proof.LEGACY_BUNDLE_SCHEMA_PATH),
            ("return schema", proof.LEGACY_RETURN_SCHEMA_PATH),
        ):
            with self.subTest(contract=name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    legacy_path = root / relative
                    legacy_path.write_bytes(legacy_path.read_bytes() + b" ")
                    with self.assertRaisesRegex(
                        proof.ProofGateError,
                        "legacy v1 .* (?:byte-frozen|exact byte identity differs)",
                    ):
                        proof.validate_bundle(root, bundle_path)

    def test_legacy_v1_proof_contract_cannot_authorize_new_production(
        self,
    ) -> None:
        cases = (
            (
                "bundle schema",
                lambda root, bundle: bundle.update(
                    {"schema": proof.LEGACY_BUNDLE_SCHEMA}
                ),
                "legacy v1 machine-proof bundles are historical/read-only",
            ),
            (
                "policy binding",
                lambda root, bundle: bundle.update(
                    {
                        "policy": {
                            "id": proof.LEGACY_POLICY_ID,
                            "path": proof.LEGACY_POLICY_PATH,
                            "version": proof.LEGACY_POLICY_VERSION,
                            "sha256": proof.LEGACY_POLICY_SHA256,
                            "git_blob_sha1": proof.LEGACY_POLICY_GIT_BLOB_SHA1,
                        }
                    }
                ),
                "legacy v1 proof policy is historical/read-only",
            ),
        )
        for name, mutation, error in cases:
            with self.subTest(contract=name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    bundle = json.loads(
                        bundle_path.read_text(encoding="utf-8")
                    )
                    mutation(root, bundle)
                    bundle_path.write_text(
                        json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            mutate_return_receipt(
                root,
                bundle_path,
                lambda receipt: receipt.update(
                    {"schema": proof.LEGACY_RETURN_SCHEMA}
                ),
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "legacy v1 prepublication return receipts are "
                "historical/read-only",
            ):
                proof.validate_bundle(root, bundle_path)

    def test_legacy_v1_is_readable_but_cannot_mutate_zenodo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            artifact = write(root, "docs/legacy.md", b"# Legacy\n")
            manifest = {
                "schema": publish.SCHEMA,
                "state": "publish",
                "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
                "repository": "Goldkelch/qik-vrt",
                "metadata": {
                    "title": "Legacy fixture",
                    "upload_type": "publication",
                    "publication_type": "technicalnote",
                    "description": "Historical read-only manifest",
                    "creators": [{"name": "Lohmann, Ingolf"}],
                    "version": "1.0.0",
                    "access_right": "open",
                    "prereserve_doi": True,
                },
                "files": [{
                    "path": "docs/legacy.md",
                    "name": "legacy.md",
                    "git_blob_sha": blob(artifact.read_bytes()),
                }],
                "evidence_path": "release/legacy/zenodo-publication.json",
            }
            manifest_path = write(
                root,
                "release/legacy/publish-request.json",
                (json.dumps(manifest) + "\n").encode(),
            )
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"}):
                loaded = publish.load_manifest(manifest_path, root)
                self.assertEqual(loaded["schema"], publish.SCHEMA)
                self.assertNotIn("owner_authorization", loaded)
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "NO_MACHINE_PROOF_NO_ZENODO_UPLOAD",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()

    def test_v2_manifest_without_owner_authorization_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            value.pop("owner_authorization")
            manifest_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "missing=owner_authorization",
            ):
                publish.load_manifest(manifest_path, root)

    def test_git_metadata_paths_are_rejected_for_every_publication_role(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            forbidden_manifest = write(
                root,
                ".git/publish-request.json",
                manifest_path.read_bytes(),
            )
            with self.assertRaisesRegex(zenodo.ZenodoError, "Git metadata"):
                publish.load_manifest(forbidden_manifest, root)

        cases = (
            (
                "evidence",
                lambda value: value.update(
                    {"evidence_path": ".git/zenodo-publication.json"}
                ),
            ),
            (
                "owner authorization",
                lambda value: value["owner_authorization"].update(
                    {"path": ".git/OWNER_ZENODO_AUTHORIZATION.json"}
                ),
            ),
            (
                "upload",
                lambda value: value["files"][0].update(
                    {"path": ".git/upload.bin"}
                ),
            ),
        )
        for label, mutation in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    _, manifest_path = self.fixture(root)
                    value = json.loads(
                        manifest_path.read_text(encoding="utf-8")
                    )
                    mutation(value)
                    manifest_path.write_text(
                        json.dumps(value) + "\n",
                        encoding="utf-8",
                    )
                    with mock.patch.dict(
                        os.environ,
                        {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
                    ):
                        with self.assertRaisesRegex(
                            zenodo.ZenodoError,
                            "Git metadata",
                        ):
                            publish.load_manifest(manifest_path, root)

    def test_v2_manifest_source_head_must_match_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            value["source_head"] = "c" * 40
            manifest_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
            ):
                with self.assertRaisesRegex(
                    zenodo.ZenodoError,
                    "source_head differs from the v2 manifest",
                ):
                    publish.load_manifest(manifest_path, root)

    def test_generic_publisher_matches_natural_person_to_creator_name_forms(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                    publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
                },
            ):
                loaded = publish.load_manifest(manifest_path, root)
            self.assertEqual(
                loaded["owner_authorization"]["principal"],
                {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
            )

    def test_owner_authorization_scope_mismatches_are_blocked(self) -> None:
        cases = (
            (
                "principal",
                lambda value: value["principal"].update({"name": "Someone Else"}),
                "not a manifest metadata creator",
            ),
            (
                "publication_id",
                lambda value: value.update({"publication_id": "other-publication"}),
                "publication_id differs",
            ),
            (
                "return receipt",
                lambda value: value["candidate_return_receipt"].update(
                    {"sha256": "0" * 64}
                ),
                "candidate_return_receipt differs",
            ),
            (
                "metadata",
                lambda value: value.update(
                    {"canonical_metadata_sha256": "0" * 64}
                ),
                "canonical metadata digest differs",
            ),
            (
                "upload bytes",
                lambda value: value["uploads"][0].update(
                    {"bytes": value["uploads"][0]["bytes"] + 1}
                ),
                "uploads differ",
            ),
            (
                "machine proof",
                lambda value: value["machine_proof"].update(
                    {"git_blob_sha": "0" * 40}
                ),
                "machine_proof differs",
            ),
            (
                "repository",
                lambda value: value.update({"repository": "other/repository"}),
                "repository differs",
            ),
            (
                "source head",
                lambda value: value.update({"source_head": "c" * 40}),
                "source_head differs",
            ),
            (
                "effects",
                lambda value: value.update(
                    {"authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS[:-1])}
                ),
                "allowed effects differ",
            ),
            (
                "single use",
                lambda value: value.update({"single_use": False}),
                "explicitly single-use",
            ),
            (
                "single use scope",
                lambda value: value.update({"single_use_scope": "GLOBAL"}),
                "single-use scope",
            ),
            (
                "nonce",
                lambda value: value.update({"nonce": "0" * 64}),
                "nonce must be",
            ),
            (
                "authorization id",
                lambda value: value.update({"authorization_id": "short"}),
                "authorization_id is unsafe",
            ),
            (
                "authorization event timestamp",
                lambda value: value["authorization_event"].update(
                    {"authorized_at": "2026-07-30 18:00:00"}
                ),
                "must be an RFC3339 timestamp",
            ),
            (
                "authorization event predates return",
                lambda value: value["authorization_event"].update(
                    {"authorized_at": "2026-07-27T18:00:00Z"}
                ),
                "predates the candidate prepublication return",
            ),
            (
                "authorization event decision",
                lambda value: value["authorization_event"].update(
                    {"decision": "REVIEW_ONLY"}
                ),
                "decision must equal AUTHORIZE_EXACT_UPLOAD",
            ),
            (
                "authorization event statement",
                lambda value: value["authorization_event"].update(
                    {"statement_sha256": "0" * 64}
                ),
                "statement digest differs",
            ),
            (
                "authorization event principal",
                lambda value: value["authorization_event"]["principal"].update(
                    {"name": "Someone Else"}
                ),
                "authorization_event principal differs",
            ),
            (
                "authorization event return receipt",
                lambda value: value["authorization_event"].update(
                    {"candidate_return_receipt_sha256": "0" * 64}
                ),
                "candidate return receipt digest differs",
            ),
            (
                "unknown key",
                lambda value: value.update({"unbound": True}),
                "invalid owner authorization keys",
            ),
        )
        for label, mutation, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    _, manifest_path = self.fixture(root)
                    mutate_authorization(root, manifest_path, mutation)
                    with mock.patch.dict(
                        os.environ,
                        {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
                    ):
                        with self.assertRaisesRegex(zenodo.ZenodoError, error):
                            publish.load_manifest(manifest_path, root)

    def test_owner_authorization_reference_tamper_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            authorization_path = root / manifest["owner_authorization"]["path"]
            authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
            authorization["nonce"] = "c" * 64
            authorization_path.write_text(
                json.dumps(authorization) + "\n",
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
            ):
                with self.assertRaisesRegex(
                    zenodo.ZenodoError,
                    "differs from the exact repository bytes",
                ):
                    publish.load_manifest(manifest_path, root)

    def test_recomputed_denial_statement_cannot_authorize_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)

            def deny(authorization: dict[str, Any]) -> None:
                statement = "DENY_EXACT_UPLOAD this publication is rejected"
                authorization["authorization_event"]["exact_statement"] = statement
                authorization["authorization_event"]["statement_sha256"] = (
                    hashlib.sha256(statement.encode("utf-8")).hexdigest()
                )

            mutate_authorization(root, manifest_path, deny)
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
            ):
                with self.assertRaisesRegex(
                    zenodo.ZenodoError,
                    "exact canonical authorization statement",
                ):
                    publish.load_manifest(manifest_path, root)

    def test_owner_principal_must_match_active_policy_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            policy_path = root / proof.POLICY_PATH
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["activation"]["principal"]["name"] = "Someone Else"
            policy_path.write_text(json.dumps(policy) + "\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
            ):
                with self.assertRaisesRegex(
                    zenodo.ZenodoError,
                    "active Zenodo proof policy exact byte identity",
                ):
                    publish.load_manifest(manifest_path, root)

    def test_owner_authorization_must_not_be_uploaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            relative = value["owner_authorization"]["path"]
            value["files"].append(
                {
                    "path": relative,
                    "name": "OWNER_ZENODO_AUTHORIZATION.json",
                    "git_blob_sha": blob((root / relative).read_bytes()),
                }
            )
            manifest_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
            ):
                with self.assertRaisesRegex(
                    zenodo.ZenodoError,
                    "exact proof-bearing set",
                ):
                    publish.load_manifest(manifest_path, root)

    def test_load_manifest_rejects_foreign_executing_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "other/repository"},
                clear=True,
            ):
                with self.assertRaisesRegex(
                    zenodo.ZenodoError,
                    "manifest repository differs from the executing repository",
                ):
                    publish.load_manifest(manifest_path, root)

    def test_production_requires_exact_repository_execution_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "repository identity is missing or mismatched",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()

    def test_wrong_github_sha_is_blocked_before_remote_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            self.assert_publish_blocked_before_lock(
                root,
                manifest_path,
                execution_head,
                "GITHUB_SHA differs",
                github_sha="0" * 40,
            )

    def test_non_ancestor_source_head_is_blocked_before_remote_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, _execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            empty_tree = run_git(
                root,
                "hash-object",
                "-w",
                "-t",
                "tree",
                "/dev/null",
            )
            unrelated = run_git(
                root,
                "commit-tree",
                empty_tree,
                "-m",
                "unrelated candidate source",
            )
            rebind_fixture(root, manifest_path, source_head=unrelated)
            run_git(root, "add", "--all")
            run_git(root, "commit", "--quiet", "-m", "bind unrelated source")
            execution_head = run_git(root, "rev-parse", "HEAD")
            self.assert_publish_blocked_before_lock(
                root,
                manifest_path,
                execution_head,
                "not a descendant",
            )

    def test_source_candidate_blob_mismatch_is_blocked_before_remote_lock(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, _execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            candidate_path = root / "docs/candidate.md"
            expected_bytes = candidate_path.read_bytes()
            candidate_path.write_bytes(b"# Different candidate source\n")
            run_git(root, "add", "--", "docs/candidate.md")
            run_git(root, "commit", "--quiet", "-m", "mismatched candidate source")
            mismatched_source = run_git(root, "rev-parse", "HEAD")
            candidate_path.write_bytes(expected_bytes)
            rebind_fixture(
                root,
                manifest_path,
                source_head=mismatched_source,
            )
            run_git(root, "add", "--all")
            run_git(root, "commit", "--quiet", "-m", "restore execution bytes")
            execution_head = run_git(root, "rev-parse", "HEAD")
            self.assert_publish_blocked_before_lock(
                root,
                manifest_path,
                execution_head,
                "candidate-return Git blob differs",
            )

    def test_execution_scope_allows_only_identical_upload_control_dual_role(
        self,
    ) -> None:
        upload_blob = "a" * 40
        legacy_control_blob = "b" * 40
        authorization_blob = "c" * 40
        manifest = {
            "files": [
                {
                    "path": publish.machine_proof.POLICY_PATH,
                    "git_blob_sha": upload_blob,
                }
            ],
            "owner_authorization": {
                "path": "release/fixture/OWNER_ZENODO_AUTHORIZATION.json",
                "git_blob_sha": authorization_blob,
            },
        }
        controls = {
            publish.machine_proof.POLICY_PATH: upload_blob,
            publish.machine_proof.LEGACY_POLICY_PATH: legacy_control_blob,
        }
        scope = publish._execution_scope_blobs(
            "release/fixture/publish-request.json",
            b"{}\n",
            manifest,
            controls,
        )
        self.assertEqual(
            scope[publish.machine_proof.POLICY_PATH],
            upload_blob,
        )
        self.assertEqual(
            scope[publish.machine_proof.LEGACY_POLICY_PATH],
            legacy_control_blob,
        )
        self.assertEqual(
            scope[manifest["owner_authorization"]["path"]],
            authorization_blob,
        )

        differing = dict(controls)
        differing[publish.machine_proof.POLICY_PATH] = "d" * 40
        with self.assertRaisesRegex(
            zenodo.ZenodoError,
            "roles disagree on the exact Git blob",
        ):
            publish._execution_scope_blobs(
                "release/fixture/publish-request.json",
                b"{}\n",
                manifest,
                differing,
            )

        owner_uploaded = copy.deepcopy(manifest)
        owner_uploaded["files"].append(
            {
                "path": manifest["owner_authorization"]["path"],
                "git_blob_sha": authorization_blob,
            }
        )
        with self.assertRaisesRegex(
            zenodo.ZenodoError,
            "must remain control-only",
        ):
            publish._execution_scope_blobs(
                "release/fixture/publish-request.json",
                b"{}\n",
                owner_uploaded,
                controls,
            )

    def test_dirty_control_mode_is_blocked_before_remote_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            run_git(
                root,
                "update-index",
                "--chmod=+x",
                "proof/EVIDENCE.json",
            )
            self.assert_publish_blocked_before_lock(
                root,
                manifest_path,
                execution_head,
                "upload/control paths are not clean",
            )

    def test_all_contract_files_must_exist_in_execution_head_not_only_worktree(
        self,
    ) -> None:
        contract_paths = (
            proof.POLICY_PATH,
            proof.BUNDLE_SCHEMA_PATH,
            proof.RETURN_SCHEMA_PATH,
            proof.LEGACY_POLICY_PATH,
            proof.LEGACY_BUNDLE_SCHEMA_PATH,
            proof.LEGACY_RETURN_SCHEMA_PATH,
        )
        for relative in contract_paths:
            with self.subTest(path=relative):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    _, manifest_path = self.fixture(root)
                    materialize_git_history(root, manifest_path)
                    contract_bytes = (root / relative).read_bytes()
                    run_git(root, "rm", "--quiet", "--", relative)
                    run_git(
                        root,
                        "commit",
                        "--quiet",
                        "-m",
                        "remove one machine-proof contract from execution head",
                    )
                    execution_head = run_git(root, "rev-parse", "HEAD")
                    write(root, relative, contract_bytes)
                    self.assert_publish_blocked_before_lock(
                        root,
                        manifest_path,
                        execution_head,
                        "upload/control bytes are not committed at the "
                        "execution HEAD",
                    )

    def test_origin_repository_mismatch_is_blocked_before_remote_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            run_git(
                root,
                "remote",
                "set-url",
                "--push",
                "origin",
                str(root / ".git/test-remotes/other/repository.git"),
            )
            self.assert_publish_blocked_before_lock(
                root,
                manifest_path,
                execution_head,
                "origin must be exact GitHub HTTPS or SSH",
            )

    def test_consumed_owner_authorization_is_rejected_before_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
            ):
                loaded = publish.load_manifest(manifest_path, root)
            authorization = loaded["owner_authorization"]
            write(
                root,
                "release/already-consumed/zenodo-publication.json",
                (
                    json.dumps(
                        {
                            "schema": publish.EVIDENCE_SCHEMA,
                            "state": "published",
                            "owner_authorization": {
                                "authorization_id": authorization[
                                    "authorization_id"
                                ],
                                "nonce_digest": authorization["nonce_digest"],
                            },
                        },
                        sort_keys=True,
                    )
                    + "\n"
                ).encode(),
            )
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                    publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
                },
            ):
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "already been consumed",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()

    def test_consumption_marker_precedes_transport_and_survives_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            evidence_path = root / "release/fixture/zenodo-publication.json"
            token = "z" * 32

            def fail_after_marker(_metadata: object) -> None:
                marker = json.loads(evidence_path.read_text(encoding="utf-8"))
                self.assertEqual(marker["state"], publish.CONSUMPTION_STATE)
                self.assertTrue(marker["recovery"]["authorization_consumed"])
                self.assertIn(
                    "authorization_id",
                    marker["owner_authorization"],
                )
                self.assertIn("nonce_digest", marker["owner_authorization"])
                self.assertEqual(
                    marker["remote_consumption"]["ref"],
                    marker["owner_authorization"]["remote_consumption_ref"],
                )
                self.assertEqual(
                    marker["remote_consumption"]["object_type"],
                    "tag",
                )
                self.assertRegex(
                    marker["remote_consumption"]["tag_object"],
                    r"^[0-9a-f]{40}$",
                )
                raise zenodo.ZenodoError("simulated create failure")

            environment = {
                "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                "GITHUB_SHA": execution_head,
                publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: token,
            }
            github = FakeGitHubGitData()
            with mock.patch.dict(os.environ, environment, clear=True):
                with mock.patch.object(
                    publish,
                    "_github_api_request",
                    side_effect=github,
                ), mock.patch.object(
                    publish,
                    "_list_all_owned_depositions",
                    return_value=[],
                ), mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    client_type.return_value.create_paper.side_effect = fail_after_marker
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "simulated create failure",
                    ):
                        publish.publish(manifest_path, root)
            marker = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(marker["state"], publish.CONSUMPTION_STATE)
            self.assertEqual(marker["phase"], "create_requested")
            with mock.patch.dict(os.environ, environment, clear=True):
                manifest = publish.load_manifest(manifest_path, root)
            validated = publish._validate_recovery_evidence(
                marker,
                manifest_path,
                root,
                manifest,
                execution_head,
            )
            self.assertEqual(validated["phase"], "create_requested")
            legacy = copy.deepcopy(marker)
            legacy["schema"] = publish.EVIDENCE_SCHEMA
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "legacy v1 publication evidence is immutable",
            ):
                publish._validate_recovery_evidence(
                    legacy,
                    manifest_path,
                    root,
                    manifest,
                    execution_head,
                )

            with mock.patch.dict(os.environ, environment, clear=True):
                with mock.patch.object(
                    publish,
                    "_github_api_request",
                    side_effect=github,
                ), mock.patch.object(
                    publish,
                    "_list_all_owned_depositions",
                    return_value=[],
                ), mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "requires exactly one canonically matching",
                    ):
                        publish.publish(manifest_path, root)
                    client_type.assert_called_once()

    def test_successful_publication_evidence_consumes_id_and_nonce_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            draft = {
                "id": 123,
                "metadata": {
                    "prereserve_doi": {"doi": "10.5281/zenodo.123"},
                },
            }
            published = {
                "id": 123,
                "doi": "10.5281/zenodo.123",
                "conceptdoi": "10.5281/zenodo.122",
                "links": {"html": "https://zenodo.org/records/123"},
                "metadata": {},
            }
            evidence_path = root / "release/fixture/zenodo-publication.json"

            def prepare(*_args: object, **_kwargs: object) -> str:
                marker = json.loads(evidence_path.read_text(encoding="utf-8"))
                self.assertEqual(marker["phase"], "record_created")
                self.assertTrue(marker["recovery"]["record_created"])
                return "draft"

            def finish(*_args: object, **_kwargs: object) -> dict[str, Any]:
                marker = json.loads(evidence_path.read_text(encoding="utf-8"))
                self.assertEqual(marker["phase"], "publish_requested")
                self.assertTrue(marker["recovery"]["prepared"])
                return published

            token = "z" * 32
            github = FakeGitHubGitData()
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                    "GITHUB_SHA": execution_head,
                    publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: token,
                },
                clear=True,
            ):
                with mock.patch.object(
                    publish,
                    "_github_api_request",
                    side_effect=github,
                ), mock.patch.object(
                    publish,
                    "_list_all_owned_depositions",
                    return_value=[],
                ), mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    client = client_type.return_value
                    client.create_paper.return_value = draft
                    client.prepare_draft.side_effect = prepare
                    client.publish_and_poll.side_effect = finish
                    evidence = publish.publish(manifest_path, root)
            authorization = evidence["owner_authorization"]
            self.assertEqual(
                authorization["authorization_id"],
                FIXTURE_AUTHORIZATION_ID,
            )
            self.assertEqual(
                authorization["nonce_digest"],
                {
                    "algorithm": "SHA-256",
                    "value": hashlib.sha256(
                        AUTHORIZATION_NONCE.encode("ascii")
                    ).hexdigest(),
                },
            )
            self.assertNotIn("nonce", authorization)
            self.assertEqual(
                evidence["remote_consumption"]["ref"],
                authorization["remote_consumption_ref"],
            )
            self.assertIn(
                evidence["remote_consumption"]["tag_object"],
                github.tags,
            )
            evidence_bytes = (
                root / "release/fixture/zenodo-publication.json"
            ).read_bytes()
            self.assertNotIn(AUTHORIZATION_NONCE.encode("ascii"), evidence_bytes)
            self.assertEqual(evidence["schema"], publish.EVIDENCE_SCHEMA_V2)
            self.assertEqual(evidence["phase"], "public_verified")
            self.assertEqual(
                evidence["governance_boundaries"],
                list(publish.GOVERNANCE_BOUNDARIES),
            )
            self.assertTrue(evidence["recovery"]["public_verified"])
            tampered = copy.deepcopy(evidence)
            tampered["record_url"] = "https://zenodo.org.evil/records/123"
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY},
                clear=True,
            ):
                manifest = publish.load_manifest(manifest_path, root)
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "exact allowlisted Zenodo record",
            ):
                publish._validate_recovery_evidence(
                    tampered,
                    manifest_path,
                    root,
                    manifest,
                    execution_head,
                )

    def test_remote_consumption_ref_is_atomic_across_two_concurrent_runners(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY},
                clear=True,
            ):
                manifest = publish.load_manifest(manifest_path, root)
            expected_ref = expected_consumption_ref(root, manifest_path)
            start_barrier = threading.Barrier(2)
            github = FakeGitHubGitData()

            def attempt() -> dict[str, str]:
                start_barrier.wait(timeout=10)
                return publish._acquire_remote_consumption_lock(
                    root,
                    manifest,
                    execution_head,
                    TEST_GITHUB_TOKEN,
                )

            with mock.patch.object(
                publish,
                "_github_api_request",
                side_effect=github,
            ):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    futures = (executor.submit(attempt), executor.submit(attempt))
                    outcomes = [future.result(timeout=30) for future in futures]

            self.assertEqual(set(github.refs), {expected_ref})
            self.assertEqual(
                {item["recovery_mode"] for item in outcomes},
                {"NEWLY_CREATED_REF", "EXISTING_EXACT_REF_NO_CREATE"},
            )
            self.assertEqual(
                {item["tag_object"] for item in outcomes},
                {github.refs[expected_ref]},
            )

    def test_existing_ref_requires_the_exact_annotated_decision_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY},
                clear=True,
            ):
                manifest = publish.load_manifest(manifest_path, root)
            github = FakeGitHubGitData()
            with mock.patch.object(
                publish,
                "_github_api_request",
                side_effect=github,
            ):
                remote = publish._acquire_remote_consumption_lock(
                    root,
                    manifest,
                    execution_head,
                    TEST_GITHUB_TOKEN,
                )
                github.tags[remote["tag_object"]]["message"] += "tampered=true\n"
                with self.assertRaisesRegex(
                    zenodo.ZenodoError,
                    "differs from the exact decision",
                ):
                    publish._acquire_remote_consumption_lock(
                        root,
                        manifest,
                        execution_head,
                        TEST_GITHUB_TOKEN,
                    )

    def test_existing_exact_ref_without_evidence_is_no_create_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            github = FakeGitHubGitData()
            environment = {
                "GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY,
                "GITHUB_SHA": execution_head,
                publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
            }
            with mock.patch.dict(os.environ, environment, clear=True):
                manifest = publish.load_manifest(manifest_path, root)
                with mock.patch.object(
                    publish,
                    "_github_api_request",
                    side_effect=github,
                ):
                    publish._acquire_remote_consumption_lock(
                        root,
                        manifest,
                        execution_head,
                        TEST_GITHUB_TOKEN,
                    )
                with mock.patch.object(
                    publish,
                    "_github_api_request",
                    side_effect=github,
                ), mock.patch.object(
                    publish,
                    "_list_all_owned_depositions",
                    return_value=[],
                ), mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "requires exactly one canonically matching",
                    ):
                        publish.publish(manifest_path, root)
                    client_type.return_value.create_paper.assert_not_called()
            marker = json.loads(
                (
                    root / "release/fixture/zenodo-publication.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(marker["phase"], "create_requested")
            self.assertEqual(
                marker["remote_consumption"]["recovery_mode"],
                "EXISTING_EXACT_REF_NO_CREATE",
            )

    def test_create_requested_rerun_recovers_one_record_without_second_draft(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            github = FakeGitHubGitData()
            environment = {
                "GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY,
                "GITHUB_SHA": execution_head,
                publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
            }
            with mock.patch.dict(os.environ, environment, clear=True):
                manifest = publish.load_manifest(manifest_path, root)
                with mock.patch.object(
                    publish,
                    "_github_api_request",
                    side_effect=github,
                ):
                    publish._acquire_remote_consumption_lock(
                        root,
                        manifest,
                        execution_head,
                        TEST_GITHUB_TOKEN,
                    )
                draft_metadata = dict(manifest["metadata"])
                draft_metadata.pop("prereserve_doi")
                draft_metadata["prereserve_doi"] = {
                    "doi": "10.5281/zenodo.123"
                }
                inventory_item = {"id": 123, "metadata": draft_metadata}
                current_draft = {
                    "id": 123,
                    "metadata": draft_metadata,
                    "files": [],
                }
                published = {
                    "id": 123,
                    "doi": "10.5281/zenodo.123",
                    "conceptdoi": "10.5281/zenodo.122",
                    "links": {"html": "https://zenodo.org/records/123"},
                    "metadata": {},
                }
                with mock.patch.object(
                    publish,
                    "_github_api_request",
                    side_effect=github,
                ), mock.patch.object(
                    publish,
                    "_list_all_owned_depositions",
                    return_value=[inventory_item],
                ), mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    client = client_type.return_value
                    client.get_deposition_or_record.return_value = (
                        "draft",
                        current_draft,
                    )
                    client._server_files.return_value = []
                    client.prepare_draft.return_value = "draft"
                    client.publish_and_poll.return_value = published
                    evidence = publish.publish(manifest_path, root)
                    client.create_paper.assert_not_called()
            self.assertEqual(evidence["phase"], "public_verified")
            self.assertEqual(evidence["record_id"], 123)
            self.assertEqual(evidence["doi"], "10.5281/zenodo.123")

    def test_identity_candidate_with_divergent_metadata_blocks_precreate(self) -> None:
        metadata = {
            "title": "Bound title",
            "version": "1.0.0",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "description": "canonical",
            "upload_type": "publication",
            "access_right": "open",
            "prereserve_doi": True,
        }
        inventory_item = {
            "id": 123,
            "metadata": {
                **metadata,
                "prereserve_doi": {"doi": "10.5281/zenodo.123"},
            },
        }
        current = copy.deepcopy(inventory_item)
        current["metadata"]["description"] = "divergent"
        current["files"] = []
        client = mock.Mock()
        client.get_deposition_or_record.return_value = ("draft", current)
        with mock.patch.object(
            publish,
            "_list_all_owned_depositions",
            return_value=[inventory_item],
        ):
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "divergent draft metadata",
            ):
                publish._canonical_inventory_candidates(
                    client,
                    "z" * 32,
                    metadata,
                    [],
                )

    def test_owned_inventory_is_complete_stable_and_page_bounded(self) -> None:
        class Response:
            def __init__(self, url: str, value: list[dict[str, Any]]) -> None:
                self.status = 200
                self.url = url
                self.raw = json.dumps(value).encode("utf-8")

            def geturl(self) -> str:
                return self.url

            def read(self, maximum: int) -> bytes:
                return self.raw[:maximum]

            def close(self) -> None:
                return None

        class StableOpener:
            def open(self, request: Any, timeout: int) -> Response:
                query = urllib.parse.parse_qs(
                    urllib.parse.urlsplit(request.full_url).query
                )
                page = int(query["page"][0])
                values = (
                    [{"id": index} for index in range(1, 101)]
                    if page == 1
                    else [{"id": 101}]
                )
                return Response(request.full_url, values)

        client = mock.Mock(base_url=zenodo.DEFAULT_BASE_URL)
        with mock.patch.object(
            urllib.request,
            "build_opener",
            return_value=StableOpener(),
        ):
            inventory = publish._list_all_owned_depositions(client, "z" * 32)
        self.assertEqual([item["id"] for item in inventory], list(range(1, 102)))

        class FullPageOpener:
            def open(self, request: Any, timeout: int) -> Response:
                return Response(
                    request.full_url,
                    [{"id": index} for index in range(1, 101)],
                )

        with mock.patch.object(
            urllib.request,
            "build_opener",
            return_value=FullPageOpener(),
        ), mock.patch.object(publish, "MAX_INVENTORY_PAGES", 1):
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "bounded page count",
            ):
                publish._owned_deposition_inventory_pass(client, "z" * 32)

    def test_owned_inventory_must_be_stable_across_two_complete_passes(self) -> None:
        class Response:
            status = 200

            def __init__(self, url: str, record_id: int) -> None:
                self.url = url
                self.raw = json.dumps([{"id": record_id}]).encode("utf-8")

            def geturl(self) -> str:
                return self.url

            def read(self, maximum: int) -> bytes:
                return self.raw[:maximum]

            def close(self) -> None:
                return None

        class UnstableOpener:
            def __init__(self) -> None:
                self.pass_number = 0

            def open(self, request: Any, timeout: int) -> Response:
                self.pass_number += 1
                return Response(request.full_url, self.pass_number)

        client = mock.Mock(base_url=zenodo.DEFAULT_BASE_URL)
        with mock.patch.object(
            urllib.request,
            "build_opener",
            return_value=UnstableOpener(),
        ):
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "changed between complete passes",
            ):
                publish._list_all_owned_depositions(client, "z" * 32)

    def test_owner_authorization_may_not_contain_zenodo_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            token = "secretpublicationtokenvalue1234"
            mutate_authorization(
                root,
                manifest_path,
                lambda value: value["authorization_event"].update(
                    {"channel": "platform-attestation-" + token}
                ),
            )
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                    "GITHUB_SHA": execution_head,
                    publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: token,
                },
                clear=True,
            ):
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "owner authorization contains the Zenodo access token",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()
            self.assertFalse(
                (root / "release/fixture/zenodo-publication.json").exists()
            )
            expected_ref = expected_consumption_ref(root, manifest_path)
            self.assertEqual(
                run_git(
                    root,
                    "ls-remote",
                    "--refs",
                    "origin",
                    expected_ref,
                ),
                "",
            )

    def test_token_in_description_never_reaches_remote_or_consumes_authorization(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            token = "description-token-value-1234567890"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["metadata"]["description"] = (
                "Proof-bearing fixture " + token
            )
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            rebind_fixture(root, manifest_path)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            expected_ref = expected_consumption_ref(root, manifest_path)
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                    "GITHUB_SHA": execution_head,
                    publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: token,
                },
                clear=True,
            ):
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "Zenodo access token",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()
            self.assertFalse(
                (root / "release/fixture/zenodo-publication.json").exists()
            )
            self.assertEqual(
                run_git(
                    root,
                    "ls-remote",
                    "--refs",
                    "origin",
                    expected_ref,
                ),
                "",
            )

    def test_token_in_upload_never_reaches_remote_or_consumes_authorization(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, manifest_path = self.fixture(root)
            token = "upload-token-value-12345678901234"
            write(
                root,
                "proof/EVIDENCE.json",
                (
                    json.dumps(
                        {"id": "observation", "state": "EVIDENCED", "secret": token},
                        sort_keys=True,
                    )
                    + "\n"
                ).encode(),
            )
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            refresh_artifact(root, bundle, "proof/EVIDENCE.json", "EVIDENCE")
            bundle_path.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            rebind_fixture(root, manifest_path)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            expected_ref = expected_consumption_ref(root, manifest_path)
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                    "GITHUB_SHA": execution_head,
                    publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: token,
                },
                clear=True,
            ):
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "upload file contains the Zenodo access token",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()
            self.assertFalse(
                (root / "release/fixture/zenodo-publication.json").exists()
            )
            self.assertEqual(
                run_git(
                    root,
                    "ls-remote",
                    "--refs",
                    "origin",
                    expected_ref,
                ),
                "",
            )

    def test_invalid_api_base_does_not_consume_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            _source_head, execution_head = materialize_git_history(
                root,
                manifest_path,
            )
            expected_ref = expected_consumption_ref(root, manifest_path)
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                    "GITHUB_SHA": execution_head,
                    "ZENODO_API_BASE": "https://example.invalid/api",
                    publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: TEST_GITHUB_TOKEN,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
                },
                clear=True,
            ):
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "allowlisted Zenodo HTTPS",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()
            self.assertFalse(
                (root / "release/fixture/zenodo-publication.json").exists()
            )
            self.assertEqual(
                run_git(
                    root,
                    "ls-remote",
                    "--refs",
                    "origin",
                    expected_ref,
                ),
                "",
            )

    def test_referenced_kernel_receipt_must_be_kernel_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            kernel_path = root / "proof/KERNEL_RECEIPT.json"
            kernel_path.write_text(
                '{"state":"BOOTSTRAP_PENDING_EXACT_HEAD"}\n',
                encoding="utf-8",
            )
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            for index, artifact in enumerate(bundle["artifacts"]):
                if artifact["path"] == "proof/KERNEL_RECEIPT.json":
                    bundle["artifacts"][index] = bound(
                        root,
                        "proof/KERNEL_RECEIPT.json",
                        kind="KERNEL_RECEIPT",
                    )
                    break
            else:
                self.fail("fixture lacks its bound kernel receipt")
            bundle_path.write_text(json.dumps(bundle) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "state must equal KERNEL_VERIFIED",
            ):
                proof.validate_bundle(root, bundle_path)

    def test_formal_proof_ref_requires_known_theorem_fragment(self) -> None:
        cases = (
            "proof/KERNEL_RECEIPT.json",
            "proof/KERNEL_RECEIPT.json#Unknown.theorem",
        )
        for proof_ref in cases:
            with self.subTest(proof_ref=proof_ref):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                    bundle["claims"][0]["proof_refs"] = [proof_ref]
                    bundle_path.write_text(
                        json.dumps(bundle) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        proof.ProofGateError,
                        "exact theorem fragment",
                    ):
                        proof.validate_bundle(root, bundle_path)

    def test_kernel_receipt_scope_and_exact_head_workflow_are_required(self) -> None:
        cases = (
            (
                "scope",
                lambda receipt: receipt.update({"scope_id": "other-publication"}),
                "publication/scope identity differs",
            ),
            (
                "conclusion",
                lambda receipt: receipt["workflow"].update(
                    {"conclusion": "failure"}
                ),
                "successful exact-head workflow",
            ),
            (
                "exact head",
                lambda receipt: receipt["workflow"].update(
                    {"exact_head_bound": False}
                ),
                "successful exact-head workflow",
            ),
        )
        for label, mutation, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    mutate_kernel_receipt(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_canonical_kernel_receipt_v2_h2_h1_chain_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            stages = enable_canonical_kernel_receipt_v2(root, bundle_path)
            validated = proof.validate_bundle(root, bundle_path)
            self.assertTrue(validated["machine_proof_complete"])
            receipt = json.loads(
                (root / "proof/KERNEL_RECEIPT.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                receipt["verified_candidate"]["head"],
                stages["h1_head"],
            )
            self.assertNotEqual(
                receipt["bootstrap_h0"]["verified_candidate"]["head"],
                receipt["verified_candidate"]["head"],
            )
            self.assertFalse(
                receipt["claim_transition"][
                    "target_exact_head_confirmation_required"
                ]
            )

    def test_canonical_kernel_receipt_v2_validates_archive_provenance(
        self,
    ) -> None:
        cases = (
            (
                "missing archive id",
                lambda receipt: receipt["artifact"].pop("id"),
                "missing=id",
            ),
            (
                "invalid archive id type",
                lambda receipt: receipt["artifact"].update({"id": True}),
                "id must be a positive integer",
            ),
            (
                "wrong archive name",
                lambda receipt: receipt["artifact"].update(
                    {"name": "unbound-evidence"}
                ),
                "name differs from the canonical artifact name",
            ),
            (
                "malformed archive digest",
                lambda receipt: receipt["artifact"].update(
                    {"archive_digest": "sha256:not-a-digest"}
                ),
                "archive_digest has an invalid digest",
            ),
            (
                "invalid archive size type",
                lambda receipt: receipt["artifact"].update(
                    {"archive_size_bytes": False}
                ),
                "archive_size_bytes must be a positive integer",
            ),
            (
                "malformed creation timestamp",
                lambda receipt: receipt["artifact"].update(
                    {"created_at": "2026-07-30"}
                ),
                "created_at must be an RFC3339 date-time",
            ),
            (
                "expiry precedes creation",
                lambda receipt: receipt["artifact"].update(
                    {"expires_at": "2026-07-29T18:46:39Z"}
                ),
                "expires_at must be later than created_at",
            ),
            (
                "H0/H1 archive id reused",
                lambda receipt: receipt["artifact"].update(
                    {"id": receipt["bootstrap_h0"]["artifact"]["id"]}
                ),
                "H0/H1 artifact IDs must differ",
            ),
            (
                "H0/H1 archive digest reused",
                lambda receipt: receipt["artifact"].update(
                    {
                        "archive_digest": receipt["bootstrap_h0"][
                            "artifact"
                        ]["archive_digest"]
                    }
                ),
                "H0/H1 archive digests must differ",
            ),
            (
                "H0/H1 raw file digest reused",
                lambda receipt: receipt["artifact"]["file"].update(
                    {
                        "sha256": receipt["bootstrap_h0"]["artifact"]["file"][
                            "sha256"
                        ]
                    }
                ),
                "H0/H1 raw file SHA-256 must differ",
            ),
        )
        for label, mutation, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    enable_canonical_kernel_receipt_v2(root, bundle_path)
                    mutate_kernel_receipt(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_canonical_kernel_receipt_v2_requires_exact_stage_and_boundary(
        self,
    ) -> None:
        cases = (
            (
                "schema downgrade",
                lambda receipt: receipt.update(
                    {"schema": "qikvrt_fixture_kernel_receipt_v2"}
                ),
                "canonical kernel receipt context requires the exact v2 schema",
            ),
            (
                "schema removed",
                lambda receipt: receipt.pop("schema"),
                "canonical kernel receipt context requires the exact v2 schema",
            ),
            (
                "state",
                lambda receipt: receipt.update(
                    {
                        "state": (
                            "BOOTSTRAP_KERNEL_VERIFIED_"
                            "AWAITING_TARGET_HEAD_CONFIRMATION"
                        )
                    }
                ),
                "state must equal KERNEL_VERIFIED",
            ),
            (
                "H2 stage",
                lambda receipt: receipt.update({"receipt_stage": "H1"}),
                "H2 receipt_stage differs",
            ),
            (
                "H1 stage",
                lambda receipt: receipt.update({"verification_stage": "H0"}),
                "H1 verification_stage differs",
            ),
            (
                "successor predecessor",
                lambda receipt: receipt["materialization_boundary"].update(
                    {
                        "predecessor_head": receipt["bootstrap_h0"][
                            "verified_candidate"
                        ]["head"]
                    }
                ),
                "H2 materialization boundary differs",
            ),
            (
                "self inclusion",
                lambda receipt: receipt["materialization_boundary"].update(
                    {"self_inclusion_claimed": True}
                ),
                "H2 materialization boundary differs",
            ),
            (
                "transition still pending",
                lambda receipt: receipt["claim_transition"].update(
                    {"target_exact_head_confirmation_required": True}
                ),
                "target H1 confirmation is not closed",
            ),
            (
                "proof-ref preservation flag",
                lambda receipt: receipt["claim_transition"].update(
                    {"proof_refs_and_statements_unchanged": False}
                ),
                "must preserve proof refs and statements",
            ),
            (
                "allowed classification transition",
                lambda receipt: receipt["claim_transition"][
                    "allowed_changes"
                ]["classification"].update({"from": "FORMAL_PROVED"}),
                "allowed_changes contract differs",
            ),
        )
        for label, mutation, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    enable_canonical_kernel_receipt_v2(root, bundle_path)
                    mutate_kernel_receipt(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_canonical_publication_id_blocks_schema_and_marker_downgrade(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            enable_canonical_kernel_receipt_v2(root, bundle_path)

            def downgrade(receipt: dict[str, Any]) -> None:
                receipt["schema"] = "qikvrt_fixture_kernel_receipt_v2"
                for marker in proof.CANONICAL_KERNEL_MARKERS:
                    receipt.pop(marker, None)

            mutate_kernel_receipt(root, bundle_path, downgrade)
            with (
                mock.patch.object(
                    proof,
                    "CANONICAL_KERNEL_PUBLICATION_ID",
                    FIXTURE_PUBLICATION_ID,
                ),
                self.assertRaisesRegex(
                    proof.ProofGateError,
                    "canonical kernel receipt context requires "
                    "the exact v2 schema",
                ),
            ):
                proof.validate_bundle(root, bundle_path)

    def test_canonical_kernel_receipt_v2_binds_h0_bootstrap_evidence(
        self,
    ) -> None:
        receipt_cases = (
            (
                "H0 artifact identity",
                lambda receipt: receipt["bootstrap_h0"]["artifact"][
                    "file"
                ].update({"sha256": "0" * 64}),
                "exact raw evidence identity differs",
            ),
            (
                "persisted H0 matrix identity",
                lambda receipt: receipt["bootstrap_h0"][
                    "persisted_claim_matrix"
                ].update({"sha256": "0" * 64}),
                "exact persisted H0 matrix identity differs",
            ),
            (
                "H0 source matrix",
                lambda receipt: receipt["bootstrap_h0"][
                    "claim_matrix"
                ].update({"sha256": "0" * 64}),
                "H0 matrix differs from transition source",
            ),
            (
                "H0 collapsed onto H1",
                lambda receipt: receipt["claim_transition"].update(
                    {
                        "source_claim_matrix": receipt["claim_transition"][
                            "target_claim_matrix"
                        ]
                    }
                ),
                "H0 and H1 matrices must differ",
            ),
            (
                "H0 workflow head",
                lambda receipt: receipt["bootstrap_h0"]["workflow"].update(
                    {"sha": receipt["verified_candidate"]["head"]}
                ),
                "sha differs from its verified candidate head",
            ),
        )
        for label, mutation, error in receipt_cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    enable_canonical_kernel_receipt_v2(root, bundle_path)
                    mutate_kernel_receipt(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            enable_canonical_kernel_receipt_v2(root, bundle_path)
            mutate_canonical_kernel_evidence(
                root,
                bundle_path,
                "H0",
                lambda evidence: evidence["claim_matrix"].update(
                    {"sha256": "0" * 64}
                ),
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "H0 raw evidence matrix differs",
            ):
                proof.validate_bundle(root, bundle_path)

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            enable_canonical_kernel_receipt_v2(root, bundle_path)
            mutate_canonical_h0_claim_matrix(
                root,
                bundle_path,
                lambda matrix: matrix["claims"][0].update(
                    {"statement": "silently changed H0 statement"}
                ),
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "matrix transition exceeds allowed changes",
            ):
                proof.validate_bundle(root, bundle_path)

    def test_canonical_kernel_receipt_v2_binds_active_h1_evidence(
        self,
    ) -> None:
        def swap_formal_binding_proofs(evidence: dict[str, Any]) -> None:
            first, second = evidence["formal_bindings"][:2]
            first_refs = first["proof_refs"]
            second_refs = second["proof_refs"]
            first["proof_refs"] = second_refs
            second["proof_refs"] = first_refs
            for binding in (first, second):
                binding["axioms_by_theorem"] = {
                    theorem: evidence["axioms_by_theorem"][theorem]
                    for theorem in binding["proof_refs"]
                }

        receipt_cases = (
            (
                "H1 artifact identity",
                lambda receipt: receipt["artifact"]["file"].update(
                    {"git_blob_sha1": "0" * 40}
                ),
                "exact raw evidence identity differs",
            ),
            (
                "top-level candidate remains H0",
                lambda receipt: receipt["verified_candidate"].update(
                    {
                        "head": receipt["bootstrap_h0"][
                            "verified_candidate"
                        ]["head"]
                    }
                ),
                "active fields still identify H0",
            ),
            (
                "top-level artifact remains H0",
                lambda receipt: receipt.update(
                    {"artifact": receipt["bootstrap_h0"]["artifact"]}
                ),
                "H0/H1 artifact IDs must differ",
            ),
            (
                "top-level workflow remains H0",
                lambda receipt: receipt["workflow"].update(
                    {
                        "run_id": receipt["bootstrap_h0"]["workflow"][
                            "run_id"
                        ]
                    }
                ),
                "run_id differs from its raw evidence",
            ),
            (
                "repository source bytes",
                lambda receipt: receipt["source"].update(
                    {"sha256": "0" * 64}
                ),
                "source differs from repository bytes",
            ),
            (
                "theorem axiom inventory",
                lambda receipt: receipt["axioms_by_theorem"].update(
                    {"Fixture.unbound": []}
                ),
                "theorem/axiom inventory differs",
            ),
            (
                "boolean theorem count",
                lambda receipt: receipt.update({"theorem_count": True}),
                "theorem_count differs",
            ),
            (
                "boolean formal claim count",
                lambda receipt: receipt.update({"formal_claim_count": True}),
                "formal_claim_count differs",
            ),
        )
        for label, mutation, error in receipt_cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    enable_canonical_kernel_receipt_v2(root, bundle_path)
                    mutate_kernel_receipt(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

        evidence_cases = (
            (
                "workflow head",
                lambda evidence: evidence["workflow"].update(
                    {"sha": "5" * 40}
                ),
                "sha differs from its verified candidate head",
            ),
            (
                "target matrix",
                lambda evidence: evidence["claim_matrix"].update(
                    {"sha256": "0" * 64}
                ),
                "H1 raw evidence target matrix differs",
            ),
            (
                "source",
                lambda evidence: evidence["source"].update(
                    {"sha256": "0" * 64}
                ),
                "H1 source sha256 differs",
            ),
            (
                "axioms",
                lambda evidence: evidence.update(
                    {"axioms_by_theorem": {"Fixture.theorem": ["propext"]}}
                ),
                "H1 axioms differ",
            ),
            (
                "plan",
                lambda evidence: evidence["plan"].update(
                    {"sha256": "0" * 64}
                ),
                "H1 raw evidence plan differs from the receipt",
            ),
            (
                "compiled object",
                lambda evidence: evidence["compiled_object"].update(
                    {"sha256": "0" * 64}
                ),
                "H1 raw evidence compiled_object differs from the receipt",
            ),
            (
                "theorem count",
                lambda evidence: evidence.update({"theorem_count": 3}),
                "H1 raw evidence theorem_count differs",
            ),
            (
                "boolean theorem count",
                lambda evidence: evidence.update({"theorem_count": True}),
                "H1 raw evidence theorem_count differs",
            ),
            (
                "boolean formal claim count",
                lambda evidence: evidence.update({"formal_claim_count": True}),
                "H1 raw evidence formal_claim_count differs",
            ),
            (
                "formal source binding",
                lambda evidence: evidence["formal_bindings"][0].update(
                    {"source_sha256": "0" * 64}
                ),
                "source binding differs",
            ),
            (
                "claimwise proof-ref swap",
                swap_formal_binding_proofs,
                "proof_refs differ from its matrix claim",
            ),
            (
                "entrypoint",
                lambda evidence: evidence["entrypoint"].update(
                    {"sha256": "0" * 64}
                ),
                "entrypoint differs from the receipt",
            ),
            (
                "lean toolchain",
                lambda evidence: evidence["lean_toolchain"].update(
                    {"value": "leanprover/lean4:v0.0.0"}
                ),
                "lean toolchain value differs from the receipt",
            ),
            (
                "runtime",
                lambda evidence: evidence["runtime"][
                    "dynamic_axiom_audit"
                ].update({"output_sha256": "0" * 64}),
                "runtime differs from the receipt",
            ),
        )
        for label, mutation, error in evidence_cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    enable_canonical_kernel_receipt_v2(root, bundle_path)
                    mutate_canonical_kernel_evidence(
                        root,
                        bundle_path,
                        "H1",
                        mutation,
                    )
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_kernel_transition_must_close_on_bound_claim_matrix(self) -> None:
        def valid_transition(root: pathlib.Path) -> dict[str, object]:
            return {
                "target_exact_head_confirmation_required": False,
                "target_claim_matrix": transition_matrix_identity(root),
            }

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            mutate_kernel_receipt(
                root,
                bundle_path,
                lambda receipt: receipt.update(
                    {"claim_transition": valid_transition(root)}
                ),
            )
            validated = proof.validate_bundle(root, bundle_path)
            self.assertTrue(validated["machine_proof_complete"])

        cases = (
            (
                "target exact head still required",
                lambda transition: transition.update(
                    {"target_exact_head_confirmation_required": True}
                ),
                "still requires target exact-head confirmation",
            ),
            (
                "target matrix mismatch",
                lambda transition: transition["target_claim_matrix"].update(
                    {"sha256": "0" * 64}
                ),
                "target claim matrix differs",
            ),
        )
        for label, mutate_transition, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)

                    def mutation(receipt: dict[str, Any]) -> None:
                        transition = valid_transition(root)
                        mutate_transition(transition)
                        receipt["claim_transition"] = transition

                    mutate_kernel_receipt(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_open_claim_worded_as_fact_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            value = json.loads(bundle_path.read_text())
            value["claims"][-1]["publication_wording"] = "ESTABLISHED_WITHIN_SCOPE"
            bundle_path.write_text(json.dumps(value) + "\n")
            with self.assertRaisesRegex(proof.ProofGateError, "disposition inconsistent"):
                proof.validate_bundle(root, bundle_path)

    def test_changed_content_without_notice_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            value = json.loads(bundle_path.read_text())
            value["prepublication_return"]["content_changed"] = True
            bundle_path.write_text(json.dumps(value) + "\n")
            with self.assertRaisesRegex(proof.ProofGateError, "lacks CHANGE_NOTICE"):
                proof.validate_bundle(root, bundle_path)

    def test_returned_candidate_hash_mismatch_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            receipt_path = root / "proof/PREPUBLICATION_RETURN_RECEIPT.json"
            value = json.loads(receipt_path.read_text())
            value["candidate_files"][0]["sha256"] = "0" * 64
            receipt_path.write_text(json.dumps(value) + "\n")
            bundle = json.loads(bundle_path.read_text())
            for index, artifact in enumerate(bundle["artifacts"]):
                if artifact["path"] == "proof/PREPUBLICATION_RETURN_RECEIPT.json":
                    bundle["artifacts"][index] = bound(
                        root,
                        "proof/PREPUBLICATION_RETURN_RECEIPT.json",
                        kind="RETURN_RECEIPT",
                    )
                    break
            else:
                self.fail("fixture lacks its bound prepublication return receipt")
            bundle_path.write_text(json.dumps(bundle) + "\n")
            with self.assertRaisesRegex(proof.ProofGateError, "returned candidate SHA-256 mismatch"):
                proof.validate_bundle(root, bundle_path)

    def test_proof_bundle_must_be_in_upload_fileset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, manifest_path = self.fixture(root)
            upload_paths = [
                item["path"]
                for item in json.loads(manifest_path.read_text())["files"]
                if item["path"] != "proof/MACHINE_PROOF_BUNDLE.json"
            ]
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "exact proof-bearing set",
            ):
                proof.validate_bundle(root, bundle_path, upload_paths=upload_paths)

    def test_claim_matrix_inventory_is_bidirectionally_complete(self) -> None:
        cases = (
            (
                "matrix-only claim",
                lambda matrix: (
                    matrix["claims"].append(
                        {
                            **matrix["claims"][-1],
                            "claim_id": "C-MATRIX-ONLY",
                        }
                    ),
                    matrix.update({"claim_count": len(matrix["claims"])}),
                ),
                "missing_from_bundle=C-MATRIX-ONLY",
            ),
            (
                "bundle-only claim",
                lambda matrix: (
                    matrix["claims"].pop(),
                    matrix.update({"claim_count": len(matrix["claims"])}),
                ),
                "absent_from_matrix=C-OPEN",
            ),
            (
                "self-inconsistent count",
                lambda matrix: matrix.update(
                    {"claim_count": matrix["claim_count"] + 1}
                ),
                "claim_count differs",
            ),
        )
        for label, mutation, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    mutate_claim_matrix(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_claim_matrix_semantic_projection_is_exact(self) -> None:
        cases = (
            (
                "statement",
                lambda matrix: matrix["claims"][0].update(
                    {"statement": "Different statement."}
                ),
                "statement/classification/boundary projection",
            ),
            (
                "classification",
                lambda matrix: matrix["claims"][0].update(
                    {"classification": "SOURCE_BOUND"}
                ),
                "statement/classification/boundary projection",
            ),
            (
                "boundary",
                lambda matrix: matrix["claims"][0].update(
                    {"boundary": "different scope"}
                ),
                "statement/classification/boundary projection",
            ),
            (
                "status",
                lambda matrix: matrix["claims"][0].update(
                    {"status": "FORMAL_PENDING_KERNEL"}
                ),
                "status projection",
            ),
            (
                "theorem",
                lambda matrix: matrix["claims"][0].update(
                    {"proof_refs": ["Fixture.other_theorem"]}
                ),
                "formal theorem fragments differ",
            ),
            (
                "source ID",
                lambda matrix: matrix["claims"][0].update(
                    {"sources": ["different-source-id"]}
                ),
                "source IDs differ",
            ),
        )
        for label, mutation, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    mutate_claim_matrix(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_exact_upload_set_rejects_extras_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, manifest_path = self.fixture(root)
            uploads = [
                item["path"]
                for item in json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )["files"]
            ]
            write(root, "proof/UNBOUND.txt", b"not proof-bound\n")
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "extra=proof/UNBOUND.txt",
            ):
                proof.validate_bundle(
                    root,
                    bundle_path,
                    upload_paths=[*uploads, "proof/UNBOUND.txt"],
                )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "duplicate repository paths",
            ):
                proof.validate_bundle(
                    root,
                    bundle_path,
                    upload_paths=[*uploads, uploads[0]],
                )

    def test_candidate_and_artifact_sets_must_be_disjoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["artifacts"].append(
                bound(root, "docs/candidate.md", kind="OTHER")
            )
            bundle_path.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "candidate and artifact path sets overlap",
            ):
                proof.validate_bundle(root, bundle_path)

    def test_changed_return_with_exact_original_and_visible_reasons_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            enable_valid_changed_return(root, bundle_path)
            receipt = proof.validate_bundle(root, bundle_path)
            self.assertTrue(receipt["machine_proof_complete"])

    def test_changed_return_contract_rejects_weak_bindings(self) -> None:
        cases = (
            (
                "duplicate changed ID",
                lambda receipt: receipt["changed_claim_ids"].append("C-OPEN"),
                "must not contain duplicates",
            ),
            (
                "unknown changed ID",
                lambda receipt: receipt["changed_claim_ids"].__setitem__(
                    0,
                    "C-UNKNOWN",
                ),
                "unknown changed claim ID",
            ),
            (
                "missing reason",
                lambda receipt: receipt.update({"change_reasons": []}),
                "changed claim IDs and change reasons differ",
            ),
            (
                "tampered original identity",
                lambda receipt: receipt["original_files"][0].update(
                    {"sha256": "0" * 64}
                ),
                "original file identity mismatch",
            ),
            (
                "wrong corrected digest",
                lambda receipt: receipt["change_reasons"][0].update(
                    {"corrected_sha256": "0" * 64}
                ),
                "corrected SHA-256 differs",
            ),
            (
                "unchanged bytes",
                lambda receipt: receipt["change_reasons"][0].update(
                    {
                        "original_sha256": receipt["change_reasons"][0][
                            "corrected_sha256"
                        ]
                    }
                ),
                "absent from original_files",
            ),
        )
        for label, mutation, error in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    root = pathlib.Path(temporary)
                    bundle_path, _ = self.fixture(root)
                    enable_valid_changed_return(root, bundle_path)
                    mutate_return_receipt(root, bundle_path, mutation)
                    with self.assertRaisesRegex(proof.ProofGateError, error):
                        proof.validate_bundle(root, bundle_path)

    def test_visible_change_notice_must_expose_bound_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            enable_valid_changed_return(root, bundle_path)
            notice_relative = "proof/CHANGE_NOTICE.md"
            write(root, notice_relative, b"# Change Notice\n\nC-OPEN\n")
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            refresh_artifact(root, bundle, notice_relative, "CHANGE_NOTICE")
            bundle_path.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "omits a changed claim ID or its machine-bound reason",
            ):
                proof.validate_bundle(root, bundle_path)

    def test_active_policy_binding_rejects_bundle_and_policy_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["policy"]["sha256"] = "0" * 64
            bundle_path.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "exact active Zenodo proof policy",
            ):
                proof.validate_bundle(root, bundle_path)

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle_path, _ = self.fixture(root)
            policy_path = root / proof.POLICY_PATH
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["hard_gates"] = policy["hard_gates"][:-1]
            policy_path.write_text(
                json.dumps(policy, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                proof.ProofGateError,
                "exact byte identity/semantics differ",
            ):
                proof.validate_bundle(root, bundle_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
