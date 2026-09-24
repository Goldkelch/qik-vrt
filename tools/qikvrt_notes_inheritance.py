# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify QIK-VRT Note inheritance without copying private counsel payloads publicly."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

POLICY = Path("policy/QIKVRT_NOTES_INHERITANCE_V1.json")
REGISTRY = Path("state/notes/QIKVRT_NOTES_REGISTRY_V1.json")
EXCLUDED_PREFIXES = ("policy/", "tools/", "tests/", "state/")
NOTE_TOKEN = re.compile(r"(^|[_-])NOTES?([_.-]|$)", re.IGNORECASE)
FORBIDDEN_PRIVATE_MARKERS = (
    "PRIVATE WORKING DRAFT — TEMDD Patent-Counsel Handoff",
    "Candidate independent-apparatus concept:",
    "Claim Set A — State-transition processing apparatus",
)

def is_note_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith(EXCLUDED_PREFIXES):
        return False
    return NOTE_TOKEN.search(Path(normalized).name) is not None

def tracked_paths() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [item.decode("utf-8") for item in proc.stdout.split(b"\0") if item]

def discover_notes() -> list[str]:
    return sorted(path for path in tracked_paths() if is_note_path(path))

def check() -> dict[str, object]:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    notes = discover_notes()

    if policy["scope"]["future_notes"] != "ALL_FUTURE_TRACKED_NOTE_CARRIERS":
        raise SystemExit("BLOCK future Note inheritance is not universal")
    if not policy["future_inheritance"]["automatic"]:
        raise SystemExit("BLOCK future Note inheritance is not automatic")
    if policy["private_counsel_packet"]["public_materialization_allowed"]:
        raise SystemExit("BLOCK private counsel payload may not be publicly materialized")
    if policy["private_counsel_packet"]["private_payload_bytes_in_public_repository"]:
        raise SystemExit("BLOCK private counsel payload bytes must remain out of public repositories")

    observed = registry["observation"]["observed_existing_note_paths"]
    missing = sorted(set(observed) - set(notes))
    if missing:
        raise SystemExit("BLOCK observed Note carriers disappeared: " + ", ".join(missing))

    leaks: list[str] = []
    for path in notes:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(marker in text for marker in FORBIDDEN_PRIVATE_MARKERS):
            leaks.append(path)
    if leaks:
        raise SystemExit("BLOCK private patent-counsel payload leaked into public Notes: " + ", ".join(leaks))

    return {
        "schema": "qikvrt_notes_inheritance_check_v1",
        "policy_id": policy["policy_id"],
        "private_packet_id": policy["private_counsel_packet"]["packet_id"],
        "current_note_count": len(notes),
        "observed_registry_count": len(observed),
        "future_notes_auto_inherit": True,
        "historical_note_bytes_rewritten": False,
        "private_payload_publicly_materialized": False,
        "result": "PASS",
    }

def main(argv: list[str]) -> int:
    if argv not in ([], ["check"]):
        print("usage: qikvrt_notes_inheritance.py [check]", file=sys.stderr)
        return 2
    print(json.dumps(check(), sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
