# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline regressions; observations here are synthetic, never runtime evidence."""
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('mesh_monitor', ROOT / 'deploy/mesh-monitor/server.py')
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)
MAIN = {'sha': 'a' * 40, 'commit': {'tree': {'sha': 'b' * 40}}}


def pr(number, title='ordinary title'):
    return {'number': number, 'title': title, 'draft': True,
            'head': {'sha': 'c' * 40}, 'base': {'sha': 'a' * 40}}


class SnapshotTests(unittest.TestCase):
    def test_valid_observation_is_not_live_or_effect(self):
        with patch.object(monitor, 'get_json', side_effect=[MAIN, [pr(1)], MAIN]):
            result = monitor.snapshot()
        self.assertEqual(result['state'], 'OBSERVED_SNAPSHOT')
        self.assertEqual(result['event_stream_state'], 'NOT_ESTABLISHED')
        self.assertFalse(result['effect_ack_done'])
        self.assertFalse(result['predecessor_evidence_transfer'])
        self.assertEqual(result['main'], {'head': 'a' * 40, 'tree': 'b' * 40})

    def test_full_inventory_is_paginated(self):
        first = [pr(i) for i in range(1, 101)]
        with patch.object(monitor, 'get_json', side_effect=[MAIN, first, [pr(101)], MAIN]) as get:
            result = monitor.snapshot()
        self.assertEqual(result['counts']['open_prs'], 101)
        self.assertTrue(result['inventory_complete'])
        self.assertIn('page=2', get.call_args_list[2].args[0])

    def test_page_limit_fails_closed(self):
        with patch.object(monitor, 'MAX_PR_PAGES', 1), patch.object(
                monitor, 'get_json', side_effect=[MAIN, [pr(i) for i in range(1, 101)]]):
            result = monitor.snapshot()
        self.assertEqual(result['reason'], 'INVENTORY_LIMIT_REACHED')
        self.assertNotIn('main', result)
        self.assertNotIn('counts', result)

    def test_duplicate_inventory_fails_closed(self):
        with patch.object(monitor, 'get_json', side_effect=[MAIN, [pr(1), pr(1)]]):
            result = monitor.snapshot()
        self.assertEqual(result['reason'], 'UNSTABLE_INVENTORY')

    def test_invalid_subject_fails_closed(self):
        with patch.object(monitor, 'get_json', return_value={'sha': 'main'}):
            result = monitor.snapshot()
        self.assertEqual(result['state'], 'HOLD_UNVERIFIED')
        self.assertNotIn('main', result)

    def test_main_drift_fails_closed(self):
        changed = {'sha': 'd' * 40, 'commit': {'tree': {'sha': 'b' * 40}}}
        with patch.object(monitor, 'get_json', side_effect=[MAIN, [], changed]):
            result = monitor.snapshot()
        self.assertEqual(result['reason'], 'MAIN_CHANGED_DURING_OBSERVATION')
        self.assertNotIn('main', result)

    def test_failure_does_not_leak_exception_details_or_partial_state(self):
        with patch.object(monitor, 'get_json', side_effect=[MAIN, RuntimeError('private-secret')]):
            result = monitor.snapshot()
        self.assertEqual(result['state'], 'HOLD_UNVERIFIED')
        self.assertNotIn('private-secret', json.dumps(result))
        self.assertNotIn('main', result)

    def test_invalid_inventory_fails_closed(self):
        with patch.object(monitor, 'get_json', side_effect=[MAIN, {'error': 'rate limited'}]):
            result = monitor.snapshot()
        self.assertEqual(result['reason'], 'INVALID_INVENTORY')

    def test_untrusted_title_remains_data(self):
        hostile = '<img src=x onerror=alert(1)>'
        with patch.object(monitor, 'get_json', side_effect=[MAIN, [pr(1, hostile)], MAIN]):
            result = monitor.snapshot()
        self.assertEqual(result['pull_requests'][0]['title'], hostile)
        self.assertNotIn('innerHTML', monitor.PAGE)
        self.assertNotIn('insertAdjacentHTML', monitor.PAGE)
        self.assertIn('node.textContent', monitor.PAGE)

    def test_no_browser_timer_polling(self):
        for forbidden in ('setInterval', 'setTimeout', 'requestAnimationFrame'):
            self.assertNotIn(forbidden, monitor.PAGE)
        self.assertIn("button.addEventListener('click'", monitor.PAGE)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = monitor.ThreadingHTTPServer(('127.0.0.1', 0), monitor.H)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health_is_transport_only_and_does_not_query_github(self):
        with patch.object(monitor, 'get_json') as get:
            with urlopen(self.base + '/health', timeout=2) as response:
                self.assertEqual(response.read(), b'ready\n')
            get.assert_not_called()

    def test_unknown_snapshot_prefix_is_not_accepted(self):
        with patch.object(monitor, 'snapshot') as snap:
            with self.assertRaises(HTTPError) as failure:
                urlopen(self.base + '/api/snapshot-extra', timeout=2)
            self.assertEqual(failure.exception.code, 404)
            failure.exception.close()
            snap.assert_not_called()

    def test_http_snapshot_cannot_reuse_cached_response(self):
        with patch.object(monitor, 'get_json', side_effect=[MAIN, [], MAIN]):
            with urlopen(self.base + '/api/snapshot', timeout=2) as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(json.load(response)['state'], 'OBSERVED_SNAPSHOT')


if __name__ == '__main__':
    unittest.main()
