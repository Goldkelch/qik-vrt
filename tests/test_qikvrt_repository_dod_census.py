import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.qikvrt_repository_dod_census import (
    OBSERVED_SCHEMA,
    UNAVAILABLE_SCHEMA,
    classify_branch,
    explicit_pr_disposition,
    load_pr_snapshot,
)


class DodCensusTests(unittest.TestCase):
    def test_explicit_pr_disposition_is_exact_marker_only(self):
        self.assertEqual(
            explicit_pr_disposition("<!-- qikvrt-dod-pr-disposition:REJECT_WITH_EVIDENCE -->"),
            "REJECT_WITH_EVIDENCE",
        )
        self.assertIsNone(explicit_pr_disposition("REJECT_WITH_EVIDENCE"))

    def test_current_candidate_branch_is_regarded_without_claiming_merge(self):
        subject = "a" * 40
        row = classify_branch("integration/final", subject, subject, "b" * 40)
        self.assertTrue(row["regarded"])
        self.assertEqual(row["disposition"], "PRODUCTIVE_CURRENT_CANDIDATE")

    def test_default_main_is_regarded(self):
        row = classify_branch("main", "a" * 40, "b" * 40, "a" * 40)
        self.assertTrue(row["regarded"])
        self.assertEqual(row["disposition"], "MERGED")

    def test_regarded_open_pr_branch_is_productive_not_merged(self):
        pr = {
            "number": 7,
            "head": "c" * 40,
            "head_ref": "feature/x",
            "regarded": True,
            "disposition": "MERGE",
        }
        with mock.patch("tools.qikvrt_repository_dod_census.ancestor", return_value=False), \
             mock.patch("tools.qikvrt_repository_dod_census.same_tree", return_value=False):
            row = classify_branch(
                "feature/x",
                "c" * 40,
                "a" * 40,
                "b" * 40,
                {"feature/x": pr},
            )
        self.assertTrue(row["regarded"])
        self.assertEqual(row["disposition"], "PRODUCTIVE_UNMERGED")

    def test_tree_identical_divergent_branch_is_redundant(self):
        with mock.patch("tools.qikvrt_repository_dod_census.ancestor", return_value=False), \
             mock.patch("tools.qikvrt_repository_dod_census.same_tree", return_value=True):
            row = classify_branch("verify/x", "c" * 40, "a" * 40, "b" * 40)
        self.assertTrue(row["regarded"])
        self.assertEqual(row["disposition"], "REDUNDANT")

    def test_rate_limited_pr_snapshot_is_hold_not_empty_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "open-prs.json"
            path.write_text(json.dumps({
                "schema": UNAVAILABLE_SCHEMA,
                "state": "HOLD_UNVERIFIED",
                "reason": "OPEN_PR_SNAPSHOT_API_UNAVAILABLE",
                "rest_rc": 1,
                "graphql_rc": 1,
            }), encoding="utf-8")
            rows, complete, reason, source = load_pr_snapshot(path)
        self.assertEqual(rows, [])
        self.assertFalse(complete)
        self.assertEqual(reason, "OPEN_PR_SNAPSHOT_API_UNAVAILABLE")
        self.assertEqual(source, "UNAVAILABLE")

    def test_graphql_observed_snapshot_is_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "open-prs.json"
            path.write_text(json.dumps({
                "schema": OBSERVED_SCHEMA,
                "state": "OBSERVED",
                "source": "GRAPHQL",
                "pull_requests": [
                    {"number": 2, "head": {"sha": "b" * 40, "ref": "feature/x"}, "state": "open"}
                ],
            }), encoding="utf-8")
            rows, complete, reason, source = load_pr_snapshot(path)
        self.assertTrue(complete)
        self.assertIsNone(reason)
        self.assertEqual(source, "GRAPHQL")
        self.assertEqual(rows[0]["number"], 2)

    def test_available_paginated_legacy_snapshot_is_flattened(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "open-prs.json"
            path.write_text(json.dumps([
                [{"number": 1, "head": {"sha": "a" * 40}, "state": "open"}],
                [{"number": 2, "head": {"sha": "b" * 40}, "state": "open"}],
            ]), encoding="utf-8")
            rows, complete, reason, source = load_pr_snapshot(path)
        self.assertTrue(complete)
        self.assertIsNone(reason)
        self.assertEqual(source, "LEGACY_LIST")
        self.assertEqual([row["number"] for row in rows], [1, 2])

    def test_unavailable_snapshot_requires_fail_closed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "open-prs.json"
            path.write_text(json.dumps({
                "schema": UNAVAILABLE_SCHEMA,
                "state": "PASS",
                "reason": "wrong",
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_pr_snapshot(path)


if __name__ == "__main__":
    unittest.main()
