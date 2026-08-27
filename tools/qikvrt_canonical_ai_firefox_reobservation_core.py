#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Observe canonical /AI routing, real Firefox terminal interaction, and bounded Effect-Ack.

This harness uses the W3C WebDriver HTTP protocol directly with the Python
standard library. It starts no external service beyond the caller-provided
loopback HTTP servers and performs no repository mutation or protected external
effect.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

EXTENSION_ID = "qikvrt-ai-terminal@goldkelch.local"
PREFERRED_EXTENSION_UUID = "7d844896-31c8-4a82-8c53-98e473a668c7"
NONCE = "QIKVRT-FIREFOX-E2E-NONCE-0001"


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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


def wait_for(
    producer: Callable[[], Any],
    predicate: Callable[[Any], bool],
    deadline: float,
    label: str,
) -> Any:
    last: Any = None
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            last = producer()
            if predicate(last):
                return last
        except Exception as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"{label} not observed; last={last!r}; error={last_error}")


def execute(
    base: str,
    session_id: str,
    script: str,
    timeout: float = 10.0,
) -> Any:
    result = request_json(
        "POST",
        f"{base}/session/{session_id}/execute/sync",
        {"script": script, "args": []},
        timeout=timeout,
    )
    return result.get("value")


def navigate(base: str, session_id: str, url: str) -> None:
    request_json(
        "POST",
        f"{base}/session/{session_id}/url",
        {"url": url},
        timeout=30.0,
    )


def current_url(base: str, session_id: str) -> str:
    value = request_json(
        "GET",
        f"{base}/session/{session_id}/url",
        timeout=5.0,
    ).get("value")
    return str(value or "")


def installed_extension_uuid(base: str, session_id: str) -> str:
    request_json(
        "POST",
        f"{base}/session/{session_id}/moz/context",
        {"context": "chrome"},
        timeout=5.0,
    )
    try:
        raw = execute(
            base,
            session_id,
            "return Services.prefs.getStringPref('extensions.webextensions.uuids', '{}');",
            timeout=5.0,
        )
    finally:
        request_json(
            "POST",
            f"{base}/session/{session_id}/moz/context",
            {"context": "content"},
            timeout=5.0,
        )
    mapping = json.loads(str(raw or "{}"))
    value = mapping.get(EXTENSION_ID)
    if not isinstance(value, str) or not value:
        raise RuntimeError(
            f"installed extension UUID unavailable for {EXTENSION_ID}: {mapping}"
        )
    return value


