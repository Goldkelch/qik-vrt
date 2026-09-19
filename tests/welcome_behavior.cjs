// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const w=require('../welcome.js');
const text=fs.readFileSync(path.join(__dirname,'../WELCOME.md'),'utf8');
const data=w.parseDocument(text);
assert.equal(Object.keys(data.sections).length,14);
assert.equal(w.chooseLocale(['xx','fr-CA']),'fr');
assert.equal(w.chooseLocale(['pt_PT']),'pt-BR');
assert.equal(w.chooseLocale(['zh-Hans-SG']),'zh-CN');
assert.equal(w.chooseLocale(['zh-Hant-TW']),'en');
assert.equal(w.chooseLocale(['ar-SA']),'ar');
assert.equal(w.chooseLocale(['ja-JP']),'ja');
assert.throws(()=>w.safeURL('javascript:alert(1)'));
assert.throws(()=>w.safeURL('https://github.com@evil.example/a'));
assert.throws(()=>w.safeURL('https://user:secret@github.com/a'));
assert.throws(()=>w.parseDocument(text.replace('<!-- qikvrt-locale:ar -->','<!-- qikvrt-locale:en -->')));
assert.throws(()=>w.parseDocument(text.replace('[p1]: https:','[p1]: javascript:')));
for(const [code,section] of Object.entries(data.sections)) {
  const plain=w.plainText(section,data.refs),parts=w.splitText(plain);
  assert(parts.length>1);
  assert(parts.every(p=>Array.from(p).length<=3500));
  assert.equal(parts.join(' ').replace(/\s+/g,' '),plain.replace(/\s+/g,' '));
  assert.equal(new Set(plain.match(/https:\/\/[^)\s]+/g)).size,39,code);
  assert.equal(w.labels[code].length,12,code);
}
const emoji='🙂'.repeat(4000);assert(w.splitText(emoji).every(s=>!s.includes('\ufffd')));
console.log('WELCOME_BEHAVIOR_OK: 14 locales, 39 shared sources, bounded Unicode-safe exports, negative URL/locale controls.');
