# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest
from pathlib import Path

from tools.qikvrt_pr_head_event_subject import bind_event_subject

REPOSITORY = "Goldkelch/qik-vrt"
MAIN = "b" * 40
HEAD = "a" * 40
ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_pr_head_continuation.yml"


def pull_request_event(*, base: str = MAIN, repository: str = REPOSITORY):
    return {
        "pull_request": {
            "number": 960,
            "head": {
                "ref": "repair/example-v1",
                "sha": HEAD,
                "repo": {"full_name": repository},
            },
            "base": {"sha": base},
        }
    }


def workflow_run_event(*, count: int = 1):
    pulls = [
        {
            "number": 960,
            "head": {"ref": "repair/example-v1", "sha": HEAD},
            "base": {"sha": MAIN},
        }
    ]
    if count == 2:
        pulls.append(
            {
                "number": 959,
                "head": {"ref": "repair/other-v1", "sha": "c" * 40},
                "base": {"sha": MAIN},
            }
        )
    return {
        "workflow_run": {
            "head_repository": {"full_name": REPOSITORY},
            "pull_requests": pulls,
        }
    }


class PrHeadEventSubjectTests(unittest.TestCase):
    def test_pull_request_target_binds_one_exact_internal_subject(self):
        value = bind_event_subject(pull_request_event(), REPOSITORY, MAIN)
        self.assertEqual(value["state"], "BOUND")
        self.assertEqual(value["d0"], 0)
        self.assertEqual(
            value["selection_basis"],
            "EXACT_PULL_REQUEST_TARGET_EVENT",
        )
        self.assertEqual(value["subject"]["number"], 960)
        self.assertEqual(value["subject"]["head"]["sha"], HEAD)
        self.assertEqual(value["subject"]["base"]["sha"], MAIN)

    def test_single_pr_workflow_run_binds_one_exact_subject(self):
        value = bind_event_subject(workflow_run_event(), REPOSITORY, MAIN)
        self.assertEqual(value["state"], "BOUND")
        self.assertEqual(value["selection_basis"], "EXACT_WORKFLOW_RUN_EVENT")

    def test_multi_pr_workflow_run_uses_bounded_global_fallback(self):
        value = bind_event_subject(
            workflow_run_event(count=2),
            REPOSITORY,
            MAIN,
        )
        self.assertEqual(value["state"], "UNBOUND")
        self.assertEqual(value["d0"], 0)
        self.assertEqual(value["next_action"], "RUN_BOUNDED_GLOBAL_DISCOVERY")

    def test_external_pull_request_is_not_promoted_to_exact_internal_subject(self):
        value = bind_event_subject(
            pull_request_event(repository="someone/fork"),
            REPOSITORY,
            MAIN,
        )
        self.assertEqual(value["state"], "UNBOUND")
        self.assertIsNone(value["subject"])

    def test_event_base_drift_holds_without_global_substitution(self):
        value = bind_event_subject(
            pull_request_event(base="d" * 40),
            REPOSITORY,
            MAIN,
        )
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["d0"], 1)
        self.assertEqual(value["first_causal_blocker"], "BASE_DRIFT")
        self.assertEqual(
            value["next_action"],
            "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
        )

    def test_malformed_exact_internal_subject_fails_closed(self):
        event = pull_request_event()
        event["pull_request"]["head"]["sha"] = "not-a-sha"
        value = bind_event_subject(event, REPOSITORY, MAIN)
        self.assertEqual(value["state"], "HOLD_UNVERIFIED")
        self.assertEqual(value["d0"], 1)
        self.assertEqual(
            value["next_action"],
            "PRESERVE_FAIL_CLOSED_WITHOUT_GLOBAL_SUBSTITUTION",
        )

    def test_unrelated_event_uses_bounded_global_fallback(self):
        value = bind_event_subject({"action": "manual"}, REPOSITORY, MAIN)
        self.assertEqual(value["state"], "UNBOUND")
        self.assertEqual(value["selection_basis"], "GLOBAL_BOUNDED_DISCOVERY")


class PrHeadEventSubjectWorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_event_binding_precedes_global_open_pr_scan(self):
        helper = "tools/qikvrt_pr_head_event_subject.py"
        global_scan = "pulls?state=open&sort=updated&direction=desc&per_page=30"
        self.assertIn(helper, self.text)
        self.assertIn(global_scan, self.text)
        self.assertLess(self.text.index(helper), self.text.index(global_scan))
        self.assertIn("EXACT_PULL_REQUEST_TARGET_EVENT", (
            ROOT / "tools" / "qikvrt_pr_head_event_subject.py"
        ).read_text(encoding="utf-8"))
        self.assertIn("EXACT_WORKFLOW_RUN_EVENT", (
            ROOT / "tools" / "qikvrt_pr_head_event_subject.py"
        ).read_text(encoding="utf-8"))

    def test_exact_event_hold_cannot_fall_through_to_unrelated_pr(self):
        self.assertIn("HOLD|HOLD_UNVERIFIED)", self.text)
        self.assertIn(
            "exact event subject failed closed before global discovery",
            self.text,
        )
        hold_index = self.text.index("HOLD|HOLD_UNVERIFIED)")
        scan_index = self.text.index(
            "pulls?state=open&sort=updated&direction=desc&per_page=30"
        )
        self.assertLess(hold_index, scan_index)

    def test_action_required_does_not_hydrate_one_jobs_endpoint_per_run(self):
        self.assertIn("action_required)\n", self.text)
        self.assertIn(
            "action_required conclusion is the zero-job admission",
            self.text,
        )
        self.assertNotIn(
            "action_required|cancelled|failure|startup_failure|timed_out)",
            self.text,
        )

    def test_checkout_and_exact_base_readback_are_bounded(self):
        self.assertIn("fetch-depth: 1", self.text)
        self.assertNotIn("fetch-depth: 0", self.text)
        self.assertIn("refs/heads/main", self.text)
        self.assertIn('test "$live_main" = "$selected_base"', self.text)
        self.assertIn('test "$live_main" = "$BASE_SHA"', self.text)

    def test_existing_authority_surface_is_not_widened(self):
        self.assertEqual(self.text.count("actions: write"), 1)
        self.assertEqual(self.text.count("contents: write"), 1)
        self.assertEqual(self.text.count("statuses: write"), 1)
        self.assertNotIn("pull-requests: write", self.text)
        self.assertNotIn("qikvrt_requested_review_executor.yml/dispatches", self.text)


if __name__ == "__main__":
    unittest.main()
