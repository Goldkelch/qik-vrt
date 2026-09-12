# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest

from tools.qikvrt_ietf_effect_extensions import ReadbackModelTests, check_sources


class IETFExtensionSourceTests(unittest.TestCase):
    def test_source_inventory_and_strict_additive_precedence(self):
        result = check_sources(Path(__file__).resolve().parents[1])
        self.assertEqual(len(result["draft_sources"]), 2)
        self.assertIs(result["P2_complete"], False)
        self.assertIs(result["native_review"], False)
        self.assertIs(result["external_submission"], False)


if __name__ == "__main__":
    unittest.main()
