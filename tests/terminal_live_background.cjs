// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Executes the real extension background script with explicit browser API doubles.
// Not a Firefox runtime / production receipt.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('browser/firefox/qikvrt-terminal/background.js', 'utf8');
const wire = fs.readFileSync('tools/qikvrt_live_sse.py', 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));
const event = n => ({schema:'qikvrt_live_event_v1',event_id:`fixture-${n}`,
  observed_at:'2026-09-15T00:00:00Z',repository:'Goldkelch/qik-vrt',
  subject:{kind:'test_fixture',head_sha:'a'.repeat(40)},phase:'P2',verb:'READBACK',
  causal_state:'REOBSERVE',source:{type:'test_fixture',id:String(n)},
  productive_effect:false,effect_ack:'NOT_REQUIRED',payload:{message:`fixture ${n}`}});
async function harness() {
  const stored = {}; const sources = []; let fetches = 0; let failNext = false;
  class EventSource {
    constructor(url) { this.url=url; this.listeners={}; sources.push(this); }
    addEventListener(name, fn) { this.listeners[name]=fn; }
    emit(name, item, id=item.event_id) {
      if (this.listeners[name]) this.listeners[name]({data:JSON.stringify(item),lastEventId:id});
    }
    close() { this.closed=true; }
  }
  const hook = {addListener() {}};
  const browser = {runtime:{onInstalled:hook,onStartup:hook,onMessage:hook},storage:{local:{
    async get() { return JSON.parse(JSON.stringify(stored)); },
    async set(values) { if(failNext) { failNext=false; throw Error('fixture storage failure'); }
      Object.assign(stored,JSON.parse(JSON.stringify(values))); }
  }}};
  const context = vm.createContext({browser,EventSource,URL,console,TextEncoder,
    fetch:async() => {fetches++; return {ok:false,status:503};}});
  vm.runInContext(source,context);
  await settle(); await settle();
  return {stored,sources,context,failStore:()=>{failNext=true;},fetches:()=>fetches};
}
async function contentHarness() {
  class Element {
    constructor(tag) { this.tagName=tag; this.children=[]; this.dataset={}; this.attributes={}; this.style={setProperty(){}}; this.listeners={}; this.disabled=false; this.scrollHeight=0; this.scrollTop=0; this.clientHeight=0; this.classList={toggle(){}}; this._text=''; }
    setAttribute(k,v) { this.attributes[k]=String(v); if(k==='id') this.id=v; }
    appendChild(node) { node.parentNode=this; this.children.push(node); return node; }
    append(...nodes) { for(const node of nodes) this.appendChild(node); }
    insertBefore(node,old) { node.parentNode=this; this.children.splice(this.children.indexOf(old),0,node); }
    removeChild(node) { this.children.splice(this.children.indexOf(node),1); node.parentNode=null; }
    get firstElementChild() { return this.children[0]; }
    get firstChild() { return this.children[0]; }
    get childElementCount() { return this.children.length; }
    set textContent(value) { this._text=String(value); this.children=[]; }
    get textContent() { return this._text+this.children.map(x=>x.textContent).join(''); }
    set innerHTML(text) { // Only the existing static bootstrap template is parsed by this double.
      for(const match of text.matchAll(/<([a-z]+)[^>]*data-(role|act)="([^"]+)"[^>]*>/g)) {
        const node=new Element(match[1]); node.attributes['data-'+match[2]]=match[3];
        if(match[0].includes('disabled')) node.disabled=true;
        this.appendChild(node);
      }
    }
    addEventListener(name,fn) { this.listeners[name]=fn; }
    querySelector(selector) {
      const match=selector.match(/^\[([^=]+)=["']?([^\]"']+)["']?\]$/);
      const predicate=match ? n=>n.attributes[match[1]]===match[2] : n=>selector==='#'+n.id;
      const visit=node=>{if(predicate(node))return node; for(const item of node.children){const found=visit(item);if(found)return found;}return null;};
      return visit(this);
    }
  }
  const body=new Element('body');
  const document={body,createElement:tag=>new Element(tag),getElementById:id=>body.querySelector('#'+id)};
  const stored={}; const listeners=[]; let sends=0;
  const browser={runtime:{sendMessage:async()=>{sends++;return {ok:false,reason:'fixture baseline',ordinary_release:false};}},storage:{
    onChanged:{addListener:fn=>listeners.push(fn)},local:{get:async()=>JSON.parse(JSON.stringify(stored))}}};
  const context=vm.createContext({browser,document,console,location:{href:'https://example.invalid/fixture'}});
  vm.runInContext(fs.readFileSync('browser/firefox/qikvrt-terminal/content.js','utf8'),context);
  await settle(); await settle();
  assert.equal(listeners.length,1,'content script has no push listener');
  const host=document.getElementById('qikvrt-ai-terminal-host');
  const journal=host.querySelector('[data-role=live-events]');
  assert.ok(journal,'visible receipt journal missing');
  const calls=sends;
  const push=(records,state='EVENT')=>{for(const listener of listeners) listener({qikvrtLiveEvents:{newValue:records},qikvrtLiveEventState:{newValue:state}},'local');};
  const first=event(1); first.payload.message='<img src=x onerror=alert(1)>';
  push([first]); const original=journal.firstChild;
  push([first,event(2),event(3)]);
  assert.equal(journal.childElementCount,3,'three events must produce three visible appends');
  assert.equal(journal.firstChild,original,'existing DOM receipt must not be replaced');
  assert.equal(sends,calls,'visible append must not send a prompt or GitHub query');
  assert.ok(journal.textContent.includes(first.payload.message),'receipt raw data must remain inspectable');
  assert.ok(journal.textContent.includes('a'.repeat(40)),'full source head must remain inspectable');
  push([first,event(2),event(3)]);
  assert.equal(journal.childElementCount,3,'replayed window must not duplicate appends');
  push([first,event(2),event(3)],'RECONNECTING');
  assert.ok(host.querySelector('[data-role=live-state]').textContent.includes('unterbrochen'));
  assert.equal(host.querySelector('[data-act=commit]').disabled,true,'monitor cannot authorize Commit');
  console.log('CONTENT_APPEND_TESTS=PASS (append/order/dedup/raw/text-only/stale/no-effect)');
}

