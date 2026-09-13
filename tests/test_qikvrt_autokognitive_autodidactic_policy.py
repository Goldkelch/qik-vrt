# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/AUTOKOGNITIVE_AUTODIDACTIC_LOOP_V1.json"
AUTHORITY = ROOT / "policy/AUTHORITY_ESCALATION_V1.json"


class AutokognitiveAutodidacticPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
