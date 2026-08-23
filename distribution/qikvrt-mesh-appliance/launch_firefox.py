#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Launch Firefox through geckodriver, install the exact XPI, and bind a browser selftest."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path

PORT = 4444
UUID = "4aef7d15-1f7b-4ca5-8f70-0a9106be0f17"
EXTENSION_ID = "qikvrt-ai-terminal@goldkelch.local"


def call(method: str, path: str, body: object | None = None) -> object:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def main() -> int:
    receipt = Path("/run/qikvrt/firefox-session.json")
    profile = Path.home() / ".mozilla/qikvrt-appliance"
    profile.mkdir(parents=True, exist_ok=True)
    log = open("/run/qikvrt/geckodriver.log", "w", encoding="utf-8")
    driver = subprocess.Popen(
        ["/usr/local/bin/geckodriver", "--host", "127.0.0.1", "--port", str(PORT), "--binary", "/opt/firefox/firefox", "--log", "info"],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    session: str | None = None
    try:
        for _ in range(100):
            try:
                status = call("GET", "/status")
                if isinstance(status, dict) and status.get("value", {}).get("ready"):
                    break
            except Exception:
                pass
            time.sleep(0.1)
        uuids = json.dumps({EXTENSION_ID: UUID}, separators=(",", ":"))
        response = call("POST", "/session", {
            "capabilities": {"alwaysMatch": {
                "browserName": "firefox",
                "acceptInsecureCerts": False,
                "moz:firefoxOptions": {
                    "binary": "/opt/firefox/firefox",
                    "args": ["-profile", str(profile), "--no-remote"],
                    "prefs": {"extensions.webextensions.uuids": uuids, "browser.shell.checkDefaultBrowser": False}
                }
            }}
        })
        session = response["value"]["sessionId"]
        addon = call("POST", f"/session/{session}/moz/addon/install", {
            "path": "/opt/qikvrt/qikvrt-terminal.xpi",
            "temporary": True,
            "allowPrivateBrowsing": False,
        })["value"]
        if addon != EXTENSION_ID:
            raise RuntimeError(f"unexpected addon id {addon!r}")
        call("POST", f"/session/{session}/url", {"url": f"moz-extension://{UUID}/selftest.html"})
        result = None
        for _ in range(200):
            value = call("POST", f"/session/{session}/execute/sync", {
                "script": "return document.getElementById('qikvrt-selftest')?.textContent || '';",
                "args": [],
            })["value"]
            if value and value != "PENDING":
                result = json.loads(value)
                if result.get("state") == "EFFECT_ACK_DONE":
                    break
                raise RuntimeError(result.get("reason", "browser selftest held"))
            time.sleep(0.1)
        if not result or result.get("state") != "EFFECT_ACK_DONE":
            raise RuntimeError("browser selftest timeout")
        result.update({
            "firefox_binary": "/opt/firefox/firefox",
            "extension_id": addon,
            "temporary_addon": True,
            "external_effect": "NONE",
        })
        receipt.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print("QIKVRT_FIREFOX_PROTOCOL_SELFTEST_DONE", flush=True)
        call("POST", f"/session/{session}/url", {"url": "https://github.com/Goldkelch/qik-vrt/blob/main/AI"})
        while driver.poll() is None:
            time.sleep(1)
        return 0
    finally:
        if session:
            try:
                call("DELETE", f"/session/{session}")
            except Exception:
                pass
        driver.terminate()
        try:
            driver.wait(timeout=10)
        except subprocess.TimeoutExpired:
            driver.kill()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
