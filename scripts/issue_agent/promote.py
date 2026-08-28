#!/usr/bin/env python3
"""Validate an issue-agent lifecycle disposition and classify terminal candidates.

This attests the repository processing state, not universal scientific truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.issue_agent.binding import json_loads_strict

REQUIRED = ("REQUEST.json", "REQUEST.sha256", "CONTEXT.md", "ANSWER.md", "STATUS.json")
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
    status = json_loads_strict(status_path.read_text(encoding="utf-8"))
    disposition = status.get("issue_disposition")

    if disposition not in ALLOWED_DISPOSITIONS:
        raise SystemExit("BLOCK: missing or invalid issue lifecycle disposition")
    if not answer:
        raise SystemExit("BLOCK: answer is empty")

    inference_completed = status.get("model_inference_completed") is True
    deterministic_contract_completed = status.get("deterministic_contract_completed") is True
    evaluation_completed = status.get("evaluation_completed") is True
    if evaluation_completed is not (inference_completed or deterministic_contract_completed or status.get("evaluation_mode") in {"DETERMINISTIC_REJECT", "EXTERNAL_AGENT_FAILURE"}):
        raise SystemExit("BLOCK: evaluation mode booleans are inconsistent")
    explicit_block = "## Gate result\n\nBLOCK" in answer
    observed_at = status.get("generated_at")

    if disposition in CLOSURE_DISPOSITIONS:
        if not evaluation_completed:
            raise SystemExit("BLOCK: terminal closure requires completed trusted evaluation")
        if explicit_block:
            raise SystemExit("BLOCK: terminal closure conflicts with blocking gate result")
        status.update({
            "status": "TERMINAL_CANDIDATE",
            "automatic_merge": False,
            "automatic_issue_close": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "authority_next_action": "REQUEST_EXACT_HEAD_REVIEW",
            "terminal_candidate_classified_at": observed_at,
            "no_false_pass": True,
        })
    elif disposition == "EXECUTE_NOW":
        if not (inference_completed or deterministic_contract_completed):
            raise SystemExit("BLOCK: admitted disposition requires completed model or deterministic-owner evaluation")
        if explicit_block:
            raise SystemExit("BLOCK: admitted disposition conflicts with blocking gate result")
        status.update({
            "status": "CONTINUE",
            "automatic_merge": False,
            "automatic_issue_close": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "validated_disposition_at": observed_at,
            "no_false_pass": True,
        })
    elif disposition in BLOCKING_DISPOSITIONS:
        status.update({
            "status": "BLOCK",
            "automatic_merge": False,
            "automatic_issue_close": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "validated_disposition_at": observed_at,
            "no_false_pass": True,
        })

    status_path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    args = parser.parse_args()
    promote(Path(args.directory))


if __name__ == "__main__":
    main()
