#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression checks for copy-safe collapsible Universal Terminal output."""
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "docs/assets/js/qikvrt-collapsible-output.js"


class CollapsibleOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.script = ADAPTER.read_text(encoding="utf-8")

    def test_native_collapsible_elements_are_used(self) -> None:
        self.assertIn('document.createElement("details")', self.script)
        self.assertIn('document.createElement("summary")', self.script)
        self.assertIn('details.className = "terminal-entry-details"', self.script)

    def test_copy_preserves_exact_text_payload(self) -> None:
        self.assertIn('navigator.clipboard.writeText(content.textContent || "")', self.script)
        self.assertIn('range.selectNodeContents(content)', self.script)

    def test_adapter_is_non_executing(self) -> None:
        for forbidden in ("innerHTML", "eval(", "Function(", 'method: "POST"', 'method: "PUT"', 'method: "PATCH"', 'method: "DELETE"'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.script)


if __name__ == "__main__":
    unittest.main()
