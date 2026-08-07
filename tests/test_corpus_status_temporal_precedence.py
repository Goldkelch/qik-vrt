#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/qikvrt_corpus_status_temporal_precedence.py"
spec = importlib.util.spec_from_file_location("corpus_temporal", PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class CorpusTemporalPrecedenceTests(unittest.TestCase):
    def test_later_evidence_resolves_workflow_without_rewriting_history(self):
        value = mod.build()
        self.assertEqual(
            value["state"],
            "CORRECTION_WORKFLOW_RESOLVED_BY_LATER_ACCEPTANCE_PROMOTION_EQUALITY",
        )
        self.assertTrue(value["historical_diagnosis_preserved"])
        self.assertEqual(len(value["historical_correction_required_subject_ids"]), 6)
        self.assertEqual(value["current_unresolved_correction_subject_ids"], [])
        self.assertFalse(value["boundaries"]["zenodo_mutation_authorized"])
        self.assertFalse(value["boundaries"]["repository_wide_pass"])

    def test_exact_expected_subject_set(self):
        value = mod.build()
        self.assertEqual(
            value["historical_correction_required_subject_ids"],
            sorted([
                "SUBJECT-172dd9bc2738fa43",
                "SUBJECT-780b9bf86425cee3",
                "SUBJECT-7956d8acdc473825",
                "SUBJECT-7fdb36aa7c07c07d",
                "SUBJECT-b4849e1a2d6b2270",
                "SUBJECT-ce2390f18618ad0c",
            ]),
        )


if __name__ == "__main__":
    unittest.main()
