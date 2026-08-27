# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Causal diagnostics for autonomous draft-PR continuation failures.

A terminal ``failure`` without an exact binding and a first causal reason is not
an actionable observation.  This module writes a compact machine-readable
receipt and renders the same disposition for GitHub annotations, step summaries,
and exact-subject pull-request comments.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Any, Iterable

SCHEMA = "qikvrt.autonomous-pr-continuation.failure-receipt.v1"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(token|password|secret|authorization)=([^\s]+)"
)


class FailureReceiptError(ValueError):
    """Raised when a failure receipt would not be evidence-correct."""


def _require_sha(name: str, value: str) -> str:
    normalized = value.strip().lower()
    if not _SHA_RE.fullmatch(normalized):
        raise FailureReceiptError(f"{name} must be a full lowercase commit SHA")
    return normalized


def _require_positive_int(name: str, value: int) -> int:
    if value <= 0:
        raise FailureReceiptError(f"{name} must be positive")
    return value


def _safe_text(value: str, *, limit: int = 600) -> str:
    one_line = " ".join(value.replace("\x00", "").splitlines()).strip()
    one_line = _SECRET_ASSIGNMENT_RE.sub(r"\1=***", one_line)
    if len(one_line) > limit:
        return one_line[: limit - 1] + "…"
    return one_line


def normalize_conflict_paths(paths: Iterable[str]) -> list[str]:
    normalized: set[str] = set()
    for raw in paths:
        path = raw.strip()
        if not path:
            continue
        candidate = pathlib.PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise FailureReceiptError(f"unsafe conflict path: {path!r}")
        if "\x00" in path or "\n" in path or "\r" in path:
            raise FailureReceiptError(f"invalid conflict path: {path!r}")
        normalized.add(path)
    return sorted(normalized)


