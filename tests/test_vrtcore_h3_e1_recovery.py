# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import copy
import inspect
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.parse
import unittest
from typing import Any, Mapping
from unittest import mock

from tests.release_authority_hold_contract import assert_authority_hold_workflow
from tools import qikvrt_vrtcore_h3_e1_recovery as recovery
from tools import qikvrt_zenodo_publish as publish


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/qikvrt_vrtcore_h3_e1_recovery.yml"
CONTROLLER_PATH = ROOT / "tools/qikvrt_vrtcore_h3_e1_recovery.py"

E1 = "53e757ebce929b40250f90a02ed2a9ec62de6217"
E1_PARENT = "cdb0e9fe8444565df665affa64463295648b1368"
E1_TREE = "99ee39034abbdf8abd4fd9891915cf3d647365db"
PUBLICATION_REF = "refs/heads/publication/vrtcore-relational-h3-v1"
RECOVERY_REF = (
    "refs/heads/qikvrt-recovery/vrtcore-zenodo/h3/" + E1
)


def _different(value: object) -> object:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        if re.fullmatch(r"[0-9a-f]{40}", value):
            return ("0" if value[0] != "0" else "1") + value[1:]
        return value + "-tampered"
    if isinstance(value, list):
        return [*value, "tampered"]
    if isinstance(value, dict):
        changed = copy.deepcopy(value)
        changed["unexpected"] = True
        return changed
    raise AssertionError(f"no deterministic mutation for {type(value).__name__}")


class FakeGitData:
    """Small stateful Git-Data transport with an auditable call journal."""

    def __init__(self, refs: Mapping[str, str] | None = None) -> None:
        self.refs = dict(refs or {})
        self.calls: list[dict[str, Any]] = []
        self.mutation_result = "success"
        self.wrong_readback_sha: str | None = None

    def __call__(
        self,
        method: str,
        path: str,
        *args: object,
        payload: Mapping[str, Any] | None = None,
        accept: tuple[int, ...] = (200,),
        allow_ambiguous_transport: bool = False,
        **kwargs: object,
    ) -> tuple[int, dict[str, Any]]:
        del args, kwargs, accept, allow_ambiguous_transport
        return self.request(method, path, payload=payload)

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        **kwargs: object,
    ) -> tuple[int, dict[str, Any]]:
        del kwargs
        normalized_payload = None if payload is None else dict(payload)
        self.calls.append(
            {"method": method, "path": path, "payload": normalized_payload}
        )

        if method == "GET" and "/git/ref/" in path:
            ref = "refs/" + urllib.parse.unquote(path.split("/git/ref/", 1)[1])
            sha = self.refs.get(ref)
            if sha is None:
                return 404, {}
            if self.wrong_readback_sha is not None:
                sha = self.wrong_readback_sha
            return 200, self.ref_value(ref, sha)

        if method == "POST" and path.endswith("/git/refs"):
            if normalized_payload is None:
                raise AssertionError("missing create payload")
            ref = str(normalized_payload["ref"])
            sha = str(normalized_payload["sha"])
            if self.mutation_result == "conflict":
                return 422, {"message": "Reference already exists"}
            if self.mutation_result == "conflict_after_effect":
                self.refs[ref] = sha
                return 422, {"message": "ambiguous conflict"}
            if self.mutation_result == "transport_after_effect":
                self.refs[ref] = sha
                raise recovery.AmbiguousRefMutation("simulated transport loss")
            if self.mutation_result == "transport":
                raise recovery.AmbiguousRefMutation("simulated transport loss")
            if self.mutation_result == "wrong_response_after_effect":
                self.refs[ref] = sha
                return 201, self.ref_value(ref, "c" * 40)
            if ref in self.refs:
                return 422, {"message": "Reference already exists"}
            self.refs[ref] = sha
            return 201, self.ref_value(ref, sha)

        if method == "PATCH" and "/git/refs/" in path:
            if normalized_payload is None:
                raise AssertionError("missing update payload")
            ref = "refs/" + urllib.parse.unquote(path.split("/git/refs/", 1)[1])
            sha = str(normalized_payload["sha"])
            if self.mutation_result == "conflict":
                return 409, {"message": "Update is not a fast forward"}
            if self.mutation_result == "conflict_after_effect":
                self.refs[ref] = sha
                return 409, {"message": "ambiguous conflict"}
            if self.mutation_result == "transport_after_effect":
                self.refs[ref] = sha
                raise recovery.AmbiguousRefMutation("simulated transport loss")
            if self.mutation_result == "transport":
                raise recovery.AmbiguousRefMutation("simulated transport loss")
            if self.mutation_result == "wrong_response_after_effect":
                self.refs[ref] = sha
                return 200, self.ref_value(ref, "c" * 40)
            if ref not in self.refs:
                return 422, {"message": "Reference does not exist"}
            self.refs[ref] = sha
            return 200, self.ref_value(ref, sha)

        raise AssertionError(f"unexpected GitHub API call: {method} {path}")

    @staticmethod
    def ref_value(ref: str, sha: str) -> dict[str, Any]:
        return {"ref": ref, "object": {"sha": sha, "type": "commit"}}

    @property
    def mutations(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if call["method"] != "GET"]


