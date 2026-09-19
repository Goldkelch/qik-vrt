/* Execute the production content script with a minimal DOM and message transport.
 * This tests the localization/authorization boundary, not Firefox installation. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..', 'browser/firefox/qikvrt-terminal');
const source = fs.readFileSync(path.join(root, 'content.js'), 'utf8');
const locales = fs.readdirSync(path.join(root, '_locales')).sort();

class Node {
  constructor(dataset = {}) {
    this.dataset = dataset;
    this.textContent = '';
    this.value = '';
    this.attributes = {};
    this.children = new Map();
    this.localized = [];
    this.labels = [];
    this.listeners = {};
    this.style = {setProperty() {}};
    this.classList = {toggle() {}};
  }
  set innerHTML(html) {
    this.template = html;
    for (const match of html.matchAll(/<[^>]+>/g)) {
      const attributes = Object.fromEntries([...match[0].matchAll(/([\w-]+)="([^"]*)"/g)].map(m => [m[1], m[2]]));
      const dataset = {};
      for (const [key, value] of Object.entries(attributes)) {
        if (key.startsWith('data-')) dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = value;
      }
      const node = new Node(dataset);
      node.disabled = /\sdisabled[\s>]/.test(match[0]);
      if (dataset.role) this.children.set(`[data-role=${dataset.role}]`, node);
      if (dataset.act) this.children.set(`[data-act=${dataset.act}]`, node);
      if (dataset.i18n) this.localized.push(node);
      if (dataset.i18nLabel) this.labels.push(node);
    }
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  querySelector(key) { assert(this.children.has(key), key); return this.children.get(key); }
  querySelectorAll(key) { return key === '[data-i18n]' ? this.localized : this.labels; }
  addEventListener(key, fn) { this.listeners[key] = fn; }
  closest() { return this; }
}

async function run(locale) {
  const catalog = JSON.parse(fs.readFileSync(path.join(root, '_locales', locale, 'messages.json')));
  const marker = '<img src=x onerror=forbidden()> & localized';
  const host = new Node();
  const calls = [];
  let prepareState = 'DONE'; // Even a translated or shortened success label is insufficient.
  const browser = {
    i18n: {getMessage(key, substitutions) {
      if (key === '@@ui_locale') return locale;
      if (key === '@@bidi_dir') return locale === 'ar' ? 'rtl' : 'ltr';
      if (key === 'subtitle') return marker;
      assert(catalog[key], `${locale}: missing ${key}`);
      return catalog[key].message.replace('$BYTES$', substitutions || '');
    }},
    storage: {local: {async get() { return {}; }}},
    runtime: {async sendMessage(message) {
      calls.push(structuredClone(message));
      if (message.kind === 'OBSERVE_AUTHORITY') return {ok: true};
      if (message.kind === 'PREPARE_EFFECT') return {effect_ack: {state: prepareState}};
      return {ordinary_release: false};
    }}
  };
  const document = {getElementById() { return null; }, createElement() { return host; }, body: {appendChild() {}}};
  vm.runInNewContext(source, {document, browser, location: {href: 'https://github.com/Goldkelch/qik-vrt/blob/main/AI'}, Date}, {filename: 'content.js'});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(host.lang, locale.replaceAll('_', '-'));
  assert.equal(host.dir, locale === 'ar' ? 'rtl' : 'ltr');
  assert(!host.template.includes(marker), 'translation must not become HTML');
  assert.equal(host.localized.find(n => n.dataset.i18n === 'subtitle').textContent, marker);
  assert.equal(host.querySelector('[data-act=prepare]').textContent, catalog.prepare.message);
  const click = action => host.listeners.click({target: host.querySelector(`[data-act=${action}]`)});
  const command = host.querySelector('[data-role=command]');
  command.value = 'Keep this exact input: العربية 日本語 <text>';
  await click('commit');
  assert.equal(calls.filter(c => c.kind === 'COMMIT_EFFECT').length, 0);
  for (const state of ['NACK', 'CONTINUE', 'ISOLATE', 'BLOCK', 'DONE', catalog.prepared.message]) {
    prepareState = state;
    await click('prepare');
    assert.equal(host.querySelector('[data-act=commit]').disabled, true);
    await click('commit');
    assert.equal(calls.filter(c => c.kind === 'COMMIT_EFFECT').length, 0);
  }
  prepareState = 'EFFECT_ACK_DONE';
  await click('prepare');
  assert.equal(host.querySelector('[data-act=commit]').disabled, false);
  const preparedRequest = calls.at(-1).payload;
  assert.equal(preparedRequest.schema, 'qikvrt_terminal_input_v1');
  assert.equal(preparedRequest.text, command.value);
  assert.equal(preparedRequest.audio, null);
  assert.equal(preparedRequest.video, null);
  assert.equal('locale' in preparedRequest, false);
  await click('commit');
  const committed = calls.find(c => c.kind === 'COMMIT_EFFECT');
  assert.deepEqual(committed.payload.request, preparedRequest);
  assert.equal(committed.payload.confirmed, true);
  assert.equal(calls.at(-1).kind, 'OBSERVE_AUTHORITY');
  await click('commit');
  assert.equal(calls.filter(c => c.kind === 'COMMIT_EFFECT').length, 1, 'a preparation is consumed once');

  const preferences = new Node();
  preferences.innerHTML = fs.readFileSync(path.join(root, 'options.html'), 'utf8');
  const fields = Object.fromEntries(['accent', 'fontScale', 'density', 'position', 'save', 'status'].map(id => [id, new Node()]));
  const original = {accent: '#123456', fontScale: 1.2, density: 'compact', position: 'left'};
  let written;
  browser.storage.local.get = async () => ({qikvrtTerminalPreferences: original});
  browser.storage.local.set = async value => { written = structuredClone(value); };
  const preferencesDocument = {
    documentElement: new Node(),
    getElementById(id) { assert(fields[id], id); return fields[id]; },
    querySelectorAll(selector) { return preferences.querySelectorAll(selector); }
  };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'options.js'), 'utf8'),
                    {document: preferencesDocument, browser}, {filename: 'options.js'});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(preferencesDocument.documentElement.dir, host.dir);
  assert.equal(fields.position.value, 'left');
  fields.save.listeners.click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(written, {qikvrtTerminalPreferences: original});
  assert.equal(fields.status.textContent, catalog.saved.message);
  assert.equal(calls.filter(c => c.kind === 'COMMIT_EFFECT').length, 1, 'preferences never execute effects');
}

(async () => {
  for (const locale of locales) await run(locale);
  process.stdout.write(`Localization and commit boundary verified for ${locales.length} locales\n`);
})().catch(error => { process.stderr.write(`${error.stack}\n`); process.exitCode = 1; });
