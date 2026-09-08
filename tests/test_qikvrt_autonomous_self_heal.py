# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_autonomous_self_heal",
    ROOT / "tools/qikvrt_autonomous_self_heal.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AutonomousSelfHealTests(unittest.TestCase):
    def test_expected_head_bound_promotion_is_exact_and_fail_closed(self) -> None:
        contract = MODULE.load_contract()
        delegation = MODULE.load_delegation()
        expected = list(MODULE.PROMOTION_CONDITIONS)
        self.assertEqual(
            contract["execution_model"]["promotion"],
            "expected_head_bound_only",
        )
        self.assertEqual(
            contract["promotion_policy"]["unconditional_automatic_merge"],
            "FORBIDDEN",
        )
        self.assertEqual(
            contract["promotion_policy"]["expected_head_bound_promotion"],
            "ALLOWED_ONLY_IF",
        )
        self.assertEqual(contract["promotion_policy"]["conditions"], expected)
        self.assertFalse(
            contract["promotion_policy"]["proposal_workflow_may_merge"]
        )
        self.assertFalse(
            contract["promotion_policy"]["general_auto_merge_authorization"]
        )
        self.assertTrue(
            delegation["promotion_policy"]["standing_delegation"]
        )
        self.assertEqual(
            delegation["promotion_policy"]["conditions"],
            expected,
        )
        forbidden = set(contract["forbidden_effects"])
        self.assertIn("unconditional_automatic_merge", forbidden)
        self.assertIn("unbound_or_stale_head_promotion", forbidden)
        self.assertIn("zenodo_mutation", forbidden)
        self.assertIn("ietf_mutation", forbidden)
        self.assertIn("deployment", forbidden)

    def test_allowlist_is_exactly_handler_owned(self) -> None:
        contract = MODULE.load_contract()
        allowed = MODULE.allowed_paths(contract)
        self.assertIn("anticipation/next-effect.json", allowed)
        self.assertIn("docs/publications/index.json", allowed)
        self.assertIn("docs/publications/index.html", allowed)
        self.assertIn("REPOSITORY_FILE_MANIFEST.json", allowed)
        self.assertNotIn("AI_STATUS.md", allowed)
        self.assertNotIn(
            ".github/workflows/qikvrt_autonomous_self_heal.yml",
            allowed,
        )

    def test_publication_overview_precedes_integrity(self) -> None:
        handlers = MODULE.load_contract()["allowlisted_handlers"]
        order = [handler["failure_class"] for handler in handlers]
        self.assertLess(
            order.index("PUBLICATION_OVERVIEW_DRIFT"),
            order.index("REPOSITORY_NATIVE_INTEGRITY_STALE"),
        )
        publication = next(
            handler
            for handler in handlers
            if handler["failure_class"] == "PUBLICATION_OVERVIEW_DRIFT"
        )
        self.assertEqual(
            publication["failure_signature"],
            "publication overview drift:",
        )

    def test_pr_continuation_is_explicitly_opt_in_and_external_gate_bounded(self) -> None:
        continuation = MODULE.load_contract()["pull_request_continuation"]
        self.assertEqual(
            continuation["opt_in_marker"],
            "<!-- qikvrt-autonomous-self-heal:enabled -->",
        )
        self.assertTrue(continuation["same_repository_only"])
        self.assertTrue(continuation["draft_only"])
        self.assertEqual(continuation["maximum_pull_requests_per_run"], 1)
        self.assertIn(
            "IDENTIFIED_HUMAN_PHYSICS_REVIEW_WHEN_REQUIRED",
            continuation["external_gates"],
        )
        self.assertIn(
            "SEPARATE_EXPLICIT_ZENODO_AUTHORIZATION",
            continuation["external_gates"],
        )

    def test_semantic_fingerprint_is_path_and_byte_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "a").write_bytes(b"one")
            (root / "b").write_bytes(b"two")
            with mock.patch.object(MODULE, "ROOT", root):
                first = MODULE.semantic_fingerprint(["a", "b"])
                second = MODULE.semantic_fingerprint(["b", "a"])
                self.assertEqual(first, second)
                (root / "b").write_bytes(b"three")
                self.assertNotEqual(
                    first,
                    MODULE.semantic_fingerprint(["a", "b"]),
                )

    def test_candidate_identity_binds_base_and_fingerprint(self) -> None:
        fingerprint = "1" * 64
        first = MODULE.candidate_identity("a" * 40, fingerprint)
        self.assertEqual(
            first,
            MODULE.candidate_identity("a" * 40, fingerprint),
        )
        self.assertNotEqual(
            first,
            MODULE.candidate_identity("b" * 40, fingerprint),
        )

    def test_non_projection_anticipation_failure_blocks(self) -> None:
        handler = {
            "failure_class": "ANTICIPATION_PROJECTION_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "projection drift:",
        }
        result = MODULE.CommandResult(
            ("probe",),
            2,
            "BLOCK",
            "source binding drift",
        )
        with mock.patch.object(MODULE, "run", return_value=result):
            with self.assertRaises(MODULE.SelfHealBlock):
                MODULE.repair_handler(handler)

    def test_generic_failure_signature_blocks_unrecognized_failure(self) -> None:
        handler = {
            "failure_class": "PUBLICATION_OVERVIEW_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "publication overview drift:",
        }
        result = MODULE.CommandResult(("probe",), 2, "", "different failure")
        with mock.patch.object(MODULE, "run", return_value=result):
            with self.assertRaises(MODULE.SelfHealBlock):
                MODULE.repair_handler(handler)

    def test_recognized_failure_runs_exact_repair(self) -> None:
        handler = {
            "failure_class": "PUBLICATION_OVERVIEW_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "publication overview drift:",
        }
        results = [
            MODULE.CommandResult(
                ("probe",), 2, "publication overview drift: missing", ""
            ),
            MODULE.CommandResult(("repair",), 0, "MATERIALIZED", ""),
            MODULE.CommandResult(("probe",), 0, "VERIFIED", ""),
        ]
        with mock.patch.object(MODULE, "run", side_effect=results) as mocked:
            value = MODULE.repair_handler(handler)
        self.assertEqual(value["state"], "SYMPTOM_CORRECTED_CAUSE_OPEN")
        self.assertFalse(value["repair_complete"])
        self.assertEqual(mocked.call_count, 3)


