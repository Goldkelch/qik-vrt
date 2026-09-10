#!/usr/bin/env python3
"""Compile a bounded issue into a deterministic QIK-VRT disposition.

This deliberately does not interpret arbitrary prose as a patch request.  An
unrecognised request is materialised as a precise HOLD rather than delegated to
an external model.
"""
import argparse
import json
from pathlib import Path


def disposition(issue: dict) -> tuple[str, str]:
    text = "\n".join(str(issue.get(key, "")) for key in ("title", "body")).lower()
    if "ruleset" in text and "github app" in text:
        return (
            "MISSING_GITHUB_APP_RULESET_AUTHORITY",
            "Configure the repository-scoped GitHub App authority declared by the bound work unit, then trigger one native issue event.",
        )
    return (
        "UNSUPPORTED_DETERMINISTIC_WORK_UNIT",
        "Add a schema-validated, allowlisted work-unit handler and trigger one native issue event.",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    issue = json.loads(Path(args.issue).read_text(encoding="utf-8"))
    reason, next_action = disposition(issue)
    Path(args.output).write_text(
        "# Deterministic repository work-unit result\n\n"
        "## Evidence used\n\n"
        "Exact GitHub issue payload and bounded repository context only.\n\n"
        "## Formal status\n\nNOT_EVALUATED\n\n"
        "## Empirical status\n\nNOT_EVALUATED\n\n"
        "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
        f"## Disposition reason\n\n{reason}\n\n"
        f"## Required next action\n\n{next_action}\n\n"
        "## Gate result\n\nBLOCK\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
