#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Realtime peer reflexivity for the QIK-VRT Standard Terminal.

The process is transport-neutral: JSONL is the canonical wire representation.
Active peers SHOULD push a fresh state envelope every four seconds.  Any peer
state older than five seconds is rendered STALE and cannot admit productive
work.  GitHub Actions remains an audit/handoff plane; it is not used to claim a
five-second realtime SLA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "qikvrt_terminal_peer_state_v1"
HEARTBEAT_INTERVAL_MS = 4000
MAX_STATE_AGE_MS = 5000
FORBIDDEN_KEY_FRAGMENTS = ("token", "secret", "password", "private_key", "credential")


class RealtimeTerminalBlock(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RealtimeTerminalBlock(f"{label} must be an object")
    return value


def _reject_credentials(value: Any, path: str = "state") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS):
                raise RealtimeTerminalBlock(f"credential-shaped field forbidden at {path}.{key}")
            _reject_credentials(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_credentials(child, f"{path}[{index}]")


def make_envelope(*, peer_id: str, sequence: int, state: Mapping[str, Any], capabilities: Sequence[str], now_ms: int | None = None) -> dict[str, Any]:
    if not peer_id.strip():
        raise RealtimeTerminalBlock("peer_id is required")
    if sequence < 0:
        raise RealtimeTerminalBlock("sequence must be non-negative")
    _reject_credentials(state)
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    state_copy = dict(state)
    event_id = digest({"peer_id": peer_id, "sequence": sequence, "state": state_copy})
    caps = sorted(set(capabilities) | {"text", "visual", "auditory"})
    return {
        "schema": SCHEMA,
        "peer_id": peer_id,
        "sequence": sequence,
        "emitted_at_ms": now,
        "expires_at_ms": now + MAX_STATE_AGE_MS,
        "heartbeat_interval_ms": HEARTBEAT_INTERVAL_MS,
        "maximum_peer_state_age_ms": MAX_STATE_AGE_MS,
        "event_id": event_id,
        "capabilities": caps,
        "state": state_copy,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def validate_envelope(envelope: Mapping[str, Any], *, now_ms: int | None = None, previous_sequence: int | None = None) -> dict[str, Any]:
    if envelope.get("schema") != SCHEMA:
        raise RealtimeTerminalBlock("peer state schema mismatch")
    peer_id = envelope.get("peer_id")
    if not isinstance(peer_id, str) or not peer_id:
        raise RealtimeTerminalBlock("peer_id missing")
    sequence = envelope.get("sequence")
    if not isinstance(sequence, int) or sequence < 0:
        raise RealtimeTerminalBlock("sequence malformed")
    if previous_sequence is not None and sequence <= previous_sequence:
        raise RealtimeTerminalBlock("peer sequence is not monotonic")
    emitted = envelope.get("emitted_at_ms")
    expires = envelope.get("expires_at_ms")
    if not isinstance(emitted, int) or not isinstance(expires, int) or expires - emitted != MAX_STATE_AGE_MS:
        raise RealtimeTerminalBlock("peer freshness binding malformed")
    state = _mapping(envelope.get("state"), "peer state")
    _reject_credentials(state)
    expected_event = digest({"peer_id": peer_id, "sequence": sequence, "state": dict(state)})
    if envelope.get("event_id") != expected_event:
        raise RealtimeTerminalBlock("peer event identity mismatch")
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    age = max(0, now - emitted)
    fresh = now <= expires and age <= MAX_STATE_AGE_MS
    return {
        "peer_id": peer_id,
        "sequence": sequence,
        "event_id": expected_event,
        "age_ms": age,
        "fresh": fresh,
        "classification": "PEER_STATE_FRESH" if fresh else "PEER_STATE_STALE",
        "admit_productive_writer": bool(fresh),
        "admit_observer": True,
    }


def _state_summary(state: Mapping[str, Any]) -> tuple[str, str, str]:
    aggregate = state.get("aggregate") if isinstance(state.get("aggregate"), Mapping) else state
    aggregate = _mapping(aggregate, "state aggregate")
    classification = str(aggregate.get("classification") or aggregate.get("state") or "OBSERVE")
    blocker = str(aggregate.get("first_blocker") or aggregate.get("blocker") or "NONE")
    next_actions = aggregate.get("next_actions") or aggregate.get("next_action") or []
    if isinstance(next_actions, list):
        next_action = ",".join(str(x) for x in next_actions) if next_actions else "CONTINUE_REFLEXIVE_OBSERVATION"
    else:
        next_action = str(next_actions)
    return classification, blocker, next_action


def render_modalities(envelope: Mapping[str, Any], *, now_ms: int | None = None) -> dict[str, Any]:
    validation = validate_envelope(envelope, now_ms=now_ms)
    state = _mapping(envelope["state"], "peer state")
    classification, blocker, next_action = _state_summary(state)
    freshness = validation["classification"]
    if not validation["fresh"]:
        classification = "PEER_STATE_STALE"
        blocker = "PEER_HEARTBEAT_OLDER_THAN_5_SECONDS"
        next_action = "REOBSERVE_PEER_STATE"
    text = f"{envelope['peer_id']} | {classification} | age={validation['age_ms']}ms | blocker={blocker} | next={next_action}"
    visual = "\n".join([
        "+---------------- QIKVRT TERMINAL PEER ----------------+",
        f" peer       : {envelope['peer_id']}",
        f" event      : {str(envelope['event_id'])[:16]}",
        f" freshness  : {freshness} ({validation['age_ms']} ms)",
        f" state      : {classification}",
        f" blocker    : {blocker}",
        f" next       : {next_action}",
        "+-------------------------------------------------------+",
    ])
    speech = f"QIK V R T peer {envelope['peer_id']}. State {classification}. Blocker {blocker}. Next action {next_action}."
    auditory = {
        "speech_text": speech,
        "earcon_hint": "hold" if not validation["admit_productive_writer"] else "clear",
        "bel_fallback": "\u0007",
    }
    return {
        "schema": "qikvrt_terminal_peer_render_v1",
        "event_id": envelope["event_id"],
        "fresh": validation["fresh"],
        "text": text,
        "visual": visual,
        "auditory": auditory,
        "admission": {
            "admit_productive_writer": validation["admit_productive_writer"],
            "admit_observer": True,
        },
    }


def _read(path: Path) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), path.as_posix())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RealtimeTerminalBlock(f"cannot read {path}: {exc}") from exc


