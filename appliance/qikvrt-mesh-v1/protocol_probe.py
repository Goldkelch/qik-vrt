#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Exercise the bounded HTTP Effect-Ack profile and reobserve its local effect."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from typing import Any
from urllib import error, request


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def call(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    effect_request: str | None = None,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    data = None if body is None else canonical(body)
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if effect_request is not None:
        headers["Effect-Ack-Request"] = effect_request
    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=8) as response:
            raw = response.read()
            return (
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                json.loads(raw),
            )
    except error.HTTPError as exc:
        raw = exc.read()
        value = json.loads(raw) if raw else {}
        return exc.code, {key.lower(): value for key, value in exc.headers.items()}, value


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def parse_dictionary(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for member in raw.split(","):
        if "=" not in member:
            raise ValueError("malformed Effect-Ack dictionary")
        key, value = member.split("=", 1)
        key = key.strip().lower()
        if not key or key in result:
            raise ValueError("duplicate or missing Effect-Ack member")
        result[key] = value.strip()
    return result


def decode_sf_bytes(value: str) -> bytes:
    if len(value) < 2 or not value.startswith(":") or not value.endswith(":"):
        raise ValueError("Structured Field byte sequence required")
    return base64.b64decode(value[1:-1], validate=True)


def run(base: str, text: str, *, health_only: bool = False) -> dict[str, Any]:
    base = base.rstrip("/")
    status, _headers, capability = call(base + "/.well-known/effect-ack")
    if (
        status != 200
        or capability.get("versions") != [1]
        or "terminal_input" not in capability.get("protected_effects", [])
    ):
        raise RuntimeError("bounded Effect-Ack capability discovery failed")
    if health_only:
        return {
            "schema": "qikvrt_appliance_health_v1",
            "state": "READY",
            "capability": capability,
        }

    payload = {
        "schema": "qikvrt_terminal_input_v1",
        "text": text,
        "audio": None,
        "video": None,
    }
    status, headers, prepared = call(
        base + "/terminal/prepare",
        method="POST",
        body=payload,
        effect_request="v=1, mode=prepare",
    )
    parsed = parse_dictionary(headers.get("effect-ack", ""))
    if status != 200 or parsed.get("state") != "done":
        raise RuntimeError("prepare did not return bounded done")
    token = decode_sf_bytes(parsed["token"]).decode("ascii")
    record_hash = decode_sf_bytes(parsed["hash"]).hex()
    if prepared.get("record_hash") != record_hash or prepared.get("commit_token") != token:
        raise RuntimeError("compact and full prepare bindings differ")
    record_url = prepared.get("record_url")
    if not isinstance(record_url, str) or not record_url.startswith("/effect-ack/records/"):
        raise RuntimeError("prepare record URL unavailable")
    record_status, record_headers, record = call(base + record_url)
    record_parsed = parse_dictionary(record_headers.get("effect-ack", ""))
    if (
        record_status != 200
        or record.get("record_hash") != "sha256:" + record_hash
        or record_parsed.get("state") != "done"
    ):
        raise RuntimeError("full prepare record validation failed")

    commit_header = (
        f"v=1, mode=commit, token={sf_bytes(token.encode('ascii'))}, "
        f"hash={sf_bytes(bytes.fromhex(record_hash))}"
    )
    commit_status, commit_headers, committed = call(
        base + "/terminal/commit",
        method="POST",
        body=payload,
        effect_request=commit_header,
    )
    commit_parsed = parse_dictionary(commit_headers.get("effect-ack", ""))
    if (
        commit_status != 200
        or commit_parsed.get("state") != "done"
        or committed.get("ordinary_release") is not True
    ):
        raise RuntimeError("bounded commit did not reach EFFECT_ACK_DONE")
    state_status, _state_headers, state = call(base + "/terminal/state")
    event = state.get("last_event") if isinstance(state, dict) else None
    if (
        state_status != 200
        or not isinstance(event, dict)
        or event.get("kind") != "TERMINAL_INPUT_ACCEPTED"
        or event.get("text") != text
    ):
        raise RuntimeError("post-effect state was not reobserved")
    if event.get("external_effect") != "NONE" or capability.get("external_effects") != "NONE":
        raise RuntimeError("unexpected external effect boundary")
    return {
        "schema": "qikvrt_mesh_appliance_protocol_probe_v1",
        "state": "BOUNDED_LOOPBACK_TERMINAL_INPUT_ACKNOWLEDGED",
        "ordinary_release": True,
        "effect_ack_state": "EFFECT_ACK_DONE",
        "input_sha256": hashlib.sha256(canonical(payload)).hexdigest(),
        "record_hash": record_hash,
        "post_effect": event,
        "external_effect": "NONE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8771")
    parser.add_argument("--text", default="QIKVRT_APPLIANCE_PROTOCOL_SMOKE")
    parser.add_argument("--health-only", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run(args.base, args.text, health_only=args.health_only)
    encoded = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
