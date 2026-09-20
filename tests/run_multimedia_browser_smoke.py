#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Isolated Chromium UI check with a real local model; no authenticated profile."""
import argparse
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
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
            deadline = time.monotonic() + 60
            while True:
                try:
                    if all(media.provider('/health', timeout=1, role=role).get('status') == 'ok'
                           for role in ('vision', 'text')): break
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
            source_status = browser('eval', 'document.getElementById("sourceStatus").textContent')
            report['source_status'] = source_status
            browser('find', 'label', 'Frage oder Arbeitsauftrag', 'fill', 'Does a Lean proof establish physical truth? Start with Yes or No, then explain the repository scientific boundaries in one sentence with a source reference.')
            browser('find', 'role', 'button', 'click', '--name', 'Lokales Modell befragen')
            deadline = time.monotonic() + 120
            while True:
                rendered = browser('eval', 'document.getElementById("sources").textContent')
                if '[R1]' in rendered and browser('eval', 'JSON.parse(document.getElementById("receipt").textContent).history_messages').strip() == '2': break
                if time.monotonic() > deadline: raise RuntimeError('REPOSITORY_SOURCE_NOT_RENDERED')
                time.sleep(.25)
            rendered = browser('eval', 'document.getElementById("sources").textContent')
            report['repository_sources'] = rendered
            report['repository_answer'] = browser('eval', 'document.getElementById("answer").textContent')
            report['conversation'] = browser('eval', 'document.getElementById("conversation").textContent')
            if 'two plus two' not in report['conversation']: raise RuntimeError('CONVERSATION_NOT_RETAINED')
            report['repository_receipt'] = browser('eval', 'document.getElementById("receipt").textContent')
            receipt = json.loads(json.loads(report['repository_receipt']))
            if (not re.match(r'(?i)^[\s*]*no\b', receipt['text']) or
                    receipt['citation_validation'] != 'REFERENCES_EXIST_NOT_SEMANTICALLY_VERIFIED'):
                raise RuntimeError('FINITE_BOUNDARY_AND_REFERENCE_CHECK_FAILED')
            # Capture before resetting; no user microphone/camera is accessed by CI.
            report['conversation_screenshot'] = browser('screenshot', str(output / 'conversation.png'), '--full')
            browser('find', 'role', 'button', 'click', '--name', 'Neues Gespräch')
            empty = browser('eval', 'document.getElementById("conversation").textContent')
            if empty.strip().strip('"'): raise RuntimeError('CONVERSATION_RESET_FAILED')
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
