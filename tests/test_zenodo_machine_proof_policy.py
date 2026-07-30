#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
from collections.abc import Callable
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
    run_git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    run_git(root, "remote", "add", "origin", str(remote))
    run_git(
        root,
        "push",
        "--quiet",
        "--set-upstream",
        "origin",
        f"{execution_head}:refs/heads/main",
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
        evidence = write(root, "proof/EVIDENCE.json", b'{"state":"EVIDENCED"}\n')
        source = write(root, "proof/SOURCE.txt", b"Primary source fixture.\n")

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
            "repository": "owner/repository",
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
            "repository": "owner/repository",
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
        expected_ref = (
            publish.CONSUMPTION_REF_PREFIX
            + hashlib.sha256(
                AUTHORIZATION_NONCE.encode("ascii")
            ).hexdigest()
        )
        with mock.patch.dict(
            os.environ,
            {
                "GITHUB_REPOSITORY": "owner/repository",
                "GITHUB_SHA": github_sha or execution_head,
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
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repository"}):
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
                + hashlib.sha256(
                    AUTHORIZATION_NONCE.encode("ascii")
                ).hexdigest(),
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
                "repository": "owner/repository",
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
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repository"}):
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
                        {"GITHUB_REPOSITORY": "owner/repository"},
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
                    "GITHUB_REPOSITORY": "owner/repository",
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
                        {"GITHUB_REPOSITORY": "owner/repository"},
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
                {"GITHUB_REPOSITORY": "owner/repository"},
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
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "exact proof-bearing set",
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
                "origin push repository identity differs",
            )

    def test_consumed_owner_authorization_is_rejected_before_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = self.fixture(root)
            with mock.patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "owner/repository"},
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
                    "GITHUB_REPOSITORY": "owner/repository",
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
                "GITHUB_REPOSITORY": "owner/repository",
                "GITHUB_SHA": execution_head,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: token,
            }
            with mock.patch.dict(os.environ, environment, clear=True):
                with mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    client_type.return_value.create_paper.side_effect = fail_after_marker
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "simulated create failure",
                    ):
                        publish.publish(manifest_path, root)
            marker = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(marker["state"], publish.CONSUMPTION_STATE)

            with mock.patch.dict(os.environ, environment, clear=True):
                with mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "already been consumed",
                    ):
                        publish.publish(manifest_path, root)
                    client_type.assert_not_called()

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
                "conceptdoi": "10.5281/zenodo.122",
                "links": {"html": "https://zenodo.org/records/123"},
                "metadata": {},
            }
            token = "z" * 32
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "owner/repository",
                    "GITHUB_SHA": execution_head,
                    zenodo.TOKEN_ENVIRONMENT_VARIABLE: token,
                },
                clear=True,
            ):
                with mock.patch.object(zenodo, "ZenodoClient") as client_type:
                    client = client_type.return_value
                    client.create_paper.return_value = draft
                    client.publish_and_poll.return_value = published
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
            self.assertEqual(
                run_git(
                    root,
                    "cat-file",
                    "-t",
                    evidence["remote_consumption"]["tag_object"],
                ),
                "tag",
            )
            evidence_bytes = (
                root / "release/fixture/zenodo-publication.json"
            ).read_bytes()
            self.assertNotIn(AUTHORIZATION_NONCE.encode("ascii"), evidence_bytes)

    def test_remote_consumption_ref_is_atomic_across_two_concurrent_clones(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            top = pathlib.Path(temporary)
            seed = top / "seed"
            seed.mkdir()
            _, seed_manifest = self.fixture(seed)
            _source_head, execution_head = materialize_git_history(
                seed,
                seed_manifest,
            )
            remote = seed / TEST_REMOTE_RELATIVE
            clone_one = top / "clone-one"
            clone_two = top / "clone-two"
            run_git(top, "clone", "--quiet", str(remote), str(clone_one))
            run_git(top, "clone", "--quiet", str(remote), str(clone_two))
            relative_manifest = pathlib.Path(
                "release/fixture/publish-request.json"
            )
            expected_ref = (
                publish.CONSUMPTION_REF_PREFIX
                + hashlib.sha256(
                    AUTHORIZATION_NONCE.encode("ascii")
                ).hexdigest()
            )
            origin_barrier = threading.Barrier(2)
            start_barrier = threading.Barrier(2)
            arrivals: list[str] = []
            arrivals_lock = threading.Lock()
            original_origin_gate = publish._validate_origin_repository

            def synchronized_origin_gate(
                root: pathlib.Path,
                repository: str,
            ) -> None:
                original_origin_gate(root, repository)
                origin_barrier.wait(timeout=10)

            class StopAfterGlobalLock:
                def __init__(self, _token: str, _base_url: str) -> None:
                    with arrivals_lock:
                        arrivals.append("ZenodoClient")

                def create_paper(self, _metadata: object) -> None:
                    raise zenodo.ZenodoError("simulated stop after global lock")

            def attempt(root: pathlib.Path) -> str:
                start_barrier.wait(timeout=10)
                try:
                    publish.publish(root / relative_manifest, root)
                except zenodo.ZenodoError as exc:
                    return str(exc)
                return "unexpected-success"

            environment = {
                "GITHUB_REPOSITORY": "owner/repository",
                "GITHUB_SHA": execution_head,
                zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
            }
            with mock.patch.dict(os.environ, environment, clear=True):
                with mock.patch.object(
                    publish,
                    "_validate_origin_repository",
                    side_effect=synchronized_origin_gate,
                ):
                    with mock.patch.object(
                        zenodo,
                        "ZenodoClient",
                        StopAfterGlobalLock,
                    ):
                        with concurrent.futures.ThreadPoolExecutor(
                            max_workers=2
                        ) as executor:
                            futures = (
                                executor.submit(attempt, clone_one),
                                executor.submit(attempt, clone_two),
                            )
                            outcomes = [future.result(timeout=30) for future in futures]

            self.assertEqual(arrivals, ["ZenodoClient"])
            self.assertEqual(
                sum("simulated stop after global lock" in item for item in outcomes),
                1,
            )
            self.assertEqual(
                sum(
                    "remote authorization consumption" in item
                    for item in outcomes
                ),
                1,
            )
            self.assertEqual(
                sum(
                    (
                        clone
                        / "release/fixture/zenodo-publication.json"
                    ).exists()
                    for clone in (clone_one, clone_two)
                ),
                1,
            )
            remote_object = run_git(remote, "rev-parse", expected_ref)
            self.assertEqual(run_git(remote, "cat-file", "-t", remote_object), "tag")

            clone_tag_objects: list[str] = []
            for clone in (clone_one, clone_two):
                inventory = run_git(
                    clone,
                    "cat-file",
                    "--batch-check=%(objectname) %(objecttype)",
                    "--batch-all-objects",
                )
                tags = [
                    line.split()[0]
                    for line in inventory.splitlines()
                    if line.endswith(" tag")
                ]
                self.assertEqual(len(tags), 1)
                clone_tag_objects.append(tags[0])
            self.assertNotEqual(clone_tag_objects[0], clone_tag_objects[1])
            self.assertIn(remote_object, clone_tag_objects)

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
                    "GITHUB_REPOSITORY": "owner/repository",
                    "GITHUB_SHA": execution_head,
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
            expected_ref = (
                publish.CONSUMPTION_REF_PREFIX
                + hashlib.sha256(
                    AUTHORIZATION_NONCE.encode("ascii")
                ).hexdigest()
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
            expected_ref = (
                publish.CONSUMPTION_REF_PREFIX
                + hashlib.sha256(
                    AUTHORIZATION_NONCE.encode("ascii")
                ).hexdigest()
            )
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "owner/repository",
                    "GITHUB_SHA": execution_head,
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
                        {"state": "EVIDENCED", "secret": token},
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
            expected_ref = (
                publish.CONSUMPTION_REF_PREFIX
                + hashlib.sha256(
                    AUTHORIZATION_NONCE.encode("ascii")
                ).hexdigest()
            )
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "owner/repository",
                    "GITHUB_SHA": execution_head,
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
            expected_ref = (
                publish.CONSUMPTION_REF_PREFIX
                + hashlib.sha256(
                    AUTHORIZATION_NONCE.encode("ascii")
                ).hexdigest()
            )
            with mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "owner/repository",
                    "GITHUB_SHA": execution_head,
                    "ZENODO_API_BASE": "https://example.invalid/api",
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