def save_screenshot(
    base: str,
    session_id: str,
    target: Path,
) -> str:
    encoded = request_json(
        "GET",
        f"{base}/session/{session_id}/screenshot",
        timeout=20.0,
    ).get("value")
    if not isinstance(encoded, str) or not encoded:
        raise RuntimeError("Firefox screenshot unavailable")
    raw = base64.b64decode(encoded)
    if len(raw) < 1024 or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Firefox screenshot is not a non-empty PNG")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def observe_canonical_ai_route(
    base: str,
    session_id: str,
    ai_url: str,
    screenshot: Path,
) -> dict[str, Any]:
    navigate(base, session_id, ai_url)
    observation = wait_for(
        lambda: execute(
            base,
            session_id,
            """
            return {
              readyState: document.readyState,
              entrypoint: document.documentElement.dataset.qikvrtEntrypoint || null,
              routeState: document.documentElement.dataset.qikvrtAiRoute || null,
              status: document.getElementById('aiRouteStatus')
                ? document.getElementById('aiRouteStatus').textContent : null,
              route: document.getElementById('terminalRoute')
                ? document.getElementById('terminalRoute').href : null,
              jsReady: Boolean(window.QIKVRTAIEntrypoint &&
                window.QIKVRTAIEntrypoint.ready === true),
              bodyWidth: document.body ? document.body.getBoundingClientRect().width : 0,
              bodyHeight: document.body ? document.body.getBoundingClientRect().height : 0
            };
            """,
        ),
        lambda value: isinstance(value, dict)
        and value.get("readyState") == "complete"
        and value.get("status") == "AI_ROUTE_READY"
        and value.get("jsReady") is True,
        time.time() + 20,
        "canonical /AI JavaScript route",
    )
    if observation.get("entrypoint") != "canonical-ai-v1":
        raise RuntimeError(f"unexpected /AI entrypoint marker: {observation}")
    if observation.get("routeState") != "ready":
        raise RuntimeError(f"/AI route state not ready: {observation}")
    if float(observation.get("bodyWidth") or 0) <= 0:
        raise RuntimeError("/AI body was not rendered with positive width")
    if float(observation.get("bodyHeight") or 0) <= 0:
        raise RuntimeError("/AI body was not rendered with positive height")

    parsed_route = urllib.parse.urlparse(str(observation.get("route") or ""))
    parsed_ai = urllib.parse.urlparse(ai_url)
    if parsed_route.scheme != parsed_ai.scheme or parsed_route.netloc != parsed_ai.netloc:
        raise RuntimeError("/AI terminal route escaped same origin")
    if parsed_route.path != "/terminal/" or parsed_route.query != "qikvrt_ai_entry=1":
        raise RuntimeError(f"unexpected terminal route: {parsed_route.geturl()}")

    clicked = execute(
        base,
        session_id,
        """
        const link = document.getElementById('terminalRoute');
        if (!link) return false;
        link.click();
        return true;
        """,
    )
    if clicked is not True:
        raise RuntimeError("canonical /AI terminal route was not clickable")

    terminal_url = wait_for(
        lambda: current_url(base, session_id),
        lambda value: urllib.parse.urlparse(value).path == "/terminal/"
        and urllib.parse.urlparse(value).query == "qikvrt_ai_entry=1",
        time.time() + 20,
        "terminal navigation",
    )
    terminal_ready = wait_for(
        lambda: execute(
            base,
            session_id,
            """
            return {
              readyState: document.readyState,
              connection: document.getElementById('terminalConnectionState')
                ? document.getElementById('terminalConnectionState').textContent : null,
              output: document.getElementById('terminalOutput')
                ? document.getElementById('terminalOutput').textContent : '',
              inputPresent: Boolean(document.getElementById('terminalInput')),
              formPresent: Boolean(document.getElementById('terminalForm'))
            };
            """,
        ),
        lambda value: isinstance(value, dict)
        and value.get("readyState") == "complete"
        and value.get("connection") == "LOCAL_READY"
        and value.get("inputPresent") is True
        and value.get("formPresent") is True,
        time.time() + 20,
        "repository terminal JavaScript initialization",
    )

    submitted = execute(
        base,
        session_id,
        """
        const input = document.getElementById('terminalInput');
        const form = document.getElementById('terminalForm');
        if (!input || !form) return false;
        input.value = 'help';
        form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
        return true;
        """,
    )
    if submitted is not True:
        raise RuntimeError("terminal help interaction could not be submitted")

    terminal_output = wait_for(
        lambda: str(
            execute(
                base,
                session_id,
                "return document.getElementById('terminalOutput').textContent;",
            )
            or ""
        ),
        lambda value: "Erlaubte Befehle:" in value or "Allowed commands:" in value,
        time.time() + 10,
        "terminal help interaction output",
    )
    screenshot_sha256 = save_screenshot(base, session_id, screenshot)
    return {
        "schema": "qikvrt_canonical_ai_firefox_route_observation_v1",
        "ai_url": ai_url,
        "terminal_url": terminal_url,
        "canonical_ai_route_observed": True,
        "browser_rendering_observed": True,
        "browser_javascript_observed": True,
        "terminal_interaction_observed": True,
        "terminal_command": "help",
        "terminal_output_sha256": hashlib.sha256(
            terminal_output.encode("utf-8")
        ).hexdigest(),
        "screenshot_sha256": screenshot_sha256,
        "initial_terminal_state": terminal_ready,
        "navigation_effect_ack": "NOT_PERFORMED",
        "external_effect": "NONE",
    }


