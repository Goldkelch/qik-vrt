# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.issue_agent.continuation import (
    ContinuationError,
    build_record,
    materialize,
    semantic_request,
    should_resume,
    validate_record,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = {
    "repository": "Goldkelch/qik-vrt",
    "ref": "refs/heads/main",
    "head_sha": "4ea0491a5484075215f17dbcd157a2a5f18ef633",
    "tree_sha": "2f3a9ba1bbc645037a937614700e606ac99ebe58",
}


def issue(*, body: str = "Bounded body.", updated_at: str = "2026-08-30T12:01:00Z") -> dict[str, object]:
    return {
        "number": 888,
        "title": "Avoid reflexive retry loops",
        "body": body,
        "user": {"login": "ingolf-lohmann"},
        "html_url": "https://github.com/Goldkelch/qik-vrt/issues/888",
        "created_at": "2026-08-30T12:00:00Z",
        "updated_at": updated_at,
    }


def status(*, generated_at: str = "2026-08-30T12:02:00Z", next_action: str = "Reobserve model admission.") -> dict[str, object]:
    return {
        "status": "BLOCK",
        "model_inference_completed": False,
        "issue_disposition": "BLOCKED_WITH_NEXT_ACTION",
        "disposition_reason": "MODEL_INFERENCE_UNAVAILABLE",
        "next_action": next_action,
        "closure_recommended": False,
        "automatic_issue_close": False,
        "automatic_merge": False,
        "generated_at": generated_at,
        "no_false_pass": True,
    }


