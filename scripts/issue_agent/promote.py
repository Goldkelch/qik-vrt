#!/usr/bin/env python3
"""Validate an issue-agent lifecycle disposition without terminalizing live work.

This attests the repository processing state, not universal scientific truth.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:  # module execution and direct script execution are both supported
    from .continuation import ContinuationError, build_record, validate_record, write_record
except ImportError:  # pragma: no cover - exercised by the workflow command
    from continuation import ContinuationError, build_record, validate_record, write_record

REQUIRED = (
    "REQUEST.json",
    "REQUEST.sha256",
    "CONTEXT.md",
    "ANSWER.md",
    "STATUS.json",
    "CONTINUATION.json",
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
        raise SystemExit(f"BLOCK: missing required artifacts: {', '.join(missing)}")

    answer = (directory / "ANSWER.md").read_text(encoding="utf-8").strip()
    status_path = directory / "STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    request = json.loads((directory / "REQUEST.json").read_text(encoding="utf-8"))
    continuation = json.loads((directory / "CONTINUATION.json").read_text(encoding="utf-8"))
    try:
        validate_record(continuation, request, status)
    except ContinuationError as exc:
        raise SystemExit(f"BLOCK: invalid exact continuation binding: {exc}") from exc
    disposition = status.get("issue_disposition")

    if disposition not in ALLOWED_DISPOSITIONS:
        raise SystemExit("BLOCK: missing or invalid issue lifecycle disposition")
    if not answer:
        raise SystemExit("BLOCK: answer is empty")

    inference_completed = status.get("model_inference_completed") is True
    explicit_block = "## Gate result\n\nBLOCK" in answer
    if disposition in CLOSURE_DISPOSITIONS:
        if not inference_completed:
            raise SystemExit("BLOCK: terminal closure requires completed inference")
        if explicit_block:
            raise SystemExit("BLOCK: terminal closure conflicts with blocking gate result")
        # A model's CLOSE_* assessment is a candidate disposition, not proof
        # that the requested action executed.  Keep the continuation live
        # until an exact current binding supplies one of its typed outcomes.
        status.update({
            "status": "CONTINUE",
            "next_action": "REOBSERVE_EXACT_CLOSURE_POSTCONDITION",
            "automatic_merge": False,
            "automatic_issue_close": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
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
            "no_false_pass": True,
        })
    elif disposition in BLOCKING_DISPOSITIONS:
        status.update({
            "status": "BLOCK",
            "automatic_merge": False,
            "automatic_issue_close": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "no_false_pass": True,
        })

    # A timestamp is observation transport, never a new issue work product.
    # Strip legacy volatile fields before writing the semantic status that is
    # bound into CONTINUATION.json.
    for key in (
        "generated_at",
        "validated_disposition_at",
        "validated_completion_promoted_at",
    ):
        status.pop(key, None)

    status_path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    # Promotion may change the semantic gate state (for example CONTINUE →
    # DONE).  Rebind the logical continuation in the same atomic work-unit
    # materialization so predecessor evidence cannot be transferred.
    source = continuation.get("current_binding", {}).get("source")
    if not isinstance(source, dict):
        raise SystemExit("BLOCK: continuation has no exact source binding")
    write_record(directory / "CONTINUATION.json", build_record(request, status, source=source))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    args = parser.parse_args()
    promote(Path(args.directory))


if __name__ == "__main__":
    main()