def observe_bounded_effect_ack(
    base: str,
    session_id: str,
    xpi: Path,
) -> dict[str, Any]:
    installed = request_json(
        "POST",
        f"{base}/session/{session_id}/moz/addon/install",
        {"path": str(xpi.resolve()), "temporary": True},
        timeout=20.0,
    )
    addon_id = installed.get("value")
    if addon_id != EXTENSION_ID:
        raise RuntimeError(f"unexpected installed addon id: {addon_id!r}")

    extension_uuid = installed_extension_uuid(base, session_id)
    extension_url = (
        f"moz-extension://{extension_uuid}/options.html?qikvrt_e2e=1"
    )
    navigate(base, session_id, extension_url)
    status_text = wait_for(
        lambda: str(
            execute(
                base,
                session_id,
                """
                return document.getElementById('status')
                  ? document.getElementById('status').textContent : '';
                """,
            )
            or ""
        ),
        lambda value: value.startswith("E2E_DONE:")
        or value.startswith("E2E_FAIL:"),
        time.time() + 30,
        "bounded Firefox Effect-Ack E2E",
    )
    if not status_text.startswith("E2E_DONE:"):
        raise RuntimeError(f"terminal did not reach E2E_DONE: {status_text}")
    page = json.loads(status_text.split(":", 1)[1])
    if page.get("nonce") != NONCE:
        raise RuntimeError("page nonce mismatch")
    if (
        page.get("prepare_state") != "EFFECT_ACK_DONE"
        or page.get("commit_state") != "EFFECT_ACK_DONE"
    ):
        raise RuntimeError("bounded Effect-Ack state mismatch")
    if page.get("commit_ordinary_release") is not True:
        raise RuntimeError("bounded terminal commit was not release eligible")
    if page.get("external_effect") != "NONE":
        raise RuntimeError("bounded Effect-Ack escaped loopback boundary")
    return {
        "extension_id": addon_id,
        "extension_uuid": extension_uuid,
        "extension_url": extension_url,
        "nonce": NONCE,
        "effect_ack_discovery_observed": page.get("discovery_observed") is True,
        "prepare_record_validated": page.get("prepare_record_validated") is True,
        "prepare_state": page.get("prepare_state"),
        "prepare_record_hash": page.get("prepare_record_hash"),
        "commit_state": page.get("commit_state"),
        "bounded_loopback_effect_ack_done": True,
        "effect_ack_done_scope": "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
        "external_effect": "NONE",
        "general_effect_ack_done": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geckodriver", required=True)
    parser.add_argument("--xpi", type=Path, required=True)
    parser.add_argument("--ai-url", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--geckodriver-log", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=4444)
    args = parser.parse_args()

    args.profile_root.mkdir(parents=True, exist_ok=True)
    args.geckodriver_log.parent.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{args.port}"
    log = args.geckodriver_log.open("wb")
    process = subprocess.Popen(
        [
            args.geckodriver,
            "--port",
            str(args.port),
            "--host",
            "127.0.0.1",
            "--profile-root",
            str(args.profile_root),
            "--allow-system-access",
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    session_id: str | None = None
    try:
        wait_ready(base, time.time() + 20)
        uuid_pref = json.dumps(
            {EXTENSION_ID: PREFERRED_EXTENSION_UUID},
            separators=(",", ":"),
        )
        created = request_json(
            "POST",
            base + "/session",
            {
                "capabilities": {
                    "alwaysMatch": {
                        "browserName": "firefox",
                        "pageLoadStrategy": "normal",
                        "moz:firefoxOptions": {
                            "args": [
                                "-headless",
                                "--width=1280",
                                "--height=800",
                            ],
                            "prefs": {
                                "extensions.webextensions.uuids": uuid_pref,
                                "browser.shell.checkDefaultBrowser": False,
                                "browser.tabs.warnOnClose": False,
                            },
                        },
                    }
                }
            },
            timeout=90.0,
        )
        value = created.get("value") or {}
        session_id = value.get("sessionId") or created.get("sessionId")
        if not session_id:
            raise RuntimeError(f"WebDriver session unavailable: {created}")
        capabilities = value.get("capabilities") or {}

        route = observe_canonical_ai_route(
            base,
            session_id,
            args.ai_url,
            args.screenshot,
        )
        effect_ack = observe_bounded_effect_ack(
            base,
            session_id,
            args.xpi,
        )

        receipt = {
            "schema": "qikvrt_canonical_ai_firefox_terminal_receipt_v1",
            "repository": os.environ.get(
                "GITHUB_REPOSITORY",
                "Goldkelch/qik-vrt",
            ),
            "source_head": os.environ.get(
                "QIKVRT_SOURCE_HEAD",
                "UNBOUND",
            ),
            "source_tree": os.environ.get(
                "QIKVRT_SOURCE_TREE",
                "UNBOUND",
            ),
            "event_name": os.environ.get(
                "GITHUB_EVENT_NAME",
                "UNBOUND",
            ),
            "authority_main_exact_head_reobserved": os.environ.get(
                "QIKVRT_AUTHORITY_MAIN_EXACT",
                "false",
            ).lower() == "true",
            "browser_name": capabilities.get("browserName"),
            "browser_version": capabilities.get("browserVersion"),
            "platform_name": capabilities.get("platformName"),
            "route": route,
            "effect_ack": effect_ack,
            "canonical_ai_route_observed": True,
            "browser_rendering_observed": True,
            "browser_javascript_observed": True,
            "terminal_interaction_observed": True,
            "bounded_loopback_effect_ack_done": True,
            "general_effect_ack_done": False,
            "external_effect": "NONE",
            "physical_megast_execution": False,
            "publication": False,
            "deployment": False,
            "pass": False,
            "final_pass": False,
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(receipt, sort_keys=True))
        return 0
    finally:
        if session_id:
            try:
                request_json(
                    "DELETE",
                    f"{base}/session/{session_id}",
                    timeout=5.0,
                )
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
