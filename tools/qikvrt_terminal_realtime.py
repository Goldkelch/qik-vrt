#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Realtime peer reflexivity for the QIK-VRT Standard Terminal.

Five seconds is the hard freshness ceiling, not the target cadence. Active peers
push semantic transitions immediately (bounded by a short local scan interval)
and otherwise emit an adaptively selected heartbeat between 100 ms and 4 s.
GitHub Actions remains an audit/handoff plane, not the realtime transport.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "qikvrt_terminal_peer_state_v1"
MIN_HEARTBEAT_INTERVAL_MS = 100
DEFAULT_HEARTBEAT_INTERVAL_MS = 1000
MAX_HEARTBEAT_INTERVAL_MS = 4000
HEARTBEAT_INTERVAL_MS = DEFAULT_HEARTBEAT_INTERVAL_MS
MAX_STATE_AGE_MS = 5000
TRANSITION_SCAN_MS = 50
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


def _bounded_interval(value: int) -> int:
    return max(MIN_HEARTBEAT_INTERVAL_MS, min(MAX_HEARTBEAT_INTERVAL_MS, int(value)))


def _system_load_fraction() -> float:
    try:
        cpus = max(1, os.cpu_count() or 1)
        return max(0.0, float(os.getloadavg()[0]) / cpus)
    except (AttributeError, OSError):
        return 0.5


def choose_interval_ms(
    *,
    transport_rtt_ms: float = 20.0,
    local_load_fraction: float | None = None,
    send_queue_depth: int = 0,
    peer_requested_interval_ms: int | None = None,
) -> int:
    """Select the fastest bounded cadence supported by current conditions.

    The policy intentionally has no unbounded acceleration: 100 ms is the
    periodic floor, state transitions use the separate immediate-push path,
    and overload/backpressure stretches the heartbeat while staying below the
    5-second stale ceiling.
    """
    if transport_rtt_ms < 0:
        raise RealtimeTerminalBlock("transport_rtt_ms must be non-negative")
    if send_queue_depth < 0:
        raise RealtimeTerminalBlock("send_queue_depth must be non-negative")
    load = _system_load_fraction() if local_load_fraction is None else float(local_load_fraction)
    if load < 0:
        raise RealtimeTerminalBlock("local_load_fraction must be non-negative")

    if transport_rtt_ms <= 5:
        target = 100
    elif transport_rtt_ms <= 20:
        target = 200
    elif transport_rtt_ms <= 75:
        target = 500
    elif transport_rtt_ms <= 200:
        target = 1000
    else:
        target = 2000

    if peer_requested_interval_ms is not None:
        target = max(target, _bounded_interval(peer_requested_interval_ms))

    if load >= 0.90 or send_queue_depth >= 16:
        target = max(target, 3500)
    elif load >= 0.75 or send_queue_depth >= 8:
        target = max(target, 2000)
    elif load >= 0.60 or send_queue_depth >= 4:
        target = max(target, 1000)

    return _bounded_interval(target)


def make_envelope(
    *,
    peer_id: str,
    sequence: int,
    state: Mapping[str, Any],
    capabilities: Sequence[str],
    now_ms: int | None = None,
    heartbeat_interval_ms: int = DEFAULT_HEARTBEAT_INTERVAL_MS,
) -> dict[str, Any]:
    if not peer_id.strip():
        raise RealtimeTerminalBlock("peer_id is required")
    if sequence < 0:
        raise RealtimeTerminalBlock("sequence must be non-negative")
    interval = _bounded_interval(heartbeat_interval_ms)
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
        "heartbeat_interval_ms": interval,
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
    interval = envelope.get("heartbeat_interval_ms")
    if not isinstance(interval, int) or not (MIN_HEARTBEAT_INTERVAL_MS <= interval <= MAX_HEARTBEAT_INTERVAL_MS):
        raise RealtimeTerminalBlock("peer heartbeat interval outside adaptive bounds")
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
        f" cadence    : {envelope['heartbeat_interval_ms']} ms",
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


