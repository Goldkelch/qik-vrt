#!/usr/bin/env python3
"""QIK-VRT Metagrammatik des Verstehens: kanonische Prüfung und Digestbindung."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "qikvrt_metagrammar_envelope_v1"
KINDS = {"OBSERVE", "DECIDE", "REQUEST", "AUTHORIZE", "ACT", "ACK", "HOLD", "NOOP", "ERROR"}
VERBS = {"OBSERVE", "CLASSIFY", "BIND", "DECIDE", "EXECUTE", "TEST", "REOBSERVE", "ACK", "PERSIST", "CREATE", "UPDATE", "CLOSE", "DISPATCH"}
AUTH_STATES = {"BOUND", "MISSING", "STALE", "OUT_OF_SCOPE"}
EFFECT_STATES = {"NONE", "REQUESTED", "EXECUTED", "OBSERVED", "ACKNOWLEDGED", "REJECTED", "UNKNOWN"}
ACK_STATES = {"NONE", "PENDING", "ACKNOWLEDGED", "REJECTED"}
HEX40 = set("0123456789abcdef")
HEX64 = HEX40


class MetagrammarError(ValueError):
    pass


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise MetagrammarError(message)


def _is_hex(value: Any, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(ch in HEX40 for ch in value)


def canonical_payload(envelope: dict[str, Any]) -> bytes:
    """Serialize the proofable message deterministically, excluding self-referential proof fields."""
    obj = copy.deepcopy(envelope)
    proof = obj.setdefault("proof", {})
    proof["canonical_sha256"] = ""
    proof["signature"] = None
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(envelope)).hexdigest()


def validate(envelope: dict[str, Any], *, verify_digest: bool = True) -> None:
    required = {"meta", "binding", "intent", "authority", "evidence", "state", "effect", "proof"}
    _require(set(envelope) == required, "top-level fields must be exactly the canonical eight sections")

    meta = envelope["meta"]
    _require(meta.get("schema") == SCHEMA, "wrong schema")
    _require(meta.get("version") == "1.0", "wrong version")
    _require(meta.get("kind") in KINDS, "invalid message kind")
    _require(isinstance(meta.get("rid"), str) and meta["rid"], "rid required")
    _require(isinstance(meta.get("timestamp"), str) and meta["timestamp"], "timestamp required")

    binding = envelope["binding"]
    _require(isinstance(binding.get("repository"), str) and binding["repository"].count("/") == 1, "repository must be owner/name")
    _require(isinstance(binding.get("ref"), str) and binding["ref"], "ref required")
    _require(_is_hex(binding.get("head"), 40), "head must be lowercase 40-hex")
    _require(_is_hex(binding.get("tree"), 40), "tree must be lowercase 40-hex")

    intent = envelope["intent"]
    _require(intent.get("verb") in VERBS, "invalid intent verb")
    _require(isinstance(intent.get("object"), str) and intent["object"], "intent object required")
    _require(isinstance(intent.get("constraints"), list), "intent constraints must be an array")

    authority = envelope["authority"]
    _require(authority.get("status") in AUTH_STATES, "invalid authority state")
    _require(isinstance(authority.get("source"), str) and authority["source"], "authority source required")
    _require(isinstance(authority.get("scope"), list), "authority scope must be an array")

    evidence = envelope["evidence"]
    _require(isinstance(evidence, list), "evidence must be an array")
    for index, item in enumerate(evidence):
        _require(isinstance(item, dict), f"evidence[{index}] must be an object")
        _require(isinstance(item.get("type"), str) and item["type"], f"evidence[{index}].type required")
        digest = item.get("sha256")
        _require(digest is None or _is_hex(digest, 64), f"evidence[{index}].sha256 invalid")

    state = envelope["state"]
    _require(isinstance(state.get("classification"), str) and state["classification"], "classification required")
    _require(isinstance(state.get("next_action"), str) and state["next_action"], "next_action required")

    effect = envelope["effect"]
    _require(effect.get("state") in EFFECT_STATES, "invalid effect state")
    _require(isinstance(effect.get("productive"), bool), "effect.productive must be boolean")
    effect_ack = effect.get("effect_ack")
    _require(isinstance(effect_ack, dict) and effect_ack.get("status") in ACK_STATES, "invalid effect ack")

    if effect["productive"]:
        _require(authority["status"] == "BOUND", "productive effect requires bound authority")
        _require(effect["state"] not in {"NONE", "UNKNOWN"}, "productive effect requires a concrete effect state")

    if authority["status"] != "BOUND":
        _require(not effect["productive"], "unbound authority must fail closed")
        _require(state["next_action"] in {"HOLD", "NOOP", "REOBSERVE", "REQUEST_AUTHORITY"}, "unbound authority requires a non-productive next action")

    if effect["state"] == "ACKNOWLEDGED":
        _require(effect.get("effect_id"), "acknowledged effect requires effect_id")
        _require(effect_ack.get("status") == "ACKNOWLEDGED", "acknowledged effect requires acknowledged effect_ack")
        _require(effect_ack.get("receipt"), "acknowledged effect requires receipt")

    if effect_ack.get("status") == "ACKNOWLEDGED":
        _require(effect["state"] == "ACKNOWLEDGED", "effect_ack cannot outrun effect state")

    proof = envelope["proof"]
    digest = proof.get("canonical_sha256")
    _require(_is_hex(digest, 64), "proof.canonical_sha256 must be lowercase 64-hex")
    if verify_digest:
        expected = canonical_sha256(envelope)
        _require(digest == expected, f"canonical digest mismatch: expected {expected}")


def bind_digest(envelope: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(envelope)
    result.setdefault("proof", {})["signature"] = None
    result["proof"]["canonical_sha256"] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="QIK-VRT Metagrammatik des Verstehens prüfen")
    parser.add_argument("path", type=Path)
    parser.add_argument("--bind-digest", action="store_true", help="kanonischen Digest setzen und JSON ausgeben")
    args = parser.parse_args()

    envelope = json.loads(args.path.read_text(encoding="utf-8"))
    if args.bind_digest:
        envelope = bind_digest(envelope)
        validate(envelope)
        print(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        validate(envelope)
        print(f"VALID {envelope['meta']['rid']} {envelope['proof']['canonical_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
