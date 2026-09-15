#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Negative regression contracts for the /AI D.o.D. observatory."""
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs/AI/dod/index.html"


class AiDodObservatoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = PAGE.read_text(encoding="utf-8")

    def test_browser_surface_has_no_polling_or_background_api_reads(self) -> None:
        for forbidden in (
            "setInterval(",
            "setTimeout(",
            "fetch(",
            "XMLHttpRequest",
            "api.github.com",
            "async function",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.page)

    def test_missing_evidence_is_never_rendered_as_pass(self) -> None:
        self.assertIn("HOLD_UNVERIFIED", self.page)
        self.assertIn("every completion component remains UNKNOWN", self.page)
        self.assertNotIn(">PASS<", self.page)
        self.assertNotIn("NO PR-GATE BLOCKER OBSERVED", self.page)
        self.assertNotIn("Proceed to exact-head review/adoption gates", self.page)

    def test_subject_binding_and_stale_failure_contract_are_explicit(self) -> None:
        for marker in (
            "bind one exact subject HEAD/TREE",
            "stale/readback failure as HOLD/UNKNOWN",
            "never combine evidence from different subjects",
            "Mutation resets dependent evidence",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.page)

    def test_downstream_effects_remain_separate(self) -> None:
        for marker in (
            "Native Goldkelch review",
            "protected Main adoption",
            "visitor/session isolation",
            "EFFECT_ACK_DONE",
            "TRANSPORT_ACK ≠ EFFECT_ACK",
            "NOOP_EXCLUDED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.page)

    def test_page_is_passive_and_has_no_executable_script(self) -> None:
        lowered = self.page.lower()
        self.assertNotIn("<script", lowered)
        self.assertNotIn("<iframe", lowered)
        self.assertNotIn("<form", lowered)
        self.assertNotIn("http-equiv=\"refresh\"", lowered)


if __name__ == "__main__":
    unittest.main()
