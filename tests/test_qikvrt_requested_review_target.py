# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
from __future__ import annotations

import contextlib
import io
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_target",
    ROOT / "tools/qikvrt_requested_review_target.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FixtureApi:
    head = "b" * 40

    def __init__(
        self,
        candidates=None,
        state="open",
        workflow_run=None,
        pull_request_states=None,
        open_pull_requests=None,
    ) -> None:
        self.candidates = candidates if candidates is not None else []
        self.state = state
        self.workflow_run = workflow_run
        self.pull_request_states = pull_request_states or {}
        self.open_pull_requests = open_pull_requests if open_pull_requests is not None else []
        self.json_paths = []
        self.pages_paths = []

    def json(self, path: str):
        self.json_paths.append(path)
        if "/actions/runs/" in path:
            if self.workflow_run is None:
                raise AssertionError("unexpected workflow run lookup")
            return self.workflow_run
        self.direct_path = path
        number = int(path.rsplit("/", 1)[1])
        return {"number": number, "state": self.pull_request_states.get(number, self.state)}

    def pages(self, path: str):
        self.pages_path = path
        self.pages_paths.append(path)
        if "/commits/" in path:
            return self.candidates
        if "/pulls?state=open&per_page=100" in path:
            return self.open_pull_requests
        raise AssertionError(f"unexpected paginated lookup: {path}")


