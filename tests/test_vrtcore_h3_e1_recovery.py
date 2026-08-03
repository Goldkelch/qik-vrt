# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import types
import urllib.parse
import unittest
from typing import Any, Mapping
from unittest import mock

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
        self.transient_post_mutation_404s = 0
        self.mutation_observed = False

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
            if self.mutation_observed and self.transient_post_mutation_404s:
                self.transient_post_mutation_404s -= 1
                return 404, {}
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
            self.mutation_observed = True
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
            self.mutation_observed = True
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

    def test_r9_push_and_run_attempt_are_exactly_one_shot(self) -> None:
        for gate in (
            "github.run_attempt == 1",
            "github.event.created == false",
            "github.event.deleted == false",
            "github.event.forced == false",
            "github.event.before == "
            "'6edde9cbcc0fb57cd29ab71de6718228cc258d80'",
            "github.event.after == github.sha",
            'test "$GITHUB_RUN_ATTEMPT" = "1"',
            'test "${{ github.event.before }}" = '
            '"$EXPECTED_CONTROLLER_PREDECESSOR"',
            'test "${{ github.event.after }}" = "$GITHUB_SHA"',
        ):
            self.assertIn(gate, self.workflow)

    def test_main_arms_only_c2_reconciliation_and_passes_exact_record(self) -> None:
        source = inspect.getsource(recovery.main)
        self.assertIn("store.arm_exact_record_created_reconciliation()", source)
        self.assertNotIn("store.arm_exact_unsent_create_replay()", source)
        self.assertIn("reconcile_record=(", source)
        self.assertIn(
            'R8_DESCRIPTION_NORMALIZATION_INCIDENT["record_id"]', source
        )
        self.assertIn('R8_DESCRIPTION_NORMALIZATION_INCIDENT["doi"]', source)

    def test_marker_is_create_only_and_cannot_trigger_any_zenodo_workflow(self) -> None:
        source = inspect.getsource(recovery.persist_create_post_once_marker)
        self.assertEqual(source.count('"POST"'), 1)
        for forbidden in ('"PATCH"', '"DELETE"', '"force"'):
            self.assertNotIn(forbidden, source)
        marker_branch = recovery.EXPECTED["create_post_once_ref"].removeprefix(
            "refs/heads/"
        )
        workflows: list[tuple[str, str]] = [
            (str(path), path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
        ]
        c1 = str(recovery.R4_UNSENT_CREATE_INCIDENT["c1"])
        historical_paths = subprocess.check_output(
            [
                "git",
                "ls-tree",
                "-r",
                "--name-only",
                c1,
                ".github/workflows",
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
        workflows.extend(
            (
                c1 + ":" + path,
                subprocess.check_output(
                    ["git", "show", c1 + ":" + path],
                    cwd=ROOT,
                    text=True,
                ),
            )
            for path in historical_paths
            if pathlib.PurePosixPath(path).suffix in {".yml", ".yaml"}
        )
        for name, text in workflows:
            if "ZENODO_ACCESS_TOKEN" not in text:
                continue
            trigger = text.split("permissions:", 1)[0]
            self.assertIn("branches:", trigger, msg=name)
            self.assertNotIn(marker_branch, trigger, msg=name)

    def test_parent_placeholder_is_unique_and_fails_closed(self) -> None:
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

    def test_materialized_controller_keeps_one_sentinel_and_exact_gates(self) -> None:
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
            '"$EXPECTED_CONTROLLER_PREDECESSOR"',
            '"$EXPECTED_CONTROLLER_PREDECESSOR_PARENT"',
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
                "tests/test_vrtcore_h3_e1_recovery.py",
                "tools/qikvrt_vrtcore_h3_e1_recovery.py",
            ],
        )

    def test_r9_is_exact_direct_child_of_r8_with_full_r7_to_r0_lineage(self) -> None:
        bindings = dict(
            re.findall(
                r"(?m)^\s*(EXPECTED_CONTROLLER_[A-Z_]+):\s*([0-9a-f]{40})\s*$",
                self.workflow,
            )
        )
        self.assertEqual(
            bindings,
            {
                "EXPECTED_CONTROLLER_PARENT": (
                    "bad1a0558b88b9bc13a6b47fe621ac27d8bfaa62"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR": (
                    "6edde9cbcc0fb57cd29ab71de6718228cc258d80"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_TREE": (
                    "9cefcb13ed1e7efdc11f7ccf844544b5e5e280d3"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_PARENT": (
                    "d941ca6b792d569b2c37c571123c7524a53c33fd"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_GRANDPARENT": (
                    "eec6f14ad937e15764d28ccf4fc5afef0c198236"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GRANDPARENT": (
                    "8db28488afa35549eea640f40f98321c1e56a4e0"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GRANDPARENT": (
                    "dfcf28f9f48b5857ef3b4ef50f979d9a1979be08"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GRANDPARENT": (
                    "89fa9a49a73a7194ccdbed080e9dbdc26a506d5e"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GREAT_GRANDPARENT": (
                    "0d104a2692be53f47f2f200d710d2190dfa2f46d"
                ),
                "EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GREAT_GREAT_GRANDPARENT": (
                    "4e794afb21c8e5a31ff713b15b77890bbbd950c4"
                ),
            },
        )
        self.assertIn(
            'test "$(git -C controller show -s --format=%P HEAD)" = \\\n'
            '            "$EXPECTED_CONTROLLER_PREDECESSOR"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
            '              "$EXPECTED_CONTROLLER_PREDECESSOR"\n'
            '          )" = "$EXPECTED_CONTROLLER_PREDECESSOR_PARENT"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller rev-parse --verify \\\n'
            '              "$EXPECTED_CONTROLLER_PREDECESSOR^{tree}"\n'
            '          )" = "$EXPECTED_CONTROLLER_PREDECESSOR_TREE"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
            '              "$EXPECTED_CONTROLLER_PREDECESSOR_PARENT"\n'
            '          )" = "$EXPECTED_CONTROLLER_PREDECESSOR_GRANDPARENT"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
            '              "$EXPECTED_CONTROLLER_PREDECESSOR_GRANDPARENT"\n'
            '          )" = "$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GRANDPARENT"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
            '              "$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GRANDPARENT"\n'
            '          )" = '
            '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GRANDPARENT"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
            '              '
            '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GRANDPARENT"\n'
            '          )" = '
            '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GRANDPARENT"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
            '              '
            '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GRANDPARENT"\n'
            '          )" = \\\n'
            '            '
            '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GREAT_GRANDPARENT"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
              '              '
              '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GREAT_GRANDPARENT"\n'
            '          )" = \\\n'
            '            '
            '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GREAT_GREAT_GRANDPARENT"',
            self.workflow,
        )
        self.assertIn(
            'git -C controller show -s --format=%P \\\n'
            '              '
            '"$EXPECTED_CONTROLLER_PREDECESSOR_GREAT_GREAT_GREAT_GREAT_GREAT_GRANDPARENT"\n'
            '          )" = "$EXPECTED_CONTROLLER_PARENT"',
            self.workflow,
        )

    def test_prepare_step_reads_its_output_file_not_self_step_context(self) -> None:
        step_start = self.workflow.index(
            "      - name: Persist and read back authorization_consumed before Zenodo"
        )
        step_end = self.workflow.index("\n      - name:", step_start + 1)
        prepare_step = self.workflow[step_start:step_end]
        self.assertNotIn("${{ steps.prepare.outputs.", prepare_step)
        self.assertIn("grep -Fx 'prepared=true' \"$GITHUB_OUTPUT\"", prepare_step)
        self.assertIn(
            "grep -Eq '^finalized=(true|false)$' \"$GITHUB_OUTPUT\"",
            prepare_step,
        )
        self.assertIn(
            "grep -Eq '^receipt_commit=[0-9a-f]{40}$' \"$GITHUB_OUTPUT\"",
            prepare_step,
        )
        later_workflow = self.workflow[step_end:]
        self.assertIn("steps.prepare.outputs.prepared", later_workflow)
        self.assertIn("steps.prepare.outputs.receipt_commit", later_workflow)

    def test_no_step_reads_its_own_outputs_during_that_step(self) -> None:
        step_blocks = re.split(r"(?m)(?=^      - name: )", self.workflow)
        checked_ids: list[str] = []
        for step_block in step_blocks:
            binding = re.search(
                r"(?m)^        id:\s*([A-Za-z_][A-Za-z0-9_-]*)\s*$",
                step_block,
            )
            if binding is None:
                continue
            step_id = binding.group(1)
            checked_ids.append(step_id)
            self.assertNotIn(
                "${{ steps." + step_id + ".outputs.",
                step_block,
                msg=f"step {step_id!r} reads its own unavailable outputs",
            )
        self.assertEqual(checked_ids, ["prepare", "publish"])

    def test_workflow_serializes_with_the_original_publisher(self) -> None:
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
    def setUp(self) -> None:
        patcher = mock.patch.object(recovery.time, "sleep")
        self.addCleanup(patcher.stop)
        self.sleep = patcher.start()

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

    def test_exact_existing_target_is_idempotent_without_mutation(self) -> None:
        target = "a" * 40
        for expected_old in (None, "b" * 40):
            with self.subTest(expected_old=expected_old):
                api = FakeGitData({RECOVERY_REF: target})
                self.assertEqual(
                    self.call(
                        api,
                        expected_old_sha=expected_old,
                        commit_sha=target,
                    ),
                    target,
                )
                self.assertEqual(api.mutations, [])
                self.assertEqual([call["method"] for call in api.calls], ["GET"])

    def test_transient_post_mutation_404_reconciles_read_only(self) -> None:
        target = "a" * 40
        api = FakeGitData()
        api.transient_post_mutation_404s = 2
        self.assertEqual(
            self.call(api, expected_old_sha=None, commit_sha=target),
            target,
        )
        self.assertEqual(len(api.mutations), 1)
        self.assertEqual(
            [call["method"] for call in api.calls],
            ["GET", "POST", "GET", "GET", "GET"],
        )
        self.assertEqual(
            [call.args[0] for call in self.sleep.call_args_list],
            list(recovery.REF_RECONCILIATION_DELAYS_SECONDS[:2]),
        )

    def test_persistent_post_mutation_404_blocks_without_mutation_retry(self) -> None:
        target = "a" * 40
        api = FakeGitData()
        api.transient_post_mutation_404s = (
            len(recovery.REF_RECONCILIATION_DELAYS_SECONDS) + 1
        )
        with self.assertRaisesRegex(
            SystemExit,
            "BLOCK: receipt ref mutation has no exact readback",
        ):
            self.call(api, expected_old_sha=None, commit_sha=target)
        self.assertEqual(len(api.mutations), 1)
        self.assertEqual(
            [call["method"] for call in api.calls],
            ["GET", "POST"]
            + ["GET"] * (len(recovery.REF_RECONCILIATION_DELAYS_SECONDS) + 1),
        )
        self.assertEqual(
            [call.args[0] for call in self.sleep.call_args_list],
            list(recovery.REF_RECONCILIATION_DELAYS_SECONDS),
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

    def test_wrong_success_response_is_advisory_after_exact_get_readback(self) -> None:
        old = "a" * 40
        new = "b" * 40
        for initial, expected_old in (({}, None), ({RECOVERY_REF: old}, old)):
            with self.subTest(operation="create" if expected_old is None else "update"):
                api = FakeGitData(initial)
                api.mutation_result = "wrong_response_after_effect"
                self.assertEqual(
                    self.call(
                        api,
                        expected_old_sha=expected_old,
                        commit_sha=new,
                    ),
                    new,
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


class VRTCoreH3E1CreatePostOnceMarkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ROOT
        self.target = str(recovery.R4_UNSENT_CREATE_INCIDENT["c1"])
        self.ref = recovery.EXPECTED["create_post_once_ref"]

    def call(self, api: FakeGitData) -> str:
        with mock.patch.object(recovery, "_fetch_credential_free") as fetch:
            result = recovery.persist_create_post_once_marker(
                api,
                self.root,
                repository=recovery.EXPECTED["repository"],
                commit_sha=self.target,
            )
        fetch.assert_called_once_with(self.root, self.ref, self.target)
        return result

    def test_marker_requires_own_201_auth_get_and_anonymous_readback(self) -> None:
        api = FakeGitData()
        self.assertEqual(self.call(api), self.target)
        self.assertEqual(api.refs, {self.ref: self.target})
        self.assertEqual(
            [call["method"] for call in api.calls],
            ["GET", "POST", "GET"],
        )
        self.assertEqual(len(api.mutations), 1)
        self.assertEqual(
            api.mutations[0]["payload"],
            {"ref": self.ref, "sha": self.target},
        )

    def test_existing_marker_never_counts_as_this_invocations_success(self) -> None:
        api = FakeGitData({self.ref: self.target})
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            self.call(api)
        self.assertEqual(api.mutations, [])

    def test_conflict_or_ambiguous_transport_never_reconciles_marker(self) -> None:
        for result in (
            "conflict",
            "conflict_after_effect",
            "transport",
            "transport_after_effect",
        ):
            with self.subTest(result=result):
                api = FakeGitData()
                api.mutation_result = result
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    self.call(api)
                self.assertEqual(len(api.mutations), 1)

    def test_wrong_201_body_or_wrong_authenticated_readback_blocks(self) -> None:
        wrong_body = FakeGitData()
        wrong_body.mutation_result = "wrong_response_after_effect"
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            self.call(wrong_body)
        self.assertEqual(len(wrong_body.mutations), 1)

        wrong_get = FakeGitData()
        wrong_get.wrong_readback_sha = "c" * 40
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            self.call(wrong_get)
        self.assertEqual(len(wrong_get.mutations), 1)

    def test_anonymous_readback_failure_blocks_after_one_marker_post(self) -> None:
        api = FakeGitData()
        with mock.patch.object(
            recovery,
            "_fetch_credential_free",
            side_effect=SystemExit("BLOCK: simulated anonymous readback failure"),
        ):
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                recovery.persist_create_post_once_marker(
                    api,
                    self.root,
                    repository=recovery.EXPECTED["repository"],
                    commit_sha=self.target,
                )
        self.assertEqual(len(api.mutations), 1)


class VRTCoreH3E1InitialCreateReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.c1 = str(recovery.R4_UNSENT_CREATE_INCIDENT["c1"])
        cls.c1_raw = subprocess.check_output(
            [
                "git",
                "show",
                cls.c1 + ":" + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
        )
        cls.c1_value = json.loads(cls.c1_raw.decode("utf-8"))

    def store(self, root: pathlib.Path) -> recovery.RecoveryReceiptStore:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = root
        store.api = object()
        store.controller_parent = "d" * 40
        store.manifest_path = root / "publish-request.json"
        store.evidence_path = root / recovery.EVIDENCE_RELATIVE
        store.evidence_path.parent.mkdir(parents=True)
        store.evidence_path.write_bytes(b"{}\n")
        store.publisher = publish
        store.manifest = {}
        store.remote_consumption = self.c1_value["remote_consumption"]
        store.publication_head = E1
        store.current_tip = self.c1
        store.create_post_once_head = None
        store._prepared_replay_pending = False
        store._initial_create_replay_pending = True
        return store

    def execute(self, *, marker_fails: bool) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            store = self.store(root)
            events: list[str] = []
            validated = {
                "phase": "create_requested",
                "remote_consumption": store.remote_consumption,
            }

            def fake_publish(_manifest: pathlib.Path, _root: pathlib.Path) -> dict[str, Any]:
                publish._atomic_recovery_evidence(
                    store.evidence_path,
                    self.c1_value,
                    {},
                )
                events.append("zenodo-create")
                return {"result": "after-create"}

            def marker(*_args: Any, **_kwargs: Any) -> str:
                events.append("marker-create-auth-anonymous-readback")
                if marker_fails:
                    raise SystemExit("BLOCK: simulated marker boundary failure")
                return self.c1

            def git(
                _root: pathlib.Path,
                *arguments: str,
                **_kwargs: object,
            ) -> tuple[int, bytes]:
                if arguments == (
                    "show",
                    self.c1 + ":" + recovery.EVIDENCE_RELATIVE.as_posix(),
                ):
                    return 0, self.c1_raw
                raise AssertionError("unexpected replay Git call: " + repr(arguments))

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
                return_value=[
                    {"phase": "authorization_consumed"},
                    {"phase": "create_requested"},
                ],
            ), mock.patch.object(
                recovery,
                "persist_create_post_once_marker",
                side_effect=marker,
            ), mock.patch.object(
                recovery,
                "_git",
                side_effect=git,
            ):
                if marker_fails:
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        recovery.run_publisher_with_checkpoints(
                            store.manifest_path,
                            root,
                            store,
                            publish_callable=fake_publish,
                        )
                else:
                    result = recovery.run_publisher_with_checkpoints(
                        store.manifest_path,
                        root,
                        store,
                        publish_callable=fake_publish,
                    )
                    self.assertEqual(result, {"result": "after-create"})
                    self.assertEqual(store.create_post_once_head, self.c1)
                    self.assertFalse(store._initial_create_replay_pending)
            return events

    def test_marker_is_durable_before_unchanged_publishers_create_effect(self) -> None:
        self.assertEqual(
            self.execute(marker_fails=False),
            ["marker-create-auth-anonymous-readback", "zenodo-create"],
        )

    def test_any_marker_boundary_failure_keeps_zenodo_create_unreachable(self) -> None:
        self.assertEqual(
            self.execute(marker_fails=True),
            ["marker-create-auth-anonymous-readback"],
        )

    def test_marker_present_reconciliation_requires_exactly_one_inventory_match(
        self,
    ) -> None:
        exact = (123456, "10.5281/zenodo.123456", None)
        for matches, accepted in (([], False), ([exact], True), ([exact, exact], False)):
            with self.subTest(count=len(matches)), mock.patch.object(
                publish,
                "_canonical_inventory_candidates",
                return_value=matches,
            ):
                if accepted:
                    self.assertEqual(
                        publish._recover_create_requested_record(
                            object(),
                            "token",
                            {},
                            [],
                        ),
                        exact,
                    )
                else:
                    with self.assertRaisesRegex(
                        publish.zenodo.ZenodoError,
                        "requires exactly one",
                    ):
                        publish._recover_create_requested_record(
                            object(),
                            "token",
                            {},
                            [],
                        )

    def test_precreate_replay_requires_zero_inventory_matches(self) -> None:
        exact = (123456, "10.5281/zenodo.123456", None)
        with mock.patch.object(
            publish,
            "_canonical_inventory_candidates",
            return_value=[],
        ):
            publish._gate_precreate_inventory(object(), "token", {}, [])
        with mock.patch.object(
            publish,
            "_canonical_inventory_candidates",
            return_value=[exact],
        ):
            with self.assertRaisesRegex(
                publish.zenodo.ZenodoError,
                "pre-create inventory contains",
            ):
                publish._gate_precreate_inventory(object(), "token", {}, [])


class VRTCoreH3E1R5OneShotExecutionTests(unittest.TestCase):
    CONTROLLER = "f" * 40

    @classmethod
    def event(cls) -> dict[str, Any]:
        return {
            "ref": "refs/heads/" + recovery.EXPECTED["trigger_branch"],
            "before": recovery.R4_UNSENT_CREATE_INCIDENT["controller"],
            "after": cls.CONTROLLER,
            "created": False,
            "deleted": False,
            "forced": False,
            "repository": {"full_name": recovery.EXPECTED["repository"]},
            "head_commit": {"id": cls.CONTROLLER},
        }

    @classmethod
    def environment(cls, event_path: pathlib.Path) -> dict[str, str]:
        return {
            "GITHUB_SHA": cls.CONTROLLER,
            "GITHUB_REPOSITORY": recovery.EXPECTED["repository"],
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": "refs/heads/" + recovery.EXPECTED["trigger_branch"],
            "GITHUB_REF_NAME": recovery.EXPECTED["trigger_branch"],
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_EVENT_PATH": str(event_path),
        }

    def validate(
        self,
        root: pathlib.Path,
        event: dict[str, Any],
        environment: dict[str, str],
    ) -> str:
        path = pathlib.Path(environment["GITHUB_EVENT_PATH"])
        path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        with mock.patch.dict(recovery.os.environ, environment, clear=True), mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ) as fetch, mock.patch.object(
            recovery,
            "_git",
            return_value=(
                0,
                (str(recovery.R4_UNSENT_CREATE_INCIDENT["controller"]) + "\n").encode(
                    "ascii"
                ),
            ),
        ):
            result = recovery._validate_r5_one_shot_execution(root)
        fetch.assert_called_once_with(
            root,
            "refs/heads/" + recovery.EXPECTED["trigger_branch"],
            self.CONTROLLER,
        )
        return result

    def test_exact_first_nonforced_r4_to_r5_push_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event_path = root / "event.json"
            self.assertEqual(
                self.validate(
                    root,
                    self.event(),
                    self.environment(event_path),
                ),
                self.CONTROLLER,
            )

    def test_attempt_event_and_branch_tampering_fail_closed(self) -> None:
        cases: list[tuple[str, str, object]] = [
            ("environment", "GITHUB_RUN_ATTEMPT", "2"),
            ("environment", "GITHUB_EVENT_NAME", "workflow_dispatch"),
            ("environment", "GITHUB_REF_NAME", "wrong-branch"),
            ("event", "created", True),
            ("event", "deleted", True),
            ("event", "forced", True),
            ("event", "before", "e" * 40),
            ("event", "after", "e" * 40),
            ("head_commit", "id", "e" * 40),
            ("repository", "full_name", "other/repository"),
        ]
        for scope, key, value in cases:
            with self.subTest(scope=scope, key=key), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                event_path = root / "event.json"
                event = self.event()
                environment = self.environment(event_path)
                if scope == "environment":
                    environment[key] = str(value)
                elif scope == "event":
                    event[key] = value
                else:
                    nested = event[scope]
                    assert isinstance(nested, dict)
                    nested[key] = value
                event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
                with mock.patch.dict(
                    recovery.os.environ,
                    environment,
                    clear=True,
                ), mock.patch.object(
                    recovery,
                    "_fetch_credential_free",
                ) as fetch:
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        recovery._validate_r5_one_shot_execution(root)
                fetch.assert_not_called()

    def test_arm_accepts_only_exact_c1_without_marker_and_binds_r4_incident(self) -> None:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = ROOT
        store.api = object()
        store.publisher = publish
        store.publication_head = E1
        store.current_tip = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
        store.create_post_once_head = None
        store._initial_create_replay_pending = False
        with mock.patch.object(
            recovery,
            "_validate_r5_one_shot_execution",
            return_value=self.CONTROLLER,
        ) as execution, mock.patch.object(
            recovery,
            "verify_historical_r4_unsent_create_incident",
        ) as incident, mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ), mock.patch.object(
            recovery,
            "_verify_r4_local_object_chain",
        ) as objects, mock.patch.object(
            store,
            "validate_recovery_chain",
            return_value=[
                {"phase": "authorization_consumed"},
                {"phase": "create_requested"},
            ],
        ):
            self.assertTrue(store.arm_exact_unsent_create_replay())
        self.assertTrue(store._initial_create_replay_pending)
        execution.assert_called_once_with(ROOT)
        incident.assert_called_once_with(store.api, ROOT)
        objects.assert_called_once_with(ROOT)

    def test_existing_marker_never_rearms_c0_and_wrong_tip_blocks(self) -> None:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = ROOT
        store.api = object()
        store.publisher = publish
        store.publication_head = E1
        store.current_tip = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
        store.create_post_once_head = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
        store._initial_create_replay_pending = False
        with mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ), mock.patch.object(
            store,
            "validate_recovery_chain",
            return_value=[
                {"phase": "authorization_consumed"},
                {"phase": "create_requested"},
            ],
        ), mock.patch.object(
            recovery,
            "verify_historical_r4_unsent_create_incident",
        ) as incident:
            self.assertFalse(store.arm_exact_unsent_create_replay())
        self.assertFalse(store._initial_create_replay_pending)
        incident.assert_not_called()

        store.current_tip = recovery.R4_UNSENT_CREATE_INCIDENT["c0"]
        with mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ), mock.patch.object(
            store,
            "validate_recovery_chain",
            return_value=[{"phase": "authorization_consumed"}],
        ):
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                store.arm_exact_unsent_create_replay()

        store.current_tip = None
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            store.arm_exact_unsent_create_replay()

        store.create_post_once_head = None
        store.current_tip = "c" * 40
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            store.arm_exact_unsent_create_replay()


