#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "AI"
CONTEXT = ROOT / "AI_CONTEXT.json"
POLICY = ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json"

EXPECTED = (
    "QIKVRT UNIVERSAL TERMINAL FORWARDER V1\n"
    "PATTERN=QIKVRT_FIREFOX_TERMINAL_PROXY_V1\n"
    "DOWNSTREAM=UNKNOWN\n"
).encode("utf-8")


class AiUniversalTerminalForwarderTests(unittest.TestCase):
    def test_ai_is_a_regular_file_and_exact_minimal_forwarder(self):
        self.assertTrue(AI.is_file())
        self.assertFalse(AI.is_symlink())
        self.assertEqual(AI.read_bytes(), EXPECTED)

    def test_forwarder_is_bound_to_existing_universal_terminal_pattern(self):
        context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        forwarding = context["entrypoint_forwarding"]
        self.assertEqual(forwarding["kind"], "REGULAR_FILE_FORWARDER")
        self.assertEqual(forwarding["pattern"], "QIKVRT_FIREFOX_TERMINAL_PROXY_V1")
        self.assertEqual(forwarding["downstream_state_before_observation"], "UNKNOWN")
        self.assertEqual(policy["proxy_pattern"]["name"], forwarding["pattern"])
        self.assertEqual(
            policy["terminal"]["entrypoint_match"],
            "https://github.com/Goldkelch/qik-vrt/blob/main/AI*",
        )

    def test_ai_carries_no_embedded_runtime_or_completion_claim(self):
        text = AI.read_text(encoding="utf-8")
        for forbidden in (
            "EFFECT_ACK_DONE",
            "BOOT SEQUENCE",
            "MACHINE-VERIFIABLE SCIENCE CHARTER",
            "ROUNDTRIP.md",
            "Zenodo",
            "DONE=",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
