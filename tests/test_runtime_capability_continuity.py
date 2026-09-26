# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
import copy
import tempfile
import unittest
from pathlib import Path
from tools.qikvrt_capability_continuity import plan
from tools.qikvrt_outlook_continuity import (
    Journal, binding, destination, move_one, reconcile, close_window,
)


def message():
    return dict(id='old', parentFolderId='in', folder_kind='inbox', kind='received',
                body='routine', subject='example', **{'from': 'sender'}, to=[], cc=[], bcc=[],
                attachments=[], isRead=False, isDraft=False, internetMessageId='example-id')


def decision(m, **overrides):
    return dict(snapshot_sha256=binding(m), attention='routine', project='ChatGPT',
                classification_complete=True, evidence=['fixture'], **overrides)


class Adapter:
    def __init__(self):
        self.messages = {'old': message()}
        self.moves = 0
        self.fail_readback = False

    def folders(self):
        return {'inbox':'in', 'ChatGPT':'chat', 'AbNan – Jamshed':'ab', 'QIK-VRT':'qik', 'QIK-VRT/Privat':'private'}

    def snapshot(self, ident):
        if self.fail_readback and ident == 'new':
            raise OSError('simulated disconnect')
        return copy.deepcopy(self.messages[ident])

    def move(self, ident, target):
        self.moves += 1
        msg = self.messages.pop(ident)
        msg.update(id='new', parentFolderId=target)
        self.messages['new'] = msg
        return {'id':'new'}

    def member(self, folder, ident):
        return self.messages.get(ident, {}).get('parentFolderId') == folder


class ContinuityTests(unittest.TestCase):
    def test_inventory_never_asserts_operational_parity(self):
        p = plan()
        self.assertEqual(p['coverage']['observed'], p['coverage']['accounted_for'])
        self.assertGreater(p['coverage']['observed'], 0)
        self.assertEqual(p['coverage']['operationally_migrated'], 0)
        self.assertTrue(all(not r['safe_to_retire_source'] for r in p['capabilities']))

    def test_unknown_attention_stays_inbox(self):
        m = message()
        d = decision(m)
        d.pop('attention')
        self.assertIsNone(destination(m, d, {'chat'}, 'in'))

    def test_stale_decision_rejected(self):
        m = message()
        d = decision(m)
        m['body'] = 'new question'
        with self.assertRaises(ValueError): destination(m, d, {'chat'}, 'in')

    def test_cc_and_managed_attention_restored_but_user_filing_preserved(self):
        m = message()
        m['parentFolderId'] = 'chat'
        d = decision(m, control_cc=True, placement='managed')
        self.assertEqual(destination(m, d, {'chat'}, 'in'), 'in')
        d['placement'] = 'user'
        self.assertIsNone(destination(m, d, {'chat'}, 'in'))

    def test_junk_and_deleted_exclusions(self):
        m = message()
        for kind in ['junk', 'deleted']:
            m['folder_kind'] = kind
            self.assertIsNone(destination(m, decision(m), {'chat'}, 'in'))

    def test_incomplete_semantics_not_sorted(self):
        m = message()
        d = decision(m)
        d['evidence'] = []
        self.assertIsNone(destination(m, d, {'chat'}, 'in'))

    def test_move_new_id_readback_and_unread_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = Journal(Path(tmp)/'private.db', initialize=True)
            a = Adapter()
            self.assertEqual(move_one(a,j,'old',decision(a.snapshot('old'))),'moved')
            self.assertEqual(a.moves,1)
            self.assertFalse(a.snapshot('new')['isRead'])
            self.assertFalse(j.pending())
            self.assertEqual(move_one(a,j,'new',decision(a.snapshot('new'))),'already_present')
            self.assertEqual(a.moves,1)
            j.db.close()

    def test_disconnect_restart_reconciles_without_second_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'private.db'
            j = Journal(path, initialize=True)
            a = Adapter()
            a.fail_readback = True
            with self.assertRaises(OSError): move_one(a,j,'old',decision(a.snapshot('old')))
            self.assertTrue(j.pending())
            with self.assertRaises(ValueError): close_window(j,'2026-09-26T00:00:00Z',pagination_complete=True,drafts_complete=True)
            j.db.close()
            j = Journal(path)
            a.fail_readback = False
            reconcile(a,j)
            self.assertFalse(j.pending())
            self.assertEqual(a.moves,1)
            close_window(j,'2026-09-26T00:00:00Z',pagination_complete=True,drafts_complete=True)
            j.db.close()

    def test_missing_journal_not_silently_initialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): Journal(Path(tmp)/'missing.db')

    def test_incomplete_pagination_blocks_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = Journal(Path(tmp)/'private.db',initialize=True)
            with self.assertRaises(ValueError): close_window(j,'2026-09-26T00:00:00Z',pagination_complete=False,drafts_complete=True)
            j.db.close()


if __name__ == '__main__': unittest.main()
