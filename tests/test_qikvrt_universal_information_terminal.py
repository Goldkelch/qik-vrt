#!/usr/bin/env python3
from __future__ import annotations
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/UNIVERSAL_INFORMATION_TERMINAL_V1.json"
MANIFEST = ROOT / "browser/firefox/qikvrt-terminal/manifest.json"
PAGE = ROOT / "browser/firefox/qikvrt-terminal/universal.html"
SCRIPT = ROOT / "browser/firefox/qikvrt-terminal/universal.js"

class UniversalInformationTerminalTests(unittest.TestCase):
    def test_policy_preserves_universal_receipt_without_inventing_trust(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        invariants = set(policy["acceptance_invariants"])
        self.assertIn("PAST_PRESENT_FUTURE_OR_UNKNOWN_DOES_NOT_BLOCK_RECEIPT", invariants)
        self.assertIn("KNOWN_UNKNOWN_OR_ANONYMOUS_SOURCE_DOES_NOT_BLOCK_RECEIPT", invariants)
        self.assertIn("KNOWN_UNKNOWN_BROADCAST_OR_OPAQUE_DESTINATION_DOES_NOT_BLOCK_RECEIPT", invariants)
        self.assertIn("RECEIVED_DOES_NOT_EQUAL_TRUSTED", invariants)
        self.assertEqual(policy["effect_boundary"]["execution"], "SEPARATE_AUTHORITY_AND_EFFECT_ACK_GATE_REQUIRED")

    def test_firefox_surface_is_declared(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["action"]["default_popup"], "universal.html")
        self.assertIn("storage", manifest["permissions"])
        self.assertTrue(PAGE.exists())
        self.assertTrue(SCRIPT.exists())

    def test_envelope_accepts_temporal_relations_but_never_auto_executes(self):
        script = SCRIPT.read_text(encoding="utf-8")
        for marker in ("PAST", "PRESENT", "FUTURE", "UNKNOWN", "UNBOUND", "RECEIVED_NOT_AUTHORIZED", "payload_sha256", "crypto.subtle.digest"):
            with self.subTest(marker=marker):
                self.assertIn(marker, script)
        for forbidden in ("eval(", "innerHTML", "execute(", "EFFECT_ACK_DONE"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

if __name__ == "__main__":
    unittest.main()