class IssueContinuationTests(unittest.TestCase):
    repository = "Goldkelch/qik-vrt"

    def test_updated_at_is_observational_not_a_new_continuation(self) -> None:
        first = semantic_request(issue(updated_at="2026-08-30T12:01:00Z"), self.repository)
        refreshed = semantic_request(issue(updated_at="2026-08-30T13:01:00Z"), self.repository)
        self.assertEqual(first, refreshed)
        self.assertEqual(
            build_record(first, status(), source=SOURCE)["continuation_id"],
            build_record(refreshed, status(), source=SOURCE)["continuation_id"],
        )

    def test_status_refresh_timestamp_is_observational(self) -> None:
        request = semantic_request(issue(), self.repository)
        first = build_record(request, status(generated_at="2026-08-30T12:02:00Z"), source=SOURCE)
        refreshed = build_record(request, status(generated_at="2026-08-30T13:02:00Z"), source=SOURCE)
        self.assertEqual(first["continuation_id"], refreshed["continuation_id"])
        self.assertEqual(first["current_binding"], refreshed["current_binding"])

    def test_semantic_issue_or_next_action_drift_rebinds(self) -> None:
        current = semantic_request(issue(), self.repository)
        changed_issue = semantic_request(issue(body="Changed causal input."), self.repository)
        first = build_record(current, status(), source=SOURCE)
        self.assertNotEqual(first["continuation_id"], build_record(changed_issue, status(), source=SOURCE)["continuation_id"])
        self.assertNotEqual(
            first["continuation_id"],
            build_record(current, status(next_action="Use a trusted deterministic work unit."), source=SOURCE)["continuation_id"],
        )

    def test_block_is_live_and_elapsed_time_is_not_a_wake(self) -> None:
        request = semantic_request(issue(), self.repository)
        record = build_record(request, status(), source=SOURCE)
        self.assertEqual(record["state"], "LIVE")
        self.assertEqual(record["liveness"], "INDEFINITE_UNTIL_EVIDENCED_OUTCOME")
        decision = should_resume(issue(updated_at="2026-09-05T12:01:00Z"), self.repository, record, SOURCE)
        self.assertEqual(decision["state"], "HOLD")
        self.assertFalse(decision["dispatch"])
        self.assertEqual(decision["reason"], "IDENTICAL_LIVE_CONTINUATION_NO_CAUSAL_WAKE")

    def test_semantic_source_drift_requests_exact_reobservation(self) -> None:
        request = semantic_request(issue(), self.repository)
        record = build_record(request, status(), source=SOURCE)
        decision = should_resume(issue(body="A later causal source revision."), self.repository, record, SOURCE)
        self.assertEqual(decision["state"], "REOBSERVE")
        self.assertTrue(decision["dispatch"])
        self.assertEqual(decision["predecessor_continuation_id"], record["continuation_id"])

    def test_record_rejects_stale_status_binding(self) -> None:
        request = semantic_request(issue(), self.repository)
        record = build_record(request, status(), source=SOURCE)
        with self.assertRaises(ContinuationError):
            validate_record(record, request, status(next_action="Different action."))

    def test_exact_source_head_or_tree_drift_requests_reobservation(self) -> None:
        request = semantic_request(issue(), self.repository)
        record = build_record(request, status(), source=SOURCE)
        drifted = {**SOURCE, "head_sha": "1111111111111111111111111111111111111111"}
        decision = should_resume(issue(), self.repository, record, drifted)
        self.assertEqual(decision["state"], "REOBSERVE")
        self.assertEqual(decision["reason"], "SOURCE_HEAD_TREE_OR_REF_CHANGED")
        self.assertEqual(decision["predecessor_continuation_id"], record["continuation_id"])

    def test_materialization_validates_the_exact_issue_request(self) -> None:
        request = semantic_request(issue(), self.repository)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "REQUEST.json").write_text(json.dumps(request), encoding="utf-8")
            (directory / "STATUS.json").write_text(json.dumps(status()), encoding="utf-8")
            record = materialize(directory, issue(), self.repository, SOURCE)
            validate_record(record, request, status())
            self.assertTrue((directory / "CONTINUATION.json").is_file())
            self.assertFalse((directory / "ISSUE_OBSERVATION.json").exists())
            with self.assertRaises(ContinuationError):
                materialize(directory, issue(body="drift"), self.repository, SOURCE)

    def test_backlog_does_not_use_elapsed_time_as_a_retry_trigger(self) -> None:
        workflow = (ROOT / ".github/workflows/issue-agent-backlog-resume.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("minimum_age_seconds", workflow)
        self.assertNotIn("generated_epoch", workflow)
        self.assertIn("continuation.py should-resume", workflow)
        self.assertIn("EXPLICIT_LEGACY_CONTINUATION_MATERIALIZATION", workflow)
        self.assertIn("actions/checkout@v4", workflow)
        self.assertIn("source_head", workflow)
        self.assertIn("--source-ref", workflow)
        self.assertIn("--source-head", workflow)
        self.assertIn("--source-tree", workflow)
        self.assertIn("AUTHORITY_MAIN_MOVED_DURING_REOBSERVATION", workflow)
        self.assertIn("INVALID_OR_UNBOUND_CONTINUATION_BINDING", workflow)

    def test_processing_deduplicates_exact_work_product_before_branch_reset(self) -> None:
        workflow = (ROOT / ".github/workflows/issue-autonomous-processing.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("Bind the exact Authority source", workflow)
        self.assertIn("--source-head", workflow)
        self.assertIn("contents/$continuation_path?ref=$prior_branch_head", workflow)
        self.assertIn("current_context_sha256", workflow)
        self.assertIn("current_answer_sha256", workflow)
        self.assertIn("NOOP: identical exact continuation", workflow)
        self.assertIn("git merge --no-ff --no-edit", workflow)
        self.assertIn('git push origin "$branch"', workflow)
        self.assertNotIn("git push --force-with-lease", workflow)
        self.assertNotIn('git add "evidence/issues/$ISSUE_NUMBER"', workflow)

    def test_autofinish_requires_current_exact_continuation_source_and_head_cas(self) -> None:
        workflow = (ROOT / ".github/workflows/issue-agent-autofinish.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONTINUATION.json?ref=$authority_head", workflow)
        self.assertIn("continuation.py check", workflow)
        self.assertIn("scripts/issue_agent/validate.py", workflow)
        self.assertIn("STALE_OR_UNVERIFIED_CONTINUATION_SOURCE_BINDING", workflow)
        self.assertIn("PR_HEAD_OR_BASE_CHANGED_DURING_REOBSERVATION", workflow)
        self.assertIn("--match-head-commit", workflow)


if __name__ == "__main__":
    unittest.main()
