# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

SPEC = importlib.util.spec_from_file_location(
    "redirect_runner", TOOLS / "qikvrt_cross_origin_redirect_runner.py"
)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class CrossOriginRedirectRunnerTests(unittest.TestCase):
    def setUp(self):
        self.handler = runner.CrossOriginAuthorizationRedirectHandler()
        self.source = urllib.request.Request(
            "https://api.github.com/repos/Goldkelch/qik-vrt/actions/artifacts/1/zip",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer secret",
            },
        )

    def test_cross_origin_redirect_drops_authorization(self):
        redirected = self.handler.redirect_request(
            self.source,
            None,
            302,
            "Found",
            {},
            "https://pipelines.actions.githubusercontent.com/signed/archive.zip?sig=x",
        )
        self.assertIsNotNone(redirected)
        assert redirected is not None
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertEqual(
            redirected.get_header("Accept"), "application/vnd.github+json"
        )

    def test_same_origin_redirect_preserves_authorization(self):
        redirected = self.handler.redirect_request(
            self.source,
            None,
            302,
            "Found",
            {},
            "https://api.github.com:443/repos/Goldkelch/qik-vrt/actions/artifacts/1/zip?redirect=1",
        )
        self.assertIsNotNone(redirected)
        assert redirected is not None
        self.assertEqual(redirected.get_header("Authorization"), "Bearer secret")


if __name__ == "__main__":
    unittest.main()
