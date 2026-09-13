# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regressions for deterministic fail-closed journey segmentation."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'journey_segmentation', ROOT/'tools/qikvrt_journey_segmentation.py')
assert spec and spec.loader
seg = importlib.util.module_from_spec(spec); spec.loader.exec_module(seg)


class FakeTokenizer:
    eos_token_id = 2

    def __call__(self, text, add_special_tokens=True, **_kwargs):
        if isinstance(text, list):
            return {'input_ids': [[0] + list(range(len(item.split()))) + [2] for item in text]}
        return {'input_ids': [0] + list(range(len(text.split()))) + [2]}

    def decode(self, seq, skip_special_tokens=True):
        return 'segment-'+str(seq[1])


class JourneySegmentationTests(unittest.TestCase):
    SOURCE = (
        'eins zwei drei vier fuenf sechs. '
        'sieben acht neun zehn elf zwoelf; '
        'dreizehn vierzehn fuenfzehn sechzehn.'
    )

    def test_monolithic_output_exhaustion_recovers_by_deterministic_segmentation(self):
        tokenizer = FakeTokenizer()
        calls = []

        def generate(part):
            calls.append(part)
            return [0, len(part.split()), tokenizer.eos_token_id]

        # The already-observed monolithic sequence has no generated EOS.
        text, plan = seg.accept_or_segment(self.SOURCE, [0, 99, 99], tokenizer, generate)
        self.assertGreaterEqual(len(plan), 2)
        self.assertEqual(calls, plan)
        self.assertTrue(text.startswith('segment-'))
        self.assertNotEqual(text, self.SOURCE)

    def test_nonterminal_child_is_recursively_subdivided_until_terminal(self):
        tokenizer = FakeTokenizer()
        calls = []

        def generate(part):
            calls.append(part)
            if len(part.split()) > 4:
                return [0, 7, 7]
            return [0, len(part.split()), tokenizer.eos_token_id]

        text, leaves = seg.translate_segmented(self.SOURCE, tokenizer, generate)
        self.assertTrue(text.startswith('segment-'))
        self.assertGreater(len(calls), len(leaves))
        self.assertTrue(all(len(part.split()) <= 4 for part in leaves))

    def test_irreducible_nonterminal_leaf_still_holds(self):
        tokenizer = FakeTokenizer()
        with self.assertRaisesRegex(ValueError, 'NO_SAFE_SEGMENT_BOUNDARY'):
            seg.translate_segmented('eins zwei', tokenizer, lambda _part: [0, 7, 7])

    def test_protected_blocks_remain_byte_identical(self):
        original = ['Titel', 'https://example.test/media', 'Absatz', 'q.e.d. Ingolf Lohmann']
        protected = lambda value: value.startswith('http') or value.startswith('q.e.d.')
        values = seg.reassemble_blocks(original, {'Titel': 'Title', 'Absatz': 'Paragraph'}, protected)
        self.assertEqual(values[1], original[1])
        self.assertEqual(values[3], original[3])
        self.assertEqual(len(values), len(original))

    def test_long_clause_uses_deterministic_whitespace_boundary_without_source_fallback(self):
        tokenizer = FakeTokenizer()
        source = ' '.join('wort'+str(i) for i in range(400))
        first = seg.segment_plan(source, tokenizer, limit=100)
        second = seg.segment_plan(source, tokenizer, limit=100)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 2)
        self.assertTrue(all(seg.token_count(tokenizer, part) <= 100 for part in first))
        self.assertEqual(' '.join(first), source)

    def test_repeated_execution_produces_identical_segmentation_plan(self):
        tokenizer = FakeTokenizer()
        first = seg.segment_plan(self.SOURCE, tokenizer, limit=10)
        second = seg.segment_plan(self.SOURCE, tokenizer, limit=10)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 2)
        self.assertTrue(all(seg.token_count(tokenizer, part) <= 10 for part in first))


if __name__ == '__main__':
    unittest.main()