class VRTCoreH3E1R9OneShotExecutionTests(unittest.TestCase):
    CONTROLLER = "e" * 40

    @classmethod
    def event(cls) -> dict[str, Any]:
        return {
            "ref": "refs/heads/" + recovery.EXPECTED["trigger_branch"],
            "before": recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT["controller"],
            "after": cls.CONTROLLER,
            "created": False,
            "deleted": False,
            "forced": False,
            "repository": {"full_name": recovery.EXPECTED["repository"]},
            "head_commit": {"id": cls.CONTROLLER},
        }

    @classmethod
    def environment(cls, event_path: pathlib.Path) -> dict[str, str]:
        return {
            "GITHUB_SHA": cls.CONTROLLER,
            "GITHUB_REPOSITORY": recovery.EXPECTED["repository"],
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": "refs/heads/" + recovery.EXPECTED["trigger_branch"],
            "GITHUB_REF_NAME": recovery.EXPECTED["trigger_branch"],
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_EVENT_PATH": str(event_path),
        }

    def validate(
        self,
        root: pathlib.Path,
        event: dict[str, Any],
        environment: dict[str, str],
    ) -> str:
        path = pathlib.Path(environment["GITHUB_EVENT_PATH"])
        path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        parent = str(recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT["controller"])
        with mock.patch.dict(recovery.os.environ, environment, clear=True), mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ) as fetch, mock.patch.object(
            recovery,
            "_git",
            return_value=(0, (parent + "\n").encode("ascii")),
        ):
            result = recovery._validate_r9_one_shot_execution(root)
        fetch.assert_called_once_with(
            root,
            "refs/heads/" + recovery.EXPECTED["trigger_branch"],
            self.CONTROLLER,
        )
        return result

    def test_exact_first_nonforced_r8_to_r9_push_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event_path = root / "event.json"
            self.assertEqual(
                self.validate(
                    root,
                    self.event(),
                    self.environment(event_path),
                ),
                self.CONTROLLER,
            )

    def test_attempt_event_and_branch_tampering_fail_closed(self) -> None:
        cases: list[tuple[str, str, object]] = [
            ("environment", "GITHUB_RUN_ATTEMPT", "2"),
            ("environment", "GITHUB_EVENT_NAME", "workflow_dispatch"),
            ("environment", "GITHUB_REF_NAME", "wrong-branch"),
            ("event", "created", True),
            ("event", "deleted", True),
            ("event", "forced", True),
            ("event", "before", "d" * 40),
            ("event", "after", "d" * 40),
            ("head_commit", "id", "d" * 40),
            ("repository", "full_name", "other/repository"),
        ]
        for scope, key, value in cases:
            with self.subTest(scope=scope, key=key), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                event_path = root / "event.json"
                event = self.event()
                environment = self.environment(event_path)
                if scope == "environment":
                    environment[key] = str(value)
                elif scope == "event":
                    event[key] = value
                else:
                    nested = event[scope]
                    assert isinstance(nested, dict)
                    nested[key] = value
                event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
                with mock.patch.dict(
                    recovery.os.environ,
                    environment,
                    clear=True,
                ), mock.patch.object(
                    recovery,
                    "_fetch_credential_free",
                ) as fetch:
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        recovery._validate_r9_one_shot_execution(root)
                fetch.assert_not_called()

    def test_local_controller_parent_must_be_exact_r8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event_path = root / "event.json"
            event_path.write_text(json.dumps(self.event()) + "\n", encoding="utf-8")
            with mock.patch.dict(
                recovery.os.environ,
                self.environment(event_path),
                clear=True,
            ), mock.patch.object(
                recovery,
                "_fetch_credential_free",
            ), mock.patch.object(
                recovery,
                "_git",
                return_value=(0, ("d" * 40 + "\n").encode("ascii")),
            ):
                with self.assertRaisesRegex(SystemExit, "single successor of R8"):
                    recovery._validate_r9_one_shot_execution(root)

    def test_arm_binds_exact_c2_marker_publication_and_r8_incident(self) -> None:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = ROOT
        store.api = object()
        store.publisher = publish
        store.publication_head = E1
        store.current_tip = incident["c2"]
        store.create_post_once_head = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
        store._initial_create_replay_pending = False
        store._record_created_reconciliation_armed = False
        store._r9_controller = None
        chain = [
            {"phase": "authorization_consumed"},
            {"phase": "create_requested"},
            {
                "phase": "record_created",
                "state": incident["state"],
                "record_id": incident["record_id"],
                "doi": incident["doi"],
            },
        ]
        with mock.patch.object(
            recovery,
            "_validate_r9_one_shot_execution",
            return_value=self.CONTROLLER,
        ) as execution, mock.patch.object(
            recovery,
            "verify_historical_r5_record_created_timeout",
        ) as historical_r5, mock.patch.object(
            recovery,
            "verify_historical_r6_draft_metadata_incident",
        ) as historical_r6, mock.patch.object(
            recovery,
            "verify_historical_r7_creator_normalization_incident",
        ) as historical_r7, mock.patch.object(
            recovery,
            "verify_historical_r8_description_normalization_incident",
        ) as historical_r8, mock.patch.object(
            recovery,
            "_fetch_credential_free",
        ) as fetch, mock.patch.object(
            recovery,
            "_verify_r8_local_object_chain",
        ) as objects, mock.patch.object(
            recovery,
            "_verify_r8_null_affiliation_evidence",
        ) as normalization, mock.patch.object(
            store,
            "validate_recovery_chain",
            return_value=chain,
        ):
            store.arm_exact_record_created_reconciliation()
        self.assertTrue(store._record_created_reconciliation_armed)
        self.assertEqual(store._r9_controller, self.CONTROLLER)
        execution.assert_called_once_with(ROOT)
        historical_r5.assert_called_once_with(store.api, ROOT)
        historical_r6.assert_called_once_with(store.api, ROOT)
        historical_r7.assert_called_once_with(store.api, ROOT)
        historical_r8.assert_called_once_with(store.api, ROOT)
        objects.assert_called_once_with(ROOT)
        normalization.assert_called_once_with(ROOT)
        self.assertEqual(
            fetch.call_args_list,
            [
                mock.call(ROOT, recovery.EXPECTED["publication_ref"], E1),
                mock.call(
                    ROOT,
                    recovery.EXPECTED["create_post_once_ref"],
                    recovery.R4_UNSENT_CREATE_INCIDENT["c1"],
                ),
                mock.call(
                    ROOT,
                    recovery.EXPECTED["recovery_ref"],
                    incident["c2"],
                ),
            ],
        )

    def test_arm_rejects_malformed_c2_chain_or_identity(self) -> None:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        exact = [
            {"phase": "authorization_consumed"},
            {"phase": "create_requested"},
            {
                "phase": "record_created",
                "state": incident["state"],
                "record_id": incident["record_id"],
                "doi": incident["doi"],
            },
        ]
        cases: list[tuple[str, list[dict[str, Any]]]] = []
        wrong_phase = copy.deepcopy(exact)
        wrong_phase[-1]["phase"] = "prepared"
        cases.append(("phase", wrong_phase))
        for key, value in (
            ("record_id", int(incident["record_id"]) + 1),
            ("doi", "10.5281/zenodo.21763615"),
            ("state", "published"),
        ):
            changed = copy.deepcopy(exact)
            changed[-1][key] = value
            cases.append((key, changed))
        for label, chain in cases:
            with self.subTest(label=label):
                store = object.__new__(recovery.RecoveryReceiptStore)
                store.root = ROOT
                store.api = object()
                store.publisher = publish
                store.publication_head = E1
                store.current_tip = incident["c2"]
                store.create_post_once_head = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
                store._initial_create_replay_pending = False
                store._record_created_reconciliation_armed = False
                store._r9_controller = None
                with mock.patch.object(
                    recovery,
                    "_validate_r9_one_shot_execution",
                    return_value=self.CONTROLLER,
                ), mock.patch.object(
                    recovery,
                    "verify_historical_r5_record_created_timeout",
                ), mock.patch.object(
                    recovery,
                    "verify_historical_r6_draft_metadata_incident",
                ), mock.patch.object(
                    recovery,
                    "verify_historical_r7_creator_normalization_incident",
                ), mock.patch.object(
                    recovery,
                    "verify_historical_r8_description_normalization_incident",
                ), mock.patch.object(
                    recovery,
                    "_fetch_credential_free",
                ), mock.patch.object(
                    recovery,
                    "_verify_r8_local_object_chain",
                ), mock.patch.object(
                    recovery,
                    "_verify_r8_null_affiliation_evidence",
                ), mock.patch.object(
                    store,
                    "validate_recovery_chain",
                    return_value=chain,
                ):
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        store.arm_exact_record_created_reconciliation()
                self.assertFalse(store._record_created_reconciliation_armed)

    def test_arm_rejects_every_nonexact_start_identity(self) -> None:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        cases = (
            ("publication_head", "d" * 40),
            ("current_tip", recovery.R4_UNSENT_CREATE_INCIDENT["c1"]),
            ("create_post_once_head", None),
            ("_initial_create_replay_pending", True),
        )
        for attribute, value in cases:
            with self.subTest(attribute=attribute):
                store = object.__new__(recovery.RecoveryReceiptStore)
                store.root = ROOT
                store.api = object()
                store.publisher = publish
                store.publication_head = E1
                store.current_tip = incident["c2"]
                store.create_post_once_head = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
                store._initial_create_replay_pending = False
                store._record_created_reconciliation_armed = False
                store._r9_controller = None
                setattr(store, attribute, value)
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    store.arm_exact_record_created_reconciliation()
                self.assertFalse(store._record_created_reconciliation_armed)


