#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest

from tools import qikvrt_ruleset_bridge_carrier as carrier


MAIN_SHA = "a" * 40
STALE_SHA = "b" * 40
REPOSITORY = "Goldkelch/qik-vrt"


def page(*runs, total_count: int | None = None):
    values = list(runs)
    return {
        "total_count": len(values) if total_count is None else total_count,
        "workflow_runs": values,
    }


def required(
    run_id: int,
    *,
    created: str,
    status: str = "completed",
    conclusion: str | None = "success",
    head_sha: str = MAIN_SHA,
    head_branch: str = "main",
    repository: str = REPOSITORY,
    name: str = carrier.REQUIRED_REVIEW_NAME,
    path: str = carrier.REQUIRED_REVIEW_PATH,
):
    return {
        "id": run_id,
        "name": name,
        "path": path,
        "repository": {"full_name": repository},
        "status": status,
        "conclusion": conclusion,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "created_at": created,
        "updated_at": created,
    }


def bridge(
    upstream: int,
    run_id: int,
    *,
    status: str,
    updated: str,
    conclusion: str | None = None,
    head_sha: str = MAIN_SHA,
    head_branch: str = "main",
    repository: str = REPOSITORY,
    name: str = carrier.BRIDGE_NAME,
    path: str = carrier.BRIDGE_PATH,
):
    if status == "completed" and conclusion is None:
        conclusion = "success"
    return {
        "id": run_id,
        "display_title": f"QIKVRT ruleset bridge upstream={upstream} carrier={run_id}",
        "name": name,
        "path": path,
        "repository": {"full_name": repository},
        "status": status,
        "conclusion": conclusion,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "created_at": updated,
        "updated_at": updated,
    }


def select(required_pages, bridge_pages):
    return carrier.select_carrier(
        required_pages,
        bridge_pages,
        expected_main_sha=MAIN_SHA,
        expected_repository=REPOSITORY,
    )


