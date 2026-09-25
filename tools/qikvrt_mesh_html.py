#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed repository-native materializer for QIK_VRT_MESH.html."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = "QIK_VRT_MESH.html"
EVENT_TYPE = "qikvrt_feature_request"
TASK = "build_qik_vrt_mesh_html"
VIEWS = ["front", "side", "top", "bottom", "isometric", "free_orbit"]
TIME_MODES = ["snapshot", "timeline", "replay", "evolution", "future_projection"]
ANIMATIONS = ["rotation", "orbit", "pulse", "growth", "focus"]
SCHEMA_VERSIONS = ["v1", "v2", "v3", "v4"]

CANONICAL_REQUEST: dict[str, Any] = {
    "title": "QIK-VRT Interactive Evidence Sphere",
    "priority": "high",
    "artifact": ARTIFACT,
    "request": {
        "offline": True,
        "single_file": True,
        "embedded_svg": True,
        "views": VIEWS,
        "time_modes": TIME_MODES,
        "animations": ANIMATIONS,
        "performance": {
            "fps_monitor": True,
            "history_chart": True,
            "profile_system": True,
            "warning_history": True,
        },
        "persistence": {
            "schema_versions": SCHEMA_VERSIONS,
            "migrations": True,
            "downgrades": True,
            "canonical_json": True,
            "unicode_nfc": True,
        },
        "testing": {
            "property_based": True,
            "roundtrip": True,
            "idempotence": True,
            "unicode": True,
            "migration": True,
        },
    },
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def validate_feature_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("feature request must be an object")
    allowed = {"title", "priority", "artifact", "request", "subject_sha"}
    required = {"title", "priority", "artifact", "request"}
    if set(value) - allowed or required - set(value):
        raise ValueError("feature request fields are incomplete or unknown")
    base = {key: value[key] for key in ("title", "priority", "artifact", "request")}
    if base != CANONICAL_REQUEST:
        raise ValueError("feature request differs from canonical executable contract")
    subject = value.get("subject_sha")
    if subject is not None and (
        not isinstance(subject, str) or re.fullmatch(r"[0-9a-f]{40}", subject) is None
    ):
        raise ValueError("subject_sha must be a lowercase 40-hex Git SHA-1")
    return value


def _decode_request(raw: str) -> dict[str, Any]:
    try:
        decoded = base64.b64decode(raw.encode("ascii"), validate=True)
        value = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("request_json_b64 must be canonical base64 UTF-8 JSON") from exc
    return validate_feature_request(value)


def request_from_event(event: dict[str, Any], event_name: str, head: str) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise ValueError("bound head must be a lowercase 40-hex Git SHA-1")
    if event_name == "repository_dispatch":
        if event.get("action") != EVENT_TYPE:
            raise ValueError("unsupported repository_dispatch action")
        request = validate_feature_request(event.get("client_payload"))
    elif event_name == "workflow_dispatch":
        inputs = event.get("inputs")
        if not isinstance(inputs, dict) or inputs.get("task") != TASK:
            raise ValueError("workflow_dispatch task is missing or unsupported")
        encoded = str(inputs.get("request_json_b64") or "").strip()
        request = _decode_request(encoded) if encoded else _clone(CANONICAL_REQUEST)
        subject = str(inputs.get("subject_sha") or "").strip()
        if subject:
            request["subject_sha"] = subject
            validate_feature_request(request)
    else:
        raise ValueError("unsupported event")
    requested = request.get("subject_sha")
    if requested is not None and requested != head:
        raise ValueError("subject_sha mismatch requested=" + requested + " actual=" + head)
    return request


def artifact_bytes() -> bytes:
    path = ROOT / ARTIFACT
    data = path.read_bytes()
    if len(data) >= 10 * 1024 * 1024:
        raise ValueError("artifact exceeds 10 MiB offline single-file boundary")
    text = data.decode("utf-8")
    if not unicodedata.is_normalized("NFC", text):
        raise ValueError("artifact must be Unicode NFC")
    lowered = text.lower()
    for forbidden in ("http://", "https://", "<script src=", "<link href=", "xmlhttprequest", "websocket(", "eventsource(", "fetch("):
        if forbidden in lowered:
            raise ValueError("artifact is not offline: " + forbidden)
    if "<svg" not in lowered or "<style>" not in lowered or "<script>" not in lowered:
        raise ValueError("artifact must embed SVG, CSS and JavaScript")
    return data


def write_artifact(path: pathlib.Path) -> None:
    data = artifact_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def check_artifact(path: pathlib.Path) -> None:
    actual = path.read_bytes()
    expected = artifact_bytes()
    if actual != expected:
        raise ValueError("artifact drift actual=" + _sha256(actual) + " expected=" + _sha256(expected))


def request_summary(request: dict[str, Any], head: str) -> dict[str, Any]:
    raw = (_canonical_json(request) + "\n").encode("utf-8")
    return {
        "schema": "qikvrt_interactive_evidence_sphere_request_receipt_v1",
        "event_type": EVENT_TYPE,
        "task": TASK,
        "artifact": ARTIFACT,
        "subject_sha": head,
        "request_sha256": _sha256(raw),
        "offline": True,
        "single_file": True,
        "embedded_svg": True,
        "effect_scope": "deterministic-build-test-artifact-only",
        "repository_mutation": False,
        "effect_ack_done": False,
    }


def build_receipt(
    request: dict[str, Any],
    head: str,
    tree: str,
    artifact: pathlib.Path,
) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        raise ValueError("tree must be a lowercase 40-hex Git SHA-1")
    check_artifact(artifact)
    data = artifact.read_bytes()
    return {
        **request_summary(request, head),
        "schema": "qikvrt_interactive_evidence_sphere_build_receipt_v1",
        "tree_sha": tree,
        "artifact_sha256": _sha256(data),
        "artifact_bytes": len(data),
        "tests_required": ["property_based", "roundtrip", "idempotence", "unicode", "migration"],
        "transport_ack_is_effect_ack": False,
        "predecessor_evidence_transfer": False,
    }


def _load_event(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("event JSON must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--output", default=ARTIFACT)
    check = sub.add_parser("check")
    check.add_argument("--path", default=ARTIFACT)
    validate = sub.add_parser("validate-event")
    validate.add_argument("--event-path", required=True)
    validate.add_argument("--event-name", required=True)
    validate.add_argument("--head", required=True)
    receipt = sub.add_parser("receipt")
    receipt.add_argument("--event-path", required=True)
    receipt.add_argument("--event-name", required=True)
    receipt.add_argument("--head", required=True)
    receipt.add_argument("--tree", required=True)
    receipt.add_argument("--artifact", required=True)
    receipt.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            write_artifact(pathlib.Path(args.output))
            print("PASS generated " + args.output + " sha256=" + _sha256(pathlib.Path(args.output).read_bytes()))
        elif args.command == "check":
            check_artifact(pathlib.Path(args.path))
            print("PASS canonical offline artifact " + args.path)
        else:
            request = request_from_event(
                _load_event(pathlib.Path(args.event_path)),
                args.event_name,
                args.head,
            )
            if args.command == "validate-event":
                print(_canonical_json(request_summary(request, args.head)))
            else:
                result = build_receipt(request, args.head, args.tree, pathlib.Path(args.artifact))
                out = pathlib.Path(args.output)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(_canonical_json(result) + "\n", encoding="utf-8")
                print("PASS receipt " + str(out))
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print("BLOCK " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
