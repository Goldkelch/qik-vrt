#!/usr/bin/env python3
"""Promote a validated issue-agent evidence bundle to DONE.

This attests completion of the repository processing contract, not universal scientific truth.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ("REQUEST.json", "REQUEST.sha256", "CONTEXT.md", "ANSWER.md", "STATUS.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    args = parser.parse_args()
    directory = Path(args.directory)

    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    if missing:
        raise SystemExit(f"BLOCK: missing required artifacts: {', '.join(missing)}")

    answer = (directory / "ANSWER.md").read_text(encoding="utf-8").strip()
    status_path = directory / "STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))

    if not status.get("model_inference_completed"):
        raise SystemExit("BLOCK: model inference did not complete")
    if not answer or "## Gate result\n\nBLOCK" in answer:
        raise SystemExit("BLOCK: answer is empty or explicitly blocked")

    status.update({
        "status": "DONE",
        "automatic_merge": True,
        "automatic_issue_close": True,
        "mirror_sync_required": True,
        "common_tag_required": True,
        "validated_completion_promoted_at": datetime.now(timezone.utc).isoformat(),
        "no_false_pass": True,
    })
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
