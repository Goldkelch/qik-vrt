#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic Terminal assignment identity and materialization backpressure."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
ASSIGNMENT_MARKER = re.compile(
    r"<!-- qikvrt-terminal-repair-assignment:([A-Za-z0-9._-]+) -->"
)
CANDIDATE_MARKER = re.compile(
    r"<!-- qikvrt-terminal-repair-candidate:assignment=([A-Za-z0-9._-]+) "
    r"comment=([1-9][0-9]*) -->"
)
OPT_IN_MARKER = "<!-- qikvrt-autonomous-self-heal:enabled -->"
SHA1 = re.compile(r"^[0-9a-f]{40}$")
STATES = ("PENDING", "MATERIALIZED", "VERIFIED", "AUTHORITY_REQUIRED")


class AssignmentBlock(RuntimeError):
    pass


def _canonical_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(_canonical_text(value).encode("utf-8")).hexdigest()


def _exact_marker(pattern: re.Pattern[str], body: str, label: str) -> re.Match[str] | None:
    matches = list(pattern.finditer(body))
    if len(matches) > 1:
        raise AssignmentBlock(f"{label} marker is duplicated")
    return matches[0] if matches else None


def load_backpressure_contract(path: pathlib.Path = CONTRACT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    policy = value.get("terminal_assignment_backpressure")
    if not isinstance(policy, dict):
        raise AssignmentBlock("terminal assignment backpressure policy is absent")
    if policy.get("schema") != "qikvrt_terminal_assignment_backpressure_v1":
        raise AssignmentBlock("terminal assignment backpressure schema mismatch")
    if policy.get("states") != list(STATES):
        raise AssignmentBlock("terminal assignment states differ")
    anchor = policy.get("anchor_assignment")
    if not isinstance(anchor, dict):
        raise AssignmentBlock("terminal assignment anchor is absent")
    if not isinstance(anchor.get("comment_id"), int) or anchor["comment_id"] <= 0:
        raise AssignmentBlock("terminal assignment anchor comment is invalid")
    if not isinstance(anchor.get("display_id"), str) or not anchor["display_id"]:
        raise AssignmentBlock("terminal assignment anchor display id is invalid")
    return policy


def _assignment_rows(
    comments: Sequence[Mapping[str, Any]], repository: str, carrier_pr: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    display_ids: dict[str, dict[str, Any]] = {}
    collisions: list[dict[str, Any]] = []
    comment_ids: set[int] = set()
    for comment in sorted(comments, key=lambda item: item.get("id", 0)):
        comment_id = comment.get("id")
        body = comment.get("body")
        if not isinstance(comment_id, int) or comment_id <= 0 or not isinstance(body, str):
            raise AssignmentBlock("comment identity or body is invalid")
        marker = _exact_marker(ASSIGNMENT_MARKER, body, "assignment")
        if marker is None:
            continue
        if comment_id in comment_ids:
            raise AssignmentBlock(f"duplicate comment id: {comment_id}")
        comment_ids.add(comment_id)
        display_id = marker.group(1)
        subject_digest = _sha256_text(body)
        identity_payload = (
            f"{repository}\0{carrier_pr}\0{comment_id}\0{subject_digest}"
        ).encode("utf-8")
        identity = hashlib.sha256(identity_payload).hexdigest()
        row = {
            "display_id": display_id,
            "comment_id": comment_id,
            "subject_digest": subject_digest,
            "identity": identity,
        }
        previous = display_ids.get(display_id)
        if previous is not None and (
            previous["comment_id"] != comment_id
            or previous["subject_digest"] != subject_digest
        ):
            collisions.append(
                {
                    "display_id": display_id,
                    "first_comment_id": previous["comment_id"],
                    "second_comment_id": comment_id,
                    "first_subject_digest": previous["subject_digest"],
                    "second_subject_digest": subject_digest,
                }
            )
        else:
            display_ids[display_id] = row
        rows.append(row)
    return rows, collisions


def _candidate_rows(
    pulls: Sequence[Mapping[str, Any]],
    *,
    repository: str,
    assignment: Mapping[str, Any],
    carrier: Mapping[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    base_sha = carrier.get("base_sha")
    for pull in pulls:
        body = pull.get("body") or ""
        if not isinstance(body, str):
            raise AssignmentBlock("candidate pull-request body is invalid")
        marker = _exact_marker(CANDIDATE_MARKER, body, "candidate")
        if marker is None:
            continue
        if marker.group(1) != assignment["display_id"]:
            continue
        if int(marker.group(2)) != assignment["comment_id"]:
            continue
        if body.count(OPT_IN_MARKER) != 1:
            continue
        head = pull.get("head") or {}
        base = pull.get("base") or {}
        head_repo = (head.get("repo") or {}).get("full_name")
        if (
            pull.get("state") != "open"
            or pull.get("draft") is not True
            or head_repo != repository
            or base.get("ref") != "main"
            or base.get("sha") != base_sha
            or not SHA1.fullmatch(str(head.get("sha") or ""))
        ):
            continue
        result.append(
            {
                "pull_request": pull.get("number"),
                "head_ref": head.get("ref"),
                "head_sha": head.get("sha"),
                "base_sha": base.get("sha"),
            }
        )
    return sorted(result, key=lambda item: item["pull_request"])


def observe(
    *,
    policy: Mapping[str, Any],
    comments: Sequence[Mapping[str, Any]],
    pulls: Sequence[Mapping[str, Any]],
    carrier: Mapping[str, Any],
    source_run_id: int,
    source_run_attempt: int,
) -> dict[str, Any]:
    repository = policy.get("repository")
    carrier_pr = policy.get("carrier_pr")
    anchor = policy.get("anchor_assignment") or {}
    if not isinstance(repository, str) or not repository:
        raise AssignmentBlock("assignment repository is invalid")
    if not isinstance(carrier_pr, int) or carrier_pr <= 0:
        raise AssignmentBlock("assignment carrier PR is invalid")
    if carrier.get("number") != carrier_pr:
        raise AssignmentBlock("carrier PR number differs")
    for field in ("base_sha", "base_tree", "head_sha", "head_tree"):
        if not SHA1.fullmatch(str(carrier.get(field) or "")):
            raise AssignmentBlock(f"carrier {field} is invalid")
    if source_run_id <= 0 or source_run_attempt <= 0:
        raise AssignmentBlock("source run binding is invalid")

    assignments, collisions = _assignment_rows(comments, repository, carrier_pr)
    current = next(
        (
            item
            for item in assignments
            if item["comment_id"] == anchor.get("comment_id")
            and item["display_id"] == anchor.get("display_id")
        ),
        None,
    )
    if current is None:
        raise AssignmentBlock("anchor assignment is absent")
    candidates = _candidate_rows(
        pulls,
        repository=repository,
        assignment=current,
        carrier=carrier,
    )
    if len(candidates) > 1:
        state = "AUTHORITY_REQUIRED"
        blocker = "MULTIPLE_BOUND_REPAIR_CANDIDATES"
    elif candidates:
        state = "MATERIALIZED"
        blocker = None
    elif carrier.get("state") != "open":
        state = "AUTHORITY_REQUIRED"
        blocker = "CARRIER_NOT_OPEN"
    elif carrier.get("draft") is not True or carrier.get("opt_in") is not True:
        state = "AUTHORITY_REQUIRED"
        blocker = "TRUSTED_MAIN_BOOTSTRAP_REQUIRED"
    else:
        state = "PENDING"
        blocker = "REPAIR_CANDIDATE_NOT_MATERIALIZED"

    value: dict[str, Any] = {
        "schema": "qikvrt_terminal_assignment_observation_v1",
        "state": state,
        "first_blocker": blocker,
        "repository": repository,
        "carrier_pr": carrier_pr,
        "carrier": dict(carrier),
        "source_run_id": source_run_id,
        "source_run_attempt": source_run_attempt,
        "assignment": current,
        "candidates": candidates,
        "legacy_display_id_collisions": collisions,
        "next_assignment_allowed": state in {"MATERIALIZED", "VERIFIED", "AUTHORITY_REQUIRED"},
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    value["receipt_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return value


def reconcile(
    controller: Mapping[str, Any], observation: Mapping[str, Any]
) -> dict[str, Any]:
    value = dict(controller)
    value["terminal_assignment"] = dict(observation)
    if value.get("state") == "NOOP" and observation.get("state") != "VERIFIED":
        value["state"] = observation["state"]
        if observation.get("first_blocker") is not None:
            value["failure_class"] = observation["first_blocker"]
    return value


def _load(path: str) -> Any:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    observe_parser = subparsers.add_parser("observe")
    observe_parser.add_argument("--comments", required=True)
    observe_parser.add_argument("--pulls", required=True)
    observe_parser.add_argument("--carrier", required=True)
    observe_parser.add_argument("--source-run-id", type=int, required=True)
    observe_parser.add_argument("--source-run-attempt", type=int, required=True)
    observe_parser.add_argument("--output", required=True)
    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("--controller", required=True)
    reconcile_parser.add_argument("--observation", required=True)
    reconcile_parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "observe":
            value = observe(
                policy=load_backpressure_contract(),
                comments=_load(args.comments),
                pulls=_load(args.pulls),
                carrier=_load(args.carrier),
                source_run_id=args.source_run_id,
                source_run_attempt=args.source_run_attempt,
            )
        else:
            value = reconcile(_load(args.controller), _load(args.observation))
    except (OSError, ValueError, json.JSONDecodeError, AssignmentBlock) as exc:
        value = {
            "schema": "qikvrt_terminal_assignment_observation_v1",
            "state": "AUTHORITY_REQUIRED",
            "first_blocker": "TERMINAL_ASSIGNMENT_OBSERVATION_BLOCKED",
            "detail": str(exc),
            "external_effect": "NONE",
        }
        pathlib.Path(args.output).write_text(
            json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        return 2
    pathlib.Path(args.output).write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
