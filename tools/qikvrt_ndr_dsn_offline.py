#!/usr/bin/env python3
"""Offline, fail-closed DSN/NDR classifier.

No network access and no external side effects.  The parser prefers structured
delivery-status MIME parts over subject/body heuristics and keeps one result per
recipient.  It deliberately does not claim that an NDR is authentic merely
because it parses successfully.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from email import policy
from email.parser import BytesParser
from typing import Iterable

STATUS_RE = re.compile(r"^[245]\.\d{1,3}\.\d{1,3}$")
ACTION_VALUES = {"delivered", "delayed", "failed", "relayed", "expanded"}
MAX_BYTES = 2 * 1024 * 1024
MAX_PARTS = 128
MAX_RECIPIENTS = 1000


@dataclass(frozen=True)
class RecipientResult:
    final_recipient: str | None
    original_recipient: str | None
    action: str | None
    status: str | None
    status_class: str
    disposition: str
    retry_by_application: bool
    evidence: str


def _value(block, name: str) -> str | None:
    value = block.get(name)
    return str(value).strip() if value is not None else None


def _recipient(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[-1].strip()


def _status_class(status: str | None) -> str:
    if not status or not STATUS_RE.match(status):
        return "UNKNOWN"
    return {"2": "SUCCESS", "4": "TRANSIENT", "5": "PERMANENT"}[status[0]]


def _disposition(action: str | None, status: str | None) -> tuple[str, bool]:
    # RFC 3464 Action is the attempt outcome.  A failed 4.x.x DSN is terminal
    # for that attempt even though the diagnostic class is transient.
    if action == "failed":
        return "ATTEMPT_FAILED", False
    if action == "delayed":
        return "MTA_RETRY_IN_PROGRESS", False
    if action == "delivered":
        return "DELIVERY_REPORTED", False
    if action in {"relayed", "expanded"}:
        return "INTERMEDIATE_SUCCESS", False
    return "MANUAL_REVIEW", False


def _iter_delivery_blocks(msg) -> Iterable:
    part_count = 0
    for part in msg.walk():
        part_count += 1
        if part_count > MAX_PARTS:
            raise ValueError("MIME_PART_LIMIT_EXCEEDED")
        if part.get_content_type() not in {
            "message/delivery-status",
            "message/global-delivery-status",
        }:
            continue
        payload = part.get_payload()
        if isinstance(payload, list):
            # First block is per-message metadata; following blocks are
            # per-recipient according to the DSN media format.
            for block in payload[1:]:
                yield block


def classify(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError("MESSAGE_SIZE_LIMIT_EXCEEDED")
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    results: list[RecipientResult] = []
    for block in _iter_delivery_blocks(msg):
        if len(results) >= MAX_RECIPIENTS:
            raise ValueError("RECIPIENT_LIMIT_EXCEEDED")
        action = (_value(block, "Action") or "").lower() or None
        status = _value(block, "Status")
        if action not in ACTION_VALUES:
            action = None
        disposition, app_retry = _disposition(action, status)
        results.append(
            RecipientResult(
                final_recipient=_recipient(_value(block, "Final-Recipient")),
                original_recipient=_recipient(_value(block, "Original-Recipient")),
                action=action,
                status=status,
                status_class=_status_class(status),
                disposition=disposition,
                retry_by_application=app_retry,
                evidence="STRUCTURED_DSN",
            )
        )

    structured = bool(results)
    # Heuristics are detection hints only. They never manufacture a status,
    # recipient, authenticity claim, or delivery result.
    subject = str(msg.get("Subject", ""))
    heuristic = bool(re.search(
        r"(?i)\b(undeliverable|unzustellbar|delivery status notification|"
        r"returned mail|failure notice|nicht zugestellt|zustellfehler)\b",
        subject,
    ))
    return {
        "schema_version": "qikvrt.ndr-dsn.offline-classifier.v1",
        "structured_dsn": structured,
        "heuristic_ndr_hint": heuristic,
        "authenticity": "UNVERIFIED",
        "correlation": "UNRESOLVED",
        "application_resend_authorized": False,
        "recipients": [asdict(x) for x in results],
        "overall": (
            "CLASSIFIED_STRUCTURED_DSN"
            if structured
            else "MANUAL_REVIEW" if heuristic
            else "NOT_IDENTIFIED_AS_DSN"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", help="RFC 5322/MIME message file")
    args = parser.parse_args()
    try:
        raw = open(args.message, "rb").read(MAX_BYTES + 1)
        result = classify(raw)
    except (OSError, ValueError) as exc:
        print(json.dumps({"overall": "CONTROLLED_ERROR", "error": str(exc)}))
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