class VRTCoreH3E1R7InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest_path = (
            ROOT
            / "release/vrtcore-relational-h3-publication-2026-08-02"
            / "publish-request.json"
        )
        cls.manifest = publish.load_manifest(manifest_path, ROOT)

    @classmethod
    def draft(cls, *, record_id: int = 21763614, doi: str | None = None) -> dict[str, Any]:
        metadata = copy.deepcopy(cls.manifest["metadata"])
        metadata["prereserve_doi"] = {
            "doi": doi or "10.5281/zenodo.21763614"
        }
        return {
            "id": record_id,
            "doi": doi or "10.5281/zenodo.21763614",
            "metadata": metadata,
            "links": {"bucket": "https://zenodo.org/api/files/exact-c2-bucket"},
            "files": [],
        }

    class Client:
        def __init__(self, current_by_id: Mapping[int, tuple[str, dict[str, Any]]]) -> None:
            self.current_by_id = dict(current_by_id)
            self.get_calls: list[int] = []
            self.wait_calls: list[tuple[object, ...]] = []

        def get_deposition_or_record(self, record_id: int) -> tuple[str, dict[str, Any]]:
            self.get_calls.append(record_id)
            return self.current_by_id[record_id]

        def wait_for_gated_record(self, *args: object, **kwargs: object) -> dict[str, Any]:
            self.wait_calls.append((*args, kwargs))
            initial = kwargs.get("initial")
            assert isinstance(initial, dict)
            return initial

        @staticmethod
        def _server_files(value: Mapping[str, Any]) -> list[dict[str, Any]]:
            files = value.get("files")
            return list(files) if isinstance(files, list) else []

    def test_exact_single_empty_draft_is_identity_gated(self) -> None:
        draft = self.draft()
        client = self.Client({21763614: ("draft", draft)})
        with mock.patch.object(
            publish,
            "_list_all_owned_depositions",
            return_value=[draft],
        ) as inventory:
            state, current = recovery._gate_r7_owned_inventory_identity(
                publish,
                self.manifest,
                client,
                "z" * 32,
            )
        self.assertEqual((state, current), ("draft", draft))
        self.assertEqual(client.get_calls, [21763614])
        self.assertEqual(client.wait_calls, [])
        inventory.assert_called_once_with(client, "z" * 32)

    def test_preexisting_draft_file_blocks_before_mutation(self) -> None:
        draft = self.draft()
        draft["files"] = [{"filename": "unexpected"}]
        client = self.Client({21763614: ("draft", draft)})
        with mock.patch.object(
            publish,
            "_list_all_owned_depositions",
            return_value=[draft],
        ):
            with self.assertRaisesRegex(SystemExit, "preexisting files"):
                recovery._gate_r7_owned_inventory_identity(
                    publish,
                    self.manifest,
                    client,
                    "z" * 32,
                )

    def test_zero_duplicate_and_unstable_inventory_block(self) -> None:
        draft = self.draft()
        client = self.Client({21763614: ("draft", draft)})
        with mock.patch.object(
            publish,
            "_list_all_owned_depositions",
            return_value=[],
        ):
            with self.assertRaisesRegex(SystemExit, "observed 0"):
                recovery._gate_r7_owned_inventory_identity(
                    publish,
                    self.manifest,
                    client,
                    "z" * 32,
                )

        duplicate = copy.deepcopy(draft)
        duplicate["id"] = 21763615
        client = self.Client(
            {
                21763614: ("draft", draft),
                21763615: ("draft", duplicate),
            }
        )
        with mock.patch.object(
            publish,
            "_list_all_owned_depositions",
            return_value=[draft, duplicate],
        ), mock.patch.object(
            recovery,
            "_validate_r7_record_identity",
        ):
            with self.assertRaisesRegex(SystemExit, "observed 2"):
                recovery._gate_r7_owned_inventory_identity(
                    publish,
                    self.manifest,
                    client,
                    "z" * 32,
                )

        with mock.patch.object(
            publish,
            "_list_all_owned_depositions",
            side_effect=SystemExit("BLOCK: inventory changed between complete passes"),
        ):
            with self.assertRaisesRegex(SystemExit, "inventory changed"):
                recovery._gate_r7_owned_inventory_identity(
                    publish,
                    self.manifest,
                    client,
                    "z" * 32,
                )

    def test_wrong_record_or_doi_blocks(self) -> None:
        cases = (
            self.draft(record_id=21763615),
            self.draft(doi="10.5281/zenodo.21763615"),
        )
        for candidate in cases:
            with self.subTest(record=candidate["id"], doi=candidate["doi"]):
                record_id = int(candidate["id"])
                client = self.Client({record_id: ("draft", candidate)})
                with mock.patch.object(
                    publish,
                    "_list_all_owned_depositions",
                    return_value=[candidate],
                ):
                    with self.assertRaisesRegex(SystemExit, "exact C2"):
                        recovery._gate_r7_owned_inventory_identity(
                            publish,
                            self.manifest,
                            client,
                            "z" * 32,
                        )

    def test_published_candidate_requires_full_public_gate(self) -> None:
        published = self.draft()
        client = self.Client({21763614: ("published", published)})
        with mock.patch.object(
            publish,
            "_list_all_owned_depositions",
            return_value=[published],
        ), mock.patch.object(
            recovery,
            "_validate_r7_record_identity",
        ) as identity:
            state, current = recovery._gate_r7_owned_inventory_identity(
                publish,
                self.manifest,
                client,
                "z" * 32,
            )
        self.assertEqual((state, current), ("published", published))
        identity.assert_called_once()
        self.assertEqual(len(client.wait_calls), 1)
        self.assertTrue(client.wait_calls[0][-1]["published"])


