# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fresh fixture-local producer, replay, HTTP, and consumer regression tests."""
from __future__ import annotations

import copy
import http.client
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import qikvrt_temdd_event_ledger as m


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.state = Path(self.temp.name) / 'state'
        page = self.root / 'docs/terminal/temdd/index.html'
        page.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / 'docs/terminal/temdd/index.html', page)
        self.git('init', '-q')
        self.git('config', 'user.name', 'TEMDD fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.runtime = m.Runtime(self.root, self.state, 'Goldkelch/qik-vrt', 1103)
        self.http = self.ingress = None
        self.threads = []
        m.terminal.STATE = m.terminal.State()

    def tearDown(self):
        self.stop_servers()
        self.runtime.ledger.close()
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def event(self, native='native:1', source_order=1, **changes):
        event = {'schema': m.SCHEMA, 'kind': 'READBACK', 'subject': copy.deepcopy(self.runtime.subject),
                 'provenance': {'source': 'repository', 'native_event_id': native, 'source_order': source_order},
                 'emitted_at': '2026-09-15T19:59:59Z',
                 'observed_at': '2026-09-15T20:00:00Z', 'message': 'native fixture readback',
                 'payload': {'receipt': 'fixture-only; not production evidence'}}
        event.update(changes)
        return event

    def start_servers(self):
        self.http = m.terminal.ThreadingHTTPServer(('127.0.0.1', 0), m.make_handler(self.runtime))
        self.ingress = m.make_ingress(self.runtime)
        for server in (self.http, self.ingress):
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            self.threads.append(t)

    def stop_servers(self):
        if self.http:
            self.runtime.ledger.stop()
            for server in (self.http, self.ingress):
                server.shutdown()
                server.server_close()
            for t in self.threads:
                t.join(timeout=3)
                self.assertFalse(t.is_alive())
            self.http = self.ingress = None
            self.threads = []

    def request(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection(*self.http.server_address, timeout=3)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        status = r.status
        c.close()
        return status, data

    def stream(self, query='', headers=None):
        c = http.client.HTTPConnection(*self.http.server_address, timeout=3)
        c.request('GET', '/api/temdd/events' + query, headers=headers or {})
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertTrue(r.getheader('Content-Type').startswith('text/event-stream'))
        first = self.frame(r)
        self.assertEqual(first['event'], 'subject')
        self.assertEqual(json.loads(first['data'])['subject'], self.runtime.subject)
        return c, r

    def frame(self, response):
        result = {}
        while True:
            line = response.readline()
            self.assertTrue(line, 'unexpected SSE EOF')
            if line == b'\n':
                return result
            key, value = line.decode().rstrip('\n').split(': ', 1)
            result[key] = value

    def disconnect(self, c, r):
        if c.sock:
            c.sock.shutdown(socket.SHUT_RDWR)
        r.close()
        c.close()

    def test_durable_restart_and_monotonic_ids(self):
        first = self.runtime.append(self.event())
        self.runtime.ledger.close()
        self.runtime = m.Runtime(self.root, self.state, 'Goldkelch/qik-vrt', 1103)
        self.assertEqual(self.runtime.ledger.replay(0), [first])
        second = self.runtime.append(self.event('native:2'))
        self.assertEqual(second['id'], first['id'].rsplit(':', 1)[0] + ':2')
        self.assertFalse(first['dod'])
        self.assertEqual(first['evidence_transfer'], 'DENY')
        self.assertEqual(first['payload_digest'], m.digest(self.event()['payload']))

    def test_idempotent_delivery_and_conflicting_native_id(self):
        first = self.runtime.append(self.event())
        self.assertEqual(self.runtime.append(self.event()), first)
        with self.assertRaisesRegex(m.Hold, 'CONFLICT'):
            self.runtime.append(self.event(message='changed'))
        self.assertEqual(len(self.runtime.ledger.replay(0)), 1)

    def test_wrong_head_tree_repository_and_pr_rejected(self):
        for field, value in [('head', 'a'*40), ('tree', 'b'*40), ('repository', 'ingolf-lohmann/qik-vrt'), ('pr', 1104)]:
            event = self.event()
            event['subject'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(m.Hold, 'SUBJECT_MISMATCH'):
                self.runtime.append(event)
        self.assertEqual(self.runtime.ledger.replay(0), [])

    def test_malformed_and_oversized_ingress_rejected(self):
        cases = [self.event(dod=True), self.event(kind='DONE'), self.event(payload=[]),
                 self.event(observed_at='not-a-time'), self.event(message='x'*4097),
                 self.event(payload={'oversized': 'x'*m.MAX_EVENT}), self.event(payload={'x': float('nan')})]
        event = self.event()
        event['provenance']['native_event_id'] = 'newline\nforgery'
        cases.append(event)
        for event in cases:
            with self.subTest(event=str(event)[:100]), self.assertRaises(ValueError):
                self.runtime.append(event)
        self.assertEqual(self.runtime.ledger.replay(0), [])

    def test_unknown_foreign_and_future_cursors_hold(self):
        first = self.runtime.append(self.event())
        bad = ['1', 'unknown:1', '0'*32+':1', first['id'].rsplit(':', 1)[0]+':999',
               first['id'].rsplit(':', 1)[0]+':9223372036854775808', first['id']+'\n']
        for cursor in bad:
            with self.subTest(cursor=cursor), self.assertRaises(m.Hold):
                self.runtime.ledger.cursor(cursor)
        self.assertEqual(self.runtime.ledger.cursor(first['id']), 1)

    def test_source_and_observation_order_are_independent(self):
        first = self.runtime.append(self.event('source:2', source_order=2))
        second = self.runtime.append(self.event('source:1', source_order=1))
        self.assertEqual((first['observation_order'], second['observation_order']), (1, 2))
        self.assertGreater(first['provenance']['source_order'], second['provenance']['source_order'])
        self.assertLess(first['observation_order'], second['observation_order'])

    def test_successor_never_replays_predecessor_evidence(self):
        first = self.runtime.append(self.event())
        self.runtime.ledger.close()
        (self.root/'successor.txt').write_text('new subject\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'successor')
        self.runtime = m.Runtime(self.root, self.state, 'Goldkelch/qik-vrt', 1103)
        self.assertEqual(self.runtime.ledger.replay(0), [])
        with self.assertRaisesRegex(m.Hold, 'STALE'):
            self.runtime.ledger.cursor(first['id'])
        with self.assertRaisesRegex(m.Hold, 'CONFLICT'):
            self.runtime.append(self.event())
        second = self.runtime.append(self.event('successor:2'))
        self.assertTrue(second['id'].endswith(':2'))
        self.assertNotEqual(first['subject'], second['subject'])

    def test_runtime_head_mutation_invalidates_observers(self):
        (self.root/'changed.txt').write_text('changed\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'changed')
        with self.assertRaisesRegex(m.Hold, 'CHANGED'):
            self.runtime.append(self.event())
        self.assertTrue(self.runtime.ledger.stopped)
        self.assertEqual(self.runtime.ledger.replay(0), [])

    def test_dirty_checkout_is_unobservable(self):
        (self.root/'docs/terminal/temdd/index.html').write_text('dirty')
        with self.assertRaisesRegex(m.Hold, 'DIRTY'):
            self.runtime.ensure_subject()
        self.assertTrue(self.runtime.ledger.stopped)

    def test_copied_checkout_ignores_stat_cache_drift_but_not_byte_changes(self):
        copied = Path(self.temp.name) / 'image-checkout'
        # Docker COPY changes cached inode/mtime metadata without changing Git bytes.
        shutil.copytree(self.root, copied, copy_function=shutil.copyfile)
        self.assertEqual(m.subject(copied, 'Goldkelch/qik-vrt', 1103), self.runtime.subject)
        (copied/'docs/terminal/temdd/index.html').write_text('actual byte mutation')
        with self.assertRaisesRegex(m.Hold, 'DIRTY'):
            m.subject(copied, 'Goldkelch/qik-vrt', 1103)

    def test_storage_failure_never_publishes(self):
        self.runtime.ledger.db.execute("CREATE TRIGGER deny BEFORE INSERT ON events BEGIN SELECT RAISE(FAIL, 'disk failure fixture'); END")
        with mock.patch.object(self.runtime.ledger.condition, 'notify_all') as notify:
            with self.assertRaises(sqlite3.Error):
                self.runtime.append(self.event())
            notify.assert_not_called()
        self.assertEqual(self.runtime.ledger.replay(0), [])

    def test_commit_before_notification_failure_is_replayable(self):
        with mock.patch.object(self.runtime.ledger.condition, 'notify_all', side_effect=RuntimeError('crash point')):
            with self.assertRaises(RuntimeError):
                self.runtime.append(self.event())
        self.runtime.ledger.close()
        self.runtime = m.Runtime(self.root, self.state, 'Goldkelch/qik-vrt', 1103)
        rows = self.runtime.ledger.replay(0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.runtime.append(self.event()), rows[0])

    def test_tampered_readback_holds(self):
        first = self.runtime.append(self.event())
        self.runtime.ledger.db.execute("UPDATE events SET body = replace(body, 'native fixture readback', 'tampered')")
        self.runtime.ledger.db.commit()
        with self.assertRaisesRegex(m.Hold, 'READBACK_MISMATCH'):
            self.runtime.ledger.replay(0)
        with self.assertRaises(m.Hold):
            self.runtime.ledger.cursor(first['id'])

    def test_store_has_exclusive_owner_and_private_ingress(self):
        with self.assertRaises(BlockingIOError):
            m.Ledger(self.state, self.runtime.subject)
        self.start_servers()
        self.assertEqual((self.state/'temdd').stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.state/'temdd/ingress.sock').stat().st_mode & 0o777, 0o600)

    def test_concurrent_native_deliveries_have_distinct_monotonic_ids(self):
        results, errors = [], []
        def append(i):
            try:
                results.append(self.runtime.ledger.append(self.event(f'parallel:{i}')))
            except BaseException as exc:
                errors.append(exc)
        threads = [threading.Thread(target=append, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
            self.assertFalse(t.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(sorted(int(x['id'].split(':')[1]) for x in results), list(range(1, 13)))

    def test_real_socket_sse_disconnect_replay_and_header_precedence(self):
        self.start_servers()
        c, r = self.stream()
        first = m.submit(self.state, self.event())['event']
        frame = self.frame(r)
        self.assertEqual(frame['id'], first['id'])
        self.assertEqual(json.loads(frame['data']), first)
        self.disconnect(c, r)
        second = m.submit(self.state, self.event('native:2'))['event']
        third = m.submit(self.state, self.event('native:3'))['event']
        self.assertFalse(self.runtime.ledger.stopped)
        c, r = self.stream('?after='+first['id'], {'Last-Event-ID': second['id']})
        self.assertEqual(self.frame(r)['id'], third['id'])
        self.disconnect(c, r)

    def test_disconnect_releases_observer_without_a_new_event(self):
        self.start_servers()
        c, r = self.stream()
        self.assertEqual(len(self.runtime.ledger.listeners), 1)
        self.disconnect(c, r)
        with self.runtime.ledger.condition:
            released = self.runtime.ledger.condition.wait_for(
                lambda: not self.runtime.ledger.listeners, timeout=3)
        self.assertTrue(released)
        self.assertFalse(self.runtime.ledger.stopped)
        self.assertEqual(self.runtime.ledger.replay(0), [])

    def test_real_socket_restart_preserves_replay(self):
        self.start_servers()
        first = m.submit(self.state, self.event())['event']
        self.stop_servers()
        self.runtime.ledger.close()
        self.runtime = m.Runtime(self.root, self.state, 'Goldkelch/qik-vrt', 1103)
        self.start_servers()
        second = m.submit(self.state, self.event('native:2'))['event']
        c, r = self.stream('?after='+first['id'])
        self.assertEqual(self.frame(r)['id'], second['id'])
        self.disconnect(c, r)

    def test_invalid_http_cursor_and_browser_writes_fail_closed(self):
        self.start_servers()
        for method, path, expected in [('GET', '/api/temdd/events?after=bad', 409),
                ('GET', '/api/temdd/events?after=x&after=y', 409),
                ('POST', '/api/temdd/events', 405)]:
            status, data = self.request(method, path, body='{}' if method=='POST' else None)
            self.assertEqual(status, expected)
            self.assertEqual(json.loads(data)['state'], 'HOLD')
        self.assertEqual(self.runtime.ledger.replay(0), [])

    def test_foreign_origin_and_rebinding_host_are_rejected(self):
        self.start_servers()
        for headers in [{'Origin': 'https://untrusted.invalid'}, {'Host': 'untrusted.invalid'}]:
            status, data = self.request('GET', '/api/temdd/subject', headers=headers)
            self.assertEqual(status, 403)
            self.assertFalse(json.loads(data)['dod'])

    def test_ai_surface_and_subject_are_served(self):
        self.start_servers()
        status, data = self.request('GET', '/AI')
        self.assertEqual(status, 200)
        self.assertIn(b'/api/temdd/events', data)
        status, data = self.request('GET', '/api/temdd/subject')
        envelope = json.loads(data)
        self.assertEqual(status, 200)
        self.assertEqual(envelope['subject'], self.runtime.subject)
        self.assertEqual(envelope['state'], 'HOLD_UNVERIFIED')
        self.assertFalse(envelope['dod'])

    def test_legacy_effect_ack_remains_exact_bound_and_single_use(self):
        self.start_servers()
        status, data = self.request('GET', '/.well-known/effect-ack')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)['external_effects'], 'NONE')
        payload = json.dumps({'schema': 'qikvrt_terminal_input_v1', 'text': 'fixture'})
        headers = {'Content-Type': 'application/json', 'Effect-Ack-Request': 'v=1, mode=prepare'}
        status, data = self.request('POST', '/terminal/prepare', payload, headers)
        prepared = json.loads(data)
        self.assertEqual(status, 200)
        headers['Effect-Ack-Request'] = ('v=1, mode=commit, token=' + m.terminal.sf_bytes(prepared['commit_token'].encode())
                                       + ', hash=' + m.terminal.sf_bytes(bytes.fromhex(prepared['record_hash'])))
        status, _ = self.request('POST', '/terminal/commit', payload.replace('fixture', 'different'), headers)
        self.assertEqual(status, 409)
        status, _ = self.request('POST', '/terminal/commit', payload, headers)
        self.assertEqual(status, 200)
        status, _ = self.request('POST', '/terminal/commit', payload, headers)
        self.assertEqual(status, 409)
        self.assertEqual(self.runtime.ledger.replay(0), [])  # terminal ACK is not a TEMDD proof

    def test_cli_append_is_finite_and_returns_durable_readback(self):
        self.start_servers()
        command = [sys.executable, '-B', str(ROOT/'src/qikvrt_temdd_event_ledger.py'),
                   'append', '--state-dir', str(self.state)]
        result = subprocess.run(command, input=json.dumps(self.event('cli:1')),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['state'], 'PERSISTED')
        self.assertFalse(receipt['authority_effect'])
        self.assertEqual(self.runtime.ledger.replay(0), [receipt['event']])
        wrong = self.event('cli:2')
        wrong['subject']['head'] = '0'*40
        result = subprocess.run(command, input=json.dumps(wrong),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)['state'], 'HOLD')
        self.assertEqual(len(self.runtime.ledger.replay(0)), 1)

    def test_repository_entrypoint_and_test_admission(self):
        entrypoint = (ROOT/'deploy/universal-terminal/entrypoint.sh').read_text()
        self.assertIn('src/qikvrt_temdd_event_ledger.py serve', entrypoint)
        self.assertIn('--state-dir "$STATE_DIR"', entrypoint)
        subprocess.run(['sh', '-n', str(ROOT/'deploy/universal-terminal/entrypoint.sh')],
                       check=True, timeout=5)
        makefile = (ROOT/'Makefile').read_text()
        self.assertIn('test: temdd-event-ledger-test', makefile)
        self.assertIn('tests/test_temdd_event_ledger.py', makefile)
        workflow = (ROOT/'.github/workflows/qikvrt_temdd.yml').read_text()
        self.assertIn('github.event.pull_request.head.sha || github.sha', workflow)
        self.assertIn('make temdd-event-ledger-test', workflow)
        self.assertIn("'REPOSITORY_FILE_MANIFEST.json.sha256'", workflow)
        self.assertNotIn("'REPOSITORY_FILE_MANIFEST.sha256'", workflow)

    def test_browser_ide_is_local_editable_and_effect_free(self):
        page = (ROOT/'docs/terminal/temdd/index.html').read_text(encoding='utf-8')
        self.assertIn('id="ideSource"', page)
        self.assertIn('ANALYZE → IR', page)
        self.assertIn('function analyzeTemdd(text)', page)
        self.assertIn('QIKVRT_DOD requires complete canonical predicate', page)
        self.assertIn('TRANSPORT_ACK != EFFECT_ACK', page)
        self.assertNotIn("fetch('/api/temdd/events',{method:'POST'", page)
        self.assertNotIn('fetch("/api/temdd/events",{method:"POST"', page)

    def test_browser_ide_parser_matches_reference_example_shape(self):
        page = (ROOT/'docs/terminal/temdd/index.html').read_text(encoding='utf-8')
        self.assertIn("schema:'temdd_ir_v0_1'", page)
        self.assertIn("version!=='0.1'", page)
        self.assertIn("binding:'exact'", page)
        self.assertIn('perspective', page)
        self.assertIn('source_order', page)
        self.assertIn('observation_order', page)
        self.assertIn('epistemic', page)
        self.assertIn('FRESH_EFFECT_READBACK', page)

    def test_consumer_validation_and_reconnect_state_machine(self):
        js = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1],'utf8'),script=html.match(/<script>([\s\S]*)<\/script>/)[1];
const elements=new Map(),storage=new Map(),sources=[];
const subj={repository:'Goldkelch/qik-vrt',pr:1103,head:'a'.repeat(40),tree:'b'.repeat(40)},epoch='c'.repeat(32);
class ES{constructor(url){this.url=url;this.handlers={};this.closed=false;sources.push(this);}addEventListener(n,f){this.handlers[n]=f;}close(){this.closed=true;}}
const ctx={document:{getElementById(id){if(!elements.has(id))elements.set(id,{textContent:'',className:'',scrollHeight:0});return elements.get(id);}},
 localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},EventSource:ES,
 fetch:async()=>({ok:true,json:async()=>({subject:subj,ledger_id:epoch,dod:false,evidence_transfer:'DENY'})}),Date,JSON,BigInt,Number,Error,console};
vm.createContext(ctx);vm.runInContext(script,ctx);
setImmediate(()=>{try{
 const es=sources[0];assert(es);es.onopen();assert.equal(elements.get('state').textContent,'CONNECTED');
 es.handlers.subject({data:JSON.stringify({subject:subj,ledger_id:epoch,dod:false,evidence_transfer:'DENY'})});
 assert.equal(elements.get('state').textContent,'OBSERVING');
 const event={schema:'qikvrt_temdd_event_v1',subject:subj,id:epoch+':1',kind:'READBACK',message:'<script>not html</script>',dod:false,evidence_transfer:'DENY',provenance:{source:'repository',native_event_id:'native:2',source_order:2},emitted_at:'2026-09-15T19:59:59Z',observed_at:'2026-09-15T20:00:00Z',observation_order:1};
 es.onmessage({data:JSON.stringify(event),lastEventId:event.id});assert.equal(storage.size,1);
 es.onerror();assert.equal(es.closed,false);assert.equal(elements.get('state').textContent,'HOLD');assert.equal(elements.get('dod').textContent,'NOT PROVEN');
 es.onopen();es.handlers.subject({data:JSON.stringify({subject:subj,ledger_id:epoch,dod:false,evidence_transfer:'DENY'})});
 event.id=epoch+':2';event.observation_order=2;event.provenance.source_order=1;event.dod=true;es.onmessage({data:JSON.stringify(event),lastEventId:event.id});
 assert.equal(es.closed,true);assert.equal(elements.get('dod').textContent,'NOT PROVEN');assert.equal([...storage.values()][0],epoch+':1');
 console.log('consumer reconnect, exact-subject binding, and false-DONE rejection PASS');
}catch(e){console.error(e);process.exitCode=1;}});
'''
        result = subprocess.run(['node', '-e', js, str(ROOT/'docs/terminal/temdd/index.html')],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
