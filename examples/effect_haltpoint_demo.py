#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""No-network QIK-VRT showcase for the five-state effect haltpoint.

Run from the repository root:

    python3 examples/effect_haltpoint_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.qikvrt_effect_ack import (  # noqa: E402
    ConnectionDecision,
    EffectAckRequest,
    RiskLevel,
    effect_ack_sync,
    sha256_identifier,
)


PAYLOAD = b"publish audited QIK-VRT result"
EVIDENCE = sha256_identifier(b"reproducible verification evidence")
FIXED_TIME = "2026-07-21T12:00:00.000000Z"


def show(label: str, request: EffectAckRequest) -> None:
    result = effect_ack_sync(request, created_utc=FIXED_TIME)
    reasons = ", ".join(result.protocol.reasons)
    print(f"{label:<18} {result.state.value:<22} release={result.ordinary_release}")
    print(f"  reason: {reasons}")
    print(f"  protocol: {result.protocol.protocol_hash}")


def main() -> int:
    common = {
        "protocol_root_id": "demo-effect",
        "input_id": "candidate-001",
        "payload": PAYLOAD,
        "transport_ack": True,
    }

    print("TRANSPORT_ACK != EFFECT_ACK")
    print("Only EFFECT_ACK_DONE permits ordinary release.\n")

    show(
        "checks open",
        EffectAckRequest(**common),
    )
    show(
        "contained",
        EffectAckRequest(
            **common,
            connection_decision=ConnectionDecision.ISOLATE,
            reasons=("EVIDENCE_REQUIRES_CONTAINED_REVIEW",),
        ),
    )
    show(
        "responsible block",
        EffectAckRequest(
            **common,
            connection_decision=ConnectionDecision.BLOCK,
            reasons=("POLICY_PROHIBITS_EFFECT",),
        ),
    )
    show(
        "fully verified",
        EffectAckRequest(
            **common,
            declared_input_hash=sha256_identifier(PAYLOAD),
            origin_checked=True,
            context_checked=True,
            semantics_reconstructed=True,
            effect_anticipated=True,
            risk_classified=True,
            risk_level=RiskLevel.LOW,
            responsibility_assigned=True,
            responsibility_owner="accountable-demo-owner",
            connection_decision=ConnectionDecision.RELEASE,
            policy_allows_release=True,
            evidence_refs=(EVIDENCE,),
            required_evidence_refs=(EVIDENCE,),
            reasons=("DEMO_RELEASE_CONDITIONS_SATISFIED",),
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