def _capabilities(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit")
    emit.add_argument("--peer-id", required=True)
    emit.add_argument("--state", type=Path, required=True)
    emit.add_argument("--sequence", type=int, default=0)
    emit.add_argument("--capabilities", default="text,visual,auditory")

    stream = sub.add_parser("stream")
    stream.add_argument("--peer-id", required=True)
    stream.add_argument("--state", type=Path, required=True)
    stream.add_argument("--start-sequence", type=int, default=0)
    stream.add_argument("--interval-ms", type=int, default=HEARTBEAT_INTERVAL_MS)
    stream.add_argument("--count", type=int, default=0, help="0 means run continuously")
    stream.add_argument("--capabilities", default="text,visual,auditory")

    render = sub.add_parser("render")
    render.add_argument("--envelope", type=Path, required=True)
    render.add_argument("--mode", choices=("json", "text", "visual", "auditory"), default="json")

    args = parser.parse_args(argv)
    try:
        if args.command == "emit":
            envelope = make_envelope(peer_id=args.peer_id, sequence=args.sequence, state=_read(args.state), capabilities=_capabilities(args.capabilities))
            print(canonical(envelope))
            return 0
        if args.command == "stream":
            if args.interval_ms <= 0 or args.interval_ms > HEARTBEAT_INTERVAL_MS:
                raise RealtimeTerminalBlock(f"interval_ms must be in 1..{HEARTBEAT_INTERVAL_MS}")
            sequence = args.start_sequence
            emitted = 0
            while args.count == 0 or emitted < args.count:
                envelope = make_envelope(peer_id=args.peer_id, sequence=sequence, state=_read(args.state), capabilities=_capabilities(args.capabilities))
                print(canonical(envelope), flush=True)
                sequence += 1
                emitted += 1
                if args.count == 0 or emitted < args.count:
                    time.sleep(args.interval_ms / 1000.0)
            return 0
        envelope = _read(args.envelope)
        rendered = render_modalities(envelope)
        if args.mode == "json":
            print(json.dumps(rendered, ensure_ascii=False, sort_keys=True, indent=2))
        elif args.mode == "text":
            print(rendered["text"])
        elif args.mode == "visual":
            print(rendered["visual"])
        else:
            print(rendered["auditory"]["bel_fallback"] + rendered["auditory"]["speech_text"])
        return 0
    except RealtimeTerminalBlock as exc:
        print(json.dumps({"state": "HOLD", "failure_class": "REALTIME_TERMINAL_BLOCKED", "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
