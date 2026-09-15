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
  console.log('BACKGROUND_EVENT_TESTS=PASS (payload/order/dedup/id/repository/collision/storage)');
})().catch(error=>{console.error(error);process.exitCode=1;});
