#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

REQUIRED = ("REQUEST.json", "REQUEST.sha256", "CONTEXT.md", "ANSWER.md", "STATUS.json")


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
    if gate == "DONE":
        if status.get("automatic_merge") is not True:
            raise SystemExit("DONE_REQUIRES_AUTOMATIC_MERGE")
        for key in ("automatic_issue_close", "mirror_sync_required", "common_tag_required"):
            if status.get(key) is not True:
                raise SystemExit(f"DONE_REQUIRES_{key.upper()}")
    elif status.get("automatic_merge") is not False:
        raise SystemExit("NON_DONE_MUST_NOT_AUTO_MERGE")
    if status.get("no_false_pass") is not True:
        raise SystemExit("NO_FALSE_PASS_GATE_FAILED")

    answer = (directory / "ANSWER.md").read_text(encoding="utf-8").strip()
    if not answer:
        raise SystemExit("EMPTY_ANSWER")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate.py DIRECTORY")
    validate(Path(sys.argv[1]))
