#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"


class LiveStatusCarrierClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_surface_failures_are_classification_inputs_not_terminal_hold(self) -> None:
        self.assertIn(
            "failure|cancelled|action_required|timed_out) verb='CLASSIFY'",
            self.text,
        )
        self.assertNotIn("verb='HOLD'", self.text)

    def test_surface_documents_missing_carrier_exhaustion_proof(self) -> None:
        self.assertIn("all issue, PR and branch", self.text)
        self.assertIn("cannot authoritatively emit HOLD", self.text)

    def test_projection_remains_event_driven(self) -> None:
        self.assertIn("workflow_run:", self.text)
        self.assertIn("issue_comment:", self.text)
        self.assertIn("pull_request:", self.text)
        self.assertNotIn("schedule:", self.text)

    def test_direct_review_executor_successor_cannot_project_a_merge_execution_head(self) -> None:
        self.assertIn("source_event=", self.text)
        self.assertIn("QIKVRT requested review executor", self.text)
        self.assertIn('"$source_event" = pull_request_review', self.text)
        self.assertIn('"$source_event" = pull_request_review_comment', self.text)
        self.assertIn("workflow-run head is an execution SHA", self.text)
        self.assertIn("exit 0", self.text)


class LiveStatusProjectionExecutionTests(unittest.TestCase):
    """Execute the actual workflow shell against local API fixtures only."""

    def run_projection(self, *, mode="existing", mismatch="", state="success", no_pr=False):
        text = WORKFLOW.read_text(encoding="utf-8")
        marker = "        run: |\n"
        self.assertEqual(text.count(marker), 1)
        script = textwrap.dedent(text.split(marker, 1)[1])
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            event = {
                "workflow_run": {
                    "pull_requests": [] if no_pr else [{"number": 1118}],
                    "head_sha": "4f948e4c26487c33aa8b6267ed5fe6e3bfa8c192",
                    "name": "QIKVRT CI", "event": "pull_request",
                    "conclusion": state, "status": "completed", "id": 701,
                    "html_url": "https://github.com/Goldkelch/qik-vrt/actions/runs/701",
                }
            }
            event_path = directory / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")
            executable = directory / "gh"
            executable.write_text(textwrap.dedent(r"""
                #!/usr/bin/env python3
                import json, os, pathlib, sys
                root = pathlib.Path(os.environ['FIXTURE_ROOT'])
                args = sys.argv[1:]
                with (root / 'calls.jsonl').open('a', encoding='utf-8') as log:
                    log.write(json.dumps(args) + '\n')
                assert args[0] == 'api', args
                base = 'repos/Goldkelch/qik-vrt'
                if args[1:] == [base + '/issues/1118/comments?per_page=100']:
                    mode = os.environ['FIXTURE_MODE']
                    comments = [] if mode == 'new' else [{
                        'id': 88 if mode == 'human' else 123,
                        'body': os.environ['MARKER'] + '\nprevious projection',
                        'user': {'login': 'human' if mode == 'human' else 'github-actions[bot]'},
                    }]
                    print(json.dumps(comments))
                elif len(args) > 3 and args[1] == '--method':
                    method, endpoint = args[2:4]
                    assert method in {'POST', 'PATCH'}, args
                    if os.environ['FIXTURE_MISMATCH'] == 'write_failure':
                        print('HTTP 403: API rate limit exceeded for installation', file=sys.stderr)
                        raise SystemExit(1)
                    assert endpoint in {base + '/issues/1118/comments', base + '/issues/comments/123', base + '/issues/comments/88'}, args
                    field = args[args.index('-f') + 1]
                    assert field.startswith('body='), args
                    value = {'id': 123, 'body': field[5:], 'user': {'login': 'github-actions[bot]'},
                             'issue_url': 'https://api.github.com/' + base + '/issues/1118'}
                    (root / 'stored.json').write_text(json.dumps(value), encoding='utf-8')
                    if '--jq' in args:
                        assert args[args.index('--jq') + 1] == '.id', args
                        print(value['id'])
                    else:
                        print(json.dumps(value))
                elif args[1:] == [base + '/issues/comments/123']:
                    value = json.loads((root / 'stored.json').read_text(encoding='utf-8'))
                    mismatch = os.environ['FIXTURE_MISMATCH']
                    if mismatch == 'body': value['body'] += '\nstale concurrent projection'
                    if mismatch == 'id': value['id'] = 124
                    if mismatch == 'author': value['user']['login'] = 'human'
                    if mismatch == 'issue': value['issue_url'] = value['issue_url'].replace('1118', '1119')
                    if mismatch == 'missing': value = {}
                    if mismatch == 'malformed':
                        print('not JSON')
                        raise SystemExit(0)
                    if mismatch == 'quota':
                        print('HTTP 403: API rate limit exceeded for installation', file=sys.stderr)
                        raise SystemExit(1)
                    print(json.dumps(value))
                else:
                    raise AssertionError('unexpected API request: ' + repr(args))
            """).lstrip("\n"), encoding="utf-8")
            executable.chmod(0o755)
            env = {**os.environ,
                   "PATH": str(directory) + os.pathsep + os.environ.get("PATH", ""),
                   "FIXTURE_ROOT": str(directory), "FIXTURE_MODE": mode,
                   "FIXTURE_MISMATCH": mismatch, "GITHUB_EVENT_PATH": str(event_path),
                   "GITHUB_RUN_ID": "702", "GITHUB_RUN_ATTEMPT": "1",
                   "EVENT_NAME": "workflow_run", "REPOSITORY": "Goldkelch/qik-vrt",
                   "DISPATCH_PR": "", "GH_TOKEN": "synthetic-fixture-not-a-credential",
                   "MARKER": "<!-- qikvrt-universal-terminal-live-surface-v1 -->"}
            result = subprocess.run(["bash", "--noprofile", "--norc", "-c", script],
                                    env=env, text=True, capture_output=True, timeout=15)
            calls_path = directory / "calls.jsonl"
            calls = [json.loads(line) for line in calls_path.read_text().splitlines()] if calls_path.exists() else []
            stored_path = directory / "stored.json"
            stored = json.loads(stored_path.read_text()) if stored_path.exists() else None
            return result, calls, stored

    def test_workflow_success_is_observation_not_external_effect(self):
        result, _, stored = self.run_projection()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Last transition:** **OBSERVE**", stored["body"])
        self.assertNotIn("**EFFECT**", stored["body"])

    def test_existing_projection_requires_separate_exact_readback(self):
        result, calls, _ = self.run_projection()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][1:3], ["--method", "PATCH"])
        self.assertEqual(calls[2], ["api", "repos/Goldkelch/qik-vrt/issues/comments/123"])
        self.assertIn("PROJECTION_READBACK=VERIFIED", result.stdout)
        self.assertIn("EXTERNAL_EFFECT=NOT_ESTABLISHED", result.stdout)

    def test_new_projection_reads_back_returned_comment_identity(self):
        result, calls, _ = self.run_projection(mode="new")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][1:3], ["--method", "POST"])
        self.assertEqual(calls[2], ["api", "repos/Goldkelch/qik-vrt/issues/comments/123"])

    def test_mismatched_missing_or_failed_readback_never_closes_projection(self):
        for mismatch in ("body", "id", "author", "issue", "missing", "malformed", "quota"):
            with self.subTest(mismatch=mismatch):
                result, calls, _ = self.run_projection(mismatch=mismatch)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("PROJECTION_READBACK=VERIFIED", result.stdout)
                self.assertEqual(len(calls), 3)
                self.assertEqual(sum('--method' in call for call in calls), 1)

    def test_write_failure_is_not_retried_or_reported_as_readback(self):
        result, calls, _ = self.run_projection(mismatch="write_failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("PROJECTION_READBACK=VERIFIED", result.stdout)

    def test_human_marker_is_not_an_automation_owned_update_target(self):
        result, calls, _ = self.run_projection(mode="human")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1][1:3], ["--method", "POST"])
        self.assertEqual(calls[-1], ["api", "repos/Goldkelch/qik-vrt/issues/comments/123"])

    def test_source_failure_remains_classification_after_successful_projection(self):
        result, _, stored = self.run_projection(state="failure")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("**Last transition:** **CLASSIFY**", stored["body"])
        self.assertNotIn("**EFFECT**", stored["body"])

    def test_unbound_workflow_event_performs_no_api_request(self):
        result, calls, stored = self.run_projection(no_pr=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])
        self.assertIsNone(stored)
        self.assertNotIn("PROJECTION_READBACK=VERIFIED", result.stdout)


if __name__ == "__main__":
    unittest.main()
