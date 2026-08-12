#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qikvrt_effect_ack import EffectState  # noqa: E402


POLICY_PATH = ROOT / "policy" / "PROTOCOL_EVOLUTION_AND_EXTENSION_V1.json"
DELEGATION_PATH = (
    ROOT
    / "state"
    / "authorization"
    / "delegations"
    / "OWNER_PROTOCOL_EVOLUTION_AND_EXTENSION_V1.json"
)
SCHEMA_PATH = ROOT / "schemas" / "qikvrt_protocol_change_envelope_v1.schema.json"
SUMMARY_PATH = ROOT / "external" / "ietf" / "EFFECT_ACK_PROTOCOL_SUMMARY.json"
WORK_UNIT_PATH = ROOT / "state" / "work_units" / "PROTOCOL_EVOLUTION_AND_EXTENSION_V1.json"
DOC_PATH = ROOT / "docs" / "PROTOCOL_EVOLUTION_AND_EXTENSION.md"


class ProtocolEvolutionAndExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.delegation = json.loads(DELEGATION_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        cls.work_unit = json.loads(WORK_UNIT_PATH.read_text(encoding="utf-8"))
        cls.docs = DOC_PATH.read_text(encoding="utf-8")

    def test_effect_ack_core_state_set_is_preserved(self) -> None:
        expected = [state.value for state in EffectState]
        self.assertEqual(
            expected,
            [
                "EFFECT_NACK",
                "EFFECT_ACK_CONTINUE",
                "EFFECT_ACK_DONE",
                "EFFECT_ACK_ISOLATE",
                "EFFECT_ACK_BLOCK",
            ],
        )
        self.assertEqual(self.policy["current_effect_ack_core"]["states"], expected)
        self.assertEqual(self.summary["states"], expected)
        self.assertFalse(
            self.policy["current_effect_ack_core"]["state_set_mutated_by_this_policy"]
        )
        self.assertTrue(
            self.summary["protocol_evolution"]["core_state_set_preserved_by_default"]
        )

    def test_done_can_only_be_strengthened(self) -> None:
        extension = self.policy["effect_ack_extension_model"]
        self.assertIn("may not make EFFECT_ACK_DONE easier", extension["done_rule"])
        self.assertEqual(
            extension["unknown_critical_extension_behavior"], "EFFECT_ACK_BLOCK"
        )
        self.assertTrue(
            self.summary["protocol_evolution"]
            ["extensions_may_only_strengthen_done_predicates"]
        )

    def test_change_classes_are_closed_and_schema_bound(self) -> None:
        policy_classes = set(self.policy["protocol_change_classes"])
        schema_classes = set(self.schema["properties"]["change_class"]["enum"])
        self.assertEqual(policy_classes, schema_classes)
        self.assertEqual(
            self.schema["properties"]["schema"]["const"],
            "qikvrt_protocol_change_envelope_v1",
        )
        self.assertFalse(self.schema["additionalProperties"])

    def test_normative_delta_conditionals_fail_closed(self) -> None:
        conditionals = self.schema["allOf"]
        no_change = next(
            item
            for item in conditionals
            if item["if"]["properties"]["change_class"].get("const")
            == "NO_PROTOCOL_CHANGE_REQUIRED"
        )
        self.assertFalse(
            no_change["then"]["properties"]["normative_delta"]["properties"]
            ["established"]["const"]
        )
        self.assertEqual(
            no_change["then"]["properties"]["external_disposition"]["properties"]
            ["ietf"]["const"],
            "NO_PROTOCOL_CHANGE_REQUIRED",
        )
        normative = next(
            item
            for item in conditionals
            if "enum" in item["if"]["properties"]["change_class"]
        )
        self.assertTrue(
            normative["then"]["properties"]["normative_delta"]["properties"]
            ["established"]["const"]
        )

    def test_unknown_critical_extension_and_effect_boundary_are_closed(self) -> None:
        compatibility = self.schema["properties"]["versioning_and_compatibility"]
        self.assertEqual(
            compatibility["properties"]["unknown_critical_extension_behavior"]
            ["const"],
            "FAIL_CLOSED",
        )
        effect = self.schema["properties"]["effect_boundary"]["properties"]
        self.assertTrue(effect["repository_internal_only"]["const"])
        self.assertFalse(effect["external_effect_authorized"]["const"])
        self.assertFalse(effect["credential_use_authorized"]["const"])
        self.assertFalse(effect["promotion_authorized"]["const"])

    def test_owner_delegation_does_not_authorize_external_effects(self) -> None:
        self.assertEqual(
            self.delegation["authorization_scope"]["state"], "ACTIVE"
        )
        denied = set(self.delegation["not_authorized"])
        self.assertIn("ietf_datatracker_submission_or_update", denied)
        self.assertIn("iana_or_other_registry_request", denied)
        self.assertIn("zenodo_publication_or_doi_effect", denied)
        self.assertIn("release_deployment_or_external_activation", denied)
        boundary = self.policy["external_effect_boundary"]
        self.assertFalse(boundary["ietf_submission_or_update_authorized"])
        self.assertFalse(boundary["iana_or_other_registry_request_authorized"])
        self.assertFalse(boundary["zenodo_publication_authorized"])
        self.assertFalse(boundary["credentialed_external_write_authorized"])

    def test_work_unit_preserves_stack_and_nonclaims(self) -> None:
        self.assertEqual(self.work_unit["stacked_base"]["pull_request"], 568)
        self.assertEqual(
            self.work_unit["single_writer"]["relationship_to_pr568"],
            "EXPLICIT_STACK",
        )
        self.assertFalse(
            self.work_unit["single_writer"]["competing_same_scope_writer_observed"]
        )
        self.assertFalse(self.work_unit["effect_boundary"]["external_effect"])
        self.assertFalse(self.work_unit["effect_boundary"]["ietf_submission"])
        self.assertFalse(self.work_unit["completion_claims"]["PASS"])
        self.assertFalse(self.work_unit["completion_claims"]["FINAL_PASS"])
        self.assertFalse(self.work_unit["completion_claims"]["EFFECT_ACK_DONE"])

    def test_human_contract_binds_machine_authorities(self) -> None:
        for relative in (
            "state/authorization/delegations/OWNER_PROTOCOL_EVOLUTION_AND_EXTENSION_V1.json",
            "policy/PROTOCOL_EVOLUTION_AND_EXTENSION_V1.json",
            "schemas/qikvrt_protocol_change_envelope_v1.schema.json",
        ):
            self.assertIn(relative, self.docs)
        self.assertIn("NO_PROTOCOL_CHANGE_REQUIRED", self.docs)
        self.assertIn("Unknown critical extensions fail closed", self.docs)


if __name__ == "__main__":
    unittest.main()
