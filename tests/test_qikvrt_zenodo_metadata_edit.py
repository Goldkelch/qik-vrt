#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Offline tests for the published-record metadata-only Zenodo controller."""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import urllib.parse
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_zenodo_actions as zenodo  # noqa: E402
from tools import qikvrt_zenodo_machine_proof as proof_gate  # noqa: E402
from tools import qikvrt_zenodo_metadata_edit as edit  # noqa: E402
from tools import qikvrt_zenodo_publish as publication  # noqa: E402


TOKEN = "z" * 64
RECORD_ID = 21888130
CONCEPT_ID = 21888129
DOI = "10.5281/zenodo.21888130"
CONCEPT_DOI = "10.5281/zenodo.21888129"
FILE_BYTES = b"immutable published proof bytes\n"


def response(
    status: int,
    value: object | None = None,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> zenodo.HttpResponse:
    if body is None:
        body = b"" if value is None else json.dumps(value, sort_keys=True).encode("utf-8")
    return zenodo.HttpResponse(
        status=status,
        headers=headers or ({"Content-Type": "application/json"} if value is not None else {}),
        body=body,
    )


def metadata_before() -> dict[str, object]:
    return {
        "title": "Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP",
        "upload_type": "publication",
        "publication_type": "workingpaper",
        "description": "Historical prepublication wording.",
        "creators": [{"name": "Lohmann, Ingolf"}],
        "version": "1.0.0",
        "publication_date": "2026-08-11",
        "access_right": "open",
        "license": "cc-by-nc-nd-4.0",
        "language": "deu",
        "keywords": ["QIK-VRT"],
        "notes": "Historical marker.",
    }


def metadata_after() -> dict[str, object]:
    value = metadata_before()
    value["description"] = "Current metadata clarification with explicit evidence boundaries."
    value["keywords"] = ["QIK-VRT", "Retrokausalität", "Eigenzeit", "proper time"]
    value["notes"] = "Metadata clarification only; files remain byte-identical."
    return value


class MetadataEditTransport:
    """Stateful same-record edit/re-publish simulation with immutable files."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bytes | None]] = []
        self.editable = False
        self.revision = 1
        self.etag = '"record-revision-1"'
        self.metadata = metadata_before()
        self.file = {
            "id": "immutable-file-id",
            "filename": "proof.bin",
            "filesize": len(FILE_BYTES),
            "checksum": "md5:" + hashlib.md5(FILE_BYTES).hexdigest(),  # noqa: S324
            "links": {
                "self": "https://zenodo.org/api/files/metadata-edit/proof.bin",
                "download": "https://zenodo.org/api/files/metadata-edit/proof.bin",
            },
        }

    def _draft(self) -> dict[str, object]:
        metadata = copy.deepcopy(self.metadata)
        if metadata.get("prereserve_doi") is True:
            metadata["prereserve_doi"] = {"doi": DOI}
        return {
            "id": RECORD_ID,
            "conceptrecid": CONCEPT_ID,
            "doi": DOI,
            "submitted": True,
            "state": "inprogress",
            "metadata": metadata,
            "files": [copy.deepcopy(self.file)],
            "links": {
                "bucket": "https://zenodo.org/api/files/metadata-edit",
                "self": f"https://zenodo.org/api/deposit/depositions/{RECORD_ID}",
            },
        }

    def _public(self) -> dict[str, object]:
        metadata = copy.deepcopy(self.metadata)
        metadata.pop("prereserve_doi", None)
        upload_type = metadata.pop("upload_type")
        publication_type = metadata.pop("publication_type")
        metadata["resource_type"] = {
            "type": upload_type,
            "subtype": publication_type,
        }
        metadata["license"] = {"id": metadata["license"]}
        public_file = copy.deepcopy(self.file)
        public_file["key"] = public_file.pop("filename")
        public_file["size"] = public_file.pop("filesize")
        return {
            "id": RECORD_ID,
            "conceptrecid": CONCEPT_ID,
            "doi": DOI,
            "conceptdoi": CONCEPT_DOI,
            "revision": self.revision,
            "metadata": metadata,
            "files": [public_file],
        }

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        max_response_bytes: int = zenodo.MAX_RESPONSE_BYTES,
    ) -> zenodo.HttpResponse:
        del content_type, max_response_bytes
        method = method.upper()
        path = urllib.parse.urlsplit(url).path
        self.calls.append((method, path, body))
        if method == "GET" and path == f"/api/records/{RECORD_ID}":
            return response(200, self._public(), headers={"ETag": self.etag, "Content-Type": "application/json"})
        if method == "POST" and path == f"/api/deposit/depositions/{RECORD_ID}/actions/edit":
            if self.editable:
                return response(409, {"message": "already editable"})
            self.editable = True
            return response(201)
        if method == "GET" and path == f"/api/deposit/depositions/{RECORD_ID}":
            if not self.editable:
                return response(404, {"message": "not editable"})
            return response(200, self._draft())
        if method == "PUT" and path == f"/api/deposit/depositions/{RECORD_ID}":
            if not self.editable:
                return response(409, {"message": "not editable"})
            payload = json.loads((body or b"{}").decode("utf-8"))
            self.metadata = copy.deepcopy(payload["metadata"])
            return response(200, self._draft())
        if method == "POST" and path == f"/api/deposit/depositions/{RECORD_ID}/actions/publish":
            if not self.editable:
                return response(409, {"message": "not editable"})
            self.editable = False
            self.revision = 2
            self.etag = '"record-revision-2"'
            return response(202)
        if method == "GET" and path == "/api/files/metadata-edit/proof.bin":
            return response(200, headers={"Content-Type": "application/octet-stream"}, body=FILE_BYTES)
        return response(500, {"message": f"unhandled {method} {path}"})


def normalized_manifest(transport: MetadataEditTransport) -> dict[str, object]:
    before = metadata_before()
    after = metadata_after()
    public_metadata = transport._public()["metadata"]
    files = [
        {
            "name": "proof.bin",
            "size": len(FILE_BYTES),
            "md5": hashlib.md5(FILE_BYTES).hexdigest(),  # noqa: S324
            "sha256": hashlib.sha256(FILE_BYTES).hexdigest(),
        }
    ]
    return {
        "target": {
            "record_id": RECORD_ID,
            "concept_record_id": CONCEPT_ID,
            "doi": DOI,
            "concept_doi": CONCEPT_DOI,
            "before_revision": 1,
            "before_etag": '"record-revision-1"',
            "before_public_metadata_sha256": hashlib.sha256(
                zenodo._json_bytes(public_metadata)
            ).hexdigest(),
            "expected_after_revision": 2,
        },
        "metadata_before": before,
        "metadata_after": after,
        "metadata_before_sha256": hashlib.sha256(zenodo._json_bytes(before)).hexdigest(),
        "metadata_after_sha256": hashlib.sha256(zenodo._json_bytes(after)).hexdigest(),
        "files": files,
        "file_inventory_sha256": hashlib.sha256(zenodo._json_bytes(files)).hexdigest(),
    }


class ZenodoMetadataEditTests(unittest.TestCase):
    def client(self, transport: MetadataEditTransport) -> zenodo.ZenodoClient:
        return zenodo.ZenodoClient(
            TOKEN,
            "https://zenodo.org/api",
            transport,
            poll_attempts=3,
            poll_interval=0,
            sleeper=lambda _seconds: None,
        )

    def test_metadata_transition_is_narrow_and_preserves_title(self) -> None:
        before, after, changed = edit._validate_metadata_transition(
            metadata_before(),
            metadata_after(),
        )
        self.assertEqual(before["title"], after["title"])
        self.assertEqual(changed, ["description", "keywords", "notes"])

        changed_title = metadata_after()
        changed_title["title"] = "Different title"
        with self.assertRaisesRegex(zenodo.ZenodoError, "non-allowlisted field"):
            edit._validate_metadata_transition(metadata_before(), changed_title)

        changed_version = metadata_after()
        changed_version["version"] = "2.0.0"
        with self.assertRaisesRegex(zenodo.ZenodoError, "non-allowlisted field"):
            edit._validate_metadata_transition(metadata_before(), changed_version)

        reserved = metadata_after()
        reserved["prereserve_doi"] = True
        with self.assertRaisesRegex(zenodo.ZenodoError, "forbidden when editing"):
            edit._validate_metadata_transition(metadata_before(), reserved)

    def test_files_are_exact_sorted_immutable_inventory(self) -> None:
        files = [
            {
                "name": "proof.bin",
                "size": len(FILE_BYTES),
                "md5": hashlib.md5(FILE_BYTES).hexdigest(),  # noqa: S324
                "sha256": hashlib.sha256(FILE_BYTES).hexdigest(),
            }
        ]
        observed, digest = edit._validate_files(files)
        self.assertEqual(observed, files)
        self.assertEqual(digest, hashlib.sha256(zenodo._json_bytes(files)).hexdigest())

        reversed_files = [dict(files[0], name="z.bin"), dict(files[0], name="a.bin")]
        with self.assertRaisesRegex(zenodo.ZenodoError, "sorted by name"):
            edit._validate_files(reversed_files)

    def test_public_before_gate_binds_etag_revision_metadata_and_bytes(self) -> None:
        transport = MetadataEditTransport()
        client = self.client(transport)
        manifest = normalized_manifest(transport)
        snapshot = edit._verify_public(client, manifest, before=True)
        self.assertEqual(snapshot["revision"], 1)
        self.assertEqual(snapshot["etag"], '"record-revision-1"')
        self.assertIn(("GET", "/api/files/metadata-edit/proof.bin", None), transport.calls)

    def test_public_gate_rejects_etag_and_revision_drift(self) -> None:
        transport = MetadataEditTransport()
        client = self.client(transport)
        manifest = normalized_manifest(transport)
        manifest["target"]["before_etag"] = '"wrong"'  # type: ignore[index]
        with self.assertRaisesRegex(zenodo.ZenodoError, "before ETag changed"):
            edit._verify_public(client, manifest, before=True)

        transport = MetadataEditTransport()
        client = self.client(transport)
        manifest = normalized_manifest(transport)
        manifest["target"]["before_revision"] = 7  # type: ignore[index]
        with self.assertRaisesRegex(zenodo.ZenodoError, "revision changed"):
            edit._verify_public(client, manifest, before=True)

    def test_effect_changes_only_metadata_and_republishes_same_record(self) -> None:
        transport = MetadataEditTransport()
        client = self.client(transport)
        manifest = normalized_manifest(transport)
        phases: list[tuple[str, object | None]] = []

        before = edit._verify_public(client, manifest, before=True)
        self.assertEqual(before["revision"], 1)
        after = edit._execute_remote(
            client,
            manifest,
            lambda phase, snapshot: phases.append((phase, snapshot)),
        )

        self.assertEqual(
            [phase for phase, _snapshot in phases],
            ["edit_requested", "metadata_updated", "republish_requested", "public_verified"],
        )
        self.assertEqual(after["record_id"], RECORD_ID)
        self.assertEqual(after["revision"], 2)
        self.assertEqual(after["etag"], '"record-revision-2"')
        self.assertEqual(transport.file["checksum"], "md5:" + hashlib.md5(FILE_BYTES).hexdigest())  # noqa: S324
        mutating_calls = [(method, path) for method, path, _body in transport.calls if method in {"POST", "PUT", "DELETE"}]
        self.assertEqual(
            mutating_calls,
            [
                ("POST", f"/api/deposit/depositions/{RECORD_ID}/actions/edit"),
                ("PUT", f"/api/deposit/depositions/{RECORD_ID}"),
                ("POST", f"/api/deposit/depositions/{RECORD_ID}/actions/publish"),
            ],
        )
        self.assertFalse(any("/files/" in path for _method, path in mutating_calls))

    def test_exact_authorization_statement_remains_canonical(self) -> None:
        statement = publication._canonical_authorization_statement(
            "qikvrt-metadata-edit-auth-0123456789abcdef",
            "qikvrt-round-trip-metadata-edit-v1",
            "a" * 64,
            "b" * 64,
            "c" * 64,
        )
        self.assertEqual(
            statement,
            "AUTHORIZE_EXACT_UPLOAD "
            "authorization_id=qikvrt-metadata-edit-auth-0123456789abcdef "
            "publication_id=qikvrt-round-trip-metadata-edit-v1 "
            f"return_sha256={'a' * 64} metadata_sha256={'b' * 64} "
            f"machine_proof_sha256={'c' * 64}",
        )

    def test_metadata_specific_proof_and_v2_return_receipt_validate_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = pathlib.Path(raw_root)
            for relative in (
                proof_gate.POLICY_PATH,
                proof_gate.BUNDLE_SCHEMA_PATH,
                proof_gate.RETURN_SCHEMA_PATH,
                proof_gate.LEGACY_POLICY_PATH,
                proof_gate.LEGACY_BUNDLE_SCHEMA_PATH,
                proof_gate.LEGACY_RETURN_SCHEMA_PATH,
            ):
                target_path = root / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target_path)

            def write_json(relative: str, value: object) -> pathlib.Path:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8",
                )
                return path

            def identity(relative: str) -> dict[str, object]:
                data = (root / relative).read_bytes()
                return {
                    "path": relative,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "git_blob_sha": publication._git_blob_sha(data),
                }

            before_path = write_json("candidate/METADATA_BEFORE.json", metadata_before())
            after_path = write_json("candidate/METADATA_AFTER.json", metadata_after())
            del before_path, after_path
            before_identity = identity("candidate/METADATA_BEFORE.json")
            after_identity = identity("candidate/METADATA_AFTER.json")
            claim_id = "metadata-description-clarification-v1"
            reason = "Replace stale prepublication wording with current searchable metadata."
            notice_path = root / "candidate/CHANGE_NOTICE.md"
            notice_path.write_text(f"# Change\n\n{claim_id}: {reason}\n", encoding="utf-8")
            write_json("candidate/SOURCE.json", {"claim": "Owner-requested metadata clarification"})
            receipt = {
                "_license": {
                    "classification": "machine_readable_prepublication_return_receipt",
                    "copyright": "Copyright 2026 Ingolf Lohmann",
                    "license": "CC-BY-NC-ND-4.0",
                    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                    "rights_holder": "Ingolf Lohmann",
                },
                "schema": "qikvrt_prepublication_return_receipt_v2",
                "publication_id": "qikvrt-round-trip-metadata-edit-v1",
                "content_changed": True,
                "original_files": [
                    {
                        "path": before_identity["path"],
                        "bytes": before_identity["bytes"],
                        "sha256": before_identity["sha256"],
                        "git_blob_sha1": before_identity["git_blob_sha"],
                    }
                ],
                "candidate_files": [
                    {
                        "path": after_identity["path"],
                        "bytes": after_identity["bytes"],
                        "sha256": after_identity["sha256"],
                        "git_blob_sha1": after_identity["git_blob_sha"],
                    }
                ],
                "changed_claim_ids": [claim_id],
                "change_reasons": [
                    {
                        "claim_id": claim_id,
                        "reason": reason,
                        "original_sha256": before_identity["sha256"],
                        "corrected_sha256": after_identity["sha256"],
                        "exact_candidate_path": after_identity["path"],
                    }
                ],
                "change_notice_path": "candidate/CHANGE_NOTICE.md",
                "return": {
                    "candidate_returned_to_owner": True,
                    "owner_name": "Ingolf Lohmann",
                    "owner_type": "NATURAL_PERSON",
                    "return_channel": "offline test fixture",
                    "returned_at": "2026-08-12T10:00:00+02:00",
                    "visible_change_notice_returned": True,
                },
            }
            write_json("candidate/PREPUBLICATION_RETURN_RECEIPT.json", receipt)
            files = [
                {
                    "name": "proof.bin",
                    "size": len(FILE_BYTES),
                    "md5": hashlib.md5(FILE_BYTES).hexdigest(),  # noqa: S324
                    "sha256": hashlib.sha256(FILE_BYTES).hexdigest(),
                }
            ]
            file_inventory_sha256 = hashlib.sha256(zenodo._json_bytes(files)).hexdigest()
            target = {
                "record_id": RECORD_ID,
                "concept_record_id": CONCEPT_ID,
                "doi": DOI,
                "concept_doi": CONCEPT_DOI,
                "before_revision": 1,
                "before_etag": '"record-revision-1"',
                "before_public_metadata_sha256": "d" * 64,
                "expected_after_revision": 2,
            }
            bundle = {
                "_license": {
                    "classification": "machine_readable_proof_bundle",
                    "copyright": "Copyright 2026 Ingolf Lohmann",
                    "license": "CC-BY-NC-ND-4.0",
                    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                    "rights_holder": "Ingolf Lohmann",
                },
                "schema": edit.PROOF_SCHEMA,
                "policy": {
                    "id": proof_gate.POLICY_ID,
                    "path": proof_gate.POLICY_PATH,
                    "version": proof_gate.POLICY_VERSION,
                    "sha256": proof_gate.POLICY_SHA256,
                    "git_blob_sha1": proof_gate.POLICY_GIT_BLOB_SHA1,
                },
                "publication_id": "qikvrt-round-trip-metadata-edit-v1",
                "target": target,
                "metadata_before": before_identity,
                "metadata_after": after_identity,
                "file_inventory_sha256": file_inventory_sha256,
                "artifacts": [
                    {**identity("candidate/CHANGE_NOTICE.md"), "kind": "CHANGE_NOTICE"},
                    {
                        **identity("candidate/PREPUBLICATION_RETURN_RECEIPT.json"),
                        "kind": "RETURN_RECEIPT",
                    },
                    {**identity("candidate/SOURCE.json"), "kind": "SOURCE"},
                ],
                "claims": [
                    {
                        "claim_id": claim_id,
                        "statement": "The published description requires a metadata clarification.",
                        "classification": "SOURCE_BOUND",
                        "status": "BOUND",
                        "publication_wording": "SOURCE_ATTRIBUTED",
                        "scope": "Zenodo metadata for the bound record only.",
                        "proof_refs": [],
                        "evidence_refs": [],
                        "source_refs": ["candidate/SOURCE.json#claim"],
                    }
                ],
                "prepublication_return": {
                    "content_changed": True,
                    "candidate_returned_to_owner": True,
                    "receipt_path": "candidate/PREPUBLICATION_RETURN_RECEIPT.json",
                    "change_notice_path": "candidate/CHANGE_NOTICE.md",
                },
                "gates": {
                    "all_metadata_claims_dispositioned": True,
                    "all_references_resolve": True,
                    "metadata_candidate_frozen": True,
                    "changed_fields_allowlisted": True,
                    "title_unchanged": True,
                    "files_declared_immutable": True,
                    "prepublication_return_complete": True,
                },
                "completion_claims": {
                    "machine_proof_complete": True,
                    "metadata_edit_authorized": True,
                    "zenodo_file_upload_authorized": False,
                },
            }
            write_json("candidate/MACHINE_PROOF_BUNDLE.json", bundle)
            observed = edit._validate_proof(
                identity("candidate/MACHINE_PROOF_BUNDLE.json"),
                root,
                publication_id="qikvrt-round-trip-metadata-edit-v1",
                target=target,
                metadata_before_identity=before_identity,
                metadata_after_identity=after_identity,
                file_inventory_sha256=file_inventory_sha256,
            )
            self.assertTrue(observed["machine_proof_complete"])
            self.assertFalse(observed["zenodo_file_upload_authorized"])
            self.assertEqual(observed["claim_count"], 1)
            authorization_id = "qikvrt-round-trip-metadata-edit-auth-v1"
            metadata_sha256 = hashlib.sha256(
                zenodo._json_bytes(metadata_after())
            ).hexdigest()
            returned_identity = {
                key: observed["candidate_return_receipt"][key]
                for key in ("path", "bytes", "sha256", "git_blob_sha")
            }
            proof_identity = {
                key: observed[key]
                for key in ("path", "bytes", "sha256", "git_blob_sha")
            }
            statement = publication._canonical_authorization_statement(
                authorization_id,
                "qikvrt-round-trip-metadata-edit-v1",
                returned_identity["sha256"],
                metadata_sha256,
                proof_identity["sha256"],
            )
            principal = {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}
            authorization = {
                "_license": {
                    "classification": "owner_effect_authorization",
                    "copyright": "Copyright 2026 Ingolf Lohmann",
                    "license": "CC-BY-NC-ND-4.0",
                    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                    "rights_holder": "Ingolf Lohmann",
                },
                "schema": edit.AUTHORIZATION_SCHEMA,
                "authorization_id": authorization_id,
                "nonce": "e" * 64,
                "single_use": True,
                "single_use_scope": publication.SINGLE_USE_SCOPE,
                "principal": principal,
                "publication_id": "qikvrt-round-trip-metadata-edit-v1",
                "repository": publication.PRODUCTION_REPOSITORY,
                "source_head": "a" * 40,
                "target": target,
                "candidate_return_receipt": returned_identity,
                "canonical_metadata_sha256": metadata_sha256,
                "machine_proof": proof_identity,
                "file_inventory_sha256": file_inventory_sha256,
                "authorized_effects": list(edit.OWNER_AUTHORIZED_EFFECTS),
                "metadata_edit_evidence_path": "candidate/zenodo-metadata-edit.json",
                "authorization_event": {
                    "channel": "offline test fixture",
                    "authorized_at": "2026-08-12T10:01:00+02:00",
                    "decision": "AUTHORIZE_EXACT_UPLOAD",
                    "exact_statement": statement,
                    "statement_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
                    "principal": principal,
                    "candidate_return_receipt_sha256": returned_identity["sha256"],
                },
            }
            write_json("candidate/OWNER_ZENODO_AUTHORIZATION.json", authorization)
            normalized_authorization = edit._validate_authorization(
                identity("candidate/OWNER_ZENODO_AUTHORIZATION.json"),
                root,
                repository=publication.PRODUCTION_REPOSITORY,
                source_head="a" * 40,
                publication_id="qikvrt-round-trip-metadata-edit-v1",
                target=target,
                metadata_after=metadata_after(),
                machine_proof=observed,
                file_inventory_sha256=file_inventory_sha256,
                evidence_path=root / "candidate/zenodo-metadata-edit.json",
            )
            self.assertTrue(normalized_authorization["single_use"])
            self.assertTrue(
                normalized_authorization["remote_consumption_ref"].startswith(
                    publication.CONSUMPTION_REF_PREFIX
                )
            )
            manifest_value = {
                "schema": edit.SCHEMA,
                "state": edit.STATE,
                "confirm": edit.CONFIRM,
                "repository": publication.PRODUCTION_REPOSITORY,
                "source_head": "a" * 40,
                "publication_id": "qikvrt-round-trip-metadata-edit-v1",
                "target": target,
                "metadata_before": before_identity,
                "metadata_after": after_identity,
                "files": files,
                "machine_proof": identity("candidate/MACHINE_PROOF_BUNDLE.json"),
                "owner_authorization": identity("candidate/OWNER_ZENODO_AUTHORIZATION.json"),
                "evidence_path": "candidate/zenodo-metadata-edit.json",
            }
            manifest_path = write_json("candidate/metadata-edit-request.json", manifest_value)
            normalized_manifest_value = edit.load_manifest(manifest_path, root)
            self.assertEqual(
                normalized_manifest_value["changed_fields"],
                ["description", "keywords", "notes"],
            )
            self.assertEqual(
                normalized_manifest_value["owner_authorization"]["authorization_id"],
                authorization_id,
            )

    def test_source_has_no_file_mutation_helper_call(self) -> None:
        source = (ROOT / "tools/qikvrt_zenodo_metadata_edit.py").read_text(encoding="utf-8")
        self.assertNotIn(".delete_all_files(", source)
        self.assertNotIn(".upload_files(", source)
        self.assertNotIn("actions/newversion", source)
        self.assertNotIn('"POST", "/api/deposit/depositions"', source)

    def test_manifest_schema_and_capability_are_parseable_and_bound(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "policy/qikvrt-zenodo-published-metadata-edit-manifest-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        capability = json.loads(
            (
                ROOT
                / "runtime/capabilities/ZENODO_METADATA_EDIT_CAPABILITY.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["schema"]["const"], edit.SCHEMA)
        self.assertEqual(schema["properties"]["confirm"]["const"], edit.CONFIRM)
        self.assertEqual(capability["implementation"], "tools/qikvrt_zenodo_metadata_edit.py")
        self.assertEqual(
            capability["manifest_schema_path"],
            "policy/qikvrt-zenodo-published-metadata-edit-manifest-v1.schema.json",
        )


if __name__ == "__main__":
    unittest.main()
