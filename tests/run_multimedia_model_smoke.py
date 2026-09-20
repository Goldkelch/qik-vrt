#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Real pinned model through the real local HTTP adapter; explicit opt-in run."""
import argparse
import base64
import hashlib
import http.client
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from test_qikvrt_multimedia import png
import qikvrt_multimedia as media
import qikvrt_effect_ack_http_terminal as terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--audio', action='store_true')
    args = parser.parse_args()
    output = Path(args.output).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qikvrt-live-smoke-') as temporary:
        log = open(Path(temporary) / 'model.log', 'w+')
        process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'tools/qikvrt_multimedia_runtime.py'), 'serve'], cwd=ROOT, stdout=log, stderr=log)
        server = ThreadingHTTPServer(('127.0.0.1', 0), terminal.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            deadline = time.monotonic() + 45
            while True:
                try:
                    if media.provider('/health', timeout=1).get('status') == 'ok': break
                except (OSError, ValueError):
                    if process.poll() is not None or time.monotonic() > deadline:
                        log.seek(0); raise RuntimeError('model start failed: ' + log.read()[-2000:])
                    time.sleep(.25)
            cases = [('text', '/generate', {'prompt': 'Answer briefly: what is two plus two?', 'images': []}),
                     ('image', '/generate', {'prompt': 'What is the dominant color in this image? Answer with one color name.',
                      'images': [{'data': 'data:image/png;base64,' + base64.b64encode(png()).decode(), 'label': 'synthetic red control image'}]})]
            cases.append(('repository', '/generate', {'prompt': 'Does a Lean proof establish physical truth? Explain the repository scientific boundaries briefly.', 'repository': True}))
            if args.audio:
                path = Path(temporary) / 'silence.wav'
                with wave.open(str(path), 'wb') as writer:
                    writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(16000); writer.writeframes(b'\0' * 32000)
                cases.append(('digital-silence', '/transcribe', {'data': base64.b64encode(path.read_bytes()).decode(), 'language': 'de'}))
            results = []
            for name, endpoint, body in cases:
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=210)
                start = time.monotonic()
                try:
                    connection.request('POST', '/api/multimedia' + endpoint, body=json.dumps(body), headers={
                        'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:' + str(server.server_port),
                        'X-QIKVRT-Media-Token': media.TOKEN})
                    response = connection.getresponse(); value = json.loads(response.read())
                    results.append({'case': name, 'http_status': response.status, 'elapsed_seconds': round(time.monotonic() - start, 3), 'result': value})
                    print(json.dumps(results[-1], ensure_ascii=False), flush=True)
                finally: connection.close()
            passed = all(r['http_status'] == 200 and r['result']['effect_ack_done'] is False for r in results)
            grounded = next(r['result'] for r in results if r['case'] == 'repository')
            passed = passed and bool(grounded.get('repository_context', {}).get('sources'))
            receipt = {'schema': 'qikvrt_multimedia_live_smoke_v1', 'state': 'PASS' if passed else 'HOLD',
                       'source_files': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                           ROOT / 'src/qikvrt_multimedia.py', ROOT / 'src/qikvrt_effect_ack_http_terminal.py',
                           ROOT / 'runtime/toolchains/multimedia.lock.json', Path(__file__))},
                       'cases': results, 'scope': 'Actual local CPU inference and HTTP transport. Synthetic image; optional silent WAV checks zero-energy rejection only, not recognition accuracy. No browser/ISO/deployment/full-system acceptance.',
                       'effect_ack_done': False}
            output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
            return 0 if passed else 1
        finally:
            server.shutdown(); server.server_close(); process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            log.close()


if __name__ == '__main__': raise SystemExit(main())
