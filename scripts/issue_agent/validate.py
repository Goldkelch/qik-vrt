#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

try:  # module execution and direct script execution are both supported
    from .continuation import ContinuationError, validate_record
except ImportError:  # pragma: no cover - exercised by the workflow command
    from continuation import ContinuationError, validate_record

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


def validate(directory: Path) -> None:
    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    if missing:
        raise SystemExit(f"Missing issue-agent artifacts: {', '.join(missing)}")

    request_bytes = (directory / "REQUEST.json").read_bytes()
    digest_line = (directory / "REQUEST.sha256").read_text(encoding="utf-8").strip()
    expected = digest_line.split()[0]
    actual = hashlib.sha256(request_bytes).hexdigest()
    if expected != actual:
        raise SystemExit("REQUEST_SHA256_MISMATCH")

    request_data = json.loads(request_bytes)
    if not isinstance(request_data.get("issue_number"), int):
        raise SystemExit("INVALID_ISSUE_NUMBER")

    status = json.loads((directory / "STATUS.json").read_text(encoding="utf-8"))
    gate = status.get("status")
    if gate not in {"DONE", "CONTINUE", "ISOLATE", "BLOCK"}:
        raise SystemExit("INVALID_GATE_STATUS")

    disposition = status.get("issue_disposition")
    if disposition not in ALLOWED_DISPOSITIONS:
        raise SystemExit("INVALID_OR_MISSING_ISSUE_DISPOSITION")
    if not isinstance(status.get("disposition_reason"), str) or not status["disposition_reason"].strip():
        raise SystemExit("MISSING_DISPOSITION_REASON")
    if not isinstance(status.get("next_action"), str) or not status["next_action"].strip():
        raise SystemExit("MISSING_NEXT_ACTION")
    if disposition not in CLOSURE_DISPOSITIONS and status["next_action"].strip().upper() == "NONE":
        raise SystemExit("NON_CLOSURE_REQUIRES_NEXT_ACTION")
    if status.get("closure_recommended") is not (disposition in CLOSURE_DISPOSITIONS):
        raise SystemExit("CLOSURE_RECOMMENDATION_MISMATCH")

    if gate == "DONE":
        if status.get("automatic_merge") is not True:
            raise SystemExit("DONE_REQUIRES_AUTOMATIC_MERGE")
        for key in ("automatic_issue_close", "mirror_sync_required", "common_tag_required"):
            if status.get(key) is not True:
                raise SystemExit(f"DONE_REQUIRES_{key.upper()}")
    else:
        if status.get("automatic_merge") is not False:
            raise SystemExit("NON_DONE_MUST_NOT_AUTO_MERGE")
        if status.get("automatic_issue_close") is not False:
            raise SystemExit("NON_DONE_MUST_NOT_AUTO_CLOSE_ISSUE")
    if status.get("no_false_pass") is not True:
        raise SystemExit("NO_FALSE_PASS_GATE_FAILED")

    try:
        continuation = json.loads((directory / "CONTINUATION.json").read_text(encoding="utf-8"))
        validate_record(continuation, request_data, status)
    except (ContinuationError, json.JSONDecodeError) as exc:
        raise SystemExit(f"INVALID_CONTINUATION_BINDING: {exc}") from exc

    answer = (directory / "ANSWER.md").read_text(encoding="utf-8").strip()
    if not answer:
        raise SystemExit("EMPTY_ANSWER")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate.py DIRECTORY")
    validate(Path(sys.argv[1]))
