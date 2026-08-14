#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Static security and accessibility regression checks for the Pages terminal."""
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs/terminal/index.html"
SCRIPT = ROOT / "docs/assets/js/qikvrt-repository-terminal.js"
STYLE = ROOT / "docs/assets/css/qikvrt-terminal.css"


class RepositoryTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = PAGE.read_text(encoding="utf-8")
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.style = STYLE.read_text(encoding="utf-8")

    def test_page_is_linked_from_pages_navigation_and_sitemap(self) -> None:
        homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        sitemap = (ROOT / "docs/sitemap.xml").read_text(encoding="utf-8")
        self.assertIn('href="terminal/"', homepage)
        self.assertIn("https://goldkelch.github.io/qik-vrt/terminal/", sitemap)

    def test_page_has_bilingual_accessible_terminal_controls(self) -> None:
        for marker in (
            'data-language="de"',
            'lang="en"',
            'id="terminalForm"',
            'id="terminalInput"',
            'id="repositorySelect"',
            'id="terminalOutput"',
            'role="log"',
            'aria-live="polite"',
            'id="startListening"',
            'id="speakOutput"',
            "ASR_DRAFT",
            "READ_ONLY",
            "EFFECT_ACK_CONTINUE",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.page)
        self.assertIn("prefers-reduced-motion", self.style)
        self.assertIn(":focus-visible", self.style)

    def test_script_has_fixed_read_only_repository_surface(self) -> None:
        for marker in (
            "Goldkelch/qik-vrt",
            "ingolf-lohmann/qik-vrt",
            'method: "GET"',
            'credentials: "omit"',
            ".well-known/qik-vrt-self-disclosure.json",
            "publication_bundles",
            "FIXED_DOCUMENTS",
            "SpeechRecognition",
            "webkitSpeechRecognition",
            "speechSynthesis",
            "ASR_DRAFT",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        for forbidden in (
            "Authorization",
            "localStorage.setItem(\"qikvrt-terminal",
            "sessionStorage",
            "innerHTML",
            "eval(",
            "Function(",
            'method: "POST"',
            'method: "PUT"',
            'method: "PATCH"',
            'method: "DELETE"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.script)

    def test_command_surface_is_explicit_and_bounded(self) -> None:
        for command in (
            'command === "help"',
            'command === "clear"',
            'command === "status"',
            'command === "capabilities"',
            'command === "read"',
            'command === "publications"',
            'command === "analyse"',
            'command === "analyze"',
        ):
            with self.subTest(command=command):
                self.assertIn(command, self.script)
        self.assertIn("no free-form commands or URLs", self.script)

    def test_script_and_test_have_current_source_license_notice(self) -> None:
        marker = "SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
        self.assertIn(marker, self.script)
        self.assertIn(marker, pathlib.Path(__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
