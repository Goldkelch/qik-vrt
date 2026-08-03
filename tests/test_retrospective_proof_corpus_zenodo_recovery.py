#!/usr/bin/env python3
"""Unit tests for the dedicated retrospective proof-corpus recovery path."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import inspect
import os
import pathlib
import unittest
import urllib.request
from unittest import mock
from typing import Any, Mapping

from tools import qikvrt_retrospective_proof_corpus_zenodo_recovery as recovery


class SimulatedCrash(RuntimeError):
    pass


class MemoryCheckpointPort:
    def __init__(self) -> None:
        self.refs: dict[str, recovery.CheckpointCandidate] = {
            recovery.PUBLICATION_REF: recovery.CheckpointCandidate(
                EXECUTION_HEAD,
                recovery.CONTROL_BASE_HEAD,
                "",
                b"",
            )
        }
        self.mutations: list[tuple[str, str | None, str]] = []
        self.reads: list[str] = []
        self.ambiguous_next = False
        self.drop_next = False
        self.wrong_readback_next = False

    def prepare_commit(
        self, parent_sha: str, relative_path: str, evidence_bytes: bytes
    ) -> recovery.CheckpointCandidate:
        sha = hashlib.sha1(  # noqa: S324 - fake Git object identity
            parent_sha.encode() + relative_path.encode() + evidence_bytes
        ).hexdigest()
        return recovery.CheckpointCandidate(
            sha, parent_sha, relative_path, evidence_bytes
        )

    def mutate_ref_once(
        self,
        ref: str,
        expected_old_sha: str | None,
        candidate_value: recovery.CheckpointCandidate,
    ) -> None:
        self.mutations.append((ref, expected_old_sha, candidate_value.commit_sha))
        current = self.refs.get(ref)
        current_sha = None if current is None else current.commit_sha
        if current_sha != expected_old_sha:
            raise recovery.CorpusRecoveryError("fake expected-old mismatch")
        if not self.drop_next:
            self.refs[ref] = candidate_value
        self.drop_next = False
        if self.ambiguous_next:
            self.ambiguous_next = False
            raise recovery.AmbiguousMutation("fake ambiguous ref")

    def read_ref_once(
        self, ref: str
    ) -> recovery.CheckpointCandidate | None:
        self.reads.append(ref)
        if self.wrong_readback_next:
            self.wrong_readback_next = False
            return None
        return self.refs.get(ref)


class FakeConsumptionPort:
    def __init__(self, *, apply: bool = True, ambiguous: bool = False) -> None:
        self.apply = apply
        self.ambiguous = ambiguous
        self.value: recovery.ConsumptionIdentity | None = None
        self.create_calls = 0
        self.read_calls = 0

    def create_once(self, expected: recovery.ConsumptionIdentity) -> None:
        self.create_calls += 1
        if self.apply:
            self.value = expected
        if self.ambiguous:
            raise recovery.AmbiguousMutation("fake consumption ambiguity")

    def read_once(self, ref: str) -> recovery.ConsumptionIdentity | None:
        self.read_calls += 1
        if self.value is not None and self.value.ref != ref:
            raise AssertionError("wrong ref")
        return self.value


class FakeCreate:
    def __init__(self, contract: recovery.FrozenUploadContract) -> None:
        self.contract = contract
        self.record = recovery.RecordIdentity(21700001, "10.5281/zenodo.21700001")
        self.snapshots: list[recovery.DraftSnapshot] = []
        self.create_calls = 0
        self.read_calls = 0
        self.apply = True
        self.ambiguous = False
        self.crash_after_apply = False

    def empty(self) -> recovery.DraftSnapshot:
        return recovery.DraftSnapshot(
            self.record, self.contract.metadata_sha256, (), True
        )

    def create_once(self, metadata_sha256: str) -> Any:
        self.create_calls += 1
        if metadata_sha256 != self.contract.metadata_sha256:
            raise AssertionError("wrong metadata")
        if self.apply:
            self.snapshots = [self.empty()]
        if self.crash_after_apply:
            raise SimulatedCrash("create response lost")
        if self.ambiguous:
            raise recovery.AmbiguousMutation("create response ambiguous")
        return self.record

    def read_create_once(self, hint: Any | None) -> list[recovery.DraftSnapshot]:
        del hint
        self.read_calls += 1
        return list(self.snapshots)


class FakeUpload:
    def __init__(
        self,
        contract: recovery.FrozenUploadContract,
        record: recovery.RecordIdentity,
    ) -> None:
        self.contract = contract
        self.record = record
        self.files: list[recovery.ServerFile] = []
        self.upload_calls = 0
        self.read_calls = 0
        self.apply = True
        self.ambiguous = False
        self.crash_after_apply = False

    def upload_once(
        self, record: recovery.RecordIdentity, entry: recovery.UploadIdentity
    ) -> None:
        self.upload_calls += 1
        if record != self.record:
            raise AssertionError("wrong record")
        if any(item.name == entry.name for item in self.files):
            raise AssertionError("reupload attempted")
        if self.apply:
            self.files.append(
                recovery.ServerFile(
                    entry.name, entry.size, entry.md5, entry.sha256
                )
            )
        if self.crash_after_apply:
            raise SimulatedCrash("upload response lost")
        if self.ambiguous:
            raise recovery.AmbiguousMutation("upload response ambiguous")

    def read_draft_once(
        self, record: recovery.RecordIdentity
    ) -> recovery.DraftSnapshot:
        self.read_calls += 1
        return recovery.DraftSnapshot(
            record,
            self.contract.metadata_sha256,
            tuple(reversed(self.files)),
            True,
        )


class FakePublish:
    def __init__(self) -> None:
        self.calls = 0
        self.ambiguous = False
        self.crash_after_apply = False

    def publish_once(self, record: recovery.RecordIdentity) -> None:
        del record
        self.calls += 1
        if self.crash_after_apply:
            raise SimulatedCrash("publish response lost")
        if self.ambiguous:
            raise recovery.AmbiguousMutation("publish response ambiguous")


class FakePublic:
    def __init__(self, snapshot: recovery.PublicSnapshot | None) -> None:
        self.snapshot = snapshot
        self.read_calls = 0

    def read_public_once(
        self, record: recovery.RecordIdentity
    ) -> recovery.PublicSnapshot | None:
        self.read_calls += 1
        if self.snapshot is not None and self.snapshot.record != record:
            raise AssertionError("wrong public record")
        return self.snapshot


EXECUTION_HEAD = "a" * 40
MANIFEST_SHA = "b" * 64
TAG_OBJECT = "c" * 40


class FakeDownloadResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body


class FakeZenodoDownloadClient:
    base_url = "https://zenodo.org/api"

    def __init__(self, contents: Mapping[str, bytes]) -> None:
        self.contents = dict(contents)
        self.downloads: list[str] = []

    @staticmethod
    def _server_files(value: Mapping[str, Any]) -> list[dict[str, Any]]:
        return recovery.zenodo.ZenodoClient._server_files(value)

    @staticmethod
    def _server_file_name(value: Mapping[str, Any]) -> str:
        return recovery.zenodo.ZenodoClient._server_file_name(value)

    def request(self, method: str, url: str, **_kwargs: Any) -> tuple[Any, None]:
        if method != "GET" or url not in self.contents:
            raise AssertionError("unexpected fake Zenodo request")
        self.downloads.append(url)
        return FakeDownloadResponse(self.contents[url]), None


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = recovery.load_frozen_contract()
        cls.key = recovery.publish._authorization_consumption_key(
            recovery.REPOSITORY,
            recovery.AUTHORIZATION_ID,
            recovery.PUBLICATION_ID,
            recovery.STATEMENT_SHA256,
        )["value"]
        cls.context = recovery.make_context(
            EXECUTION_HEAD, MANIFEST_SHA, cls.key, TAG_OBJECT
        )

    def controller(
        self,
        port: MemoryCheckpointPort | None = None,
        *,
        history: list[recovery.PersistedCheckpoint] | None = None,
        final: recovery.PersistedCheckpoint | None = None,
    ) -> recovery.RecoveryController:
        port = port or MemoryCheckpointPort()
        history = history or []
        recovery_head = history[-1].commit_sha if history else None
        publication_head = (
            final.commit_sha if final is not None else EXECUTION_HEAD
        )
        return recovery.RecoveryController(
            self.contract,
            self.context,
            port,
            history=history,
            recovery_head=recovery_head,
            publication_head=publication_head,
            final_checkpoint=final,
        )

    @staticmethod
    def persisted(
        history: list[recovery.PersistedCheckpoint],
    ) -> list[recovery.PersistedCheckpoint]:
        return list(history)

    def create_controller(
        self,
    ) -> tuple[
        recovery.RecoveryController,
        MemoryCheckpointPort,
        FakeCreate,
    ]:
        port = MemoryCheckpointPort()
        controller = self.controller(port)
        controller.bootstrap_authorization_consumed()
        remote = FakeCreate(self.contract)
        controller.create_record(remote)
        return controller, port, remote

    def public_snapshot(
        self,
        record: recovery.RecordIdentity,
        *,
        transport: recovery.PublicTransportAttestation | None = None,
    ) -> recovery.PublicSnapshot:
        return recovery.PublicSnapshot(
            record,
            "10.5281/zenodo.21700000",
            self.contract.metadata_sha256,
            tuple(
                recovery.ServerFile(
                    entry.name, entry.size, entry.md5, entry.sha256
                )
                for entry in reversed(self.contract.entries)
            ),
            transport or recovery.PublicTransportAttestation(),
        )

    def generic_evidence(
        self, snapshot: recovery.PublicSnapshot
    ) -> dict[str, Any]:
        record = snapshot.record
        return {
            "schema": recovery.GENERIC_EVIDENCE_SCHEMA,
            "state": "published",
            "phase": "public_verified",
            "manifest_path": recovery.MANIFEST_RELATIVE,
            "manifest_sha256": MANIFEST_SHA,
            "machine_proof": {"bound": True},
            "owner_authorization": {"bound": True},
            "remote_consumption": {
                "remote": "github_git_data_api",
                "api_origin": recovery.GITHUB_API_BASE,
                "repository": recovery.REPOSITORY,
                "ref": self.context.consumption.ref,
                "tag_object": TAG_OBJECT,
                "object_type": "tag",
                "execution_head": EXECUTION_HEAD,
                "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
                "recovery_mode": "EXISTING_EXACT_REF_NO_CREATE",
            },
            "repository": recovery.REPOSITORY,
            "repository_commit": EXECUTION_HEAD,
            "source_head": recovery.SOURCE_HEAD,
            "binding": {
                "schema": recovery.publish.CONSUMPTION_KEY_SCHEMA,
                "repository": recovery.REPOSITORY,
                "authorization_id": recovery.AUTHORIZATION_ID,
                "publication_id": recovery.PUBLICATION_ID,
                "statement_sha256": recovery.STATEMENT_SHA256,
                "consumption_key": {"value": self.key},
                "manifest_sha256": MANIFEST_SHA,
                "source_head": recovery.SOURCE_HEAD,
                "execution_head": EXECUTION_HEAD,
            },
            "governance_boundaries": list(recovery.publish.GOVERNANCE_BOUNDARIES),
            "recovery": recovery.publish._recovery_flags("public_verified"),
            "record_id": record.record_id,
            "doi": record.doi,
            "title": self.contract.title,
            "version": self.contract.version,
            "files": [entry.generic_file() for entry in self.contract.entries],
            "conceptdoi": snapshot.conceptdoi,
            "record_url": f"https://zenodo.org/records/{record.record_id}",
        }

    def advance_all_uploads(
        self,
        controller: recovery.RecoveryController,
        remote: FakeUpload,
    ) -> None:
        for _index in range(recovery.EXPECTED_UPLOADS):
            controller.upload_next(remote)

    @staticmethod
    def synthetic_draft_fixture() -> tuple[
        recovery.FrozenUploadContract,
        dict[str, Any],
        dict[str, bytes],
    ]:
        payloads = (b"alpha", b"bravo", b"charlie")
        entries: list[recovery.UploadIdentity] = []
        files: list[dict[str, Any]] = []
        contents: dict[str, bytes] = {}
        for index, raw in enumerate(payloads):
            name = f"synthetic-{index}.bin"
            url = f"https://zenodo.org/api/files/{name}"
            md5 = hashlib.md5(raw).hexdigest()  # noqa: S324 - transport fixture
            entries.append(
                recovery.UploadIdentity(
                    index,
                    "fixture/" + name,
                    name,
                    len(raw),
                    md5,
                    hashlib.sha256(raw).hexdigest(),
                    recovery.git_blob_sha1(raw),
                )
            )
            files.append(
                {
                    "filename": name,
                    "filesize": len(raw),
                    "checksum": "md5:" + md5,
                    "links": {"download": url},
                }
            )
            contents[url] = raw
        contract = recovery.FrozenUploadContract(
            tuple(entries),
            "0" * 64,
            "1" * 64,
            sum(map(len, payloads)),
            "2" * 64,
            "Synthetic",
            "1",
        )
        draft = {
            "id": 21700001,
            "doi": "10.5281/zenodo.21700001",
            "metadata": {"title": "Synthetic"},
            "submitted": False,
            "state": "inprogress",
            "files": files,
        }
        return contract, draft, contents

    def test_frozen_contract_is_exact_ordered_65(self) -> None:
        self.assertEqual(len(self.contract.entries), 65)
        self.assertEqual(self.contract.total_bytes, 221_808_115)
        self.assertEqual(
            self.contract.canonical_sha256,
            "3965b4167094ff47de60fc32023ac74ea1598148ab381885be8da3db4c427609",
        )
        self.assertEqual(
            [entry.index for entry in self.contract.entries], list(range(65))
        )
        self.assertEqual(
            len({entry.name for entry in self.contract.entries}), 65
        )

    def test_strict_json_rejects_duplicates_nonfinite_surrogates_and_shape(self) -> None:
        for raw in (
            b'{"a":1,"a":2}',
            b'{"a":NaN}',
            b'{"a":1e9999}',
            b'{"a":-1e9999}',
            b'{"a":"\\ud800"}',
            b"[]",
        ):
            with self.subTest(raw=raw), self.assertRaises(
                recovery.CorpusRecoveryError
            ):
                recovery.strict_json_bytes(raw, "test")

    def test_fresh_zenodo_adapter_verifies_full_prefix_then_only_unseen(self) -> None:
        contract, draft, contents = self.synthetic_draft_fixture()
        client = FakeZenodoDownloadClient(contents)
        adapter = recovery.ProductionZenodoAdapter(
            client, "token", contract, {"title": "Synthetic"}
        )

        two_files = copy.deepcopy(draft)
        two_files["files"] = two_files["files"][:2]
        adapter._draft_snapshot(two_files, verify_unseen_prefix=True)
        self.assertEqual(client.downloads, list(contents)[:2])

        adapter._draft_snapshot(two_files, verify_unseen_prefix=True)
        self.assertEqual(client.downloads, list(contents)[:2])

        adapter._draft_snapshot(draft, verify_unseen_prefix=True)
        self.assertEqual(client.downloads, list(contents))

        fresh_client = FakeZenodoDownloadClient(contents)
        fresh = recovery.ProductionZenodoAdapter(
            fresh_client, "token", contract, {"title": "Synthetic"}
        )
        fresh._draft_snapshot(two_files, verify_unseen_prefix=True)
        self.assertEqual(fresh_client.downloads, list(contents)[:2])

        corrupt_contents = dict(contents)
        corrupt_contents[list(contents)[0]] = b"ALPHA"
        corrupt = recovery.ProductionZenodoAdapter(
            FakeZenodoDownloadClient(corrupt_contents),
            "token",
            contract,
            {"title": "Synthetic"},
        )
        with self.assertRaises(recovery.CorpusRecoveryError):
            corrupt._draft_snapshot(two_files, verify_unseen_prefix=True)

    def test_remote_consumption_preserves_mode_and_gets_new_tag_exactly(self) -> None:
        expected_ref = self.context.consumption.ref
        manifest = {"owner_authorization": {"remote_consumption_ref": expected_ref}}

        def observed(mode: str) -> dict[str, Any]:
            return {
                "remote": "github_git_data_api",
                "api_origin": recovery.GITHUB_API_BASE,
                "repository": recovery.REPOSITORY,
                "ref": expected_ref,
                "tag_object": TAG_OBJECT,
                "object_type": "tag",
                "execution_head": EXECUTION_HEAD,
                "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
                "recovery_mode": mode,
            }

        with (
            mock.patch.object(
                recovery.publish,
                "_acquire_remote_consumption_lock",
                return_value=observed("NEWLY_CREATED_REF"),
            ),
            mock.patch.object(
                recovery.publish,
                "_github_api_request",
                return_value=(200, {"exact": True}),
            ) as tag_get,
            mock.patch.object(
                recovery.publish,
                "_expected_consumption_tag",
                return_value={"expected": True},
            ),
            mock.patch.object(
                recovery.publish, "_validate_github_tag_response"
            ) as validate_tag,
        ):
            value = recovery._canonical_remote_consumption(
                manifest, EXECUTION_HEAD, "github-token"
            )
        self.assertEqual(value["recovery_mode"], "NEWLY_CREATED_REF")
        tag_get.assert_called_once_with(
            "GET",
            "/repos/Goldkelch/qik-vrt/git/tags/" + TAG_OBJECT,
            "github-token",
            accept=(200, 404),
        )
        validate_tag.assert_called_once_with(
            {"exact": True}, {"expected": True}, TAG_OBJECT
        )

        with (
            mock.patch.object(
                recovery.publish,
                "_acquire_remote_consumption_lock",
                return_value=observed("EXISTING_EXACT_REF_NO_CREATE"),
            ),
            mock.patch.object(recovery.publish, "_github_api_request") as tag_get,
        ):
            value = recovery._canonical_remote_consumption(
                manifest, EXECUTION_HEAD, "github-token"
            )
        self.assertEqual(
            value["recovery_mode"], "EXISTING_EXACT_REF_NO_CREATE"
        )
        tag_get.assert_not_called()

        for bad in (observed("WRONG"), {**observed("NEWLY_CREATED_REF"), "extra": 1}):
            with (
                self.subTest(bad=bad),
                mock.patch.object(
                    recovery.publish,
                    "_acquire_remote_consumption_lock",
                    return_value=bad,
                ),
                self.assertRaises(recovery.CorpusRecoveryError),
            ):
                recovery._canonical_remote_consumption(
                    manifest, EXECUTION_HEAD, "github-token"
                )

    def test_journal_roundtrip_and_unknown_key_fail_closed(self) -> None:
        value = recovery.make_journal(
            self.contract,
            self.context,
            phase="authorization_consumed",
            sequence=0,
        )
        raw = recovery.journal_bytes(value)
        self.assertEqual(
            recovery.journal_from_bytes(raw, self.contract, self.context), value
        )
        tampered = dict(value)
        tampered["unexpected"] = True
        with self.assertRaises(recovery.CorpusRecoveryError):
            recovery.validate_journal(tampered, self.contract, self.context)
        with self.assertRaises(recovery.CorpusRecoveryError):
            recovery.journal_from_bytes(
                recovery.canonical_json_bytes(value), self.contract, self.context
            )

    def test_consumption_is_one_mutation_one_readback_even_if_ambiguous(self) -> None:
        port = FakeConsumptionPort(ambiguous=True)
        expected = self.context.consumption
        self.assertEqual(
            recovery.consume_authorization_once(port, expected), expected
        )
        self.assertEqual((port.create_calls, port.read_calls), (1, 1))
        missing = FakeConsumptionPort(apply=False, ambiguous=True)
        with self.assertRaises(recovery.CorpusRecoveryError):
            recovery.consume_authorization_once(missing, expected)
        self.assertEqual((missing.create_calls, missing.read_calls), (1, 1))

    def test_checkpoint_ambiguous_applied_is_accepted_without_retry(self) -> None:
        port = MemoryCheckpointPort()
        port.ambiguous_next = True
        controller = self.controller(port)
        controller.bootstrap_authorization_consumed()
        self.assertEqual(controller.phase, "authorization_consumed")
        self.assertEqual(len(port.mutations), 1)
        self.assertEqual(len(port.reads), 1)

    def test_checkpoint_wrong_readback_blocks_without_retry(self) -> None:
        port = MemoryCheckpointPort()
        port.wrong_readback_next = True
        controller = self.controller(port)
        with self.assertRaises(recovery.CorpusRecoveryError):
            controller.bootstrap_authorization_consumed()
        self.assertEqual(len(port.mutations), 1)
        self.assertEqual(len(port.reads), 1)

    def test_create_normal_and_ambiguous_have_one_call_and_one_readback(self) -> None:
        for ambiguous in (False, True):
            with self.subTest(ambiguous=ambiguous):
                controller = self.controller()
                controller.bootstrap_authorization_consumed()
                remote = FakeCreate(self.contract)
                remote.ambiguous = ambiguous
                controller.create_record(remote)
                self.assertEqual(controller.phase, "record_created")
                self.assertEqual((remote.create_calls, remote.read_calls), (1, 1))

    def test_crashed_create_restores_get_only(self) -> None:
        port = MemoryCheckpointPort()
        controller = self.controller(port)
        controller.bootstrap_authorization_consumed()
        remote = FakeCreate(self.contract)
        remote.crash_after_apply = True
        with self.assertRaises(SimulatedCrash):
            controller.create_record(remote)
        history = self.persisted(controller.history)
        restored = self.controller(port, history=history)
        before = remote.create_calls
        restored.reconcile_create_requested(remote)
        self.assertEqual(remote.create_calls, before)
        self.assertEqual(restored.phase, "record_created")

    def test_restored_create_absent_or_multiple_blocks_without_create(self) -> None:
        port = MemoryCheckpointPort()
        controller = self.controller(port)
        controller.bootstrap_authorization_consumed()
        with self.assertRaises(SimulatedCrash):
            controller.create_record(
                FakeCreate(self.contract),
                after_intent=lambda: (_ for _ in ()).throw(SimulatedCrash()),
            )
        for count in (0, 2):
            remote = FakeCreate(self.contract)
            remote.snapshots = [remote.empty() for _ in range(count)]
            restored = self.controller(port, history=list(controller.history))
            with self.assertRaises(recovery.CorpusRecoveryError):
                restored.reconcile_create_requested(remote)
            self.assertEqual(remote.create_calls, 0)

    def test_upload_prefix_accepts_order_independent_exact_server_set(self) -> None:
        controller, _port, create = self.create_controller()
        remote = FakeUpload(self.contract, create.record)
        controller.upload_next(remote)
        controller.upload_next(remote)
        self.assertEqual(remote.upload_calls, 2)
        self.assertEqual(remote.read_calls, 2)
        self.assertEqual(
            controller.values[-1]["preparation"], recovery.observed_preparation(2)
        )

    def test_ambiguous_upload_applied_advances_once(self) -> None:
        controller, _port, create = self.create_controller()
        remote = FakeUpload(self.contract, create.record)
        remote.ambiguous = True
        controller.upload_next(remote)
        self.assertEqual(remote.upload_calls, 1)
        self.assertEqual(len(remote.files), 1)
        self.assertEqual(remote.read_calls, 1)

    def test_crashed_upload_restores_get_only_and_never_reuploads(self) -> None:
        controller, port, create = self.create_controller()
        remote = FakeUpload(self.contract, create.record)
        remote.crash_after_apply = True
        with self.assertRaises(SimulatedCrash):
            controller.upload_next(remote)
        restored = self.controller(port, history=list(controller.history))
        before = remote.upload_calls
        restored.reconcile_upload_intent(remote)
        self.assertEqual(remote.upload_calls, before)
        self.assertEqual(
            restored.values[-1]["preparation"], recovery.observed_preparation(1)
        )

    def test_restored_upload_absent_blocks_without_retry(self) -> None:
        controller, port, create = self.create_controller()
        remote = FakeUpload(self.contract, create.record)
        with self.assertRaises(SimulatedCrash):
            controller.upload_next(
                remote,
                after_intent=lambda: (_ for _ in ()).throw(SimulatedCrash()),
            )
        restored = self.controller(port, history=list(controller.history))
        with self.assertRaises(recovery.CorpusRecoveryError):
            restored.reconcile_upload_intent(remote)
        self.assertEqual(remote.upload_calls, 0)

    def test_prefix_gap_extra_and_wrong_bytes_are_rejected(self) -> None:
        record = recovery.RecordIdentity(21700001, "10.5281/zenodo.21700001")
        first, second = self.contract.entries[:2]
        bad_sets = (
            (
                recovery.ServerFile(
                    second.name, second.size, second.md5, second.sha256
                ),
            ),
            (
                recovery.ServerFile(
                    first.name, first.size + 1, first.md5, first.sha256
                ),
            ),
            (
                recovery.ServerFile(
                    "unexpected.bin", first.size, first.md5, first.sha256
                ),
            ),
        )
        for files in bad_sets:
            snapshot = recovery.DraftSnapshot(
                record, self.contract.metadata_sha256, files, True
            )
            with self.subTest(files=files), self.assertRaises(
                recovery.CorpusRecoveryError
            ):
                recovery.exact_prefix_count(snapshot, self.contract, record)

    def test_all_65_uploads_have_bounded_prefix_chain_and_prepared(self) -> None:
        controller, _port, create = self.create_controller()
        remote = FakeUpload(self.contract, create.record)
        self.advance_all_uploads(controller, remote)
        self.assertEqual(len(remote.files), 65)
        self.assertEqual(len(controller.history), 133)
        controller.mark_prepared()
        self.assertEqual(controller.phase, "prepared")
        self.assertEqual(len(controller.history), 134)
        with self.assertRaises(recovery.CorpusRecoveryError):
            controller.upload_next(remote)

    def test_restored_complete_prefix_is_get_verified_before_prepare_and_publish(self) -> None:
        controller, port, create = self.create_controller()
        upload = FakeUpload(self.contract, create.record)
        self.advance_all_uploads(controller, upload)
        restored = self.controller(port, history=list(controller.history))
        before = upload.read_calls
        recovery._verify_complete_draft_prefix(restored, upload)
        self.assertEqual(upload.read_calls, before + 1)

        restored.mark_prepared()
        prepared = self.controller(port, history=list(restored.history))
        recovery._verify_complete_draft_prefix(prepared, upload)
        self.assertEqual(upload.read_calls, before + 2)

        upload.files.pop()
        with self.assertRaisesRegex(
            recovery.CorpusRecoveryError, "exact 65-file prefix"
        ):
            recovery._verify_complete_draft_prefix(prepared, upload)

    def test_public_transport_and_exact_files_are_fail_closed(self) -> None:
        record = recovery.RecordIdentity(21700001, "10.5281/zenodo.21700001")
        good = self.public_snapshot(record)
        recovery.validate_public_snapshot(good, self.contract, record)
        bad_transport = dataclasses.replace(
            good,
            transport=dataclasses.replace(good.transport, proxy_handler="ENABLED"),
        )
        with self.assertRaises(recovery.CorpusRecoveryError):
            recovery.validate_public_snapshot(
                bad_transport, self.contract, record
            )
        with self.assertRaises(recovery.CorpusRecoveryError):
            recovery.validate_public_snapshot(
                dataclasses.replace(good, files=good.files[:-1]),
                self.contract,
                record,
            )

    def test_publish_normal_persists_generic_v2_final(self) -> None:
        controller, port, create = self.create_controller()
        upload = FakeUpload(self.contract, create.record)
        self.advance_all_uploads(controller, upload)
        controller.mark_prepared()
        snapshot = self.public_snapshot(create.record)
        public = FakePublic(snapshot)
        mutation = FakePublish()
        controller.publish_once(
            mutation,
            public,
            self.generic_evidence,
            lambda value: value,
        )
        self.assertEqual(controller.phase, "public_verified")
        self.assertEqual((mutation.calls, public.read_calls), (1, 1))
        self.assertIsNotNone(controller.final_checkpoint)
        self.assertEqual(
            controller.final_checkpoint.relative_path, recovery.EVIDENCE_RELATIVE
        )
        self.assertEqual(len(controller.history), 135)
        self.assertIn(recovery.PUBLICATION_REF, port.refs)

    def test_crashed_publish_restores_anonymous_get_only(self) -> None:
        controller, port, create = self.create_controller()
        upload = FakeUpload(self.contract, create.record)
        self.advance_all_uploads(controller, upload)
        controller.mark_prepared()
        mutation = FakePublish()
        mutation.crash_after_apply = True
        snapshot = self.public_snapshot(create.record)
        with self.assertRaises(SimulatedCrash):
            controller.publish_once(
                mutation,
                FakePublic(snapshot),
                self.generic_evidence,
                lambda value: value,
            )
        restored = self.controller(port, history=list(controller.history))
        before = mutation.calls
        restored.reconcile_publish_requested(
            FakePublic(snapshot), self.generic_evidence, lambda value: value
        )
        self.assertEqual(mutation.calls, before)
        self.assertEqual(restored.phase, "public_verified")

    def test_final_rerun_preserves_historical_new_consumption_mode(self) -> None:
        controller, _port, create = self.create_controller()
        upload = FakeUpload(self.contract, create.record)
        self.advance_all_uploads(controller, upload)
        controller.mark_prepared()
        snapshot = self.public_snapshot(create.record)

        def new_mode(value: recovery.PublicSnapshot) -> dict[str, Any]:
            evidence = self.generic_evidence(value)
            evidence["remote_consumption"]["recovery_mode"] = "NEWLY_CREATED_REF"
            return evidence

        controller.publish_once(
            FakePublish(),
            FakePublic(snapshot),
            new_mode,
            lambda value: value,
        )
        final = controller.final_checkpoint
        self.assertIsNotNone(final)
        assert final is not None
        persisted = recovery.strict_json_bytes(
            final.evidence_bytes, "persisted final"
        )
        self.assertEqual(
            persisted["remote_consumption"]["recovery_mode"],
            "NEWLY_CREATED_REF",
        )

        verified = recovery._verify_final_controller(
            controller,
            FakePublic(snapshot),  # type: ignore[arg-type]
            self.generic_evidence,
            lambda value: value,
        )
        self.assertEqual(
            verified["remote_consumption"]["recovery_mode"],
            "NEWLY_CREATED_REF",
        )

    def test_generic_final_unknown_key_or_wrong_files_is_rejected(self) -> None:
        record = recovery.RecordIdentity(21700001, "10.5281/zenodo.21700001")
        snapshot = self.public_snapshot(record)
        good = self.generic_evidence(snapshot)
        recovery.validate_generic_public_evidence(
            good, self.contract, self.context, snapshot
        )
        for mutate in (
            lambda value: value.update({"unexpected": True}),
            lambda value: value.__setitem__("files", value["files"][:-1]),
            lambda value: value.__setitem__("phase", "publish_requested"),
        ):
            bad = copy.deepcopy(good)
            mutate(bad)
            with self.assertRaises(recovery.CorpusRecoveryError):
                recovery.validate_generic_public_evidence(
                    bad, self.contract, self.context, snapshot
                )

    def test_final_checkpoint_requires_publish_requested_parent(self) -> None:
        controller, _port, _create = self.create_controller()
        parent = controller.history[-1]
        final = recovery.PersistedCheckpoint(
            "d" * 40,
            parent.commit_sha,
            recovery.EVIDENCE_RELATIVE,
            b"{}\n",
        )
        with self.assertRaisesRegex(
            recovery.CorpusRecoveryError, "not publish_requested"
        ):
            recovery.validate_ref_state(
                controller.history,
                self.context,
                parent.commit_sha,
                final.commit_sha,
                final,
            )

    def test_exact_execution_head_binds_branch_name_and_sole_parent(self) -> None:
        environment = {
            "GITHUB_SHA": EXECUTION_HEAD,
            "GITHUB_REPOSITORY": recovery.REPOSITORY,
            "GITHUB_REF": recovery.PUBLICATION_REF,
            "GITHUB_REF_NAME": recovery.PUBLICATION_REF.removeprefix(
                "refs/heads/"
            ),
        }

        def exact_git(*arguments: str) -> str:
            if arguments[0] == "rev-parse":
                return EXECUTION_HEAD
            if arguments[0] == "rev-list":
                return EXECUTION_HEAD + " " + recovery.CONTROL_BASE_HEAD
            raise AssertionError("unexpected Git gate")

        with (
            mock.patch.dict(os.environ, environment, clear=True),
            mock.patch.object(recovery, "_git_text", side_effect=exact_git),
        ):
            self.assertEqual(recovery._exact_execution_head(), EXECUTION_HEAD)

        for key, bad_value in (
            ("GITHUB_REF", "refs/heads/main"),
            ("GITHUB_REF_NAME", "main"),
        ):
            bad_environment = dict(environment)
            bad_environment[key] = bad_value
            with (
                self.subTest(key=key),
                mock.patch.dict(os.environ, bad_environment, clear=True),
                mock.patch.object(recovery, "_git_text", side_effect=exact_git),
                self.assertRaises(recovery.CorpusRecoveryError),
            ):
                recovery._exact_execution_head()

        def wrong_parent(*arguments: str) -> str:
            if arguments[0] == "rev-parse":
                return EXECUTION_HEAD
            return EXECUTION_HEAD + " " + ("e" * 40)

        with (
            mock.patch.dict(os.environ, environment, clear=True),
            mock.patch.object(recovery, "_git_text", side_effect=wrong_parent),
            self.assertRaises(recovery.CorpusRecoveryError),
        ):
            recovery._exact_execution_head()

    def test_missing_publication_ref_blocks_restore_and_cannot_be_created(self) -> None:
        class MissingRefAPI:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str]] = []

            def request(
                self, method: str, path: str, **_kwargs: Any
            ) -> tuple[int, dict[str, Any]]:
                self.calls.append((method, path))
                return 404, {}

        api = MissingRefAPI()
        port = recovery.GitHubCheckpointPort(
            api, EXECUTION_HEAD, "2026-08-03T00:00:00Z"
        )
        with self.assertRaisesRegex(
            recovery.CorpusRecoveryError, "publication ref is absent"
        ):
            port.restore(self.contract, self.context)
        self.assertEqual(len(api.calls), 2)
        self.assertTrue(all(method == "GET" for method, _path in api.calls))

        api = MissingRefAPI()
        port = recovery.GitHubCheckpointPort(
            api, EXECUTION_HEAD, "2026-08-03T00:00:00Z"
        )
        port.ref_heads[recovery.PUBLICATION_REF] = None
        candidate = recovery.CheckpointCandidate(
            "d" * 40,
            "e" * 40,
            recovery.EVIDENCE_RELATIVE,
            b"{}\n",
        )
        with self.assertRaisesRegex(
            recovery.CorpusRecoveryError, "may not be created"
        ):
            port.mutate_ref_once(
                recovery.PUBLICATION_REF, None, candidate
            )
        self.assertEqual(api.calls, [])

    def test_chain_tamper_parent_path_sequence_and_record_are_rejected(self) -> None:
        controller, _port, _create = self.create_controller()
        history = list(controller.history)
        variants: list[list[recovery.PersistedCheckpoint]] = []
        variants.append(
            [dataclasses.replace(history[0], parent_sha="d" * 40), *history[1:]]
        )
        variants.append(
            [
                dataclasses.replace(history[0], relative_path="wrong.json"),
                *history[1:],
            ]
        )
        value = recovery.strict_json_bytes(history[-1].evidence_bytes, "journal")
        value["sequence"] = 99
        variants.append(
            [
                *history[:-1],
                dataclasses.replace(
                    history[-1], evidence_bytes=recovery.journal_bytes(value)
                ),
            ]
        )
        for variant in variants:
            with self.assertRaises(recovery.CorpusRecoveryError):
                recovery.validate_recovery_chain(
                    variant, self.contract, self.context
                )

    def test_anonymous_url_and_opener_enforce_boundaries(self) -> None:
        request = recovery.build_anonymous_public_request(
            "https://zenodo.org/api/records/21700001"
        )
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.get_header("Authorization"))
        content = recovery.build_anonymous_public_request(
            "https://zenodo.org/api/records/21700001/files/a.bin/content"
        )
        self.assertEqual(content.get_header("Accept"), "application/octet-stream")
        for url in (
            "http://zenodo.org/api/records/1",
            "https://evil.example/api/records/1",
            "https://zenodo.org/api/records/1?token=x",
            "https://user@zenodo.org/api/records/1",
            "https://zenodo.org/api/deposit/depositions/1",
        ):
            with self.subTest(url=url), self.assertRaises(
                recovery.CorpusRecoveryError
            ):
                recovery.build_anonymous_public_request(url)
        opener = recovery.build_anonymous_public_opener()
        # urllib elides an empty ProxyHandler from the final handler chain;
        # absence here proves it did not install environment-derived proxies.
        self.assertFalse(
            any(isinstance(handler, urllib.request.ProxyHandler) for handler in opener.handlers)
        )
        self.assertTrue(
            any(isinstance(handler, recovery._RejectRedirects) for handler in opener.handlers)
        )

    def test_restored_methods_have_no_mutation_call_and_source_has_no_delete(self) -> None:
        self.assertNotIn(
            ".create_once(", inspect.getsource(recovery.RecoveryController.reconcile_create_requested)
        )
        self.assertNotIn(
            ".upload_once(", inspect.getsource(recovery.RecoveryController.reconcile_upload_intent)
        )
        self.assertNotIn(
            ".publish_once(", inspect.getsource(recovery.RecoveryController.reconcile_publish_requested)
        )
        source = pathlib.Path(recovery.__file__).read_text(encoding="utf-8")
        self.assertNotIn("delete_all_files", source)
        self.assertNotIn('self.request("DELETE"', source)
        self.assertIn('"--execute"', source)
        self.assertIn('"--check"', source)

    def test_final_integrity_adds_only_both_receipts_to_execution_manifest(self) -> None:
        head = recovery._git_text("rev-parse", "--verify", "HEAD^{commit}")
        values = recovery._expected_final_integrity(head, b"journal\n", b"final\n")
        self.assertEqual(set(values), set(recovery.INTEGRITY_PATHS))
        manifest = recovery.strict_json_bytes(
            values["REPOSITORY_FILE_MANIFEST.json"], "generated integrity"
        )
        by_path = {entry["path"]: entry for entry in manifest["files"]}
        self.assertEqual(by_path[recovery.RECOVERY_RELATIVE]["bytes"], 8)
        self.assertEqual(by_path[recovery.EVIDENCE_RELATIVE]["bytes"], 6)
        self.assertEqual(
            values["REPOSITORY_FILE_MANIFEST.json.sha256"],
            (
                hashlib.sha256(values["REPOSITORY_FILE_MANIFEST.json"]).hexdigest()
                + "  REPOSITORY_FILE_MANIFEST.json\n"
            ).encode("ascii"),
        )


if __name__ == "__main__":
    unittest.main()