class RequestedReviewTargetTests(unittest.TestCase):
    repository = "Goldkelch/qik-vrt"

    def candidate(self, number: int, state="open", head=None):
        return {"number": number, "state": state, "head": {"sha": head or FixtureApi.head}}

    def workflow_run(self, pull_requests, **overrides):
        value = {
            "id": 9123,
            "repository": {"full_name": self.repository},
            "name": "QIK-VRT requested review signal",
            "event": "pull_request_review",
            "workflow_id": 731,
            "path": ".github/workflows/qikvrt_requested_review_signal.yml@refs/pull/640/merge",
            "pull_requests": pull_requests,
        }
        value.update(overrides)
        return value

    def test_direct_target_must_still_be_open(self) -> None:
        self.assertEqual(
            MODULE.resolve_direct_open_pull_request(FixtureApi(), self.repository, 640), 640
        )
        self.assertIsNone(
            MODULE.resolve_direct_open_pull_request(
                FixtureApi(state="closed"), self.repository, 640
            )
        )

    def test_exact_head_resolves_a_unique_open_pull_request(self) -> None:
        api = FixtureApi([self.candidate(640)])
        self.assertEqual(
            MODULE.resolve_unique_open_pull_request_for_head(api, self.repository, api.head),
            640,
        )
        self.assertIn(f"commits/{api.head}/pulls", api.pages_path)

    def test_stale_or_closed_head_is_a_safe_noop(self) -> None:
        self.assertIsNone(
            MODULE.resolve_unique_open_pull_request_for_head(
                FixtureApi([self.candidate(640, state="closed")]),
                self.repository,
                FixtureApi.head,
            )
        )

    def test_ambiguous_open_head_fails_closed(self) -> None:
        with self.assertRaises(MODULE.TargetResolutionError):
            MODULE.resolve_unique_open_pull_request_for_head(
                FixtureApi([self.candidate(640), self.candidate(641)]),
                self.repository,
                FixtureApi.head,
            )

    def test_test_merge_commit_association_resolves_without_head_equality(self) -> None:
        test_merge = "c" * 40
        api = FixtureApi([self.candidate(640, head=FixtureApi.head)])
        self.assertEqual(
            MODULE.resolve_unique_open_pull_request_for_commit(api, self.repository, test_merge),
            640,
        )
        self.assertIn(f"commits/{test_merge}/pulls", api.pages_path)

    def test_ambiguous_test_merge_commit_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.TargetResolutionError, "multiple open pull requests"):
            MODULE.resolve_unique_open_pull_request_for_commit(
                FixtureApi([self.candidate(640), self.candidate(641)]),
                self.repository,
                "c" * 40,
            )

    def test_workflow_run_resolves_its_unique_open_association(self) -> None:
        api = FixtureApi(workflow_run=self.workflow_run([{"number": 640}]))
        self.assertEqual(
            MODULE.resolve_unique_open_pull_request_for_workflow_run(
                api,
                self.repository,
                9123,
                expected_workflow_name="QIK-VRT requested review signal",
                expected_event="pull_request_review",
                expected_workflow_path=".github/workflows/qikvrt_requested_review_signal.yml",
            ),
            640,
        )
        self.assertIn(f"repos/{self.repository}/actions/runs/9123", api.json_paths)
        self.assertIn(f"repos/{self.repository}/pulls/640", api.json_paths)

    def test_workflow_run_without_an_association_fails_closed(self) -> None:
        api = FixtureApi(workflow_run=self.workflow_run([]))
        with self.assertRaisesRegex(MODULE.TargetResolutionError, "exactly one pull request"):
            MODULE.resolve_unique_open_pull_request_for_workflow_run(api, self.repository, 9123)

    def test_workflow_run_with_ambiguous_associations_fails_closed(self) -> None:
        api = FixtureApi(workflow_run=self.workflow_run([{"number": 640}, {"number": 641}]))
        with self.assertRaisesRegex(MODULE.TargetResolutionError, "exactly one pull request"):
            MODULE.resolve_unique_open_pull_request_for_workflow_run(api, self.repository, 9123)

    def test_workflow_run_with_closed_association_is_a_safe_noop(self) -> None:
        api = FixtureApi(
            workflow_run=self.workflow_run([{"number": 640}]),
            pull_request_states={640: "closed"},
        )
        self.assertIsNone(
            MODULE.resolve_unique_open_pull_request_for_workflow_run(api, self.repository, 9123)
        )

    def test_workflow_run_binding_mismatch_fails_closed(self) -> None:
        api = FixtureApi(
            workflow_run=self.workflow_run(
                [{"number": 640}], repository={"full_name": "other/repository"}
            )
        )
        with self.assertRaisesRegex(MODULE.TargetResolutionError, "expected repository"):
            MODULE.resolve_unique_open_pull_request_for_workflow_run(api, self.repository, 9123)

    def test_workflow_run_path_mismatch_fails_closed(self) -> None:
        api = FixtureApi(
            workflow_run=self.workflow_run(
                [{"number": 640}], path=".github/workflows/copied-name.yml@refs/pull/640/merge"
            )
        )
        with self.assertRaisesRegex(MODULE.TargetResolutionError, "expected workflow path"):
            MODULE.resolve_unique_open_pull_request_for_workflow_run(
                api,
                self.repository,
                9123,
                expected_workflow_path=".github/workflows/qikvrt_requested_review_signal.yml",
            )

    def test_workflow_run_event_mismatch_fails_closed(self) -> None:
        api = FixtureApi(workflow_run=self.workflow_run([{"number": 640}], event="push"))
        with self.assertRaisesRegex(MODULE.TargetResolutionError, "expected event"):
            MODULE.resolve_unique_open_pull_request_for_workflow_run(
                api,
                self.repository,
                9123,
                expected_event="pull_request",
            )

    def test_scheduler_lists_distinct_current_open_pull_requests(self) -> None:
        api = FixtureApi(
            open_pull_requests=[
                {"number": 641, "state": "open"},
                {"number": 640, "state": "open"},
            ]
        )
        self.assertEqual(
            MODULE.resolve_all_current_open_pull_requests(api, self.repository), [640, 641]
        )
        self.assertIn(f"repos/{self.repository}/pulls?state=open&per_page=100", api.pages_paths)

    def test_scheduler_cli_emits_open_pull_request_list(self) -> None:
        api = FixtureApi(open_pull_requests=[{"number": 640, "state": "open"}])
        output = io.StringIO()
        with mock.patch.object(MODULE, "GitHubApi", return_value=api), contextlib.redirect_stdout(
            output
        ):
            self.assertEqual(MODULE.main(["--repository", self.repository, "--all-open"]), 0)
        self.assertEqual(json.loads(output.getvalue()), {"pull_requests": [640]})


if __name__ == "__main__":
    unittest.main()