class RecursiveRepairRuntimeTests(unittest.TestCase):
    def handler(self):
        return {"failure_class": "EXACT_TEST_FAILURE", "probe": ["probe"], "repair": ["repair"]}

    def result(self, command, code):
        return MODULE.CommandResult((command,), code, "result", "")

    def test_exit_zero_without_effect_is_not_repaired(self):
        results = [self.result("probe", 1), self.result("repair", 0), self.result("probe", 1)]
        with mock.patch.object(MODULE, "run", side_effect=results) as run:
            value = MODULE.repair_handler(self.handler())
        self.assertEqual(value["state"], "HOLD_REPAIR_INCOMPLETE")
        self.assertEqual(run.call_count, 3)
        self.assertFalse(value["repair_complete"])

    def test_failed_command_partial_effect_is_reobserved_without_retry(self):
        results = [self.result("probe", 1), self.result("repair", 1), self.result("probe", 0)]
        with mock.patch.object(MODULE, "run", side_effect=results) as run:
            value = MODULE.repair_handler(self.handler())
        self.assertTrue(value["symptom_reobserved_corrected"])
        self.assertFalse(value["repair_command_succeeded"])
        self.assertEqual(value["state"], "HOLD_REPAIR_INCOMPLETE")
        self.assertEqual(run.call_args_list, [mock.call(("probe",)), mock.call(("repair",)), mock.call(("probe",))])

    def test_timeout_still_requires_effect_readback(self):
        results = [self.result("probe", 1), MODULE.subprocess.TimeoutExpired(["repair"], 1), self.result("probe", 0)]
        with mock.patch.object(MODULE, "run", side_effect=results) as run:
            value = MODULE.repair_handler(self.handler())
        self.assertEqual(value["repair_error"], "TimeoutExpired")
        self.assertEqual(run.call_count, 3)
        self.assertFalse(value["repair_complete"])

    def test_unavailable_readback_is_unknown_not_success(self):
        results = [self.result("probe", 1), self.result("repair", 0), OSError("readback unavailable")]
        with mock.patch.object(MODULE, "run", side_effect=results):
            value = MODULE.repair_handler(self.handler())
        self.assertFalse(value["symptom_reobserved_corrected"])
        self.assertIsNone(value["evidence"]["after"])
        self.assertEqual(value["reobservation_error"], "OSError")

    def test_green_reprobe_retains_cause_and_original_flow_obligations(self):
        results = [self.result("probe", 1), self.result("repair", 0), self.result("probe", 0)]
        with mock.patch.object(MODULE, "run", side_effect=results):
            value = MODULE.repair_handler(self.handler())
        self.assertEqual(value["cause_state"], "UNVERIFIED")
        self.assertEqual(value["original_flow_state"], "UNVERIFIED")
        self.assertTrue(value["exact_committed_subject_readback_required"])
        self.assertEqual(value["next_action"], "IDENTIFY_AND_CORRECT_CAUSE")

    def test_clean_probe_does_not_execute_repair(self):
        with mock.patch.object(MODULE, "run", return_value=self.result("probe", 0)) as run:
            value = MODULE.repair_handler(self.handler())
        self.assertEqual(value["state"], "NOOP")
        self.assertEqual(run.call_count, 1)

    def test_obligation_identity_is_stable_not_timestamp_based(self):
        results = [self.result("probe", 1), self.result("repair", 0), self.result("probe", 0)]
        with mock.patch.object(MODULE, "run", side_effect=results * 2):
            first = MODULE.repair_handler(self.handler())
            second = MODULE.repair_handler(self.handler())
        self.assertEqual(first["work_unit_id"], second["work_unit_id"])
        self.assertEqual(len(first["evidence"]["before"]["stdout_sha256"]), 64)

    def test_existing_executor_invokes_reducer_and_preserves_unknown_backlog(self):
        contract = {"allowlisted_handlers": [{**self.handler(), "mutable_paths": ["a"]}]}
        with mock.patch.object(MODULE, "load_contract", return_value=contract), mock.patch.object(MODULE, "run", return_value=MODULE.CommandResult((), 0, "", "")), mock.patch.object(MODULE, "observed_base_revision", return_value="a" * 40), mock.patch.object(MODULE, "changed_paths", return_value=[]), mock.patch.object(MODULE, "recursive_debugging_plan", wraps=MODULE.recursive_debugging_plan) as reducer:
            value = MODULE.execute(True)
        reducer.assert_called_once_with(None)
        self.assertEqual(value["state"], "NOOP")
        self.assertFalse(value["recursive_debugging"]["complete"])
        self.assertEqual(value["recursive_debugging"]["prior_obligations"], "UNKNOWN_NOT_CLEARED")

    def test_basis_policy_absence_blocks_registered_controller(self):
        with mock.patch.object(MODULE, "_load_json", return_value={}):
            with self.assertRaisesRegex(MODULE.SelfHealBlock, "base algorithm"):
                MODULE.load_contract()


if __name__ == "__main__":
    unittest.main()
