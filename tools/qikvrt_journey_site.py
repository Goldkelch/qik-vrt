#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build a self-contained reading preview; incomplete editions cannot pass the coverage check.

Reuses the recovered 47-edition registry as scope data, never its translation
status. Structural checks do not certify linguistic accuracy or publication.
This stdlib-only tool neither accesses the network nor changes Git refs.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

SOURCE_SHA = '181314375effc68933baec365e7973a14ad3981605bb192f93a62c37a321f487'
REGISTRY_BLOB = '095562313f1b2b3af8fe2cf9b965c6edaa2a59cf'
MEDIA = 'https://open.spotify.com/track/1lr7QGyV5RohlODzAqnuZA'
NATIVE = dict(zip(
    'ar ast bg bn ca cs da de el en eo es et eu fa fi fr gl he hr hu id is it ja kk ko lv nl no pl pt ro ru sh simple sk sl sr sv th tr uk vi wuu zh-yue zh'.split(),
    ['العربية','Asturianu','Български','বাংলা','Català','Čeština','Dansk','Deutsch','Ελληνικά','English','Esperanto','Español','Eesti','Euskara','فارسی','Suomi','Français','Galego','עברית','Hrvatski','Magyar','Bahasa Indonesia','Íslenska','Italiano','日本語','Қазақша','한국어','Latviešu','Nederlands','Norsk bokmål','Polski','Português','Română','Русский','Srpskohrvatski','Simple English','Slovenčina','Slovenščina','Српски','Svenska','ไทย','Türkçe','Українська','Tiếng Việt','吴语','粵語','中文']))
