# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""QIK-VRT repository-wide requirement delivery Definition of Done.

The classifier is deliberately effect-free.  It consumes one delivery
obligation together with an exact Trusted-Main observation and an external
Effect-ACK receipt.  Only the conjunction of all three may produce DONE.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

_SHA40 = 40


class DeliveryEvidenceError(ValueError):
    pass


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == _SHA40 and all(c in "0123456789abcdef" for c in value)


def classify_obligation(
    obligation: Mapping[str, Any],
    *,
    repository_root: Path,
    main_sha: str,
    main_reobservation: Mapping[str, Any] | None,
    effect_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify one obligation without transferring predecessor evidence."""
    if not _sha(main_sha):
        raise DeliveryEvidenceError("main_sha must be exact 40-hex")
    ident = obligation.get("id")
    if not isinstance(ident, str) or not ident:
        raise DeliveryEvidenceError("obligation id missing")
    paths = obligation.get("required_main_paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p for p in paths):
        raise DeliveryEvidenceError(f"{ident}: required_main_paths invalid")

    missing = [p for p in paths if not (repository_root / p).is_file()]
    base = {
        "schema": "qikvrt_requirement_delivery_disposition_v1",
        "obligation_id": ident,
        "main_sha": main_sha,
        "completion_claims": {"PASS": False, "FINAL_PASS": False},
    }
    if missing:
        return {
            **base,
            "state": "WAIT_MAIN",
            "d0": 1,
            "first_causal_blocker": "DELIVERABLE_NOT_ON_TRUSTED_MAIN",
            "missing_main_paths": missing,
            "next_action": "CONTINUE_REPOSITORY_PROMOTION_WITHOUT_PREDECESSOR_TRANSFER",
            "EFFECT_ACK_DONE": False,
        }

    if not isinstance(main_reobservation, Mapping):
        return {
            **base,
            "state": "WAIT_EXACT_MAIN_REOBSERVATION",
            "d0": 2,
            "first_causal_blocker": "EXACT_MAIN_HEAD_NOT_REOBSERVED",
            "next_action": "REOBSERVE_EXACT_TRUSTED_MAIN_HEAD",
            "EFFECT_ACK_DONE": False,
        }
    if main_reobservation.get("main_sha") != main_sha or main_reobservation.get("state") != "REOBSERVED":
        return {
            **base,
            "state": "WAIT_EXACT_MAIN_REOBSERVATION",
            "d0": 2,
            "first_causal_blocker": "MAIN_REOBSERVATION_BINDING_MISMATCH",
            "next_action": "REOBSERVE_EXACT_TRUSTED_MAIN_HEAD",
            "EFFECT_ACK_DONE": False,
        }

    delivery = obligation.get("delivery")
    if not isinstance(delivery, Mapping) or delivery.get("effect_ack_required") is not True:
        raise DeliveryEvidenceError(f"{ident}: delivery Effect-ACK contract invalid")
    required_fields = delivery.get("authoritative_readback") or []
    if not isinstance(required_fields, list) or not all(isinstance(x, str) and x for x in required_fields):
        raise DeliveryEvidenceError(f"{ident}: authoritative_readback invalid")

    if not isinstance(effect_receipt, Mapping):
        return {
            **base,
            "state": "DELIVERY_REQUIRED",
            "d0": 2,
            "first_causal_blocker": "EXTERNAL_EFFECT_NOT_OBSERVED",
            "next_action": "EXECUTE_BOUND_DELIVERY_AND_READ_BACK_EFFECT",
            "EFFECT_ACK_DONE": False,
        }
    if (
        effect_receipt.get("obligation_id") != ident
        or effect_receipt.get("main_sha") != main_sha
        or effect_receipt.get("state") != "EFFECT_ACK_DONE"
    ):
        return {
            **base,
            "state": "DELIVERY_REQUIRED",
            "d0": 2,
            "first_causal_blocker": "EFFECT_ACK_BINDING_MISMATCH",
            "next_action": "REOBSERVE_EXTERNAL_EFFECT_WITHOUT_BLIND_RETRY",
            "EFFECT_ACK_DONE": False,
        }
    readback = effect_receipt.get("readback")
    if not isinstance(readback, Mapping) or any(not readback.get(field) for field in required_fields):
        return {
            **base,
            "state": "DELIVERY_REQUIRED",
            "d0": 2,
            "first_causal_blocker": "AUTHORITATIVE_READBACK_INCOMPLETE",
            "next_action": "REOBSERVE_EXTERNAL_EFFECT_WITHOUT_BLIND_RETRY",
            "EFFECT_ACK_DONE": False,
        }

    return {
        **base,
        "state": "DONE",
        "d0": 0,
        "first_causal_blocker": None,
        "next_action": "NOOP",
        "EFFECT_ACK_DONE": True,
        "readback": dict(readback),
    }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DeliveryEvidenceError(f"{path}: expected JSON object")
    return value
