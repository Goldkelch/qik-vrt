# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Structural evidence only; these tests do not certify translation semantics."""
import hashlib
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('de','en','fr','es','pt-BR','it','tr','ru','ar','hi','id','ja','ko','zh-CN')

class WelcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / 'WELCOME.md').read_bytes()
        cls.text = cls.raw.decode('utf-8')
        cls.html = (ROOT / 'WELCOME.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'welcome.js').read_text(encoding='utf-8')
        cls.evidence = json.loads((ROOT / 'WELCOME_EVIDENCE.json').read_text(encoding='utf-8'))

    def test_exact_source_binding(self):
        digest = hashlib.sha256(self.raw).hexdigest()
        self.assertEqual(self.evidence['article_sha256'], digest)
        self.assertIn('data-source-sha256="' + digest + '"', self.html)
        self.assertIn('hash!==document.body.dataset.sourceSha256', self.js)

    def test_every_language_has_complete_prose_and_identical_references(self):
        content = self.text.split('<!-- qikvrt-sources -->')[0]
        matches = list(re.finditer(r'<!-- qikvrt-locale:([^ ]+) -->', content))
        self.assertEqual(tuple(m[1] for m in matches), LANGUAGES)
        for i, m in enumerate(matches):
            block = content[m.end():matches[i+1].start() if i+1<len(matches) else len(content)]
            block = re.sub(r'<a id="[^"]+"></a>', '', block).strip()
            title, body = block.split('\n', 1)
            self.assertTrue(title.startswith('## '))
            paragraphs = re.split(r'\n\s*\n', body.strip())
            self.assertEqual(len(paragraphs), 13, m[1])
            self.assertTrue(all(len(p)>80 for p in paragraphs), m[1])
            self.assertEqual(set(re.findall(r'\]\[([a-z]\d+)\]',body)),set(self.evidence['sources']),m[1])
            self.assertIn('WELCOME.md#' + m[1], self.html)

    def test_only_explicit_https_sources(self):
        definitions = re.findall(r'^\[([a-z]\d+)\]: (\S+)$',self.text,re.M)
        self.assertEqual(len(definitions),39)
        self.assertEqual(dict(definitions),{k:v['url'] for k,v in self.evidence['sources'].items()})
        for _, url in definitions:
            u=urlsplit(url)
            self.assertEqual(u.scheme,'https')
            self.assertIn(u.hostname,{'github.com','goldkelch.github.io','doi.org','zenodo.org','datatracker.ietf.org'})
            self.assertIsNone(u.username)
            self.assertIsNone(u.password)

    def test_pages_projections_are_byte_identical(self):
        for name in ('WELCOME.md','WELCOME_EVIDENCE.json','WELCOME.html','welcome.js'):
            self.assertEqual((ROOT/name).read_bytes(),(ROOT/'docs'/name).read_bytes(),name)
        self.assertEqual((ROOT/'WELCOME.html').read_bytes(),(ROOT/'docs'/'welcome.html').read_bytes())

    def test_reader_is_nonexecuting_and_does_not_send(self):
        for forbidden in ('innerHTML','eval(', 'new Function(', 'wa.me', 'api.whatsapp', 'localStorage', 'sendBeacon', 'WebSocket'):
            self.assertNotIn(forbidden,self.js)
        self.assertEqual(self.js.count('fetch('),1)
        self.assertIn("fetch('WELCOME.md'",self.js)
        self.assertIn("credentials:'omit'",self.js)
        self.assertIn("addEventListener('click',async()",self.js)
        self.assertIn("default-src 'none'",self.html)
        self.assertIn('hidden',self.html)

    def test_attribution_and_limits_are_explicit(self):
        self.assertEqual(self.evidence['attribution']['project_conception_and_responsibility'],'Ingolf Lohmann')
        self.assertFalse(self.evidence['attribution']['independent_human_linguistic_review'])
        self.assertTrue(self.evidence['distribution_subject']['prerelease'])
        self.assertFalse(self.evidence['distribution_subject']['fresh_boot_execution'])
        self.assertEqual(self.evidence['base_subject']['head'],'a86054139b49c13c5cd344753b248b46b5daf66f')
        self.assertEqual(len(self.evidence['bound_articles']),2)
        for item in self.evidence['bound_articles']:
            self.assertEqual(item['head'],'4ea0491a5484075215f17dbcd157a2a5f18ef633')
            self.assertRegex(item['sha256'],r'^[0-9a-f]{64}$')

if __name__ == '__main__':
    unittest.main()
