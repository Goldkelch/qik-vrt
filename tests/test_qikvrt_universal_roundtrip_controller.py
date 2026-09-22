# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'roundtrip_controller_under_test', ROOT / 'tools/qikvrt_universal_roundtrip_controller.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
REPO = 'Goldkelch/qik-vrt'
HEAD, TREE = 'a' * 40, 'b' * 40
SUBJECT = M.bind_subject(REPO, HEAD, TREE)


def run(workflow=M.CARRIERS[0], status='completed', conclusion='success', **changes):
    result = {'id': 42, 'path': M.carrier_path(workflow), 'head_sha': HEAD,
              'head_branch': 'main', 'status': status, 'conclusion': conclusion}
    result.update(changes)
    return result


class Boundaries(unittest.TestCase):
    def test_unknown_carrier_is_rejected(self):
        with self.assertRaises(M.BoundaryError):
            M.carrier_path('../../untrusted.yml')

    def test_bad_repository_is_rejected(self):
        with self.assertRaises(M.BoundaryError):
            M.bind_subject('repo/../../other', HEAD, TREE)

    def test_unknown_tree_is_rejected(self):
        with self.assertRaises(M.BoundaryError):
            M.bind_subject(REPO, HEAD, '')

    def test_previous_head_cannot_supply_evidence(self):
        with self.assertRaisesRegex(M.BoundaryError, 'MISMATCH'):
            M.classify_run(run(head_sha='c' * 40), [], M.CARRIERS[0], SUBJECT)

    def test_wrong_workflow_cannot_supply_evidence(self):
        with self.assertRaises(M.BoundaryError):
            M.classify_run(run(path='.github/workflows/other.yml'), [], M.CARRIERS[0], SUBJECT)

    def test_zero_job_success_is_not_execution(self):
        self.assertEqual(M.classify_run(run(), [], M.CARRIERS[0], SUBJECT),
                         'TERMINAL_WITHOUT_ADMITTED_JOBS')

    def test_action_required_is_not_success(self):
        self.assertEqual(M.classify_run(run(conclusion='action_required'), [],
                                       M.CARRIERS[0], SUBJECT),
                         'TERMINAL_WITHOUT_ADMITTED_JOBS')

    def test_all_skipped_is_not_success(self):
        self.assertEqual(M.classify_run(run(), [{'conclusion': 'skipped'}],
                                       M.CARRIERS[0], SUBJECT), 'NO_SUCCESSFUL_JOB')

    def test_green_execution_is_not_effect_ack(self):
        self.assertEqual(M.classify_run(run(), [{'conclusion': 'success'}],
                                       M.CARRIERS[0], SUBJECT),
                         'NATIVE_CARRIER_COMPLETED_NOT_EFFECT_ACK')

    def test_queued_without_jobs_is_not_admitted(self):
        self.assertEqual(M.classify_run(run(status='queued', conclusion=None), [],
                                       M.CARRIERS[0], SUBJECT), 'ADMISSION_NOT_OBSERVED')

    def test_unknown_status_fails_closed(self):
        with self.assertRaises(M.BoundaryError):
            M.classify_run(run(status='mystery'), [], M.CARRIERS[0], SUBJECT)

    def test_terminal_failure_is_not_blindly_retried(self):
        self.assertIsNone(M.choose_carrier([M.CARRIERS[0]],
                                           [run(conclusion='failure')], HEAD, [])[0])

    def test_active_execution_is_reobserved_not_duplicated(self):
        active = run(status='in_progress', conclusion=None)
        self.assertEqual(M.choose_carrier([M.CARRIERS[0]], [active], HEAD, [active])[2],
                         'OBSERVE_EXISTING')

    def test_active_writer_does_not_block_read_only_watchdog(self):
        writer = run(M.CARRIERS[1], status='in_progress')
        self.assertEqual(M.choose_carrier([M.CARRIERS[0]], [], HEAD, [writer])[2], 'DISPATCH')

    def test_active_writer_prevents_second_writer(self):
        writer = run(M.CARRIERS[3], status='in_progress', head_sha='d' * 40)
        self.assertIsNone(M.choose_carrier([M.CARRIERS[1]], [], HEAD, [writer])[0])

    def test_ci_execution_does_not_become_a_global_writer_lock(self):
        ci = run(path='.github/workflows/qikvrt_ci.yml', name='QIKVRT CI', status='in_progress')
        self.assertEqual(M.choose_carrier([M.CARRIERS[1]], [], HEAD, [ci])[2], 'DISPATCH')

    def test_materializer_is_an_actual_writer(self):
        writer = run(path='.github/workflows/qikvrt_batch04_integrity.yml',
                     name='QIKVRT repository evidence materialization', status='in_progress')
        self.assertIsNone(M.choose_carrier([M.CARRIERS[1]], [], HEAD, [writer])[0])

    def test_missing_token_is_not_execution_authority(self):
        with self.assertRaises(M.BoundaryError):
            M.GitHubAPI(REPO, '')

    def test_api_write_surface_is_only_allowlisted_dispatch(self):
        api = M.GitHubAPI(REPO, 'test-token-never-transmitted')
        with patch.object(M.urllib.request, 'urlopen') as transport:
            for path, body in (
                ('repos/' + REPO + '/git/refs/heads/main', {'sha': HEAD}),
                ('repos/' + REPO + '/actions/workflows/other.yml/dispatches', {'ref': 'main'}),
                ('repos/' + REPO + '/actions/workflows/' + M.CARRIERS[0] + '/dispatches',
                 {'ref': 'untrusted-pr', 'return_run_details': True}),
                ('repos/' + REPO + '/../other/actions/runs', None),
            ):
                with self.subTest(path=path), self.assertRaises(M.BoundaryError):
                    api(path, body)
            transport.assert_not_called()

    def test_active_watchdog_does_not_starve_independent_repair(self):
        watchdog = run(status='in_progress', conclusion=None)
        workflow, _, action = M.choose_carrier(list(M.CARRIERS[:2]), [watchdog], HEAD, [watchdog])
        self.assertEqual(workflow, M.CARRIERS[1])
        self.assertEqual(action, 'DISPATCH')

    def test_forks_do_not_enable_pr_writer(self):
        pr = {'draft': True, 'body': M.OPT_IN,
              'head': {'repo': {'full_name': 'other/fork'}}}
        self.assertEqual(M.eligible_carriers([pr], REPO), list(M.CARRIERS[:2]))

    def test_draft_writer_requires_explicit_opt_in(self):
        pr = {'draft': True, 'body': '', 'head': {'repo': {'full_name': REPO}}}
        self.assertNotIn(M.CARRIERS[3], M.eligible_carriers([pr], REPO))
        pr['body'] = M.OPT_IN
        self.assertIn(M.CARRIERS[3], M.eligible_carriers([pr], REPO))

    def test_truncated_api_collection_fails_closed(self):
        with self.assertRaises(M.BoundaryError):
            M.pages(lambda path: {'jobs': [], 'total_count': 1}, 'jobs', 'jobs')

    def test_child_success_is_reobserved_and_never_becomes_done(self):
        calls = []
        completed = []
        def api(path, body=None):
            calls.append((path, body))
            if '/git/ref/' in path:
                return {'object': {'sha': HEAD}}
            if '/git/commits/' in path:
                return {'tree': {'sha': TREE}}
            if 'actions/workflows?' in path:
                return {'workflows': [{'path': M.carrier_path(M.CARRIERS[0]), 'state': 'active'}],
                        'total_count': 1}
            if path.endswith('/dispatches'):
                self.assertEqual(body['ref'], 'main')
                self.assertTrue(body['return_run_details'])
                completed.append(run())
                return {'workflow_run_id': 42}
            if path.endswith('/actions/runs/42'):
                return run()
            if '/actions/runs/42/jobs?' in path:
                return {'jobs': [{'conclusion': 'success'}], 'total_count': 1}
            if '/actions/runs?' in path:
                runs = completed if 'head_sha=' in path else []
                return {'workflow_runs': runs, 'total_count': len(runs)}
            return []
        with tempfile.TemporaryDirectory() as directory:
            result = M.execute(api, REPO, Path(directory) / 'receipt.json')
            saved = json.loads((Path(directory) / 'receipt.json').read_text())
        self.assertFalse(result['effect_ack_done'])
        self.assertFalse(saved['effect_ack_done'])
        self.assertEqual(len(result['observations']), 2)
        self.assertEqual(len(result['child_executions']), 1)
        self.assertEqual(sum(body is not None for _, body in calls), 1)
        self.assertEqual(result['child_executions'][0]['run_id'], 42)

    def test_job_environment_uses_only_admissible_expression_contexts(self):
        import re
        text = (ROOT / '.github/workflows/qikvrt_universal_roundtrip_controller.yml').read_text()
        job_env = False
        allowed = {'github', 'needs', 'strategy', 'matrix', 'vars', 'secrets', 'inputs'}
        for line in text.splitlines():
            if line == '    env:':
                job_env = True
                continue
            if job_env and line.strip() and not line.startswith('      '):
                job_env = False
            if job_env:
                for context in re.findall(r'\$\{\{\s*([A-Za-z_]+)\.', line):
                    self.assertIn(context, allowed, line)

    def test_workflow_privilege_separation(self):
        text = (ROOT / '.github/workflows/qikvrt_universal_roundtrip_controller.yml').read_text()
        self.assertIn('persist-credentials: false', text)
        self.assertIn("github.event_name != 'pull_request'", text)
        self.assertNotIn('contents: write', text)
        self.assertNotIn('cancel-in-progress: true', text)
        self.assertIn('if: always()', text)
        self.assertNotIn('Fail closed on unfinished repository work', text)
        self.assertIn('python3 -B tools/qikvrt_universal_roundtrip_controller.py', text)


if __name__ == '__main__':
    unittest.main()
