#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Observe the QIK-VRT Firefox terminal and bounded Effect-Ack lifecycle.

The harness uses the W3C WebDriver HTTP protocol directly (stdlib only), installs
an unsigned temporary XPI into a headless Firefox session, opens the extension's
options page in an explicitly bounded E2E mode, and records the page-observed
Effect-Ack result. It does not perform any repository or external effect.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

EXTENSION_ID = "qikvrt-ai-terminal@goldkelch.local"
PREFERRED_EXTENSION_UUID = "7d844896-31c8-4a82-8c53-98e473a668c7"
NONCE = "QIKVRT-FIREFOX-E2E-NONCE-0001"


def request_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"WebDriver HTTP {exc.code} for {url}: {detail}") from exc
    return json.loads(raw.decode("utf-8")) if raw else {"value": None}


def wait_ready(base: str, deadline: float) -> None:
    last: Exception | None = None
    while time.time() < deadline:
        try:
            value = request_json("GET", base + "/status", timeout=1.0)
            if value.get("value", {}).get("ready") is True:
                return
        except Exception as exc:
            last = exc
        time.sleep(0.1)
    raise RuntimeError(f"geckodriver did not become ready: {last}")


def execute(base: str, session_id: str, script: str, timeout: float = 5.0) -> Any:
    result = request_json("POST", f"{base}/session/{session_id}/execute/sync", {"script": script, "args": []}, timeout=timeout)
    return result.get("value")


def installed_extension_uuid(base: str, session_id: str) -> str:
    request_json("POST", f"{base}/session/{session_id}/moz/context", {"context": "chrome"}, timeout=5.0)
    try:
        raw = execute(base, session_id, "return Services.prefs.getStringPref('extensions.webextensions.uuids', '{}');", timeout=5.0)
    finally:
        request_json("POST", f"{base}/session/{session_id}/moz/context", {"context": "content"}, timeout=5.0)
    mapping = json.loads(str(raw or "{}"))
    value = mapping.get(EXTENSION_ID)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"installed extension UUID unavailable for {EXTENSION_ID}: {mapping}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geckodriver", required=True)
    parser.add_argument("--xpi", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--geckodriver-log", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=4444)
    args = parser.parse_args()

    args.xpi = args.xpi.resolve()
    args.profile_root.mkdir(parents=True, exist_ok=True)
    args.geckodriver_log.parent.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{args.port}"
    log = args.geckodriver_log.open("wb")
    process = subprocess.Popen(
        [args.geckodriver, "--port", str(args.port), "--host", "127.0.0.1", "--profile-root", str(args.profile_root), "--allow-system-access"],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    session_id: str | None = None
    try:
        wait_ready(base, time.time() + 20)
        uuid_pref = json.dumps({EXTENSION_ID: PREFERRED_EXTENSION_UUID}, separators=(",", ":"))
        created = request_json("POST", base + "/session", {
            "capabilities": {"alwaysMatch": {
                "browserName": "firefox",
                "moz:firefoxOptions": {
                    "args": ["-headless"],
                    "prefs": {
                        "extensions.webextensions.uuids": uuid_pref,
                        "browser.shell.checkDefaultBrowser": False,
                        "browser.tabs.warnOnClose": False
                    }
                }
            }}
        }, timeout=90.0)
        value = created.get("value") or {}
        session_id = value.get("sessionId") or created.get("sessionId")
        if not session_id:
            raise RuntimeError(f"WebDriver session unavailable: {created}")
        capabilities = value.get("capabilities") or {}

        installed = request_json("POST", f"{base}/session/{session_id}/moz/addon/install", {"path": str(args.xpi), "temporary": True}, timeout=20.0)
        addon_id = installed.get("value")
        if addon_id != EXTENSION_ID:
            raise RuntimeError(f"unexpected installed addon id: {addon_id!r}")

        extension_uuid = installed_extension_uuid(base, session_id)
        extension_url = f"moz-extension://{extension_uuid}/options.html?qikvrt_e2e=1"
        request_json("POST", f"{base}/session/{session_id}/url", {"url": extension_url}, timeout=20.0)

        status_text = ""
        deadline = time.time() + 30
        while time.time() < deadline:
            status_text = str(execute(base, session_id, "return document.getElementById('status') ? document.getElementById('status').textContent : '';", timeout=5.0) or "")
            if status_text.startswith("E2E_DONE:") or status_text.startswith("E2E_FAIL:"):
                break
            time.sleep(0.1)
        if not status_text.startswith("E2E_DONE:"):
            raise RuntimeError(f"terminal did not reach E2E_DONE: {status_text}")
        page = json.loads(status_text.split(":", 1)[1])
        if page.get("nonce") != NONCE:
            raise RuntimeError("page nonce mismatch")
        if page.get("prepare_state") != "EFFECT_ACK_DONE" or page.get("commit_state") != "EFFECT_ACK_DONE":
            raise RuntimeError("Effect-Ack terminal state mismatch")
        if page.get("commit_ordinary_release") is not True:
            raise RuntimeError("bounded terminal commit was not release eligible")
        if page.get("external_effect") != "NONE":
            raise RuntimeError("E2E escaped loopback no-external-effect boundary")

        receipt = {
            "schema": "qikvrt_firefox_terminal_effect_ack_browser_receipt_v1",
            "source_head": os.environ.get("QIKVRT_SOURCE_HEAD", "UNBOUND"),
            "source_tree": os.environ.get("QIKVRT_SOURCE_TREE", "UNBOUND"),
            "firefox_terminal_execution_observed": True,
            "extension_id": addon_id,
            "extension_uuid": extension_uuid,
            "browser_name": capabilities.get("browserName"),
            "browser_version": capabilities.get("browserVersion"),
            "platform_name": capabilities.get("platformName"),
            "nonce": NONCE,
            "effect_ack_discovery_observed": page["discovery_observed"],
            "prepare_record_validated": page["prepare_record_validated"],
            "prepare_state": page["prepare_state"],
            "prepare_record_hash": page["prepare_record_hash"],
            "commit_state": page["commit_state"],
            "bounded_loopback_effect_ack_done": True,
            "external_effect": "NONE",
            "physical_megast_execution": False,
            "general_internet_reachability_claimed": False
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt, sort_keys=True))
        return 0
    finally:
        if session_id:
            try:
                request_json("DELETE", f"{base}/session/{session_id}", timeout=5.0)
            except Exception:
                pass
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
