#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Firefox 153+ Local Network Access adapter for the canonical /AI E2E harness.

The core harness remains byte-preserved in
``qikvrt_canonical_ai_firefox_reobservation_core``.  Firefox 153 introduced a
separate ``loopback-network`` site permission.  A headless CI browser cannot
answer the UI prompt, so this adapter grants that exact permission to the
installed temporary extension principal for the current Firefox session only,
reobserves the permission, and then runs the unchanged core harness.

This does not disable Local Network Access protection globally, does not grant
LAN access, and does not broaden the bounded loopback Effect-Ack scope.
"""
from __future__ import annotations

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
_ORIGINAL_INSTALLED_EXTENSION_UUID = core.installed_extension_uuid
_ORIGINAL_OBSERVE_BOUNDED_EFFECT_ACK = core.observe_bounded_effect_ack


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
    origin = f"moz-extension://{extension_uuid}"
    _set_context(base, session_id, "chrome")
    try:
        result = core.execute(
            base,
            session_id,
            f"""
            const origin = {json.dumps(origin)};
            const uri = Services.io.newURI(origin);
            const principal = Services.scriptSecurityManager
              .createContentPrincipal(uri, {{}});
            Services.perms.addFromPrincipal(
              principal,
              "loopback-network",
              Services.perms.ALLOW_ACTION,
              Services.perms.EXPIRE_SESSION
            );
            const capability = Services.perms
              .testExactPermissionFromPrincipal(
                principal,
                "loopback-network"
              );
            return {{
              origin: principal.origin,
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
    if result.get("capability") != result.get("allowCapability"):
        raise RuntimeError(f"loopback-network permission not granted: {result!r}")
    if result.get("permission") != "loopback-network":
        raise RuntimeError(f"unexpected Firefox LNA permission: {result!r}")
    if result.get("scope") != "FIREFOX_SESSION_ONLY":
        raise RuntimeError(f"Firefox LNA permission escaped session scope: {result!r}")

    _LNA_RECEIPT.clear()
    _LNA_RECEIPT.update(result)
    _LNA_RECEIPT["loopback_network_permission_observed"] = True
    _LNA_RECEIPT["global_lna_protection_disabled"] = False
    return extension_uuid


def observe_bounded_effect_ack_with_lna_receipt(
    base: str,
    session_id: str,
    xpi,
) -> dict[str, Any]:
    result = _ORIGINAL_OBSERVE_BOUNDED_EFFECT_ACK(base, session_id, xpi)
    if _LNA_RECEIPT.get("loopback_network_permission_observed") is not True:
        raise RuntimeError("session-scoped loopback-network permission was not reobserved")
    result["loopback_network_permission_observed"] = True
    result["loopback_network_permission"] = dict(_LNA_RECEIPT)
    return result


core.installed_extension_uuid = installed_extension_uuid_with_loopback_permission
core.observe_bounded_effect_ack = observe_bounded_effect_ack_with_lna_receipt


if __name__ == "__main__":
    raise SystemExit(core.main())
