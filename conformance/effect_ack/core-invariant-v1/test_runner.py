"""Negative controls for the comparator, using synthetic receipts only.

These fixtures are not execution evidence for any language carrier.
"""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[2]))
from src.temdd.v1_adapter import adapt

spec = importlib.util.spec_from_file_location('core_crosscheck', BASE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ComparatorControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = json.loads((BASE / 'vectors.json').read_text())
        self.expected = runner.expected_rows(self.contract)
        self.ir = adapt((BASE / 'core_invariant.temdd').read_text())
        self.args = argparse.Namespace(
            contract=self.root / 'vectors.json', temdd_ir=self.root / 'temdd.json',
            lean_marker=self.root / 'lean.marker', spark_marker=self.root / 'spark.marker',
            lean_log=self.root / 'lean.log', spark_log=self.root / 'spark.log',
            head='a' * 40, tree='b' * 40, output=self.root / 'report.json',
            backend=[self.root / (name + '.out') for name in sorted(runner.BACKENDS)])
        self.args.contract.write_bytes((BASE / 'vectors.json').read_bytes())
        self.save_ir()
        for path in self.args.backend:
            path.write_text(''.join(' '.join(map(str, row)) + '\n' for row in self.expected))
        self.args.lean_marker.write_text('QIKVRT_CORE_INVARIANT_LEAN_PASS\n')
        self.args.spark_marker.write_text('QIKVRT_CORE_INVARIANT_SPARK_PASS\n')
        self.args.lean_log.write_text('SYNTHETIC TEST FIXTURE; not Lean evidence\n')
        self.args.spark_log.write_text('SYNTHETIC TEST FIXTURE; not SPARK evidence\n')

    def save_ir(self):
        self.args.temdd_ir.write_text(json.dumps(self.ir))

    def test_complete_synthetic_inputs_and_temdd_release_evaluation(self):
        report = runner.compare(self.args)
        self.assertEqual(report['overall'], 'PASS')
        self.assertEqual(set(report['backends']), runner.BACKENDS)
        self.assertEqual(runner.temdd_rows(self.ir), self.expected)
        self.assertFalse(report['effect_ack_done'])
        self.assertTrue(report['proof_receipts_require_trusted_workflow'])

    def test_each_required_executable_output_must_be_present(self):
        original = self.args.backend
        for missing in original:
            with self.subTest(missing=missing.name):
                self.args.backend = [p for p in original if p != missing]
                with self.assertRaisesRegex(ValueError, 'require exactly'):
                    runner.compare(self.args)

    def test_duplicate_output_cannot_replace_a_missing_language(self):
        self.args.backend[-1] = self.args.backend[0]
        with self.assertRaisesRegex(ValueError, 'require exactly'):
            runner.compare(self.args)

    def test_extra_output_is_not_silently_accepted(self):
        self.args.backend.append(self.args.backend[0])
        with self.assertRaisesRegex(ValueError, 'require exactly'):
            runner.compare(self.args)

    def test_changed_oracle_is_rejected_even_if_semantically_identical(self):
        self.args.contract.write_text(json.dumps(self.contract))
        with self.assertRaisesRegex(ValueError, 'digest changed'):
            runner.compare(self.args)

    def test_sixteen_duplicate_rows_are_not_exhaustive(self):
        self.contract['vectors'] = [self.contract['vectors'][0]] * 16
        with self.assertRaisesRegex(ValueError, 'each Boolean assignment'):
            runner.expected_rows(self.contract)

    def test_integer_or_string_booleans_are_rejected(self):
        for invalid in (0, 1, 'false', 'true'):
            with self.subTest(value=invalid):
                self.contract['vectors'][0]['transport_ack'] = invalid
                with self.assertRaisesRegex(ValueError, 'JSON booleans'):
                    runner.expected_rows(self.contract)

    def test_always_block_carrier_fails_positive_cases(self):
        path = next(p for p in self.args.backend if p.stem == 'lean')
        path.write_text(''.join(' '.join(map(str, [*row[:4], 4, 0])) + '\n'
                                for row in self.expected))
        with self.assertRaisesRegex(ValueError, 'backend divergence'):
            runner.compare(self.args)

    def test_wrong_release_is_detected_in_each_executable_carrier(self):
        for path in self.args.backend:
            with self.subTest(carrier=path.stem):
                before = path.read_text()
                path.write_text(before.replace('1 0 0 1 2 1', '1 0 0 1 2 0'))
                with self.assertRaisesRegex(ValueError, 'backend divergence'):
                    runner.compare(self.args)
                path.write_text(before)

    def test_nonboolean_output_is_rejected(self):
        self.args.backend[0].write_text('2 0 0 0 0 0\n' * 16)
        with self.assertRaisesRegex(ValueError, 'malformed row'):
            runner.compare(self.args)

    def test_duplicate_output_row_is_rejected(self):
        path = self.args.backend[0]
        lines = path.read_text().splitlines()
        lines[-1] = lines[0]
        path.write_text('\n'.join(lines) + '\n')
        with self.assertRaisesRegex(ValueError, 'backend divergence'):
            runner.compare(self.args)

    def test_conflicting_temdd_relation_cannot_be_overwritten(self):
        duplicate = copy.deepcopy(self.ir['relations'][0])
        duplicate['name'] = 'hidden_conflict'
        duplicate['target'] = 'EFFECT_ACK_DONE'
        self.ir['relations'].insert(0, duplicate)
        self.save_ir()
        with self.assertRaisesRegex(ValueError, 'conflicting TEMDD'):
            runner.compare(self.args)

    def test_temdd_truth_and_freshness_are_checked(self):
        for field, invalid in (('epistemic', 'FALSE'), ('epistemic', 'UNKNOWN'),
                               ('freshness', 'STALE')):
            with self.subTest(field=field, value=invalid):
                before = self.ir['relations'][0][field]
                self.ir['relations'][0][field] = invalid
                self.save_ir()
                with self.assertRaisesRegex(ValueError, 'TRUE and FRESH'):
                    runner.compare(self.args)
                self.ir['relations'][0][field] = before

    def test_temdd_release_is_not_inferred_from_expected_decision(self):
        relation = next(r for r in self.ir['relations']
                        if r['predicate'] == 'permits_ordinary_release'
                        and r['source'] == 'EFFECT_ACK_DONE')
        relation['target'] = 'false'
        self.save_ir()
        with self.assertRaisesRegex(ValueError, 'TEMDD decision/release divergence'):
            runner.compare(self.args)

    def test_missing_temdd_release_relation_fails(self):
        self.ir['relations'].pop()
        self.save_ir()
        with self.assertRaisesRegex(ValueError, 'domain is incomplete'):
            runner.compare(self.args)

    def test_empty_proof_logs_are_not_accepted_as_receipts(self):
        self.args.lean_log.write_text('')
        with self.assertRaisesRegex(ValueError, 'proof log is empty'):
            runner.compare(self.args)

    def test_failed_rerun_overwrites_stale_pass(self):
        self.args.output.write_text('{"overall":"PASS"}')
        self.args.backend.pop()
        argv = []
        for name in ('contract', 'temdd_ir', 'lean_marker', 'spark_marker', 'lean_log',
                     'spark_log', 'head', 'tree', 'output'):
            argv += ['--' + name.replace('_', '-'), str(getattr(self.args, name))]
        argv += [str(path) for path in self.args.backend]
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(runner.main(argv), 1)
        self.assertEqual(json.loads(self.args.output.read_text())['overall'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
