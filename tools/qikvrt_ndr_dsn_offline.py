#!/usr/bin/env python3
"""Bounded offline DSN classifier. Output is INTERNAL, not a public issue payload.

Parsing authenticates neither the reporter nor the original send attempt.
No network, resend, address deactivation or other external action is performed.
Internationalized DSNs are recognized but routed to review, not silently lost.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser

STATUS_RE = re.compile(r"[245]\.[0-9]{1,3}\.[0-9]{1,3}")
TYPED_RE = re.compile(r"([A-Za-z0-9-]+);[ \t]*(\S[^\r\n]*)")
ACTION_CLASSES = {
    "failed": "45", "delayed": "4", "delivered": "2",
    "relayed": "2", "expanded": "2",
}
DISPOSITIONS = {
    "failed": "ATTEMPT_FAILED", "delayed": "MTA_RETRY_IN_PROGRESS",
    "delivered": "DELIVERY_REPORTED", "relayed": "INTERMEDIATE_SUCCESS",
    "expanded": "INTERMEDIATE_SUCCESS",
}
STATUS_SUBJECTS = {
    "0": "UNDEFINED", "1": "ADDRESS", "2": "MAILBOX", "3": "MAIL_SYSTEM",
    "4": "NETWORK_ROUTING", "5": "PROTOCOL", "6": "CONTENT_MEDIA",
    "7": "SECURITY_POLICY",
}
MAX_BYTES = 2 * 1024 * 1024
# Includes per-recipient DSN blocks: enforced during allocation, before walk().
MAX_PARSE_OBJECTS = 128
MAX_DEPTH = 16
MAX_RECIPIENTS = 100
DSN_TYPES = {"message/delivery-status", "message/global-delivery-status"}


def _single(block, name: str, issues: list[str], *, required: bool = True):
    values = block.get_all(name, [])
    if len(values) != 1:
        if required or len(values) > 1:
            issues.append("FIELD_COUNT:" + name)
        return None
    value = str(values[0]).strip()
    if not value or any(ord(c) < 32 and c != "\t" for c in value):
        issues.append("FIELD_VALUE:" + name)
        return None
    return value


def _typed(value, name: str, issues: list[str]):
    if value is None:
        return None
    match = TYPED_RE.fullmatch(value)
    if not match:
        issues.append("TYPED_FIELD:" + name)
        return None
    return match.group(2).strip()


def _recipient(block, inherited: list[str]) -> dict:
    issues = list(inherited)
    final = _typed(_single(block, "Final-Recipient", issues), "Final-Recipient", issues)
    original = _typed(_single(block, "Original-Recipient", issues, required=False),
                      "Original-Recipient", issues)
    action = _single(block, "Action", issues)
    action = action.lower() if action else None
    status = _single(block, "Status", issues)
    valid_status = bool(status and STATUS_RE.fullmatch(status))
    if action not in ACTION_CLASSES:
        issues.append("INVALID_ACTION")
    if not valid_status:
        issues.append("INVALID_STATUS")
    elif action in ACTION_CLASSES and status[0] not in ACTION_CLASSES[action]:
        issues.append("ACTION_STATUS_CONFLICT")
    return {
        "final_recipient": final,
        "original_recipient": original,
        "action": action,
        "status": status,
        "status_class": ({"2": "SUCCESS", "4": "TRANSIENT", "5": "PERMANENT"}
                         [status[0]] if valid_status else "UNKNOWN"),
        "status_subject": (STATUS_SUBJECTS.get(status.split(".")[1], "UNKNOWN")
                           if valid_status else "UNKNOWN"),
        "disposition": DISPOSITIONS[action] if not issues else "MANUAL_REVIEW",
        "retry_by_application": False,
        "evidence": "STRUCTURED_DSN_UNVERIFIED_REPORT",
        "issues": sorted(set(issues)),
    }


def classify(raw: bytes) -> dict:
    """Classify bounded bytes; ValueError denotes a resource or parse failure.

    The input cap and allocation cap are enforced before unbounded MIME walking.
    This library does not claim a hard real-time deadline or raw-mail retention.
    """
    if not isinstance(raw, bytes):
        raise TypeError("MESSAGE_MUST_BE_BYTES")
    if len(raw) > MAX_BYTES:
        raise ValueError("MESSAGE_SIZE_LIMIT_EXCEEDED")
    allocated = 0

    def factory(*args, **kwargs):
        nonlocal allocated
        allocated += 1
        if allocated > MAX_PARSE_OBJECTS:
            raise ValueError("MIME_OBJECT_LIMIT_EXCEEDED")
        return EmailMessage(*args, **kwargs)

    try:
        msg = BytesParser(_class=factory, policy=policy.default).parsebytes(raw)
    except RecursionError as exc:
        raise ValueError("MIME_RECURSION_LIMIT_EXCEEDED") from exc
    parts = []
    pending = [(msg, 0)]
    envelope_issues: list[str] = []
    while pending:
        part, depth = pending.pop()
        if depth > MAX_DEPTH:
            raise ValueError("MIME_DEPTH_LIMIT_EXCEEDED")
        parts.append(part)
        if part.defects:
            envelope_issues.append("MALFORMED_MIME")
        for field in ("Content-Type", "Content-Transfer-Encoding", "MIME-Version"):
            if len(part.get_all(field, [])) > 1:
                envelope_issues.append("AMBIGUOUS_MIME_HEADER:" + field)
        payload = part.get_payload()
        if isinstance(payload, list):
            pending.extend((child, depth + 1) for child in reversed(payload))

    recipients = []
    issues = list(envelope_issues)
    structured = False
    for part in parts:
        media_type = part.get_content_type()
        if media_type not in DSN_TYPES:
            continue
        structured = True
        if media_type == "message/global-delivery-status":
            # CPython treats this as generic message/*, not delivery-status blocks.
            # Preserve the exact input digest; do not claim lossless EAI parsing.
            issues.append("GLOBAL_DSN_REQUIRES_REVIEW")
            continue
        payload = part.get_payload()
        if not isinstance(payload, list) or len(payload) < 2:
            issues.append("MISSING_DSN_RECIPIENT_BLOCK")
            continue
        metadata_issues = list(envelope_issues)
        _typed(_single(payload[0], "Reporting-MTA", metadata_issues),
               "Reporting-MTA", metadata_issues)
        _single(payload[0], "Original-Envelope-ID", metadata_issues, required=False)
        issues.extend(metadata_issues)
        for block in payload[1:]:
            if len(recipients) >= MAX_RECIPIENTS:
                raise ValueError("RECIPIENT_LIMIT_EXCEEDED")
            result = _recipient(block, metadata_issues)
            recipients.append(result)
            issues.extend(result["issues"])

    subject = str(msg.get("Subject", ""))
    hint = bool(re.search(
        r"(?i)\b(undeliverable|unzustellbar|delivery status notification|"
        r"returned mail|failure notice|nicht zugestellt|zustellfehler)\b", subject))
    overall = "NOT_IDENTIFIED_AS_DSN"
    if issues or (hint and not structured) or (structured and not recipients):
        overall = "MANUAL_REVIEW"
    elif structured:
        overall = "CLASSIFIED_STRUCTURED_DSN"
    return {
        "schema_version": "qikvrt.ndr-dsn.offline-classifier.v1",
        "data_classification": "INTERNAL_SENSITIVE",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "structured_dsn": structured,
        "heuristic_ndr_hint": hint,
        "authenticity": "UNVERIFIED",
        "correlation": "UNRESOLVED",
        "application_resend_authorized": False,
        "communication_effect_ack_done": False,
        "recipients": recipients,
        "issues": sorted(set(issues)),
        "overall": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", help="RFC 5322/MIME message file (internal data)")
    args = parser.parse_args()
    try:
        with open(args.message, "rb") as stream:
            result = classify(stream.read(MAX_BYTES + 1))
    except OSError:
        print(json.dumps({"overall": "CONTROLLED_ERROR", "error": "INPUT_READ_FAILED"}))
        return 2
    except ValueError as exc:
        print(json.dumps({"overall": "CONTROLLED_ERROR", "error": str(exc)}))
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 1 if result["overall"] == "MANUAL_REVIEW" else 0


if __name__ == "__main__":
    raise SystemExit(main())
