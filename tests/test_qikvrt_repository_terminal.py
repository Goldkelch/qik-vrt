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


class CloudSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        from html.parser import HTMLParser

        class Elements(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.elements = []

            def handle_starttag(self, tag, attrs):
                self.elements.append((tag, dict(attrs)))

        self.page = (ROOT / "docs/AI/index.html").read_text(encoding="utf-8")
        parser = Elements()
        parser.feed(self.page)
        self.elements = parser.elements
        self.links = {attrs.get("id"): attrs for tag, attrs in self.elements if tag == "a"}

    def test_primary_link_opens_the_real_browser_with_gateway_websocket_path(self) -> None:
        from urllib.parse import parse_qs, urlsplit
        target = urlsplit(self.links["cloudFirefox"]["href"])
        self.assertEqual(target.scheme, "https")
        self.assertEqual(target.netloc, "universal-terminal-production.up.railway.app")
        self.assertEqual(target.path, "/qik-vrt/mesh/v1/terminal/vnc.html")
        self.assertEqual(parse_qs(target.query)["path"], ["qik-vrt/mesh/v1/terminal/websockify"])
        self.assertEqual(parse_qs(target.query)["autoconnect"], ["true"])

    def test_repository_console_is_secondary_and_explicitly_read_only(self) -> None:
        self.assertEqual(self.links["repositoryReader"]["href"], "../terminal/")
        self.assertIn("führt keine Befehle aus", self.page)
        self.assertNotEqual(self.links["cloudFirefox"]["href"], "../terminal/")

    def test_no_redirect_background_requests_or_automatic_shared_desktop(self) -> None:
        self.assertFalse(any(tag in {"script", "iframe", "object", "embed", "form", "input"}
                             for tag, _attrs in self.elements))
        self.assertFalse(any(tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh"
                             for tag, attrs in self.elements))
        self.assertFalse(any(key.lower().startswith("on") for _tag, attrs in self.elements for key in attrs))

    def test_external_links_are_explicit_and_do_not_share_opener_or_referrer(self) -> None:
        for tag, attrs in self.elements:
            if tag == "a" and attrs.get("href", "").startswith("https://"):
                self.assertEqual(attrs.get("target"), "_blank")
                self.assertTrue({"noopener", "noreferrer"}.issubset(set(attrs.get("rel", "").split())))

    def test_runtime_links_use_actual_mesh_proxy_routes(self) -> None:
        from urllib.parse import urlsplit
        for element, route in {
            "runtimeHealth": "/qik-vrt/mesh/v1/healthz",
            "runtimeState": "/qik-vrt/mesh/v1/effect-ack/terminal/state",
            "effectCapabilities": "/qik-vrt/mesh/v1/effect-ack/.well-known/effect-ack",
        }.items():
            target = urlsplit(self.links[element]["href"])
            self.assertEqual(target.netloc, "universal-terminal-production.up.railway.app")
            self.assertEqual(target.path, route)

    def test_shared_session_and_unproven_continuation_remain_visible(self) -> None:
        self.assertIn("Bestehende gemeinsame Instanz, keine neue private Sitzung.", self.page)
        self.assertIn("Das Öffnen dieses Browsers startet oder bestätigt sie nicht.", self.page)
        self.assertIn("HOLD_UNVERIFIED", self.page)
        self.assertIn("NOOP_EXCLUDED", self.page)
        self.assertEqual(self.links["cloudFirefox"]["aria-describedby"], "sessionBoundary")


if __name__ == "__main__":
    unittest.main()
