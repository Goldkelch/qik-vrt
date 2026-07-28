#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "tools" / "qikvrt_effect_ack_event_adapter.py"


def run_case(event_name: str, payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        event_path = tmp_path / "event.json"
        output = tmp_path / "out"
        event_path.write_text(json.dumps(payload), encoding="utf-8")
        subprocess.run(
            [
                "python3",
                "-B",
                str(ADAPTER),
                "--event-name",
                event_name,
                "--event-path",
                str(event_path),
                "--repository",
                "Goldkelch/qik-vrt",
                "--run-id",
                "123",
                "--run-attempt",
                "1",
                "--output-dir",
                str(output),
            ],
            check=True,
        )
        frame = json.loads((output / "latest.json").read_text(encoding="utf-8"))
        assert (output / "frames" / f"{frame['event_id']}.json").exists()
        return frame


def main() -> int:
    push = run_case("push", {"ref": "refs/heads/main", "after": "a" * 40})
    assert push["state"] == "EFFECT_ACK_CONTINUE"
    assert push["next_deterministic_effect"] == "REFRESH_REPOSITORY_CAPABILITY_AND_PROGRESS_STATE"
    assert push["pass"] is False
    assert push["final_pass"] is False
    assert push["effect_ack_done"] is False
    assert len(push["payload_sha256"]) == 64
    assert len(push["frame_sha256"]) == 64

    failed = run_case("workflow_run", {"workflow_run": {"conclusion": "failure"}})
    assert failed["state"] == "BLOCK"
    assert failed["next_deterministic_effect"] == "INSPECT_FAILED_WORKFLOW_RUN"

    succeeded = run_case("workflow_run", {"workflow_run": {"conclusion": "success"}})
    assert succeeded["state"] == "EFFECT_ACK_CONTINUE"
    assert succeeded["productive_progress_claimed"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
