#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate issue-agent evidence, including the platform-publication boundary."""
from __future__ import annotations

import hashlib
import json
import sys
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


def validate(directory: Path) -> None:
    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    if missing:
        raise SystemExit(
            f"Missing issue-agent artifacts: {', '.join(missing)}"
        )

    request_bytes = (directory / "REQUEST.json").read_bytes()
    digest_line = (
        directory / "REQUEST.sha256"
    ).read_text(encoding="utf-8").strip()
    expected = digest_line.split()[0]
    actual = hashlib.sha256(request_bytes).hexdigest()
    if expected != actual:
        raise SystemExit("REQUEST_SHA256_MISMATCH")

    request_data = json.loads(request_bytes)
    if not isinstance(request_data.get("issue_number"), int):
        raise SystemExit("INVALID_ISSUE_NUMBER")

    status = json.loads(
        (directory / "STATUS.json").read_text(encoding="utf-8")
    )
    gate = status.get("status")
    if gate not in {"DONE", "CONTINUE", "ISOLATE", "BLOCK"}:
        raise SystemExit("INVALID_GATE_STATUS")

    disposition = status.get("issue_disposition")
    if disposition not in ALLOWED_DISPOSITIONS:
        raise SystemExit("INVALID_OR_MISSING_ISSUE_DISPOSITION")
    reason = status.get("disposition_reason")
    if not isinstance(reason, str) or not reason.strip():
        raise SystemExit("MISSING_DISPOSITION_REASON")
    next_action = status.get("next_action")
    if not isinstance(next_action, str) or not next_action.strip():
        raise SystemExit("MISSING_NEXT_ACTION")
    if (
        disposition not in CLOSURE_DISPOSITIONS
        and next_action.strip().upper() == "NONE"
    ):
        raise SystemExit("NON_CLOSURE_REQUIRES_NEXT_ACTION")
    if status.get("closure_recommended") is not (
        disposition in CLOSURE_DISPOSITIONS
    ):
        raise SystemExit("CLOSURE_RECOMMENDATION_MISMATCH")

    publication_required = status.get("publication_required") is True
    publication_state = status.get("publication_state", "NOT_REQUESTED")
    if publication_required and publication_state not in {
        "READY",
        "PUBLIC_VERIFIED",
        "WAITING_INTERNAL",
        "INVALID",
    }:
        raise SystemExit("INVALID_PUBLICATION_STATE")
    if (
        publication_required
        and publication_state == "READY"
        and gate == "DONE"
    ):
        raise SystemExit("READY_PUBLICATION_MUST_NOT_BE_DONE")
    if publication_required and gate == "DONE":
        if publication_state != "PUBLIC_VERIFIED":
            raise SystemExit(
                "PUBLICATION_REQUIRED_DONE_REQUIRES_PUBLIC_VERIFIED"
            )
        receipt_path = status.get("publication_effect_receipt")
        if (
            not isinstance(receipt_path, str)
            or not receipt_path
            or not (directory.parent.parent.parent / receipt_path).is_file()
        ):
            raise SystemExit(
                "PUBLICATION_REQUIRED_DONE_REQUIRES_EFFECT_RECEIPT"
            )
        if status.get("effect_ack_done") is not True:
            raise SystemExit(
                "PUBLICATION_REQUIRED_DONE_REQUIRES_EFFECT_ACK_DONE"
            )
    elif status.get("effect_ack_done") is True:
        raise SystemExit("NON_DONE_MUST_NOT_CLAIM_EFFECT_ACK_DONE")

    if gate == "DONE":
        if status.get("automatic_merge") is not True:
            raise SystemExit("DONE_REQUIRES_AUTOMATIC_MERGE")
        for key in (
            "automatic_issue_close",
            "mirror_sync_required",
            "common_tag_required",
        ):
            if status.get(key) is not True:
                raise SystemExit(f"DONE_REQUIRES_{key.upper()}")
    else:
        if status.get("automatic_merge") is not False:
            raise SystemExit("NON_DONE_MUST_NOT_AUTO_MERGE")
        if status.get("automatic_issue_close") is not False:
            raise SystemExit("NON_DONE_MUST_NOT_AUTO_CLOSE_ISSUE")
        if status.get("mirror_sync_required") is True:
            raise SystemExit("NON_DONE_MUST_NOT_REQUIRE_MIRROR_SYNC")
        if status.get("common_tag_required") is True:
            raise SystemExit("NON_DONE_MUST_NOT_REQUIRE_COMMON_TAG")

    if status.get("no_false_pass") is not True:
        raise SystemExit("NO_FALSE_PASS_GATE_FAILED")

    answer = (directory / "ANSWER.md").read_text(encoding="utf-8").strip()
    if not answer:
        raise SystemExit("EMPTY_ANSWER")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate.py DIRECTORY")
    validate(Path(sys.argv[1]))
