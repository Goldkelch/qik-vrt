#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import pathlib
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

# Execute the actual workflow shell with a strict local GitHub fixture. No
# network, credentials, scheduler, alternate controller or remote write is used.
import json
import os
import shutil
import subprocess
import sys
import tempfile

MARKER = '<!-- qikvrt-universal-terminal-live-surface-v2 -->'
LEGACY_MARKER = '<!-- qikvrt-universal-terminal-live-surface-v1 -->'
HEAD = 'a' * 40
TREE = 'b' * 40
BOT = {'login': 'github-actions[bot]', 'type': 'Bot'}
FAKE_GH = r'''
import json, os, pathlib, subprocess, sys
from urllib.parse import parse_qs, urlsplit
root = pathlib.Path(os.environ['FIXTURE_ROOT'])
config = json.loads((root / 'fixture.json').read_text())
args = sys.argv[1:]
assert args.pop(0) == 'api'
method, expression, body, endpoint = 'GET', None, None, None
while args:
    item = args.pop(0)
    if item == '--method': method = args.pop(0)
    elif item == '--jq': expression = args.pop(0)
    elif item == '-f':
        field = args.pop(0)
        assert field.startswith('body=')
        body = field[5:]
    elif item.startswith('-'): raise AssertionError(item)
    else:
        assert endpoint is None
        endpoint = item
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'method': method, 'endpoint': endpoint}) + '\n')
prefix = 'repos/Goldkelch/qik-vrt/'
assert endpoint.startswith(prefix), endpoint
path = endpoint[len(prefix):]
saved = root / 'saved.json'
if path.startswith('issues/1105/comments?'):
    if config.get('rate_limited'):
        print('HTTP 403: API rate limit exceeded for installation', file=sys.stderr)
        sys.exit(1)
    query = parse_qs(urlsplit(path).query)
    size = int(query.get('per_page', ['30'])[0])
    page = int(query.get('page', ['1'])[0])
    comments = config['comments']
    if saved.exists():
        obj = json.loads(saved.read_text())
        comments = [x for x in comments if x['id'] != obj['id']] + [obj]
    result = comments[(page-1)*size:page*size]
elif path.startswith('git/commits/'):
    result = {'tree': {'sha': 'b'*40}}
elif path == 'pulls/1105':
    result = {'head': {'sha': 'a'*40}}
elif method in ('PATCH', 'POST'):
    assert path == 'issues/1105/comments' or path.startswith('issues/comments/')
    if config.get('write_failed'): sys.exit(1)
    ident = int(path.rsplit('/', 1)[1]) if method == 'PATCH' else 999
    result = {'id': ident, 'body': body, 'user': {'login': 'github-actions[bot]', 'type': 'Bot'}, 'issue_url': 'https://api.github.com/repos/Goldkelch/qik-vrt/issues/1105'}
    saved.write_text(json.dumps(result))
elif path.startswith('issues/comments/'):
    result = json.loads(saved.read_text())
    if config.get('readback_mismatch'): result['body'] = 'concurrent replacement'
    if config.get('foreign_issue'): result['issue_url'] = 'https://api.github.com/repos/Goldkelch/qik-vrt/issues/999'
else:
    raise AssertionError(path)
text = json.dumps(result)
if expression is not None:
    process = subprocess.run([os.environ['REAL_JQ'], '-r', expression], input=text, text=True, capture_output=True, check=True)
    print(process.stdout, end='')
else:
    print(text)
'''


class LiveStatusExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(shutil.which('bash'), 'declared bash runtime is required')
        self.assertIsNotNone(shutil.which('jq'), 'declared jq runtime is required')
        self.temp = tempfile.TemporaryDirectory(prefix='qikvrt-live-status-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        fake = self.root / 'gh'
        fake.write_text('#!' + sys.executable + '\n' + FAKE_GH, encoding='utf-8')
        fake.chmod(0o700)
        text = WORKFLOW.read_text(encoding='utf-8')
        declared_markers = [line.strip().split(': ', 1)[1].strip("'")
                            for line in text.splitlines() if line.strip().startswith('MARKER: ')]
        self.assertEqual(len(declared_markers), 1)
        self.declared_marker = declared_markers[0]
        self.assertEqual(text.count('        run: |\n'), 1)
        block = text.split('        run: |\n', 1)[1].split('\n      - ', 1)[0]
        self.shell = '\n'.join(line[10:] if line.startswith('          ') else line for line in block.splitlines()) + '\n'

    def comment(self, ident: int = 77, body: str | None = None) -> dict:
        return {'id': ident, 'body': body if body is not None else MARKER + '\n\n## Live event journal\n- `before` **OBSERVE** · old event\n', 'user': BOT, 'issue_url': 'https://api.github.com/repos/Goldkelch/qik-vrt/issues/1105'}

    def event(self, kind: str, state: str = 'success') -> dict:
        pr = {'number': 1105, 'head': {'sha': HEAD}, 'issue_url': 'https://api.github.com/repos/Goldkelch/qik-vrt/issues/1105'}
        if kind == 'workflow_run':
            return {'action': 'completed' if state == 'success' else 'in_progress', 'workflow_run': {'id': 99, 'run_attempt': 2, 'head_sha': HEAD, 'name': 'QIKVRT CI', 'status': 'completed' if state == 'success' else state, 'conclusion': 'success' if state == 'success' else None, 'html_url': 'https://github.com/Goldkelch/qik-vrt/actions/runs/99', 'pull_requests': [{'number': 1105}]}}
        if kind == 'pull_request_review':
            return {'action': 'submitted', 'pull_request': pr, 'review': {'commit_id': 'c'*40, 'state': 'approved', 'user': {'login': 'reviewer'}}}
        if kind == 'issue_comment':
            return {'action': 'created', 'issue': {'number': 1105, 'pull_request': {'url': 'https://api.github.com/repos/Goldkelch/qik-vrt/pulls/1105'}}, 'comment': {'body': 'ordinary comment', 'user': {'login': 'user'}}}
        return {'action': 'synchronize', 'pull_request': pr}

    def run_event(self, kind: str = 'workflow_run', comments: list | None = None, event: dict | None = None, attempt: int = 1, **flags) -> subprocess.CompletedProcess:
        if comments is not None:
            (self.root / 'fixture.json').write_text(json.dumps({'comments': comments, **flags}), encoding='utf-8')
        (self.root / 'event.json').write_text(json.dumps(event if event is not None else self.event(kind)), encoding='utf-8')
        env = {'PATH': str(self.root) + os.pathsep + os.environ['PATH'], 'HOME': str(self.root), 'FIXTURE_ROOT': str(self.root), 'REAL_JQ': shutil.which('jq'), 'REPOSITORY': 'Goldkelch/qik-vrt', 'GITHUB_EVENT_PATH': str(self.root / 'event.json'), 'EVENT_NAME': kind, 'DISPATCH_PR': '1105', 'MARKER': self.declared_marker, 'GITHUB_RUN_ID': '700', 'GITHUB_RUN_ATTEMPT': str(attempt), 'RUNNER_TEMP': str(self.root)}
        return subprocess.run(['bash', '-e', '-o', 'pipefail'], input=self.shell, text=True, capture_output=True, timeout=20, env=env)

    def calls(self) -> list:
        path = self.root / 'calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def writes(self) -> list:
        return [x for x in self.calls() if x['method'] in ('PATCH', 'POST')]

    def saved(self) -> dict:
        return json.loads((self.root / 'saved.json').read_text())

    def test_workflow_event_without_issue_url_reads_back_exact_object(self) -> None:
        result = self.run_event(comments=[self.comment()])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PROJECTION_READBACK_OK', result.stdout)
        self.assertEqual(self.calls()[-1], {'method': 'GET', 'endpoint': 'repos/Goldkelch/qik-vrt/issues/comments/77'})
        self.assertIn(HEAD, self.saved()['body'])
        self.assertIn(TREE, self.saved()['body'])
        self.assertIn('old event', self.saved()['body'])
        self.assertNotIn('**EFFECT**', self.saved()['body'])
        self.assertNotIn('**Current exact subject:**', self.saved()['body'])

    def test_surface_after_twentieth_comment_is_not_recreated(self) -> None:
        comments = [self.comment(i, 'ordinary') for i in range(1, 22)] + [self.comment()]
        result = self.run_event('pull_request', comments=comments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([x['method'] for x in self.writes()], ['PATCH'])
        self.assertEqual(self.saved()['id'], 77)

    def test_second_page_surface_is_preserved(self) -> None:
        comments = [self.comment(i, 'ordinary') for i in range(1000, 1100)] + [self.comment()]
        result = self.run_event(comments=comments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([x['method'] for x in self.writes()], ['PATCH'])
        self.assertEqual(len([x for x in self.calls() if '?' in x['endpoint']]), 2)

    def test_exhausted_inventory_budget_performs_no_write(self) -> None:
        comments = [self.comment(i, 'ordinary') for i in range(1000, 1500)]
        result = self.run_event(comments=comments)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('inventory exceeds five pages', result.stderr)
        self.assertEqual(len(self.calls()), 5)
        self.assertEqual(self.writes(), [])

    def test_rate_limit_is_not_retried_or_masked(self) -> None:
        result = self.run_event(comments=[], rate_limited=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(self.writes(), [])

    def test_duplicate_source_transition_does_not_write_again(self) -> None:
        result = self.run_event(comments=[self.comment()])
        self.assertEqual(result.returncode, 0, result.stderr)
        again = self.run_event(attempt=2)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn('PROJECTION_ALREADY_PRESENT', again.stdout)
        self.assertEqual(len(self.writes()), 1)

    def test_distinct_workflow_transitions_are_not_deduplicated(self) -> None:
        first = self.run_event(comments=[self.comment()], event=self.event('workflow_run', 'in_progress'))
        second = self.run_event()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(len(self.writes()), 2)
        self.assertIn('workflow_run:99:2:in_progress', self.saved()['body'])
        self.assertIn('workflow_run:99:2:success', self.saved()['body'])

    def test_write_ack_without_matching_readback_fails(self) -> None:
        result = self.run_event(comments=[self.comment()], readback_mismatch=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PROJECTION_READBACK_OK', result.stdout)

    def test_failed_write_is_not_retried(self) -> None:
        result = self.run_event(comments=[self.comment()], write_failed=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.writes()), 1)
        self.assertNotIn('PROJECTION_READBACK_OK', result.stdout)

    def test_duplicate_surfaces_fail_without_overwriting_either(self) -> None:
        result = self.run_event(comments=[self.comment(), self.comment(78)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate live-surface', result.stderr)
        self.assertEqual(self.writes(), [])

    def test_marker_in_human_comment_does_not_authorize_overwrite(self) -> None:
        forged = self.comment()
        forged['user'] = {'login': 'someone', 'type': 'User'}
        result = self.run_event(comments=[forged])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([x['method'] for x in self.writes()], ['POST'])
        self.assertEqual(self.saved()['id'], 999)

    def test_review_is_bound_to_reviewed_commit_not_new_pr_head(self) -> None:
        result = self.run_event('pull_request_review', comments=[self.comment()])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PR #1105 @ ' + 'c'*40, self.saved()['body'])
        self.assertNotIn('PR #1105 @ ' + HEAD, self.saved()['body'])

    def test_self_projection_event_uses_no_api_calls(self) -> None:
        event = self.event('issue_comment')
        event['comment'] = {'body': MARKER, 'user': BOT, 'issue_url': 'https://api.github.com/repos/Goldkelch/qik-vrt/issues/1105'}
        result = self.run_event('issue_comment', comments=[], event=event)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_issue_comment_and_dispatch_use_repository_scoped_paths(self) -> None:
        for kind in ('issue_comment', 'workflow_dispatch'):
            result = self.run_event(kind, comments=[self.comment()])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(x['endpoint'].startswith('repos/Goldkelch/qik-vrt/') for x in self.calls()))


    def receipt(self) -> dict:
        return json.loads((self.root / 'qikvrt-live-status-readback.json').read_text())

    def set_flags(self, **flags) -> None:
        path = self.root / 'fixture.json'
        value = json.loads(path.read_text())
        value.update(flags)
        path.write_text(json.dumps(value))

    def test_duplicate_transition_still_requires_exact_readback(self) -> None:
        first = self.run_event(comments=[self.comment()])
        self.assertEqual(first.returncode, 0, first.stderr)
        self.set_flags(readback_mismatch=True)
        again = self.run_event(attempt=2)
        self.assertNotEqual(again.returncode, 0)
        self.assertNotIn('PROJECTION_READBACK_OK', again.stdout)
        self.assertNotIn('PROJECTION_ALREADY_PRESENT', again.stdout)
        self.assertEqual(len(self.writes()), 1)
        self.assertFalse((self.root / 'qikvrt-live-status-readback.json').exists())

    def test_duplicate_id_cannot_hide_conflicting_source_payload(self) -> None:
        first = self.run_event(comments=[self.comment()])
        self.assertEqual(first.returncode, 0, first.stderr)
        path = self.root / 'saved.json'
        value = self.saved()
        value['body'] = value['body'].replace('PR #1105 @ ' + HEAD, 'PR #1105 @ ' + 'd'*40)
        path.write_text(json.dumps(value))
        again = self.run_event(attempt=2)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn('conflicting source transition', again.stderr)
        self.assertEqual(len(self.writes()), 1)

    def test_readback_from_another_issue_is_rejected(self) -> None:
        result = self.run_event(comments=[self.comment()], foreign_issue=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PROJECTION_READBACK_OK', result.stdout)
        self.assertFalse((self.root / 'qikvrt-live-status-readback.json').exists())

    def test_scoped_receipt_binds_readback_and_duplicate_without_effect(self) -> None:
        first = self.run_event(comments=[self.comment()])
        self.assertEqual(first.returncode, 0, first.stderr)
        receipt = self.receipt()
        self.assertEqual(receipt['source_head'], HEAD)
        self.assertEqual(receipt['source_tree'], TREE)
        self.assertEqual(receipt['event_id'], 'workflow_run:99:2:success')
        self.assertEqual(receipt['comment_id'], 77)
        self.assertEqual(receipt['body_sha256'], hashlib.sha256(self.saved()['body'].encode()).hexdigest())
        self.assertTrue(receipt['readback_verified'])
        self.assertTrue(receipt['write_performed'])
        self.assertFalse(receipt['duplicate'])
        self.assertFalse(receipt['effect_ack_done'])
        self.assertEqual(receipt['binding_scope'], 'HISTORICAL_EVENT_SOURCE')
        second = self.run_event(attempt=2)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(self.receipt()['duplicate'])
        self.assertFalse(self.receipt()['write_performed'])
        self.assertEqual(receipt['body_sha256'], self.receipt()['body_sha256'])
        self.assertEqual(self.calls()[-1], {'method': 'GET', 'endpoint': 'repos/Goldkelch/qik-vrt/issues/comments/77'})

    def test_historical_duplicate_survives_a_newer_displayed_header(self) -> None:
        first = self.run_event(comments=[self.comment()])
        self.assertEqual(first.returncode, 0, first.stderr)
        value = self.saved()
        value['body'] = value['body'].replace('**Observed event subject:** `PR #1105 @ ' + HEAD, '**Observed event subject:** `PR #1105 @ ' + 'c'*40)
        (self.root / 'saved.json').write_text(json.dumps(value))
        again = self.run_event(attempt=2)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(len(self.writes()), 1)
        self.assertTrue(self.receipt()['duplicate'])
        self.assertEqual(self.receipt()['source_head'], HEAD)

    def test_workflow_run_and_pr_events_share_the_pr_serialization_key(self) -> None:
        source = WORKFLOW.read_text()
        self.assertIn('github.event.workflow_run.pull_requests[0].number ||', source)
        self.assertIn('qikvrt-live-status-readback.json', source)
        self.assertIn('actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a', source)


    def test_multiple_lines_for_one_source_identifier_are_conflicting(self) -> None:
        first = self.run_event(comments=[self.comment()])
        self.assertEqual(first.returncode, 0, first.stderr)
        value = self.saved()
        value['body'] += '\n- `conflict` **OBSERVE** · different payload · event `workflow_run:99:2:success`\n'
        (self.root / 'saved.json').write_text(json.dumps(value))
        again = self.run_event(attempt=2)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn('conflicting source transition', again.stderr)
        self.assertEqual(len(self.writes()), 1)


    def test_declared_marker_isolated_from_legacy_default_branch(self) -> None:
        self.assertEqual(self.declared_marker, MARKER)
        self.assertNotIn(LEGACY_MARKER, self.declared_marker)

    def test_legacy_surface_is_not_adopted_or_copied(self) -> None:
        legacy = self.comment(76, LEGACY_MARKER + '\n\n## Live event journal\n- `old` **EFFECT** · predecessor\n')
        result = self.run_event('pull_request', comments=[legacy])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([x['method'] for x in self.writes()], ['POST'])
        self.assertEqual(self.saved()['id'], 999)
        self.assertTrue(self.saved()['body'].startswith(MARKER))
        self.assertNotIn(LEGACY_MARKER, self.saved()['body'])
        self.assertNotIn('**EFFECT**', self.saved()['body'])

    def test_versioned_inventory_updates_only_current_surface(self) -> None:
        legacy = self.comment(76, LEGACY_MARKER + '\nlegacy history')
        result = self.run_event(comments=[legacy, self.comment()])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.writes(), [{'method': 'PATCH', 'endpoint': 'repos/Goldkelch/qik-vrt/issues/comments/77'}])
        self.assertNotIn(LEGACY_MARKER, self.saved()['body'])

    def test_legacy_writer_selector_cannot_select_new_surface(self) -> None:
        legacy = self.comment(76, LEGACY_MARKER + '\nlegacy history')
        result = self.run_event('pull_request', comments=[legacy])
        self.assertEqual(result.returncode, 0, result.stderr)
        # Execute Main a8605413's actual contains-marker selection. The v2
        # body is last: if selected, a legacy event would overwrite it.
        selected = subprocess.run(
            ['jq', '-r', '--arg', 'marker', LEGACY_MARKER,
             '.[] | select(.body | contains($marker)) | .id'],
            input=json.dumps([legacy, self.saved()]), text=True,
            capture_output=True, timeout=5, check=True,
        )
        self.assertEqual(selected.stdout.splitlines(), ['76'])
        self.assertNotIn(str(self.saved()['id']), selected.stdout.splitlines())



if __name__ == "__main__":
    unittest.main()
