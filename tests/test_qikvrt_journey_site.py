# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Structural/negative tests; no linguistic-equivalence or release claim."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('journey', ROOT/'tools/qikvrt_journey_site.py')
assert spec and spec.loader
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)

class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'reise'
        # These negative fixtures intentionally contain only DE and EN, even
        # after all other editions have been added to the repository.
        self.root.mkdir()
        (self.root/'translations').mkdir()
        for relative in ('source.de.txt','WIKIPEDIA_47_LANGUAGE_SOURCE.json',
                         'translations/en.txt','translations/en.json'):
            shutil.copyfile(ROOT/'docs/reise'/relative,self.root/relative)

    def write_meta(self, code='en', **changes):
        path = self.root/f'translations/{code}.json'
        meta = json.loads(path.read_text())
        meta.update(changes)
        path.write_text(json.dumps(meta))

    def test_exact_new_source(self):
        raw=(self.root/'source.de.txt').read_bytes()
        self.assertEqual(len(raw),39745)
        self.assertEqual(site.digest(raw),site.SOURCE_SHA)
        self.assertEqual(site.git_blob(raw),'45c1f23cdf842ef5d92bfbef1d17da536b47f069')
        old=raw.replace(('\n\n\n'+site.MEDIA+'\n\n\n').encode(),b'\n\n',1)
        self.assertEqual(site.git_blob(old),'e1311a33d368559959633ba147e8d97d7bbd60f1')

    def test_source_change_fails_closed(self):
        p=self.root/'source.de.txt';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'SOURCE_CHANGED'):site.inspect(self.root)

    def test_scope_is_exact_47_and_old_translation_states_are_not_used(self):
        report,editions,codes=site.inspect(self.root)
        self.assertEqual(len(codes),47)
        self.assertEqual(report['editions']['de']['status'],'OWNER_SUPPLIED_SOURCE')
        self.assertEqual(report['editions']['en']['status'],'AI_TRANSLATION_DRAFT_UNREVIEWED')

    def test_all_blocks_aligned(self):
        report,editions,codes=site.inspect(self.root)
        self.assertEqual(len(editions['de']),540)
        self.assertEqual(len(editions['en']),540)
        self.assertEqual([i for i,v in enumerate(editions['de']) if v=='⸻'],[i for i,v in enumerate(editions['en']) if v=='⸻'])
        self.assertEqual(editions['en'][1],site.MEDIA)
        self.assertEqual(editions['en'][-1],'q.e.d.\nIngolf Lohmann')

    def test_missing_translations_are_explicit(self):
        report,editions,codes=site.inspect(self.root)
        self.assertEqual(report['available_count'],2)
        self.assertEqual(len(report['missing_editions']),45)
        self.assertFalse(report['all_47_texts_present'])
        self.assertFalse(report['public_deployment_claimed'])
        self.assertFalse(report['EFFECT_ACK_DONE'])

    def test_shortened_translation_fails(self):
        p=self.root/'translations/en.txt';data=p.read_bytes().split(b'\n\n',1)[1];p.write_bytes(data)
        self.write_meta(bytes=len(data),sha256=site.digest(data))
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_TRANSLATION'):site.inspect(self.root)

    def test_changed_translation_digest_fails(self):
        p=self.root/'translations/en.txt';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'TRANSLATION_BYTES_CHANGED'):site.inspect(self.root)

    def test_stale_source_binding_fails(self):
        self.write_meta(source_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'STALE_OR_WRONG'):site.inspect(self.root)

    def test_source_fallback_is_rejected(self):
        data=(self.root/'source.de.txt').read_bytes();(self.root/'translations/en.txt').write_bytes(data)
        self.write_meta(bytes=len(data),sha256=site.digest(data))
        with self.assertRaisesRegex(ValueError,'SILENT_SOURCE_FALLBACK'):site.inspect(self.root)

    def test_changed_media_rejected_even_with_updated_digest(self):
        p=self.root/'translations/en.txt';data=p.read_bytes().replace(site.MEDIA.encode(),b'https://example.com/other');p.write_bytes(data)
        self.write_meta(bytes=len(data),sha256=site.digest(data))
        with self.assertRaisesRegex(ValueError,'CHANGED_PROTECTED'):site.inspect(self.root)

    def test_git_blob_binding_without_manual_sha256_is_verified(self):
        path=self.root/'translations/en.json'
        meta=json.loads(path.read_text())
        meta.pop('sha256');meta.pop('bytes')
        meta['git_blob_sha1']=site.git_blob((self.root/'translations/en.txt').read_bytes())
        path.write_text(json.dumps(meta))
        report,_,_=site.inspect(self.root)
        self.assertEqual(report['editions']['en']['sha256'],'c30c77e779712ad6cffc2874728f3154193311ee60a356a8b5bea09fb19a08b9')
        meta['git_blob_sha1']='0'*40;path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError,'TRANSLATION_BYTES_CHANGED'):site.inspect(self.root)

    def test_false_human_review_claim_is_rejected(self):
        self.write_meta(human_language_review=True)
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_REVIEW_CLAIM'):site.inspect(self.root)

    def test_duplicate_language_cannot_fill_an_empty_slot(self):
        data=(self.root/'translations/en.txt').read_bytes()
        (self.root/'translations/fr.txt').write_bytes(data)
        meta=json.loads((self.root/'translations/en.json').read_text())
        meta['language']='fr'
        (self.root/'translations/fr.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OTHER_LANGUAGE_EDITION'):site.inspect(self.root)

    def test_silent_review_upgrade_fails(self):
        self.write_meta(status='HUMAN_REVIEWED')
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_REVIEW_STATUS'):site.inspect(self.root)

    def test_no_hidden_network_or_media_embedding(self):
        page,report=site.render(self.root)
        self.assertNotIn('<iframe',page)
        self.assertNotIn('<audio',page)
        self.assertNotIn('autoplay',page)
        self.assertNotIn('fetch(',page)
        self.assertNotIn('<script src=',page)
        self.assertNotIn('<link rel="stylesheet"',page)
        self.assertIn('rel="noopener noreferrer"',page)

    def test_media_is_between_title_and_subtitle(self):
        page,report=site.render(self.root)
        start=page.index('<h1 id="page-title"')
        self.assertLess(page.index('href="'+site.MEDIA+'"',start),page.index('id="page-subtitle"',start))

    def test_unknown_language_does_not_fallback(self):
        page,report=site.render(self.root)
        self.assertIn("current=null;return false;",page)
        self.assertIn("e.hidden=true",page)
        self.assertIn('data-lang="fr" aria-pressed="false" disabled',page)

    def test_symlink_source_is_rejected(self):
        p=self.root/'source.de.txt';other=self.root/'other.txt';p.rename(other);p.symlink_to(other)
        with self.assertRaisesRegex(ValueError,'SYMLINK'):site.inspect(self.root)

if __name__=='__main__':unittest.main()
