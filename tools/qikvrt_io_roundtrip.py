#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Persist every I/O envelope and fail-closed route proven knowledge to publication.

The orchestrator is transport-agnostic. Callers provide one JSON envelope on stdin or
via --input. Repository persistence always precedes any external effect. Zenodo and
IETF effects are executable only when the envelope is eligible, exact authorization
is present, and the corresponding command adapter is configured in the environment.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/IO_ROUNDTRIP_AUTONOMOUS_PUBLICATION_V1.json"
STORE = ROOT / "evidence/io-roundtrip"
QUEUE = STORE / "publication-queue.jsonl"
EFFECTS = STORE / "effect-receipts"

ALLOWED_MODALITIES = {
    "text", "audio", "image", "video", "binary", "structured_data",
    "tool_call", "tool_result", "repository_event", "external_reference", "other",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical(value).decode("utf-8") + "\n")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def validate_policy() -> dict[str, Any]:
    policy = load_json(POLICY)
    if policy.get("schema") != "qikvrt_io_roundtrip_autonomous_publication_v1":
        raise ValueError("policy schema mismatch")
    if policy.get("invariant") != "EVERY_INPUT_OUTPUT_ENVELOPE_IS_PERSISTED_BEFORE_DERIVED_EXTERNAL_PUBLICATION":
        raise ValueError("I/O persistence invariant mismatch")
    return policy


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    modality = str(raw.get("modality", "other"))
    if modality not in ALLOWED_MODALITIES:
        modality = "other"
    payload = raw.get("payload")
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    proof = raw.get("machine_proof_receipt") if isinstance(raw.get("machine_proof_receipt"), dict) else None
    return {
        "schema": "qikvrt_io_envelope_v1",
        "direction": raw.get("direction", "UNSPECIFIED"),
        "modality": modality,
        "payload": payload,
        "metadata": metadata,
        "epistemic_status": raw.get("epistemic_status", "UNCLASSIFIED"),
        "granularity": raw.get("granularity", "UNASSESSED"),
        "connectability": raw.get("connectability", "UNASSESSED"),
        "ietf_applicable": raw.get("ietf_applicable") is True,
        "machine_proof_receipt": proof,
        "observed_at": raw.get("observed_at") or now(),
    }


def persist(envelope: dict[str, Any]) -> tuple[str, pathlib.Path]:
    envelope_id = digest(envelope)
    path = STORE / "envelopes" / envelope_id[:2] / f"{envelope_id}.json"
    if path.exists():
        current = load_json(path)
        if current != envelope:
            raise ValueError("content-address collision")
    else:
        write_json(path, envelope)
    return envelope_id, path


def publication_state(envelope: dict[str, Any]) -> dict[str, Any]:
    proof = envelope.get("machine_proof_receipt")
    proof_ok = isinstance(proof, dict) and isinstance(proof.get("sha256"), str) and len(proof["sha256"]) == 64
    granularity_ok = envelope.get("granularity") in {"ELIGIBLE", "PUBLICATION_UNIT"}
    connectable = envelope.get("connectability") in {"CONNECTABLE", "CANONICAL"}
    exact_artifact = bool(envelope.get("metadata", {}).get("artifact_sha256"))
    return {
        "new_knowledge": envelope.get("epistemic_status") == "NEW_KNOWLEDGE",
        "machine_proof_receipt": proof_ok,
        "eligible_granularity": granularity_ok,
        "connectable": connectable,
        "exact_artifact_binding": exact_artifact,
        "ietf_applicable": envelope.get("ietf_applicable") is True,
    }


def authorized(effect: str) -> bool:
    value = os.environ.get("QIKVRT_EXTERNAL_EFFECT_AUTHORIZATION", "")
    return value in {"ALL", effect}


def configured(effect: str) -> str | None:
    key = "QIKVRT_ZENODO_PUBLISH_CMD" if effect == "ZENODO" else "QIKVRT_IETF_SUBMIT_CMD"
    return os.environ.get(key) or None


def run_effect(effect: str, command: str, envelope_id: str, envelope_path: pathlib.Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["QIKVRT_IO_ENVELOPE_ID"] = envelope_id
    env["QIKVRT_IO_ENVELOPE_PATH"] = str(envelope_path)
    completed = subprocess.run(shlex.split(command), cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900, check=False)
    receipt = {
        "schema": "qikvrt_io_external_effect_receipt_v1",
        "effect": effect,
        "envelope_id": envelope_id,
        "executed_at": now(),
        "returncode": completed.returncode,
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "state": "EFFECT_SUCCEEDED" if completed.returncode == 0 else "EFFECT_FAILED_HOLD",
    }
    write_json(EFFECTS / envelope_id / f"{effect.lower()}.json", receipt)
    return receipt


def process(raw: dict[str, Any], execute_effects: bool) -> dict[str, Any]:
    validate_policy()
    envelope = normalize(raw)
    envelope_id, envelope_path = persist(envelope)
    state = publication_state(envelope)
    zenodo_eligible = all([
        state["new_knowledge"], state["machine_proof_receipt"], state["eligible_granularity"],
        state["connectable"], state["exact_artifact_binding"],
    ])
    ietf_eligible = zenodo_eligible and state["ietf_applicable"]
    queue_record = {
        "schema": "qikvrt_io_publication_queue_record_v1",
        "envelope_id": envelope_id,
        "envelope_path": envelope_path.relative_to(ROOT).as_posix(),
        "zenodo_eligible": zenodo_eligible,
        "ietf_eligible": ietf_eligible,
        "queued_at": now(),
    }
    if zenodo_eligible:
        append_jsonl(QUEUE, queue_record)

    effects: list[dict[str, Any]] = []
    if execute_effects and zenodo_eligible:
        command = configured("ZENODO")
        if authorized("ZENODO") and command:
            effects.append(run_effect("ZENODO", command, envelope_id, envelope_path))
        if ietf_eligible:
            command = configured("IETF")
            if authorized("IETF") and command:
                effects.append(run_effect("IETF", command, envelope_id, envelope_path))

    return {
        "schema": "qikvrt_io_roundtrip_result_v1",
        "state": "PERSISTED",
        "envelope_id": envelope_id,
        "envelope_path": envelope_path.relative_to(ROOT).as_posix(),
        "publication": queue_record,
        "effects": effects,
        "external_effects_requested": execute_effects,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path)
    parser.add_argument("--execute-effects", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.input:
            raw = load_json(args.input)
        else:
            raw = json.load(sys.stdin)
            if not isinstance(raw, dict):
                raise ValueError("input JSON object required")
        result = process(raw, args.execute_effects)
    except Exception as exc:
        print(json.dumps({"state": "HOLD", "failure_class": "IO_ROUNDTRIP_BLOCKED", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
