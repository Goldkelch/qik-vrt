# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import re
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_requested_review_lifecycle.yml"
SIGNAL_WORKFLOW = ROOT / ".github/workflows/qikvrt_requested_review_signal.yml"
SNAPSHOT = ROOT / "tools/qikvrt_requested_review_snapshot.py"
TARGET = ROOT / "tools/qikvrt_requested_review_target.py"
WORK_UNIT = ROOT / "state/work_units/QIKVRT_REQUESTED_REVIEW_LIFECYCLE_EXECUTOR_V1.json"
ORIGIN_POLICY = ROOT / "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json"


class RequestedReviewLifecycleContractTests(unittest.TestCase):
    @staticmethod
    def pull_request_workflows() -> dict[str, str]:
        result: dict[str, str] = {}
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            source = path.read_text(encoding="utf-8")
            if not re.search(r"^\s{2}pull_request:\s*(?:#.*)?$", source, re.MULTILINE):
                continue
            match = re.search(r"^name:\s*(.+)$", source, re.MULTILINE)
            assert match, path
            name = match.group(1)
            self_path = str(path.relative_to(ROOT))
            if name in result:
                raise AssertionError(f"duplicate pull-request workflow display name {name!r}")
            result[name] = self_path
        return result

    def test_policy_binds_the_executable_lifecycle(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        executor = policy["review_lifecycle"]["executor"]
        self.assertEqual(executor["decision_path"], "tools/qikvrt_requested_review_lifecycle.py")
        self.assertEqual(executor["observation_path"], "tools/qikvrt_requested_review_snapshot.py")
        self.assertEqual(executor["target_path"], "tools/qikvrt_requested_review_target.py")
        self.assertEqual(executor["workflow_path"], ".github/workflows/qikvrt_requested_review_lifecycle.yml")
        self.assertEqual(executor["signal_workflow_path"], ".github/workflows/qikvrt_requested_review_signal.yml")
        self.assertEqual(executor["automatic_disposition"], "COMMENT_WITH_BLOCKER_ONLY")
        self.assertFalse(executor["automatic_approval"])
        self.assertFalse(executor["automatic_merge"])
        self.assertEqual(executor["gate_coverage"], "OBSERVED_ACTIONS_AND_LEGACY_ONLY")
        self.assertEqual(
            executor["platform_required_gate_set"],
            "NOT_OBSERVED_NO_MERGE_OR_REVIEW_READY_CLAIM",
        )

    def test_privileged_workflow_uses_trusted_bytes_and_binds_review_write_exactly(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_target", workflow)
        self.assertIn("workflow_run", workflow)
        self.assertIn("status:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("review_requested", workflow)
        self.assertIn("review_request_removed", workflow)
        self.assertIn("github.event.repository.default_branch", workflow)
        self.assertIn("job.workflow_sha", workflow)
        self.assertIn("job.workflow_ref", workflow)
        self.assertIn("steps.trusted_source.outputs.sha", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("github.event.pull_request.head.sha", workflow)
        self.assertNotIn("\n  pull_request_review:\n", workflow)
        self.assertNotIn("\n  pull_request:\n", workflow)
        self.assertNotIn("actions/download-artifact", workflow)
        self.assertNotIn("actions/upload-artifact", workflow)
        self.assertIn("qikvrt_requested_review_target.py", workflow)
        self.assertIn("QIKVRT CI", workflow)
        self.assertIn("QIK-VRT requested review signal", workflow)
        self.assertIn("--workflow-run-id", workflow)
        self.assertIn("--expected-workflow-path", workflow)
        self.assertIn("--expected-event", workflow)
        self.assertIn("WORKFLOW_RUN_EVENT", workflow)
        self.assertIn('if [ "$WORKFLOW_RUN_EVENT" != "$EXPECTED_WORKFLOW_EVENT" ]; then', workflow)
        self.assertIn('printf \'{"pull_request":null}\\n\' > "$selection"', workflow)
        self.assertIn("--commit-sha", workflow)
        self.assertIn("pull_requests", workflow)
        self.assertIn(
            "qikvrt-requested-review-lifecycle-${{ github.repository }}-${{ matrix.pull_request }}",
            workflow,
        )
        self.assertNotIn(
            "group: qikvrt-requested-review-lifecycle-${{ github.repository }}\n",
            workflow,
        )
        self.assertNotIn("\n  check_run:\n", workflow)
        self.assertIn("qikvrt_requested_review_snapshot.py", workflow)
        self.assertIn("qikvrt_requested_review_lifecycle.py evaluate", workflow)
        self.assertIn("Reobserve immediately before a lifecycle write", workflow)
        self.assertIn("Reobserve final exact requested-review state", workflow)
        self.assertIn('"commit_id=${head}"', workflow)
        self.assertIn("created lifecycle review is not bound to the expected head", workflow)
        self.assertIn("COMMENT_WITH_BLOCKER", workflow)
        disposition_token = 'print("<!-- qikvrt-review-disposition:COMMENT_WITH_BLOCKER -->")'
        marker_render = 'print(value["review_marker"])'
        self.assertIn(disposition_token, workflow)
        self.assertIn(marker_render, workflow)
        self.assertLess(workflow.index(disposition_token), workflow.index(marker_render))
        self.assertIn("observed_exact_head_review_states", workflow)
        self.assertIn("without inferring it absent", workflow)
        self.assertIn("MAX_EXCERPT_ITEMS = 16", workflow)
        self.assertIn("def safe_json(value):", workflow)
        self.assertIn("def markdown_json(value):", workflow)
        self.assertIn('return "`" + safe_json(value) + "`"', workflow)
        self.assertIn('.replace("@", "\\\\u0040")', workflow)
        self.assertIn('body_bytes="$(wc -c < /tmp/qikvrt-requested-review.md)"', workflow)
        self.assertIn('[ "$body_bytes" -gt 60000 ]', workflow)
        self.assertNotIn("join(f'`{path}`'", workflow)
        self.assertIn("-f event=COMMENT", workflow)
        self.assertNotIn("event=APPROVE", workflow)
        self.assertNotIn("/merge", workflow)

    def test_pr_controlled_review_excerpt_is_a_single_inert_markdown_code_span(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"python3 -B - <<'PY' > /tmp/qikvrt-requested-review\.md\n"
            r"(?P<helpers>.*?)\n          value = json\.load",
            workflow,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        namespace: dict[str, object] = {}
        exec(textwrap.dedent(match.group("helpers")), namespace)
        rendered = namespace["markdown_json"](
            ["![remote](https://attacker.invalid/pixel.png) @mention ` <html> &"]
        )
        self.assertTrue(rendered.startswith("`") and rendered.endswith("`"))
        self.assertEqual(rendered.count("`"), 2)
        self.assertNotIn("@mention", rendered)
        self.assertNotIn("<html>", rendered)
        self.assertIn("![remote](https://attacker.invalid/pixel.png)", rendered)

    def test_review_signal_default_definition_is_non_authoritative_and_exports_no_data(self) -> None:
        signal = SIGNAL_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_review", signal)
        self.assertIn("permissions: {}", signal)
        self.assertNotIn("actions/checkout", signal)
        self.assertNotIn("gh api", signal)
        self.assertNotIn("actions/upload-artifact", signal)
        self.assertNotIn("actions/download-artifact", signal)
        self.assertNotIn("pull-requests: write", signal)
        documentation = (ROOT / "docs/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("security\nauthority", documentation)
        self.assertIn("Repository Actions settings", documentation)

    def test_snapshot_is_complete_and_paginated(self) -> None:
        source = SNAPSHOT.read_text(encoding="utf-8")
        self.assertIn("issues/{number}/comments", source)
        self.assertIn("issues/{number}/events", source)
        self.assertIn("pulls/{number}/files", source)
        self.assertIn("application/vnd.github.diff", source)
        self.assertIn("reviewThreads(first: 100, after: $after)", source)
        self.assertIn("hasNextPage", source)
        self.assertIn("check-runs?per_page=100&filter=latest", source)
        self.assertIn("statuses?per_page=100", source)
        self.assertIn("merge_commit_sha", source)
        self.assertIn("gate_observations", source)
        self.assertIn("OBSERVED_ACTIONS_AND_LEGACY_ONLY", source)
        self.assertIn("requested_reviewer_history", source)
        self.assertIn("review_request_removed", source)
        self.assertIn("requested_team_history", source)
        self.assertIn("/pulls?state=open&head=", source)
        self.assertIn("final pull request", source)
        self.assertIn("existing_lifecycle_reviews", source)

    def test_target_resolver_requires_one_current_open_pr_for_commit_and_run_events(self) -> None:
        source = TARGET.read_text(encoding="utf-8")
        self.assertIn("commits/{head}/pulls?per_page=100", source)
        self.assertIn("multiple open pull requests", source)
        self.assertIn("state", source)
        self.assertIn("actions/runs/{run_id}", source)
        self.assertIn("pull_requests", source)
        self.assertIn("expected workflow path", source)
        self.assertIn("resolve_unique_open_pull_request_for_commit", source)

    def test_gate_source_catalog_covers_each_unique_pr_workflow_without_self_trigger(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        configured = policy["review_lifecycle"]["executor"]["gate_completion_workflows"]
        self.assertEqual(len(configured), len(set(configured)))
        local = self.pull_request_workflows()
        self.assertEqual(set(configured), set(local))
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for name, path in local.items():
            self.assertIn(f"- {name}", workflow)
            self.assertIn(f'"{name}") EXPECTED_WORKFLOW_PATH="{path}"', workflow)
        self.assertIn("- QIK-VRT requested review signal", workflow)
        self.assertNotIn("- QIK-VRT requested review lifecycle\n", workflow)

    def test_work_unit_has_required_provenance_and_false_release_claims(self) -> None:
        required = set(
            json.loads(ORIGIN_POLICY.read_text(encoding="utf-8"))["contribution_provenance"][
                "required_fields"
            ]
        )
        work_unit = json.loads(WORK_UNIT.read_text(encoding="utf-8"))
        self.assertTrue(required.issubset(work_unit))
        self.assertEqual(
            work_unit["release_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )
        self.assertFalse(work_unit["git_history"]["force_push"])
        self.assertFalse(work_unit["git_history"]["history_rewrite"])


if __name__ == "__main__":
    unittest.main()
