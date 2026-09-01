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
