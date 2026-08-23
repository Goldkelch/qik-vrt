#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Reobserve that Firefox loaded the QIK-VRT adapter and executed its bounded probe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time
from urllib import request

EXTENSION_ID = "qikvrt-ai-terminal@goldkelch.local"
EXPECTED_TEXT = "QIKVRT_APPLIANCE_FIREFOX_SMOKE"


def addon_active(profile: Path) -> bool:
    path = profile / "extensions.json"
    if not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    for addon in value.get("addons", []):
        if addon.get("id") == EXTENSION_ID and addon.get("active") is True:
            return True
    return False


def state(base: str) -> dict[str, object]:
    with request.urlopen(base.rstrip("/") + "/terminal/state", timeout=5) as response:
        return json.loads(response.read())


def firefox_running() -> bool:
    completed = subprocess.run(
        ["pgrep", "-fa", "firefox"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0 and bool(completed.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8771")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--output")
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    last: dict[str, object] = {}
    while time.monotonic() < deadline:
        try:
            last = state(args.base)
        except Exception:
            last = {}
        event = last.get("last_event") if isinstance(last, dict) else None
        if (
            addon_active(args.profile)
            and firefox_running()
            and isinstance(event, dict)
            and event.get("text") == EXPECTED_TEXT
            and event.get("kind") == "TERMINAL_INPUT_ACCEPTED"
            and event.get("external_effect") == "NONE"
        ):
            result = {
                "schema": "qikvrt_mesh_appliance_firefox_probe_v1",
                "firefox_process_observed": True,
                "extension_id": EXTENSION_ID,
                "extension_active": True,
                "effect_ack_state": "EFFECT_ACK_DONE",
                "bounded_loopback_terminal_input_acknowledged": True,
                "post_effect_reobserved": True,
                "external_effect": "NONE",
                "event": event,
            }
            encoded = json.dumps(result, sort_keys=True, indent=2) + "\n"
            if args.output:
                Path(args.output).write_text(encoded, encoding="utf-8")
            print(encoded, end="")
            return 0
        time.sleep(1)
    raise SystemExit(
        "BLOCK: Firefox appliance probe not observed; "
        f"addon_active={addon_active(args.profile)} "
        f"firefox_running={firefox_running()} state={last!r}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