class VRTCoreH3E1R7MetadataSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest_path = (
            ROOT
            / "release/vrtcore-relational-h3-publication-2026-08-02"
            / "publish-request.json"
        )
        cls.manifest = publish.load_manifest(manifest_path, ROOT)

    def draft(self) -> dict[str, Any]:
        metadata = copy.deepcopy(self.manifest["metadata"])
        metadata["prereserve_doi"] = {
            "doi": recovery.R6_DRAFT_METADATA_INCIDENT["doi"],
        }
        return {
            "id": recovery.R6_DRAFT_METADATA_INCIDENT["record_id"],
            "metadata": metadata,
            "links": {
                "bucket": (
                    "https://zenodo.org/api/files/"
                    "12345678-1234-1234-1234-123456789abc"
                )
            },
            "files": [],
        }

    def test_r8_creator_comparator_accepts_exact_and_null_affiliation(self) -> None:
        expected = [{"name": "Lohmann, Ingolf"}]
        for actual in (
            [{"name": "Lohmann, Ingolf"}],
            [{"affiliation": None, "name": "Lohmann, Ingolf"}],
        ):
            with self.subTest(actual=actual):
                self.assertTrue(
                    recovery._creators_match_r8_null_affiliation_normalization(
                        actual,
                        expected,
                    )
                )

    def test_r8_creator_comparator_rejects_foreign_additional_fields(self) -> None:
        expected = [{"name": "Lohmann, Ingolf"}]
        for actual in (
            [
                {
                    "name": "Lohmann, Ingolf",
                    "affiliation": "Foreign Institution",
                }
            ],
            [{"name": "Lohmann, Ingolf", "orcid": None}],
            [
                {
                    "name": "Lohmann, Ingolf",
                    "affiliation": None,
                    "orcid": "0000-0000-0000-0000",
                }
            ],
        ):
            with self.subTest(actual=actual):
                self.assertFalse(
                    recovery._creators_match_r8_null_affiliation_normalization(
                        actual,
                        expected,
                    )
                )

    def test_r8_creator_comparator_is_nested_json_type_exact(self) -> None:
        cases = (
            (
                [{"name": "Lohmann, Ingolf", "identity": {"verified": True}}],
                [{"name": "Lohmann, Ingolf", "identity": {"verified": 1}}],
            ),
            (
                [{"name": "Lohmann, Ingolf", "identity": [1]}],
                [{"name": "Lohmann, Ingolf", "identity": [True]}],
            ),
            (
                [{"name": " Lohmann, Ingolf"}],
                [{"name": " Lohmann, Ingolf"}],
            ),
        )
        for actual, expected in cases:
            with self.subTest(actual=actual, expected=expected):
                self.assertFalse(
                    recovery._creators_match_r8_null_affiliation_normalization(
                        actual,
                        expected,
                    )
                )

    def test_r9_description_accepts_only_exact_or_exact_paragraph(self) -> None:
        expected = str(self.manifest["metadata"]["description"])
        self.assertEqual(
            recovery._r9_description_normalization(expected, expected),
            "EXACT",
        )
        self.assertEqual(
            recovery._r9_description_normalization(
                "<p>" + expected + "</p>",
                expected,
            ),
            "HTML_PARAGRAPH",
        )
        for actual in (
            "<div>" + expected + "</div>",
            '<p class="zenodo">' + expected + "</p>",
            "<p>" + expected + "</p>\n",
            "<p><span>" + expected + "</span></p>",
            "<p>" + expected + " changed</p>",
            "<p><p>" + expected + "</p></p>",
            None,
            True,
        ):
            with self.subTest(actual=actual):
                self.assertIsNone(
                    recovery._r9_description_normalization(actual, expected)
                )

    def test_r9_nullable_imprint_and_paragraph_are_semantically_exact(self) -> None:
        current = self.draft()
        metadata = current["metadata"]
        metadata["description"] = (
            "<p>" + self.manifest["metadata"]["description"] + "</p>"
        )
        metadata["imprint_publisher"] = None
        self.assertEqual(
            recovery._r7_draft_metadata_mismatch_keys(
                publish,
                metadata,
                self.manifest["metadata"],
            ),
            (),
        )
        recovery._validate_r7_record_identity(
            publish,
            self.manifest,
            "draft",
            current,
            require_exact_draft_metadata=True,
        )

    def test_r9_nonnull_imprint_and_nearby_html_forms_block(self) -> None:
        for value in ("Publisher", "", False, 0, {}, []):
            with self.subTest(imprint=value):
                current = self.draft()
                current["metadata"]["imprint_publisher"] = value
                with self.assertRaisesRegex(SystemExit, "imprint_publisher"):
                    recovery._validate_r7_record_identity(
                        publish,
                        self.manifest,
                        "draft",
                        current,
                        require_exact_draft_metadata=True,
                    )
        current = self.draft()
        expected = self.manifest["metadata"]["description"]
        current["metadata"]["description"] = "<p>" + expected + " </p>"
        with self.assertRaisesRegex(SystemExit, "description"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "draft",
                current,
                require_exact_draft_metadata=True,
            )

    def test_r9_public_comparator_normalizes_only_bounded_fields(self) -> None:
        current = self.draft()
        metadata = current["metadata"]
        expected = self.manifest["metadata"]
        metadata["license"] = {"id": expected["license"]}
        metadata["resource_type"] = {
            "type": metadata.pop("upload_type"),
            "subtype": metadata.pop("publication_type"),
        }
        metadata.pop("prereserve_doi", None)
        metadata["doi"] = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT["doi"]
        metadata["description"] = "<p>" + expected["description"] + "</p>"
        metadata["imprint_publisher"] = None
        self.assertTrue(
            recovery._published_metadata_matches_r9_normalizations(
                publish,
                metadata,
                expected,
            )
        )
        metadata["description"] = "<div>" + expected["description"] + "</div>"
        self.assertFalse(
            recovery._published_metadata_matches_r9_normalizations(
                publish,
                metadata,
                expected,
            )
        )
        metadata["description"] = "<p>" + expected["description"] + "</p>"
        metadata["imprint_publisher"] = "unauthorized"
        self.assertFalse(
            recovery._published_metadata_matches_r9_normalizations(
                publish,
                metadata,
                expected,
            )
        )

    def test_every_nonidentity_field_is_correctable_but_not_strictly_accepted(self) -> None:
        mutable = sorted(
            set(self.manifest["metadata"])
            - {"title", "version", "creators", "prereserve_doi"}
        )
        self.assertTrue(mutable)
        for key in mutable:
            with self.subTest(key=key):
                current = self.draft()
                current["metadata"].pop(key)
                recovery._validate_r7_record_identity(
                    publish,
                    self.manifest,
                    "draft",
                    current,
                    require_exact_draft_metadata=False,
                )
                with self.assertRaisesRegex(SystemExit, key):
                    recovery._validate_r7_record_identity(
                        publish,
                        self.manifest,
                        "draft",
                        current,
                        require_exact_draft_metadata=True,
                    )

    def test_identity_fields_never_enter_correctable_mode(self) -> None:
        for key in ("title", "version", "creators"):
            with self.subTest(key=key):
                current = self.draft()
                current["metadata"].pop(key)
                with self.assertRaisesRegex(SystemExit, "title, version, or creators"):
                    recovery._validate_r7_record_identity(
                        publish,
                        self.manifest,
                        "draft",
                        current,
                        require_exact_draft_metadata=False,
                    )

    def test_creator_object_extras_never_enter_correctable_mode(self) -> None:
        current = self.draft()
        current["metadata"]["creators"][0]["affiliation"] = "Foreign Institution"
        with self.assertRaisesRegex(SystemExit, "creators differ"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "draft",
                current,
                require_exact_draft_metadata=False,
            )

    def test_known_zenodo_normalizations_preserve_exact_semantics(self) -> None:
        current = self.draft()
        metadata = current["metadata"]
        metadata["creators"][0]["affiliation"] = None
        metadata["license"] = {"id": self.manifest["metadata"]["license"]}
        metadata["resource_type"] = {
            "type": metadata.pop("upload_type"),
            "subtype": metadata.pop("publication_type"),
        }
        metadata["description"] = (
            "<p>" + self.manifest["metadata"]["description"] + "</p>"
        )
        metadata["imprint_publisher"] = None
        self.assertEqual(
            recovery._r7_draft_metadata_mismatch_keys(
                publish,
                metadata,
                self.manifest["metadata"],
            ),
            (),
        )
        recovery._validate_r7_record_identity(
            publish,
            self.manifest,
            "draft",
            current,
            require_exact_draft_metadata=True,
        )

    def test_conflicting_or_malformed_dual_resource_type_blocks(self) -> None:
        for key, normalized_key in (
            ("upload_type", "type"),
            ("publication_type", "subtype"),
        ):
            with self.subTest(key=key):
                current = self.draft()
                current["metadata"]["resource_type"] = {
                    "type": self.manifest["metadata"]["upload_type"],
                    "subtype": self.manifest["metadata"]["publication_type"],
                }
                current["metadata"]["resource_type"][normalized_key] = "wrong"
                with self.assertRaisesRegex(SystemExit, key):
                    recovery._validate_r7_record_identity(
                        publish,
                        self.manifest,
                        "draft",
                        current,
                        require_exact_draft_metadata=True,
                    )
        for malformed in ("malformed", None):
            with self.subTest(malformed_resource_type=malformed):
                current = self.draft()
                current["metadata"]["resource_type"] = malformed
                with self.assertRaisesRegex(
                    SystemExit,
                    "publication_type|upload_type",
                ):
                    recovery._validate_r7_record_identity(
                        publish,
                        self.manifest,
                        "draft",
                        current,
                        require_exact_draft_metadata=True,
                    )

    def test_unrequested_client_metadata_field_blocks_strict_gate(self) -> None:
        current = self.draft()
        current["metadata"]["communities"] = [{"identifier": "foreign"}]
        recovery._validate_r7_record_identity(
            publish,
            self.manifest,
            "draft",
            current,
            require_exact_draft_metadata=False,
        )
        with self.assertRaisesRegex(SystemExit, "unexpected:communities"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "draft",
                current,
                require_exact_draft_metadata=True,
            )

    def test_conflicting_public_legacy_alias_blocks(self) -> None:
        current = self.draft()
        metadata = current["metadata"]
        metadata["license"] = {"id": self.manifest["metadata"]["license"]}
        metadata["resource_type"] = {
            "type": metadata.pop("upload_type"),
            "subtype": metadata.pop("publication_type"),
        }
        metadata.pop("prereserve_doi", None)
        metadata["doi"] = recovery.R6_DRAFT_METADATA_INCIDENT["doi"]
        metadata["upload_type"] = "conflicting-public-alias"
        with self.assertRaisesRegex(SystemExit, "conflicting metadata aliases"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "published",
                current,
                require_exact_draft_metadata=True,
            )

    def test_conflicting_alternate_record_or_doi_identity_blocks(self) -> None:
        current = self.draft()
        current["record_id"] = int(current["id"]) + 1
        with self.assertRaisesRegex(SystemExit, "conflicting record"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "draft",
                current,
                require_exact_draft_metadata=False,
            )
        current = self.draft()
        current["metadata"]["doi"] = "10.5281/zenodo.21763615"
        with self.assertRaisesRegex(SystemExit, "conflicting DOI"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "draft",
                current,
                require_exact_draft_metadata=False,
            )
        current = self.draft()
        current["doi"] = "10.5281/zenodo.21763615"
        with self.assertRaisesRegex(SystemExit, "conflicting DOI"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "draft",
                current,
                require_exact_draft_metadata=False,
            )
        for location in ("top", "metadata", "reserved"):
            with self.subTest(malformed_doi=location):
                current = self.draft()
                if location == "top":
                    current["doi"] = 21763614
                elif location == "metadata":
                    current["metadata"]["doi"] = 21763614
                else:
                    current["metadata"]["prereserve_doi"] = 21763614
                    current["doi"] = self.manifest["metadata"].get(
                        "doi",
                        recovery.R6_DRAFT_METADATA_INCIDENT["doi"],
                    )
                with self.assertRaisesRegex(SystemExit, "conflicting DOI"):
                    recovery._validate_r7_record_identity(
                        publish,
                        self.manifest,
                        "draft",
                        current,
                        require_exact_draft_metadata=False,
                    )
        for key, value in (
            ("record_id", float(recovery.R6_DRAFT_METADATA_INCIDENT["record_id"])),
            ("recid", True),
        ):
            with self.subTest(malformed_record_alias=key):
                current = self.draft()
                current[key] = value
                with self.assertRaisesRegex(SystemExit, "record identity"):
                    recovery._validate_r7_record_identity(
                        publish,
                        self.manifest,
                        "draft",
                        current,
                        require_exact_draft_metadata=False,
                    )
        current = self.draft()
        current["metadata"]["prereserve_doi"]["recid"] = (
            recovery.R6_DRAFT_METADATA_INCIDENT["record_id"] + 1
        )
        with self.assertRaisesRegex(SystemExit, "reserved record identity"):
            recovery._validate_r7_record_identity(
                publish,
                self.manifest,
                "draft",
                current,
                require_exact_draft_metadata=False,
            )


