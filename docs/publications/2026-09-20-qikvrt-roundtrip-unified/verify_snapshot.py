# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Enforce the single-file, script-free, sub-10-MB reading contract."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent


class Snapshot(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.anchors = []
        self.styles = []
        self.in_style = False
        self.in_pre = False
        self.texts = []
        self.csp = None
        self.download = None
        self.errors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {'script', 'iframe', 'frame', 'object', 'embed', 'form', 'input', 'button', 'audio', 'video', 'source', 'base'}:
            self.errors.append('active or unsupported element: ' + tag)
        if any(name.startswith('on') for name in attrs):
            self.errors.append('event handler')
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for name in ('src', 'poster', 'srcset', 'background', 'ping', 'action'):
            if attrs.get(name) and not attrs[name].startswith('data:'):
                self.errors.append('network attribute: ' + name)
        if tag == 'link' and not (attrs.get('rel') == 'icon' and attrs.get('href', '').startswith('data:')):
            self.errors.append('external resource link')
        if tag == 'meta':
            equiv = attrs.get('http-equiv', '').lower()
            if equiv == 'refresh':
                self.errors.append('refresh')
            if equiv == 'content-security-policy':
                self.csp = attrs.get('content')
        if tag == 'a':
            href = attrs.get('href', '')
            if href.startswith('#'):
                self.anchors.append(href[1:])
            elif not href.startswith(('https://', 'data:text/html;charset=utf-8;base64,')):
                self.errors.append('unexpected navigation scheme')
            if 'download' in attrs:
                self.download = href
        if attrs.get('style'):
            self.styles.append(attrs['style'])
        if tag == 'style':
            self.in_style = True
        if tag == 'pre' and attrs.get('class') == 'original':
            self.in_pre = True
            self.texts.append('')

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False
        if tag == 'pre':
            self.in_pre = False

    def handle_data(self, text):
        if self.in_style:
            self.styles.append(text)
        if self.in_pre:
            self.texts[-1] += text


manifest = json.loads((ROOT/'embedded-source-manifest.json').read_text())
binding = json.loads((ROOT/'SNAPSHOT.json').read_text())['artifact']
raw = (ROOT/binding['file']).read_bytes()
assert len(raw) == binding['bytes'] < 10_000_000
assert hashlib.sha256(raw).hexdigest() == binding['sha256']
parsed = Snapshot()
parsed.feed(raw.decode('utf-8'))
assert not parsed.errors, parsed.errors
assert len(parsed.ids) == len(set(parsed.ids)), 'duplicate IDs'
assert set(parsed.anchors) <= set(parsed.ids), 'broken internal link'
for directive in ("default-src 'none'", "script-src 'none'", "connect-src 'none'", "frame-src 'none'"):
    assert directive in parsed.csp, directive
css = '\n'.join(parsed.styles)
assert not re.search(r'@import|@font-face|expression\s*\(', css, re.I)
for target in re.findall(r'url\((.*?)\)', css, re.I):
    assert target.strip(' \"\'').startswith(('#', 'data:')), 'CSS resource load'
assert len(parsed.texts) == len(manifest) == binding['embedded_originals']
for source, text in zip(manifest, parsed.texts):
    assert hashlib.sha256(text.encode()).hexdigest() == source['text_sha256'], source['key']
assert parsed.download == 'https://qikvrt-roundtrip.ingolf-lohmann.chatgpt.site/QIKVRT_Roundtrip.snapshot', 'canonical attachment navigation'
report = {'method': 'HTML parsing, CSS dependency inspection, exact embedded-text comparisons; no browser execution claimed', 'result': 'PASS', 'file': binding['file'], 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'embedded_texts': len(parsed.texts), 'scripts': 0, 'external_resource_dependencies': 0, 'internal_links': len(parsed.anchors)}
expected_report = ROOT/'VALIDATION.json'
if expected_report.exists():
    assert json.loads(expected_report.read_text()) == report, 'validation receipt drift'
print(json.dumps(report, ensure_ascii=False, indent=2))
