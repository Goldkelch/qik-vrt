import unittest

from tools.qikvrt_repair_effectiveness_guard import classify


class RepairEffectivenessGuardTests(unittest.TestCase):
    def test_non_repair_is_not_closed(self):
        self.assertEqual(classify({"repair": False})["state"], "NOT_REPAIR")

    def test_verified_pr_without_promotion_binding_is_not_closed(self):
        result = classify({"repair": True, "promotion_bound": False, "effective_on_main": False, "regression_probe_success": False})
        self.assertEqual(result, {"state": "NEED_PROMOTION_BINDING", "closed": False})

    def test_verified_repair_not_on_main_is_not_closed(self):
        result = classify({"repair": True, "promotion_bound": True, "effective_on_main": False, "regression_probe_success": True})
        self.assertEqual(result, {"state": "VERIFIED_NOT_EFFECTIVE", "closed": False})

    def test_main_effect_without_probe_is_not_closed(self):
        result = classify({"repair": True, "promotion_bound": True, "effective_on_main": True, "regression_probe_success": False})
        self.assertEqual(result, {"state": "EFFECTIVE_UNPROBED", "closed": False})

    def test_only_main_effect_plus_probe_is_closed(self):
        result = classify({"repair": True, "promotion_bound": True, "effective_on_main": True, "regression_probe_success": True})
        self.assertEqual(result, {"state": "CLOSED", "closed": True})


if __name__ == "__main__":
    unittest.main()