class RulesetBridgeCarrierTests(unittest.TestCase):
    def test_selects_the_oldest_exact_run_from_one_complete_bounded_page(self):
        result = select(
            [
                page(
                    required(20, created="2026-01-02T00:00:00Z"),
                    required(10, created="2026-01-01T00:00:00Z"),
                )
            ],
            [page()],
        )
        self.assertEqual(result["state"], "CANDIDATE")
        self.assertEqual(result["upstream_run_id"], 10)
        self.assertEqual(result["eligible_required_review_runs"], 2)
        self.assertEqual(result["expected_main_sha"], MAIN_SHA)
        self.assertEqual(result["expected_repository"], REPOSITORY)

    def test_active_bridge_run_is_not_replayed(self):
        result = select(
            [page(required(10, created="2026-01-01T00:00:00Z"), required(20, created="2026-01-02T00:00:00Z"))],
            [page(bridge(10, 100, status="in_progress", updated="2026-01-03T00:00:00Z"))],
        )
        self.assertEqual(result["upstream_run_id"], 20)

    def test_completed_bridge_is_replayable_and_round_robin_uses_oldest_carrier(self):
        result = select(
            [page(required(10, created="2026-01-01T00:00:00Z"), required(20, created="2026-01-02T00:00:00Z"))],
            [page(
                bridge(10, 100, status="completed", updated="2026-01-09T00:00:00Z"),
                bridge(20, 200, status="completed", updated="2026-01-05T00:00:00Z"),
            )],
        )
        self.assertEqual(result["upstream_run_id"], 20)
        self.assertEqual(result["previous_bridge_run_id"], 200)

    def test_stale_required_review_head_is_not_eligible(self):
        result = select(
            [page(required(10, created="2026-01-01T00:00:00Z", head_sha=STALE_SHA))],
            [page()],
        )
        self.assertEqual(result["state"], "NOOP")
        self.assertEqual(result["first_blocker"], "NO_REPLAYABLE_REQUIRED_REVIEW_RUN")

    def test_only_completed_successful_exact_required_reviews_are_eligible(self):
        result = select(
            [page(
                required(
                    10,
                    created="2026-01-01T00:00:00Z",
                    status="in_progress",
                    conclusion=None,
                ),
                required(
                    20,
                    created="2026-01-02T00:00:00Z",
                    conclusion="failure",
                ),
            )],
            [page()],
        )
        self.assertEqual(result["state"], "NOOP")

    def test_exact_main_rest_path_form_is_accepted(self):
        result = select(
            [
                page(
                    required(
                        10,
                        created="2026-01-01T00:00:00Z",
                        path=f"{carrier.REQUIRED_REVIEW_PATH}@main",
                    )
                )
            ],
            [page()],
        )
        self.assertEqual(result["state"], "CANDIDATE")

    def test_stale_bridge_provenance_cannot_block_an_exact_required_review(self):
        result = select(
            [page(required(10, created="2026-01-01T00:00:00Z"))],
            [page(
                bridge(
                    10,
                    100,
                    status="in_progress",
                    updated="2026-01-03T00:00:00Z",
                    head_sha=STALE_SHA,
                )
            )],
        )
        self.assertEqual(result["state"], "CANDIDATE")
        self.assertEqual(result["upstream_run_id"], 10)

    def test_unknown_status_or_terminal_conclusion_is_fail_closed(self):
        cases = (
            (
                "unknown required status",
                [page(required(10, created="2026-01-01T00:00:00Z", status="mystery", conclusion=None))],
                [page()],
            ),
            (
                "unknown bridge status",
                [page(required(10, created="2026-01-01T00:00:00Z"))],
                [page(bridge(10, 100, status="mystery", updated="2026-01-02T00:00:00Z"))],
            ),
            (
                "unknown completed bridge conclusion",
                [page(required(10, created="2026-01-01T00:00:00Z"))],
                [page(
                    bridge(
                        10,
                        100,
                        status="completed",
                        conclusion="mystery",
                        updated="2026-01-02T00:00:00Z",
                    )
                )],
            ),
        )
        for label, required_pages, bridge_pages in cases:
            with self.subTest(label=label):
                with self.assertRaises(carrier.CarrierSelectionError):
                    select(required_pages, bridge_pages)

    def test_over_bound_or_incomplete_page_is_fail_closed(self):
        cases = (
            (
                "more than one page",
                [
                    page(required(10, created="2026-01-01T00:00:00Z")),
                    page(required(20, created="2026-01-02T00:00:00Z")),
                ],
                [page()],
            ),
            (
                "total count over one 100-run page",
                [page(total_count=101)],
                [page()],
            ),
            (
                "incomplete count",
                [page(required(10, created="2026-01-01T00:00:00Z"), total_count=2)],
                [page()],
            ),
        )
        for label, required_pages, bridge_pages in cases:
            with self.subTest(label=label):
                with self.assertRaises(carrier.CarrierSelectionError):
                    select(required_pages, bridge_pages)

    def test_malformed_paginated_observation_is_fail_closed(self):
        with self.assertRaisesRegex(carrier.CarrierSelectionError, "total_count"):
            select({"workflow_runs": []}, [page()])

    def test_expected_main_sha_and_repository_are_required_and_exact(self):
        with self.assertRaises(TypeError):
            carrier.select_carrier([page()], [page()])
        with self.assertRaisesRegex(carrier.CarrierSelectionError, "expected_main_sha"):
            carrier.select_carrier(
                [page()],
                [page()],
                expected_main_sha="not-a-sha",
                expected_repository=REPOSITORY,
            )
        with self.assertRaisesRegex(carrier.CarrierSelectionError, "expected_repository"):
            carrier.select_carrier(
                [page()],
                [page()],
                expected_main_sha=MAIN_SHA,
                expected_repository="not a repository",
            )


if __name__ == "__main__":
    unittest.main()