class VRTCoreH3E1RecoveryStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.controller = CONTROLLER_PATH.read_text(encoding="utf-8")

    def test_expected_contract_is_bound_to_the_original_e1(self) -> None:
        expected = recovery.EXPECTED
        self.assertEqual(expected["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(expected["e1"], E1)
        self.assertEqual(expected["e1_parent"], E1_PARENT)
        self.assertEqual(expected["e1_tree"], E1_TREE)
        self.assertEqual(expected["publication_ref"], PUBLICATION_REF)
        self.assertEqual(expected["recovery_ref"], RECOVERY_REF)
        self.assertEqual(expected["run_id"], 30753751400)
        self.assertEqual(expected["job_id"], 91512247885)
        self.assertRegex(expected["tag_object"], r"^[0-9a-f]{40}$")
        self.assertEqual(expected["initial_phase"], "authorization_consumed")
        self.assertEqual(
            expected["recovery_mode"], "EXISTING_EXACT_REF_NO_CREATE"
        )

    def test_workflow_has_one_exact_static_push_trigger(self) -> None:
        assert_authority_hold_workflow(self, WORKFLOW_PATH.name)
        return
        trigger = self.workflow.split("permissions:", 1)[0]
        branch = recovery.EXPECTED["trigger_branch"]
        self.assertEqual(trigger.count("      - " + branch + "\n"), 1)
        for forbidden in (
            "workflow_dispatch",
            "repository_dispatch",
            "pull_request",
            "workflow_run",
            "schedule:",
        ):
            self.assertNotIn(forbidden, trigger)
        self.assertNotRegex(trigger, r"(?m)^\s*-\s*main\s*$")
        self.assertIn("github.repository == 'Goldkelch/qik-vrt'", self.workflow)
        self.assertIn("github.event_name == 'push'", self.workflow)
        self.assertIn("github.event.forced == false", self.workflow)

    def test_parent_placeholder_is_unique_and_fails_closed(self) -> None:
        assert_authority_hold_workflow(self, WORKFLOW_PATH.name)
        return
        placeholder = recovery.EXPECTED["controller_parent_placeholder"]
        binding = re.search(
            r"(?m)^\s*EXPECTED_CONTROLLER_PARENT:\s*(\S+)\s*$",
            self.workflow,
        )
        self.assertIsNotNone(binding)
        assert binding is not None
        env_value = binding.group(1)
        tokens = set(
            re.findall(r"__[A-Z0-9_]*H3[A-Z0-9_]*PARENT[A-Z0-9_]*__", self.workflow)
        )
        self.assertEqual(tokens, {placeholder})
        if env_value == placeholder:
            self.assertEqual(self.workflow.count(placeholder), 2)
        else:
            self.assertRegex(env_value, r"^[0-9a-f]{40}$")
            self.assertEqual(self.workflow.count(placeholder), 1)
        self.assertIn("EXPECTED_CONTROLLER_PARENT", self.workflow)
        self.assertIn("BLOCK: unresolved controller parent placeholder", self.workflow)

    def test_r0_and_materialized_r1_keep_one_sentinel_and_exact_gates(self) -> None:
        assert_authority_hold_workflow(self, WORKFLOW_PATH.name)
        return
        placeholder = recovery.EXPECTED["controller_parent_placeholder"]
        binding = re.search(
            r"(?m)^(\s*EXPECTED_CONTROLLER_PARENT:\s*)(\S+)(\s*)$",
            self.workflow,
        )
        self.assertIsNotNone(binding)
        assert binding is not None
        prefix, env_value, suffix = binding.groups()
        materialized_parent = env_value if env_value != placeholder else "d" * 40
        self.assertRegex(materialized_parent, r"^[0-9a-f]{40}$")
        r0 = (
            self.workflow[: binding.start()]
            + prefix
            + placeholder
            + suffix
            + self.workflow[binding.end() :]
        )
        r1 = (
            self.workflow[: binding.start()]
            + prefix
            + materialized_parent
            + suffix
            + self.workflow[binding.end() :]
        )
        self.assertEqual(r0.count(placeholder), 2)
        self.assertEqual(
            re.findall(
                r"(?m)^\s*EXPECTED_CONTROLLER_PARENT:\s*(\S+)\s*$",
                r0,
            ),
            [placeholder],
        )
        self.assertEqual(
            re.findall(
                r"(?m)^\s*EXPECTED_CONTROLLER_PARENT:\s*([0-9a-f]{40})\s*$",
                r1,
            ),
            [materialized_parent],
        )
        self.assertEqual(r1.count(placeholder), 1)
        self.assertEqual(
            r1.count('"' + placeholder + '"'),
            1,
        )
        for gate in (
            'show -s --format=%P HEAD)',
            '"$EXPECTED_CONTROLLER_PARENT"',
            "expected_delta=\"$(",
            "observed_delta=\"$(",
            "--name-status",
            "--no-renames",
            'test "$observed_delta" = "$expected_delta"',
            'test "$main_head" = "$EXPECTED_CONTROLLER_PARENT"',
        ):
            self.assertIn(gate, r1)
        self.assertEqual(
            re.findall(r"'M\t([^'\n]+)'", r1),
            [
                ".github/workflows/qikvrt_vrtcore_h3_e1_recovery.yml",
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ],
        )

    def test_workflow_serializes_with_the_original_publisher(self) -> None:
        assert_authority_hold_workflow(self, WORKFLOW_PATH.name)
        return
        self.assertIn(
            "group: qikvrt-vrtcore-causal-zenodo-publication-v1",
            self.workflow,
        )
        self.assertIn("cancel-in-progress: false", self.workflow)
        permissions = self.workflow.split("permissions:\n", 1)[1].split(
            "\nconcurrency:",
            1,
        )[0]
        self.assertEqual(
            permissions,
            "  contents: write\n  actions: read\n",
        )
        self.assertIn("persist-credentials: false", self.workflow)
        self.assertIn(E1, self.workflow)
        self.assertIn("run_publisher_with_checkpoints", self.workflow)
        for action in re.findall(
            r"(?m)^\s*uses:\s*([^\s#]+)", self.workflow
        ):
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_zenodo_secret_is_scoped_to_the_publisher_step(self) -> None:
        assert_authority_hold_workflow(self, WORKFLOW_PATH.name)
        return
        expression = "${{ secrets.ZENODO_ACCESS_TOKEN }}"
        self.assertEqual(self.workflow.count(expression), 1)
        secret_at = self.workflow.index(expression)
        step_start = self.workflow.rfind("\n      - name:", 0, secret_at)
        step_end = self.workflow.find("\n      - name:", secret_at)
        self.assertGreaterEqual(step_start, 0)
        if step_end < 0:
            step_end = len(self.workflow)
        secret_step = self.workflow[step_start:step_end]
        self.assertIn("run_publisher_with_checkpoints", secret_step)
        self.assertNotIn(expression, self.workflow[:step_start])
        self.assertNotIn(expression, self.workflow[step_end:])

    def test_secret_step_has_no_unscrubbed_git_and_local_git_scrubs_tokens(
        self,
    ) -> None:
        assert_authority_hold_workflow(self, WORKFLOW_PATH.name)
        return
        expression = "${{ secrets.ZENODO_ACCESS_TOKEN }}"
        secret_at = self.workflow.index(expression)
        step_start = self.workflow.rfind("\n      - name:", 0, secret_at)
        step_end = self.workflow.find("\n      - name:", secret_at)
        if step_end < 0:
            step_end = len(self.workflow)
        secret_step = self.workflow[step_start:step_end]
        self.assertNotRegex(
            secret_step,
            r"(?m)^\s*git\b[^\n]*\bls-remote\b",
        )
        self.assertIn(
            "env -u GITHUB_TOKEN -u GH_TOKEN -u ZENODO_ACCESS_TOKEN \\\n"
            "              git -C execution rev-parse --verify HEAD^{commit}",
            secret_step,
        )

        completed = subprocess.CompletedProcess(
            args=["git", "status"],
            returncode=0,
            stdout=b"",
            stderr=b"",
        )
        supplied_environment = {
            "GITHUB_TOKEN": "github-secret",
            "GH_TOKEN": "gh-secret",
            "ZENODO_ACCESS_TOKEN": "zenodo-secret",
            "SAFE_RECOVERY_VALUE": "retained",
        }
        with mock.patch.object(
            recovery.subprocess,
            "run",
            return_value=completed,
        ) as run:
            recovery._git(
                ROOT,
                "status",
                "--porcelain=v1",
                environment=supplied_environment,
            )
        child_environment = run.call_args.kwargs["env"]
        for secret_name in (
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "ZENODO_ACCESS_TOKEN",
        ):
            self.assertNotIn(secret_name, child_environment)
        self.assertEqual(child_environment["SAFE_RECOVERY_VALUE"], "retained")

    def test_final_persistence_has_one_commit_one_ref_write_and_readback(self) -> None:
        source = inspect.getsource(recovery.RecoveryReceiptStore.persist_final)
        self.assertEqual(source.count("self._create_receipt_commit("), 1)
        self.assertEqual(source.count("persist_receipt_create_only_or_ff("), 1)
        self.assertEqual(source.count("self._readback("), 1)
        create_at = source.index("self._create_receipt_commit(")
        persist_at = source.index("persist_receipt_create_only_or_ff(")
        readback_at = source.index("self._readback(")
        self.assertLess(create_at, persist_at)
        self.assertLess(persist_at, readback_at)
        self.assertIn('ref=EXPECTED["publication_ref"]', source)
        self.assertIn('expected_old_sha=EXPECTED["e1"]', source)
        self.assertIn(
            'self._readback(\n            EXPECTED["publication_ref"]',
            source,
        )

    def test_receipt_validation_checks_provenance_after_validated_phase(self) -> None:
        source = inspect.getsource(recovery._validate_receipt_commit)
        self.assertEqual(
            source.count("_validate_receipt_commit_provenance("),
            1,
        )
        self.assertLess(
            source.index('validated["phase"] != expected_phase'),
            source.index("_validate_receipt_commit_provenance("),
        )
        self.assertLess(
            source.index("_validate_receipt_commit_provenance("),
            source.index("_validate_receipt_integrity("),
        )

    def test_workflow_has_no_tag_or_force_write_path(self) -> None:
        lowered = (self.workflow + "\n" + self.controller).lower()
        self.assertNotIn("git tag ", lowered)
        self.assertNotIn("git push ", lowered)
        self.assertNotIn('"force": true', lowered)
        self.assertNotIn("force: true", lowered)
        self.assertNotRegex(
            lowered,
            r"(?:post|patch|put|delete).{0,160}(?:/git/tags|refs/tags)",
        )
        self.assertNotRegex(
            lowered,
            r"(?:/git/tags|refs/tags).{0,160}(?:post|patch|put|delete)",
        )


class VRTCoreH3E1RecoveryBasisTests(unittest.TestCase):
    def test_repository_basis_is_exact_and_contains_no_nonce(self) -> None:
        raw = recovery.BASIS_PATH.read_bytes()
        self.assertNotIn(b'"nonce"', raw.lower())
        direct = json.loads(raw.decode("utf-8"))
        loaded = recovery.load_recovery_basis()
        self.assertEqual(loaded, direct)
        self.assertEqual(recovery.validate_recovery_basis(copy.deepcopy(loaded)), loaded)
        for key in (
            "repository",
            "e1",
            "e1_parent",
            "e1_tree",
            "publication_ref",
            "recovery_ref",
            "run_id",
            "job_id",
            "tag_object",
            "initial_phase",
            "recovery_mode",
        ):
            self.assertEqual(loaded[key], recovery.EXPECTED[key], key)

    def test_every_exact_basis_binding_rejects_tampering(self) -> None:
        basis = recovery.load_recovery_basis()
        for key in (
            "repository",
            "e1",
            "e1_parent",
            "e1_tree",
            "publication_ref",
            "recovery_ref",
            "run_id",
            "job_id",
            "tag_object",
            "initial_phase",
            "recovery_mode",
            "job_log_sha256",
            "failure_boundary",
        ):
            with self.subTest(key=key):
                tampered = copy.deepcopy(basis)
                tampered[key] = _different(tampered[key])
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    recovery.validate_recovery_basis(tampered)

    def test_missing_or_unknown_basis_fields_fail_closed(self) -> None:
        basis = recovery.load_recovery_basis()
        missing = copy.deepcopy(basis)
        missing.pop("e1_tree")
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            recovery.validate_recovery_basis(missing)
        unknown = copy.deepcopy(basis)
        unknown["unreviewed"] = True
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            recovery.validate_recovery_basis(unknown)

    def test_safety_boundaries_in_the_basis_cannot_be_promoted(self) -> None:
        basis = recovery.load_recovery_basis()
        mutations = (
            (("failed_run", "observed_boundary", "zenodo_api_call_started"), True),
            (("failed_run", "observed_boundary", "durable_v2_evidence"), True),
            (("remote_consumption", "new_tag_write_allowed"), True),
            (("recovery_contract", "new_authorization"), True),
            (("recovery_contract", "replacement_nonce"), True),
            (("recovery_contract", "authorization_rebinding"), True),
            (("claims", "zenodo_publication_completed"), True),
            (("claims", "effect_ack_done"), True),
            (("claims", "final_pass"), True),
        )
        for path, replacement in mutations:
            with self.subTest(path=path):
                tampered = copy.deepcopy(basis)
                target = tampered
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    recovery.validate_recovery_basis(tampered)

    def test_real_e1_git_objects_and_exact_delta_are_verified(self) -> None:
        basis = recovery.load_recovery_basis()
        recovery.validate_e1_repository_objects(ROOT, basis)
        self.assertEqual(
            basis["original_execution"]["exact_parent_delta"],
            [
                "A\t.github/workflows/qikvrt_vrtcore_zenodo_publish.yml",
                "M\tREPOSITORY_FILE_MANIFEST.json",
                "M\tREPOSITORY_FILE_MANIFEST.json.sha256",
                "M\tSHA256SUMS.txt",
                "M\ttests/test_vrtcore_zenodo_publication_controls.py",
            ],
        )

    def test_real_but_wrong_git_objects_fail_closed(self) -> None:
        basis = recovery.load_recovery_basis()
        for key, value in (
            ("e1", E1_PARENT),
            ("e1_parent", "ad947e6e1c3665c8c9fd838d53ccc2ea17641b1b"),
        ):
            with self.subTest(key=key):
                tampered = copy.deepcopy(basis)
                tampered[key] = value
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    recovery.validate_e1_repository_objects(ROOT, tampered)

        tampered_delta = copy.deepcopy(basis)
        tampered_delta["original_execution"]["exact_parent_delta"][0] = (
            "A\tunexpected"
        )
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            recovery.validate_e1_repository_objects(ROOT, tampered_delta)

    def test_real_object_reads_with_tampered_observation_fail_closed(self) -> None:
        basis = recovery.load_recovery_basis()
        real_git = recovery._git

        def corrupt_tree(
            root: pathlib.Path,
            *arguments: str,
            **kwargs: object,
        ) -> tuple[int, bytes]:
            status, raw = real_git(root, *arguments, **kwargs)
            if arguments == ("rev-parse", "--verify", f"{E1}^{{tree}}"):
                return status, ("0" * 40 + "\n").encode("ascii")
            return status, raw

        with mock.patch.object(recovery, "_git", side_effect=corrupt_tree):
            with self.assertRaisesRegex(SystemExit, "BLOCK: E1 tree differs"):
                recovery.validate_e1_repository_objects(ROOT, basis)

        def corrupt_delta(
            root: pathlib.Path,
            *arguments: str,
            **kwargs: object,
        ) -> tuple[int, bytes]:
            status, raw = real_git(root, *arguments, **kwargs)
            if arguments[:3] == ("diff", "--name-status", "--no-renames"):
                return status, b""
            return status, raw

        with mock.patch.object(recovery, "_git", side_effect=corrupt_delta):
            with self.assertRaisesRegex(SystemExit, "BLOCK: E1 exact parent delta"):
                recovery.validate_e1_repository_objects(ROOT, basis)


class VRTCoreH3E1RecoveryLoaderTests(unittest.TestCase):
    PINNED_MODULES = {
        "actions": "qikvrt_vrtcore_h3_e1_pinned_actions",
        "machine_proof": "qikvrt_vrtcore_h3_e1_pinned_machine_proof",
        "publisher": "qikvrt_vrtcore_h3_e1_pinned_publisher",
    }
    PINNED_FILES = (
        (
            "tools/qikvrt_zenodo_actions.py",
            "e1_actions_blob",
            "e1_actions_bytes",
            "e1_actions_sha256",
        ),
        (
            "tools/qikvrt_zenodo_machine_proof.py",
            "e1_machine_proof_blob",
            "e1_machine_proof_bytes",
            "e1_machine_proof_sha256",
        ),
        (
            "tools/qikvrt_zenodo_publish.py",
            "e1_publisher_blob",
            "e1_publisher_bytes",
            "e1_publisher_sha256",
        ),
    )

    @staticmethod
    def git(*arguments: str, root: pathlib.Path = ROOT) -> bytes:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr.decode("utf-8", "replace"))
        return result.stdout

    @classmethod
    def checkout_e1(cls, parent: pathlib.Path) -> pathlib.Path:
        checkout = parent / "e1-checkout"
        cls.git(
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(ROOT),
            str(checkout),
        )
        cls.git("checkout", "--quiet", "--detach", E1, root=checkout)
        head = cls.git("rev-parse", "--verify", "HEAD", root=checkout)
        if head.decode("ascii").strip() != E1:
            raise AssertionError("temporary checkout is not exact E1")
        return checkout

    @classmethod
    def module_snapshot(cls) -> tuple[object, dict[str, object]]:
        missing = object()
        return missing, {
            name: sys.modules.get(name, missing)
            for name in cls.PINNED_MODULES.values()
        }

    @classmethod
    def restore_modules(
        cls,
        missing: object,
        previous: Mapping[str, object],
    ) -> None:
        for name, value in previous.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

    def test_loads_exact_e1_publisher_and_injects_pinned_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.checkout_e1(pathlib.Path(directory))
            missing, previous = self.module_snapshot()
            try:
                module = recovery._load_e1_publisher(checkout)
                self.assertEqual(
                    pathlib.Path(module.__file__).resolve(),
                    (checkout / "tools/qikvrt_zenodo_publish.py").resolve(),
                )
                self.assertIs(
                    module.zenodo,
                    sys.modules[self.PINNED_MODULES["actions"]],
                )
                self.assertIs(
                    module.machine_proof,
                    sys.modules[self.PINNED_MODULES["machine_proof"]],
                )
                self.assertIs(
                    module,
                    sys.modules[self.PINNED_MODULES["publisher"]],
                )
                self.assertEqual(
                    pathlib.Path(module.zenodo.__file__).resolve(),
                    (checkout / "tools/qikvrt_zenodo_actions.py").resolve(),
                )
                self.assertEqual(
                    pathlib.Path(module.machine_proof.__file__).resolve(),
                    (checkout / "tools/qikvrt_zenodo_machine_proof.py").resolve(),
                )
                for relative, blob_key, size_key, digest_key in self.PINNED_FILES:
                    raw = (checkout / relative).read_bytes()
                    self.assertEqual(recovery._git_blob_sha(raw), recovery.EXPECTED[blob_key])
                    self.assertEqual(len(raw), recovery.EXPECTED[size_key])
                    self.assertEqual(
                        recovery.hashlib.sha256(raw).hexdigest(),
                        recovery.EXPECTED[digest_key],
                    )
            finally:
                self.restore_modules(missing, previous)

    def test_distinct_e1_zenodo_error_is_normalized_to_controller_error(self) -> None:
        class PinnedZenodoError(RuntimeError):
            pass

        pinned_zenodo = type(
            "PinnedZenodo",
            (),
            {"ZenodoError": PinnedZenodoError},
        )
        publisher_module = type("PinnedPublisher", (), {})()
        original_exclusive = lambda *_args: None
        original_atomic = lambda *_args: None
        original_acquire = lambda *_args: None

        def fail_publish(
            _manifest_path: pathlib.Path,
            _root: pathlib.Path,
        ) -> dict[str, Any]:
            raise PinnedZenodoError("pinned E1 transport failure")

        publisher_module.zenodo = pinned_zenodo
        publisher_module.publish = fail_publish
        publisher_module._create_consumption_receipt = original_exclusive
        publisher_module._atomic_recovery_evidence = original_atomic
        publisher_module._acquire_remote_consumption_lock = original_acquire

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=publisher_module,
        ):
            root = pathlib.Path(directory)
            with self.assertRaises(recovery.zenodo.ZenodoError) as raised:
                recovery.run_publisher_with_checkpoints(
                    root / "publish-request.json",
                    root,
                    object(),
                )
        self.assertIs(type(raised.exception), recovery.zenodo.ZenodoError)
        self.assertEqual(str(raised.exception), "pinned E1 transport failure")
        self.assertIs(
            publisher_module._create_consumption_receipt,
            original_exclusive,
        )
        self.assertIs(publisher_module._atomic_recovery_evidence, original_atomic)
        self.assertIs(
            publisher_module._acquire_remote_consumption_lock,
            original_acquire,
        )

    def test_tampered_e1_dependency_byte_blocks_before_publisher_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.checkout_e1(pathlib.Path(directory))
            dependency = checkout / "tools/qikvrt_zenodo_actions.py"
            raw = dependency.read_bytes()
            dependency.write_bytes(bytes((raw[0] ^ 1,)) + raw[1:])
            missing, previous = self.module_snapshot()
            try:
                with self.assertRaisesRegex(
                    SystemExit,
                    "BLOCK: loaded E1 module bytes differ from their exact pin",
                ):
                    recovery._load_e1_publisher(checkout)
                for name, value in previous.items():
                    self.assertIs(sys.modules.get(name, missing), value)
            finally:
                self.restore_modules(missing, previous)


