# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import base64
import datetime as dt
import unittest

from tools import qikvrt_weekly_publication_status as tracker


def item(**overrides):
    value = {
        "number": 1120,
        "head": "a" * 40,
        "state": "open",
        "draft": False,
        "merged": False,
        "requested_reviewers": ["Goldkelch"],
        "exact_head_approvals": [],
        "checks": {"success": 3, "failure": 0, "pending": 0, "neutral": 0},
        "public_readback": {
            "state": "NOT_ESTABLISHED",
            "evidence_source": None,
            "url": None,
        },
    }
    value.update(overrides)
    return value


class WeeklyPublicationStatusTest(unittest.TestCase):
    def test_week_is_iso_week(self):
        now = dt.datetime(2026, 9, 24, 7, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(tracker.utc_week(now), "2026-W39")

    def test_marker_roundtrip(self):
        snapshot = {"schema": "x", "prs": {"1120": item()}}
        line = tracker.marker_line("2026-W39", snapshot)
        self.assertEqual(tracker.parse_marker(line), ("2026-W39", snapshot))

    def test_current_week_marker_suppresses_duplicate(self):
        first = {"schema": "x", "prs": {}}
        comments = [{"body": tracker.marker_line("2026-W39", first)}]
        emitted, previous = tracker.previous_snapshot(comments, "2026-W39")
        self.assertTrue(emitted)
        self.assertEqual(previous, first)

    def test_exact_head_approval_does_not_transfer(self):
        head = "a" * 40
        reviews = [
            {"user": {"login": "Goldkelch"}, "commit_id": "b" * 40, "state": "APPROVED"},
            {"user": {"login": "Other"}, "commit_id": head, "state": "APPROVED"},
        ]
        self.assertEqual(
            tracker.effective_exact_head_approvals(reviews, head),
            ["Other"],
        )

    def test_later_dismissal_removes_exact_head_approval(self):
        head = "a" * 40
        reviews = [
            {"user": {"login": "Goldkelch"}, "commit_id": head, "state": "APPROVED"},
            {"user": {"login": "Goldkelch"}, "commit_id": head, "state": "DISMISSED"},
        ]
        self.assertEqual(tracker.effective_exact_head_approvals(reviews, head), [])

    def test_check_summary_separates_pending_and_failure(self):
        checks = [
            {"status": "completed", "conclusion": "success"},
            {"status": "completed", "conclusion": "failure"},
            {"status": "in_progress", "conclusion": None},
        ]
        self.assertEqual(
            tracker.check_summary(checks),
            {"success": 1, "failure": 1, "pending": 1, "neutral": 0},
        )

    def test_public_url_is_allowlisted(self):
        self.assertTrue(tracker.is_allowed_public_url("https://zenodo.org/records/123"))
        self.assertTrue(
            tracker.is_allowed_public_url("https://doi.org/10.5281/zenodo.123")
        )
        self.assertFalse(tracker.is_allowed_public_url("http://zenodo.org/records/123"))
        self.assertFalse(tracker.is_allowed_public_url("https://example.com/records/123"))

    def test_public_url_regex_extracts_supported_urls(self):
        text = (
            "https://zenodo.org/records/123 "
            "https://doi.org/10.5281/zenodo.456"
        )
        self.assertEqual(
            tracker.PUBLIC_URL_RE.findall(text),
            [
                "https://zenodo.org/records/123",
                "https://doi.org/10.5281/zenodo.456",
            ],
        )

    def test_publication_evidence_requires_exact_head_binding(self):
        head = "a" * 40

        class FakeGitHub:
            def __init__(self, payload):
                self.payload = payload

            def repo_paged(self, suffix):
                self.assert_suffix = suffix
                return [{"filename": "release/PUBLICATION_STATUS.json"}]

            def repo_get(self, suffix):
                encoded = base64.b64encode(self.payload.encode("utf-8")).decode("ascii")
                return {"encoding": "base64", "content": encoded}

        unbound = FakeGitHub('{"url":"https://zenodo.org/records/123"}')
        self.assertEqual(tracker.evidence_urls(unbound, 1120, head), [])

        bound = FakeGitHub(
            '{"head":"' + head + '","url":"https://zenodo.org/records/123"}'
        )
        self.assertEqual(
            tracker.evidence_urls(bound, 1120, head),
            [("release/PUBLICATION_STATUS.json", "https://zenodo.org/records/123")],
        )

    def test_unchanged_state_has_no_fresh_change(self):
        current = item()
        self.assertEqual(tracker.changed_fields(current, current), [])

    def test_blockers_keep_review_separate_from_effect_ack(self):
        value = item()
        self.assertEqual(
            tracker.blockers(value),
            ["UNMERGED", "NATIVE_REVIEW_PENDING"],
        )
        self.assertIn("native exact-head review", tracker.next_step(value).lower())

    def test_render_keeps_completion_boundary_explicit(self):
        prs = {str(number): item(number=number) for number in tracker.TRACKED_PRS}
        snapshot = {
            "schema": "qikvrt-weekly-publication-status/1",
            "week": "2026-W39",
            "observed_at": "2026-09-24T07:00:00+00:00",
            "repository": "Goldkelch/qik-vrt",
            "tracking_issue": 1186,
            "prs": prs,
            "completion_claims": {
                "repository_success_is_effect_ack_done": False,
                "effect_ack_done": False,
            },
        }
        text = tracker.render_comment("2026-W39", None, snapshot)
        self.assertIn("BASELINE_CAPTURE", text)
        self.assertIn("REPOSITORY_SUCCESS != EFFECT_ACK_DONE", text)
        self.assertIn("WORKFLOW_GREEN != PUBLICATION", text)
        self.assertIn("PREDECESSOR_EVIDENCE_TRANSFER = false", text)


if __name__ == "__main__":
    unittest.main()
