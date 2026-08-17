from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EffectAckHttpTerminalV2Tests(unittest.TestCase):
    def test_http_draft_binds_current_structured_fields_and_causality(self) -> None:
        path = ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml"
        ET.parse(path)
        text = path.read_text(encoding="utf-8")
        self.assertIn('docName="draft-lohmann-qikvrt-effect-ack-http-00"', text)
        self.assertIn('reference.RFC.9651.xml', text)
        self.assertNotIn('reference.RFC.8941.xml', text)
        self.assertIn("Causality, Serialization and Metagrammar Binding", text)
        self.assertIn("MUST NOT infer causal authorization from message order", text)
        self.assertIn("wall-clock order", text)
        self.assertIn("successful status code alone", text)
        self.assertIn("deterministic topological order", text)
        self.assertIn("MUST preserve all bound non-commutative effects", text)
        self.assertIn("Transport acknowledgement MUST NOT be substituted", text)
        self.assertIn("rendering MUST remain observation-only", text)
        self.assertIn("MUST NOT enable Prepare or Commit", text)

    def test_v2_policy_is_fail_closed(self) -> None:
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V2.json").read_text(encoding="utf-8"))
        inv = policy["invariants"]
        self.assertTrue(inv["causality_is_not_sequence"])
        self.assertTrue(inv["serialization_is_topological_projection"])
        self.assertTrue(inv["parallel_projection_preserves_causal_edges"])
        self.assertTrue(inv["imported_proxy_frame_is_display_only"])
        self.assertTrue(inv["imported_proxy_frame_cannot_prepare"])
        self.assertTrue(inv["imported_proxy_frame_cannot_commit"])
        self.assertTrue(inv["watchdog_alarm_reinitialized_on_install_startup"])
        self.assertEqual(policy["http"]["structured_fields_rfc"], 9651)
        self.assertTrue(policy["http"]["html_discovery_is_advisory"])
        self.assertFalse(policy["completion_claims"]["PASS"])
        self.assertFalse(policy["completion_claims"]["FINAL_PASS"])
        self.assertFalse(policy["completion_claims"]["EFFECT_ACK_DONE"])

    def test_firefox_proxy_is_loaded_and_display_only(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        scripts = manifest["content_scripts"][0]["js"]
        self.assertEqual(scripts, ["content.js", "proxy.js"])
        proxy = (ROOT / "browser/firefox/qikvrt-terminal/proxy.js").read_text(encoding="utf-8")
        for required in (
            'FRAME_KIND = "QIKVRT_TERMINAL_FRAME"',
            'FRAME_SCHEMA = "qikvrt_terminal_frame_v1"',
            'event.source !== window',
            'event.origin !== location.origin',
            'MAX_FRAME_BYTES = 256 * 1024',
            'display_only: true',
            'rendering_is_authorization: false',
            'proxy_frame_can_prepare: false',
            'proxy_frame_can_commit: false',
            'commit.disabled = true',
        ):
            self.assertIn(required, proxy)
        self.assertNotIn('runtime.sendMessage', proxy)
        self.assertNotIn('PREPARE_EFFECT', proxy)
        self.assertNotIn('COMMIT_EFFECT', proxy)

    def test_watchdog_reinitializes_after_firefox_restart(self) -> None:
        background = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
        self.assertIn("browser.runtime.onInstalled.addListener", background)
        self.assertIn("browser.runtime.onStartup.addListener", background)
        self.assertIn("browser.alarms.get(WATCHDOG_ALARM)", background)
        self.assertIn("periodInMinutes: WATCHDOG_PERIOD_MINUTES", background)


if __name__ == "__main__":
    unittest.main()