class VRTCoreH3E1RecoveryGitDataTests(unittest.TestCase):
    def call(
        self,
        api: FakeGitData,
        *,
        ref: str = RECOVERY_REF,
        expected_old_sha: str | None,
        commit_sha: str,
    ) -> str:
        return recovery.persist_receipt_create_only_or_ff(
            api,
            repository="Goldkelch/qik-vrt",
            ref=ref,
            expected_old_sha=expected_old_sha,
            commit_sha=commit_sha,
        )

    def test_create_only_uses_one_post_and_exact_readback(self) -> None:
        new = "a" * 40
        api = FakeGitData()
        self.assertEqual(
            self.call(api, expected_old_sha=None, commit_sha=new),
            new,
        )
        self.assertEqual(api.refs, {RECOVERY_REF: new})
        self.assertEqual(len(api.mutations), 1)
        mutation = api.mutations[0]
        self.assertEqual(mutation["method"], "POST")
        self.assertTrue(mutation["path"].endswith("/git/refs"))
        self.assertEqual(
            mutation["payload"], {"ref": RECOVERY_REF, "sha": new}
        )
        self.assertEqual(
            [call["method"] for call in api.calls],
            ["GET", "POST", "GET"],
        )

    def test_fast_forward_uses_one_non_force_patch_and_exact_readback(self) -> None:
        old = "a" * 40
        new = "b" * 40
        api = FakeGitData({RECOVERY_REF: old})
        self.assertEqual(
            self.call(api, expected_old_sha=old, commit_sha=new),
            new,
        )
        self.assertEqual(api.refs[RECOVERY_REF], new)
        self.assertEqual(len(api.mutations), 1)
        mutation = api.mutations[0]
        self.assertEqual(mutation["method"], "PATCH")
        self.assertEqual(mutation["payload"], {"sha": new, "force": False})
        self.assertEqual(
            [call["method"] for call in api.calls],
            ["GET", "PATCH", "GET"],
        )

    def test_conflict_is_accepted_only_after_exact_effect_readback(self) -> None:
        old = "a" * 40
        new = "b" * 40
        for initial, expected_old in (({}, None), ({RECOVERY_REF: old}, old)):
            with self.subTest(operation="create" if expected_old is None else "update"):
                api = FakeGitData(initial)
                api.mutation_result = "conflict_after_effect"
                self.assertEqual(
                    self.call(
                        api,
                        expected_old_sha=expected_old,
                        commit_sha=new,
                    ),
                    new,
                )
                self.assertEqual(len(api.mutations), 1)

                blocked = FakeGitData(initial)
                blocked.mutation_result = "conflict"
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    self.call(
                        blocked,
                        expected_old_sha=expected_old,
                        commit_sha=new,
                    )
                self.assertEqual(len(blocked.mutations), 1)

    def test_ambiguous_transport_is_accepted_only_after_exact_readback(self) -> None:
        old = "a" * 40
        new = "b" * 40
        for initial, expected_old in (({}, None), ({RECOVERY_REF: old}, old)):
            with self.subTest(operation="create" if expected_old is None else "update"):
                api = FakeGitData(initial)
                api.mutation_result = "transport_after_effect"
                self.assertEqual(
                    self.call(
                        api,
                        expected_old_sha=expected_old,
                        commit_sha=new,
                    ),
                    new,
                )
                self.assertEqual(len(api.mutations), 1)

                blocked = FakeGitData(initial)
                blocked.mutation_result = "transport"
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    self.call(
                        blocked,
                        expected_old_sha=expected_old,
                        commit_sha=new,
                    )
                self.assertEqual(len(blocked.mutations), 1)

    def test_create_and_update_preconditions_fail_without_mutation(self) -> None:
        old = "a" * 40
        new = "b" * 40
        cases = (
            (FakeGitData({RECOVERY_REF: old}), None),
            (FakeGitData(), old),
            (FakeGitData({RECOVERY_REF: "c" * 40}), old),
        )
        for api, expected_old in cases:
            with self.subTest(expected_old=expected_old, refs=api.refs):
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    self.call(
                        api,
                        expected_old_sha=expected_old,
                        commit_sha=new,
                    )
                self.assertEqual(api.mutations, [])

    def test_wrong_post_mutation_readback_blocks_without_retry(self) -> None:
        old = "a" * 40
        new = "b" * 40
        api = FakeGitData({RECOVERY_REF: old})
        api.wrong_readback_sha = old
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            self.call(api, expected_old_sha=old, commit_sha=new)
        self.assertEqual(len(api.mutations), 1)

    def test_wrong_success_response_blocks_without_retry(self) -> None:
        old = "a" * 40
        new = "b" * 40
        for initial, expected_old in (({}, None), ({RECOVERY_REF: old}, old)):
            with self.subTest(operation="create" if expected_old is None else "update"):
                api = FakeGitData(initial)
                api.mutation_result = "wrong_response_after_effect"
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    self.call(
                        api,
                        expected_old_sha=expected_old,
                        commit_sha=new,
                    )
                self.assertEqual(len(api.mutations), 1)

    def test_unsafe_ref_and_identifiers_are_rejected_before_transport(self) -> None:
        cases = (
            ("refs/tags/forbidden", None, "a" * 40),
            ("refs/heads/main", None, "a" * 40),
            (RECOVERY_REF + "\n", None, "a" * 40),
            (RECOVERY_REF, "not-a-sha", "a" * 40),
            (RECOVERY_REF, None, "not-a-sha"),
        )
        for ref, old, new in cases:
            api = FakeGitData()
            with self.subTest(ref=ref, old=old, new=new):
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    self.call(
                        api,
                        ref=ref,
                        expected_old_sha=old,
                        commit_sha=new,
                    )
                self.assertEqual(api.calls, [])