def read_conflict_paths(path: pathlib.Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    return normalize_conflict_paths(path.read_text(encoding="utf-8").splitlines())


def derive_next_evidence(classification: str, branch_push_state: str) -> str:
    if classification == "NON_ALLOWLISTED_MERGE_CONFLICTS":
        return (
            "HISTORY_PRESERVING_CURRENT_MAIN_SUCCESSOR_WITH_EXPLICIT_"
            "SEMANTIC_CONFLICT_RESOLUTION_AND_EXACT_HEAD_REOBSERVATION"
        )
    if branch_push_state == "OBSERVED":
        return "EXACT_PUSHED_HEAD_REOBSERVATION_AND_TERMINAL_DISPOSITION"
    if branch_push_state == "IN_PROGRESS":
        return "LIVE_HEAD_CAS_REOBSERVATION_BEFORE_ANY_RETRY"
    return "EXACT_BOUND_CAUSAL_REPAIR_AND_FRESH_CONTINUATION_REOBSERVATION"


def build_receipt(
    *,
    repository: str,
    run_id: int,
    run_attempt: int,
    job: str,
    pr_number: int,
    head_ref: str,
    expected_head_sha: str,
    observed_base_sha: str,
    current_main_sha: str,
    classification: str,
    exit_code: int,
    failing_phase: str,
    failing_line: int | None,
    failing_command: str,
    branch_push_state: str,
    conflict_paths: Iterable[str] = (),
) -> dict[str, Any]:
    repository = repository.strip()
    if "/" not in repository or repository.startswith("/") or repository.endswith("/"):
        raise FailureReceiptError("repository must use owner/name form")
    classification = _safe_text(classification, limit=120)
    if not classification:
        raise FailureReceiptError("classification must not be empty")
    if branch_push_state not in {"NOT_ATTEMPTED", "IN_PROGRESS", "OBSERVED"}:
        raise FailureReceiptError("invalid branch push state")

    paths = normalize_conflict_paths(conflict_paths)
    expected_head = _require_sha("expected_head_sha", expected_head_sha)
    current_main = _require_sha("current_main_sha", current_main_sha)
    observed_base = _require_sha("observed_base_sha", observed_base_sha)
    pr = _require_positive_int("pr_number", pr_number)
    run = _require_positive_int("run_id", run_id)
    attempt = _require_positive_int("run_attempt", run_attempt)
    if exit_code <= 0:
        raise FailureReceiptError("exit_code must describe a failure")

    if classification == "NON_ALLOWLISTED_MERGE_CONFLICTS" and not paths:
        raise FailureReceiptError("merge-conflict classification requires paths")

    return {
        "schema": SCHEMA,
        "state": "BLOCK",
        "classification": classification,
        "binding": {
            "repository": repository,
            "pull_request": pr,
            "head_ref": head_ref.strip(),
            "expected_head_sha": expected_head,
            "observed_base_sha": observed_base,
            "current_main_sha": current_main,
        },
        "execution": {
            "run_id": run,
            "run_attempt": attempt,
            "job": job.strip(),
            "exit_code": exit_code,
            "failing_phase": _safe_text(failing_phase, limit=120),
            "failing_line": failing_line if failing_line and failing_line > 0 else None,
            "failing_command": _safe_text(failing_command),
        },
        "causal_detail": {
            "conflict_count": len(paths),
            "conflict_paths": paths,
        },
        "effects": {
            "branch_push_state": branch_push_state,
            "external_effect": "NONE",
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        },
        "next_evidence": derive_next_evidence(classification, branch_push_state),
    }


def render_annotation(receipt: dict[str, Any]) -> str:
    binding = receipt["binding"]
    detail = receipt["causal_detail"]
    classification = receipt["classification"]
    head = binding["expected_head_sha"][:12]
    main = binding["current_main_sha"][:12]
    if detail["conflict_count"]:
        cause = (
            f"{detail['conflict_count']} non-allowlisted conflict path(s)"
            if classification == "NON_ALLOWLISTED_MERGE_CONFLICTS"
            else f"{detail['conflict_count']} conflict path(s)"
        )
    else:
        cause = receipt["execution"]["failing_command"] or "command failure"
    return _safe_text(
        f"PR #{binding['pull_request']} exact head {head} blocked while bound to "
        f"main {main}: {classification} ({cause}); causal receipt preserved.",
        limit=900,
    )


def render_summary(receipt: dict[str, Any]) -> str:
    binding = receipt["binding"]
    execution = receipt["execution"]
    detail = receipt["causal_detail"]
    effects = receipt["effects"]
    lines = [
        "## Autonomous draft-PR continuation blocked",
        "",
        f"- classification: `{receipt['classification']}`",
        f"- run: `{execution['run_id']}` attempt `{execution['run_attempt']}`",
        f"- job: `{execution['job']}`",
        f"- pull request: `#{binding['pull_request']}`",
        f"- exact observed head: `{binding['expected_head_sha']}`",
        f"- observed PR base: `{binding['observed_base_sha']}`",
        f"- current main used by the run: `{binding['current_main_sha']}`",
        f"- failing phase: `{execution['failing_phase']}`",
        f"- exit code: `{execution['exit_code']}`",
        f"- branch-push state: `{effects['branch_push_state']}`",
        f"- external effect: `{effects['external_effect']}`",
    ]
    if detail["conflict_paths"]:
        lines.extend(["", "### First causal detail", ""])
        lines.extend(f"- `{path}`" for path in detail["conflict_paths"])
    elif execution["failing_command"]:
        lines.extend(
            [
                "",
                "### First causal detail",
                "",
                f"- failing command: `{execution['failing_command']}`",
            ]
        )
    lines.extend(
        [
            "",
            "### Smallest next evidence",
            "",
            f"`{receipt['next_evidence']}`",
            "",
            "No PASS, FINAL_PASS, Authority-main merge, publication, deployment, "
            "or general EFFECT_ACK_DONE is implied.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_pr_comment(receipt: dict[str, Any], *, current_head_sha: str) -> str:
    binding = receipt["binding"]
    current_head = _require_sha("current_head_sha", current_head_sha)
    observed_head = binding["expected_head_sha"]
    drift = current_head != observed_head
    marker = (
        "<!-- qikvrt-autonomous-pr-continuation-failure "
        f"run={receipt['execution']['run_id']} "
        f"attempt={receipt['execution']['run_attempt']} -->"
    )
    summary = render_summary(receipt).replace(
        "## Autonomous draft-PR continuation blocked",
        "### Autonomous continuation blocked with causal detail",
        1,
    )
    binding_note = (
        f"- current live PR head at notification: `{current_head}`\n"
        f"- binding drift after the failed run: `{'true' if drift else 'false'}`\n"
    )
    return f"{marker}\n{summary}\n{binding_note}"


def _write_text(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _cmd_write(args: argparse.Namespace) -> int:
    receipt = build_receipt(
        repository=args.repository,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        job=args.job,
        pr_number=args.pr_number,
        head_ref=args.head_ref,
        expected_head_sha=args.expected_head,
        observed_base_sha=args.observed_base,
        current_main_sha=args.current_main,
        classification=args.classification,
        exit_code=args.exit_code,
        failing_phase=args.failing_phase,
        failing_line=args.failing_line,
        failing_command=args.failing_command,
        branch_push_state=args.branch_push_state,
        conflict_paths=read_conflict_paths(args.conflicts_file),
    )
    _write_text(
        args.output,
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )
    _write_text(args.summary_output, render_summary(receipt))
    _write_text(args.annotation_output, render_annotation(receipt) + "\n")
    return 0


def _cmd_render_comment(args: argparse.Namespace) -> int:
    receipt = json.loads(args.input.read_text(encoding="utf-8"))
    if receipt.get("schema") != SCHEMA:
        raise FailureReceiptError("unsupported failure receipt schema")
    print(render_pr_comment(receipt, current_head_sha=args.current_head), end="")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    write = subparsers.add_parser("write")
    write.add_argument("--output", type=pathlib.Path, required=True)
    write.add_argument("--summary-output", type=pathlib.Path, required=True)
    write.add_argument("--annotation-output", type=pathlib.Path, required=True)
    write.add_argument("--repository", required=True)
    write.add_argument("--run-id", type=int, required=True)
    write.add_argument("--run-attempt", type=int, required=True)
    write.add_argument("--job", required=True)
    write.add_argument("--pr-number", type=int, required=True)
    write.add_argument("--head-ref", required=True)
    write.add_argument("--expected-head", required=True)
    write.add_argument("--observed-base", required=True)
    write.add_argument("--current-main", required=True)
    write.add_argument("--classification", required=True)
    write.add_argument("--exit-code", type=int, required=True)
    write.add_argument("--failing-phase", required=True)
    write.add_argument("--failing-line", type=int)
    write.add_argument("--failing-command", default="")
    write.add_argument(
        "--branch-push-state",
        choices=("NOT_ATTEMPTED", "IN_PROGRESS", "OBSERVED"),
        required=True,
    )
    write.add_argument("--conflicts-file", type=pathlib.Path)
    write.set_defaults(func=_cmd_write)

    comment = subparsers.add_parser("render-comment")
    comment.add_argument("--input", type=pathlib.Path, required=True)
    comment.add_argument("--current-head", required=True)
    comment.set_defaults(func=_cmd_render_comment)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
