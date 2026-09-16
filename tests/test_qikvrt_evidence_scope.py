# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression fixtures are test inputs, never live repository evidence."""
from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_evidence_scope as scope
from tools import qikvrt_autonomous_self_heal as heal

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = "bbec1a5e0309c53f36adea0029b3bd0a36da46af"
TREE = "33130ddc233415f8d7f67f666ed077705318a4e7"
PREDECESSOR = "2153d8b9cddbc83d9bc30b7ddab3b5a0f9af1968"
MERGE = "86a550060b9a25d83e4e10c22cd9e526d02ae090"
REPO = "Goldkelch/qik-vrt"


class EvidenceScopeTests(unittest.TestCase):
    def receipt(self):
        return {
            "schema": "qikvrt_cloud_transputer_integrity_objects_v1",
            "state": "NOOP", "source_head": HEAD, "source_tree": TREE,
            "ref_mutation": False, "candidate_validation_transferred": False,
            "general_effect_ack_done": False,
        }

    def observation(self):
        return {
            "repository": REPO, "actual_checkout_head": HEAD,
            "actual_checkout_tree": TREE, "job_executed": True,
            "validation_passed": True, "worktree_clean": True,
            "candidate_validation_transferred": False,
        }

    def admissible(self, observation):
        return scope.exact_validation_admissible(
            observation, expected_repository=REPO, expected_head=HEAD,
            expected_tree=TREE,
        )

    def test_pr1108_idempotent_receipt_is_local_not_global_done(self):
        receipt = self.receipt()
        original = copy.deepcopy(receipt)
        result = scope.bind_local_result(receipt, source_head=HEAD, source_tree=TREE)
        self.assertEqual(receipt, original)
        self.assertEqual(result["state"], "NOOP")
        self.assertEqual(result["state_scope"], "LOCAL_OPERATION")
        self.assertEqual(result["repository_completion"], "NOT_EVALUATED")
        self.assertFalse(result["ref_mutation"])
        self.assertTrue(all(value is False for value in result["completion_claims"].values()))
        self.assertFalse(self.admissible(receipt))

    def test_repeated_local_binding_is_idempotent(self):
        result = scope.bind_local_result(self.receipt(), source_head=HEAD, source_tree=TREE)
        self.assertEqual(result, scope.bind_local_result(result, source_head=HEAD, source_tree=TREE))

    def test_positive_exact_checkout_readback_is_admissible_only_for_its_subject(self):
        self.assertTrue(self.admissible(self.observation()))
        for field, value in (("repository", "ingolf-lohmann/qik-vrt"),
                             ("actual_checkout_head", PREDECESSOR),
                             ("actual_checkout_tree", "0" * 40)):
            with self.subTest(field=field):
                observation = self.observation()
                observation[field] = value
                self.assertFalse(self.admissible(observation))

    def test_green_merge_with_same_tree_and_event_head_is_not_literal_head(self):
        observation = self.observation()
        observation.update(actual_checkout_head=MERGE, head_sha=HEAD, conclusion="success")
        self.assertFalse(self.admissible(observation))

    def test_dirty_materialization_and_zero_job_success_cannot_validate_candidate(self):
        for key in ("worktree_clean", "job_executed", "validation_passed"):
            with self.subTest(key=key):
                observation = self.observation()
                observation.update({key: False, "conclusion": "success"})
                self.assertFalse(self.admissible(observation))

    def test_missing_fields_fail_closed(self):
        for key in self.observation():
            with self.subTest(key=key):
                observation = self.observation()
                del observation[key]
                self.assertFalse(self.admissible(observation))

    def test_non_boolean_readback_is_not_boolean_evidence(self):
        for key in ("job_executed", "validation_passed", "worktree_clean",
                    "candidate_validation_transferred"):
            for value in (0, 1, "true", "false", None):
                with self.subTest(key=key, value=value):
                    observation = self.observation()
                    observation[key] = value
                    self.assertFalse(self.admissible(observation))
        observation = self.observation()
        observation["candidate_validation_transferred"] = True
        self.assertFalse(self.admissible(observation))

    def test_local_guard_rejects_inflation_instead_of_silently_rewriting_it(self):
        for claim in scope.GLOBAL_CLAIMS:
            for value in (True, 1, 0, "false", None):
                for nested in (False, True):
                    with self.subTest(claim=claim, value=value, nested=nested):
                        result = {"completion_claims": {claim: value}} if nested else {claim: value}
                        with self.assertRaises(ValueError):
                            scope.bind_local_result(result, source_head=HEAD, source_tree=TREE)
        for key in ("candidate_validation_transferred", "general_effect_ack_done"):
            with self.assertRaises(ValueError):
                scope.bind_local_result({key: True}, source_head=HEAD, source_tree=TREE)

    def test_terminal_global_labels_and_conflicting_scopes_are_rejected(self):
        cases = [{"state": label} for label in
                 ("DONE", "FINAL_PASS", "EFFECT_ACK_DONE", "REPOSITORY_NOOP")]
        cases += [{"state_scope": "GLOBAL"}, {"repository_completion": "DONE"},
                  {"subject_binding": "VALIDATED"}, {"completion_claims": None}]
        for result in cases:
            with self.subTest(result=result):
                with self.assertRaises(ValueError):
                    scope.bind_local_result(result, source_head=HEAD, source_tree=TREE)

    def test_noop_repair_handler_remains_locally_scoped(self):
        result = heal.CommandResult(("probe",), 0, "", "")
        with mock.patch.object(heal, "run", return_value=result) as run:
            observed = heal.repair_handler({"probe": ["probe"], "failure_class": "TEST"})
        self.assertEqual(observed["state"], "NOOP")
        self.assertEqual(observed["state_scope"], "LOCAL_REPAIR_HANDLER")
        self.assertEqual(run.call_count, 1)

    def test_source_rebinding_and_invalid_identifiers_fail_closed(self):
        with self.assertRaises(ValueError):
            scope.bind_local_result(self.receipt(), source_head=PREDECESSOR, source_tree=TREE)
        for value in (None, "", "0" * 40, "g" * 40, "a" * 39, "a" * 41):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    scope.bind_local_result({}, source_head=value, source_tree=TREE)
                self.assertFalse(scope.exact_validation_admissible(
                    self.observation(), expected_repository=REPO,
                    expected_head=value, expected_tree=TREE))
        self.assertFalse(self.admissible(None))

    def test_self_heal_check_uses_guard_without_claiming_probe_or_repository_completion(self):
        contract = {"allowlisted_handlers": []}
        result = heal.CommandResult((), 0, "", "")
        with mock.patch.object(heal, "load_contract", return_value=contract), \
             mock.patch.object(heal, "run", return_value=result), \
             mock.patch.object(heal, "observed_source_subject", return_value=(HEAD, TREE)), \
             mock.patch.object(heal, "changed_paths", return_value=[]), \
             mock.patch.object(heal, "repair_handler") as repair:
            observed = heal.execute(False)
        repair.assert_not_called()
        self.assertEqual(observed["state"], "NOOP")
        self.assertEqual(observed["actions"], [])
        self.assertEqual(observed["subject_binding"], "SOURCE_ONLY_NOT_VALIDATION")
        self.assertEqual(observed["source_head"], HEAD)
        self.assertEqual(observed["source_tree"], TREE)
        self.assertFalse(observed["completion_claims"]["P2_PASS"])
        self.assertFalse(observed["completion_claims"]["EFFECT_ACK_DONE"])

    def test_scoped_regressions_are_admitted_to_existing_gate(self):
        entry = (ROOT / "tests/test_progress_deadlocks.py").read_text(encoding="utf-8")
        self.assertIn("from tests.test_qikvrt_evidence_scope import EvidenceScopeTests", entry)

    def test_self_heal_source_drift_blocks_even_with_no_file_delta(self):
        result = heal.CommandResult((), 0, "", "")
        with mock.patch.object(heal, "load_contract", return_value={"allowlisted_handlers": []}), \
             mock.patch.object(heal, "run", return_value=result), \
             mock.patch.object(heal, "changed_paths", return_value=[]), \
             mock.patch.object(heal, "observed_source_subject", side_effect=[(HEAD, TREE), (MERGE, TREE)]):
            with self.assertRaises(heal.SelfHealBlock):
                heal.execute(False)

    def test_real_git_subject_readback_binds_actual_commit_and_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            def git(*args):
                return subprocess.run(["git", "-C", str(root), *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            git("init", "-q")
            (root / "file").write_text("fixture\n", encoding="utf-8")
            git("add", "file")
            git("-c", "user.name=Scope test", "-c", "user.email=scope@example.invalid",
                "commit", "-qm", "fixture")
            expected = (git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}"))
            with mock.patch.object(heal, "ROOT", root):
                self.assertEqual(heal.observed_source_subject(), expected)

    def test_policy_and_entrypoint_enforce_the_same_repository_wide_boundary(self):
        policy = json.loads((ROOT / scope.POLICY_PATH).read_text(encoding="utf-8"))
        local = policy["local_completion"]
        self.assertEqual(local["idempotent_wire_state"], "NOOP")
        self.assertEqual(local["state_scope"], "LOCAL_OPERATION")
        self.assertEqual(local["empty_repeat_commit"], "FORBIDDEN")
        self.assertEqual(policy["repository_noop"]["missing_or_incomplete_observation"], "HOLD_UNVERIFIED")
        self.assertFalse(policy["evidence_binding"]["candidate_validation_transferred"])
        self.assertFalse(policy["evidence_binding"]["synthetic_merge_counts_as_literal_head"])
        self.assertFalse(policy["evidence_binding"]["source_binding_is_validation"])
        entrypoint = (ROOT / "AI").read_text(encoding="utf-8")
        self.assertIn(scope.POLICY_PATH, entrypoint)
        self.assertIn("LOCAL_NOOP != REPOSITORY_NOOP != EFFECT_ACK_DONE", entrypoint)
        self.assertNotIn("must produce a repository NOOP when the semantic fingerprint is unchanged", entrypoint)


if __name__ == "__main__":
    unittest.main()