def _emit(peer_id: str, sequence: int, state: Mapping[str, Any], capabilities: Sequence[str], interval_ms: int) -> None:
    envelope = make_envelope(
        peer_id=peer_id,
        sequence=sequence,
        state=state,
        capabilities=capabilities,
        heartbeat_interval_ms=interval_ms,
    )
    print(canonical(envelope), flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit")
    emit.add_argument("--peer-id", required=True)
    emit.add_argument("--state", type=Path, required=True)
    emit.add_argument("--sequence", type=int, default=0)
    emit.add_argument("--capabilities", default="text,visual,auditory")
    emit.add_argument("--interval-ms", type=int, default=DEFAULT_HEARTBEAT_INTERVAL_MS)

    stream = sub.add_parser("stream")
    stream.add_argument("--peer-id", required=True)
    stream.add_argument("--state", type=Path, required=True)
    stream.add_argument("--start-sequence", type=int, default=0)
    stream.add_argument("--interval-ms", type=int, help="Explicit bounded cadence; omit for adaptive scaling")
    stream.add_argument("--transport-rtt-ms", type=float, default=20.0)
    stream.add_argument("--peer-requested-interval-ms", type=int)
    stream.add_argument("--send-queue-depth", type=int, default=0)
    stream.add_argument("--count", type=int, default=0, help="0 means run continuously")
    stream.add_argument("--capabilities", default="text,visual,auditory")

    render = sub.add_parser("render")
    render.add_argument("--envelope", type=Path, required=True)
    render.add_argument("--mode", choices=("json", "text", "visual", "auditory"), default="json")

    args = parser.parse_args(argv)
    try:
        if args.command == "emit":
            if not (MIN_HEARTBEAT_INTERVAL_MS <= args.interval_ms <= MAX_HEARTBEAT_INTERVAL_MS):
                raise RealtimeTerminalBlock("interval_ms outside adaptive bounds")
            envelope = make_envelope(peer_id=args.peer_id, sequence=args.sequence, state=_read(args.state), capabilities=_capabilities(args.capabilities), heartbeat_interval_ms=args.interval_ms)
            print(canonical(envelope))
            return 0
        if args.command == "stream":
            if args.interval_ms is not None and not (MIN_HEARTBEAT_INTERVAL_MS <= args.interval_ms <= MAX_HEARTBEAT_INTERVAL_MS):
                raise RealtimeTerminalBlock("interval_ms outside adaptive bounds")
            sequence = args.start_sequence
            emitted = 0
            state = _read(args.state)
            state_fingerprint = digest(state)
            interval_ms = args.interval_ms or choose_interval_ms(
                transport_rtt_ms=args.transport_rtt_ms,
                send_queue_depth=args.send_queue_depth,
                peer_requested_interval_ms=args.peer_requested_interval_ms,
            )
            _emit(args.peer_id, sequence, state, _capabilities(args.capabilities), interval_ms)
            sequence += 1
            emitted += 1
            last_emit = time.monotonic()
            while args.count == 0 or emitted < args.count:
                if args.interval_ms is None:
                    interval_ms = choose_interval_ms(
                        transport_rtt_ms=args.transport_rtt_ms,
                        send_queue_depth=args.send_queue_depth,
                        peer_requested_interval_ms=args.peer_requested_interval_ms,
                    )
                deadline = last_emit + interval_ms / 1000.0
                sleep_s = max(0.001, min(TRANSITION_SCAN_MS / 1000.0, deadline - time.monotonic()))
                time.sleep(sleep_s)
                current_state = _read(args.state)
                current_fingerprint = digest(current_state)
                transitioned = current_fingerprint != state_fingerprint
                heartbeat_due = time.monotonic() >= deadline
                if not transitioned and not heartbeat_due:
                    continue
                state = current_state
                state_fingerprint = current_fingerprint
                _emit(args.peer_id, sequence, state, _capabilities(args.capabilities), interval_ms)
                sequence += 1
                emitted += 1
                last_emit = time.monotonic()
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