class FakeRecoveryReceiptStore:
    def __init__(self, events: list[str], fail_phase: str | None = None) -> None:
        self.events = events
        self.fail_phase = fail_phase

    def persist_and_readback(self, evidence_path: pathlib.Path, phase: str) -> None:
        value = json.loads(evidence_path.read_text(encoding="utf-8"))
        if value.get("phase") != phase:
            raise AssertionError("store phase differs from evidence bytes")
        self.events.append("persist-and-readback:" + phase)
        if phase == self.fail_phase:
            raise SystemExit("BLOCK: simulated remote checkpoint failure")


class VRTCoreH3E1RecoveryCheckpointTests(unittest.TestCase):
    @staticmethod
    def fake_publisher(
        evidence_path: pathlib.Path,
        events: list[str],
    ) -> Any:
        def execute(_manifest_path: pathlib.Path, _root: pathlib.Path) -> str:
            phases = tuple(recovery.CHECKPOINT_PHASES)
            for index, phase in enumerate(phases):
                value = {
                    "schema": publish.EVIDENCE_SCHEMA_V2,
                    "state": publish.CONSUMPTION_STATE,
                    "phase": phase,
                }
                if index == 0:
                    publish._create_consumption_receipt(
                        evidence_path,
                        value,
                        {},
                    )
                else:
                    publish._atomic_recovery_evidence(
                        evidence_path,
                        value,
                        {},
                    )
                if phase == "create_requested":
                    events.append("create_paper")
                elif phase == "publish_requested":
                    events.append("publish_and_poll")
            return "publisher-result"

        return execute

    def test_required_checkpoints_precede_zenodo_create_and_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            evidence_path = root / "zenodo-publication.json"
            events: list[str] = []
            store = FakeRecoveryReceiptStore(events)
            result = recovery.run_publisher_with_checkpoints(
                root / "publish-request.json",
                root,
                store,
                publish_callable=self.fake_publisher(evidence_path, events),
            )
        self.assertEqual(result, "publisher-result")
        self.assertLess(
            events.index("persist-and-readback:authorization_consumed"),
            events.index("persist-and-readback:create_requested"),
        )
        self.assertLess(
            events.index("persist-and-readback:create_requested"),
            events.index("create_paper"),
        )
        self.assertLess(
            events.index("persist-and-readback:publish_requested"),
            events.index("publish_and_poll"),
        )
        self.assertEqual(
            [event for event in events if event.startswith("persist-and-readback:")],
            ["persist-and-readback:" + phase for phase in recovery.CHECKPOINT_PHASES],
        )

    def test_store_mutates_once_then_performs_credential_free_readback(self) -> None:
        persist_source = inspect.getsource(
            recovery.RecoveryReceiptStore.persist_and_readback
        )
        self.assertEqual(persist_source.count("persist_receipt_create_only_or_ff("), 1)
        self.assertEqual(persist_source.count("self._readback("), 1)
        self.assertLess(
            persist_source.index("persist_receipt_create_only_or_ff("),
            persist_source.index("self._readback("),
        )
        readback_source = inspect.getsource(recovery.RecoveryReceiptStore._readback)
        self.assertIn("_fetch_credential_free(self.root, ref, commit)", readback_source)
        credential_free_source = inspect.getsource(recovery._fetch_credential_free)
        self.assertIn("_credential_free_remote_head(root, ref)", credential_free_source)
        self.assertIn("credential_free=True", credential_free_source)

    def test_checkpoint_failure_blocks_before_corresponding_zenodo_effect(self) -> None:
        for phase, forbidden_event in (
            ("create_requested", "create_paper"),
            ("publish_requested", "publish_and_poll"),
        ):
            with self.subTest(phase=phase):
                with tempfile.TemporaryDirectory() as directory:
                    root = pathlib.Path(directory)
                    evidence_path = root / "zenodo-publication.json"
                    events: list[str] = []
                    store = FakeRecoveryReceiptStore(events, fail_phase=phase)
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        recovery.run_publisher_with_checkpoints(
                            root / "publish-request.json",
                            root,
                            store,
                            publish_callable=self.fake_publisher(
                                evidence_path,
                                events,
                            ),
                        )
                self.assertNotIn(forbidden_event, events)

    def test_checkpoint_hook_is_removed_after_publisher_returns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            evidence_path = root / "zenodo-publication.json"
            events: list[str] = []
            store = FakeRecoveryReceiptStore(events)
            recovery.run_publisher_with_checkpoints(
                root / "publish-request.json",
                root,
                store,
                publish_callable=self.fake_publisher(evidence_path, events),
            )
            persisted = len(events)
            publish._atomic_recovery_evidence(
                root / "after-return.json",
                {
                    "schema": publish.EVIDENCE_SCHEMA_V2,
                    "state": publish.CONSUMPTION_STATE,
                    "phase": "prepared",
                },
                {},
            )
        self.assertEqual(len(events), persisted)

    def test_wrapper_rejects_lock_acquisition_and_restores_original(self) -> None:
        original_acquire = publish._acquire_remote_consumption_lock
        effects: list[str] = []

        def attempts_new_lock(
            _manifest_path: pathlib.Path,
            _root: pathlib.Path,
        ) -> dict[str, Any]:
            self.assertIsNot(
                publish._acquire_remote_consumption_lock,
                original_acquire,
            )
            publish._acquire_remote_consumption_lock()
            effects.append("zenodo")
            return {}

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with self.assertRaisesRegex(
                SystemExit,
                "BLOCK: recovery may not acquire or create an authorization lock",
            ):
                recovery.run_publisher_with_checkpoints(
                    root / "publish-request.json",
                    root,
                    object(),
                    publish_callable=attempts_new_lock,
                )
        self.assertIs(publish._acquire_remote_consumption_lock, original_acquire)
        self.assertEqual(effects, [])

    def test_missing_evidence_blocks_with_no_lock_or_zenodo_effect(self) -> None:
        original_acquire = publish._acquire_remote_consumption_lock
        effects: list[str] = []

        def fail_closed_without_evidence(
            _manifest_path: pathlib.Path,
            root: pathlib.Path,
        ) -> dict[str, Any]:
            evidence_path = root / "zenodo-publication.json"
            if not evidence_path.exists():
                raise SystemExit("BLOCK: exact recovery evidence is missing")
            effects.append("lock")
            publish._acquire_remote_consumption_lock()
            effects.append("zenodo")
            return {}

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with self.assertRaisesRegex(
                SystemExit,
                "BLOCK: exact recovery evidence is missing",
            ):
                recovery.run_publisher_with_checkpoints(
                    root / "publish-request.json",
                    root,
                    object(),
                    publish_callable=fail_closed_without_evidence,
                )
        self.assertIs(publish._acquire_remote_consumption_lock, original_acquire)
        self.assertEqual(effects, [])


