#!/usr/bin/env python3
"""Validate an issue-agent lifecycle disposition and promote only terminal closures.

This attests the repository processing state, not universal scientific truth.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = ("REQUEST.json", "REQUEST.sha256", "CONTEXT.md", "ANSWER.md", "STATUS.json")
ALLOWED_DISPOSITIONS = {
    "EXECUTE_NOW",
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}
CLOSURE_DISPOSITIONS = {
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}
BLOCKING_DISPOSITIONS = {
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
}


def promote(directory: Path) -> None:
    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    if missing:
        raise SystemExit(f"BLOCK: missing required artifacts: {', '.join(missing)}")

    answer = (directory / "ANSWER.md").read_text(encoding="utf-8").strip()
    status_path = directory / "STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    disposition = status.get("issue_disposition")

    if disposition not in ALLOWED_DISPOSITIONS:
        raise SystemExit("BLOCK: missing or invalid issue lifecycle disposition")
    if not answer:
        raise SystemExit("BLOCK: answer is empty")

    inference_completed = status.get("model_inference_completed") is True
    explicit_block = "## Gate result\n\nBLOCK" in answer
    observed_at = status.get("generated_at")
    if not isinstance(observed_at, str) or not observed_at:
        raise SystemExit("BLOCK: deterministic issue transaction timestamp is missing")

    if disposition in CLOSURE_DISPOSITIONS:
        if not inference_completed:
            raise SystemExit("BLOCK: terminal closure requires completed inference")
        if explicit_block:
            raise SystemExit("BLOCK: terminal closure conflicts with blocking gate result")
        status.update({
            "status": "DONE",
            "automatic_merge": True,
            "automatic_issue_close": True,
            "mirror_sync_required": True,
            "common_tag_required": True,
            "validated_completion_promoted_at": observed_at,
            "no_false_pass": True,
        })
    elif disposition == "EXECUTE_NOW":
        if not inference_completed:
            raise SystemExit("BLOCK: executable disposition requires completed inference")
        if explicit_block:
            raise SystemExit("BLOCK: executable disposition conflicts with blocking gate result")
        status.update({
            "status": "CONTINUE",
            "automatic_merge": False,
            "automatic_issue_close": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "validated_disposition_at": observed_at,
            "no_false_pass": True,
        })
    elif disposition in BLOCKING_DISPOSITIONS:
        status.update({
            "status": "BLOCK",
            "automatic_merge": False,
            "automatic_issue_close": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "validated_disposition_at": observed_at,
            "no_false_pass": True,
        })

    status_path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    args = parser.parse_args()
    promote(Path(args.directory))


if __name__ == "__main__":
    main()
