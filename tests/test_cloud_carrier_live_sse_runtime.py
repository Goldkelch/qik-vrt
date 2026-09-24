# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Cloud/standalone SSE lifecycle and real local transport regressions.

The HTTP tests use explicitly synthetic fixtures, not GitHub or Firefox evidence.
The container workflow remains the independent browser/start/restart witness.
"""
from pathlib import Path
import http.client
import json
import os
import runpy
import stat
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]


class CloudCarrierLiveSseRuntime(unittest.TestCase):
    def test_repaired_relay_is_present(self):
        path = ROOT / 'tools/qikvrt_live_sse.py'
        self.assertTrue(path.is_file(), 'live SSE relay absent from cloud carrier')
        text = path.read_text(encoding='utf-8')
        self.assertIn('event: qikvrt', text)
        self.assertIn('Last-Event-ID', text)
        self.assertNotIn('time.sleep(', text)

    def test_repaired_extension_consumes_same_event(self):
        text = (ROOT / 'browser/firefox/qikvrt-terminal/background.js').read_text(encoding='utf-8')
        self.assertIn('source.addEventListener("qikvrt"', text)
        self.assertIn('qikvrtLastEventId', text)
        self.assertNotIn('browser.alarms', text)

    def test_shared_terminal_owns_required_relay(self):
        text = (ROOT / 'deploy/universal-terminal/entrypoint.sh').read_text(encoding='utf-8')
        self.assertIn('qikvrt_live_sse.py', text, 'health requires SSE but standalone terminal never starts it')
        self.assertIn('--host 127.0.0.1 --port 8787', text)
        self.assertIn('LIVE_SSE_PID=$!', text)
        self.assertIn('PIDS="$PIDS ${LIVE_SSE_PID}"', text)
        self.assertLess(text.index('qikvrt_live_sse.py'), text.index('firefox-esr --no-remote'))
        self.assertIn('--initialize-journal', text)
        self.assertIn('${STATE_DIR}/live/QIKVRT_LIVE_EVENTS.jsonl', text)

    def test_cloud_does_not_double_bind_terminal_relay(self):
        text = (ROOT / 'deploy/universal-terminal/cloud-entrypoint.sh').read_text(encoding='utf-8')
        self.assertIn('/usr/local/bin/qikvrt-universal-terminal &', text)
        self.assertNotIn('python3 -B /opt/qikvrt/tools/qikvrt_live_sse.py', text)

    def test_runtime_health_checks_live_relay(self):
        text = (ROOT / 'deploy/universal-terminal/runtime-health.sh').read_text(encoding='utf-8')
        self.assertIn('8787', text)
        self.assertIn('/events', text)

    def test_xpi_is_built_from_repository_extension(self):
        text = (ROOT / 'deploy/universal-terminal/Dockerfile').read_text(encoding='utf-8')
        self.assertIn('browser/firefox/qikvrt-terminal', text)
        self.assertIn('qikvrt-ai-terminal@goldkelch.local.xpi', text)


class DurableLiveSseTransport(unittest.TestCase):
    def setUp(self):
        self.module = runpy.run_path(str(ROOT / 'tools/qikvrt_live_sse.py'))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state/live/events.jsonl'

    def initialize(self):
        function = self.module.get('prepare_journal')
        self.assertTrue(callable(function), 'cold durable journal initialization is absent')
        function(self.path)

    def test_cold_journal_is_empty_private_and_restart_preserves_bytes(self):
        self.initialize()
        self.assertEqual(self.path.read_bytes(), b'')
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode) & 0o077, 0)
        payload = b'historical bytes must not be overwritten\n'
        self.path.write_bytes(payload)
        self.initialize()
        self.assertEqual(self.path.read_bytes(), payload)

    def test_symlink_and_fifo_are_rejected_without_mutating_target(self):
        self.path.parent.mkdir(parents=True)
        target = Path(self.temp.name) / 'target'
        target.write_bytes(b'unchanged')
        self.path.symlink_to(target)
        with self.assertRaises((OSError, ValueError)):
            self.module['prepare_journal'](self.path)
        self.assertEqual(target.read_bytes(), b'unchanged')
        self.path.unlink()
        os.mkfifo(self.path)
        with self.assertRaises((OSError, ValueError)):
            self.module['prepare_journal'](self.path)
        self.assertTrue(stat.S_ISFIFO(self.path.stat().st_mode))

    def test_live_appends_resume_and_unknown_cursor_over_real_http(self):
        self.initialize()
        handler = type('FixtureHandler', (self.module['Handler'],), {'events_path': self.path})
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(worker.join, 3)
        self.addCleanup(server.shutdown)
        host, port = server.server_address
        connection = http.client.HTTPConnection(host, port, timeout=3)
        self.addCleanup(connection.close)
        connection.request('GET', '/events')
        response = connection.getresponse()
        self.addCleanup(response.close)
        self.assertEqual(response.status, 200)
        self.assertTrue(response.getheader('Content-Type').startswith('text/event-stream'))

        def read_frame(stream):
            lines = [stream.readline() for _ in range(4)]
            self.assertEqual(lines[1], b'event: qikvrt\n')
            self.assertEqual(lines[3], b'\n')
            return json.loads(lines[2].removeprefix(b'data: '))

        fixtures = []
        for number in range(1, 4):
            event = {
                'schema': 'qikvrt_live_event_v1', 'event_id': f'test-fixture-{number}',
                'observed_at': '2000-01-01T00:00:00Z', 'repository': 'Goldkelch/qik-vrt',
                'subject': {'head_sha': 'a' * 40, 'tree_sha': 'b' * 40},
                'phase': 'TEST_FIXTURE', 'verb': 'APPEND', 'causal_state': 'OBSERVED',
                'source': {'kind': 'synthetic-local-regression'}, 'productive_effect': False,
                'effect_ack': 'NOT_IMPLIED', 'payload': {'sequence': number},
            }
            fixtures.append(event)
            with self.path.open('ab') as journal:
                journal.write(json.dumps(event).encode() + b'\n')
                journal.flush()
                os.fsync(journal.fileno())
            self.assertEqual(read_frame(response), event)

        resumed = http.client.HTTPConnection(host, port, timeout=3)
        self.addCleanup(resumed.close)
        resumed.request('GET', '/events?since=test-fixture-1', headers={'Last-Event-ID': 'test-fixture-2'})
        replay = resumed.getresponse()
        self.addCleanup(replay.close)
        self.assertEqual(replay.status, 200)
        self.assertEqual(read_frame(replay), fixtures[2])
        missing = http.client.HTTPConnection(host, port, timeout=3)
        self.addCleanup(missing.close)
        missing.request('GET', '/events', headers={'Last-Event-ID': 'not-retained'})
        conflict = missing.getresponse()
        self.addCleanup(conflict.close)
        self.assertEqual(conflict.status, 409)
        self.assertEqual(json.loads(conflict.read())['state'], 'HOLD')


if __name__ == '__main__':
    unittest.main()
