"""Static contract for the Firefox-visible Atari terminal projection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs" / "atari-terminal" / "index.html").read_text(encoding="utf-8")

def test_atari_terminal_is_source_bound_and_loopback_only() -> None:
    for token in ("ATARI / FIREFOX UNIVERSAL TERMINAL", "127.0.0.1:8771/qikvrt/atari/boot", "5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e", "qikvrt.atari-terminal-boot.v1", "LOCAL_BRIDGE_UNAVAILABLE", "HOLD: bridge did not assert a booted Atari."):
        assert token in PAGE

def test_atari_terminal_has_observable_control_surface() -> None:
    for token in ('id="boot"', 'id="clear"', 'id="screen"', 'aria-live="polite"', "RECEIPT "):
        assert token in PAGE
