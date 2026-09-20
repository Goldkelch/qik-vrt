import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_cycle import Invalid, assess, observation_hash, read_json


class CooperationCycleTests(unittest.TestCase):
    def setUp(self):
        self.data = read_json(ROOT / "data/synthetic_demo.json")

    def candidate_result(self, candidate_id="A"):
        return next(x for x in assess(self.data)["candidates"] if x["id"] == candidate_id)

    def test_cost_effect_tradeoff_preserves_two_choices(self):
        report = assess(self.data)
        self.assertEqual(report["frontier"], ["A", "C"])
        self.assertEqual(report["state"], "SYNTHETIC_DEMONSTRATION")
        self.assertIsNone(report["selected_intervention"])
        self.assertFalse(report["causal_effect_established"])
        self.assertEqual(self.candidate_result()["observed_net_person_minutes_saved"], 40)

    def test_dominated_option_is_identified(self):
        result = self.candidate_result("B")
        self.assertEqual(result["state"], "DOMINATED")
        self.assertEqual(result["dominated_by"], ["A"])

    def test_group_gain_does_not_hide_individual_loss(self):
        result = self.candidate_result("D")
        self.assertEqual(result["state"], "HOLD")
        self.assertGreater(result["observed_net_person_minutes_saved"], 0)
        self.assertTrue(any("P1/total_minutes" in x for x in result["findings"]))

    def test_empty_checks_are_not_evidence(self):
        self.data["candidates"][0]["declared_checks"] = {}
        self.assertEqual(self.candidate_result()["findings"], ["INCOMPLETE_CHECK_SET"])

    def test_truthy_text_is_not_true(self):
        self.data["candidates"][0]["declared_checks"]["equal_access"] = "false"
        self.assertEqual(self.candidate_result()["findings"], ["CHECK_NOT_EXACT_TRUE"])

    def test_bad_numeric_values_are_rejected(self):
        for number in (float("nan"), float("inf"), True, -1):
            with self.subTest(number=number):
                self.data["candidates"][0]["participants"]["P1"]["task_minutes"] = number
                self.assertEqual(self.candidate_result()["state"], "HOLD")

    def test_missing_participant_is_not_silently_dropped(self):
        del self.data["candidates"][0]["participants"]["P1"]
        self.assertEqual(self.candidate_result()["findings"], ["PARTICIPANT_SET_MISMATCH"])

    def test_unfinished_task_is_not_a_time_saving(self):
        self.data["candidates"][0]["participants"]["P1"]["completed_repetitions"] = 0
        self.assertEqual(self.candidate_result()["findings"], ["INCOMPLETE_TASK:P1"])

    def test_changed_baseline_requires_new_binding(self):
        self.data["baseline"]["participants"]["P1"]["task_minutes"] = 61
        report = assess(self.data)
        self.assertEqual(report["frontier"], [])
        self.assertTrue(all(x["findings"] == ["STALE_BASELINE_BINDING"] for x in report["candidates"]))

    def test_mixed_synthetic_and_observed_data_are_rejected(self):
        self.data["candidates"][0]["data_kind"] = "observed"
        self.assertEqual(self.candidate_result()["findings"], ["MIXED_DATA_KINDS"])

    def test_budget_is_enforced(self):
        self.data["candidates"][0]["rule_changes"] = 3
        self.assertEqual(self.candidate_result()["findings"], ["RULE_CHANGE_BUDGET"])

    def test_old_source_and_policy_cannot_inherit_result(self):
        for key in ("source_binding", "policy_sha256"):
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data[key] = "unbound"
                with self.assertRaises(Invalid):
                    assess(data)

    def test_modified_module_is_not_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "upstream").mkdir()
            shutil.copyfile(ROOT / "source_binding.json", root / "source_binding.json")
            (root / "upstream/qikvrt_perfect_optimum.py").write_text("raise RuntimeError('must not execute')")
            with self.assertRaisesRegex(Invalid, "SOURCE_HASH_MISMATCH"):
                assess(self.data, root)

    def test_empty_live_template_requests_baseline(self):
        report = assess(read_json(ROOT / "data/live_template.json"))
        self.assertEqual(report["state"], "NEED_BASELINE")
        self.assertIsNone(report["selected_intervention"])

    def test_baseline_alone_cannot_predict_best_intervention(self):
        self.data["candidates"] = []
        self.assertEqual(assess(self.data)["state"], "NEED_OBSERVATIONS")

    def test_changed_context_cannot_be_compared(self):
        self.data["candidates"][0]["context"]["task_id"] = "different_task"
        self.assertEqual(self.candidate_result()["findings"], ["CONTEXT_MISMATCH"])

    def test_equal_outcomes_do_not_count_as_progress(self):
        self.data["candidates"][0]["participants"] = copy.deepcopy(self.data["baseline"]["participants"])
        self.assertEqual(self.candidate_result()["native_decision"], "HOLD")

    def test_duplicate_keys_and_nonfinite_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            for text in ('{"x": 1, "x": 2}', '{"x": NaN}'):
                path.write_text(text)
                with self.assertRaises(Invalid):
                    read_json(path)

    def test_baseline_hash_ignores_json_formatting(self):
        reformatted = json.loads(json.dumps(self.data["baseline"], indent=4))
        self.assertEqual(observation_hash(reformatted), observation_hash(self.data["baseline"]))


if __name__ == "__main__":
    unittest.main()
