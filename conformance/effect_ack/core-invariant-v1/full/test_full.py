import copy
import json
from pathlib import Path
import tempfile
import unittest

import check
import temdd_profile

HERE = Path(__file__).resolve().parent


class FullContractControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((HERE / "contract.json").read_text())
        cls.core = check.compile_cubes(cls.contract["core_rules"], "risk", "decision", "state")
        cls.consumer = check.compile_cubes(cls.contract["consumer_rules"], "derived", "declared", "release")
        cls.oracle = check.expected(cls.contract)

    def state(self, mask, risk=1, decision=2):
        return check.lookup(self.core, mask, risk, decision)

    def test_positive_domain(self):
        self.assertEqual(len(self.oracle), check.CORE_CASES + check.CONSUMER_CASES)
        self.assertEqual(self.oracle[:check.CORE_CASES].count(b"2"), 4)
        self.assertEqual(self.oracle[check.CORE_CASES:].count(b"1"), 1)
        self.assertEqual(set(self.oracle[:check.CORE_CASES]), set(b"012345"))
        check.compare_bytes(self.oracle, self.oracle)

    def test_every_required_boolean_can_prevent_done(self):
        good = 61439
        self.assertEqual(self.state(good), 2)
        for bit in list(range(12)) + [13, 14, 15]:
            with self.subTest(bit=bit):
                self.assertNotEqual(self.state(good ^ (1 << bit)), 2)
        for bit in [12, 16, 17]:
            self.assertEqual(self.state(good | (1 << bit)), 4)

    def test_unknown_risk_and_nonrelease_decisions(self):
        self.assertEqual(self.state(61439, risk=0), 1)
        for decision, expected in [(0, 1), (1, 1), (3, 3), (4, 4), (5, 5)]:
            self.assertEqual(self.state(61439, decision=decision), expected)

    def test_rejection_before_state_derivation(self):
        self.assertEqual(self.state(1 << 16, risk=5), 5)
        self.assertEqual(self.state(1 << 12, decision=5), 5)

    def test_overlapping_first_match_precedence(self):
        self.assertEqual(self.state(0, decision=4), 0)
        self.assertEqual(self.state(0, decision=3), 0)
        self.assertEqual(self.state(1 << 17), 0)
        self.assertEqual(self.state(1 << 16), 4)
        self.assertEqual(self.state(1 << 12), 4)
        self.assertEqual(self.state(6 | (1 << 17), decision=3), 4)

    def test_consumer_requires_each_validator_and_matching_done(self):
        self.assertEqual(check.lookup(self.consumer, 511, 2, 2), 1)
        for bit in range(9):
            self.assertEqual(check.lookup(self.consumer, 511 ^ (1 << bit), 2, 2), 0)
        for state in [0, 1, 3, 4, 5]:
            self.assertEqual(check.lookup(self.consumer, 511, state, 2), 0)
            self.assertEqual(check.lookup(self.consumer, 511, 2, state), 0)

    def test_always_block_mutant_rejected(self):
        mutant = b"4" * check.CORE_CASES + b"0" * check.CONSUMER_CASES
        with self.assertRaisesRegex(ValueError, "divergence"):
            check.compare_bytes(mutant, self.oracle)

    def test_single_release_mutation_rejected(self):
        mutant = bytearray(self.oracle)
        mutant[-1] = ord("1")
        with self.assertRaisesRegex(ValueError, "consumer"):
            check.compare_bytes(mutant, self.oracle)

    def test_missing_extended_and_nonboolean_output_rejected(self):
        for mutant in [self.oracle[:-1], self.oracle + b"\n"]:
            with self.assertRaisesRegex(ValueError, "domain"):
                check.compare_bytes(mutant, self.oracle)
        mutant = bytearray(self.oracle)
        mutant[check.CORE_CASES] = ord("9")
        with self.assertRaisesRegex(ValueError, "consumer"):
            check.compare_bytes(mutant, self.oracle)

    def test_missing_or_duplicate_carrier_rejected(self):
        names = [Path(name + ".out") for name in sorted(check.CARRIERS)]
        check.carrier_paths(names)
        for paths in [names[:-1], names[:-1] + [names[0]]]:
            with self.assertRaises(ValueError):
                check.carrier_paths(paths)

    def test_frozen_contract_and_failed_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            contract = folder / "contract.json"
            contract.write_text(json.dumps(self.contract))
            report = folder / "report.json"
            report.write_text('{"overall":"PASS"}')
            code = check.main(["--contract", str(contract), "--directory", str(folder),
                               "--head", "a" * 40, "--tree", "b" * 40,
                               "--output", str(report)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(report.read_text())["overall"], "FAIL")

    def test_temdd_profile_rejects_stale_and_duplicate_order(self):
        ir = temdd_profile.adapt((HERE / "full.temdd").read_text())
        temdd_profile.programs(ir)
        for field, value in [("freshness", "STALE"), ("epistemic", "UNKNOWN"),
                             ("predicate", "foreign")]:
            bad = copy.deepcopy(ir)
            bad["relations"][0][field] = value
            with self.assertRaises(ValueError):
                temdd_profile.programs(bad)
        bad = copy.deepcopy(ir)
        bad["relations"][1]["source_order"] = bad["relations"][0]["source_order"]
        with self.assertRaises(ValueError):
            temdd_profile.programs(bad)

    def test_temdd_expression_language_is_closed(self):
        for text in ['__import__("os")', 'm.attr', 'm[0]', 'm + 1']:
            with self.assertRaises(ValueError):
                temdd_profile.expression(text, {"m"})


if __name__ == "__main__":
    unittest.main()
