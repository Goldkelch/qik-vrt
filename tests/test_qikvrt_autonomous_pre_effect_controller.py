# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_autonomous_pre_effect_controller",
    ROOT / "tools/qikvrt_autonomous_pre_effect_controller.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AutonomousPreEffectControllerTests(unittest.TestCase):
    @staticmethod
    def command_result(command: tuple[str, ...], stdout: str = "", returncode: int = 0):
        return MODULE.self_heal.CommandResult(command, returncode, stdout, "")

    def test_policy_is_active_and_fail_closed(self) -> None:
        policy = MODULE.load_policy()
        self.assertEqual(policy["mission"], "AUTONOMOUS_UNTIL_FIRST_IRREVERSIBLE_EXTERNAL_EFFECT")
        self.assertEqual(policy["preconditions"], MODULE.EXPECTED_PRECONDITIONS)
        self.assertEqual(policy["fail_closed"]["state"], "HOLD")
        self.assertTrue(policy["fail_closed"]["repair_forbidden"])
        self.assertTrue(
            MODULE.REQUIRED_AUTONOMOUS_CAPABILITIES.issubset(
                set(policy["autonomous_capabilities"])
            )
        )
        self.assertIn(
            "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json",
            MODULE.REQUIRED_EVIDENCE_PATHS,
        )

    def test_all_preconditions_allow_repository_internal_execution(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        self.assertEqual(MODULE.classify(preconditions, None), "AUTONOMOUS_EXECUTION_ALLOWED")

    def test_missing_precondition_holds_instead_of_repairs(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        preconditions["NO_COMPETING_WRITER"] = False
        self.assertEqual(MODULE.classify(preconditions, None), "HOLD")

    def test_irreversible_effect_requires_exact_owner_authorization(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        for effect in MODULE.IRREVERSIBLE_EFFECTS:
            self.assertEqual(MODULE.classify(preconditions, effect), "REQUIRE_EXACT_PRODUCT_OWNER_AUTHORIZATION")

    def test_unknown_effect_fails_closed(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        with self.assertRaises(MODULE.PreEffectBlock):
            MODULE.classify(preconditions, "UNBOUND_EXTERNAL_EFFECT")

    def test_completion_and_epistemic_claims_remain_prohibited(self) -> None:
        policy = MODULE.load_policy()
        prohibited = set(policy["prohibited_autonomous_effects"])
        self.assertTrue(MODULE.PROHIBITED_CLAIMS.issubset(prohibited))
        self.assertFalse(policy["epistemic_boundaries"]["scientific_confirmation_inferable"])
        self.assertFalse(policy["epistemic_boundaries"]["physical_correspondence_inferable"])
        self.assertFalse(policy["epistemic_boundaries"]["independent_review_fabricable"])
        self.assertFalse(policy["epistemic_boundaries"]["measurement_fabricable"])

    def test_normative_policy_selects_declared_authority_remote(self) -> None:
        contract = MODULE._canonical_upstream_contract()
        self.assertEqual(contract["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(contract["remote_name"], "authority")
        self.assertEqual(
            contract["remote_url"],
            "https://github.com/Goldkelch/qik-vrt.git",
        )
        self.assertEqual(contract["default_branch"], "main")

    def test_materialized_authority_remote_is_used_without_origin_fallback(self) -> None:
        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote"):
                return self.command_result(command, "origin\nauthority\n")
            if command == ("git", "remote", "get-url", "authority"):
                return self.command_result(
                    command, "https://github.com/Goldkelch/qik-vrt.git\n"
                )
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            self.assertEqual(MODULE._canonical_source_remote(), "authority")

    def test_missing_declared_authority_remote_fails_closed(self) -> None:
        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote"):
                return self.command_result(command, "origin\nupstream\n")
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            with self.assertRaisesRegex(
                MODULE.PreEffectBlock, "canonical source remote is absent"
            ):
                MODULE._canonical_source_remote()

    def test_mismatched_authority_url_fails_closed(self) -> None:
        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote"):
                return self.command_result(command, "origin\nauthority\n")
            if command == ("git", "remote", "get-url", "authority"):
                return self.command_result(
                    command, "https://github.com/example/not-qik-vrt.git\n"
                )
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            with self.assertRaisesRegex(
                MODULE.PreEffectBlock, "canonical source remote URL mismatch"
            ):
                MODULE._canonical_source_remote()

    def test_remote_main_revision_queries_policy_declared_remote_and_branch(self) -> None:
        expected = "836a068d42b30f4df496caf4d712dbe8da45c043"

        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote"):
                return self.command_result(command, "origin\nauthority\n")
            if command == ("git", "remote", "get-url", "authority"):
                return self.command_result(
                    command, "https://github.com/Goldkelch/qik-vrt.git\n"
                )
            if command == (
                "git", "ls-remote", "--heads", "authority", "refs/heads/main"
            ):
                return self.command_result(command, f"{expected}\trefs/heads/main\n")
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            self.assertEqual(MODULE._remote_main_revision(), expected)


if __name__ == "__main__":
    unittest.main()