class VRTCoreH3E1RecoveryRestoreTests(unittest.TestCase):
    @staticmethod
    def store(
        root: pathlib.Path,
        evidence_path: pathlib.Path,
    ) -> recovery.RecoveryReceiptStore:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = root
        store.evidence_path = evidence_path
        store.publication_head = E1
        store.current_tip = "a" * 40
        return store

    def restore(self, root: pathlib.Path, evidence_path: pathlib.Path) -> bytes:
        raw = b'{"phase":"authorization_consumed"}\n'
        store = self.store(root, evidence_path)

        def git(
            _root: pathlib.Path,
            *arguments: str,
            **_kwargs: object,
        ) -> tuple[int, bytes]:
            if arguments == (
                "show",
                f"{'a' * 40}:{recovery.EVIDENCE_RELATIVE.as_posix()}",
            ):
                return 0, raw
            raise AssertionError("unexpected restore Git call: " + repr(arguments))

        with mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ), mock.patch.object(
            recovery,
            "_git",
            side_effect=git,
        ), mock.patch.object(
            store,
            "validate_recovery_chain",
            return_value=[{"phase": "authorization_consumed"}],
        ):
            self.assertEqual(store.restore_or_bootstrap(), (False, "a" * 40))
        return raw

    def test_restore_uses_exclusive_regular_nofollow_write(self) -> None:
        source = inspect.getsource(recovery.RecoveryReceiptStore.restore_or_bootstrap)
        self.assertIn("_write_exclusive_regular(", source)
        self.assertNotIn(".write_bytes(", source)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            evidence_path = root / "state" / "zenodo-publication.json"
            raw = self.restore(root, evidence_path)
            self.assertEqual(evidence_path.read_bytes(), raw)
            self.assertEqual(evidence_path.stat().st_mode & 0o777, 0o600)

    def test_restore_refuses_existing_file_without_changing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            evidence_path = root / "state" / "zenodo-publication.json"
            evidence_path.parent.mkdir(parents=True)
            evidence_path.write_bytes(b"sentinel")
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.restore(root, evidence_path)
            self.assertEqual(evidence_path.read_bytes(), b"sentinel")

    def test_restore_refuses_symlink_without_changing_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            target = root / "target.json"
            target.write_bytes(b"sentinel")
            evidence_path = root / "state" / "zenodo-publication.json"
            evidence_path.parent.mkdir(parents=True)
            evidence_path.symlink_to(target)
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.restore(root, evidence_path)
            self.assertTrue(evidence_path.is_symlink())
            self.assertEqual(target.read_bytes(), b"sentinel")


