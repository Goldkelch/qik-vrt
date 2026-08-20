/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
(function(){
"use strict";
const SCHEMA="qikvrt.universal-information-envelope.v1";
const STORE_IN="qikvrtUniversalInbox";
const STORE_OUT="qikvrtUniversalOutbox";
const TEMPORAL=new Set(["PAST","PRESENT","FUTURE","UNKNOWN","UNBOUND"]);
const MAX_ITEMS=64;
const enc=new TextEncoder();
function byId(id){return document.getElementById(id)}
function now(){return new Date().toISOString()}
function randomId(){const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);return Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("")}
async function sha256(text){const digest=await crypto.subtle.digest("SHA-256",enc.encode(text));return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("")}
function normalizeEndpoint(value){const v=String(value||"").trim();return v||"UNKNOWN"}
function validateEnvelope(e){if(!e||e.schema!==SCHEMA)return "schema";if(typeof e.id!=="string"||!e.id)return "id";if(!TEMPORAL.has(e.temporal_relation))return "temporal_relation";if(!e.source||typeof e.source.claimed!=="string")return "source";if(!e.destination||typeof e.destination.claimed!=="string")return "destination";if(e.payload_encoding!=="utf-8")return "payload_encoding";if(typeof e.payload!=="string")return "payload";if(!/^[0-9a-f]{64}$/.test(e.payload_sha256||""))return "payload_sha256";return null}
async function buildEnvelope(){const payload=byId("payload").value;return{schema:SCHEMA,id:randomId(),created_at:now(),observed_at:null,temporal_relation:byId("temporalRelation").value,source:{relation:"CLAIMED",claimed:normalizeEndpoint(byId("source").value)},destination:{relation:"OPAQUE",claimed:normalizeEndpoint(byId("destination").value)},content_type:normalizeEndpoint(byId("contentType").value),payload_encoding:"utf-8",payload,payload_sha256:await sha256(payload),causal_predecessors:[],authority:{state:"UNRESOLVED"},evidence:[],effect_state:"RECEIVED_NOT_AUTHORIZED"}}
async function getList(key){const v=await browser.storage.local.get(key);return Array.isArray(v[key])?v[key]:[]}
async function putList(key,list){await browser.storage.local.set({[key]:list.slice(-MAX_ITEMS)})}
async function append(key,e){const list=await getList(key);list.push(e);await putList(key,list);return list}
async function receiveEnvelope(e){const problem=validateEnvelope(e);if(problem)throw new Error(`invalid envelope: ${problem}`);const actual=await sha256(e.payload);if(actual!==e.payload_sha256)throw new Error("payload digest mismatch");const observed={...e,observed_at:now(),effect_state:"RECEIVED_NOT_AUTHORIZED"};await append(STORE_IN,observed);return observed}
function summary(e){return `${e.temporal_relation} | ${e.source.claimed} -> ${e.destination.claimed} | ${e.content_type}`}
function meta(e){return [`id: ${e.id}`,`created_at: ${e.created_at}`,`observed_at: ${e.observed_at||"UNOBSERVED"}`,`payload_sha256: ${e.payload_sha256}`,`authority: ${(e.authority&&e.authority.state)||"UNRESOLVED"}`,`effect_state: ${e.effect_state}`].join("\n")}
async function copyText(text){await navigator.clipboard.writeText(text)}
function renderOne(e,box,isOut){const d=document.createElement("details");d.className="envelope";const s=document.createElement("summary");s.textContent=summary(e);const m=document.createElement("pre");m.className="meta";m.textContent=meta(e);const p=document.createElement("pre");p.className="payload";p.textContent=e.payload;const actions=document.createElement("div");actions.className="actions";const copyEnvelope=document.createElement("button");copyEnvelope.type="button";copyEnvelope.textContent="Umschlag kopieren";copyEnvelope.addEventListener("click",()=>copyText(JSON.stringify(e,null,2)).then(()=>setStatus("COPIED_ENVELOPE")).catch(err=>setStatus(`COPY_FAILED: ${err.message}`)));const copyPayload=document.createElement("button");copyPayload.type="button";copyPayload.textContent="Inhalt kopieren";copyPayload.addEventListener("click",()=>copyText(e.payload).then(()=>setStatus("COPIED_PAYLOAD")).catch(err=>setStatus(`COPY_FAILED: ${err.message}`)));actions.append(copyEnvelope,copyPayload);if(isOut){const loop=document.createElement("button");loop.type="button";loop.textContent="Lokal empfangen";loop.addEventListener("click",()=>receiveEnvelope(e).then(refresh).then(()=>setStatus("RECEIVED_LOOPBACK")).catch(err=>setStatus(`RECEIVE_FAILED: ${err.message}`)));actions.append(loop)}d.append(s,m,p,actions);box.append(d)}
async function renderList(key,element,isOut){const box=byId(element);box.replaceChildren();const list=await getList(key);for(const e of list.slice().reverse())renderOne(e,box,isOut)}
async function refresh(){await Promise.all([renderList(STORE_IN,"inbox",false),renderList(STORE_OUT,"outbox",true)])}
function setStatus(v){byId("status").textContent=v}
byId("createEnvelope").addEventListener("click",async()=>{try{const e=await buildEnvelope();await append(STORE_OUT,e);await refresh();setStatus("OUTBOX_ACCEPTED")}catch(err){setStatus(`CREATE_FAILED: ${err.message}`)}});
byId("pasteEnvelope").addEventListener("click",async()=>{try{const text=await navigator.clipboard.readText();const e=JSON.parse(text);await receiveEnvelope(e);await refresh();setStatus("INBOX_ACCEPTED")}catch(err){setStatus(`RECEIVE_FAILED: ${err.message}`)}});
refresh().catch(err=>setStatus(`INIT_FAILED: ${err.message}`));
})();
