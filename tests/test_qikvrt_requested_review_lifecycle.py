# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_lifecycle",
    ROOT / "tools/qikvrt_requested_review_lifecycle.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequestedReviewLifecycleTests(unittest.TestCase):
    def snapshot(self, **overrides):
        value = {
            "repository": "Goldkelch/qik-vrt",
            "pull_request": 640,
            "state": "open",
            "current_state": "open",
            "base_ref": "main",
            "current_base_ref": "main",
            "base_sha": "a" * 40,
            "current_pull_request_base_sha": "a" * 40,
            "current_base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "current_head_sha": "b" * 40,
            "tree_sha": "c" * 40,
            "current_tree_sha": "c" * 40,
            "merge_commit_sha": "e" * 40,
            "current_merge_commit_sha": "e" * 40,
            "updated_at": "2026-08-16T14:00:00Z",
            "current_updated_at": "2026-08-16T14:00:00Z",
            "active_requested_reviewers": ["Goldkelch"],
            "requested_reviewer_history": ["Goldkelch"],
            "requested_reviewer_requested_at": {"Goldkelch": "2026-08-16T14:00:00Z"},
            "requested_reviewer_request_event_ids": {"Goldkelch": 10},
            "active_requested_teams": [],
            "requested_team_history": [],
            "requested_team_requested_at": {},
            "requested_team_request_event_ids": {},
            "changed_paths": ["AGENTS.md", "tests/test_example.py"],
            "diff_sha256": "d" * 64,
            "diff_bytes": 42,
            "comments": [],
            "reviews": [],
            "unresolved_threads": 0,
            "gate_coverage": "OBSERVED_ACTIONS_AND_LEGACY_ONLY",
            "all_observed_candidate_gates_terminal_green": True,
            "gate_observations": [
                {
                    "kind": "check_run",
                    "context": "test_merge",
                    "sha": "e" * 40,
                    "name": "CI / test",
                    "status": "completed",
                    "conclusion": "success",
                    "id": 99,
                    "details_url": "https://example.invalid/check/99",
                }
            ],
            "competing_writer_or_supersession": False,
            "competing_writer_detail": "no open pull request shares the mutable candidate head ref",
            "existing_lifecycle_reviews": [],
        }
        value.update(overrides)
        if (
            "all_observed_candidate_gates_terminal_green" in overrides
            and not overrides["all_observed_candidate_gates_terminal_green"]
            and "gate_observations" not in overrides
        ):
            value["gate_observations"] = [
                {
                    "kind": "check_run",
                    "context": "test_merge",
                    "sha": "e" * 40,
                    "name": "CI / test",
                    "status": "in_progress",
                    "conclusion": None,
                    "id": 99,
                    "details_url": "https://example.invalid/check/99",
                }
            ]
        return value

    def exact_review(self, state: str, body: str = "", **overrides):
        value = {
            "id": 1,
            "user": {"login": "Goldkelch"},
            "state": state,
            "body": body,
            "commit_id": "b" * 40,
            "submitted_at": "2026-08-16T15:00:00Z",
        }
        value.update(overrides)
        return value

    def test_exact_head_requested_reviewer_approval_is_recorded(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(reviews=[self.exact_review("APPROVED")])
        )
        self.assertEqual(result["state"], "REVIEW_RECORDED")
        self.assertEqual(result["disposition"], "APPROVE")
        self.assertEqual(result["platform_review_state"], "APPROVED")

    def test_consumed_active_request_still_accepts_historical_requested_approval(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                active_requested_reviewers=[],
                requested_reviewer_history=["Goldkelch"],
                reviews=[self.exact_review("APPROVED")],
            )
        )
        self.assertEqual(result["state"], "REVIEW_RECORDED")
        self.assertEqual(result["reviewer"], "Goldkelch")

    def test_exact_requested_changes_request_is_a_review_disposition(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(reviews=[self.exact_review("CHANGES_REQUESTED")])
        )
        self.assertEqual(result["state"], "REVIEW_RECORDED")
        self.assertEqual(result["disposition"], "REQUEST_CHANGES")

    def test_structured_requested_comment_with_blocker_is_a_review_disposition(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                reviews=[
                    self.exact_review(
                        "COMMENTED",
                        "<!-- qikvrt-review-disposition:COMMENT_WITH_BLOCKER -->\nneeds a signer",
                    )
                ]
            )
        )
        self.assertEqual(result["state"], "REVIEW_RECORDED")
        self.assertEqual(result["disposition"], "COMMENT_WITH_BLOCKER")

    def test_unstructured_comment_does_not_complete_requested_review(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(reviews=[self.exact_review("COMMENTED", "looks promising")])
        )
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_NOT_RECORDED")

    def test_negated_or_quoted_comment_token_does_not_complete_requested_review(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                reviews=[
                    self.exact_review(
                        "COMMENTED",
                        "I am not issuing COMMENT_WITH_BLOCKER; the quoted token is documentation.",
                    )
                ]
            )
        )
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_NOT_RECORDED")

    def test_missing_requested_review_emits_exact_comment_with_blocker(self) -> None:
        result = MODULE.evaluate_review_lifecycle(self.snapshot())
        self.assertEqual(result["state"], "BLOCK")
        self.assertTrue(result["persistable"])
        self.assertEqual(result["disposition"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_NOT_RECORDED")
        self.assertEqual(len(result["binding_sha256"]), 64)
        self.assertFalse(result["review_already_recorded"])

    def test_one_marker_deduplicates_different_blockers_for_one_exact_binding(self) -> None:
        marker = MODULE.evaluate_review_lifecycle(self.snapshot())["review_marker"]
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                all_observed_candidate_gates_terminal_green=False,
                existing_lifecycle_reviews=[
                    self.exact_review(
                        "COMMENTED",
                        marker,
                        user={"login": "github-actions[bot]"},
                    )
                ],
            )
        )
        self.assertEqual(result["first_blocker"], "OBSERVED_CANDIDATE_GATE_PENDING_OR_ADVERSE")
        self.assertTrue(result["review_already_recorded"])

    def test_base_or_tree_change_requires_a_fresh_exact_observation_marker(self) -> None:
        old_marker = MODULE.evaluate_review_lifecycle(self.snapshot(base_sha="d" * 40, current_base_sha="d" * 40))["review_marker"]
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                existing_lifecycle_reviews=[
                    self.exact_review(
                        "COMMENTED", old_marker, user={"login": "github-actions[bot]"}
                    )
                ]
            )
        )
        self.assertFalse(result["review_already_recorded"])

    def test_base_ref_change_requires_a_fresh_exact_binding_marker(self) -> None:
        marker = MODULE.evaluate_review_lifecycle(self.snapshot())["review_marker"]
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                base_ref="release",
                current_base_ref="release",
                existing_lifecycle_reviews=[
                    self.exact_review(
                        "COMMENTED", marker, user={"login": "github-actions[bot]"}
                    )
                ],
            )
        )
        self.assertFalse(result["review_already_recorded"])

    def test_requested_reviewer_scope_change_requires_a_fresh_exact_binding_marker(self) -> None:
        marker = MODULE.evaluate_review_lifecycle(self.snapshot())["review_marker"]
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                active_requested_reviewers=["AnotherOwner"],
                requested_reviewer_history=["AnotherOwner"],
                existing_lifecycle_reviews=[
                    self.exact_review(
                        "COMMENTED", marker, user={"login": "github-actions[bot]"}
                    )
                ],
            )
        )
        self.assertFalse(result["review_already_recorded"])

    def test_untrusted_copied_marker_does_not_suppress_lifecycle_review(self) -> None:
        marker = MODULE.evaluate_review_lifecycle(self.snapshot())["review_marker"]
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                existing_lifecycle_reviews=[
                    self.exact_review("COMMENTED", marker, user={"login": "untrusted-contributor"})
                ]
            )
        )
        self.assertFalse(result["review_already_recorded"])

    def test_marker_on_another_head_does_not_suppress_lifecycle_review(self) -> None:
        marker = MODULE.evaluate_review_lifecycle(self.snapshot())["review_marker"]
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                existing_lifecycle_reviews=[
                    self.exact_review(
                        "COMMENTED",
                        marker,
                        commit_id="e" * 40,
                        user={"login": "github-actions[bot]"},
                    )
                ]
            )
        )
        self.assertFalse(result["review_already_recorded"])

    def test_no_requested_reviewer_is_not_a_spurious_review_failure(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(active_requested_reviewers=[], requested_reviewer_history=[])
        )
        self.assertEqual(result["state"], "NOT_APPLICABLE")
        self.assertFalse(result["persistable"])

    def test_team_only_request_fails_closed_until_member_mapping_exists(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                active_requested_reviewers=[],
                requested_reviewer_history=[],
                active_requested_teams=["core-owners"],
                requested_team_history=["core-owners"],
            )
        )
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "UNSUPPORTED_REQUESTED_TEAM_REVIEWER")

    def test_head_drift_precedes_review_disposition(self) -> None:
        result = MODULE.evaluate_review_lifecycle(self.snapshot(current_head_sha="e" * 40))
        self.assertEqual(result["first_blocker"], "HEAD_DRIFT")
        self.assertFalse(result["persistable"])

    def test_base_ref_drift_precedes_review_disposition(self) -> None:
        result = MODULE.evaluate_review_lifecycle(self.snapshot(current_base_ref="release"))
        self.assertEqual(result["first_blocker"], "BASE_REF_DRIFT")

    def test_base_ref_resolution_race_is_nonpersistable(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(current_base_sha="d" * 40, reviews=[self.exact_review("APPROVED")])
        )
        self.assertEqual(result["first_blocker"], "BASE_REF_RESOLUTION_DRIFT")
        self.assertFalse(result["persistable"])

    def test_final_pull_request_base_drift_is_not_hidden_by_ref_lookup(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                current_pull_request_base_sha="d" * 40,
                current_base_sha="a" * 40,
                reviews=[self.exact_review("APPROVED")],
            )
        )
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")
        self.assertFalse(result["persistable"])

    def test_nonterminal_or_adverse_gate_blocks_review(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(all_observed_candidate_gates_terminal_green=False)
        )
        self.assertEqual(result["first_blocker"], "OBSERVED_CANDIDATE_GATE_PENDING_OR_ADVERSE")
        self.assertEqual(result["first_non_green_gate"]["name"], "CI / test")

    def test_gate_context_sha_mismatch_rejects_the_snapshot(self) -> None:
        mismatched_gate = {
            **self.snapshot()["gate_observations"][0],
            "sha": "f" * 40,
        }
        with self.assertRaisesRegex(MODULE.ReviewLifecycleBlock, "does not match the bound candidate"):
            MODULE.evaluate_review_lifecycle(
                self.snapshot(gate_observations=[mismatched_gate], reviews=[self.exact_review("APPROVED")])
            )

    def test_no_request_is_not_applicable_before_merge_gate_requirements(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                merge_commit_sha=None,
                current_merge_commit_sha=None,
                active_requested_reviewers=[],
                requested_reviewer_history=[],
                requested_reviewer_requested_at={},
                requested_reviewer_request_event_ids={},
                gate_observations=[
                    {
                        "kind": "check_run",
                        "context": "head",
                        "sha": "b" * 40,
                        "name": "CI / head",
                        "status": "completed",
                        "conclusion": "success",
                        "id": 100,
                        "details_url": "https://example.invalid/check/100",
                    }
                ],
            )
        )
        self.assertEqual(result["state"], "NOT_APPLICABLE")

    def test_exact_review_is_recorded_after_gates_later_turn_green(self) -> None:
        review = self.exact_review("APPROVED")
        pending = MODULE.evaluate_review_lifecycle(
            self.snapshot(reviews=[review], all_observed_candidate_gates_terminal_green=False)
        )
        completed = MODULE.evaluate_review_lifecycle(
            self.snapshot(reviews=[review], all_observed_candidate_gates_terminal_green=True)
        )
        self.assertEqual(pending["first_blocker"], "OBSERVED_CANDIDATE_GATE_PENDING_OR_ADVERSE")
        self.assertEqual(pending["lifecycle_review_state"], "BLOCKED")
        self.assertNotIn("platform_review_state", pending)
        self.assertEqual(pending["observed_exact_head_review_states"][0]["state"], "APPROVED")
        self.assertEqual(completed["state"], "REVIEW_RECORDED")

    def test_unresolved_threads_block_review(self) -> None:
        result = MODULE.evaluate_review_lifecycle(self.snapshot(unresolved_threads=1))
        self.assertEqual(result["first_blocker"], "UNRESOLVED_REVIEW_THREADS")

    def test_competing_writer_or_supersession_blocks_review(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                competing_writer_or_supersession=True,
                competing_writer_detail="open pull request(s) share mutable head ref: #641",
            )
        )
        self.assertEqual(result["first_blocker"], "COMPETING_WRITER_OR_SUPERSESSION")

    def test_later_dismissal_invalidates_an_older_exact_head_approval(self) -> None:
        approval = self.exact_review("APPROVED", id=1, submitted_at="2026-08-16T15:00:00Z")
        dismissal = self.exact_review("DISMISSED", id=2, submitted_at="2026-08-16T15:01:00Z")
        result = MODULE.evaluate_review_lifecycle(self.snapshot(reviews=[approval, dismissal]))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_NOT_RECORDED")

    def test_review_order_uses_instants_not_lexical_timezone_offsets(self) -> None:
        approval = self.exact_review("APPROVED", id=1, submitted_at="2026-08-16T15:00:00+02:00")
        dismissal = self.exact_review("DISMISSED", id=2, submitted_at="2026-08-16T14:00:00Z")
        result = MODULE.evaluate_review_lifecycle(self.snapshot(reviews=[approval, dismissal]))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_NOT_RECORDED")

    def test_later_unstructured_comment_does_not_invalidate_an_exact_head_approval(self) -> None:
        approval = self.exact_review("APPROVED", id=1, submitted_at="2026-08-16T15:00:00Z")
        comment = self.exact_review(
            "COMMENTED", "ordinary follow-up", id=2, submitted_at="2026-08-16T15:01:00Z"
        )
        result = MODULE.evaluate_review_lifecycle(self.snapshot(reviews=[approval, comment]))
        self.assertEqual(result["state"], "REVIEW_RECORDED")
        self.assertEqual(result["disposition"], "APPROVE")

    def test_review_before_current_request_does_not_complete_re_request(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                requested_reviewer_requested_at={"Goldkelch": "2026-08-16T16:00:00Z"},
                requested_reviewer_request_event_ids={"Goldkelch": 11},
                reviews=[self.exact_review("APPROVED", submitted_at="2026-08-16T15:00:00Z")],
            )
        )
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_NOT_RECORDED")

    def test_review_at_the_request_timestamp_does_not_complete_re_request(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                requested_reviewer_requested_at={"Goldkelch": "2026-08-16T15:00:00Z"},
                requested_reviewer_request_event_ids={"Goldkelch": 11},
                reviews=[self.exact_review("APPROVED", submitted_at="2026-08-16T15:00:00Z")],
            )
        )
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_NOT_RECORDED")

    def test_re_request_generation_changes_the_exact_binding_marker(self) -> None:
        first = MODULE.evaluate_review_lifecycle(self.snapshot())["review_marker"]
        second = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                requested_reviewer_requested_at={"Goldkelch": "2026-08-16T16:00:00Z"},
                requested_reviewer_request_event_ids={"Goldkelch": 11},
            )
        )["review_marker"]
        self.assertNotEqual(first, second)

    def test_automation_requester_cannot_satisfy_its_own_lifecycle_review(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(
                active_requested_reviewers=["github-actions[bot]"],
                requested_reviewer_history=["github-actions[bot]"],
                requested_reviewer_requested_at={
                    "github-actions[bot]": "2026-08-16T14:00:00Z"
                },
                requested_reviewer_request_event_ids={"github-actions[bot]": 10},
                reviews=[
                    self.exact_review(
                        "COMMENTED",
                        "<!-- qikvrt-review-disposition:COMMENT_WITH_BLOCKER -->\nautomated",
                        user={"login": "github-actions[bot]"},
                    )
                ],
            )
        )
        self.assertEqual(result["first_blocker"], "UNSUPPORTED_AUTOMATION_REQUESTED_REVIEWER")

    def test_closed_pr_is_nonpersistable(self) -> None:
        result = MODULE.evaluate_review_lifecycle(self.snapshot(current_state="closed"))
        self.assertEqual(result["first_blocker"], "PULL_REQUEST_NOT_OPEN")
        self.assertFalse(result["persistable"])

    def test_merge_context_drift_is_nonpersistable(self) -> None:
        result = MODULE.evaluate_review_lifecycle(
            self.snapshot(current_merge_commit_sha="f" * 40)
        )
        self.assertEqual(result["first_blocker"], "MERGE_CONTEXT_DRIFT")
        self.assertFalse(result["persistable"])

    def test_invalid_snapshot_is_fail_closed_and_not_persistable(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as source:
            json.dump({"repository": "Goldkelch/qik-vrt"}, source)
            source.flush()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = MODULE.main(["evaluate", "--input", source.name])
        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["first_blocker"], "INVALID_REVIEW_SNAPSHOT")
        self.assertFalse(result["persistable"])


if __name__ == "__main__":
    unittest.main()