class VRTCoreH3E1RecoveryRemoteBoundaryTests(unittest.TestCase):
    @staticmethod
    def store(root: pathlib.Path) -> recovery.RecoveryReceiptStore:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = root
        store.api = object()
        store.controller_parent = "d" * 40
        store.manifest_path = root / "publish-request.json"
        store.evidence_path = root / "zenodo-publication.json"
        store.evidence_path.write_text("{}\n", encoding="utf-8")
        store.publisher = publish
        store.manifest = {}
        store.remote_consumption = {"tag_object": recovery.EXPECTED["tag_object"]}
        store.publication_head = E1
        store.current_tip = None
        return store

    def test_remote_recheck_brackets_candidate_before_ref_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(pathlib.Path(directory))
            events: list[str] = []
            validated = {
                "phase": "authorization_consumed",
                "remote_consumption": store.remote_consumption,
            }
            with mock.patch.object(
                publish,
                "_validate_recovery_evidence",
                return_value=validated,
            ), mock.patch.object(
                store,
                "_recheck_remote_boundary",
                side_effect=lambda: events.append("remote-boundary"),
            ), mock.patch.object(
                store,
                "_create_receipt_commit",
                side_effect=lambda *_args: (
                    events.append("local-candidate") or "b" * 40,
                    "c" * 40,
                ),
            ), mock.patch.object(
                recovery,
                "persist_receipt_create_only_or_ff",
                side_effect=lambda *_args, **_kwargs: (
                    events.append("ref-mutation") or "b" * 40
                ),
            ), mock.patch.object(
                store,
                "_readback",
                side_effect=lambda *_args: events.append("readback") or validated,
            ):
                self.assertEqual(
                    store.persist_and_readback(
                        store.evidence_path,
                        "authorization_consumed",
                    ),
                    "b" * 40,
                )
            self.assertEqual(
                events,
                [
                    "remote-boundary",
                    "local-candidate",
                    "remote-boundary",
                    "ref-mutation",
                    "readback",
                ],
            )

    def test_early_remote_drift_blocks_candidate_and_ref_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(pathlib.Path(directory))
            validated = {
                "phase": "authorization_consumed",
                "remote_consumption": store.remote_consumption,
            }
            with mock.patch.object(
                publish,
                "_validate_recovery_evidence",
                return_value=validated,
            ), mock.patch.object(
                store,
                "_recheck_remote_boundary",
                side_effect=SystemExit("BLOCK: simulated remote drift"),
            ), mock.patch.object(
                store,
                "_create_receipt_commit",
            ) as create, mock.patch.object(
                recovery,
                "persist_receipt_create_only_or_ff",
            ) as mutate:
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    store.persist_and_readback(
                        store.evidence_path,
                        "authorization_consumed",
                    )
            create.assert_not_called()
            mutate.assert_not_called()

    def test_late_remote_drift_blocks_after_candidate_before_ref_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(pathlib.Path(directory))
            validated = {
                "phase": "authorization_consumed",
                "remote_consumption": store.remote_consumption,
            }
            checks = 0

            def recheck() -> None:
                nonlocal checks
                checks += 1
                if checks == 2:
                    raise SystemExit("BLOCK: simulated late remote drift")

            with mock.patch.object(
                publish,
                "_validate_recovery_evidence",
                return_value=validated,
            ), mock.patch.object(
                store,
                "_recheck_remote_boundary",
                side_effect=recheck,
            ), mock.patch.object(
                store,
                "_create_receipt_commit",
                return_value=("b" * 40, "c" * 40),
            ) as create, mock.patch.object(
                recovery,
                "persist_receipt_create_only_or_ff",
            ) as mutate:
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    store.persist_and_readback(
                        store.evidence_path,
                        "authorization_consumed",
                    )
            self.assertEqual(checks, 2)
            create.assert_called_once_with(E1, "authorization_consumed")
            mutate.assert_not_called()


class VRTCoreH3E1RecoveryReplayTests(unittest.TestCase):
    RECORD_ID = 123456
    DOI = "10.5281/zenodo.123456"

    @classmethod
    def chain(cls, *, include_prepared: bool = True) -> list[dict[str, Any]]:
        identity = {"record_id": cls.RECORD_ID, "doi": cls.DOI}
        chain: list[dict[str, Any]] = []
        if include_prepared:
            chain.append({"phase": "prepared", **identity})
        chain.append({"phase": "publish_requested", **identity})
        return chain

    @staticmethod
    def store(root: pathlib.Path) -> recovery.RecoveryReceiptStore:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = root
        store.api = object()
        store.controller_parent = "d" * 40
        store.manifest_path = root / "publish-request.json"
        store.evidence_path = root / "zenodo-publication.json"
        store.publisher = publish
        store.manifest = {}
        store.remote_consumption = {"tag_object": recovery.EXPECTED["tag_object"]}
        store.publication_head = E1
        store.current_tip = "a" * 40
        store._prepared_replay_pending = False
        return store

    @staticmethod
    def validated(
        store: recovery.RecoveryReceiptStore,
        phase: str,
        *,
        record_id: int = RECORD_ID,
        doi: str = DOI,
    ) -> dict[str, Any]:
        return {
            "phase": phase,
            "remote_consumption": store.remote_consumption,
            "record_id": record_id,
            "doi": doi,
        }

    def test_prepared_replay_requires_and_confirms_identical_publish_intent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(pathlib.Path(directory))
            chain = self.chain()
            store.evidence_path.write_text(
                json.dumps({"phase": "prepared"}) + "\n",
                encoding="utf-8",
            )

            def validate(value: Mapping[str, Any], *_args: Any) -> dict[str, Any]:
                return self.validated(store, str(value["phase"]))

            with mock.patch.object(
                publish,
                "_validate_recovery_evidence",
                side_effect=validate,
            ), mock.patch.object(
                store,
                "_recheck_remote_boundary",
            ), mock.patch.object(
                store,
                "validate_recovery_chain",
                return_value=chain,
            ), mock.patch.object(
                store,
                "_create_receipt_commit",
            ) as create, mock.patch.object(
                recovery,
                "persist_receipt_create_only_or_ff",
            ) as mutate:
                self.assertEqual(
                    store.persist_and_readback(store.evidence_path, "prepared"),
                    "a" * 40,
                )
                self.assertTrue(store._prepared_replay_pending)

                requested_raw = (
                    json.dumps({"phase": "publish_requested"}) + "\n"
                ).encode("utf-8")
                store.evidence_path.write_bytes(requested_raw)
                with mock.patch.object(
                    recovery,
                    "_git",
                    return_value=(0, requested_raw),
                ) as git:
                    self.assertEqual(
                        store.persist_and_readback(
                            store.evidence_path,
                            "publish_requested",
                        ),
                        "a" * 40,
                    )
                git.assert_called_once_with(
                    store.root,
                    "show",
                    "a" * 40 + ":" + recovery.EVIDENCE_RELATIVE.as_posix(),
                )
            self.assertFalse(store._prepared_replay_pending)
            create.assert_not_called()
            mutate.assert_not_called()

    def test_prepared_replay_without_prior_prepared_or_same_identity_blocks(
        self,
    ) -> None:
        cases = (
            ("no-prior-prepared", self.chain(include_prepared=False), self.RECORD_ID, self.DOI),
            ("record-id-differs", self.chain(), self.RECORD_ID + 1, self.DOI),
            ("doi-differs", self.chain(), self.RECORD_ID, self.DOI + ".1"),
        )
        for label, chain, record_id, doi in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                store = self.store(pathlib.Path(directory))
                store.evidence_path.write_text(
                    json.dumps({"phase": "prepared"}) + "\n",
                    encoding="utf-8",
                )
                validated = self.validated(
                    store,
                    "prepared",
                    record_id=record_id,
                    doi=doi,
                )
                with mock.patch.object(
                    publish,
                    "_validate_recovery_evidence",
                    return_value=validated,
                ), mock.patch.object(
                    store,
                    "_recheck_remote_boundary",
                ), mock.patch.object(
                    store,
                    "validate_recovery_chain",
                    return_value=chain,
                ), mock.patch.object(
                    store,
                    "_create_receipt_commit",
                ) as create, mock.patch.object(
                    recovery,
                    "persist_receipt_create_only_or_ff",
                ) as mutate:
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        store.persist_and_readback(
                            store.evidence_path,
                            "prepared",
                        )
                self.assertFalse(store._prepared_replay_pending)
                create.assert_not_called()
                mutate.assert_not_called()

    def test_replayed_publish_confirmation_with_changed_identity_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(pathlib.Path(directory))
            chain = self.chain()
            store.evidence_path.write_text(
                json.dumps({"phase": "prepared"}) + "\n",
                encoding="utf-8",
            )
            validation = self.validated(store, "prepared")
            with mock.patch.object(
                publish,
                "_validate_recovery_evidence",
                side_effect=lambda *_args: validation,
            ), mock.patch.object(
                store,
                "_recheck_remote_boundary",
            ), mock.patch.object(
                store,
                "validate_recovery_chain",
                return_value=chain,
            ), mock.patch.object(
                store,
                "_create_receipt_commit",
            ) as create, mock.patch.object(
                recovery,
                "persist_receipt_create_only_or_ff",
            ) as mutate:
                store.persist_and_readback(store.evidence_path, "prepared")
                self.assertTrue(store._prepared_replay_pending)
                store.evidence_path.write_text(
                    json.dumps({"phase": "publish_requested"}) + "\n",
                    encoding="utf-8",
                )
                validation = self.validated(
                    store,
                    "publish_requested",
                    record_id=self.RECORD_ID + 1,
                )
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    store.persist_and_readback(
                        store.evidence_path,
                        "publish_requested",
                    )
            self.assertTrue(store._prepared_replay_pending)
            create.assert_not_called()
            mutate.assert_not_called()


