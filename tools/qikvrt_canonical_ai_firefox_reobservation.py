#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Firefox 153+ Local Network Access adapter for the canonical /AI E2E harness.

The core harness remains byte-preserved in
``qikvrt_canonical_ai_firefox_reobservation_core``. Firefox 153 introduced a
separate ``loopback-network`` site permission. A headless CI browser cannot
answer the UI prompt, so this adapter keeps the isolated WebDriver profile's
Local Network Access defaults fail-closed and grants only the exact installed
WebExtension principal a session-scoped loopback permission before the bounded
request is made.

This does not disable Local Network Access protection globally, does not grant
LAN access, does not use a reconstructed content principal, and does not
broaden the bounded loopback Effect-Ack scope.
"""
from __future__ import annotations

import copy
import json
from typing import Any

import qikvrt_canonical_ai_firefox_reobservation_core as core


CLAIM_BOUNDARIES = {
    "canonical_ai_route_observed": True,
    "browser_rendering_observed": True,
    "browser_javascript_observed": True,
    "terminal_interaction_observed": True,
    "bounded_loopback_effect_ack_done": True,
    "general_effect_ack_done": False,
    "external_effect": "NONE",
    "physical_megast_execution": False,
}

_LNA_RECEIPT: dict[str, Any] = {}
_ORIGINAL_REQUEST_JSON = core.request_json
_ORIGINAL_INSTALLED_EXTENSION_UUID = core.installed_extension_uuid
_ORIGINAL_OBSERVE_BOUNDED_EFFECT_ACK = core.observe_bounded_effect_ack


def request_json_with_isolated_loopback_profile(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    effective_body = body
    if method == "POST" and url.endswith("/session") and isinstance(body, dict):
        effective_body = copy.deepcopy(body)
        prefs = (
            effective_body
            .setdefault("capabilities", {})
            .setdefault("alwaysMatch", {})
            .setdefault("moz:firefoxOptions", {})
            .setdefault("prefs", {})
        )
        # Keep every page in the isolated profile fail-closed. The only ALLOW
        # edge is attached below to the actual installed WebExtension principal.
        prefs["permissions.default.loopback-network"] = 0
        prefs["permissions.default.local-network"] = 0
        prefs["network.lna.enabled"] = True
        prefs["network.lna.blocking"] = True
        _LNA_RECEIPT.update({
            "isolated_profile_loopback_default": "PROMPT",
            "isolated_profile_local_network_default": "PROMPT",
            "local_network_access_enabled": True,
            "local_network_access_blocking_enabled": True,
            "profile_scope": "ISOLATED_WEBDRIVER_PROFILE",
            "global_lna_protection_disabled": False,
            "profile_wide_loopback_allow": False,
        })
    return _ORIGINAL_REQUEST_JSON(method, url, effective_body, timeout)


def _set_context(base: str, session_id: str, context: str) -> None:
    core.request_json(
        "POST",
        f"{base}/session/{session_id}/moz/context",
        {"context": context},
        timeout=5.0,
    )


def installed_extension_uuid_with_loopback_permission(
    base: str,
    session_id: str,
) -> str:
    extension_uuid = _ORIGINAL_INSTALLED_EXTENSION_UUID(base, session_id)
    _set_context(base, session_id, "chrome")
    try:
        result = core.execute(
            base,
            session_id,
            f"""
            const expectedAddonId = {json.dumps(core.EXTENSION_ID)};
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
              (principal.originAttributes && principal.originAttributes.addonId) ||
              null;
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
            timeout=5.0,
        )
    finally:
        _set_context(base, session_id, "content")

    if not isinstance(result, dict):
        raise RuntimeError(f"loopback-network permission receipt unavailable: {result!r}")
    if result.get("error"):
        raise RuntimeError(f"exact WebExtension principal unavailable: {result!r}")
    if result.get("capability") != result.get("allowCapability"):
        raise RuntimeError(f"loopback-network permission not granted: {result!r}")
    if result.get("permission") != "loopback-network":
        raise RuntimeError(f"unexpected Firefox LNA permission: {result!r}")
    if result.get("scope") != "FIREFOX_SESSION_ONLY":
        raise RuntimeError(f"Firefox LNA permission escaped session scope: {result!r}")
    if result.get("actualExtensionPrincipalUsed") is not True:
        raise RuntimeError(f"Firefox extension principal was not used: {result!r}")
    if result.get("reconstructedPrincipalUsed") is not False:
        raise RuntimeError(f"reconstructed principal was used: {result!r}")
    if result.get("addonId") != core.EXTENSION_ID:
        raise RuntimeError(f"unexpected extension identity: {result!r}")
    if result.get("policyId") != core.EXTENSION_ID:
        raise RuntimeError(f"unexpected WebExtension policy identity: {result!r}")
    if result.get("policyHostname") != extension_uuid:
        raise RuntimeError(f"unexpected WebExtension policy hostname: {result!r}")
    if result.get("principalAddonId") != core.EXTENSION_ID:
        raise RuntimeError(f"extension principal addonId mismatch: {result!r}")

    _LNA_RECEIPT.update(result)
    _LNA_RECEIPT["loopback_network_permission_observed"] = True
    print(json.dumps({"firefox_lna_receipt": _LNA_RECEIPT}, sort_keys=True))
    return extension_uuid


def observe_bounded_effect_ack_with_lna_receipt(
    base: str,
    session_id: str,
    xpi,
) -> dict[str, Any]:
    result = _ORIGINAL_OBSERVE_BOUNDED_EFFECT_ACK(base, session_id, xpi)
    if _LNA_RECEIPT.get("loopback_network_permission_observed") is not True:
        raise RuntimeError("session-scoped loopback-network permission was not reobserved")
    if _LNA_RECEIPT.get("actualExtensionPrincipalUsed") is not True:
        raise RuntimeError("exact WebExtension principal permission was not reobserved")
    if _LNA_RECEIPT.get("profile_wide_loopback_allow") is not False:
        raise RuntimeError("profile-wide loopback permission escaped fail-closed boundary")
    result["loopback_network_permission_observed"] = True
    result["loopback_network_permission"] = dict(_LNA_RECEIPT)
    return result


core.request_json = request_json_with_isolated_loopback_profile
core.installed_extension_uuid = installed_extension_uuid_with_loopback_permission
core.observe_bounded_effect_ack = observe_bounded_effect_ack_with_lna_receipt


if __name__ == "__main__":
    raise SystemExit(core.main())