class VRTCoreH3E1R7PublisherFirewallTests(unittest.TestCase):
    RECORD_ID = 21763614
    DOI = "10.5281/zenodo.21763614"
    BUCKET = "https://zenodo.org/api/files/12345678-1234-1234-1234-123456789abc"

    @classmethod
    def draft(cls, *, preconverged: bool = False) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "title": "Exact C2",
            "version": "v1",
            "creators": [{"name": "Ingolf Lohmann"}],
            "prereserve_doi": {"doi": cls.DOI},
        }
        if preconverged:
            metadata["creators"] = [
                {"affiliation": None, "name": "Ingolf Lohmann"}
            ]
            metadata["description"] = "<p>Exact description</p>"
            metadata["imprint_publisher"] = None
        else:
            metadata["notes"] = "stale pre-R8 metadata"
        return {
            "id": cls.RECORD_ID,
            "doi": cls.DOI,
            "metadata": metadata,
            "links": {"bucket": cls.BUCKET},
            "files": [],
        }

    def fixture(
        self,
        operation: tuple[str, str] | str,
        *,
        fail_boundary_at: int | None = None,
        fail_phase: str | None = None,
    ) -> tuple[Any, Any, list[str], Any]:
        events: list[str] = []
        preconverged = operation in {
            "metadata_put_preconverged",
            "published_gate",
            "already_published_entry",
        }
        current = self.draft(preconverged=preconverged)
        upload_body = b"exact-r7-bucket-drift-test\n"
        upload_entry = {
            "name": "paper.pdf",
            "size": len(upload_body),
            "md5": hashlib.md5(upload_body).hexdigest(),  # noqa: S324
            "sha256": hashlib.sha256(upload_body).hexdigest(),
        }

        class PinnedZenodoError(RuntimeError):
            pass

        class Client:
            def __init__(
                instance: Any,
                _token: str,
                base_url: str,
                _transport: Any | None = None,
                *,
                poll_attempts: int = 30,
                poll_interval: float = 2.0,
                sleeper: Any = None,
            ) -> None:
                instance.base_url = base_url
                instance.poll_attempts = poll_attempts
                instance.poll_interval = poll_interval
                instance.sleeper = sleeper or (lambda _seconds: None)
                events.append(f"init:{poll_attempts}:{poll_interval}")

            def request(
                instance: Any,
                method: str,
                url: str,
                **request_kwargs: Any,
            ) -> tuple[object, dict[str, Any]]:
                del instance
                request_path = urllib.parse.urlsplit(url).path
                events.append("transport:" + method + ":" + request_path)
                if method == "GET":
                    self.assertEqual(
                        request_path,
                        f"/api/deposit/depositions/{self.RECORD_ID}",
                    )
                    self.assertEqual(request_kwargs, {"accept": (200,)})
                    return types.SimpleNamespace(status=200), copy.deepcopy(current)
                if (
                    method == "PUT"
                    and request_path == f"/api/deposit/depositions/{self.RECORD_ID}"
                    and isinstance(request_kwargs.get("payload"), dict)
                    and isinstance(request_kwargs["payload"].get("metadata"), dict)
                ):
                    updated_metadata = copy.deepcopy(
                        request_kwargs["payload"]["metadata"]
                    )
                    updated_metadata["prereserve_doi"] = {"doi": self.DOI}
                    current["metadata"] = updated_metadata
                if operation == "metadata_put_ambiguous_retry" and method == "PUT":
                    raise RuntimeError("simulated ambiguous transport")
                return object(), {}

            def create_paper(instance: Any, _metadata: Mapping[str, Any]) -> dict[str, Any]:
                del instance
                events.append("original-create")
                return current

            def get_deposition_or_record(
                instance: Any,
                record_id: int,
            ) -> tuple[str, dict[str, Any]]:
                del instance
                self.assertEqual(record_id, self.RECORD_ID)
                events.append("record-get")
                return (
                    "published"
                    if operation == "already_published_entry"
                    else "draft"
                ), current

            def get(
                instance: Any,
                path: str,
                accept: tuple[int, ...] = (200,),
            ) -> tuple[int, dict[str, Any]]:
                del instance
                self.assertEqual(
                    path,
                    f"/api/deposit/depositions/{self.RECORD_ID}",
                )
                self.assertEqual(accept, (200, 202))
                events.append("metadata-get")
                return 200, current

            @staticmethod
            def _server_files(value: Mapping[str, Any]) -> list[dict[str, Any]]:
                files = value.get("files")
                return list(files) if isinstance(files, list) else []

            @staticmethod
            def _server_file_name(value: Mapping[str, Any]) -> str:
                return str(value["filename"])

            def wait_for_editable_metadata(
                instance: Any,
                _record_id: int,
                _metadata: Mapping[str, Any],
            ) -> dict[str, Any]:
                del instance
                return current

            def wait_for_gated_record(
                instance: Any,
                record_id: int,
                metadata: Mapping[str, Any],
                entries: Any,
                expected_doi: str,
                *,
                published: bool,
                initial: Mapping[str, Any] | None = None,
            ) -> dict[str, Any]:
                self.assertTrue(published)
                self.assertEqual(record_id, self.RECORD_ID)
                self.assertEqual(expected_doi, self.DOI)
                self.assertIsNotNone(initial)
                assert initial is not None
                events.append("public-wait")
                instance.gate_record(
                    initial,
                    record_id,
                    metadata,
                    entries,
                    expected_doi,
                    published=True,
                )
                return dict(initial)

            def gate_record(
                instance: Any,
                value: Mapping[str, Any],
                *_args: Any,
                **kwargs: Any,
            ) -> None:
                del instance
                if kwargs.get("published") is True:
                    self.assertEqual(
                        value.get("metadata", {}).get("description"),
                        "Exact description",
                    )
                    events.append("original-published-gate-normalized")

            def gate_files(instance: Any, *_args: Any, **_kwargs: Any) -> None:
                del instance

        zenodo_module = types.SimpleNamespace(
            ZenodoClient=Client,
            ZenodoError=PinnedZenodoError,
            TOKEN_ENVIRONMENT_VARIABLE=publish.zenodo.TOKEN_ENVIRONMENT_VARIABLE,
            validate_response_url=publish.zenodo.validate_response_url,
            _record_id=publish.zenodo._record_id,
            _doi_from_deposition=publish.zenodo._doi_from_deposition,
            _metadata_matches=publish.zenodo._metadata_matches,
            _published_metadata_matches=publish.zenodo._published_metadata_matches,
        )
        module = types.SimpleNamespace()
        module.zenodo = zenodo_module
        module._create_consumption_receipt = lambda *_args, **_kwargs: None
        module._atomic_recovery_evidence = lambda *_args, **_kwargs: None
        module._acquire_remote_consumption_lock = lambda *_args, **_kwargs: None
        module._shared_entries = lambda files: [dict(item) for item in files]
        module._inventory_publication_identity_candidate = (
            lambda _value, _metadata: True
        )
        module._list_all_owned_depositions = (
            lambda _client, _token: [copy.deepcopy(current)]
        )

        def original_resume(
            _evidence: Mapping[str, Any],
            _evidence_path: pathlib.Path,
            _manifest_path: pathlib.Path,
            _root: pathlib.Path,
            _manifest: Mapping[str, Any],
            _execution_head: str,
            _verified: Mapping[tuple[str, str], bytes],
            client: Any,
            _secrets: Mapping[str, str],
        ) -> dict[str, Any]:
            events.append("resume")
            if operation == "create_paper":
                client.create_paper({})
            elif operation in ("metadata_put", "metadata_put_preconverged"):
                client.request(
                    "PUT",
                    f"/api/deposit/depositions/{self.RECORD_ID}",
                    payload={"metadata": _manifest["metadata"]},
                    accept=(200, 202),
                )
            elif operation == "metadata_put_twice":
                for _index in range(2):
                    client.request(
                        "PUT",
                        f"/api/deposit/depositions/{self.RECORD_ID}",
                        payload={"metadata": _manifest["metadata"]},
                        accept=(200, 202),
                    )
            elif operation == "metadata_put_wrong_payload":
                client.request(
                    "PUT",
                    f"/api/deposit/depositions/{self.RECORD_ID}",
                    payload={"metadata": {"title": "wrong"}},
                    accept=(200, 202),
                )
            elif operation == "metadata_put_wrong_accept":
                client.request(
                    "PUT",
                    f"/api/deposit/depositions/{self.RECORD_ID}",
                    payload={"metadata": _manifest["metadata"]},
                    accept=(200,),
                )
            elif operation == "metadata_put_ambiguous_retry":
                try:
                    client.request(
                        "PUT",
                        f"/api/deposit/depositions/{self.RECORD_ID}",
                        payload={"metadata": _manifest["metadata"]},
                        accept=(200, 202),
                    )
                except RuntimeError:
                    client.request(
                        "PUT",
                        f"/api/deposit/depositions/{self.RECORD_ID}",
                        payload={"metadata": _manifest["metadata"]},
                        accept=(200, 202),
                    )
            elif operation == "publish_after_failed_intent":
                client.request(
                    "PUT",
                    f"/api/deposit/depositions/{self.RECORD_ID}",
                    payload={"metadata": _manifest["metadata"]},
                    accept=(200, 202),
                )
                client.wait_for_editable_metadata(
                    self.RECORD_ID,
                    _manifest["metadata"],
                )
                for phase in ("prepared", "publish_requested"):
                    module._atomic_recovery_evidence(
                        _evidence_path,
                        {"phase": phase},
                        {},
                    )
                client.request(
                    "POST",
                    f"/api/deposit/depositions/{self.RECORD_ID}/actions/publish",
                    accept=(200, 201, 202, 409),
                )
            elif operation == "upload_after_bucket_drift":
                client.request(
                    "PUT",
                    f"/api/deposit/depositions/{self.RECORD_ID}",
                    payload={"metadata": _manifest["metadata"]},
                    accept=(200, 202),
                )
                client.wait_for_editable_metadata(
                    self.RECORD_ID,
                    _manifest["metadata"],
                )
                current["links"]["bucket"] = (
                    "https://zenodo.org/api/files/"
                    "87654321-4321-4321-4321-cba987654321"
                )
                client.request(
                    "PUT",
                    self.BUCKET + "/paper.pdf",
                    data=upload_body,
                    content_type="application/octet-stream",
                    accept=(200, 201, 202),
                )
            elif operation == "post_put_file_appears":
                client.request(
                    "PUT",
                    f"/api/deposit/depositions/{self.RECORD_ID}",
                    payload={"metadata": _manifest["metadata"]},
                    accept=(200, 202),
                )
                current["files"] = [
                    {
                        "filename": "unexpected.txt",
                        "filesize": 1,
                        "checksum": "md5:c4ca4238a0b923820dcc509a6f75849b",
                    }
                ]
                client.wait_for_editable_metadata(
                    self.RECORD_ID,
                    _manifest["metadata"],
                )
            elif operation == "published_gate":
                client.gate_record(
                    current,
                    self.RECORD_ID,
                    _manifest["metadata"],
                    [],
                    self.DOI,
                    published=True,
                )
            elif operation == "already_published_entry":
                return {
                    "record_id": self.RECORD_ID,
                    "doi": self.DOI,
                    "phase": "public_verified",
                    "state": "published",
                }
            else:
                assert isinstance(operation, tuple)
                client.request(operation[0], operation[1])
            return {"record_id": self.RECORD_ID, "doi": self.DOI}

        module._resume_publication = original_resume

        manifest_files = (
            [upload_entry] if operation == "upload_after_bucket_drift" else []
        )
        manifest = {
            "metadata": {
                "title": "Exact C2",
                "version": "v1",
                "creators": [{"name": "Ingolf Lohmann"}],
                "description": "Exact description",
                "prereserve_doi": True,
            },
            "files": manifest_files,
        }
        evidence = {
            "phase": "record_created",
            "state": publish.CONSUMPTION_STATE,
            "record_id": self.RECORD_ID,
            "doi": self.DOI,
        }

        def execute(manifest_path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
            client = Client("z" * 32, "https://zenodo.org/api")
            return module._resume_publication(
                evidence,
                root / "zenodo-publication.json",
                manifest_path,
                root,
                manifest,
                E1,
                (
                    {("publication", "paper.pdf"): upload_body}
                    if operation == "upload_after_bucket_drift"
                    else {}
                ),
                client,
                {publish.zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32},
            )

        module.publish = execute

        class Store:
            _record_created_reconciliation_armed = True

            def __init__(instance: Any) -> None:
                instance.boundaries = 0

            def persist_and_readback(
                instance: Any,
                _path: pathlib.Path,
                phase: str,
            ) -> None:
                del instance
                events.append("durable:" + phase)
                if phase == fail_phase:
                    raise SystemExit("BLOCK: simulated remote checkpoint failure")

            def _recheck_remote_boundary(instance: Any) -> None:
                instance.boundaries += 1
                events.append("boundary")
                if fail_boundary_at == instance.boundaries:
                    raise SystemExit("BLOCK: simulated boundary drift")

        return module, Client, events, Store()

    def run_fixture(
        self,
        operation: tuple[str, str] | str,
        *,
        fail_boundary_at: int | None = None,
    ) -> tuple[list[str], Any, Any, tuple[Any, ...]]:
        preconverged = operation in {
            "metadata_put_preconverged",
            "published_gate",
            "already_published_entry",
        }
        module, client_type, events, store = self.fixture(
            operation,
            fail_boundary_at=fail_boundary_at,
        )
        originals = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=module,
        ), mock.patch.object(
            recovery,
            "_gate_r7_owned_inventory_identity",
            side_effect=lambda *_args: (
                events.append("inventory")
                or ("draft", self.draft(preconverged=preconverged))
            ),
        ):
            root = pathlib.Path(directory)
            result = recovery.run_publisher_with_checkpoints(
                root / "publish-request.json",
                root,
                store,
                reconcile_record=(self.RECORD_ID, self.DOI),
            )
        self.assertEqual(result, {"record_id": self.RECORD_ID, "doi": self.DOI})
        return events, module, client_type, originals

    @staticmethod
    def assert_restored(module: Any, client_type: Any, originals: tuple[Any, ...]) -> None:
        current = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        for observed, expected in zip(current, originals):
            if observed is not expected:
                raise AssertionError("R7 wrapper hook was not restored")

    def test_allowed_metadata_put_is_bracketed_and_restored(self) -> None:
        events, module, client_type, originals = self.run_fixture(
            "metadata_put",
        )
        self.assertEqual(events[0], "init:120:2.0")
        self.assertLess(events.index("inventory"), events.index("resume"))
        mutation = "transport:PUT:/api/deposit/depositions/21763614"
        self.assertEqual(events[-4:], ["boundary", "record-get", "boundary", mutation])
        self.assert_restored(module, client_type, originals)

    def test_preconverged_metadata_put_is_a_read_only_noop(self) -> None:
        events, module, client_type, originals = self.run_fixture(
            "metadata_put_preconverged",
        )
        self.assertEqual(
            [item for item in events if item.startswith("transport:")],
            ["transport:GET:/api/deposit/depositions/21763614"],
        )
        self.assertNotIn(
            "transport:PUT:/api/deposit/depositions/21763614",
            events,
        )
        self.assert_restored(module, client_type, originals)

    def test_published_gate_uses_only_in_memory_description_normalization(self) -> None:
        events, module, client_type, originals = self.run_fixture(
            "published_gate",
        )
        self.assertIn("original-published-gate-normalized", events)
        self.assertFalse(any(item.startswith("transport:") for item in events))
        self.assert_restored(module, client_type, originals)

    def test_already_public_entry_converges_read_only_before_inventory_arm(
        self,
    ) -> None:
        module, client_type, events, store = self.fixture(
            "already_published_entry"
        )
        originals = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=module,
        ):
            root = pathlib.Path(directory)
            result = recovery.run_publisher_with_checkpoints(
                root / "publish-request.json",
                root,
                store,
                reconcile_record=(self.RECORD_ID, self.DOI),
            )
        self.assertEqual(
            result,
            {
                "record_id": self.RECORD_ID,
                "doi": self.DOI,
                "phase": "public_verified",
                "state": "published",
            },
        )
        self.assertIn("public-wait", events)
        self.assertIn("original-published-gate-normalized", events)
        self.assertFalse(any(item.startswith("transport:") for item in events))
        self.assertFalse(any(item.startswith("durable:") for item in events))
        self.assert_restored(module, client_type, originals)

    def test_wrong_or_second_metadata_put_blocks_before_extra_transport(self) -> None:
        cases = (
            ("metadata_put_wrong_payload", 0),
            ("metadata_put_wrong_accept", 0),
            ("metadata_put_twice", 1),
            ("metadata_put_ambiguous_retry", 1),
        )
        for operation, expected_transports in cases:
            with self.subTest(operation=operation):
                module, client_type, events, store = self.fixture(operation)
                originals = (
                    module._create_consumption_receipt,
                    module._atomic_recovery_evidence,
                    module._acquire_remote_consumption_lock,
                    module._resume_publication,
                    client_type.__init__,
                    client_type.request,
                    client_type.create_paper,
                    client_type.wait_for_editable_metadata,
                    client_type.gate_record,
                )
                with tempfile.TemporaryDirectory() as directory, mock.patch.object(
                    recovery,
                    "_load_e1_publisher",
                    return_value=module,
                ), mock.patch.object(
                    recovery,
                    "_gate_r7_owned_inventory_identity",
                    return_value=("draft", self.draft()),
                ):
                    root = pathlib.Path(directory)
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        recovery.run_publisher_with_checkpoints(
                            root / "publish-request.json",
                            root,
                            store,
                            reconcile_record=(self.RECORD_ID, self.DOI),
                        )
                transports = [
                    item for item in events if item.startswith("transport:")
                ]
                self.assertEqual(len(transports), expected_transports)
                self.assert_restored(module, client_type, originals)

    def test_failed_publish_intent_checkpoint_blocks_publish_transport(self) -> None:
        module, client_type, events, store = self.fixture(
            "publish_after_failed_intent",
            fail_phase="publish_requested",
        )
        originals = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=module,
        ), mock.patch.object(
            recovery,
            "_gate_r7_owned_inventory_identity",
            return_value=("draft", self.draft()),
        ):
            root = pathlib.Path(directory)
            with self.assertRaisesRegex(SystemExit, "checkpoint failure"):
                recovery.run_publisher_with_checkpoints(
                    root / "publish-request.json",
                    root,
                    store,
                    reconcile_record=(self.RECORD_ID, self.DOI),
                )
        self.assertIn("durable:prepared", events)
        self.assertIn("durable:publish_requested", events)
        self.assertFalse(
            any(
                item
                == "transport:POST:/api/deposit/depositions/21763614/actions/publish"
                for item in events
            )
        )
        self.assert_restored(module, client_type, originals)

    def test_bucket_drift_blocks_upload_before_file_transport(self) -> None:
        module, client_type, events, store = self.fixture(
            "upload_after_bucket_drift",
        )
        originals = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=module,
        ), mock.patch.object(
            recovery,
            "_gate_r7_owned_inventory_identity",
            return_value=("draft", self.draft()),
        ):
            root = pathlib.Path(directory)
            with self.assertRaisesRegex(SystemExit, "upload bucket changed"):
                recovery.run_publisher_with_checkpoints(
                    root / "publish-request.json",
                    root,
                    store,
                    reconcile_record=(self.RECORD_ID, self.DOI),
                )
        self.assertEqual(
            events.count(
                "transport:PUT:/api/deposit/depositions/21763614"
            ),
            1,
        )
        self.assertNotIn(
            "transport:PUT:/api/files/"
            "12345678-1234-1234-1234-123456789abc/paper.pdf",
            events,
        )
        self.assert_restored(module, client_type, originals)

    def test_any_post_put_file_observation_blocks_immediately(self) -> None:
        module, client_type, events, store = self.fixture(
            "post_put_file_appears",
        )
        originals = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=module,
        ), mock.patch.object(
            recovery,
            "_gate_r7_owned_inventory_identity",
            return_value=("draft", self.draft()),
        ):
            root = pathlib.Path(directory)
            with self.assertRaisesRegex(SystemExit, "gained files"):
                recovery.run_publisher_with_checkpoints(
                    root / "publish-request.json",
                    root,
                    store,
                    reconcile_record=(self.RECORD_ID, self.DOI),
                )
        self.assertEqual(
            [item for item in events if item.startswith("transport:")],
            ["transport:PUT:/api/deposit/depositions/21763614"],
        )
        self.assert_restored(module, client_type, originals)

    def test_file_delete_upload_and_publish_block_before_metadata_convergence(self) -> None:
        forbidden = (
            ("PUT", self.BUCKET + "/paper.pdf"),
            ("DELETE", self.BUCKET + "/old-paper.pdf"),
            (
                "DELETE",
                f"/api/deposit/depositions/{self.RECORD_ID}/files/legacy-file-id",
            ),
            (
                "POST",
                f"/api/deposit/depositions/{self.RECORD_ID}/actions/publish",
            ),
        )
        for operation in forbidden:
            with self.subTest(operation=operation):
                module, client_type, events, store = self.fixture(operation)
                originals = (
                    module._create_consumption_receipt,
                    module._atomic_recovery_evidence,
                    module._acquire_remote_consumption_lock,
                    module._resume_publication,
                    client_type.__init__,
                    client_type.request,
                    client_type.create_paper,
                    client_type.wait_for_editable_metadata,
                    client_type.gate_record,
                )
                with tempfile.TemporaryDirectory() as directory, mock.patch.object(
                    recovery,
                    "_load_e1_publisher",
                    return_value=module,
                ), mock.patch.object(
                    recovery,
                    "_gate_r7_owned_inventory_identity",
                    return_value=("draft", self.draft()),
                ):
                    root = pathlib.Path(directory)
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        recovery.run_publisher_with_checkpoints(
                            root / "publish-request.json",
                            root,
                            store,
                            reconcile_record=(self.RECORD_ID, self.DOI),
                        )
                self.assertFalse(any(item.startswith("transport:") for item in events))
                self.assert_restored(module, client_type, originals)

    def test_create_and_nonallowlisted_mutations_fail_before_transport(self) -> None:
        forbidden: tuple[tuple[str, str] | str, ...] = (
            "create_paper",
            ("POST", "/api/deposit/depositions"),
            (
                "POST",
                f"/api/deposit/depositions/{self.RECORD_ID}/actions/newversion",
            ),
            ("DELETE", f"/api/deposit/depositions/{self.RECORD_ID}"),
            ("PUT", "/api/deposit/depositions/21763615"),
        )
        for operation in forbidden:
            with self.subTest(operation=operation):
                module, client_type, events, store = self.fixture(operation)
                originals = (
                    module._create_consumption_receipt,
                    module._atomic_recovery_evidence,
                    module._acquire_remote_consumption_lock,
                    module._resume_publication,
                    client_type.__init__,
                    client_type.request,
                    client_type.create_paper,
                    client_type.wait_for_editable_metadata,
                    client_type.gate_record,
                )
                with tempfile.TemporaryDirectory() as directory, mock.patch.object(
                    recovery,
                    "_load_e1_publisher",
                    return_value=module,
                ), mock.patch.object(
                    recovery,
                    "_gate_r7_owned_inventory_identity",
                    return_value=("draft", self.draft()),
                ):
                    root = pathlib.Path(directory)
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        recovery.run_publisher_with_checkpoints(
                            root / "publish-request.json",
                            root,
                            store,
                            reconcile_record=(self.RECORD_ID, self.DOI),
                        )
                self.assertFalse(any(item.startswith("transport:") for item in events))
                self.assertNotIn("original-create", events)
                self.assert_restored(module, client_type, originals)

    def test_second_boundary_drift_blocks_the_original_transport(self) -> None:
        module, client_type, events, store = self.fixture(
            "metadata_put",
            fail_boundary_at=3,
        )
        originals = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=module,
        ), mock.patch.object(
            recovery,
            "_gate_r7_owned_inventory_identity",
            return_value=("draft", self.draft()),
        ):
            root = pathlib.Path(directory)
            with self.assertRaisesRegex(SystemExit, "simulated boundary drift"):
                recovery.run_publisher_with_checkpoints(
                    root / "publish-request.json",
                    root,
                    store,
                    reconcile_record=(self.RECORD_ID, self.DOI),
                )
        self.assertEqual(events.count("boundary"), 3)
        self.assertIn("record-get", events)
        self.assertFalse(any(item.startswith("transport:") for item in events))
        self.assert_restored(module, client_type, originals)

    def test_invalid_target_blocks_before_loading_or_installing_hooks(self) -> None:
        with mock.patch.object(recovery, "_load_e1_publisher") as loader:
            with self.assertRaisesRegex(SystemExit, "target differs from exact C2"):
                recovery.run_publisher_with_checkpoints(
                    pathlib.Path("publish-request.json"),
                    pathlib.Path("."),
                    object(),
                    reconcile_record=(self.RECORD_ID + 1, self.DOI),
                )
        loader.assert_not_called()


