# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_snapshot",
    ROOT / "tools/qikvrt_requested_review_snapshot.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FixtureApi:
    def __init__(self, current_head: str | None = None) -> None:
        self.base = "a" * 40
        self.head = "b" * 40
        self.tree = "c" * 40
        self.merge = "d" * 40
        self.current_head = current_head or self.head
        self.current_tree = "f" * 40 if current_head else self.tree
        self.current_merge = self.merge
        self.pull_reads = 0

    def json(self, path: str):
        if path.endswith("/pulls/640"):
            self.pull_reads += 1
            head = self.head if self.pull_reads == 1 else self.current_head
            return {
                "number": 640,
                "state": "open",
                "changed_files": 1,
                "updated_at": "2026-08-16T14:00:00Z",
                "merge_commit_sha": self.merge if self.pull_reads == 1 else self.current_merge,
                "head": {
                    "sha": head,
                    "ref": "delivery-closure",
                    "repo": {"owner": {"login": "Goldkelch"}},
                },
                "base": {"sha": self.base, "ref": "main"},
                "requested_reviewers": [{"login": "Goldkelch"}],
                "requested_teams": [],
            }
        if path.endswith("/commits/main"):
            return {"sha": self.base}
        if path.endswith(f"/commits/{self.head}"):
            return {"commit": {"tree": {"sha": self.tree}}}
        if path.endswith(f"/commits/{self.current_head}"):
            return {"commit": {"tree": {"sha": self.current_tree}}}
        raise AssertionError(path)

    def pages(self, path: str):
        if "/pulls?state=open&head=" in path:
            return [
                {
                    "number": 640,
                    "head": {"ref": "delivery-closure"},
                }
            ]
        if "/files?" in path:
            return [{"filename": "AGENTS.md"}]
        if "/comments?" in path:
            return [{"id": 1, "body": "observed"}]
        if "/reviews?" in path:
            return []
        if "/events?" in path:
            return [
                {
                    "id": 10,
                    "created_at": "2026-08-16T14:00:00Z",
                    "event": "review_requested",
                    "requested_reviewer": {"login": "Goldkelch"},
                }
            ]
        if "/check-runs?" in path:
            return [{"check_runs": [{"name": "CI", "status": "completed", "conclusion": "success"}]}]
        if "/statuses?" in path:
            return []
        raise AssertionError(path)

    def raw(self, path: str, accept: str) -> bytes:
        self.raw_path = (path, accept)
        return b"diff --git a/AGENTS.md b/AGENTS.md\n"

    def graphql(self, query: str, variables):
        self.graphql_variables = variables
        return {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [{"isResolved": True}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        }


class RequestedReviewSnapshotTests(unittest.TestCase):
    def test_snapshot_observes_history_diff_comments_threads_and_gates(self) -> None:
        api = FixtureApi()
        value = MODULE.observe_pull_request(api, "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["base_ref"], "main")
        self.assertEqual(value["head_sha"], api.head)
        self.assertEqual(value["tree_sha"], api.tree)
        self.assertEqual(value["requested_reviewer_history"], ["Goldkelch"])
        self.assertEqual(
            value["requested_reviewer_requested_at"],
            {"Goldkelch": "2026-08-16T14:00:00Z"},
        )
        self.assertEqual(value["active_requested_reviewers"], ["Goldkelch"])
        self.assertEqual(value["active_requested_teams"], [])
        self.assertEqual(value["changed_paths"], ["AGENTS.md"])
        self.assertEqual(value["diff_bytes"], len(b"diff --git a/AGENTS.md b/AGENTS.md\n"))
        self.assertEqual(len(value["comments"]), 1)
        self.assertEqual(value["gate_coverage"], "OBSERVED_ACTIONS_AND_LEGACY_ONLY")
        self.assertTrue(value["all_observed_candidate_gates_terminal_green"])
        self.assertEqual({gate["context"] for gate in value["gate_observations"]}, {"head", "test_merge"})
        self.assertEqual(value["unresolved_threads"], 0)
        self.assertEqual(api.raw_path[1], "application/vnd.github.diff")

    def test_current_tree_is_observed_from_current_head(self) -> None:
        api = FixtureApi(current_head="e" * 40)
        value = MODULE.observe_pull_request(api, "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["head_sha"], "b" * 40)
        self.assertEqual(value["current_head_sha"], "e" * 40)
        self.assertEqual(value["current_tree_sha"], "f" * 40)

    def test_final_reobservation_reports_base_ref_and_base_sha_drift(self) -> None:
        class BaseDriftApi(FixtureApi):
            def json(self, path: str):
                if path.endswith("/commits/release"):
                    return {"sha": "d" * 40}
                value = super().json(path)
                if path.endswith("/pulls/640") and self.pull_reads == 2:
                    value["base"] = {"sha": "d" * 40, "ref": "release"}
                return value

        value = MODULE.observe_pull_request(BaseDriftApi(), "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["base_ref"], "main")
        self.assertEqual(value["current_base_ref"], "release")
        self.assertEqual(value["current_pull_request_base_sha"], "d" * 40)
        self.assertEqual(value["current_base_sha"], "d" * 40)

    def test_final_pull_request_base_cannot_be_hidden_by_a_later_ref_lookup(self) -> None:
        class BaseRefRaceApi(FixtureApi):
            def json(self, path: str):
                value = super().json(path)
                if path.endswith("/pulls/640") and self.pull_reads == 2:
                    value["base"] = {"sha": "d" * 40, "ref": "main"}
                return value

        value = MODULE.observe_pull_request(BaseRefRaceApi(), "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["base_sha"], "a" * 40)
        self.assertEqual(value["current_pull_request_base_sha"], "d" * 40)
        self.assertEqual(value["current_base_sha"], "a" * 40)

    def test_changed_path_count_mismatch_fails_closed(self) -> None:
        class IncompleteFilesApi(FixtureApi):
            def json(self, path: str):
                value = super().json(path)
                if path.endswith("/pulls/640"):
                    value["changed_files"] = 3001
                return value

        with self.assertRaisesRegex(MODULE.SnapshotError, "exceeds GitHub files API completeness bound"):
            MODULE.observe_pull_request(IncompleteFilesApi(), "Goldkelch/qik-vrt", 640)

    def test_changed_path_count_mismatch_below_api_limit_fails_closed(self) -> None:
        class MissingFileApi(FixtureApi):
            def json(self, path: str):
                value = super().json(path)
                if path.endswith("/pulls/640"):
                    value["changed_files"] = 2
                return value

        with self.assertRaisesRegex(MODULE.SnapshotError, "does not match pull request changed_files"):
            MODULE.observe_pull_request(MissingFileApi(), "Goldkelch/qik-vrt", 640)

    def test_changed_source_text_cannot_forge_a_rendered_diff_header(self) -> None:
        class ForgedDiffHeaderApi(FixtureApi):
            def json(self, path: str):
                value = super().json(path)
                if path.endswith("/pulls/640"):
                    value["changed_files"] = 2
                return value

            def pages(self, path: str):
                if "/files?" in path:
                    return [{"filename": "AGENTS.md"}, {"filename": "tests/example.py"}]
                return super().pages(path)

            def raw(self, path: str, accept: str) -> bytes:
                return (
                    b"diff --git a/AGENTS.md b/AGENTS.md\n"
                    b"+diff --git a/not-a-header b/not-a-header\n"
                )

        with self.assertRaisesRegex(MODULE.SnapshotError, "headers do not match"):
            MODULE.observe_pull_request(ForgedDiffHeaderApi(), "Goldkelch/qik-vrt", 640)

    def test_renamed_file_binds_both_previous_and_current_paths(self) -> None:
        class RenameApi(FixtureApi):
            def pages(self, path: str):
                if "/files?" in path:
                    return [{"filename": "docs/current.md", "previous_filename": "docs/previous.md"}]
                return super().pages(path)

            def raw(self, path: str, accept: str) -> bytes:
                return b"diff --git a/docs/previous.md b/docs/current.md\n"

        value = MODULE.observe_pull_request(RenameApi(), "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["changed_paths"], ["docs/current.md", "docs/previous.md"])

    def test_per_file_rendered_diff_boundary_fails_closed(self) -> None:
        class OversizedSingleFileDiffApi(FixtureApi):
            def raw(self, path: str, accept: str) -> bytes:
                # Stay below the 20,000-line aggregate boundary while
                # exceeding GitHub's 500 KiB per-file rendered-diff limit.
                return (
                    b"diff --git a/AGENTS.md b/AGENTS.md\n"
                    + b"+0123456789abcdef0123456789abcdef\n" * 18000
                )

        with self.assertRaisesRegex(MODULE.SnapshotError, "reaches GitHub completeness boundary"):
            MODULE.observe_pull_request(OversizedSingleFileDiffApi(), "Goldkelch/qik-vrt", 640)

    def test_legacy_status_uses_latest_context_result(self) -> None:
        class RetriedStatusApi(FixtureApi):
            def pages(self, path: str):
                if "/statuses?" in path:
                    return [
                        {
                            "id": 1,
                            "context": "legacy-ci",
                            "state": "failure",
                            "updated_at": "2026-08-16T15:00:00Z",
                        },
                        {
                            "id": 2,
                            "context": "legacy-ci",
                            "state": "success",
                            "updated_at": "2026-08-16T15:01:00Z",
                        },
                    ]
                return super().pages(path)

        value = MODULE.observe_pull_request(RetriedStatusApi(), "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["legacy_status_count"], 2)
        self.assertTrue(value["all_observed_candidate_gates_terminal_green"])

    def test_shared_mutable_head_ref_is_reported_as_competing_writer(self) -> None:
        class CompetingWriterApi(FixtureApi):
            def pages(self, path: str):
                if "/pulls?state=open&head=" in path:
                    return [
                        {"number": 640, "head": {"ref": "delivery-closure"}},
                        {"number": 641, "head": {"ref": "delivery-closure"}},
                    ]
                return super().pages(path)

        value = MODULE.observe_pull_request(CompetingWriterApi(), "Goldkelch/qik-vrt", 640)
        self.assertTrue(value["competing_writer_or_supersession"])
        self.assertIn("#641", value["competing_writer_detail"])

    def test_requested_team_history_is_observed(self) -> None:
        class TeamRequestApi(FixtureApi):
            def json(self, path: str):
                value = super().json(path)
                if path.endswith("/pulls/640"):
                    value["requested_reviewers"] = []
                    value["requested_teams"] = [{"slug": "core-owners"}]
                return value

            def pages(self, path: str):
                if "/events?" in path:
                    return [
                        {
                            "id": 10,
                            "created_at": "2026-08-16T14:00:00Z",
                            "event": "review_requested",
                            "requested_team": {"slug": "core-owners"},
                        }
                    ]
                return super().pages(path)

        value = MODULE.observe_pull_request(TeamRequestApi(), "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["active_requested_teams"], ["core-owners"])
        self.assertEqual(value["requested_team_history"], ["core-owners"])

    def test_removed_request_is_not_retained_without_a_re_request(self) -> None:
        class RemovedRequestApi(FixtureApi):
            def json(self, path: str):
                value = super().json(path)
                if path.endswith("/pulls/640"):
                    value["requested_reviewers"] = []
                return value

            def pages(self, path: str):
                if "/events?" in path:
                    return [
                        {
                            "id": 11,
                            "created_at": "2026-08-16T14:01:00Z",
                            "event": "review_request_removed",
                            "requested_reviewer": {"login": "Goldkelch"},
                        },
                        {
                            "id": 10,
                            "created_at": "2026-08-16T14:00:00Z",
                            "event": "review_requested",
                            "requested_reviewer": {"login": "Goldkelch"},
                        },
                    ]
                return super().pages(path)

        value = MODULE.observe_pull_request(RemovedRequestApi(), "Goldkelch/qik-vrt", 640)
        self.assertEqual(value["requested_reviewer_history"], [])
        self.assertEqual(value["requested_reviewer_requested_at"], {})

    def test_re_request_history_uses_latest_generation(self) -> None:
        class ReRequestApi(FixtureApi):
            def pages(self, path: str):
                if "/events?" in path:
                    return [
                        {
                            "id": 12,
                            "created_at": "2026-08-16T14:02:00Z",
                            "event": "review_requested",
                            "requested_reviewer": {"login": "Goldkelch"},
                        },
                        {
                            "id": 11,
                            "created_at": "2026-08-16T14:01:00Z",
                            "event": "review_request_removed",
                            "requested_reviewer": {"login": "Goldkelch"},
                        },
                        {
                            "id": 10,
                            "created_at": "2026-08-16T14:00:00Z",
                            "event": "review_requested",
                            "requested_reviewer": {"login": "Goldkelch"},
                        },
                    ]
                return super().pages(path)

        value = MODULE.observe_pull_request(ReRequestApi(), "Goldkelch/qik-vrt", 640)
        self.assertEqual(
            value["requested_reviewer_requested_at"],
            {"Goldkelch": "2026-08-16T14:02:00Z"},
        )
        self.assertEqual(value["requested_reviewer_request_event_ids"], {"Goldkelch": 12})


if __name__ == "__main__":
    unittest.main()
