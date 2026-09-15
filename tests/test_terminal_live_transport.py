# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Behavioral relay tests. Fixtures are not production or Firefox receipts."""
import http.client
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from tools import qikvrt_live_sse as relay

ROOT = Path(__file__).resolve().parents[1]


def fixture(number):
    return {
        'schema': 'qikvrt_live_event_v1', 'event_id': 'fixture-' + str(number),
        'observed_at': '2026-09-15T00:00:00Z', 'repository': 'Goldkelch/qik-vrt',
        'subject': {'kind': 'test_fixture', 'head_sha': 'a' * 40},
        'phase': 'P2', 'verb': 'READBACK', 'causal_state': 'REOBSERVE',
        'source': {'type': 'test_fixture', 'id': str(number)},
        'productive_effect': False, 'effect_ack': 'NOT_REQUIRED', 'payload': {}
    }


class TerminalLiveTransportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'events.jsonl'
        self.path.write_text('', encoding='utf-8')
        handler = type('BoundHandler', (relay.Handler,), {'events_path': self.path})
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connections = []

    def tearDown(self):
        for connection, response in self.connections:
            # Close the socket as well as the buffered HTTP response. This wakes
            # the event-driven reader; no background fixture writers are left.
            if connection.sock:
                try:
                    connection.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            response.close()
            connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.directory.cleanup()

    def append(self, number):
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(fixture(number)) + '\n')
            stream.flush()

    def request(self, path='/events', headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        connection.request('GET', path, headers=headers or {})
        response = connection.getresponse()
        self.connections.append((connection, response))
        return response

    def frame(self, response):
        frame = bytearray()
        while not frame.endswith(b'\n\n'):
            byte = response.read(1)
            self.assertTrue(byte, 'SSE connection ended before the next complete receipt')
            frame.extend(byte)
            self.assertLess(len(frame), 65536)
        return frame.decode('utf-8')

    def test_persisted_cursor_replays_only_after_exact_event(self):
        self.append(1); self.append(2)
        response = self.request('/events?since=fixture-1')
        self.assertEqual(response.status, 200)
        self.assertIn('id: fixture-2\n', self.frame(response))

    def test_last_event_id_supersedes_old_url_cursor(self):
        self.append(1); self.append(2); self.append(3)
        response = self.request('/events?since=fixture-1', {'Last-Event-ID': 'fixture-2'})
        self.assertEqual(response.status, 200)
        self.assertIn('id: fixture-3\n', self.frame(response))

    def test_unknown_cursor_is_visible_conflict_not_silent_empty_stream(self):
        self.append(1)
        self.assertEqual(self.request('/events?since=unknown').status, 409)

    def test_missing_source_is_not_a_connected_empty_stream(self):
        self.path.unlink()
        self.assertEqual(self.request().status, 503)

    def test_invalid_object_cannot_crash_decoder_or_become_event(self):
        self.assertIsNone(relay.decode_event('[]'))
        self.assertIsNone(relay.decode_event('{bad json'))
        item = fixture(1); item['event_id'] = 'injected\nevent: done'
        self.assertFalse(relay.valid_event(item))

    def test_three_consecutive_appends_use_one_http_connection(self):
        self.append(1)
        response = self.request()
        self.assertEqual(response.status, 200)
        for number in (1, 2, 3):
            if number != 1:
                self.append(number)
            frame = self.frame(response)
            self.assertIn('event: qikvrt\n', frame)
            self.assertIn('id: fixture-' + str(number) + '\n', frame)
            payload = json.loads(frame.split('data: ', 1)[1].strip())
            self.assertEqual(payload, fixture(number))
        self.assertEqual(len(self.connections), 1)

    def test_partial_append_is_delivered_only_after_line_completion(self):
        self.append(1)
        response = self.request()
        self.frame(response)
        data = json.dumps(fixture(2))
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(data[:20]); stream.flush()
            stream.write(data[20:] + '\n'); stream.flush()
        self.assertIn('id: fixture-2\n', self.frame(response))

    def test_two_consumers_receive_the_same_append(self):
        self.append(1)
        first = self.request(); second = self.request()
        self.frame(first); self.frame(second)
        self.append(2)
        self.assertEqual(self.frame(first), self.frame(second))

    def test_source_code_has_no_timer_driven_progress_fallback(self):
        source = (ROOT / 'tools/qikvrt_live_sse.py').read_text(encoding='utf-8')
        self.assertNotIn('time.sleep(', source)
        self.assertNotIn('poll_seconds', source)

    def test_actual_extension_background_preserves_event_payload_and_cursor(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/terminal_live_background.cjs')],
            cwd=ROOT, text=True, capture_output=True, timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('BACKGROUND_EVENT_TESTS=PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
