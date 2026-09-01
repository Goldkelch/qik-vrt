"""Regression contract for the Firefox universal terminal on PR pages."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
BACKGROUND = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
CONTENT = (ROOT / "browser/firefox/qikvrt-terminal/content.js").read_text(encoding="utf-8")

class FirefoxUniversalPrTerminalTests(unittest.TestCase):
    def test_firefox_terminal_injects_on_all_authority_pr_pages(self) -> None:
        matches = MANIFEST["content_scripts"][0]["matches"]
        self.assertIn("https://github.com/Goldkelch/qik-vrt/pull/*", matches)

    def test_pr_observation_binds_number_head_tree_and_never_releases_effect(self) -> None:
        for token in ("observePullRequest", "qikvrt_terminal_pr_frame_v1", "pull_request: Number(number)", "ordinary_release_requires", "OBSERVE_PR"):
            self.assertIn(token, BACKGROUND)
        self.assertIn("reobserving PR #${pr[1]} head/tree", CONTENT)
        self.assertIn('send(pr ? "OBSERVE_PR" : "OBSERVE_AUTHORITY"', CONTENT)

    def test_atari_page_uses_extension_loopback_bridge(self) -> None:
        for token in ("ATARI_BOOT", "ATARI_STATUS", "atariBoot", "atariStatus", "qikvrt.atari-terminal-boot-receipt.v1", "qikvrt.atari-terminal-status-receipt.v1", "event.source !== window", "isAtariTerminalSender", "Atari boot sender outside terminal page", "Atari status sender outside terminal page", "/qik-vrt/atari-terminal/"):
            self.assertIn(token, BACKGROUND + CONTENT)

    def test_atari_bridge_remains_exactly_local_and_sender_bound(self) -> None:
        self.assertIn("http://127.0.0.1/*", MANIFEST["host_permissions"])
        self.assertIn("http://127.0.0.1:8771", MANIFEST["content_security_policy"]["extension_pages"])
        self.assertNotIn("<all_urls>", MANIFEST["host_permissions"])
        self.assertIn("/^[0-9a-f]{32}$/.test(payload.boot_id", BACKGROUND)
        self.assertIn("request.request_id.length > 160", CONTENT)