class VRTCoreH3E1R7PinnedE1IntegrationTests(unittest.TestCase):
    RECORD_ID = 21763614
    DOI = "10.5281/zenodo.21763614"
    BUCKET_ID = "12345678-1234-1234-1234-123456789abc"

    def test_real_e1_prepare_upload_checkpoint_publish_order_and_restoration(self) -> None:
        module = recovery._load_e1_publisher(ROOT)
        manifest_path = (
            ROOT
            / "release/vrtcore-relational-h3-publication-2026-08-02"
            / "publish-request.json"
        )
        loaded = module.load_manifest(manifest_path, ROOT)
        metadata = copy.deepcopy(loaded["metadata"])
        body = b"exact-r7-pinned-e1-integration\n"
        entry = {
            "path": "integration.txt",
            "name": "integration.txt",
            "size": len(body),
            "md5": hashlib.md5(body).hexdigest(),  # noqa: S324
            "sha256": hashlib.sha256(body).hexdigest(),
        }
        manifest = copy.deepcopy(loaded)
        manifest["files"] = [entry]
        entries = [dict(entry)]
        verified = {("publication", entry["name"]): body}
        events: list[str] = []

        def normalized_creators() -> list[dict[str, Any]]:
            value = copy.deepcopy(metadata["creators"])
            for creator in value:
                creator.setdefault("affiliation", None)
            return value

        def normalized_metadata() -> dict[str, Any]:
            value = copy.deepcopy(metadata)
            value["creators"] = normalized_creators()
            value["prereserve_doi"] = {"doi": self.DOI}
            value["license"] = {"id": value["license"]}
            value["resource_type"] = {
                "type": value.pop("upload_type"),
                "subtype": value.pop("publication_type"),
            }
            return value

        state: dict[str, Any] = {
            "published": False,
            "metadata": {
                "title": metadata["title"],
                "version": metadata["version"],
                "creators": normalized_creators(),
                "notes": "stale pre-R8 metadata",
                "prereserve_doi": {"doi": self.DOI},
            },
            "files": {},
        }

        class Transport:
            @staticmethod
            def response(status: int, value: Any) -> Any:
                raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
                return module.zenodo.HttpResponse(
                    status=status,
                    headers={"Content-Type": "application/json"},
                    body=raw,
                )

            @staticmethod
            def file_items() -> list[dict[str, Any]]:
                return [
                    {
                        "filename": name,
                        "filesize": len(raw),
                        "checksum": "md5:" + hashlib.md5(raw).hexdigest(),  # noqa: S324
                        "links": {
                            "download": (
                                "https://zenodo.org/api/files/"
                                + self.BUCKET_ID
                                + "/"
                                + urllib.parse.quote(name, safe="")
                            )
                        },
                    }
                    for name, raw in state["files"].items()
                ]

            @classmethod
            def draft(cls) -> dict[str, Any]:
                return {
                    "id": self.RECORD_ID,
                    "metadata": copy.deepcopy(state["metadata"]),
                    "links": {
                        "bucket": (
                            "https://zenodo.org/api/files/" + self.BUCKET_ID
                        )
                    },
                    "files": cls.file_items(),
                    "submitted": bool(state["published"]),
                    "state": "done" if state["published"] else "unsubmitted",
                }

            @classmethod
            def public(cls) -> dict[str, Any]:
                public_metadata = normalized_metadata()
                public_metadata.pop("prereserve_doi", None)
                public_metadata["doi"] = self.DOI
                return {
                    "id": self.RECORD_ID,
                    "conceptdoi": "10.5281/zenodo.21763613",
                    "metadata": public_metadata,
                    "files": cls.file_items(),
                    "links": {
                        "html": f"https://zenodo.org/records/{self.RECORD_ID}",
                    },
                }

            def request(
                instance: Any,
                method: str,
                url: str,
                *,
                body: bytes | None = None,
                content_type: str | None = None,
                max_response_bytes: int,
            ) -> Any:
                del instance, max_response_bytes
                path = urllib.parse.urlsplit(url).path
                events.append("http:" + method + ":" + path)
                deposition = f"/api/deposit/depositions/{self.RECORD_ID}"
                bucket = "/api/files/" + self.BUCKET_ID
                if method == "GET" and path == deposition:
                    return Transport.response(200, Transport.draft())
                if method == "GET" and path == f"/api/records/{self.RECORD_ID}":
                    return Transport.response(
                        200 if state["published"] else 404,
                        Transport.public() if state["published"] else {},
                    )
                if method == "PUT" and path == deposition:
                    self.assertEqual(content_type, "application/json")
                    assert body is not None
                    payload = json.loads(body.decode("utf-8"))
                    self.assertEqual(payload, {"metadata": metadata})
                    state["metadata"] = normalized_metadata()
                    return Transport.response(200, Transport.draft())
                if method == "PUT" and path == bucket + "/integration.txt":
                    self.assertEqual(content_type, "application/octet-stream")
                    self.assertEqual(body, b"exact-r7-pinned-e1-integration\n")
                    assert body is not None
                    state["files"]["integration.txt"] = body
                    return Transport.response(200, {"key": "integration.txt"})
                if method == "GET" and path == bucket + "/integration.txt":
                    return module.zenodo.HttpResponse(
                        status=200,
                        headers={"Content-Type": "application/octet-stream"},
                        body=state["files"]["integration.txt"],
                    )
                if method == "POST" and path == deposition + "/actions/publish":
                    self.assertIsNone(body)
                    state["published"] = True
                    return Transport.response(202, Transport.public())
                raise AssertionError(f"unexpected E1 transport request: {method} {path}")

        transport = Transport()

        class Store:
            _record_created_reconciliation_armed = True

            def _recheck_remote_boundary(instance: Any) -> None:
                del instance
                events.append("boundary")

            def persist_and_readback(
                instance: Any,
                _path: pathlib.Path,
                phase: str,
            ) -> None:
                del instance
                events.append("durable:" + phase)

        store = Store()
        def execute(manifest_arg: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
            remote_consumption = {
                "ref": "refs/tags/qikvrt-r7-integration",
                "tag_object": "a" * 40,
            }
            evidence = module._phase_evidence(
                manifest_arg,
                root,
                manifest,
                E1,
                remote_consumption,
                "record_created",
                record_id=self.RECORD_ID,
                doi=self.DOI,
            )
            client = module.zenodo.ZenodoClient(
                "z" * 32,
                "https://zenodo.org/api",
                transport,
                sleeper=lambda _seconds: None,
            )
            return module._resume_publication(
                evidence,
                root / "zenodo-publication.json",
                manifest_arg,
                root,
                manifest,
                E1,
                verified,
                client,
                {
                    module.zenodo.TOKEN_ENVIRONMENT_VARIABLE: "z" * 32,
                    module.GITHUB_TOKEN_ENVIRONMENT_VARIABLE: "g" * 32,
                },
            )

        client_type = module.zenodo.ZenodoClient
        originals = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        initial = Transport.draft()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            recovery,
            "_load_e1_publisher",
            return_value=module,
        ), mock.patch.object(
            recovery,
            "_gate_r7_owned_inventory_identity",
            return_value=("draft", initial),
        ), mock.patch.object(
            module,
            "_verify_remote_consumption_lock",
            return_value=None,
        ), mock.patch.object(
            module,
            "publish",
            new=execute,
        ):
            root = pathlib.Path(directory)
            result = recovery.run_publisher_with_checkpoints(
                root / "publish-request.json",
                root,
                store,
                reconcile_record=(self.RECORD_ID, self.DOI),
            )
        self.assertEqual(
            (result.get("record_id"), result.get("doi"), result.get("phase")),
            (self.RECORD_ID, self.DOI, "public_verified"),
        )
        self.assertTrue(state["published"])
        self.assertEqual(state["files"], {"integration.txt": body})
        self.assertFalse(any(event.startswith("http:DELETE:") for event in events))
        self.assertLess(events.index("durable:prepared"), events.index("durable:publish_requested"))
        publish_event = "http:POST:/api/deposit/depositions/21763614/actions/publish"
        self.assertLess(events.index("durable:publish_requested"), events.index(publish_event))
        restored = (
            module._create_consumption_receipt,
            module._atomic_recovery_evidence,
            module._acquire_remote_consumption_lock,
            module._resume_publication,
            client_type.__init__,
            client_type.request,
            client_type.create_paper,
            client_type.wait_for_editable_metadata,
            client_type.gate_record,
        )
        self.assertEqual(restored, originals)


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
        store.publisher = publish
        store.create_post_once_head = None
        store._initial_create_replay_pending = False
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

    def test_exact_unsent_create_replay_restores_c0_but_keeps_remote_c1(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            evidence_path = root / "state" / "zenodo-publication.json"
            store = self.store(root, evidence_path)
            store.current_tip = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
            store._initial_create_replay_pending = True
            c0_raw = b'{"phase":"authorization_consumed"}\n'

            def git(
                _root: pathlib.Path,
                *arguments: str,
                **_kwargs: object,
            ) -> tuple[int, bytes]:
                expected = (
                    "show",
                    str(recovery.R4_UNSENT_CREATE_INCIDENT["c0"])
                    + ":"
                    + recovery.EVIDENCE_RELATIVE.as_posix(),
                )
                if arguments == expected:
                    return 0, c0_raw
                raise AssertionError("unexpected C0 restore Git call: " + repr(arguments))

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
                return_value=[
                    {"phase": "authorization_consumed"},
                    {"phase": "create_requested"},
                ],
            ):
                self.assertEqual(
                    store.restore_or_bootstrap(),
                    (False, recovery.R4_UNSENT_CREATE_INCIDENT["c1"]),
                )
            self.assertEqual(evidence_path.read_bytes(), c0_raw)
            self.assertEqual(
                store.current_tip,
                recovery.R4_UNSENT_CREATE_INCIDENT["c1"],
            )

    def test_record_bearing_recovery_without_marker_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            evidence_path = root / "state" / "zenodo-publication.json"
            store = self.store(root, evidence_path)
            store.current_tip = "b" * 40
            with mock.patch.object(
                recovery,
                "_fetch_credential_free",
            ), mock.patch.object(
                store,
                "validate_recovery_chain",
                return_value=[
                    {"phase": "authorization_consumed"},
                    {"phase": "create_requested"},
                    {"phase": "record_created"},
                ],
            ):
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    store.restore_or_bootstrap()

    def test_marker_with_only_c0_or_no_recovery_chain_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            store = self.store(root, root / "state" / "zenodo-publication.json")
            store.current_tip = recovery.R4_UNSENT_CREATE_INCIDENT["c0"]
            store.create_post_once_head = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
            with mock.patch.object(
                recovery,
                "_fetch_credential_free",
            ), mock.patch.object(
                store,
                "validate_recovery_chain",
                return_value=[{"phase": "authorization_consumed"}],
            ):
                with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                    store.restore_or_bootstrap()


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
        store.create_post_once_head = None
        store._prepared_replay_pending = False
        store._initial_create_replay_pending = False
        store._r9_controller = None
        return store

    def test_r9_trigger_branch_drift_blocks_the_remote_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(pathlib.Path(directory))
            store._r9_controller = "e" * 40

            def read_ref(
                _api: Any,
                ref: str,
                *,
                allow_absent: bool = False,
            ) -> str | None:
                del allow_absent
                if ref == "refs/heads/main":
                    return store.controller_parent
                if ref == "refs/heads/" + recovery.EXPECTED["trigger_branch"]:
                    return "c" * 40
                raise AssertionError("boundary read passed the moved trigger")

            with mock.patch.object(
                recovery,
                "_read_head_ref",
                side_effect=read_ref,
            ), mock.patch.object(
                recovery,
                "_validate_existing_consumption_tag",
            ) as tag:
                with self.assertRaisesRegex(SystemExit, "trigger branch moved"):
                    store._recheck_remote_boundary()
            tag.assert_not_called()

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
        store.create_post_once_head = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
        store._prepared_replay_pending = False
        store._initial_create_replay_pending = False
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
        store.create_post_once_head = recovery.R4_UNSENT_CREATE_INCIDENT["c1"]
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

    def test_final_persistence_blocks_without_the_c1_marker(self) -> None:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.current_tip = "a" * 40
        store._prepared_replay_pending = False
        store._initial_create_replay_pending = False
        store.create_post_once_head = None
        with self.assertRaisesRegex(SystemExit, "BLOCK:"):
            store.persist_final()

    def test_recovery_chain_must_be_an_exact_phase_prefix(self) -> None:
        store = object.__new__(recovery.RecoveryReceiptStore)
        store.root = ROOT
        store.publisher = publish
        store.remote_consumption = {
            "tag_object": recovery.EXPECTED["tag_object"],
        }
        first = str(recovery.R4_UNSENT_CREATE_INCIDENT["c0"])
        tip = str(recovery.R4_UNSENT_CREATE_INCIDENT["c1"])
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
        if path in {run_path, run_path + "/attempts/1"}:
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


