#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only, on-demand bootstrap view; not an authenticated event stream."""
import json
import os
import re
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

REPO_API = 'https://api.github.com/repos/Goldkelch/qik-vrt'
MAX_PR_PAGES = 10
SHA = re.compile(r'[0-9a-f]{40}')


def get_json(path):
    req = urllib.request.Request(REPO_API + path, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'qikvrt-mesh-monitor/1',
    })
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.load(response)


def require_sha(value):
    if not isinstance(value, str) or SHA.fullmatch(value) is None:
        raise ValueError('INVALID_SUBJECT')
    return value


def snapshot():
    out = {
        'schema': 'qikvrt_mesh_monitor_v1',
        'observed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'repository': 'Goldkelch/qik-vrt',
        'state': 'HOLD_UNVERIFIED',
        'observation_mode': 'ON_DEMAND_SNAPSHOT',
        'observation_consistency': 'SEQUENTIAL_READS_NOT_ATOMIC',
        'event_stream_state': 'NOT_ESTABLISHED',
        'predecessor_evidence_transfer': False,
        'effect_ack_done': False,
    }
    try:
        main = get_json('/commits/main')
        subject = {'head': require_sha(main['sha']),
                   'tree': require_sha(main['commit']['tree']['sha'])}
        prs, seen = [], set()
        for page in range(1, MAX_PR_PAGES + 1):
            batch = get_json(f'/pulls?state=open&per_page=100&page={page}')
            if not isinstance(batch, list) or len(batch) > 100:
                raise ValueError('INVALID_INVENTORY')
            for pr in batch:
                number = pr['number']
                if type(number) is not int or number <= 0 or number in seen:
                    raise ValueError('UNSTABLE_INVENTORY')
                if not isinstance(pr['title'], str) or type(pr['draft']) is not bool:
                    raise ValueError('INVALID_INVENTORY')
                seen.add(number)
                prs.append({'number': number, 'title': pr['title'], 'draft': pr['draft'],
                            'head': require_sha(pr['head']['sha']),
                            'base': require_sha(pr['base']['sha']),
                            'updated_at': pr.get('updated_at')})
            if len(batch) < 100:
                break
        else:
            raise ValueError('INVENTORY_LIMIT_REACHED')
        latest = get_json('/commits/main')
        if (require_sha(latest['sha']) != subject['head'] or
                require_sha(latest['commit']['tree']['sha']) != subject['tree']):
            raise ValueError('MAIN_CHANGED_DURING_OBSERVATION')
        out.update(main=subject, pull_requests=prs, counts={'open_prs': len(prs)},
                   inventory_complete=True, state='OBSERVED_SNAPSHOT')
    except Exception as exc:
        # Do not expose credentials, remote response bodies, or partial success.
        out['error'] = type(exc).__name__
        if isinstance(exc, ValueError) and str(exc) in {
            'INVALID_SUBJECT', 'INVALID_INVENTORY', 'UNSTABLE_INVENTORY',
            'INVENTORY_LIMIT_REACHED', 'MAIN_CHANGED_DURING_OBSERVATION',
        }:
            out['reason'] = str(exc)
    out['completed_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    return out


PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QIK-VRT Mesh Monitor</title>
<style>body{font:15px system-ui;background:#0d0d15;color:#f5f5f7;padding:24px}main{max-width:1000px;margin:auto}p{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #343442;padding:8px;overflow-wrap:anywhere}button{font:inherit;padding:10px}#x{overflow-x:auto}</style>
<main><h1>QIK-VRT Mesh Monitor</h1>
<p>On-demand observation only. No automatic polling. Authenticated event stream: NOT_ESTABLISHED. No predecessor evidence transfer.</p>
<button id="refresh" type="button">Observe current repository state</button>
<div id="x" role="status" aria-live="polite">No observation requested.</div></main>
<script>
const output = document.getElementById('x');
const button = document.getElementById('refresh');
function textElement(tag, value) {
  const node = document.createElement(tag);
  node.textContent = String(value ?? 'UNKNOWN');
  return node;
}
function render(data) {
  output.replaceChildren();
  for (const [label, value] of [
    ['State', data.state], ['Observed', data.observed_at],
    ['Main HEAD', data.main?.head], ['Main TREE', data.main?.tree],
    ['Open PRs (sequential snapshot)', data.counts?.open_prs],
    ['Event stream', data.event_stream_state], ['Reason', data.reason || data.error || 'none']
  ]) output.append(textElement('p', label + ': ' + (value ?? 'UNKNOWN')));
  const table = document.createElement('table');
  const header = document.createElement('tr');
  for (const label of ['PR', 'Subject', 'Exact HEAD', 'Draft']) header.append(textElement('th', label));
  const thead = document.createElement('thead'); thead.append(header); table.append(thead);
  const body = document.createElement('tbody');
  for (const pr of data.pull_requests || []) {
    const row = document.createElement('tr');
    for (const value of [pr.number, pr.title, pr.head, pr.draft]) row.append(textElement('td', value));
    body.append(row);
  }
  table.append(body); output.append(table);
}
button.addEventListener('click', async () => {
  button.disabled = true;
  output.textContent = 'Observing current repository state…';
  try {
    const response = await fetch('/api/snapshot', {cache: 'no-store'});
    if (!response.ok) throw new Error('HTTP observation failed');
    render(await response.json());
  } catch (error) {
    output.textContent = 'HOLD_UNVERIFIED: snapshot unavailable';
  } finally { button.disabled = false; }
});
</script></html>'''


class H(BaseHTTPRequestHandler):
    def send(self, code, ctype, body):
        payload = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/health':
            return self.send(200, 'text/plain; charset=utf-8', 'ready\n')
        if path == '/api/snapshot':
            return self.send(200, 'application/json', json.dumps(snapshot(), separators=(',', ':')))
        if path == '/':
            return self.send(200, 'text/html; charset=utf-8', PAGE)
        self.send(404, 'text/plain; charset=utf-8', 'not found\n')

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


def main():
    port = int(os.getenv('PORT', '8080'))
    print(json.dumps({'event': 'MESH_MONITOR_START', 'port': port,
                      'started_at': time.time()}), flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()


if __name__ == '__main__':
    main()
