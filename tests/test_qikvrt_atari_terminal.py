"""Static contract for the Firefox-visible Atari terminal projection."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs" / "atari-terminal" / "index.html").read_text(encoding="utf-8")

class AtariTerminalTests(unittest.TestCase):
    def test_atari_terminal_is_source_bound_and_loopback_only(self) -> None:
        for token in ("ATARI / FIREFOX UNIVERSAL TERMINAL", "5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e", "qikvrt.atari-terminal-boot.v1", "qikvrt.atari-terminal-boot-receipt.v1", "qikvrt.atari-terminal-status.v1", "qikvrt.atari-terminal-status-receipt.v1", "qikvrt_atari_terminal_boot_status_v1", "FIREFOX_EXTENSION_BRIDGE_UNAVAILABLE", "bounded Atari reobservation timed out"):
            self.assertIn(token, PAGE)
        self.assertNotIn("fetch('http://127.0.0.1", PAGE)

    def test_atari_terminal_has_observable_control_surface(self) -> None:
        for token in ('id="boot"', 'id="clear"', 'id="screen"', 'aria-live="polite"', "ATARI_BOOT_ID", "APPEND_ONLY_REOBSERVATION", "EFFECT_ACK_DONE=false"):
            self.assertIn(token, PAGE)
