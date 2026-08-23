#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Promote an issue disposition without crossing a platform-effect boundary."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = (
    "REQUEST.json",
    "REQUEST.sha256",
    "CONTEXT.md",
    "ANSWER.md",
    "STATUS.json",
)
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
        raise SystemExit(
            f"BLOCK: missing required artifacts: {', '.join(missing)}"
        )

    answer = (directory / "ANSWER.md").read_text(encoding="utf-8").strip()
    status_path = directory / "STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    disposition = status.get("issue_disposition")

    if disposition not in ALLOWED_DISPOSITIONS:
        raise SystemExit(
            "BLOCK: missing or invalid issue lifecycle disposition"
        )
    if not answer:
        raise SystemExit("BLOCK: answer is empty")

    inference_completed = status.get("model_inference_completed") is True
    explicit_block = "## Gate result\n\nBLOCK" in answer
    publication_required = status.get("publication_required") is True
    publication_state = status.get("publication_state", "NOT_REQUESTED")
    now = datetime.now(timezone.utc).isoformat()

    if disposition in CLOSURE_DISPOSITIONS:
        if not inference_completed:
            raise SystemExit(
                "BLOCK: terminal closure requires completed inference"
            )
        if explicit_block:
            raise SystemExit(
                "BLOCK: terminal closure conflicts with blocking gate result"
            )
        if publication_required and publication_state != "PUBLIC_VERIFIED":
            status.update(
                {
                    "status": "CONTINUE",
                    "issue_disposition": "EXECUTE_NOW",
                    "disposition_reason": "PLATFORM_PUBLICATION_READY",
                    "next_action": (
                        "Execute the exact manifest-bound platform publication, "
                        "reobserve the public bytes and commit the effect receipt."
                    ),
                    "closure_recommended": False,
                    "automatic_merge": False,
                    "automatic_issue_close": False,
                    "mirror_sync_required": False,
                    "common_tag_required": False,
                    "effect_ack_done": False,
                    "validated_disposition_at": now,
                    "no_false_pass": True,
                }
            )
        else:
            status.update(
                {
                    "status": "DONE",
                    "automatic_merge": True,
                    "automatic_issue_close": True,
                    "mirror_sync_required": True,
                    "common_tag_required": True,
                    "effect_ack_done": bool(publication_required),
                    "validated_completion_promoted_at": now,
                    "no_false_pass": True,
                }
            )
    elif disposition == "EXECUTE_NOW":
        if not inference_completed and not status.get("work_unit_state"):
            raise SystemExit(
                "BLOCK: executable disposition requires inference or a "
                "deterministic work-unit state"
            )
        if explicit_block:
            raise SystemExit(
                "BLOCK: executable disposition conflicts with blocking gate result"
            )
        status.update(
            {
                "status": "CONTINUE",
                "automatic_merge": False,
                "automatic_issue_close": False,
                "mirror_sync_required": False,
                "common_tag_required": False,
                "effect_ack_done": False,
                "validated_disposition_at": now,
                "no_false_pass": True,
            }
        )
    elif disposition in BLOCKING_DISPOSITIONS:
        status.update(
            {
                "status": "BLOCK",
                "automatic_merge": False,
                "automatic_issue_close": False,
                "mirror_sync_required": False,
                "common_tag_required": False,
                "effect_ack_done": False,
                "validated_disposition_at": now,
                "no_false_pass": True,
            }
        )

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
