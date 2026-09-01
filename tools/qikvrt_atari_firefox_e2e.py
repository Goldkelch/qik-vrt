#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Observe the exact Atari terminal candidate through a real Firefox process.

This deliberately uses the W3C WebDriver HTTP protocol with Python's standard
library.  It does not host the candidate page, start the terminal backend, or
make a protected external effect.  The caller supplies an already bound local
TLS origin, the temporary XPI, and the local Hatari-backed terminal service.

Firefox's Local Network Access protection remains fail-closed in the isolated
WebDriver profile.  Before opening the candidate page, the harness installs the
temporary XPI and grants only its *actual installed WebExtension principal* a
session-scoped ``loopback-network`` permission.  The static page has no direct
loopback fetch path; it asks that extension to perform the bounded relay.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable


EXTENSION_ID = "qikvrt-ai-terminal@goldkelch.local"
PREFERRED_EXTENSION_UUID = "7d844896-31c8-4a82-8c53-98e473a668c7"
CANDIDATE_ORIGIN = "https://goldkelch.github.io"
CANDIDATE_PATH = "/qik-vrt/atari-terminal/"
TERMINAL_SUCCESS_STATE = "VIRTUAL_MEGAST_EXECUTION_OBSERVED"
BOOT_ID = re.compile(r"^[0-9a-f]{32}$")
VISIBLE_SHA256 = re.compile(
    r"(?:^|\n)(MLP\.OPEN|HATARI\.LOG) sha256:([0-9a-f]{64})(?=\n|$)"
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of an exact local artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_candidate_url(value: str) -> str:
    """Accept only the extension's exact static Atari terminal origin and path."""
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "goldkelch.github.io"
        or parsed.port is not None
        or parsed.path != CANDIDATE_PATH
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            "candidate URL must be exactly " + CANDIDATE_ORIGIN + CANDIDATE_PATH
        )
    return CANDIDATE_ORIGIN + CANDIDATE_PATH


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Make one WebDriver JSON request and preserve error detail for HOLD."""
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method=method)
    if payload is not None:
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
    while time.monotonic() < deadline:
        try:
            response = request_json("GET", base + "/status", timeout=1.0)
            if response.get("value", {}).get("ready") is True:
                return
        except Exception as exc:  # pragma: no cover - exercised against geckodriver
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
    while time.monotonic() < deadline:
        try:
            last = producer()
            if predicate(last):
                return last
        except Exception as exc:  # pragma: no cover - depends on real browser timing
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"{label} not observed; last={last!r}; error={last_error}")


def execute(base: str, session_id: str, script: str, timeout: float = 10.0) -> Any:
    return request_json(
        "POST",
        f"{base}/session/{session_id}/execute/sync",
        {"script": script, "args": []},
        timeout=timeout,
    ).get("value")


def set_context(base: str, session_id: str, context: str) -> None:
    request_json(
        "POST",
        f"{base}/session/{session_id}/moz/context",
        {"context": context},
        timeout=5.0,
    )


def firefox_session_payload() -> dict[str, Any]:
    """Return the isolated, fail-closed Firefox capability contract."""
    uuid_pref = json.dumps(
        {EXTENSION_ID: PREFERRED_EXTENSION_UUID}, separators=(",", ":")
    )
    return {
        "capabilities": {
            "alwaysMatch": {
                "browserName": "firefox",
                # The workflow binds a candidate-local TLS endpoint.  Its
                # ephemeral CI certificate is accepted only by this isolated
                # WebDriver session; this is not a production Pages deployment.
                "acceptInsecureCerts": True,
                "moz:firefoxOptions": {
                    "args": ["-headless", "--width=1280", "--height=800"],
                    "prefs": {
                        "extensions.webextensions.uuids": uuid_pref,
                        "browser.shell.checkDefaultBrowser": False,
                        "browser.tabs.warnOnClose": False,
                        # Firefox 153+ Local Network Access remains fail closed.
                        "permissions.default.loopback-network": 0,
                        "permissions.default.local-network": 0,
                        "network.lna.enabled": True,
                        "network.lna.blocking": True,
                        # A candidate-local DNS binding must not silently leave
                        # the runner through DNS-over-HTTPS.
                        "network.trr.mode": 5,
                        # Do not inherit a runner proxy for the exact loopback
                        # candidate origin; the evidence must stay local.
                        "network.proxy.type": 0,
                    },
                },
            }
        }
    }


def create_session(base: str) -> tuple[str, dict[str, Any]]:
    response = request_json("POST", base + "/session", firefox_session_payload(), timeout=90.0)
    value = response.get("value") or {}
    session_id = value.get("sessionId") or response.get("sessionId")
    if not isinstance(session_id, str) or not session_id:
        raise RuntimeError(f"WebDriver session unavailable: {response}")
    capabilities = value.get("capabilities") or {}
    if not isinstance(capabilities, dict):
        capabilities = {}
    return session_id, capabilities


def install_temporary_xpi(base: str, session_id: str, xpi: Path) -> tuple[str, str]:
    """Install one exact XPI for this session and return its identity and digest."""
    if not xpi.is_file():
        raise RuntimeError(f"XPI unavailable: {xpi}")
    digest = sha256_file(xpi)
    installed = request_json(
        "POST",
        f"{base}/session/{session_id}/moz/addon/install",
        {"path": str(xpi.resolve()), "temporary": True},
        timeout=30.0,
    )
    addon_id = installed.get("value")
    if addon_id != EXTENSION_ID:
        raise RuntimeError(f"unexpected installed addon id: {addon_id!r}")
    return addon_id, digest


def installed_extension_uuid(base: str, session_id: str) -> str:
    """Read the UUID Firefox assigned to the installed extension, not a guess."""
    set_context(base, session_id, "chrome")
    try:
        raw = execute(
            base,
            session_id,
            "return Services.prefs.getStringPref('extensions.webextensions.uuids', '{}');",
            timeout=5.0,
        )
    finally:
        set_context(base, session_id, "content")
    mapping = json.loads(str(raw or "{}"))
    extension_uuid = mapping.get(EXTENSION_ID)
    if not isinstance(extension_uuid, str) or not extension_uuid:
        raise RuntimeError(
            f"installed extension UUID unavailable for {EXTENSION_ID}: {mapping}"
        )
    return extension_uuid


def grant_exact_extension_loopback_permission(
    base: str, session_id: str, extension_uuid: str
) -> dict[str, Any]:
    """Grant loopback only to the real installed extension principal, for this session."""
    set_context(base, session_id, "chrome")
    try:
        result = execute(
            base,
            session_id,
            f"""
            const expectedAddonId = {json.dumps(EXTENSION_ID)};
            const expectedUUID = {json.dumps(extension_uuid)};
            const policy = WebExtensionPolicy.getByID(expectedAddonId);
            if (!policy || !policy.extension || !policy.extension.principal) {{
              return {{
                error: "EXACT_WEBEXTENSION_PRINCIPAL_UNAVAILABLE",
                expectedAddonId,
                expectedUUID,
                policyPresent: Boolean(policy),
                extensionPresent: Boolean(policy && policy.extension)
              }};
            }}
            const principal = policy.extension.principal;
            const principalAddonId = principal.addonId ||
              (principal.originAttributes && principal.originAttributes.addonId) || null;
            Services.perms.addFromPrincipal(
              principal,
              "loopback-network",
              Services.perms.ALLOW_ACTION,
              Services.perms.EXPIRE_SESSION
            );
            const capability = Services.perms.testExactPermissionFromPrincipal(
              principal,
              "loopback-network"
            );
            return {{
              addonId: expectedAddonId,
              policyId: policy.id,
              policyHostname: policy.mozExtensionHostname,
              extensionUUID: expectedUUID,
              principalOrigin: principal.origin,
              principalOriginNoSuffix: principal.originNoSuffix,
              principalAddonId,
              actualExtensionPrincipalUsed: true,
              reconstructedPrincipalUsed: false,
              permission: "loopback-network",
              capability,
              allowCapability: Services.perms.ALLOW_ACTION,
              expireType: Services.perms.EXPIRE_SESSION,
              scope: "FIREFOX_SESSION_ONLY",
              target: "127.0.0.1:8771"
            }};
            """,
            timeout=10.0,
        )
    finally:
        set_context(base, session_id, "content")
    if not isinstance(result, dict):
        raise RuntimeError(f"loopback-network permission receipt unavailable: {result!r}")
    expected = {
        "addonId": EXTENSION_ID,
        "policyId": EXTENSION_ID,
        "policyHostname": extension_uuid,
        "extensionUUID": extension_uuid,
        "permission": "loopback-network",
        "scope": "FIREFOX_SESSION_ONLY",
        "target": "127.0.0.1:8771",
        "actualExtensionPrincipalUsed": True,
        "reconstructedPrincipalUsed": False,
    }
    if result.get("error") or any(result.get(key) != value for key, value in expected.items()):
        raise RuntimeError(f"exact extension loopback permission failed: {result!r}")
    if result.get("capability") != result.get("allowCapability"):
        raise RuntimeError(f"loopback-network permission was not granted: {result!r}")
    if result.get("principalAddonId") != EXTENSION_ID:
        raise RuntimeError(f"extension principal addonId mismatch: {result!r}")
    return {
        **result,
        "loopback_network_permission_observed": True,
        "isolated_profile_loopback_default": "PROMPT",
        "isolated_profile_local_network_default": "PROMPT",
        "local_network_access_enabled": True,
        "local_network_access_blocking_enabled": True,
        "profile_scope": "ISOLATED_WEBDRIVER_PROFILE",
        "global_lna_protection_disabled": False,
        "profile_wide_loopback_allow": False,
    }


def navigate(base: str, session_id: str, url: str) -> None:
    request_json(
        "POST", f"{base}/session/{session_id}/url", {"url": url}, timeout=45.0
    )


def terminal_projection(base: str, session_id: str) -> dict[str, Any]:
    """Read only visible candidate and extension state from the active document."""
    value = execute(
        base,
        session_id,
        """
        const state = document.getElementById('state');
        const screen = document.getElementById('screen');
        const boot = document.getElementById('boot');
        const universalTerminal = document.getElementById('qikvrt-ai-terminal-host');
        return {
          readyState: document.readyState,
          origin: location.origin,
          path: location.pathname,
          state: state ? state.textContent : null,
          screen: screen ? screen.textContent : null,
          bootPresent: Boolean(boot),
          universalTerminalPresent: Boolean(universalTerminal),
          bodyWidth: document.body ? document.body.getBoundingClientRect().width : 0,
          bodyHeight: document.body ? document.body.getBoundingClientRect().height : 0
        };
        """,
        timeout=10.0,
    )
    if not isinstance(value, dict):
        raise RuntimeError(f"candidate terminal projection unavailable: {value!r}")
    return value


def candidate_page_ready(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("readyState") == "complete"
        and value.get("origin") == CANDIDATE_ORIGIN
        and value.get("path") == CANDIDATE_PATH
        and value.get("bootPresent") is True
        and value.get("universalTerminalPresent") is True
        and float(value.get("bodyWidth") or 0) > 0
        and float(value.get("bodyHeight") or 0) > 0
    )


def terminal_success(value: Any) -> bool:
    if not isinstance(value, dict) or value.get("state") != TERMINAL_SUCCESS_STATE:
        return False
    screen = value.get("screen")
    return isinstance(screen, str) and all(
        marker in screen
        for marker in (
            "ATARI_BOOT_ID ",
            "MLP.OPEN sha256:",
            "HATARI.LOG sha256:",
            "EFFECT_ACK_DONE=false",
        )
    )


def click_boot(base: str, session_id: str) -> None:
    clicked = execute(
        base,
        session_id,
        """
        const boot = document.getElementById('boot');
        if (!boot || boot.disabled) return false;
        boot.click();
        return true;
        """,
        timeout=10.0,
    )
    if clicked is not True:
        raise RuntimeError("Atari terminal boot control was not clickable")


def save_screenshot(base: str, session_id: str, target: Path) -> str:
    encoded = request_json(
        "GET", f"{base}/session/{session_id}/screenshot", timeout=30.0
    ).get("value")
    if not isinstance(encoded, str) or not encoded:
        raise RuntimeError("Firefox screenshot unavailable")
    raw = base64.b64decode(encoded)
    if len(raw) < 1024 or not raw.startswith(PNG_SIGNATURE):
        raise RuntimeError("Firefox screenshot is not a non-empty PNG")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def atari_boot_id(screen: str) -> str:
    match = re.search(r"(?:^|\n)ATARI_BOOT_ID ([0-9a-f]{32})(?:\n|$)", screen)
    if not match or not BOOT_ID.fullmatch(match.group(1)):
        raise RuntimeError("candidate screen did not expose a valid Atari boot identifier")
    return match.group(1)


def visible_terminal_digest(screen: str, label: str) -> str:
    """Return one exact digest emitted in the candidate terminal projection."""
    matches = [digest for observed, digest in VISIBLE_SHA256.findall(screen) if observed == label]
    if len(matches) != 1:
        raise RuntimeError(f"candidate screen did not expose exactly one {label} digest")
    return matches[0]


def build_receipt(
    *,
    candidate_url: str,
    xpi_sha256: str,
    capabilities: dict[str, Any],
    extension_id: str,
    extension_uuid: str,
    lna_permission: dict[str, Any],
    terminal: dict[str, Any],
    screenshot_sha256: str,
) -> dict[str, Any]:
    """Bind only observed browser/virtual-Mega-ST facts, retaining effect boundaries."""
    screen = terminal.get("screen")
    if not terminal_success(terminal) or not isinstance(screen, str):
        raise RuntimeError("cannot receipt an Atari terminal state that was not observed")
    return {
        "schema": "qikvrt_atari_firefox_e2e_receipt_v1",
        "repository": os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"),
        "source_head": os.environ.get("QIKVRT_SOURCE_HEAD", "UNBOUND"),
        "source_tree": os.environ.get("QIKVRT_SOURCE_TREE", "UNBOUND"),
        "event_name": os.environ.get("GITHUB_EVENT_NAME", "UNBOUND"),
        "candidate_url": candidate_url,
        "candidate_origin": CANDIDATE_ORIGIN,
        "candidate_path": CANDIDATE_PATH,
        "candidate_local_tls_observation": True,
        "candidate_pages_deployment": False,
        "browser": {
            "name": capabilities.get("browserName"),
            "version": capabilities.get("browserVersion"),
            "platform": capabilities.get("platformName"),
        },
        "extension": {
            "id": extension_id,
            "uuid": extension_uuid,
            "xpi_sha256": xpi_sha256,
            "temporary_install": True,
        },
        "loopback_network_permission": lna_permission,
        "browser_rendering_observed": True,
        "browser_javascript_observed": True,
        "universal_terminal_pattern_observed": True,
        "atari_boot_control_observed": True,
        "virtual_megast_execution_observed": True,
        "terminal_state": terminal["state"],
        "atari_boot_id": atari_boot_id(screen),
        "mlp_open_sha256": visible_terminal_digest(screen, "MLP.OPEN"),
        "hatari_trace_sha256": visible_terminal_digest(screen, "HATARI.LOG"),
        "terminal_screen_sha256": hashlib.sha256(screen.encode("utf-8")).hexdigest(),
        "screenshot_sha256": screenshot_sha256,
        # Required explicit non-claims.  The observed state is a local Hatari
        # projection, not a deployment, release verdict, or general effect ack.
        "effect_ack_done": False,
        "general_effect_ack_done": False,
        "external_effect": "NONE",
        "physical_megast_execution": False,
        "deployment": False,
        "pass": False,
        "final_pass": False,
        "publication": False,
    }


def observe(args: argparse.Namespace) -> dict[str, Any]:
    candidate_url = validate_candidate_url(args.candidate_url)
    args.profile_root.mkdir(parents=True, exist_ok=True)
    args.geckodriver_log.parent.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{args.port}"
    session_id: str | None = None
    process: subprocess.Popen[bytes] | None = None
    with args.geckodriver_log.open("wb") as log:
        process = subprocess.Popen(
            [
                str(args.geckodriver),
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
        try:
            wait_ready(base, time.monotonic() + args.driver_timeout)
            session_id, capabilities = create_session(base)
            extension_id, xpi_sha256 = install_temporary_xpi(base, session_id, args.xpi)
            extension_uuid = installed_extension_uuid(base, session_id)
            lna_permission = grant_exact_extension_loopback_permission(
                base, session_id, extension_uuid
            )
            navigate(base, session_id, candidate_url)
            wait_for(
                lambda: terminal_projection(base, session_id),
                candidate_page_ready,
                time.monotonic() + args.page_timeout,
                "candidate Atari terminal and Universal Terminal Pattern",
            )
            click_boot(base, session_id)
            terminal = wait_for(
                lambda: terminal_projection(base, session_id),
                terminal_success,
                time.monotonic() + args.boot_timeout,
                TERMINAL_SUCCESS_STATE,
            )
            screenshot_sha256 = save_screenshot(base, session_id, args.screenshot)
            receipt = build_receipt(
                candidate_url=candidate_url,
                xpi_sha256=xpi_sha256,
                capabilities=capabilities,
                extension_id=extension_id,
                extension_uuid=extension_uuid,
                lna_permission=lna_permission,
                terminal=terminal,
                screenshot_sha256=screenshot_sha256,
            )
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(
                json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(receipt, sort_keys=True))
            return receipt
        finally:
            if session_id:
                try:
                    request_json("DELETE", f"{base}/session/{session_id}", timeout=5.0)
                except Exception:
                    pass
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Observe the exact Atari terminal candidate with real Firefox WebDriver."
    )
    parser.add_argument("--geckodriver", type=Path, required=True)
    parser.add_argument("--xpi", type=Path, required=True)
    parser.add_argument("--candidate-url", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--geckodriver-log", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=4444)
    parser.add_argument("--driver-timeout", type=float, default=30.0)
    parser.add_argument("--page-timeout", type=float, default=30.0)
    parser.add_argument("--boot-timeout", type=float, default=120.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    observe(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
