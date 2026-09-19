"""Real nginx tests against a finite guard fixture, not product acceptance.

Run in the Universal Terminal image (nginx is mandatory there). The backend
fixture makes the proxy's Host/Origin, route and read-only boundary observable;
actual ledger/runtime acceptance remains a separately executed image test.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '/qik-vrt/mesh/v1/effect-ack'


class GuardFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        record = {'path': self.path, 'headers': dict(self.headers.items())}
        self.server.observations.append(record)
        loopback = '127.0.0.1:' + str(self.server.server_port)
        allowed = self.headers.get('Host') == loopback and self.headers.get('Origin') in (None, 'http://' + loopback)
        code = 200 if allowed else 403
        payload = json.dumps(record).encode()
        media = 'application/json'
        if allowed and self.path.startswith('/api/temdd/events'):
            payload = b'event: subject\ndata: {"fixture":true}\n\n'
            media = 'text/event-stream'
        self.send_response(code)
        self.send_header('Content-Type', media)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self.server.observations.append({'unexpected_write': self.command})
        self.send_error(500, 'write reached backend fixture')

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = do_POST


class TEMDDPublicProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nginx = shutil.which('nginx')
        if cls.nginx is None:
            raise unittest.SkipTest('nginx integration dependency absent; run in Universal Terminal image')
        cls.temp = tempfile.TemporaryDirectory(prefix='qikvrt-proxy-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        cls.backend = ThreadingHTTPServer(('127.0.0.1', 0), GuardFixture)
        cls.backend.observations = []
        cls.thread = threading.Thread(target=cls.backend.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.backend.server_close)
        cls.addClassCleanup(cls.backend.shutdown)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            cls.port = reservation.getsockname()[1]
        source = ROOT / 'deploy/universal-terminal/nginx.conf'
        text = source.read_text()
        text = text.replace('listen 8080;', f'listen 127.0.0.1:{cls.port};')
        text = text.replace('127.0.0.1:8771', '127.0.0.1:' + str(cls.backend.server_port))
        text = text.replace('/opt/qikvrt/deploy/universal-terminal', str(cls.work))
        text = text.replace('/tmp/nginx', str(cls.work / 'nginx'))
        text = text.replace('/tmp/qikvrt-mesh-health.json', str(cls.work / 'health.json'))
        for name in ('client-body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'):
            (cls.work / ('nginx-' + name)).mkdir()
        (cls.work / 'mesh-index.html').write_text('existing mesh landing page')
        (cls.work / 'health.json').write_text('{"state":"FIXTURE"}')
        config = cls.work / 'nginx.conf'
        config.write_text(text)
        check = subprocess.run([cls.nginx, '-t', '-c', str(config)], capture_output=True, text=True, timeout=10)
        if check.returncode:
            raise AssertionError(check.stderr)
        cls.log = (cls.work / 'nginx.log').open('w+')
        cls.addClassCleanup(cls.log.close)
        cls.process = subprocess.Popen([cls.nginx, '-c', str(config), '-g', 'daemon off;'], stdout=cls.log, stderr=cls.log)
        cls.addClassCleanup(cls.stop_proxy)
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1', cls.port), timeout=.1):
                    return
            except OSError:
                if cls.process.poll() is not None:
                    break
                time.sleep(.02)
        cls.log.seek(0)
        raise AssertionError('nginx failed to listen: ' + cls.log.read())

    @classmethod
    def stop_proxy(cls):
        if cls.process.poll() is None:
            cls.process.terminate()
        try:
            cls.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait(timeout=5)

    def request(self, path, method='GET', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=4)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_prefixed_ide_and_subject_are_readable(self):
        for suffix in ('/AI', '/AI/', '/api/temdd/subject'):
            with self.subTest(suffix=suffix):
                code, _, body = self.request(PREFIX + suffix)
                self.assertEqual(code, 200, body)
                self.assertEqual(json.loads(body)['path'], suffix)

    def test_browser_absolute_subject_path_reaches_same_backend(self):
        code, _, body = self.request('/api/temdd/subject')
        self.assertEqual(code, 200, body)
        self.assertEqual(json.loads(body)['path'], '/api/temdd/subject')

    def test_event_stream_preserves_query_and_reconnect_cursor(self):
        for prefix in ('', PREFIX):
            code, headers, body = self.request(prefix + '/api/temdd/events?after=epoch%3A7', headers={'Last-Event-ID': 'epoch:9'})
            self.assertEqual(code, 200, body)
            self.assertEqual(headers['Content-Type'], 'text/event-stream')
            self.assertIn(b'event: subject', body)
            record = self.backend.observations[-1]
            self.assertEqual(record['path'], '/api/temdd/events?after=epoch%3A7')
            self.assertEqual(record['headers']['Last-Event-ID'], 'epoch:9')

    def test_same_host_browser_origin_is_validated_before_translation(self):
        for scheme in ('http', 'https'):
            code, _, body = self.request(PREFIX + '/AI', headers={'Origin': f'{scheme}://127.0.0.1:{self.port}'})
            self.assertEqual(code, 200, body)
            self.assertNotIn('Origin', json.loads(body)['headers'])

    def test_foreign_null_and_deceptive_origins_never_reach_backend(self):
        for origin in ('https://attacker.invalid', 'null', f'https://127.0.0.1:{self.port}.attacker.invalid'):
            before = len(self.backend.observations)
            code, _, _ = self.request('/api/temdd/subject', headers={'Origin': origin, 'X-Forwarded-Host': f'127.0.0.1:{self.port}'})
            self.assertEqual(code, 403)
            self.assertEqual(len(self.backend.observations), before)

    def test_non_get_methods_never_reach_backend(self):
        for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'):
            for path in (PREFIX + '/AI', '/api/temdd/subject', PREFIX + '/api/temdd/events'):
                with self.subTest(method=method, path=path):
                    before = len(self.backend.observations)
                    code, _, _ = self.request(path, method)
                    self.assertEqual(code, 405)
                    self.assertEqual(len(self.backend.observations), before)

    def test_observation_routes_do_not_forward_browser_credentials(self):
        code, _, body = self.request('/api/temdd/subject', headers={'Authorization': 'Bearer synthetic-fixture', 'Cookie': 'session=synthetic-fixture'})
        self.assertEqual(code, 200, body)
        headers = json.loads(body)['headers']
        self.assertNotIn('Authorization', headers)
        self.assertNotIn('Cookie', headers)

    def test_unknown_paths_get_no_loopback_translation(self):
        for path in ('/api/temdd/append', '/api/temdd/subject/extra', PREFIX + '/api/temdd/append'):
            code, _, _ = self.request(path)
            self.assertIn(code, (403, 404))

    def test_existing_landing_and_redirect_stay_unchanged(self):
        code, _, body = self.request('/AI/')
        self.assertEqual((code, body), (200, b'existing mesh landing page'))
        code, headers, _ = self.request('/AI')
        self.assertEqual((code, headers['Location']), (308, '/AI/'))


if __name__ == '__main__':
    unittest.main()