class FakeR4IncidentAPI:
    def __init__(
        self,
        log: bytes,
        artifact_zip: bytes,
        incident: Mapping[str, Any] | None = None,
    ) -> None:
        self.incident = incident or recovery.R4_UNSENT_CREATE_INCIDENT
        incident = self.incident
        self.log = log
        self.artifact_zip = artifact_zip
        self.calls: list[tuple[str, str]] = []
        self.run = {
            "id": incident["run_id"],
            "run_attempt": 1,
            "event": "push",
            "head_sha": incident["controller"],
            "head_branch": recovery.EXPECTED["trigger_branch"],
            "status": "completed",
            "conclusion": "failure",
            "repository": {"full_name": recovery.EXPECTED["repository"]},
            "head_repository": {"full_name": recovery.EXPECTED["repository"]},
        }
        self.job = {
            "id": incident["job_id"],
            "run_id": incident["run_id"],
            "run_attempt": 1,
            "head_sha": incident["controller"],
            "status": "completed",
            "conclusion": "failure",
            "run_url": (
                "https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs/"
                + str(incident["run_id"])
            ),
        }
        self.artifacts = {
            "total_count": 1,
            "artifacts": [
                {
                    "id": incident["artifact_id"],
                    "name": incident["artifact_name"],
                    "size_in_bytes": incident["artifact_size"],
                    "digest": incident["artifact_digest"],
                    "expired": False,
                }
            ],
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        **_kwargs: object,
    ) -> tuple[int, dict[str, Any]]:
        if method != "GET" or payload is not None:
            raise AssertionError("R4 incident API attempted a mutation")
        self.calls.append((method, path))
        incident = self.incident
        run_path = (
            "/repos/Goldkelch/qik-vrt/actions/runs/" + str(incident["run_id"])
        )
        job_path = (
            "/repos/Goldkelch/qik-vrt/actions/jobs/" + str(incident["job_id"])
        )
        if path in {run_path, run_path + "/attempts/1"}:
            return 200, copy.deepcopy(self.run)
        if path == job_path:
            return 200, copy.deepcopy(self.job)
        if path == run_path + "/artifacts":
            return 200, copy.deepcopy(self.artifacts)
        raise AssertionError("unexpected recovery incident path: " + path)

    def request_bytes(self, path: str, maximum: int) -> bytes:
        incident = self.incident
        log_path = (
            "/repos/Goldkelch/qik-vrt/actions/jobs/"
            + str(incident["job_id"])
            + "/logs"
        )
        artifact_path = (
            "/repos/Goldkelch/qik-vrt/actions/artifacts/"
            + str(incident["artifact_id"])
            + "/zip"
        )
        self.calls.append(("GET_BYTES", path))
        if path == log_path and maximum == incident["log_bytes"]:
            return self.log
        if path == artifact_path and maximum == incident["artifact_size"]:
            return self.artifact_zip
        raise AssertionError("recovery incident raw request differs")


