#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Isolated Chromium UI check with a real local model; no authenticated profile."""
import argparse
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import qikvrt_multimedia as media
import qikvrt_effect_ack_http_terminal as terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve(); output.mkdir(parents=True, exist_ok=True)
    cli = ROOT / 'runtime/toolchains/multimedia-browser/node_modules/.bin/agent-browser'
    def browser(*argv):
        return subprocess.check_output([str(cli), '--session', 'qikvrt-multimedia-smoke', *argv], text=True, timeout=60)
    with tempfile.TemporaryFile(mode='w+') as log:
        process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'tools/qikvrt_multimedia_runtime.py'), 'serve'], stdout=log, stderr=log)
        server = ThreadingHTTPServer(('127.0.0.1', 0), terminal.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        report = {'state': 'HOLD', 'scope': 'Chromium UI and actual local model; not Firefox/ISO release acceptance', 'effect_ack_done': False}
        try:
            deadline = time.monotonic() + 45
            while True:
                try:
                    if media.provider('/health', timeout=1).get('status') == 'ok': break
                except (OSError, ValueError): pass
                if process.poll() is not None or time.monotonic() > deadline: raise RuntimeError('MODEL_START_FAILED')
                time.sleep(.25)
            report['open'] = browser('open', 'http://127.0.0.1:' + str(server.server_port) + '/multimedia')
            browser('wait', '--load', 'networkidle')
            report['snapshot'] = browser('snapshot', '-i')
            if 'Frage oder Arbeitsauftrag' not in report['snapshot']: raise RuntimeError('MISSING_INPUT')
            browser('find', 'label', 'Frage oder Arbeitsauftrag', 'fill', 'Answer briefly: what is two plus two?')
            browser('find', 'role', 'button', 'click', '--name', 'Lokales Modell befragen')
            deadline = time.monotonic() + 45
            while True:
                answer = browser('eval', 'document.getElementById("answer").textContent')
                if 'four' in answer.lower() or '4' in answer: break
                if time.monotonic() > deadline: raise RuntimeError('UI_REPLY_NOT_OBSERVED')
                time.sleep(.25)
            report['answer'] = answer
            report['browser'] = browser('eval', 'navigator.userAgent')
            report['errors'] = browser('errors')
            if report['errors'].strip() not in ('', '[]', 'No errors'): raise RuntimeError('BROWSER_ERRORS')
            report['screenshot'] = browser('screenshot', str(output / 'multimedia.png'), '--full')
            report['state'] = 'PASS'
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            report['reason'] = str(exc)
            try: browser('screenshot', str(output / 'failure.png'))
            except (OSError, subprocess.SubprocessError): pass
        finally:
            try: browser('close')
            except (OSError, subprocess.SubprocessError): pass
            server.shutdown(); server.server_close(); process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        (output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report['state'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