class VRTCoreH3E1RecoveryReceiptVerificationTests(unittest.TestCase):
    EFFECT_DATE = "2026-08-01T12:34:56+00:00"
    BOT_NAME = "qik-vrt-zenodo-publication[bot]"
    BOT_EMAIL = "qik-vrt-zenodo-publication[bot]@users.noreply.github.com"

    @classmethod
    def provenance_fields(cls) -> list[str]:
        return [
            "zenodo: persist VRTCore h3 recovery receipt",
            "",
            cls.BOT_NAME,
            cls.BOT_EMAIL,
            cls.EFFECT_DATE,
            cls.BOT_NAME,
            cls.BOT_EMAIL,
            cls.EFFECT_DATE,
        ]

    @staticmethod
    def provenance_raw(fields: list[str]) -> bytes:
        return "\0".join(fields).encode("utf-8") + b"\n"

    def test_receipt_message_author_committer_and_date_tamper_block(self) -> None:
        exact = self.provenance_fields()
        with mock.patch.object(
            recovery,
            "_git",
            side_effect=[
                (0, (self.EFFECT_DATE + "\n").encode("ascii")),
                (0, self.provenance_raw(exact)),
            ],
        ):
            recovery._validate_receipt_commit_provenance(
                ROOT,
                "b" * 40,
                "prepared",
            )

        for label, index, changed in (
            ("message", 0, "tampered receipt message"),
            ("author", 2, "untrusted author"),
            ("committer", 5, "untrusted committer"),
            ("date", 4, "2026-08-01T12:34:57+00:00"),
        ):
            with self.subTest(label=label):
                tampered = exact.copy()
                tampered[index] = changed
                with mock.patch.object(
                    recovery,
                    "_git",
                    side_effect=[
                        (0, (self.EFFECT_DATE + "\n").encode("ascii")),
                        (0, self.provenance_raw(tampered)),
                    ],
                ):
                    with self.assertRaisesRegex(
                        SystemExit,
                        "BLOCK: fetched receipt commit provenance differs",
                    ):
                        recovery._validate_receipt_commit_provenance(
                            ROOT,
                            "b" * 40,
                            "prepared",
                        )

    @staticmethod
    def finalized_store(root: pathlib.Path) -> recovery.RecoveryReceiptStore:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = root
        store.api = object()
        return store

    def verify_finalized(
        self,
        store: recovery.RecoveryReceiptStore,
        evidence: dict[str, Any],
        prior: dict[str, Any],
    ) -> dict[str, Any]:
        parent = "a" * 40
        with mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ), mock.patch.object(
            store,
            "_parent_of",
            return_value=parent,
        ), mock.patch.object(
            recovery,
            "_validate_receipt_commit",
            return_value=evidence,
        ), mock.patch.object(
            recovery,
            "_read_head_ref",
            return_value=parent,
        ), mock.patch.object(
            store,
            "validate_recovery_chain",
            return_value=[prior],
        ):
            return store.verify_finalized("f" * 40)

    def test_finalized_must_match_last_publish_intent_identity(self) -> None:
        remote_consumption = {
            "tag_object": recovery.EXPECTED["tag_object"],
            "authorization_id": "qikvrt-test-authorization",
        }
        evidence = {
            "phase": "public_verified",
            "remote_consumption": remote_consumption,
            "record_id": 123456,
            "doi": "10.5281/zenodo.123456",
        }
        matching_prior = {
            "phase": "publish_requested",
            "remote_consumption": remote_consumption,
            "record_id": evidence["record_id"],
            "doi": evidence["doi"],
        }
        with tempfile.TemporaryDirectory() as directory:
            store = self.finalized_store(pathlib.Path(directory))
            self.assertIs(
                self.verify_finalized(store, evidence, matching_prior),
                evidence,
            )
            tampered_cases = (
                (
                    "remote-consumption",
                    {
                        **matching_prior,
                        "remote_consumption": {
                            **remote_consumption,
                            "tag_object": "0" * 40,
                        },
                    },
                ),
                (
                    "record-id",
                    {**matching_prior, "record_id": evidence["record_id"] + 1},
                ),
                (
                    "doi",
                    {**matching_prior, "doi": evidence["doi"] + ".1"},
                ),
            )
            for label, prior in tampered_cases:
                with self.subTest(label=label):
                    with self.assertRaisesRegex(
                        SystemExit,
                        "BLOCK: finalized publication diverges from durable publish intent",
                    ):
                        self.verify_finalized(store, evidence, prior)

    def test_recovery_chain_must_be_an_exact_phase_prefix(self) -> None:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = ROOT
        store.publisher = publish
        store.remote_consumption = {
            "tag_object": recovery.EXPECTED["tag_object"],
        }
        first = "a" * 40
        tip = "b" * 40
        parents = {tip: first, first: E1}
        evidence = {
            first: {
                "phase": "authorization_consumed",
                "remote_consumption": store.remote_consumption,
            },
            tip: {
                "phase": "record_created",
                "remote_consumption": store.remote_consumption,
                "record_id": 123456,
                "doi": "10.5281/zenodo.123456",
            },
        }
        with mock.patch.object(
            store,
            "_parent_of",
            side_effect=lambda commit: parents[commit],
        ), mock.patch.object(
            recovery,
            "_validate_receipt_commit",
            side_effect=lambda _root, commit, _parent: evidence[commit],
        ):
            with self.assertRaisesRegex(
                SystemExit,
                "BLOCK: recovery receipt chain is not the exact phase prefix",
            ):
                store.validate_recovery_chain(tip)