class VRTCoreH3E1R4UnsentCreateIncidentTests(unittest.TestCase):
    @staticmethod
    def artifact_fixture() -> tuple[bytes, dict[str, Any]]:
        evidence = subprocess.check_output(
            [
                "git",
                "show",
                str(recovery.R4_UNSENT_CREATE_INCIDENT["c1"])
                + ":"
                + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
        )
        buffer = recovery.io.BytesIO()
        with recovery.zipfile.ZipFile(
            buffer,
            mode="w",
            compression=recovery.zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            entry = recovery.zipfile.ZipInfo(
                str(recovery.R4_UNSENT_CREATE_INCIDENT["artifact_entry"]),
                (2026, 8, 2, 19, 24, 26),
            )
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            entry.compress_type = recovery.zipfile.ZIP_DEFLATED
            archive.writestr(entry, evidence, compresslevel=6)
        raw = buffer.getvalue()
        with recovery.zipfile.ZipFile(recovery.io.BytesIO(raw), mode="r") as archive:
            parsed = archive.infolist()[0]
        overrides = {
            "artifact_size": len(raw),
            "artifact_digest": "sha256:" + recovery.hashlib.sha256(raw).hexdigest(),
            "artifact_entry_compressed_bytes": parsed.compress_size,
            "artifact_entry_crc32": parsed.CRC,
            "artifact_entry_unix_mode": parsed.external_attr >> 16,
        }
        return raw, overrides

    @staticmethod
    def log_bytes() -> bytes:
        lines: list[str] = []
        for marker, count in recovery.R4_INCIDENT_LOG_REQUIRED_COUNTS.items():
            lines.extend(marker for _index in range(count))
        prefix = b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8")
        size = int(recovery.R4_UNSENT_CREATE_INCIDENT["log_bytes"])
        if len(prefix) > size:
            raise AssertionError("R4 incident fixture exceeds exact size")
        return prefix + b"x" * (size - len(prefix))

    @staticmethod
    def verify(api: FakeR4IncidentAPI, *, digest_for: bytes) -> None:
        real_sha256 = recovery.hashlib.sha256

        class FixedDigest:
            def hexdigest(self) -> str:
                return str(recovery.R4_UNSENT_CREATE_INCIDENT["log_sha256"])

        def sha256(raw: bytes = b"") -> Any:
            if raw == digest_for:
                return FixedDigest()
            return real_sha256(raw)

        with mock.patch.object(recovery.hashlib, "sha256", side_effect=sha256):
            recovery.verify_historical_r4_unsent_create_incident(api, ROOT)

    def test_exact_r4_run_job_artifact_and_log_are_read_only(self) -> None:
        raw = self.log_bytes()
        artifact_zip, overrides = self.artifact_fixture()
        with mock.patch.dict(recovery.R4_UNSENT_CREATE_INCIDENT, overrides):
            api = FakeR4IncidentAPI(raw, artifact_zip)
            self.verify(api, digest_for=raw)
        self.assertEqual(
            [method for method, _path in api.calls],
            ["GET", "GET", "GET", "GET_BYTES", "GET_BYTES"],
        )

    def test_r4_c0_c1_commit_tree_parent_and_evidence_pins_are_real(self) -> None:
        recovery._verify_r4_local_object_chain(ROOT)

    def test_r4_metadata_or_artifact_tampering_blocks(self) -> None:
        raw = self.log_bytes()
        artifact_zip, overrides = self.artifact_fixture()
        with mock.patch.dict(recovery.R4_UNSENT_CREATE_INCIDENT, overrides):
            run_api = FakeR4IncidentAPI(raw, artifact_zip)
            run_api.run["head_sha"] = "c" * 40
            artifact_api = FakeR4IncidentAPI(raw, artifact_zip)
            artifact_api.artifacts["artifacts"][0]["digest"] = "sha256:" + "0" * 64
            for label, api in (("run", run_api), ("artifact", artifact_api)):
                with self.subTest(label=label):
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(api, digest_for=raw)
                    self.assertTrue(
                        all(
                            method in {"GET", "GET_BYTES"}
                            for method, _path in api.calls
                        )
                    )

    def test_r4_artifact_zip_structure_and_c1_bytes_fail_closed(self) -> None:
        log = self.log_bytes()
        evidence = subprocess.check_output(
            [
                "git",
                "show",
                str(recovery.R4_UNSENT_CREATE_INCIDENT["c1"])
                + ":"
                + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
        )

        def build(
            *,
            name: str,
            body: bytes,
            mode: int = 0o100600,
            extra_entry: bool = False,
        ) -> tuple[bytes, dict[str, Any]]:
            buffer = recovery.io.BytesIO()
            with recovery.zipfile.ZipFile(
                buffer,
                mode="w",
                compression=recovery.zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                entry = recovery.zipfile.ZipInfo(name, (2026, 8, 2, 19, 24, 26))
                entry.create_system = 3
                entry.external_attr = mode << 16
                entry.compress_type = recovery.zipfile.ZIP_DEFLATED
                archive.writestr(entry, body, compresslevel=6)
                if extra_entry:
                    archive.writestr("unexpected.txt", b"unexpected")
            artifact = buffer.getvalue()
            with recovery.zipfile.ZipFile(
                recovery.io.BytesIO(artifact), mode="r"
            ) as archive:
                parsed = archive.infolist()[0]
            return artifact, {
                "artifact_size": len(artifact),
                "artifact_digest": (
                    "sha256:" + recovery.hashlib.sha256(artifact).hexdigest()
                ),
                "artifact_entry_compressed_bytes": parsed.compress_size,
                "artifact_entry_crc32": parsed.CRC,
            }

        changed_evidence = evidence.replace(b'"create_requested"', b'"create_requesteD"', 1)
        self.assertEqual(len(changed_evidence), len(evidence))
        cases = (
            build(
                name=str(recovery.R4_UNSENT_CREATE_INCIDENT["artifact_entry"]),
                body=evidence,
                extra_entry=True,
            ),
            build(name="../zenodo-publication.json", body=evidence),
            build(
                name=str(recovery.R4_UNSENT_CREATE_INCIDENT["artifact_entry"]),
                body=evidence,
                mode=0o120777,
            ),
            build(
                name=str(recovery.R4_UNSENT_CREATE_INCIDENT["artifact_entry"]),
                body=changed_evidence,
            ),
        )
        for index, (artifact_zip, overrides) in enumerate(cases):
            with self.subTest(index=index):
                with mock.patch.dict(recovery.R4_UNSENT_CREATE_INCIDENT, overrides):
                    api = FakeR4IncidentAPI(log, artifact_zip)
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(api, digest_for=log)
                    self.assertTrue(
                        all(
                            method in {"GET", "GET_BYTES"}
                            for method, _path in api.calls
                        )
                    )

    def test_r4_log_bom_digest_and_effect_markers_are_exact(self) -> None:
        raw = self.log_bytes()
        artifact_zip, overrides = self.artifact_fixture()
        without_bom = b"xxx" + raw[3:]
        with mock.patch.dict(recovery.R4_UNSENT_CREATE_INCIDENT, overrides):
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(
                    FakeR4IncidentAPI(without_bom, artifact_zip),
                    digest_for=without_bom,
                )

            marker = next(iter(recovery.R4_INCIDENT_LOG_REQUIRED_COUNTS))
            marker_tampered = raw.replace(
                marker.encode("utf-8"),
                ("_" * len(marker)).encode("utf-8"),
                1,
            )
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(
                    FakeR4IncidentAPI(marker_tampered, artifact_zip),
                    digest_for=marker_tampered,
                )

            published = recovery.R4_INCIDENT_LOG_FORBIDDEN_MARKERS[0].encode("utf-8")
            effect_tampered = raw[:-len(published)] + published
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(
                    FakeR4IncidentAPI(effect_tampered, artifact_zip),
                    digest_for=effect_tampered,
                )


class VRTCoreH3E1R5RecordCreatedIncidentTests(unittest.TestCase):
    @staticmethod
    def evidence() -> bytes:
        incident = recovery.R5_RECORD_CREATED_TIMEOUT_INCIDENT
        return subprocess.check_output(
            [
                "git",
                "show",
                str(incident["c2"])
                + ":"
                + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
        )

    @classmethod
    def artifact_fixture(
        cls,
        body: bytes | None = None,
    ) -> tuple[bytes, dict[str, Any]]:
        incident = recovery.R5_RECORD_CREATED_TIMEOUT_INCIDENT
        evidence = cls.evidence() if body is None else body
        buffer = recovery.io.BytesIO()
        with recovery.zipfile.ZipFile(
            buffer,
            mode="w",
            compression=recovery.zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            entry = recovery.zipfile.ZipInfo(
                str(incident["artifact_entry"]),
                (2026, 8, 2, 20, 2, 28),
            )
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            entry.compress_type = recovery.zipfile.ZIP_DEFLATED
            archive.writestr(entry, evidence, compresslevel=6)
        raw = buffer.getvalue()
        with recovery.zipfile.ZipFile(recovery.io.BytesIO(raw), mode="r") as archive:
            parsed = archive.infolist()[0]
        return raw, {
            "artifact_size": len(raw),
            "artifact_digest": "sha256:" + recovery.hashlib.sha256(raw).hexdigest(),
            "artifact_entry_compressed_bytes": parsed.compress_size,
            "artifact_entry_crc32": parsed.CRC,
            "artifact_entry_unix_mode": parsed.external_attr >> 16,
        }

    @staticmethod
    def log_bytes() -> bytes:
        lines: list[str] = []
        for marker, count in recovery.R5_TIMEOUT_LOG_REQUIRED_COUNTS.items():
            lines.extend(marker for _index in range(count))
        prefix = b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8")
        size = int(recovery.R5_RECORD_CREATED_TIMEOUT_INCIDENT["log_bytes"])
        if len(prefix) > size:
            raise AssertionError("R5 incident fixture exceeds exact size")
        return prefix + b"x" * (size - len(prefix))

    @staticmethod
    def verify(api: FakeR4IncidentAPI, *, digest_for: bytes) -> None:
        incident = recovery.R5_RECORD_CREATED_TIMEOUT_INCIDENT
        real_sha256 = recovery.hashlib.sha256

        class FixedDigest:
            def hexdigest(self) -> str:
                return str(incident["log_sha256"])

        def sha256(raw: bytes = b"") -> Any:
            if raw == digest_for:
                return FixedDigest()
            return real_sha256(raw)

        with mock.patch.object(recovery.hashlib, "sha256", side_effect=sha256):
            recovery.verify_historical_r5_record_created_timeout(api, ROOT)

    def test_exact_r5_run_job_artifact_and_log_are_read_only(self) -> None:
        incident = recovery.R5_RECORD_CREATED_TIMEOUT_INCIDENT
        log = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            api = FakeR4IncidentAPI(log, artifact, incident)
            self.verify(api, digest_for=log)
        self.assertEqual(
            [method for method, _path in api.calls],
            ["GET", "GET", "GET", "GET_BYTES", "GET_BYTES"],
        )

    def test_r5_controller_c2_parent_tree_and_evidence_pins_are_real(self) -> None:
        recovery._verify_r5_local_object_chain(ROOT)

    def test_r5_metadata_artifact_and_c2_byte_tampering_block(self) -> None:
        incident = recovery.R5_RECORD_CREATED_TIMEOUT_INCIDENT
        log = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            run_api = FakeR4IncidentAPI(log, artifact, incident)
            run_api.run["head_sha"] = "c" * 40
            digest_api = FakeR4IncidentAPI(log, artifact, incident)
            digest_api.artifacts["artifacts"][0]["digest"] = "sha256:" + "0" * 64
            for label, api in (("run", run_api), ("artifact", digest_api)):
                with self.subTest(label=label):
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(api, digest_for=log)
                    self.assertTrue(
                        all(
                            method in {"GET", "GET_BYTES"}
                            for method, _path in api.calls
                        )
                    )

        evidence = self.evidence()
        changed = evidence.replace(b'"record_created"', b'"record_createD"', 1)
        self.assertEqual(len(changed), len(evidence))
        changed_artifact, changed_overrides = self.artifact_fixture(changed)
        with mock.patch.dict(incident, changed_overrides):
            api = FakeR4IncidentAPI(log, changed_artifact, incident)
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(api, digest_for=log)

    def test_r5_log_bom_required_and_forbidden_markers_are_exact(self) -> None:
        incident = recovery.R5_RECORD_CREATED_TIMEOUT_INCIDENT
        raw = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        without_bom = b"xxx" + raw[3:]
        marker = next(iter(recovery.R5_TIMEOUT_LOG_REQUIRED_COUNTS))
        marker_tampered = raw.replace(
            marker.encode("utf-8"),
            ("_" * len(marker)).encode("utf-8"),
            1,
        )
        published = recovery.R5_TIMEOUT_LOG_FORBIDDEN_MARKERS[0].encode("utf-8")
        forbidden = raw[: -len(published)] + published
        with mock.patch.dict(incident, overrides):
            for label, log in (
                ("bom", without_bom),
                ("required", marker_tampered),
                ("forbidden", forbidden),
            ):
                with self.subTest(label=label):
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(
                            FakeR4IncidentAPI(log, artifact, incident),
                            digest_for=log,
                        )


class VRTCoreH3E1R6DraftMetadataIncidentTests(unittest.TestCase):
    @staticmethod
    def evidence() -> bytes:
        incident = recovery.R6_DRAFT_METADATA_INCIDENT
        return subprocess.check_output(
            [
                "git",
                "show",
                str(incident["c2"])
                + ":"
                + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
        )

    @classmethod
    def artifact_fixture(cls) -> tuple[bytes, dict[str, Any]]:
        incident = recovery.R6_DRAFT_METADATA_INCIDENT
        buffer = recovery.io.BytesIO()
        with recovery.zipfile.ZipFile(
            buffer,
            mode="w",
            compression=recovery.zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            entry = recovery.zipfile.ZipInfo(
                str(incident["artifact_entry"]),
                (2026, 8, 2, 21, 52, 8),
            )
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            entry.compress_type = recovery.zipfile.ZIP_DEFLATED
            archive.writestr(entry, cls.evidence(), compresslevel=6)
        raw = buffer.getvalue()
        with recovery.zipfile.ZipFile(recovery.io.BytesIO(raw), mode="r") as archive:
            parsed = archive.infolist()[0]
        return raw, {
            "artifact_size": len(raw),
            "artifact_digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "artifact_entry_compressed_bytes": parsed.compress_size,
            "artifact_entry_crc32": parsed.CRC,
            "artifact_entry_unix_mode": parsed.external_attr >> 16,
        }

    @staticmethod
    def log_bytes() -> bytes:
        lines: list[str] = []
        for marker, count in recovery.R6_METADATA_LOG_REQUIRED_COUNTS.items():
            lines.extend(marker for _index in range(count))
        prefix = b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8")
        size = int(recovery.R6_DRAFT_METADATA_INCIDENT["log_bytes"])
        if len(prefix) > size:
            raise AssertionError("R6 incident fixture exceeds exact size")
        return prefix + b"x" * (size - len(prefix))

    @staticmethod
    def verify(api: FakeR4IncidentAPI, *, digest_for: bytes) -> None:
        incident = recovery.R6_DRAFT_METADATA_INCIDENT
        real_sha256 = recovery.hashlib.sha256

        class FixedDigest:
            def hexdigest(self) -> str:
                return str(incident["log_sha256"])

        def sha256(raw: bytes = b"") -> Any:
            if raw == digest_for:
                return FixedDigest()
            return real_sha256(raw)

        with mock.patch.object(recovery.hashlib, "sha256", side_effect=sha256):
            recovery.verify_historical_r6_draft_metadata_incident(api, ROOT)

    def test_exact_r6_run_job_artifact_and_log_are_read_only(self) -> None:
        incident = recovery.R6_DRAFT_METADATA_INCIDENT
        log = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            api = FakeR4IncidentAPI(log, artifact, incident)
            self.verify(api, digest_for=log)
        self.assertEqual(
            [method for method, _path in api.calls],
            ["GET", "GET", "GET", "GET_BYTES", "GET_BYTES"],
        )

    def test_r6_controller_parent_tree_and_c2_pins_are_real(self) -> None:
        recovery._verify_r6_local_object_chain(ROOT)

    def test_r6_log_and_artifact_tampering_block(self) -> None:
        incident = recovery.R6_DRAFT_METADATA_INCIDENT
        raw = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        marker = next(iter(recovery.R6_METADATA_LOG_REQUIRED_COUNTS))
        changed_log = raw.replace(
            marker.encode("utf-8"),
            ("_" * len(marker)).encode("utf-8"),
            1,
        )
        with mock.patch.dict(incident, overrides):
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(
                    FakeR4IncidentAPI(changed_log, artifact, incident),
                    digest_for=changed_log,
                )
            api = FakeR4IncidentAPI(raw, artifact, incident)
            api.artifacts["artifacts"][0]["digest"] = "sha256:" + "0" * 64
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(api, digest_for=raw)

    def test_r6_public_or_effect_function_markers_are_forbidden(self) -> None:
        incident = recovery.R6_DRAFT_METADATA_INCIDENT
        raw = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            for marker in recovery.R6_METADATA_LOG_FORBIDDEN_MARKERS:
                with self.subTest(marker=marker):
                    encoded = marker.encode("utf-8")
                    changed = raw[: -len(encoded)] + encoded
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(
                            FakeR4IncidentAPI(changed, artifact, incident),
                            digest_for=changed,
                        )


class VRTCoreH3E1R7CreatorNormalizationIncidentTests(unittest.TestCase):
    @staticmethod
    def evidence() -> bytes:
        incident = recovery.R7_CREATOR_NORMALIZATION_INCIDENT
        return subprocess.check_output(
            [
                "git",
                "show",
                str(incident["c2"])
                + ":"
                + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
        )

    @classmethod
    def artifact_fixture(cls) -> tuple[bytes, dict[str, Any]]:
        incident = recovery.R7_CREATOR_NORMALIZATION_INCIDENT
        buffer = recovery.io.BytesIO()
        with recovery.zipfile.ZipFile(
            buffer,
            mode="w",
            compression=recovery.zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            entry = recovery.zipfile.ZipInfo(
                str(incident["artifact_entry"]),
                (2026, 8, 2, 22, 44, 40),
            )
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            entry.compress_type = recovery.zipfile.ZIP_DEFLATED
            archive.writestr(entry, cls.evidence(), compresslevel=6)
        raw = buffer.getvalue()
        with recovery.zipfile.ZipFile(recovery.io.BytesIO(raw), mode="r") as archive:
            parsed = archive.infolist()[0]
        return raw, {
            "artifact_size": len(raw),
            "artifact_digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "artifact_entry_compressed_bytes": parsed.compress_size,
            "artifact_entry_crc32": parsed.CRC,
            "artifact_entry_unix_mode": parsed.external_attr >> 16,
        }

    @staticmethod
    def log_bytes() -> bytes:
        lines: list[str] = []
        for marker, count in recovery.R7_CREATOR_LOG_REQUIRED_COUNTS.items():
            lines.extend(marker for _index in range(count))
        prefix = b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8")
        size = int(recovery.R7_CREATOR_NORMALIZATION_INCIDENT["log_bytes"])
        if len(prefix) > size:
            raise AssertionError("R7 incident fixture exceeds exact size")
        return prefix + b"x" * (size - len(prefix))

    @staticmethod
    def verify(api: FakeR4IncidentAPI, *, digest_for: bytes) -> None:
        incident = recovery.R7_CREATOR_NORMALIZATION_INCIDENT
        real_sha256 = recovery.hashlib.sha256

        class FixedDigest:
            def hexdigest(self) -> str:
                return str(incident["log_sha256"])

        def sha256(raw: bytes = b"") -> Any:
            if raw == digest_for:
                return FixedDigest()
            return real_sha256(raw)

        with mock.patch.object(recovery.hashlib, "sha256", side_effect=sha256):
            recovery.verify_historical_r7_creator_normalization_incident(
                api,
                ROOT,
            )

    def test_exact_r7_run_job_artifact_and_log_are_read_only(self) -> None:
        incident = recovery.R7_CREATOR_NORMALIZATION_INCIDENT
        log = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            api = FakeR4IncidentAPI(log, artifact, incident)
            self.verify(api, digest_for=log)
        self.assertEqual(
            [method for method, _path in api.calls],
            ["GET", "GET", "GET", "GET_BYTES", "GET_BYTES"],
        )

    def test_r7_controller_parent_tree_c2_and_e1_evidence_pins_are_real(
        self,
    ) -> None:
        recovery._verify_r7_local_object_chain(ROOT)
        recovery._verify_r8_null_affiliation_evidence(ROOT)

    def test_r7_log_and_artifact_tampering_block(self) -> None:
        incident = recovery.R7_CREATOR_NORMALIZATION_INCIDENT
        raw = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        marker = next(iter(recovery.R7_CREATOR_LOG_REQUIRED_COUNTS))
        changed_log = raw.replace(
            marker.encode("utf-8"),
            ("_" * len(marker)).encode("utf-8"),
            1,
        )
        with mock.patch.dict(incident, overrides):
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(
                    FakeR4IncidentAPI(changed_log, artifact, incident),
                    digest_for=changed_log,
                )
            api = FakeR4IncidentAPI(raw, artifact, incident)
            api.artifacts["artifacts"][0]["digest"] = "sha256:" + "0" * 64
            with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                self.verify(api, digest_for=raw)

    def test_r7_public_and_post_metadata_effect_markers_are_forbidden(
        self,
    ) -> None:
        incident = recovery.R7_CREATOR_NORMALIZATION_INCIDENT
        raw = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            for marker in recovery.R7_CREATOR_LOG_FORBIDDEN_MARKERS:
                with self.subTest(marker=marker):
                    encoded = marker.encode("utf-8")
                    changed = raw[: -len(encoded)] + encoded
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(
                            FakeR4IncidentAPI(changed, artifact, incident),
                            digest_for=changed,
                        )


class VRTCoreH3E1R8DescriptionNormalizationIncidentTests(unittest.TestCase):
    @staticmethod
    def evidence() -> bytes:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        return subprocess.check_output(
            [
                "git",
                "show",
                str(incident["c2"])
                + ":"
                + recovery.EVIDENCE_RELATIVE.as_posix(),
            ],
            cwd=ROOT,
        )

    @classmethod
    def artifact_fixture(cls) -> tuple[bytes, dict[str, Any]]:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        buffer = recovery.io.BytesIO()
        with recovery.zipfile.ZipFile(
            buffer,
            mode="w",
            compression=recovery.zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            entry = recovery.zipfile.ZipInfo(
                str(incident["artifact_entry"]),
                (2026, 8, 2, 23, 59, 58),
            )
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            entry.compress_type = recovery.zipfile.ZIP_DEFLATED
            archive.writestr(entry, cls.evidence(), compresslevel=6)
        raw = buffer.getvalue()
        with recovery.zipfile.ZipFile(
            recovery.io.BytesIO(raw), mode="r"
        ) as archive:
            parsed = archive.infolist()[0]
        return raw, {
            "artifact_size": len(raw),
            "artifact_digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "artifact_entry_compressed_bytes": parsed.compress_size,
            "artifact_entry_crc32": parsed.CRC,
            "artifact_entry_unix_mode": parsed.external_attr >> 16,
        }

    @staticmethod
    def log_bytes() -> bytes:
        lines: list[str] = []
        for marker, count in recovery.R8_DESCRIPTION_LOG_REQUIRED_COUNTS.items():
            lines.extend(marker for _index in range(count))
        prefix = b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8")
        size = int(recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT["log_bytes"])
        if len(prefix) > size:
            raise AssertionError("R8 incident fixture exceeds exact size")
        return prefix + b"x" * (size - len(prefix))

    @staticmethod
    def verify(api: FakeR4IncidentAPI, *, digest_for: bytes) -> None:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        real_sha256 = recovery.hashlib.sha256

        class FixedDigest:
            def hexdigest(self) -> str:
                return str(incident["log_sha256"])

        def sha256(raw: bytes = b"") -> Any:
            if raw == digest_for:
                return FixedDigest()
            return real_sha256(raw)

        with mock.patch.object(recovery.hashlib, "sha256", side_effect=sha256):
            recovery.verify_historical_r8_description_normalization_incident(
                api,
                ROOT,
            )

    def test_exact_r8_run_job_artifact_and_log_are_read_only(self) -> None:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        log = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            api = FakeR4IncidentAPI(log, artifact, incident)
            self.verify(api, digest_for=log)
        self.assertEqual(
            [method for method, _path in api.calls],
            [
                "GET",
                "GET",
                "GET",
                "GET",
                "GET_BYTES",
                "GET_BYTES",
                "GET",
            ],
        )

    def test_r8_controller_tree_and_unchanged_c2_pins_are_real(self) -> None:
        recovery._verify_r8_local_object_chain(ROOT)
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        canonical = recovery.R7_CREATOR_NORMALIZATION_INCIDENT
        for key in (
            "c2",
            "c2_parent",
            "c2_tree",
            "c2_evidence_blob",
            "c2_evidence_bytes",
            "c2_evidence_sha256",
            "phase",
            "state",
            "record_id",
            "doi",
        ):
            self.assertEqual(incident[key], canonical[key], msg=key)
        with mock.patch.dict(incident, {"c2_parent": "0" * 40}):
            with self.assertRaisesRegex(SystemExit, "unchanged C2"):
                recovery._verify_r8_local_object_chain(ROOT)

    def test_r8_run_attempt_log_and_artifact_tampering_block(self) -> None:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        raw = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        marker = next(iter(recovery.R8_DESCRIPTION_LOG_REQUIRED_COUNTS))
        changed_log = raw.replace(
            marker.encode("utf-8"),
            ("_" * len(marker)).encode("utf-8"),
            1,
        )
        with mock.patch.dict(incident, overrides):
            rerun = FakeR4IncidentAPI(raw, artifact, incident)
            rerun.run["run_attempt"] = 2
            digest = FakeR4IncidentAPI(raw, artifact, incident)
            digest.artifacts["artifacts"][0]["digest"] = "sha256:" + "0" * 64
            for label, api, log in (
                ("attempt", rerun, raw),
                ("log", FakeR4IncidentAPI(changed_log, artifact, incident), changed_log),
                ("artifact", digest, raw),
            ):
                with self.subTest(label=label):
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(api, digest_for=log)
                    self.assertTrue(
                        all(
                            method in {"GET", "GET_BYTES"}
                            for method, _path in api.calls
                        )
                    )

    def test_r8_public_and_post_metadata_effect_markers_are_forbidden(
        self,
    ) -> None:
        incident = recovery.R8_DESCRIPTION_NORMALIZATION_INCIDENT
        raw = self.log_bytes()
        artifact, overrides = self.artifact_fixture()
        with mock.patch.dict(incident, overrides):
            for marker in recovery.R8_DESCRIPTION_LOG_FORBIDDEN_MARKERS:
                with self.subTest(marker=marker):
                    encoded = marker.encode("utf-8")
                    changed = raw[: -len(encoded)] + encoded
                    with self.assertRaisesRegex(SystemExit, "BLOCK:"):
                        self.verify(
                            FakeR4IncidentAPI(changed, artifact, incident),
                            digest_for=changed,
                        )


if __name__ == "__main__":
    unittest.main()
