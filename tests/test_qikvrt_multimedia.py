"""Exercise real HTTP boundaries and a finite provider fixture; not model quality."""
import base64
import hashlib
import http.client
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import struct
import sys
import threading
import unittest
import wave
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import qikvrt_effect_ack_http_terminal as terminal
import qikvrt_multimedia as media


def png(width=16, height=16):
    def chunk(name, body):
        return struct.pack('>I', len(body)) + name + body + struct.pack('>I', zlib.crc32(name + body))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress((b'\0' + b'\xff\0\0' * width) * height)) + chunk(b'IEND', b'')


class Provider(BaseHTTPRequestHandler):
    observations = []
    alias = 'qikvrt-smolvlm2-500m'
    def log_message(self, *args): pass
    def do_GET(self):
        self.send_json({'status': 'ok'} if self.path == '/health' else {'data': [{'id': self.alias}]})
    def do_POST(self):
        self.observations.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.send_json({'model': self.alias, 'choices': [{'message': {'content': '<script>fixture</script>'}, 'finish_reason': 'stop'}]})
    def send_json(self, value):
        raw = json.dumps(value).encode()
        self.send_response(200); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)


class MultimediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), terminal.Handler)
        for server in (cls.provider, cls.server):
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        cls.env = patch.dict(os.environ, {'QIKVRT_MODEL_PORT': str(cls.provider.server_port)})
        cls.env.start()
        cls.origin = 'http://127.0.0.1:' + str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        for server in (cls.server, cls.provider):
            server.shutdown(); server.server_close()
    def request(self, path='/api/multimedia/status', method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
        try:
            hdr = {'Origin': self.origin, 'Content-Type': 'application/json', 'X-QIKVRT-Media-Token': media.TOKEN}
            hdr.update(headers or {})
            connection.request(method, path, body=None if body is None else json.dumps(body), headers=hdr)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally: connection.close()
    def generate(self, body, headers=None):
        code, hdr, raw = self.request('/api/multimedia/generate', 'POST', body, headers)
        return code, json.loads(raw)
    def test_local_status_and_page(self):
        code, headers, raw = self.request()
        self.assertEqual(code, 200); self.assertTrue(json.loads(raw)['ready'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        code, headers, raw = self.request('/multimedia')
        self.assertEqual(code, 200); self.assertIn(b'/multimedia/app.js', raw)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
    def test_foreign_host_origin_and_missing_token_block_before_provider(self):
        start = len(Provider.observations)
        for hdr in ({'Host': 'evil.invalid'}, {'Origin': 'https://github.com'}, {'Origin': 'null'}, {'X-QIKVRT-Media-Token': ''}):
            code, _ = self.generate({'prompt': 'hello'}, hdr); self.assertEqual(code, 403)
        self.assertEqual(len(Provider.observations), start)
    def test_external_site_cannot_read_status_token(self):
        self.assertEqual(self.request(headers={'Origin': 'https://attacker.invalid'})[0], 403)
    def test_real_transport_preserves_image_and_no_effect(self):
        raw = png(); image = 'data:image/png;base64,' + base64.b64encode(raw).decode()
        body = {'prompt': 'Describe this video frame', 'images': [{'data': image, 'label': 'video @ 1.000 s'}]}
        before = len(terminal.STATE.events)
        code, value = self.generate(body)
        self.assertEqual(code, 200); self.assertEqual(value['state'], 'UNVERIFIED_PROPOSAL')
        self.assertFalse(value['effect_ack_done']); self.assertFalse(value['ordinary_release'])
        self.assertEqual(value['images'][0]['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(value['input_sha256'], hashlib.sha256(media.canonical(body)).hexdigest())
        self.assertEqual(Provider.observations[-1]['messages'][0]['content'][-1]['image_url']['url'], image)
        self.assertNotIn('tools', Provider.observations[-1]); self.assertEqual(len(terminal.STATE.events), before)
    def test_oversize_external_urls_tool_requests_and_bad_types_rejected(self):
        for body in ({'prompt': ''}, {'prompt': 'x' * 12001}, {'prompt': 'x', 'tools': ['shell']},
                     {'prompt': 'x', 'images': [{'data': 'https://example.com/image.png', 'label': 'remote'}]},
                     {'prompt': 'x', 'images': [None]}, {'prompt': 1}, [], {'prompt': 'x', 'images': [1] * 5}):
            code, value = self.generate(body); self.assertEqual(code, 422, body)
            self.assertFalse(value['effect_ack_done'])
    def test_pixel_bound_precedes_provider(self):
        raw = png(2049, 1)
        code, value = self.generate({'prompt': 'x', 'images': [{'data': 'data:image/png;base64,' + base64.b64encode(raw).decode(), 'label': 'large'}]})
        self.assertEqual(code, 422); self.assertEqual(value['reason'], 'IMAGE_DIMENSIONS')
    def test_mismatched_model_never_becomes_receipt(self):
        with patch.object(Provider, 'alias', 'another-model'):
            code, value = self.generate({'prompt': 'hello'})
        self.assertEqual(code, 422); self.assertEqual(value['reason'], 'MODEL_ID_MISMATCH')
    def test_busy_is_bounded(self):
        media.SLOT.acquire()
        try: self.assertEqual(self.generate({'prompt': 'hello'})[0], 429)
        finally: media.SLOT.release()
    def test_transfer_encoding_and_wrong_content_type_rejected(self):
        for headers in ({'Transfer-Encoding': 'chunked'}, {'Content-Type': 'text/plain'}):
            self.assertEqual(self.generate({'prompt': 'x'}, headers)[0], 422)
    def test_unavailable_provider_is_not_success(self):
        with patch.object(media, 'provider', side_effect=ConnectionRefusedError()):
            self.assertFalse(json.loads(self.request()[2])['ready'])
            code, value = self.generate({'prompt': 'hello'})
            self.assertEqual(code, 422); self.assertFalse(value['effect_ack_done'])
    def test_model_list_does_not_make_loading_model_ready(self):
        def loading(path, **kwargs):
            return {'status': 'loading'} if path == '/health' else {'data': [{'id': Provider.alias}]}
        with patch.object(media, 'provider', side_effect=loading):
            self.assertFalse(json.loads(self.request()[2])['ready'])
    @unittest.skipUnless(__import__('shutil').which('ffmpeg'), 'FFmpeg audio decoder absent')
    def test_digital_silence_never_reaches_asr(self):
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as writer:
            writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(16000); writer.writeframes(b'\0' * 32000)
        with patch.object(media, 'audio_paths', return_value=(None, None, True)):
            code, _, raw = self.request('/api/multimedia/transcribe', 'POST', {'data': base64.b64encode(buffer.getvalue()).decode(), 'language': 'de'})
        value = json.loads(raw)
        self.assertEqual(code, 200); self.assertEqual(value['state'], 'NO_AUDIO_ENERGY'); self.assertEqual(value['text'], '')
    def test_audio_runtime_failure_is_explicit(self):
        with patch.object(media, 'audio_paths', return_value=(None, None, False)):
            code, _, raw = self.request('/api/multimedia/transcribe', 'POST', {'data': 'YXVkaW8=', 'language': 'de'})
        self.assertEqual(code, 422); self.assertEqual(json.loads(raw)['reason'], 'OFFLINE_AUDIO_RUNTIME_NOT_INSTALLED')
    def test_browser_renders_model_output_as_text(self):
        source = (media.ROOT / 'docs/terminal/multimedia/app.js').read_text()
        self.assertNotIn('innerHTML', source)
        self.assertIn("el('answer').textContent=result.text", source)


if __name__ == '__main__': unittest.main()