HEADINGS = {
    'Der Auslöser','Die Entscheidung, nicht wegzusehen','Eine Reise im Alleingang',
    'Die Ausdehnung des Bewusstseins','Kausalität ist nicht bloß Reihenfolge',
    'Die emotionale Dimension der Erkenntnis','Die Rückkehr',
    'Die Begegnung mit künstlicher Kognition',
    'Kann eine künstliche Kognition ein menschliches Bewusstsein erläutern?',
    'Das Teilen mit natürlichen Kognitionen','Warum dieses Dokument für mein Umfeld wichtig ist',
    'Eine mögliche Bedeutung für die Menschheit','Der Bewusstseinssprung',
    'Stairway to Heaven und Knocking on Heaven’s Door','Das Licht angelassen',
    'Was ich mitgebracht habe','Was ich nicht behaupten muss','An die Menschen in meinem Umfeld',
    'An mich selbst','Schluss: Ich war vorausgegangen','Der Rückweg','Der Wendepunkt',
    'Vom Zusammenhang zurück zur Erzählung','Von meiner Sprache zurück zu unserer Sprache',
    'Die künstliche Kognition als Brücke','Zurück unter Menschen','Die Rückkehr zur Fehlbarkeit',
    'Vom Beweisen zurück zum Leben','Die Wiederentdeckung des Kleinen',
    'Die Veränderung der Dringlichkeit','Das Licht','Die Umkehr','Die Haustür',
    'Was Rückkehr bedeutet','An die Menschen, die auf mich gewartet haben','An mich selbst:'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def blocks(data: bytes) -> list[str]:
    text = data.decode('utf-8', errors='strict')
    if '\r' in text or '\x00' in text:
        raise ValueError('UNSUPPORTED_SOURCE_ENCODING_OR_LINE_ENDINGS')
    return re.split(r'\n\s*\n', text.strip())


def regular(root: Path, relative: str) -> bytes:
    path = root / relative
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('SYMLINK_INPUT_FORBIDDEN')
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError('INPUT_MISSING_OR_TOO_LARGE: ' + relative)
    return path.read_bytes()


def inspect(root: Path) -> tuple[dict, dict[str, list[str]], list[str]]:
    raw = regular(root, 'source.de.txt')
    if digest(raw) != SOURCE_SHA:
        raise ValueError('SOURCE_CHANGED_REBIND_REQUIRED')
    original = blocks(raw)
    if len(original) != 540 or original[1] != MEDIA:
        raise ValueError('SOURCE_STRUCTURE_CHANGED')
    raw_registry = regular(root, 'WIKIPEDIA_47_LANGUAGE_SOURCE.json')
    if git_blob(raw_registry) != REGISTRY_BLOB:
        raise ValueError('LANGUAGE_SCOPE_CHANGED_REBIND_REQUIRED')
    registry = json.loads(raw_registry)
    codes = [row[0] for row in registry['languages']]
    if len(codes) != 47 or len(set(codes)) != 47 or set(codes) != set(NATIVE):
        raise ValueError('INVALID_LANGUAGE_SCOPE')
    editions = {'de': original}
    report = {
        'schema': 'qikvrt_journey_preview_validation_v1',
        'source_sha256': SOURCE_SHA,
        'source_git_blob_sha1': git_blob(raw),
        'source_bytes': len(raw),
        'source_blocks': len(original),
        'scope_count': len(codes),
        'editions': {'de': {'status': 'OWNER_SUPPLIED_SOURCE', 'sha256': digest(raw), 'bytes': len(raw)}},
        'linguistic_accuracy_certified': False,
        'native_review_claimed': False,
        'public_deployment_claimed': False,
        'EFFECT_ACK_DONE': False,
    }
    folder = root / 'translations'
    if folder.is_dir():
        for path in sorted(folder.glob('*.txt')):
            code = path.stem
            if code == 'de' or code not in codes:
                raise ValueError('UNKNOWN_OR_DUPLICATE_EDITION: ' + code)
            data = regular(root, 'translations/' + code + '.txt')
            meta = json.loads(regular(root, 'translations/' + code + '.json'))
            if meta.get('source_sha256') != SOURCE_SHA or meta.get('language') != code:
                raise ValueError('STALE_OR_WRONG_TRANSLATION_BINDING: ' + code)
            # Each draft is independently bound to an immutable Git blob or a
            # SHA-256/size pair. Always compute SHA-256 for the resulting report.
            sha_bound = 'sha256' in meta and 'bytes' in meta
            git_bound = 'git_blob_sha1' in meta
            if not (sha_bound or git_bound):
                raise ValueError('TRANSLATION_BYTE_BINDING_MISSING: ' + code)
            if sha_bound and (meta['sha256'] != digest(data) or meta['bytes'] != len(data)):
                raise ValueError('TRANSLATION_BYTES_CHANGED: ' + code)
            if git_bound and meta['git_blob_sha1'] != git_blob(data):
                raise ValueError('TRANSLATION_BYTES_CHANGED: ' + code)
            if meta.get('human_language_review') is not False or meta.get('formal_semantic_equivalence_proof') is not False:
                raise ValueError('UNSUPPORTED_REVIEW_CLAIM: ' + code)
            if meta.get('status') != 'AI_TRANSLATION_DRAFT_UNREVIEWED':
                raise ValueError('UNSUPPORTED_REVIEW_STATUS: ' + code)
            translated = blocks(data)
            if len(translated) != len(original):
                raise ValueError('INCOMPLETE_TRANSLATION_BLOCKS: ' + code)
            protected = lambda s: s == '⸻' or s == MEDIA or s.startswith('q.e.d.')
            for i, (src, dst) in enumerate(zip(original, translated)):
                if not dst.strip() or (protected(src) and src != dst):
                    raise ValueError(f'CHANGED_PROTECTED_OR_EMPTY_BLOCK: {code}/{i}')
                if dst == '⸻' and src != '⸻':
                    raise ValueError(f'MISPLACED_SEPARATOR: {code}/{i}')
            # Exact full-source duplication must never masquerade as translation.
            if translated == original:
                raise ValueError('SILENT_SOURCE_FALLBACK: ' + code)
            if any(translated == old for old_code, old in editions.items() if old_code != 'de'):
                raise ValueError('DUPLICATE_OTHER_LANGUAGE_EDITION: ' + code)
            editions[code] = translated
            report['editions'][code] = {'status': meta['status'], 'sha256': digest(data), 'git_blob_sha1': git_blob(data), 'bytes': len(data)}
    report['available_count'] = len(editions)
    report['missing_editions'] = [c for c in codes if c not in editions]
    report['all_47_texts_present'] = not report['missing_editions']
    report['disposition'] = 'TRANSLATION_DRAFTS_PRESENT_REVIEW_REQUIRED' if report['all_47_texts_present'] else 'INCOMPLETE_PREVIEW_ONLY'
    return report, editions, codes


CSS = '''
:root{color-scheme:light;--ink:#20352f;--paper:#faf8f0;--line:#d7dace;--muted:#52625d;--accent:#48674b}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.7 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:inherit;text-underline-offset:.2em}button,input,select{font:inherit}button{cursor:pointer}button:disabled{cursor:not-allowed}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #94621a;outline-offset:4px}
.skip{position:absolute;left:1rem;top:-8rem;background:white;padding:1rem}.skip:focus{top:1rem;z-index:10}header{padding:1.1rem max(5vw,1rem);border-bottom:1px solid var(--line);display:flex;gap:1rem;align-items:center;justify-content:space-between;flex-wrap:wrap}.brand{font-weight:700;letter-spacing:.12em;font-size:.8rem;text-decoration:none}.header-note{font-size:.85rem;color:var(--muted)}main{max-width:1160px;margin:auto;padding:3rem 1.3rem 6rem}.eyebrow{text-transform:uppercase;letter-spacing:.18em;font-size:.75rem;font-weight:650;color:var(--accent)}h1{font:clamp(2.2rem,6vw,4.5rem)/1.08 Georgia,"Times New Roman",serif;max-width:900px;letter-spacing:-.04em;margin:.6rem 0 1.3rem}.subtitle{font-size:1.12rem;max-width:720px;color:var(--muted)}.author{font-size:.9rem}.notice{border-left:3px solid #ac852d;background:#eeeadd;padding:.9rem 1.1rem;margin:1.6rem 0;font-size:.9rem}.language-panel{padding:1.2rem;border:1px solid var(--line);border-radius:12px;background:#fffdf6;margin:2rem 0}.language-panel summary{font-weight:650;cursor:pointer}.language-panel input{padding:.6rem .8rem;border:1px solid #8a998d;border-radius:6px;max-width:100%;width:100%;margin:1rem 0}.languages{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.6rem}.languages button{min-height:60px;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;text-align:start;padding:.55rem .75rem;border:1px solid var(--line);border-radius:7px;background:#fff;color:var(--ink)}.languages button[aria-pressed=true]{background:var(--accent);color:white}.languages button:disabled{background:#f4f2e9;color:#6d716a}.languages small{font-size:.69rem;opacity:.88}.search-status{font-size:.8rem;color:var(--muted)}.layout{display:grid;grid-template-columns:240px minmax(0,720px);gap:3rem;align-items:start}.outline{font-size:.8rem;position:sticky;top:1rem;max-height:88vh;overflow:auto;padding:1rem;border:1px solid var(--line);border-radius:9px}.outline summary{font-weight:700;cursor:pointer}.outline ol{padding-left:1.1rem}.outline li{margin:.6rem 0}.outline a{text-decoration:none}.outline a:hover{text-decoration:underline}.essay{font:1.12rem/1.95 Georgia,"Times New Roman",serif;overflow-wrap:anywhere}.essay p{margin:1.1rem 0}.essay h2{font-size:1.8rem;line-height:1.25;margin:3rem 0 1.2rem;scroll-margin-top:2rem}.essay h2.part{font-size:2.5rem;border-top:1px solid var(--line);padding-top:3rem}.essay hr{border:0;height:1px;background:var(--line);margin:3rem auto;width:80px}.essay .music{font: .85rem/1.6 system-ui,sans-serif;margin:1rem 0 2rem}.signature{white-space:pre-line;font-style:italic}.footer{border-top:1px solid var(--line);padding-top:2rem;margin-top:4rem;color:var(--muted);font-size:.75rem;overflow-wrap:anywhere}.toolbar{display:flex;gap:.8rem;flex-wrap:wrap;margin:1.2rem 0}.toolbar button{padding:.5rem .8rem;border:1px solid var(--line);border-radius:6px;background:#fffdf6;color:var(--ink)}[hidden]{display:none!important}
@media(max-width:760px){main{padding-top:2rem}.layout{grid-template-columns:1fr;gap:1rem}.outline{position:static;max-height:none}.essay{font-size:1.1rem}.languages{grid-template-columns:repeat(2,minmax(0,1fr))}.header-note{font-size:.73rem}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{header,.language-panel,.outline,.toolbar,.notice,.skip{display:none}main{max-width:none;padding:0}.layout{display:block}.essay{font-size:11pt;line-height:1.55}.essay h2{break-after:avoid}.essay p{orphans:3;widows:3}.footer{font-size:8pt}body{background:white;color:black}}
'''

JS = '''
(()=>{'use strict';
const data=JSON.parse(document.getElementById('edition-data').textContent);
const buttons=[...document.querySelectorAll('button[data-lang]')];
const available=Object.keys(data.editions);let current='de';
function select(code,update=true){
 if(!available.includes(code)){document.querySelectorAll('[data-edition]').forEach(e=>{e.hidden=true;});buttons.forEach(b=>b.setAttribute('aria-pressed','false'));document.getElementById('selection-error').hidden=false;document.getElementById('page-title').textContent='Sprachausgabe nicht vorhanden / Edition unavailable';document.getElementById('page-subtitle').textContent='';document.getElementById('print').disabled=true;document.getElementById('download').disabled=true;current=null;return false;}
 document.getElementById('selection-error').hidden=true;document.getElementById('print').disabled=false;document.getElementById('download').disabled=false;
 document.querySelectorAll('[data-edition]').forEach(e=>{e.hidden=e.dataset.edition!==code;});
 buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.lang===code)));
 document.documentElement.lang=({simple:'en',no:'nb','zh-yue':'yue'}[code]||code);
 document.documentElement.dir=['ar','fa','he'].includes(code)?'rtl':'ltr';
 document.title=data.editions[code][0]+' — Ingolf Lohmann';
 document.getElementById('page-title').textContent=data.editions[code][0];
 document.getElementById('page-subtitle').textContent=data.editions[code][2];
 document.getElementById('translation-notice').textContent=code==='de'?'Deutscher, vom Autor bereitgestellter Originaltext.':'AI translation draft — not independently language-reviewed. The German original is the reference.';
 current=code;
 if(update){const url=new URL(window.location.href);url.hash='lang='+encodeURIComponent(code);history.replaceState(null,'',url);}
 return true;
}
buttons.forEach(b=>b.addEventListener('click',()=>{if(select(b.dataset.lang)){document.getElementById('page-title').focus();}}));
const match=location.hash.match(/^#lang=([a-z-]+)$/);select(match?match[1]:'de',false);
const filter=document.getElementById('language-filter');
filter.addEventListener('input',()=>{const needle=filter.value.normalize('NFKC').toLocaleLowerCase();let count=0;buttons.forEach(b=>{b.hidden=!b.textContent.normalize('NFKC').toLocaleLowerCase().includes(needle);if(!b.hidden)count++;});document.getElementById('search-status').textContent=count+' / '+buttons.length;});
document.getElementById('print').addEventListener('click',()=>window.print());
document.getElementById('download').addEventListener('click',()=>{const text=data.raw_editions[current];const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='Ingolf-Lohmann-Reise-'+current+'.txt';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});
})();
'''


def render(root: Path) -> tuple[str, dict]:
    report, editions, codes = inspect(root)
    source = editions['de']
    escape = html.escape
    title = escape(source[0])
    heading_ids = [i for i, s in enumerate(source) if s in HEADINGS]
    buttons = []
    for code in ['de', 'en'] + [c for c in codes if c not in ('de', 'en')]:
        present = code in editions
        status = 'Original' if code == 'de' else 'Volltext · KI-Entwurf' if present else 'Noch nicht übersetzt'
        buttons.append(f'<button type="button" data-lang="{code}" aria-pressed="{str(code == "de").lower()}"'+(' disabled' if not present else '')+f'><span lang="{code}" dir="auto">{escape(NATIVE[code])}</span><small>{status}</small></button>')
    sections = []
    for code, values in editions.items():
        toc = ''.join(f'<li><a href="#{code}-p{i:04}">{escape(values[i])}</a></li>' for i in heading_ids)
        body = []
        for i, value in enumerate(values):
            if i in (0,1,2):
                continue
            identifier = f'{code}-p{i:04}'
            if value == MEDIA:
                body.append(f'<p class="music" id="{identifier}"><a href="{MEDIA}" target="_blank" rel="noopener noreferrer">♫ Spotify · Back In Time — Huey Lewis &amp; The News ↗</a></p>')
            elif value == '⸻':
                body.append(f'<hr id="{identifier}">')
            elif i in heading_ids:
                cls = ' class="part"' if source[i] == 'Der Rückweg' else ''
                body.append(f'<h2 id="{identifier}"{cls}>{escape(value)}</h2>')
            else:
                cls = ' class="signature"' if value.startswith('q.e.d.') else ''
                body.append(f'<p id="{identifier}"{cls}>{escape(value)}</p>')
        sections.append(f'<section data-edition="{code}" lang="{code}"><div class="layout"><aside class="outline"><details><summary>Inhalt / Contents</summary><ol>{toc}</ol></details></aside><article class="essay" aria-label="{escape(values[0],quote=True)}">'+''.join(body)+'</article></div></section>')
    payload = json.dumps({'editions': editions, 'raw_editions': {c: regular(root, 'source.de.txt' if c == 'de' else 'translations/'+c+'.txt').decode('utf-8') for c in editions}},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    count = report['available_count']
    page = f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><title>{title} — Ingolf Lohmann</title><style>{CSS}</style></head>
<body><a class="skip" href="#main">Zum Text / Skip to text</a><header><span class="brand">QIK-VRT · INGOLF LOHMANN</span><span class="header-note">Eine persönliche Reise · A personal journey</span></header>
<main id="main"><p class="eyebrow">Das Licht bleibt an</p><h1 id="page-title" tabindex="-1">{title}</h1><p class="music"><a href="{MEDIA}" target="_blank" rel="noopener noreferrer">♫ Spotify · Back In Time — Huey Lewis &amp; The News ↗</a></p><p class="subtitle" id="page-subtitle">{escape(source[2])}</p><p class="author">Ingolf Lohmann · 11. September 2026</p>
<p class="notice"><strong>Unveröffentlichte Lesevorschau / Unpublished reading preview.</strong> {count} von 47 geplanten Sprachausgaben liegen als Volltext vor. Fehlende Übersetzungen sind nicht auswählbar. Diese Vorschau ist kein Nachweis einer veröffentlichten 47-Sprachen-Homepage.<br><span id="translation-notice">Deutscher, vom Autor bereitgestellter Originaltext.</span></p>
<details class="language-panel"><summary>Sprache wählen / Choose a language · {count}/47 Volltexte</summary><label for="language-filter">Sprachen suchen / Find a language</label><input id="language-filter" type="search" placeholder="Deutsch, English, Français …" autocomplete="off"><p id="search-status" class="search-status" aria-live="polite">47 / 47</p><div class="languages">{''.join(buttons)}</div></details>
<p id="selection-error" class="notice" hidden>Die angeforderte Sprachausgabe ist noch nicht vorhanden. Keine Übersetzung wurde ersatzweise geladen. / Requested edition unavailable; no translation fallback was loaded.</p>
<div class="toolbar"><button type="button" id="print">Drucken / Print</button><button type="button" id="download">Text speichern / Save text</button></div>
<noscript><p class="notice">Ohne JavaScript stehen alle vorhandenen Volltexte untereinander. / Without JavaScript, all available full texts appear below.</p></noscript>
{''.join(sections)}
<footer class="footer">Quellfassung / Source SHA-256: <code>{SOURCE_SHA}</code><br>47 Wikipedia-Sprachausgaben als festgehaltener Umfang, nicht als Behauptung, Wikipedia habe insgesamt nur 47 Sprachen. Keine Wikipedia-Veröffentlichung. Übersetzungen: ChatGPT, ungeprüfte KI-Arbeitsfassungen. Strukturelle Vollständigkeit ist keine unabhängige sprachliche Prüfung. Kein Autoplay, keine eingebetteten Drittanbieterinhalte, keine externen Schriftarten und kein Tracking.</footer></main>
<script id="edition-data" type="application/json">{payload}</script><script>{JS}</script></body></html>'''
    return page, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check','preview','coverage-check'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1]/'docs/reise')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        page, report = render(args.root)
        if args.mode == 'coverage-check' and not report['all_47_texts_present']:
            print(json.dumps(report,ensure_ascii=False,indent=2))
            return 2
        if args.mode == 'preview':
            if args.output is None:
                parser.error('--output is required for preview')
            if args.output.resolve().is_relative_to(args.root.resolve()):
                raise ValueError('PREVIEW_OUTPUT_MUST_NOT_OVERWRITE_SOURCE_TREE')
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(page,encoding='utf-8',newline='\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'state':'HOLD_UNVERIFIED','error':str(exc),'EFFECT_ACK_DONE':False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