class VRTCoreH3E1RecoveryLocalCandidateTests(unittest.TestCase):
    @staticmethod
    def git(root: pathlib.Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(
                "fixture Git failed: "
                + " ".join(arguments)
                + "\n"
                + result.stderr
            )
        return result.stdout.strip()

    @classmethod
    def materialize_e1(cls, base: pathlib.Path) -> pathlib.Path:
        root = base / "e1"
        root.mkdir()
        cls.git(root, "init", "--quiet")
        common_raw = cls.git(ROOT, "rev-parse", "--git-common-dir")
        common = pathlib.Path(common_raw)
        if not common.is_absolute():
            common = (ROOT / common).resolve()
        info = root / ".git" / "objects" / "info"
        info.mkdir(parents=True, exist_ok=True)
        (info / "alternates").write_text(
            str((common / "objects").resolve()) + "\n",
            encoding="utf-8",
        )
        cls.git(root, "checkout", "--quiet", "--detach", E1)
        if cls.git(root, "rev-parse", "HEAD") != E1:
            raise AssertionError("temporary worktree is not exact E1")
        return root

    @staticmethod
    def prepare_candidate(root: pathlib.Path) -> pathlib.Path:
        evidence_path = root / recovery.EVIDENCE_RELATIVE
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(b'{"fixture":"local-receipt-candidate"}\n')
        result = recovery.integrity.generate(root)
        if not result.ok:
            raise AssertionError("cannot generate local candidate integrity")
        return evidence_path

    def test_exact_e1_plus_receipt_paths_is_the_only_local_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.materialize_e1(pathlib.Path(directory))
            evidence_path = self.prepare_candidate(root)
            recovery._validate_local_receipt_candidate(
                root,
                E1,
                evidence_path,
            )

            unexpected = root / "unexpected.txt"
            unexpected.write_text("untracked\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                recovery._validate_local_receipt_candidate(
                    root,
                    E1,
                    evidence_path,
                )
            unexpected.unlink()

            tracked = root / "README.md"
            original = tracked.read_bytes()
            tracked.write_bytes(original + b"\nforeign delta\n")
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                recovery._validate_local_receipt_candidate(
                    root,
                    E1,
                    evidence_path,
                )
            tracked.write_bytes(original)

    def test_invalid_local_candidate_blocks_before_ref_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.materialize_e1(pathlib.Path(directory))
            evidence_path = self.prepare_candidate(root)
            (root / "unexpected.txt").write_text("untracked\n", encoding="utf-8")
            store = object.__new__(recovery.RecoveryReceiptStore)
            store.root = root
            store.evidence_path = evidence_path
            store.api = object()
            with mock.patch.object(
                store,
                "_prepare_integrity",
            ), mock.patch.object(
                recovery,
                "_call_api",
            ) as object_api, mock.patch.object(
                recovery,
                "persist_receipt_create_only_or_ff",
            ) as ref_mutation:
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    store._create_receipt_commit(E1, "authorization_consumed")
            object_api.assert_not_called()
            ref_mutation.assert_not_called()

    def test_candidate_validation_precedes_every_remote_object_or_ref_write(self) -> None:
        create_source = inspect.getsource(
            recovery.RecoveryReceiptStore._create_receipt_commit
        )
        self.assertLess(
            create_source.index("_validate_local_receipt_candidate("),
            create_source.index("_call_api("),
        )
        checkpoint_source = inspect.getsource(
            recovery.RecoveryReceiptStore.persist_and_readback
        )
        self.assertLess(
            checkpoint_source.index("self._create_receipt_commit("),
            checkpoint_source.index("persist_receipt_create_only_or_ff("),
        )


class FakeIncidentAPI:
    def __init__(self, log: bytes) -> None:
        run_id = recovery.EXPECTED["run_id"]
        job_id = recovery.EXPECTED["job_id"]
        self.log = log
        self.calls: list[tuple[str, str]] = []
        self.run = {
            "id": run_id,
            "run_attempt": 1,
            "head_sha": E1,
            "head_branch": PUBLICATION_REF.removeprefix("refs/heads/"),
            "status": "completed",
            "conclusion": "failure",
            "repository": {"full_name": "Goldkelch/qik-vrt"},
            "head_repository": {"full_name": "Goldkelch/qik-vrt"},
        }
        self.job = {
            "id": job_id,
            "run_id": run_id,
            "run_attempt": 1,
            "head_sha": E1,
            "status": "completed",
            "conclusion": "failure",
            "run_url": (
                "https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs/"
                + str(run_id)
            ),
        }
        self.artifacts = {"total_count": 0, "artifacts": []}

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        **_kwargs: object,
    ) -> tuple[int, dict[str, Any]]:
        if method != "GET" or payload is not None:
            raise AssertionError("historical incident API attempted a mutation")
        self.calls.append((method, path))
        run_path = (
            "/repos/Goldkelch/qik-vrt/actions/runs/"
            + str(recovery.EXPECTED["run_id"])
        )
        job_path = (
            "/repos/Goldkelch/qik-vrt/actions/jobs/"
            + str(recovery.EXPECTED["job_id"])
        )
        if path == run_path + "/attempts/1":
            return 200, copy.deepcopy(self.run)
        if path == job_path:
            return 200, copy.deepcopy(self.job)
        if path == run_path + "/artifacts":
            return 200, copy.deepcopy(self.artifacts)
        raise AssertionError("unexpected historical incident path: " + path)

    def request_bytes(self, path: str, maximum: int) -> bytes:
        expected = (
            "/repos/Goldkelch/qik-vrt/actions/jobs/"
            + str(recovery.EXPECTED["job_id"])
            + "/logs"
        )
        if path != expected or maximum != recovery.EXPECTED["job_log_bytes"]:
            raise AssertionError("historical log request differs")
        self.calls.append(("GET_BYTES", path))
        return self.log


class VRTCoreH3E1RecoveryIncidentTests(unittest.TestCase):
    @staticmethod
    def log_bytes() -> bytes:
        lines: list[str] = []
        for marker, count in recovery.INCIDENT_LOG_REQUIRED_COUNTS.items():
            lines.extend(marker for _index in range(count))
        prefix = ("\n".join(lines) + "\n").encode("utf-8")
        size = recovery.EXPECTED["job_log_bytes"]
        if len(prefix) > size:
            raise AssertionError("incident fixture exceeds its exact size")
        return prefix + b"x" * (size - len(prefix))

    @staticmethod
    def verify(api: FakeIncidentAPI, *, digest_for: bytes) -> None:
        real_sha256 = recovery.hashlib.sha256

        class FixedDigest:
            def hexdigest(self) -> str:
                return recovery.EXPECTED["job_log_sha256"]

        def sha256(raw: bytes = b"") -> Any:
            if raw == digest_for:
                return FixedDigest()
            return real_sha256(raw)

        with mock.patch.object(recovery.hashlib, "sha256", side_effect=sha256):
            recovery.verify_historical_incident(
                api,
                recovery.load_recovery_basis(),
            )

    def test_exact_historical_run_job_log_and_artifacts_are_read_only(self) -> None:
        raw = self.log_bytes()
        api = FakeIncidentAPI(raw)
        self.verify(api, digest_for=raw)
        self.assertEqual(
            [method for method, _path in api.calls],
            ["GET", "GET", "GET", "GET_BYTES"],
        )

    def test_historical_metadata_or_artifact_tampering_fails_closed(self) -> None:
        raw = self.log_bytes()
        cases: list[tuple[str, Any]] = []
        run_api = FakeIncidentAPI(raw)
        run_api.run["head_sha"] = "c" * 40
        cases.append(("run", run_api))
        job_api = FakeIncidentAPI(raw)
        job_api.job["run_id"] = recovery.EXPECTED["run_id"] + 1
        cases.append(("job", job_api))
        artifact_api = FakeIncidentAPI(raw)
        artifact_api.artifacts = {
            "total_count": 1,
            "artifacts": [{"id": 1}],
        }
        cases.append(("artifacts", artifact_api))
        for label, api in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    self.verify(api, digest_for=raw)
                self.assertTrue(
                    all(method in {"GET", "GET_BYTES"} for method, _path in api.calls)
                )

    def test_historical_log_byte_or_marker_tampering_fails_closed(self) -> None:
        raw = self.log_bytes()
        byte_tampered = raw[:-1] + (b"y" if raw[-1:] != b"y" else b"z")
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            self.verify(FakeIncidentAPI(byte_tampered), digest_for=raw)

        marker = next(iter(recovery.INCIDENT_LOG_REQUIRED_COUNTS))
        replacement = "_" * len(marker)
        marker_tampered = raw.replace(
            marker.encode("utf-8"),
            replacement.encode("utf-8"),
            1,
        )
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            self.verify(
                FakeIncidentAPI(marker_tampered),
                digest_for=marker_tampered,
            )


if __name__ == "__main__":
    unittest.main()
