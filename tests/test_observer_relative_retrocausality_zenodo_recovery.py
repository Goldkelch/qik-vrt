# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import inspect
import json
import pathlib
import subprocess
import tempfile
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = (
    ROOT
    / ".github/workflows/"
    "qikvrt_observer_relative_retrocausality_zenodo_recovery.yml"
)
BASIS = (
    ROOT
    / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/"
    "ORR_V2_RECOVERY_BASIS.json"
)
MANIFEST = (
    ROOT
    / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/"
    "publish-request.json"
)

from tools import qikvrt_observer_relative_retrocausality_zenodo_recovery as recovery
from tools import qikvrt_zenodo_publish as publisher


class BasisTests(unittest.TestCase):
    def test_exact_basis_validates(self) -> None:
        loaded = recovery.load_recovery_basis()
        self.assertEqual(recovery.validate_recovery_basis(copy.deepcopy(loaded)), loaded)
        self.assertEqual(loaded["seed_receipt"]["commit"], recovery.SEED)
        self.assertEqual(loaded["seed_receipt"]["record_id"], recovery.RECORD_ID)
        self.assertEqual(loaded["seed_receipt"]["doi"], recovery.DOI)
        self.assertEqual(
            loaded["recovery_contract"]["checkpoint_ref"],
            recovery.RECEIPT_REF,
        )
        self.assertEqual(
            loaded["recovery_contract"]["final_storage_ref"],
            recovery.RECEIPT_REF,
        )

    def test_basis_rejects_unknown_missing_or_changed_values(self) -> None:
        basis = recovery.load_recovery_basis()
        mutations = []
        extra = copy.deepcopy(basis)
        extra["unexpected"] = True
        mutations.append(extra)
        missing = copy.deepcopy(basis)
        del missing["metadata_probe"]
        mutations.append(missing)
        paths = (
            ("controller", "main_parent", "0" * 40),
            ("execution", "commit", "0" * 40),
            ("seed_receipt", "commit", "0" * 40),
            ("seed_receipt", "phase", "create_requested"),
            ("seed_receipt", "record_id", 21947142),
            ("start_receipt", "commit", "0" * 40),
            ("start_receipt", "phase", "record_created"),
            ("start_receipt", "source_artifact_sha256", "0" * 64),
            ("consumption", "tag_object", "0" * 40),
            ("consumption", "recovery_mode", "EXISTING_EXACT_REF_NO_CREATE"),
            ("metadata_probe", "effect", "WRITE"),
            ("metadata_probe", "difference_count", 2),
            ("normalization", "actual_sha256", "0" * 64),
            ("normalization", "all_other_controlled_metadata_exact", False),
            ("recovery_contract", "new_deposition", True),
            ("recovery_contract", "checkpoint_ref", "refs/heads/other"),
            ("claims", "zenodo_publication_completed", True),
        )
        for section, key, value in paths:
            changed = copy.deepcopy(basis)
            changed[section][key] = value
            mutations.append(changed)
        for index, changed in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaisesRegex(SystemExit, "^BLOCK:"):
                    recovery.validate_recovery_basis(changed)

    def test_basis_binds_probe_and_attempt_one_artifacts(self) -> None:
        basis = json.loads(BASIS.read_text(encoding="utf-8"))
        self.assertEqual(
            basis["metadata_probe"]["controller_head"],
            "5c4cba7e8dd6c179c9be4731801691c47d472c16",
        )
        self.assertEqual(basis["metadata_probe"]["run_id"], 31881807652)
        self.assertEqual(basis["metadata_probe"]["job_id"], 95005347027)
        self.assertEqual(basis["metadata_probe"]["artifact_id"], 9246223317)
        self.assertEqual(basis["metadata_probe"]["artifact_size"], 2194)
        self.assertEqual(
            basis["consumption"]["recovery_mode"],
            recovery.SEED_RECOVERY_MODE,
        )
        self.assertEqual(
            basis["seed_receipt"]["source_artifact_sha256"],
            "eede2bf7fb99bb205ca1ef8eb7afbcd62e68db6573eee865af4b831ee4e46215",
        )
        self.assertEqual(basis["start_receipt"]["commit"], recovery.START_TIP)
        self.assertEqual(basis["start_receipt"]["phase"], "prepared")
        self.assertEqual(basis["start_receipt"]["source_run_id"], 31883760835)
        self.assertEqual(basis["start_receipt"]["source_job_id"], 95009877957)
        self.assertEqual(basis["start_receipt"]["source_artifact_id"], 9246720496)
        self.assertEqual(basis["start_receipt"]["source_artifact_bytes"], 5046)
        self.assertEqual(
            basis["start_receipt"]["source_artifact_sha256"],
            "099668a8aba616bebbb1f6d75b598034cd162a0e5a4aced702259b289ade003a",
        )

    def test_exact_prepared_start_receipt_is_a_single_seed_successor(self) -> None:
        self.assertEqual(
            subprocess.run(
                ["git", "show", "-s", "--format=%P", recovery.START_TIP],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
            recovery.SEED,
        )
        raw = subprocess.run(
            [
                "git",
                "show",
                recovery.START_TIP + ":" + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        prepared = json.loads(raw.decode("utf-8"))
        self.assertEqual(prepared["phase"], "prepared")
        self.assertEqual(prepared["record_id"], recovery.RECORD_ID)
        self.assertEqual(prepared["doi"], recovery.DOI)
        self.assertEqual(
            prepared["remote_consumption"]["tag_object"],
            recovery.TAG_OBJECT,
        )

    def test_durable_seed_binds_historical_newly_created_ref_mode(self) -> None:
        raw = subprocess.run(
            [
                "git",
                "show",
                recovery.SEED + ":" + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        seed = json.loads(raw.decode("utf-8"))
        remote = seed["remote_consumption"]
        self.assertEqual(remote["recovery_mode"], recovery.SEED_RECOVERY_MODE)
        self.assertEqual(remote["ref"], recovery.CONSUMPTION_REF)
        self.assertEqual(remote["tag_object"], recovery.TAG_OBJECT)
        self.assertEqual(remote["execution_head"], recovery.EXECUTION)
        self.assertFalse(
            recovery.load_recovery_basis()["recovery_contract"][
                "new_consumption_lock"
            ]
        )


class NormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.expected = cls.manifest["metadata"]["description"]
        cls.actual = cls.expected.translate({0x201E: '"', 0x201C: '"'})

    def test_only_exact_directed_smart_quote_pair_is_accepted(self) -> None:
        self.assertEqual(self.expected.count("„"), 1)
        self.assertEqual(self.expected.count("“"), 1)
        self.assertEqual(
            recovery._description_normalization(self.expected, self.expected),
            "EXACT",
        )
        self.assertEqual(
            recovery._description_normalization(self.actual, self.expected),
            "ZENODO_SMART_QUOTES_TO_ASCII_EXACT_HASH_PAIR",
        )
        self.assertIsNone(recovery._description_normalization(self.expected, self.actual))
        self.assertIsNone(recovery._description_normalization('"x"', "„x“"))
        self.assertIsNone(
            recovery._description_normalization(self.actual + " ", self.expected)
        )
        self.assertIsNone(
            recovery._description_normalization(
                self.expected.replace("„", '"'),
                self.expected,
            )
        )

    def test_hash_and_byte_pins_match_the_manifest_transform(self) -> None:
        import hashlib

        expected_raw = self.expected.encode("utf-8")
        actual_raw = self.actual.encode("utf-8")
        self.assertEqual(len(expected_raw), recovery.NORMALIZED_EXPECTED_BYTES)
        self.assertEqual(
            hashlib.sha256(expected_raw).hexdigest(),
            recovery.NORMALIZED_EXPECTED_SHA256,
        )
        self.assertEqual(len(actual_raw), recovery.NORMALIZED_ACTUAL_BYTES)
        self.assertEqual(
            hashlib.sha256(actual_raw).hexdigest(),
            recovery.NORMALIZED_ACTUAL_SHA256,
        )

    def test_scoped_draft_comparator_accepts_no_other_difference(self) -> None:
        expected = copy.deepcopy(self.manifest["metadata"])
        actual = copy.deepcopy(expected)
        actual.pop("prereserve_doi")
        actual["description"] = self.actual
        actual["creators"][0]["affiliation"] = None
        self.assertEqual(
            recovery._draft_metadata_mismatch_keys(publisher, actual, expected),
            (),
        )
        changed = copy.deepcopy(actual)
        changed["title"] += " changed"
        self.assertEqual(
            recovery._draft_metadata_mismatch_keys(publisher, changed, expected),
            ("title",),
        )
        changed = copy.deepcopy(actual)
        changed["description"] += " "
        self.assertEqual(
            recovery._draft_metadata_mismatch_keys(publisher, changed, expected),
            ("description",),
        )


class FakeGitHubAPI:
    def __init__(
        self,
        old: str,
        *,
        ambiguous: bool = False,
        patch_response: dict | None = None,
        patch_status: int = 200,
        readback_after: str | None = None,
    ) -> None:
        self.sha = old
        self.ambiguous = ambiguous
        self.patch_response = patch_response
        self.patch_status = patch_status
        self.readback_after = readback_after
        self.calls: list[tuple[str, str, object]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        payload=None,
        accept=(200,),
        allow_ambiguous_transport=False,
    ):
        self.calls.append((method, path, payload))
        value = {
            "ref": recovery.RECEIPT_REF,
            "object": {"sha": self.sha, "type": "commit"},
        }
        if method == "GET":
            return 200, value
        if method == "PATCH":
            self.assert_patch(payload)
            self.sha = self.readback_after or payload["sha"]
            if self.ambiguous and allow_ambiguous_transport:
                raise recovery.h3.AmbiguousRefMutation
            response = {
                "ref": recovery.RECEIPT_REF,
                "object": {"sha": payload["sha"], "type": "commit"},
            }
            return self.patch_status, copy.deepcopy(
                response if self.patch_response is None else self.patch_response
            )
        raise AssertionError("unexpected API method " + method)

    @staticmethod
    def assert_patch(payload) -> None:
        if payload != {"sha": "b" * 40, "force": False}:
            raise AssertionError("non-force fast-forward payload differs")


class GitDataTests(unittest.TestCase):
    def test_receipt_operation_is_update_only_non_force_with_readback(self) -> None:
        api = FakeGitHubAPI("a" * 40)
        result = recovery.persist_receipt_fast_forward(
            api,
            expected_old_sha="a" * 40,
            commit_sha="b" * 40,
        )
        self.assertEqual(result, "b" * 40)
        self.assertEqual([call[0] for call in api.calls], ["GET", "PATCH", "GET"])
        self.assertNotIn("POST", [call[0] for call in api.calls])
        self.assertEqual(api.calls[1][2], {"sha": "b" * 40, "force": False})

    def test_ambiguous_fast_forward_requires_exact_readback(self) -> None:
        api = FakeGitHubAPI("a" * 40, ambiguous=True)
        self.assertEqual(
            recovery.persist_receipt_fast_forward(
                api,
                expected_old_sha="a" * 40,
                commit_sha="b" * 40,
            ),
            "b" * 40,
        )
        self.assertEqual(api.sha, "b" * 40)

    def test_ambiguous_fast_forward_without_ref_effect_blocks_on_get(self) -> None:
        api = FakeGitHubAPI(
            "a" * 40,
            ambiguous=True,
            readback_after="a" * 40,
        )
        with self.assertRaisesRegex(SystemExit, "^BLOCK:"):
            recovery.persist_receipt_fast_forward(
                api,
                expected_old_sha="a" * 40,
                commit_sha="b" * 40,
            )
        self.assertEqual([call[0] for call in api.calls], ["GET", "PATCH", "GET"])
        self.assertEqual(sum(call[0] == "PATCH" for call in api.calls), 1)
        self.assertEqual(api.sha, "a" * 40)

    def test_200_patch_response_is_non_authoritative_when_exact_get_succeeds(self) -> None:
        responses = (
            {},
            {
                "ref": "refs/heads/unrelated",
                "object": {"sha": "c" * 40, "type": "tag"},
            },
        )
        for response in responses:
            with self.subTest(response=response):
                api = FakeGitHubAPI("a" * 40, patch_response=response)
                self.assertEqual(
                    recovery.persist_receipt_fast_forward(
                        api,
                        expected_old_sha="a" * 40,
                        commit_sha="b" * 40,
                    ),
                    "b" * 40,
                )
                self.assertEqual(
                    [call[0] for call in api.calls],
                    ["GET", "PATCH", "GET"],
                )

    def test_exact_get_mismatch_blocks_even_after_successful_patch_response(self) -> None:
        api = FakeGitHubAPI("a" * 40, readback_after="c" * 40)
        with self.assertRaisesRegex(SystemExit, "^BLOCK:"):
            recovery.persist_receipt_fast_forward(
                api,
                expected_old_sha="a" * 40,
                commit_sha="b" * 40,
            )
        self.assertEqual([call[0] for call in api.calls], ["GET", "PATCH", "GET"])

    def test_conflict_statuses_pass_only_with_exact_authoritative_get(self) -> None:
        for status in (409, 422):
            with self.subTest(status=status, readback="exact"):
                api = FakeGitHubAPI("a" * 40, patch_status=status)
                self.assertEqual(
                    recovery.persist_receipt_fast_forward(
                        api,
                        expected_old_sha="a" * 40,
                        commit_sha="b" * 40,
                    ),
                    "b" * 40,
                )
            with self.subTest(status=status, readback="mismatch"):
                api = FakeGitHubAPI(
                    "a" * 40,
                    patch_status=status,
                    readback_after="c" * 40,
                )
                with self.assertRaisesRegex(SystemExit, "^BLOCK:"):
                    recovery.persist_receipt_fast_forward(
                        api,
                        expected_old_sha="a" * 40,
                        commit_sha="b" * 40,
                    )

    def test_wrong_old_head_blocks_before_patch(self) -> None:
        api = FakeGitHubAPI("c" * 40)
        with self.assertRaisesRegex(SystemExit, "^BLOCK:"):
            recovery.persist_receipt_fast_forward(
                api,
                expected_old_sha="a" * 40,
                commit_sha="b" * 40,
            )
        self.assertEqual([call[0] for call in api.calls], ["GET"])


class ProbeBindingTests(unittest.TestCase):
    class API:
        def __init__(self) -> None:
            self.values = self._values()

        @staticmethod
        def _run():
            return {
                "id": recovery.PROBE_RUN_ID,
                "run_attempt": 1,
                "workflow_id": recovery.PROBE_WORKFLOW_ID,
                "name": recovery.PROBE_WORKFLOW_NAME,
                "path": recovery.PROBE_WORKFLOW_PATH,
                "event": "push",
                "head_sha": recovery.PROBE_HEAD,
                "head_branch": recovery.PROBE_BRANCH,
                "status": "completed",
                "conclusion": "success",
                "repository": {"full_name": recovery.REPOSITORY},
                "head_repository": {"full_name": recovery.REPOSITORY},
            }

        @staticmethod
        def _artifact():
            return {
                "id": recovery.PROBE_ARTIFACT_ID,
                "name": recovery.PROBE_ARTIFACT_NAME,
                "size_in_bytes": recovery.PROBE_ARTIFACT_SIZE,
                "digest": "sha256:" + recovery.PROBE_ARTIFACT_SHA256,
                "expired": False,
            }

        @classmethod
        def _values(cls):
            run_path = "/repos/Goldkelch/qik-vrt/actions/runs/" + str(
                recovery.PROBE_RUN_ID
            )
            artifact = cls._artifact()
            return {
                run_path: cls._run(),
                run_path + "/attempts/1": cls._run(),
                "/repos/Goldkelch/qik-vrt/actions/jobs/"
                + str(recovery.PROBE_JOB_ID): {
                    "id": recovery.PROBE_JOB_ID,
                    "run_id": recovery.PROBE_RUN_ID,
                    "run_attempt": 1,
                    "name": "probe",
                    "head_sha": recovery.PROBE_HEAD,
                    "status": "completed",
                    "conclusion": "success",
                    "run_url": "https://api.github.com" + run_path,
                },
                run_path + "/artifacts": {
                    "total_count": 1,
                    "artifacts": [copy.deepcopy(artifact)],
                },
                "/repos/Goldkelch/qik-vrt/actions/artifacts/"
                + str(recovery.PROBE_ARTIFACT_ID): copy.deepcopy(artifact),
            }

        def request(self, method, path, **_kwargs):
            if method != "GET" or path not in self.values:
                raise AssertionError((method, path))
            return 200, copy.deepcopy(self.values[path])

    def test_live_probe_run_job_and_artifact_are_exactly_bound(self) -> None:
        recovery.verify_metadata_probe(self.API())

    def test_expired_or_digest_changed_probe_artifact_blocks(self) -> None:
        for key, value in (
            ("expired", True),
            ("digest", "sha256:" + "0" * 64),
            ("size_in_bytes", recovery.PROBE_ARTIFACT_SIZE + 1),
        ):
            api = self.API()
            path = "/repos/Goldkelch/qik-vrt/actions/artifacts/" + str(
                recovery.PROBE_ARTIFACT_ID
            )
            api.values[path][key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(SystemExit, "^BLOCK:"):
                    recovery.verify_metadata_probe(api)


class PublisherWrapperTests(unittest.TestCase):
    class Client:
        def request(self, *_args, **_kwargs):
            return None

        def create_paper(self, *_args, **_kwargs):
            return {"id": 999}

        def prepare_draft(self, *_args, **_kwargs):
            return "draft"

        def wait_for_editable_metadata(self, *_args, **_kwargs):
            return {}

        def gate_record(self, *_args, **_kwargs):
            return None

    class Store:
        def __init__(self):
            self.phases = []

        def persist_and_readback(self, _path, _phase):
            self.phases.append(_phase)
            return "f" * 40

        def recheck_remote_boundary(self):
            return None

    @staticmethod
    def module_for(action):
        client = PublisherWrapperTests.Client
        module = types.SimpleNamespace()
        module.zenodo = types.SimpleNamespace(ZenodoClient=client)
        module._create_consumption_receipt = lambda *_a, **_k: None
        module._atomic_recovery_evidence = lambda *_a, **_k: None
        module._acquire_remote_consumption_lock = lambda *_a, **_k: "lock"
        module._resume_publication = lambda *_a, **_k: {}
        module._list_all_owned_depositions = lambda *_a, **_k: []
        module._canonical_inventory_candidates = lambda *_a, **_k: []
        module._recover_create_requested_record = lambda *_a, **_k: None
        module._gate_precreate_inventory = lambda *_a, **_k: None
        module.publish = lambda *_a, **_k: action(module)
        return module

    def test_new_consumption_lock_is_unconditionally_blocked_and_restored(self) -> None:
        module = self.module_for(lambda value: value._acquire_remote_consumption_lock())
        original = module._acquire_remote_consumption_lock
        with self.assertRaisesRegex(SystemExit, "authorization lock"):
            recovery.run_publisher_with_checkpoints(
                MANIFEST,
                ROOT,
                self.Store(),
                publisher_module=module,
            )
        self.assertIs(module._acquire_remote_consumption_lock, original)

    def test_create_paper_is_unconditionally_blocked_and_restored(self) -> None:
        original = self.Client.create_paper
        module = self.module_for(lambda _value: self.Client().create_paper({}))
        with self.assertRaisesRegex(SystemExit, "creation of a Zenodo deposition"):
            recovery.run_publisher_with_checkpoints(
                MANIFEST,
                ROOT,
                self.Store(),
                publisher_module=module,
            )
        self.assertIs(self.Client.create_paper, original)

    def test_every_precreate_inventory_hook_is_blocked_and_restored(self) -> None:
        names = (
            "_list_all_owned_depositions",
            "_canonical_inventory_candidates",
            "_recover_create_requested_record",
            "_gate_precreate_inventory",
        )
        for name in names:
            module = self.module_for(lambda value, selected=name: getattr(value, selected)())
            original = getattr(module, name)
            with self.subTest(name=name):
                with self.assertRaisesRegex(SystemExit, "pre-create inventory"):
                    recovery.run_publisher_with_checkpoints(
                        MANIFEST,
                        ROOT,
                        self.Store(),
                        publisher_module=module,
                    )
                self.assertIs(getattr(module, name), original)

    def test_wrapper_never_replaces_global_metadata_comparator(self) -> None:
        source = inspect.getsource(recovery.run_publisher_with_checkpoints)
        self.assertNotIn("._metadata_matches =", source)
        self.assertIn("create_paper = reject_create_paper", source)
        self.assertIn("_acquire_remote_consumption_lock = reject_new_consumption_lock", source)
        for name in (
            "_list_all_owned_depositions",
            "_canonical_inventory_candidates",
            "_recover_create_requested_record",
            "_gate_precreate_inventory",
        ):
            self.assertIn(name + " = reject_precreate_path", source)

    class BehaviorClient:
        transport_calls = []
        stable_get_calls = 0
        server_file_snapshots = []

        def __init__(self, record, state="draft"):
            self.record = copy.deepcopy(record)
            self.state = state
            self.base_url = "https://zenodo.org"
            self.poll_attempts = 1
            self.poll_interval = 0
            self.sleeper = lambda _delay: None

        @classmethod
        def reset(cls):
            cls.transport_calls = []
            cls.stable_get_calls = 0
            cls.server_file_snapshots = []

        def request(self, method, url, **kwargs):
            self.transport_calls.append((method, url, kwargs))
            return types.SimpleNamespace(status=200), copy.deepcopy(self.record)

        def create_paper(self, *_args, **_kwargs):
            raise AssertionError("create_paper must remain unreachable")

        def prepare_draft(self, *_args, **_kwargs):
            raise AssertionError("the wrapper must decide replay behavior")

        def wait_for_editable_metadata(self, *_args, **_kwargs):
            raise AssertionError("the wrapper must replace metadata polling")

        def gate_record(self, *_args, **_kwargs):
            return None

        def get_deposition_or_record(self, _record_id):
            return self.state, copy.deepcopy(self.record)

        def get(self, _path, *, accept):
            type(self).stable_get_calls += 1
            return 200, copy.deepcopy(self.record)

        def wait_for_gated_record(
            self,
            _record_id,
            metadata,
            entries,
            doi,
            *,
            published,
            initial=None,
        ):
            value = copy.deepcopy(initial if initial is not None else self.record)
            self.gate_record(
                value,
                recovery.RECORD_ID,
                metadata,
                entries,
                doi,
                published=published,
            )
            return value

        @classmethod
        def _server_files(cls, value):
            files = copy.deepcopy(value.get("files", []))
            cls.server_file_snapshots.append(files)
            return files

        @staticmethod
        def _server_file_name(value):
            return value.get("filename", value.get("key"))

    @classmethod
    def behavior_module(cls, phase="record_created", remote_state="draft", files=None):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        metadata = copy.deepcopy(manifest["metadata"])
        metadata["description"] = metadata["description"].translate(
            {0x201E: '"', 0x201C: '"'}
        )
        if remote_state == "published":
            metadata["license"] = {"id": manifest["metadata"]["license"]}
            metadata["resource_type"] = {
                "type": manifest["metadata"]["upload_type"],
                "subtype": manifest["metadata"]["publication_type"],
            }
        record = {
            "id": recovery.RECORD_ID,
            "doi": recovery.DOI,
            "metadata": metadata,
            "files": copy.deepcopy([] if files is None else files),
            "links": {
                "bucket": "https://zenodo.org/api/files/11111111-1111-1111-1111-111111111111"
            },
        }
        client_type = cls.BehaviorClient
        client_type.reset()
        module = types.SimpleNamespace()
        module.CONSUMPTION_STATE = publisher.CONSUMPTION_STATE
        module.zenodo = types.SimpleNamespace(
            ZenodoClient=client_type,
            validate_response_url=lambda url, _base: url,
            _record_id=lambda value, _where: value["id"],
            _doi_from_deposition=lambda value, _where: value["doi"],
            _metadata_matches=publisher.zenodo._metadata_matches,
            _published_metadata_matches=publisher.zenodo._published_metadata_matches,
        )
        module._create_consumption_receipt = lambda *_a, **_k: None
        module._atomic_recovery_evidence = lambda *_a, **_k: None
        module._acquire_remote_consumption_lock = lambda *_a, **_k: "lock"
        module._list_all_owned_depositions = lambda *_a, **_k: []
        module._canonical_inventory_candidates = lambda *_a, **_k: []
        module._recover_create_requested_record = lambda *_a, **_k: None
        module._gate_precreate_inventory = lambda *_a, **_k: None
        module._shared_entries = lambda _files: []
        evidence = {
            "phase": phase,
            "state": publisher.CONSUMPTION_STATE,
            "record_id": recovery.RECORD_ID,
            "doi": recovery.DOI,
            "remote_consumption": {
                "ref": recovery.CONSUMPTION_REF,
                "tag_object": recovery.TAG_OBJECT,
                "execution_head": recovery.EXECUTION,
                "recovery_mode": recovery.SEED_RECOVERY_MODE,
            },
        }

        def original_resume(
            value,
            evidence_path,
            manifest_path,
            root,
            bound_manifest,
            _execution,
            verified,
            client,
            secrets,
        ):
            if phase == "record_created":
                client.request(
                    "PUT",
                    f"https://zenodo.org/api/deposit/depositions/{recovery.RECORD_ID}",
                    payload={"metadata": bound_manifest["metadata"]},
                    accept=(200, 202),
                )
                client.wait_for_editable_metadata(
                    recovery.RECORD_ID,
                    bound_manifest["metadata"],
                )
                return dict(value)
            if remote_state == "draft":
                result = client.prepare_draft(
                    "publication",
                    recovery.RECORD_ID,
                    bound_manifest["metadata"],
                    [],
                    verified,
                    recovery.DOI,
                )
                if result != "draft":
                    raise AssertionError(result)
                return dict(value)
            current_state, current = client.get_deposition_or_record(recovery.RECORD_ID)
            if current_state != "published":
                raise AssertionError(current_state)
            public = client.wait_for_gated_record(
                recovery.RECORD_ID,
                bound_manifest["metadata"],
                [],
                recovery.DOI,
                published=True,
                initial=current,
            )
            final = dict(value)
            final.update(phase="public_verified", state="published", published=public)
            module._atomic_recovery_evidence(evidence_path, final, secrets)
            return final

        module._resume_publication = original_resume

        def run(_manifest_path, root):
            client = client_type(record, remote_state)
            return module._resume_publication(
                evidence,
                root / recovery.EVIDENCE_RELATIVE,
                MANIFEST,
                root,
                manifest,
                recovery.EXECUTION,
                {},
                client,
                {},
            )

        module.publish = run
        return module

    def test_metadata_put_is_get_noop_then_two_stable_empty_file_gets(self) -> None:
        module = self.behavior_module()
        originals = {
            "request": self.BehaviorClient.request,
            "prepare_draft": self.BehaviorClient.prepare_draft,
            "wait": self.BehaviorClient.wait_for_editable_metadata,
            "resume": module._resume_publication,
        }
        recovery.run_publisher_with_checkpoints(
            MANIFEST,
            ROOT,
            self.Store(),
            publisher_module=module,
        )
        self.assertEqual(
            [call[0] for call in self.BehaviorClient.transport_calls],
            ["GET"],
        )
        self.assertEqual(self.BehaviorClient.stable_get_calls, 2)
        self.assertTrue(self.BehaviorClient.server_file_snapshots)
        self.assertTrue(all(not files for files in self.BehaviorClient.server_file_snapshots))
        self.assertIs(self.BehaviorClient.request, originals["request"])
        self.assertIs(self.BehaviorClient.prepare_draft, originals["prepare_draft"])
        self.assertIs(self.BehaviorClient.wait_for_editable_metadata, originals["wait"])
        self.assertIs(module._resume_publication, originals["resume"])

    def test_record_created_with_any_server_file_blocks_before_noop(self) -> None:
        module = self.behavior_module(files=[{"filename": "unexpected"}])
        with self.assertRaisesRegex(SystemExit, "gained files"):
            recovery.run_publisher_with_checkpoints(
                MANIFEST,
                ROOT,
                self.Store(),
                publisher_module=module,
            )
        self.assertEqual(self.BehaviorClient.transport_calls, [])

    def test_prepared_draft_replay_is_read_only_and_allowed(self) -> None:
        module = self.behavior_module(phase="prepared")
        recovery.run_publisher_with_checkpoints(
            MANIFEST,
            ROOT,
            self.Store(),
            publisher_module=module,
        )
        self.assertEqual(self.BehaviorClient.transport_calls, [])
        self.assertEqual(self.BehaviorClient.stable_get_calls, 0)

    def test_prepared_full_sequence_durably_intends_exactly_one_publish(self) -> None:
        module = self.behavior_module(phase="prepared")
        events = []

        class SequenceStore:
            def __init__(self):
                self.current_phase = "prepared"
                self.phases = []
                self.same_phase_prepared = 0

            def persist_and_readback(self, _path, phase):
                self.phases.append(phase)
                if phase == "prepared":
                    if self.current_phase != "prepared":
                        raise AssertionError("prepared replay was not same-phase")
                    self.same_phase_prepared += 1
                    events.append("durable:prepared:same-phase")
                elif phase == "publish_requested":
                    if self.current_phase != "prepared" or self.same_phase_prepared != 1:
                        raise AssertionError("publish intent skipped prepared replay")
                    self.current_phase = phase
                    events.append("durable:publish_requested")
                elif phase == "public_verified":
                    if self.current_phase != "publish_requested":
                        raise AssertionError("public verification preceded publish intent")
                    self.current_phase = phase
                    events.append("durable:public_verified")
                else:
                    raise AssertionError("unexpected phase " + phase)
                return "f" * 40

            def recheck_remote_boundary(self):
                return None

        store = SequenceStore()
        forbidden_calls = {
            "create_paper": 0,
            "lock": 0,
            "list_owned": 0,
            "inventory_candidates": 0,
            "recover_create_requested": 0,
            "gate_precreate_inventory": 0,
        }

        def tracked_forbidden(name, result=None):
            def call(*_args, **_kwargs):
                forbidden_calls[name] += 1
                return result

            return call

        original_client_request = self.BehaviorClient.request
        original_create_paper = self.BehaviorClient.create_paper

        def observed_request(instance, method, url, **kwargs):
            if method == "POST":
                if store.current_phase != "publish_requested":
                    raise AssertionError("publish POST preceded durable intent")
                events.append("request:POST:" + url)
            return original_client_request(instance, method, url, **kwargs)

        def observed_create_paper(*_args, **_kwargs):
            forbidden_calls["create_paper"] += 1
            raise AssertionError("create_paper must remain unreachable")

        self.BehaviorClient.request = observed_request
        self.BehaviorClient.create_paper = observed_create_paper
        module._acquire_remote_consumption_lock = tracked_forbidden("lock", "lock")
        module._list_all_owned_depositions = tracked_forbidden("list_owned", [])
        module._canonical_inventory_candidates = tracked_forbidden(
            "inventory_candidates", []
        )
        module._recover_create_requested_record = tracked_forbidden(
            "recover_create_requested"
        )
        module._gate_precreate_inventory = tracked_forbidden(
            "gate_precreate_inventory"
        )

        def record_write(_path, value, _secrets):
            events.append("write:" + value["phase"])

        module._atomic_recovery_evidence = record_write

        def complete_prepared_record(
            value,
            evidence_path,
            _manifest_path,
            _root,
            manifest,
            _execution,
            verified,
            client,
            secrets,
        ):
            preparation = client.prepare_draft(
                "publication",
                recovery.RECORD_ID,
                manifest["metadata"],
                [],
                verified,
                recovery.DOI,
            )
            if preparation != "draft":
                raise AssertionError(preparation)
            prepared = dict(value, phase="prepared")
            module._atomic_recovery_evidence(evidence_path, prepared, secrets)
            publish_requested = dict(value, phase="publish_requested")
            module._atomic_recovery_evidence(
                evidence_path,
                publish_requested,
                secrets,
            )
            client.request(
                "POST",
                "https://zenodo.org/api/deposit/depositions/"
                + str(recovery.RECORD_ID)
                + "/actions/publish",
                accept=(200, 201, 202, 409),
            )
            client.state = "published"
            client.record["metadata"]["license"] = {
                "id": manifest["metadata"]["license"]
            }
            client.record["metadata"]["resource_type"] = {
                "type": manifest["metadata"]["upload_type"],
                "subtype": manifest["metadata"]["publication_type"],
            }
            published = client.wait_for_gated_record(
                recovery.RECORD_ID,
                manifest["metadata"],
                [],
                recovery.DOI,
                published=True,
                initial=client.record,
            )
            final = dict(
                value,
                phase="public_verified",
                state="published",
                published=published,
            )
            module._atomic_recovery_evidence(evidence_path, final, secrets)
            return final

        module._resume_publication = complete_prepared_record
        try:
            result = recovery.run_publisher_with_checkpoints(
                MANIFEST,
                ROOT,
                store,
                publisher_module=module,
            )
        finally:
            self.BehaviorClient.request = original_client_request
            self.BehaviorClient.create_paper = original_create_paper

        publish_url = (
            "https://zenodo.org/api/deposit/depositions/"
            + str(recovery.RECORD_ID)
            + "/actions/publish"
        )
        self.assertEqual(result["phase"], "public_verified")
        self.assertEqual(
            store.phases,
            ["prepared", "publish_requested", "public_verified"],
        )
        self.assertEqual(store.same_phase_prepared, 1)
        self.assertEqual(
            events,
            [
                "write:prepared",
                "durable:prepared:same-phase",
                "write:publish_requested",
                "durable:publish_requested",
                "request:POST:" + publish_url,
                "write:public_verified",
                "durable:public_verified",
            ],
        )
        self.assertEqual(
            self.BehaviorClient.transport_calls,
            [("POST", publish_url, {"accept": (200, 201, 202, 409)})],
        )
        self.assertEqual(
            sum(
                method == "POST" and url == publish_url
                for method, url, _kwargs in self.BehaviorClient.transport_calls
            ),
            1,
        )
        self.assertEqual(
            [
                call
                for call in self.BehaviorClient.transport_calls
                if call[0] in {"PUT", "DELETE"}
            ],
            [],
        )
        self.assertEqual(
            [
                call
                for call in self.BehaviorClient.transport_calls
                if call[0] == "POST"
                and call[1] == "https://zenodo.org/api/deposit/depositions"
            ],
            [],
        )
        self.assertEqual(forbidden_calls, {name: 0 for name in forbidden_calls})

    def test_publish_requested_public_record_advances_without_mutation(self) -> None:
        module = self.behavior_module(
            phase="publish_requested",
            remote_state="published",
        )
        store = self.Store()
        result = recovery.run_publisher_with_checkpoints(
            MANIFEST,
            ROOT,
            store,
            publisher_module=module,
        )
        self.assertEqual(result["phase"], "public_verified")
        self.assertEqual(store.phases, ["public_verified"])
        self.assertEqual(self.BehaviorClient.transport_calls, [])


class StaticContractTests(unittest.TestCase):
    def test_workflow_is_one_shot_exact_push_only(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.run_attempt == 1", text)
        self.assertIn("github.event.created == false", text)
        self.assertIn("github.event.deleted == false", text)
        self.assertIn("github.event.forced == false", text)
        self.assertIn("github.event.before == '" + recovery.MAIN + "'", text)
        self.assertIn("github.event.after == github.sha", text)
        self.assertIn(recovery.TRIGGER_BRANCH, text)
        self.assertNotIn("workflow_dispatch", text)
        self.assertNotIn("rerun", text.lower())

    def test_workflow_uses_same_receipt_ref_and_exact_prepared_start(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count(recovery.RECEIPT_REF), 1)
        self.assertIn(recovery.SEED, text)
        self.assertIn(recovery.START_TIP, text)
        self.assertIn(recovery.START_EVIDENCE_BLOB, text)
        self.assertIn('= "$START_EVIDENCE_BLOB"', text)
        self.assertNotIn("fb1a0e88602a59f2b7e99280be47e9094223801b", text)
        self.assertIn(recovery.TAG_OBJECT, text)
        self.assertIn(recovery.EXECUTION, text)
        self.assertIn("ZENODO_ACCESS_TOKEN: ${{ secrets.ZENODO_ACCESS_TOKEN }}", text)
        self.assertIn("contents: write", text)
        self.assertNotIn(
            "recovery-execution/observer-relative-retrocausality-v2-21947141-v2",
            text,
        )

    def test_controller_delta_is_exactly_seven_paths(self) -> None:
        basis = recovery.load_recovery_basis()
        self.assertEqual(
            basis["controller"]["trigger_commit_delta"],
            list(recovery.EXPECTED_TRIGGER_DELTA),
        )
        self.assertEqual(len(recovery.EXPECTED_TRIGGER_DELTA), 7)

    def test_checkpoint_suffix_ends_public_verified_on_same_ref(self) -> None:
        self.assertEqual(
            recovery.CHECKPOINT_PHASES,
            ("prepared", "publish_requested", "public_verified"),
        )
        source = inspect.getsource(recovery.RecoveryReceiptStore.persist_and_readback)
        self.assertIn("persist_receipt_fast_forward", source)
        self.assertNotIn("publication_ref", source)

    def test_tool_reuses_h3_pinned_loader_and_git_data_transport(self) -> None:
        source = (ROOT / recovery.TOOL_RELATIVE).read_text(encoding="utf-8")
        self.assertIn("h3._load_e1_publisher", source)
        self.assertIn("h3._call_api", source)
        self.assertIn("h3._git", source)
        self.assertIn("h3._without_effect_credentials", source)

    def test_exact_execution_and_seed_objects_validate_in_detached_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qikvrt-orr-test-") as directory:
            target = pathlib.Path(directory) / "execution"
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(target), recovery.EXECUTION],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                recovery.validate_execution_objects(
                    target,
                    recovery.load_recovery_basis(),
                )
            finally:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(target)],
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )


if __name__ == "__main__":
    unittest.main()
