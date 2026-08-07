#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/qikvrt_corpus_closure_overlay.py"
spec = importlib.util.spec_from_file_location("closure_overlay", PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class CorpusClosureOverlayTests(unittest.TestCase):
    def test_effective_closure_removes_only_resolved_correction_blockers(self):
        value = mod.build()
        self.assertEqual(value["current_unresolved_correction_subject_ids"], [])
        self.assertEqual(len(value["historical_correction_required_subject_ids"]), 6)
        self.assertTrue(value["historical_root_projection_preserved"])
        self.assertEqual(
            [b["failure_class"] for b in value["effective_blockers"]],
            ["ZENODO_RETROSPECTIVE_PROOF_CORPUS_MUTATION_NOT_AUTHORIZED"],
        )
        self.assertFalse(value["boundaries"]["zenodo_mutation_authorized"])
        self.assertFalse(value["boundaries"]["pass"])

    def test_next_edge_is_freeze_not_publication_effect(self):
        value = mod.build()
        self.assertEqual(value["next_deterministic_effect"], "FREEZE_FINAL_ROUND_TRIP_PUBLICATION_BYTES")
        self.assertFalse(value["boundaries"]["zenodo_publication_complete"])


if __name__ == "__main__":
    unittest.main()
