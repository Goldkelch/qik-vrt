# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/AUTOKOGNITIVE_AUTODIDACTIC_LOOP_V1.json"
AUTHORITY = ROOT / "policy/AUTHORITY_ESCALATION_V1.json"
MESH_EXPLANATION = ROOT / "policy/MESH_SELF_EXPLANATION_V1.json"
DISCLOSURE = ROOT / ".well-known/qik-vrt-self-disclosure.json"
README = ROOT / "README.md"
AI = ROOT / "AI"
HUMAN_CONTRACT = ROOT / "docs/MESH_SELF_EXPLANATION_AND_DELIVERY.md"


class AutokognitiveAutodidacticPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        cls.mesh_explanation = json.loads(MESH_EXPLANATION.read_text(encoding="utf-8"))
        cls.disclosure = json.loads(DISCLOSURE.read_text(encoding="utf-8"))
        cls.readme = README.read_text(encoding="utf-8")
        cls.ai = AI.read_text(encoding="utf-8")
        cls.human_contract = HUMAN_CONTRACT.read_text(encoding="utf-8")

    def test_identity_and_recursive_learning_are_explicit(self):
        self.assertEqual(
            self.policy["schema"], "qikvrt_autokognitive_autodidactic_loop_v1"
        )
        self.assertEqual(self.policy["repository"], "Goldkelch/qik-vrt")
        self.assertIn("autokognitive", self.policy["terminology"])
        self.assertIn("autodidactic", self.policy["terminology"])
        self.assertIs(self.policy["recursion"]["applies_to_its_own_rules"], True)
        self.assertIs(self.policy["recursion"]["universal_bug_freedom_claimed"], False)

    def test_loop_repairs_symptom_and_root_cause_before_learning(self):
        loop = self.policy["loop"]
        required = [
            "OBSERVE_EXACT_SUBJECT",
            "REPRODUCE_FAILURE_OR_BLOCKER",
            "CORRECT_IMMEDIATE_FAILURE",
            "IDENTIFY_CAUSAL_ROOT",
            "CORRECT_CAUSAL_ROOT",
            "GENERALIZE_LESSON",
            "ADD_NEGATIVE_REGRESSION",
            "REEXECUTE_ON_EXACT_SUCCESSOR",
            "READ_BACK_EFFECT",
            "LEARN_AND_REPEAT_UNTIL_NO_KNOWN_DETERMINISTIC_BLOCKERS",
        ]
        for item in required:
            self.assertIn(item, loop)
        self.assertLess(loop.index("CORRECT_IMMEDIATE_FAILURE"), loop.index("IDENTIFY_CAUSAL_ROOT"))
        self.assertLess(loop.index("CORRECT_CAUSAL_ROOT"), loop.index("GENERALIZE_LESSON"))
        self.assertLess(loop.index("GENERALIZE_LESSON"), loop.index("ADD_NEGATIVE_REGRESSION"))
        self.assertLess(loop.index("ADD_NEGATIVE_REGRESSION"), loop.index("READ_BACK_EFFECT"))

    def test_learning_record_requires_cause_counterexample_and_readback(self):
        fields = set(self.policy["mandatory_learning_record"]["required_fields"])
        self.assertTrue({
            "failure_signature",
            "first_causal_blocker",
            "root_cause",
            "root_cause_repair",
            "generalized_rule",
            "negative_regression",
            "scope_limit",
            "exact_successor_readback",
        } <= fields)
        self.assertIs(
            self.policy["mandatory_learning_record"]["no_claim_without_bound_evidence"],
            True,
        )

    def test_optimization_cannot_weaken_evidence_or_authority_boundaries(self):
        preserve = set(self.policy["optimization"]["must_preserve"])
        self.assertIn("QIKVRT_EXECUTION_PRECEDENCE_V1", preserve)
        self.assertIn("PREDECESSOR_EVIDENCE_TRANSFER=false", preserve)
        self.assertIn("TRANSPORT_ACK != EFFECT_ACK", preserve)
        self.assertIn("automation != native review", preserve)
        forbidden = "\n".join(self.policy["optimization"]["forbidden_optimizations"])
        self.assertIn("weaken a gate", forbidden)
        self.assertIn("invent or transfer evidence", forbidden)
        self.assertIn("self-grant review or authority", forbidden)
        self.assertIn("blindly retry", forbidden)

    def test_first_lesson_generalizes_the_observed_credential_defect(self):
        lesson = self.policy["initial_lessons"][0]
        self.assertEqual(lesson["id"], "PHANTOM_CREDENTIAL_ESCALATION_V1")
        self.assertEqual(lesson["source_policy"], "policy/AUTHORITY_ESCALATION_V1.json")
        self.assertEqual(
            self.authority["rules"]["classification"]["missing_optional_admin_secret"],
            "NOT_A_BLOCKER_UNTIL_A_PROVEN_PRIVILEGED_MUTATION_IS_REQUIRED",
        )
        self.assertIs(
            self.authority["rules"]["observation"]["must_not_depend_on_optional_admin_secret"],
            True,
        )
        self.assertIn("specific privileged mutation", lesson["generalized_rule"])
        self.assertIn("additional authority", lesson["scope_limit"])

    def test_zero_bug_semantics_remain_bounded(self):
        done = self.policy["done_semantics"]
        self.assertIn("ZERO_KNOWN_DETERMINISTIC_BUGS", done["local_zero_bug_claim"])
        excluded = set(done["not_equivalent_to"])
        self.assertIn("universal absence of unknown bugs", excluded)
        self.assertIn("native approval", excluded)
        self.assertIn("general EFFECT_ACK_DONE", excluded)

    def test_mesh_self_explanation_is_dual_cognition_and_single_truth(self):
        contract = self.mesh_explanation["dual_cognition_contract"]
        self.assertIs(contract["same_semantics_required"], True)
        self.assertIs(contract["single_canonical_truth_model"], True)
        self.assertEqual(contract["semantic_conflict_state"], "BLOCK")
        self.assertEqual(contract["semantic_drift_state"], "BLOCK")
        entrypoints = self.mesh_explanation["entrypoint_contract"]
        self.assertEqual(entrypoints["human_entrypoint"], "/README.md")
        self.assertEqual(entrypoints["artificial_cognition_entrypoint"], "/AI")
        self.assertEqual(
            entrypoints["machine_discovery_entrypoint"],
            "/.well-known/qik-vrt-self-disclosure.json",
        )
        self.assertEqual(entrypoints["canonical_context"], "/AI_CONTEXT.json")

    def test_self_explanation_optimization_is_fast_but_fail_closed(self):
        optimization = self.mesh_explanation["optimization_contract"]
        self.assertIs(optimization["continuous"], True)
        self.assertIs(optimization["fastest_verified_path"], True)
        self.assertIs(optimization["reuse_before_create"], True)
        self.assertIs(optimization["minimize_cognitive_hops"], True)
        self.assertIs(optimization["optimization_may_weaken_gates"], False)
        self.assertIs(optimization["optimization_may_invent_evidence"], False)
        self.assertIs(optimization["optimization_may_self_grant_authority"], False)
        self.assertIs(optimization["optimization_may_hide_uncertainty"], False)
        self.assertIs(
            optimization["perfection_is_a_direction_not_an_unbounded_completion_claim"],
            True,
        )

    def test_self_explanation_surfaces_are_bound_and_fault_tolerant(self):
        binding = self.disclosure["bindings"]["mesh_self_explanation"]
        self.assertEqual(binding["policy"], "policy/MESH_SELF_EXPLANATION_V1.json")
        self.assertEqual(binding["human_entrypoint"], "README.md")
        self.assertEqual(binding["artificial_cognition_entrypoint"], "AI")
        self.assertEqual(
            binding["machine_discovery_entrypoint"],
            ".well-known/qik-vrt-self-disclosure.json",
        )
        self.assertIs(binding["semantic_parity_required"], True)
        self.assertEqual(binding["semantic_conflict_state"], "BLOCK")
        self.assertEqual(binding["semantic_drift_state"], "BLOCK")
        fault = self.mesh_explanation["fault_tolerance"]
        self.assertEqual(fault["missing_normative_surface"], "BLOCK")
        self.assertEqual(fault["unparseable_machine_surface"], "BLOCK")
        self.assertEqual(fault["broken_reference"], "BLOCK")
        self.assertEqual(fault["normative_fallback"], "policy/MESH_SELF_EXPLANATION_V1.json")

    def test_existing_human_and_artificial_entrypoints_expose_core_orientation(self):
        for text in (
            "TRANSPORT_ACK != EFFECT_ACK",
            "One-minute evaluator path",
            "Current authority map",
            "Machine-readable publication index",
        ):
            self.assertIn(text, self.readme)
        for text in (
            "Repository evidence is canonical",
            "AI_CONTEXT.json",
            "FASTEST_VERIFIED_PATH",
            "Do not claim PASS",
        ):
            self.assertIn(text, self.ai)
        for text in (
            "Fastest safe orientation path",
            "TRANSPORT_ACK != EFFECT_ACK",
            "Normative machine-readable policy",
            "No material doubt may be hidden",
            "human/machine semantic parity",
        ):
            self.assertIn(text, self.human_contract)

    def test_maintenance_contract_blocks_partial_semantic_updates(self):
        maintenance = self.mesh_explanation["maintenance_contract"]
        self.assertEqual(maintenance["partial_update_state"], "BLOCK")
        self.assertEqual(maintenance["stale_binding_state"], "REOBSERVE")
        self.assertEqual(maintenance["unknown_required_field_state"], "HOLD")
        required = set(maintenance["semantic_change_requires_all"])
        self.assertTrue({
            "UPDATE_NORMATIVE_POLICY",
            "UPDATE_AFFECTED_HUMAN_SURFACE",
            "UPDATE_AFFECTED_ARTIFICIAL_SURFACE",
            "UPDATE_AFFECTED_MACHINE_DISCOVERY",
            "RUN_SELF_EXPLANATION_REGRESSION",
            "REOBSERVE_EXACT_SUCCESSOR",
        } <= required)
        preserve = set(self.mesh_explanation["mesh_interoperability"]["must_preserve"])
        self.assertIn("human_machine_semantic_parity", preserve)
        self.assertIs(
            self.mesh_explanation["mesh_interoperability"]["all_mesh_components_must_preserve_this_contract"],
            True,
        )


if __name__ == "__main__":
    unittest.main()
