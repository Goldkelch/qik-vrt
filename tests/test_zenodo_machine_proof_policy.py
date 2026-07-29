#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_machine_proof as proof
from tools import qikvrt_zenodo_publish as publish


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


class MachineProofBeforeZenodoTests(unittest.TestCase):
    maxDiff = None

    def fixture(self, root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        policy_path = write(
            root,
            proof.POLICY_PATH,
            (json.dumps({"schema": proof.POLICY_SCHEMA}) + "\n").encode(),
        )
        self.assertTrue(policy_path.is_file())
        primary = write(
            root,
            "docs/candidate.md",
            b"# Candidate\n\nAll claims are classified and scope bounded.\n",
        )
        claim_matrix = write(root, "proof/CLAIM_MATRIX.json", b'{"claims":6}\n')
        kernel = write(root, "proof/KERNEL_RECEIPT.json", b'{"state":"KERNEL_VERIFIED"}\n')
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
            "publication_id": "fixture-publication-v1",
            "content_changed": False,
            "original_files": [],
            "candidate_files": [
                {
                    key: candidate_identity[key]
                    for key in ("path", "bytes", "sha256", "git_blob_sha1")
                }
            ],
            "changed_claim_ids": [],
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
                "source_refs": [],
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
                "version": "1.0.0",
            },
            "publication_id": "fixture-publication-v1",
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
        manifest = {
            "schema": publish.SCHEMA_V2,
            "state": "publish",
            "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
            "repository": "owner/repository",
            "metadata": {
                "title": "Machine-proved fixture",
                "upload_type": "publication",
                "publication_type": "technicalnote",
                "description": "Proof-bearing fixture",
                "creators": [{"name": "Lohmann, Ingolf"}],
                "version": "1.0.0",
                "access_right": "open",
                "license": "cc-by-nc-nd-4.0",
                "prereserve_doi": True,
            },
            "files": [
                {
                    "path": relative,
                    "name": pathlib.PurePosixPath(relative).name,
                    "git_blob_sha": blob((root / relative).read_bytes()),
                }
                for relative in upload_paths
            ],
            "machine_proof": {
                "path": "proof/MACHINE_PROOF_BUNDLE.json",
                "git_blob_sha": blob(bundle_path.read_bytes()),
                "policy_id": proof.POLICY_ID,
            },
            "evidence_path": "release/fixture/zenodo-publication.json",
        }
        manifest_path = write(
            root,
            "release/fixture/publish-request.json",
            (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(),
        )
        return bundle_path, manifest_path

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
            self.assertTrue(receipt["machine_proof_complete"])
            self.assertEqual(receipt["claim_count"], 6)
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repository"}):
                manifest = publish.load_manifest(manifest_path, root)
            self.assertEqual(manifest["schema"], publish.SCHEMA_V2)
            self.assertTrue(manifest["machine_proof"]["machine_proof_complete"])

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
                with mock.patch.object(zenodo, "ZenodoClient") as client:
                    with self.assertRaisesRegex(
                        zenodo.ZenodoError,
                        "NO_MACHINE_PROOF_NO_ZENODO_UPLOAD",
                    ):
                        publish.publish(manifest_path, root)
                    client.assert_not_called()

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
            with self.assertRaisesRegex(proof.ProofGateError, "absent from the Zenodo upload"):
                proof.validate_bundle(root, bundle_path, upload_paths=upload_paths)


if __name__ == "__main__":
    unittest.main(verbosity=2)
