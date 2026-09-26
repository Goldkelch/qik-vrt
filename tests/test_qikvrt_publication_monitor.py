# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Synthetic fixtures prove adapter/state behavior, not live platform availability."""
import copy
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('monitor', ROOT / 'tools/qikvrt_publication_monitor.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
POLICY = m.load_json((ROOT / 'policy/PUBLICATION_MONITOR_V1.json').read_bytes())
NOW = '2026-09-26T12:00:00Z'
SOURCE = {'head': 'a' * 40, 'tree': 'b' * 40, 'run_id': 'local-test'}


def proof(url='https://crates.io/api/v1/crates/qik-vrt', now=NOW, status=200, raw=b'fixture'):
    return {'evidence_class': 'PUBLIC_READBACK', 'method': 'GET', 'url': url,
            'observed_at': now, 'status': status, 'response_sha256': m.digest(raw),
            'response_path': 'monitor/responses/' + m.digest(raw) + '.body'}


def crate(yanked=False, owner='ingolf-lohmann', num='1.0.0', ident=1):
    data = {'crate': {'id': 'qik-vrt', 'name': 'qik-vrt', 'versions': [ident],
                     'max_version': num, 'repository': 'https://github.com/Goldkelch/qik-vrt'},
            'versions': [{'id': ident, 'num': num, 'crate': 'qik-vrt', 'yanked': yanked}]}
    owners = {'users': [{'id': 294949349, 'login': owner, 'kind': 'user'}]}
    return data, owners


def zenodo():
    return {'id': 22941556, 'doi': '10.5281/zenodo.22941556',
            'metadata': {'title': 'Proof Closure', 'creators': [{'name': 'Lohmann, Ingolf'}], 'version': '1.0.0'},
            'files': [{'key': 'README.md', 'checksum': 'md5:' + 'a' * 32, 'size': 42}]}


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def read(self, url, xml=False):
        self.calls.append(url)
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result, proof(url)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.state = m.genesis(POLICY, SOURCE)
        self.l = m.Ledger(self.state, POLICY, NOW)

    def test_consumed_zero_baseline_preserved_silently(self):
        p = self.state['platforms']['cratesio']
        self.assertTrue(p['baseline_established'])
        self.assertEqual(p['queries']['canonical'], {'queries': {'cloud-transputer': 0, 'qik-vrt': 0, 'qikvrt': 0, 'temdd': 0}, 'relevant_crates': []})
        self.assertEqual(self.state['outbox'], {})

    def test_historical_ack_is_not_public_state(self):
        self.assertEqual(self.state['platforms']['zenodo']['subjects'], {})
        self.assertFalse(self.state['migration']['historical_reports_are_public_readback'])
        self.assertFalse(self.state['migration']['complete_prior_inventory_recovered'])
        p = ROOT / POLICY['migration']['historical_ack_path']
        self.assertEqual(m.digest(p.read_bytes()), POLICY['migration']['historical_ack_sha256'])

    def test_new_crate_version_after_zero_baseline_is_material(self):
        self.l.accept('cratesio', 'version:qik-vrt@1.0.0', {'yanked': False}, proof())
        event = next(iter(self.l.state['outbox'].values()))
        self.assertIsNone(event['old'])
        self.assertEqual(event['subject'], 'version:qik-vrt@1.0.0')
        self.assertEqual(event['new']['state'], {'yanked': False})

    def test_first_recovered_zenodo_subject_is_not_reannounced(self):
        self.l.accept('zenodo', 'record:22941556', zenodo(), proof('https://zenodo.org/api/records/22941556'))
        self.assertEqual(self.l.state['outbox'], {})
        self.l.finish('zenodo', {'q': [22941556]})
        self.assertTrue(self.l.state['platforms']['zenodo']['baseline_established'])

    def test_same_subject_replay_does_not_duplicate(self):
        for _ in range(3):
            self.l.accept('cratesio', 'version:qik-vrt@1.0.0', {'yanked': False}, proof())
        self.assertEqual(len(self.l.state['outbox']), 1)

    def test_real_repeated_yank_transition_has_new_event(self):
        for state in (False, True, False, True):
            self.l.accept('cratesio', 'version:qik-vrt@1.0.0', {'yanked': state}, proof())
        self.assertEqual(len(self.l.state['outbox']), 4)

    def test_new_version_cannot_validate_predecessor(self):
        self.l.accept('cratesio', 'version:qik-vrt@1.0.0', {'yanked': False}, proof())
        old = copy.deepcopy(self.l.state['platforms']['cratesio']['subjects']['version:qik-vrt@1.0.0'])
        self.l.accept('cratesio', 'version:qik-vrt@2.0.0', {'yanked': True}, proof())
        self.assertEqual(self.l.state['platforms']['cratesio']['subjects']['version:qik-vrt@1.0.0'], old)

    def test_failure_retains_last_good_and_outbox(self):
        self.l.accept('cratesio', 'crate:qik-vrt', {'name': 'qik-vrt'}, proof())
        before = copy.deepcopy(self.l.state['platforms']['cratesio']['subjects'])
        outbox = copy.deepcopy(self.l.state['outbox'])
        for status in (None, 403, 429, 500, 503):
            self.l.failure('cratesio', 'crate:qik-vrt', m.ReadError('failure', status, proof(status=status)))
        self.l.finish('cratesio', None)
        self.assertEqual(before, self.l.state['platforms']['cratesio']['subjects'])
        self.assertEqual(outbox, self.l.state['outbox'])
        self.assertEqual(self.l.state['platforms']['cratesio']['health'], 'READ_FAILED_PRESERVED_LAST_GOOD')

    def test_one_404_is_not_disappearance(self):
        self.l.accept('cratesio', 'crate:qik-vrt', {'name': 'qik-vrt'}, proof())
        self.l.failure('cratesio', 'crate:qik-vrt', m.ReadError('404', 404, proof(status=404)), True)
        self.assertTrue(self.l.state['platforms']['cratesio']['subjects']['crate:qik-vrt']['available'])
        self.assertEqual(len(self.l.state['outbox']), 1)

    def test_two_official_404s_with_working_inventory_preserve_last_metadata(self):
        self.l.accept('cratesio', 'crate:qik-vrt', {'name': 'qik-vrt'}, proof())
        self.l.failure('cratesio', 'crate:qik-vrt', m.ReadError('404', 404, proof(status=404)), True)
        later = '2026-09-26T12:02:00Z'
        l = m.Ledger(self.l.state, POLICY, later)
        l.failure('cratesio', 'crate:qik-vrt', m.ReadError('404', 404, proof(now=later, status=404)), True)
        item = l.state['platforms']['cratesio']['subjects']['crate:qik-vrt']
        self.assertFalse(item['available'])
        self.assertEqual(item['canonical'], {'name': 'qik-vrt'})
        self.assertEqual(len(l.state['outbox']), 2)
        l.accept('cratesio', 'crate:qik-vrt', {'name': 'qik-vrt'}, proof(now=later))
        self.assertEqual(len(l.state['outbox']), 3)

    def test_owner_endpoint_failure_cannot_remove_crate(self):
        self.l.accept('cratesio', 'crate:qik-vrt', {'name': 'qik-vrt'}, proof())
        for now in (NOW, '2026-09-26T12:02:00Z'):
            self.l.now = now
            self.l.failure('cratesio', 'crate:qik-vrt', m.ReadError('404', 404, proof('https://crates.io/api/v1/crates/qik-vrt/owners', now, 404)), True)
        self.assertTrue(self.l.state['platforms']['cratesio']['subjects']['crate:qik-vrt']['available'])
        self.assertNotIn('pending_absence', self.l.state['platforms']['cratesio']['subjects']['crate:qik-vrt'])

    def test_corruption_and_policy_drift_fail_closed(self):
        self.state['policy_sha256'] = '0' * 64
        with self.assertRaises(m.MonitorError):
            m.validate_state(self.state, POLICY)

    def test_string_or_missing_evidence_is_not_success(self):
        for bad in ({}, {**proof(), 'status': '200'}, {**proof(), 'evidence_class': 'PRIOR_ASSISTANT_REPORT_NOT_FRESH_PUBLIC_READBACK'}):
            with self.assertRaises(m.MonitorError):
                self.l.accept('zenodo', 'record:22941556', zenodo(), bad)

    def test_retry_after_preserved_without_platform_alert(self):
        ev = {**proof(status=429), 'retry_after': '3600'}
        self.l.failure('cratesio', 'query:qik-vrt', m.ReadError('quota', 429, ev))
        self.l.finish('cratesio', None)
        self.assertEqual(self.l.state['platforms']['cratesio']['retry_not_before'], '2026-09-26T13:00:00Z')
        self.assertEqual(self.l.state['outbox'], {})


class AdapterTests(unittest.TestCase):
    def test_complete_empty_inventory_not_missing_total(self):
        items, _ = m.paged_json(Client([{'meta': {'total': 0}, 'crates': []}]), 'https://crates.io/api/v1/crates', {'q': 'temdd'}, 'cratesio', 2)
        self.assertEqual(items, [])
        with self.assertRaises((m.MonitorError, KeyError)):
            m.paged_json(Client([{'crates': []}]), 'https://crates.io/api/v1/crates', {}, 'cratesio', 2)

    def test_truncated_and_duplicate_paging_rejected(self):
        for responses in ([{'meta': {'total': 1}, 'crates': []}],
                          [{'meta': {'total': 2}, 'crates': [{'id': 'a'}]}, {'meta': {'total': 2}, 'crates': [{'id': 'a'}]}],
                          [{'meta': {'total': {'relation': 'gte', 'value': 0}}, 'crates': []}]):
            with self.assertRaises(m.MonitorError):
                m.paged_json(Client(responses), 'https://crates.io/api/v1/crates', {}, 'cratesio', 2)

    def test_pagination_collects_all_unique_subjects(self):
        c = Client([{'meta': {'total': 2}, 'crates': [{'id': 'a'}]}, {'meta': {'total': 2}, 'crates': [{'id': 'b'}]}])
        result, _ = m.paged_json(c, 'https://crates.io/api/v1/crates', {}, 'cratesio', 2)
        self.assertEqual([r['id'] for r in result], ['a', 'b'])
        self.assertIn('page=2', c.calls[1])

    def test_crates_exact_owners_and_version_identity(self):
        data, owners = crate()
        result = m.crate_subjects(data, owners, 'qik-vrt')
        self.assertEqual(result['crate:qik-vrt']['owners'][0]['login'], 'ingolf-lohmann')
        self.assertEqual(result['version:qik-vrt@1.0.0']['id'], 1)
        self.assertFalse(result['version:qik-vrt@1.0.0']['yanked'])

    def test_incomplete_version_inventory_does_not_remove_predecessor(self):
        data, owners = crate()
        data['crate']['versions'].append(2)
        with self.assertRaises(m.MonitorError):
            m.crate_subjects(data, owners, 'qik-vrt')

    def test_string_false_yanked_rejected(self):
        data, owners = crate(yanked='false')
        with self.assertRaises(m.MonitorError):
            m.crate_subjects(data, owners, 'qik-vrt')

    def test_download_counts_do_not_change_identity(self):
        data, owners = crate()
        before = m.crate_subjects(data, owners, 'qik-vrt')
        data['crate']['downloads'] = 123456
        data['versions'][0]['downloads'] = 99999
        self.assertEqual(before, m.crate_subjects(data, owners, 'qik-vrt'))

    def test_crate_owner_and_project_link_changes_remain_visible(self):
        data, owners = crate()
        before = m.crate_subjects(data, owners, 'qik-vrt')
        owners['users'][0]['login'] = 'different-owner'
        data['crate']['repository'] = None
        self.assertNotEqual(before, m.crate_subjects(data, owners, 'qik-vrt'))

    def test_no_inferred_zenodo_concept(self):
        value = m.zenodo_record(zenodo(), '22941556')
        self.assertIsNone(value['concept_id'])
        self.assertIsNone(value['concept_doi'])

    def test_wrong_record_and_invalid_digest_rejected(self):
        with self.assertRaises(m.MonitorError):
            m.zenodo_record(zenodo(), '22941555')
        item = zenodo()
        item['files'][0]['checksum'] = 'md5:short'
        with self.assertRaises(m.MonitorError):
            m.zenodo_record(item, '22941556')

    def test_public_metadata_does_not_claim_redownload(self):
        self.assertEqual(m.zenodo_record(zenodo(), '22941556')['file_evidence_scope'], 'PUBLISHER_METADATA_NOT_FRESH_FILE_REDOWNLOAD')

    def test_stats_and_order_not_identity_changes(self):
        value = zenodo()
        first = m.zenodo_record(value, '22941556')
        value['stats'] = {'downloads': 98765}
        self.assertEqual(first, m.zenodo_record(value, '22941556'))

    def test_wiki_missing_is_explicit_only(self):
        value = {'query': {'pages': [{'title': 'QIK-VRT', 'missing': True}]}}
        self.assertFalse(m.wiki_page(value, 'QIK-VRT')['exists'])
        with self.assertRaises(m.MonitorError):
            m.wiki_page({'query': {'pages': []}}, 'QIK-VRT')
        with self.assertRaises(m.MonitorError):
            m.wiki_page({'error': {'code': 'maxlag'}}, 'QIK-VRT')

    def test_wiki_positive_binds_revision(self):
        value = {'query': {'pages': [{'title': 'QIK-VRT', 'pageid': 5, 'revisions': [{'revid': 6, 'timestamp': NOW, 'sha1': 'abc'}]}]}}
        result = m.wiki_page(value, 'QIK-VRT')
        self.assertEqual(result['pageid'], 5)
        self.assertEqual(result['revision']['revid'], 6)

    def test_arxiv_exact_version_required(self):
        xml = '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>1</o:totalResults><entry><id>http://arxiv.org/abs/2609.12345v2</id><title>Example</title></entry></feed>'
        count, records = m.arxiv_entries(ET.fromstring(xml))
        self.assertEqual(count, 1)
        self.assertEqual(records[0]['version_id'], '2609.12345v2')
        with self.assertRaises(m.MonitorError):
            m.arxiv_entries(ET.fromstring(xml.replace('2609.12345v2', '2609.12345')))

    def test_arxiv_error_entry_is_not_absence(self):
        xml = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#badquery</id></entry></feed>'
        with self.assertRaises(m.MonitorError):
            m.arxiv_entries(ET.fromstring(xml))

    def test_query_schemas_reject_boolean_totals(self):
        with self.assertRaises(m.MonitorError):
            m.total(False)

    def test_read_transport_forbids_effects_secrets_and_redirect_targets(self):
        bad = ['http://zenodo.org/api/records', 'https://zenodo.org/api/deposit/depositions',
               'https://crates.io/api/v1/crates/new?token=abc', 'https://u:p@crates.io/api/v1/crates',
               'https://evil.example/api/records', 'https://en.wikipedia.org/w/api.php?action=edit',
               'https://zenodo.org/api/records?access_token=secret', 'https://zenodo.org/api/records?q=a&q=b']
        for url in bad:
            with self.subTest(url=url), self.assertRaises((m.MonitorError, ValueError)):
                m.allowed_url(url)
        self.assertEqual(m.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example'), None)

    def test_duplicate_json_and_nan_rejected(self):
        for data in (b'{"total":0,"total":1}', b'{"total":NaN}'):
            with self.assertRaises(m.MonitorError):
                m.load_json(data)


class PersistenceTests(unittest.TestCase):
    def test_missing_state_is_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(m.MonitorError):
                m.safe_read(Path(directory) / m.STATE_PATH)

    def test_roundtrip_history_and_cas(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = m.canonical(m.genesis(POLICY, SOURCE))
            m.atomic_write(root / m.STATE_PATH, before)
            state = m.load_json(before)
            sha, history = m.publish_local_snapshot(root, before, state)
            self.assertEqual(m.digest(m.safe_read(root / m.STATE_PATH)), sha)
            self.assertEqual(m.safe_read(root / history), m.safe_read(root / m.STATE_PATH))
            self.assertEqual(m.load_json(m.safe_read(root / history))['previous_state_sha256'], m.digest(before))
            with self.assertRaises(m.MonitorError):
                m.publish_local_snapshot(root, before, m.load_json(before))

    def test_restart_can_read_and_cannot_reinitialize(self):
        with tempfile.TemporaryDirectory() as directory:
            base = [sys.executable, '-B', str(ROOT / 'tools/qikvrt_publication_monitor.py')]
            flags = ['--policy', str(ROOT / 'policy/PUBLICATION_MONITOR_V1.json'), '--store', directory]
            init = base + ['initialize'] + flags + ['--source-head', 'a' * 40, '--source-tree', 'b' * 40, '--run-id', 'local-test']
            subprocess.run(init, check=True, capture_output=True)
            value = subprocess.run(base + ['validate'] + flags, check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(value.stdout)['generation'], 0)
            self.assertEqual(subprocess.run(init, capture_output=True).returncode, 2)

    def test_symlinks_and_parallel_writers_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory)
            with m.exclusive_store(store):
                with self.assertRaises(m.MonitorError):
                    with m.exclusive_store(store):
                        pass
            (store / 'outside').mkdir()
            (store / 'alias').symlink_to(store / 'outside', target_is_directory=True)
            with self.assertRaises(m.MonitorError):
                m.atomic_write(store / 'alias' / 'file.json', b'{}')

    def test_consumed_event_is_retained_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory)
            ledger = m.Ledger(m.genesis(POLICY, SOURCE), POLICY, NOW)
            ledger.accept('cratesio', 'crate:qik-vrt', {'name': 'qik-vrt'}, proof())
            identifier = next(iter(ledger.state['outbox']))
            raw = m.canonical(ledger.state)
            m.atomic_write(store / m.STATE_PATH, raw)
            m.atomic_write(store / 'monitor/history' / ('%012d-%s.json' % (0, m.digest(raw))), raw)
            m.atomic_write(store / proof()['response_path'], b'fixture')
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/qikvrt_publication_monitor.py'), 'acknowledge', '--store', directory, '--event-id', identifier], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = m.load_json(m.safe_read(store / m.STATE_PATH))
            self.assertEqual(state['outbox'], {})
            self.assertIn(identifier, state['acknowledged_events'])
            m.validate_state(state, POLICY)


    def test_streaming_read_timeout_becomes_read_error(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def geturl(self): return 'https://crates.io/api/v1/crates'
            def read(self, size): raise TimeoutError('synthetic network timeout')
        with tempfile.TemporaryDirectory() as directory:
            client = m.PublicGET(POLICY, Path(directory))
            with patch.object(client.opener, 'open', return_value=Response()):
                with self.assertRaises(m.ReadError):
                    client.read('https://crates.io/api/v1/crates')

    def test_persisted_public_bytes_and_history_are_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory)
            state = m.genesis(POLICY, SOURCE)
            raw = m.canonical(state)
            m.atomic_write(store / m.STATE_PATH, raw)
            m.atomic_write(store / 'monitor/history' / ('%012d-%s.json' % (0,m.digest(raw))), raw)
            ledger = m.Ledger(state, POLICY, NOW)
            ledger.accept('cratesio', 'crate:qik-vrt', {'name':'qik-vrt'}, proof())
            m.atomic_write(store / proof()['response_path'], b'fixture')
            m.publish_local_snapshot(store, raw, ledger.state)
            m.validate_store(store, ledger.state, POLICY)
            (store / proof()['response_path']).write_bytes(b'changed')
            with self.assertRaises(m.MonitorError):
                m.validate_store(store, ledger.state, POLICY)
            (store / proof()['response_path']).write_bytes(b'fixture')
            (store / 'monitor/history' / ('%012d-%s.json' % (0,m.digest(raw)))).unlink()
            with self.assertRaises(m.MonitorError):
                m.validate_store(store, ledger.state, POLICY)

    def test_zenodo_public_page_size_matches_observed_anonymous_limit(self):
        client = Client([{'hits': {'total': 0, 'hits': []}}])
        m.paged_json(client, 'https://zenodo.org/api/records', {}, 'zenodo', 2)
        self.assertIn('size=25', client.calls[0])
        self.assertNotIn('size=100', client.calls[0])

    def test_xml_media_negotiation_and_main_effect_trigger(self):
        source = (ROOT / 'tools/qikvrt_publication_monitor.py').read_text()
        self.assertIn('application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.1', source)
        workflow = (ROOT / '.github/workflows/qikvrt_publication_monitor.yml').read_text()
        self.assertIn('push:\n    branches: [main]', workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)

    def test_required_ci_registers_regressions(self):
        ci = (ROOT / '.github/workflows/qikvrt_ci.yml').read_text()
        self.assertIn('python3 -B tests/test_qikvrt_publication_monitor.py', ci)


if __name__ == '__main__':
    unittest.main(verbosity=2)
