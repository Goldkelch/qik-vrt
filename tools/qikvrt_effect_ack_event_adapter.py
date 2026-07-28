#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qikvrt_effect_ack_event_frame_v1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def classify(event_name: str, payload: dict[str, Any]) -> tuple[str, str]:
    if event_name == "workflow_run":
        run = payload.get("workflow_run") or {}
        conclusion = run.get("conclusion")
        if conclusion in {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}:
            return "BLOCK", "INSPECT_FAILED_WORKFLOW_RUN"
        if conclusion == "success":
            return "EFFECT_ACK_CONTINUE", "REOBSERVE_PRODUCTIVE_CHAIN"
    if event_name in {"push", "pull_request", "issues", "issue_comment", "release", "create", "delete", "repository_dispatch"}:
        return "EFFECT_ACK_CONTINUE", "REFRESH_REPOSITORY_CAPABILITY_AND_PROGRESS_STATE"
    return "EFFECT_ACK_CONTINUE", "CLASSIFY_UNRECOGNIZED_EVENT"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.event_path).read_text(encoding="utf-8"))
    state, next_effect = classify(args.event_name, payload)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    source = {
        "repository": args.repository,
        "event_name": args.event_name,
        "run_id": int(args.run_id),
        "run_attempt": int(args.run_attempt),
        "delivery_hint": os.environ.get("GITHUB_RUN_ID", args.run_id),
        "actor": os.environ.get("GITHUB_ACTOR"),
        "ref": os.environ.get("GITHUB_REF"),
        "sha": os.environ.get("GITHUB_SHA"),
    }
    identity_material = {"source": source, "payload": payload}
    event_digest = hashlib.sha256(canonical_json(identity_material)).hexdigest()
    event_id = f"qikvrt-{args.event_name}-{event_digest[:24]}"

    frame = {
        "schema": SCHEMA,
        "event_id": event_id,
        "observed_at": observed_at,
        "source": source,
        "state": state,
        "next_deterministic_effect": next_effect,
        "productive_progress_claimed": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
        "payload_sha256": hashlib.sha256(canonical_json(payload)).hexdigest(),
        "frame_sha256": None,
    }
    frame["frame_sha256"] = hashlib.sha256(canonical_json({k: v for k, v in frame.items() if k != "frame_sha256"})).hexdigest()

    out = Path(args.output_dir)
    frames = out / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    frame_path = frames / f"{event_id}.json"
    frame_path.write_text(json.dumps(frame, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "latest.json").write_text(json.dumps(frame, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(frame, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
