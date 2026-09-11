# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Real temporary Git objects and filesystem readback; no network or fake PASS."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_evidence_sphere_step as sphere


class EvidenceSphereTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.repo = self.home / 'repo'
        self.repo.mkdir()
        self.run_git('init', '-q')
        self.run_git('config', 'user.name', 'QIK-VRT Test Fixture')
        self.run_git('config', 'user.email', 'fixture@example.invalid')
        self.run_git('remote', 'add', 'origin', 'https://github.com/example/qik-vrt.git')
        (self.repo / 'a.txt').write_bytes(b'first observed bytes\n')
        (self.repo / 'b.txt').write_bytes(b'second observed bytes\n')
        (self.repo / 'alias.txt').write_bytes(b'first observed bytes\n')
        (self.repo / 'symlink').symlink_to('a.txt')
        self.run_git('add', '.')
        self.run_git('commit', '-qm', 'fixture')
        self.head = self.run_git('rev-parse', 'HEAD').strip()
        self.ledger = self.home / 'ledger.jsonl'
        self.event = self.observe('a.txt')

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE, text=True)

    def observe(self, path):
        return sphere.observe(self.repo, 'example/qik-vrt', self.head, path)

    def apply(self, event=None, **kwargs):
        return sphere.step(self.repo, self.ledger, event or self.event,
                           sphere.inspect(self.ledger)['root'], apply=True, **kwargs)

    def test_first_real_byte_observation_grows_and_reopens(self):
        old = sphere.inspect(self.ledger)
        result = self.apply()
        self.assertEqual(result['decision'], 'APPEND')
        self.assertEqual((result['nodes_added'], result['relations_added'], result['new_content_objects']), (3, 1, 1))
        self.assertTrue(result['reobserved'])
        self.assertEqual(result['old_root'], old['root'])
        self.assertEqual(result['new_root'], sphere.inspect(self.ledger)['root'])
        self.assertNotEqual(result['old_root'], result['new_root'])
        self.assertFalse(result['ordinary_release'])
        self.assertEqual(result['external_effect'], 'NONE')

    def test_duplicate_is_byte_preserving_noop(self):
        self.apply()
        raw = self.ledger.read_bytes()
        result = self.apply()
        self.assertEqual(result['decision'], 'NOOP')
        self.assertEqual(result['new_content_objects'], 0)
        self.assertEqual(result['old_root'], result['new_root'])
        self.assertEqual(raw, self.ledger.read_bytes())

    def test_restart_reconstructs_same_graph(self):
        self.apply()
        one = sphere.SphereLedger(self.ledger)
        two = sphere.SphereLedger(self.ledger)
        self.assertEqual(one.graph, two.graph)
        self.assertEqual(one.previous_record_sha256, two.previous_record_sha256)
        self.assertEqual(one.sequence, 1)

    def test_no_apply_requires_local_write_authorization(self):
        result = sphere.step(self.repo, self.ledger, self.event, sphere.inspect(self.ledger)['root'])
        self.assertEqual(result['decision'], 'REQUEST_AUTHORITY')
        self.assertFalse(self.ledger.exists())

    def test_stale_expected_root_cannot_append(self):
        old = sphere.inspect(self.ledger)['root']
        self.apply()
        raw = self.ledger.read_bytes()
        result = sphere.step(self.repo, self.ledger, self.observe('b.txt'), old, apply=True)
        self.assertEqual(result['reason'], 'STALE_EXPECTED_ROOT')
        self.assertEqual(raw, self.ledger.read_bytes())

    def test_forged_content_digest_cannot_grow(self):
        result = self.apply({**self.event, 'sha256': '0'*64})
        self.assertEqual(result['decision'], 'HOLD')
        self.assertFalse(self.ledger.exists())

    def test_forged_tree_cannot_grow(self):
        self.assertEqual(self.apply({**self.event, 'tree': '0'*40})['decision'], 'HOLD')
        self.assertFalse(self.ledger.exists())

    def test_forged_blob_cannot_grow(self):
        self.assertEqual(self.apply({**self.event, 'blob': '0'*40})['decision'], 'HOLD')

    def test_self_claim_is_not_an_observation(self):
        for field in ('PASS', 'EFFECT_ACK_DONE', 'approved', 'truth', 'delivery_id'):
            with self.subTest(field=field):
                self.assertEqual(self.apply({**self.event, field: True})['reason'], 'EXACT_EVENT_FIELDS_REQUIRED')
        self.assertFalse(self.ledger.exists())

    def test_same_tree_successor_is_binding_not_new_content(self):
        first = self.apply()
        self.run_git('commit', '--allow-empty', '-qm', 'new exact subject')
        self.head = self.run_git('rev-parse', 'HEAD').strip()
        event = self.observe('a.txt')
        self.assertEqual(event['tree'], self.event['tree'])
        result = self.apply(event)
        self.assertEqual(result['decision'], 'APPEND')
        self.assertEqual(result['new_content_objects'], 0)
        self.assertEqual(result['growth_kind'], 'NEW_SUBJECT_OR_PATH_BINDING')
        self.assertEqual(result['old_root'], first['new_root'])

    def test_stale_head_does_not_inherit_validity(self):
        self.run_git('commit', '--allow-empty', '-qm', 'new head')
        self.assertEqual(self.apply()['reason'], 'HEAD_DRIFT')
        self.assertFalse(self.ledger.exists())

    def test_identical_blob_different_path_adds_only_binding(self):
        self.apply()
        result = self.apply(self.observe('alias.txt'))
        self.assertEqual((result['nodes_added'], result['relations_added'], result['new_content_objects']), (0, 1, 0))

    def test_new_content_preserves_previous_nodes_relations_and_prefix(self):
        self.apply()
        old = sphere.inspect(self.ledger)
        prefix = self.ledger.read_bytes()
        result = self.apply(self.observe('b.txt'))
        new = sphere.inspect(self.ledger)
        self.assertEqual(result['new_content_objects'], 1)
        self.assertTrue(self.ledger.read_bytes().startswith(prefix))
        for key in ('nodes', 'relations'):
            for identity, item in old['graph'][key].items():
                self.assertEqual(item, new['graph'][key][identity])

    def test_independent_order_does_not_change_semantic_root(self):
        a, b = self.event, self.observe('b.txt')
        one, _ = sphere.plan(sphere.empty_graph(), a)
        one, _ = sphere.plan(one, b)
        two, _ = sphere.plan(sphere.empty_graph(), b)
        two, _ = sphere.plan(two, a)
        self.assertEqual(sphere.graph_root(one), sphere.graph_root(two))

    def test_semantic_tamper_even_with_rehashed_record_fails(self):
        self.apply()
        record = json.loads(self.ledger.read_text())
        record['response']['receipt']['new_content_objects'] = 42
        record.pop('record_sha256')
        record['record_sha256'] = sphere.canonical_sha256(record)
        self.ledger.write_bytes(sphere.canonical_json_bytes(record) + b'\n')
        with self.assertRaises(sphere.SphereError):
            sphere.inspect(self.ledger)

    def test_broken_hash_fails(self):
        self.apply()
        record = json.loads(self.ledger.read_text())
        record['message_id'] = 'forged'
        self.ledger.write_text(json.dumps(record) + '\n')
        with self.assertRaises(sphere.MeshRuntimeError):
            sphere.inspect(self.ledger)

    def test_torn_append_fails_closed(self):
        self.apply()
        self.ledger.write_bytes(self.ledger.read_bytes()[:-1])
        with self.assertRaises(sphere.MeshRuntimeError):
            sphere.inspect(self.ledger)

    def test_competing_writer_does_not_poll_or_append(self):
        with sphere.locked(self.ledger):
            result = sphere.step(self.repo, self.ledger, self.event,
                                 sphere.graph_root(sphere.empty_graph()), apply=True)
        self.assertEqual(result['reason'], 'COMPETING_WRITER_ACTIVE')
        self.assertFalse(self.ledger.exists())

    def test_ledger_symlink_is_rejected(self):
        target = self.home / 'target'
        target.write_bytes(b'protected')
        self.ledger.symlink_to(target)
        result = sphere.step(self.repo, self.ledger, self.event, 'invalid', apply=True)
        self.assertEqual(result['reason'], 'LEDGER_SYMLINK')
        self.assertEqual(target.read_bytes(), b'protected')

    def test_source_symlink_is_not_regular_evidence(self):
        with self.assertRaises(sphere.SphereError):
            self.observe('symlink')

    def test_literal_path_cannot_inject_or_traverse(self):
        for path in ('../a.txt', '/a.txt', 'a.txt\n', './a.txt', 'a//b', '*'):
            with self.subTest(path=path), self.assertRaises(sphere.SphereError):
                self.observe(path)

    def test_origin_configuration_is_checked(self):
        self.run_git('remote', 'set-url', 'origin', 'https://github.com/other/qik-vrt.git')
        self.assertEqual(self.apply()['reason'], 'ORIGIN_CONFIGURATION_MISMATCH')

    def test_second_witness_must_still_match_before_append(self):
        changed = {**self.event, 'tree': '1'*40}
        with mock.patch.object(sphere, 'observe', side_effect=[self.event, changed]):
            result = self.apply()
        self.assertEqual(result['reason'], 'PRE_APPEND_SUBJECT_DRIFT')
        self.assertFalse(self.ledger.exists())

    def test_contract_and_proof_class_are_bound(self):
        self.apply()
        state = sphere.inspect(self.ledger)
        relation = next(iter(state['graph']['relations'].values()))
        self.assertEqual(relation['epistemic_class'], 'BYTE_OBSERVATION_NOT_CONTENT_TRUTH')
        self.assertIn(relation['contract'], state['graph']['nodes'])
        record = json.loads(self.ledger.read_text())
        self.assertEqual(record['response']['receipt']['contract'], sphere.CONTRACT_ID)


if __name__ == '__main__':
    unittest.main()