(async () => {
  assert.match(wire,/event: qikvrt\\n/,'test must consume the actual relay event name');
  const h=await harness();
  assert.equal(h.sources.length,1);
  const calls=h.fetches();
  assert.ok(h.sources[0].listeners.qikvrt,'relay qikvrt event has no Firefox consumer');
  for (const n of [1,2,3]) h.sources[0].emit('qikvrt',event(n));
  await settle(); await settle();
  assert.deepEqual(h.stored.qikvrtLiveEvents,[event(1),event(2),event(3)]);
  assert.equal(h.stored.qikvrtLastEventId,'fixture-3');
  assert.equal(h.fetches(),calls,'incoming receipt was replaced by GitHub re-fetch');
  h.sources[0].emit('qikvrt',event(3)); await settle();
  assert.equal(h.stored.qikvrtLiveEvents.length,3,'duplicate delivery appended twice');
  h.sources[0].emit('qikvrt',event(4),'wrong-id'); await settle();
  assert.equal(h.stored.qikvrtLastEventId,'fixture-3');
  assert.equal(h.stored.qikvrtLiveEventState,'HOLD');
  h.sources[0].emit('qikvrt',{...event(4),repository:'foreign/repo'}); await settle();
  assert.equal(h.stored.qikvrtLastEventId,'fixture-3');
  const collision=event(3); collision.payload={tampered:true};
  h.sources[0].emit('qikvrt',collision); await settle();
  assert.equal(h.stored.qikvrtLiveEventState,'HOLD');
  assert.deepEqual(h.stored.qikvrtLiveEvents[2],event(3));
  const fresh=await harness();
  fresh.failStore(); fresh.sources[0].emit('qikvrt',event(1)); await settle(); await settle();
  assert.equal(fresh.stored.qikvrtLastEventId,undefined,'cursor acknowledged failed persistence');
  fresh.sources[0].emit('qikvrt',event(2)); await settle(); await settle();
  assert.equal(fresh.stored.qikvrtLastEventId,undefined,'a later event skipped failed persistence');
  assert.equal(fresh.sources[0].closed,true,'failed persistence must stop this cursor source');
  await contentHarness();
  console.log('BACKGROUND_EVENT_TESTS=PASS (payload/order/dedup/id/repository/collision/storage)');
})().catch(error=>{console.error(error);process.exitCode=1;});
