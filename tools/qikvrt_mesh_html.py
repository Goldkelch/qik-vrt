#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic offline QIK-VRT interactive evidence-sphere materializer."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
from typing import Any

ARTIFACT = "QIK_VRT_MESH.html"
EVENT_TYPE = "qikvrt_feature_request"
TASK = "build_qik_vrt_mesh_html"
VIEWS = ["front", "side", "top", "bottom", "isometric", "free_orbit"]
TIME_MODES = ["snapshot", "timeline", "replay", "evolution", "future_projection"]
ANIMATIONS = ["rotation", "orbit", "pulse", "growth", "focus"]
SCHEMA_VERSIONS = ["v1", "v2", "v3", "v4"]
CANONICAL_REQUEST: dict[str, Any] = {
    "title": "QIK-VRT Interactive Evidence Sphere",
    "priority": "high",
    "artifact": ARTIFACT,
    "request": {
        "offline": True,
        "single_file": True,
        "embedded_svg": True,
        "views": VIEWS,
        "time_modes": TIME_MODES,
        "animations": ANIMATIONS,
        "performance": {"fps_monitor": True, "history_chart": True, "profile_system": True, "warning_history": True},
        "persistence": {"schema_versions": SCHEMA_VERSIONS, "migrations": True, "downgrades": True, "canonical_json": True, "unicode_nfc": True},
        "testing": {"property_based": True, "roundtrip": True, "idempotence": True, "unicode": True, "migration": True},
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} fields must be exactly {sorted(keys)}")
    return value


def validate_feature_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("feature request must be an object")
    allowed = {"title", "priority", "artifact", "request", "subject_sha"}
    if not {"title", "priority", "artifact", "request"}.issubset(value) or set(value) - allowed:
        raise ValueError("feature request fields mismatch")
    if value["title"] != CANONICAL_REQUEST["title"] or value["priority"] != "high" or value["artifact"] != ARTIFACT:
        raise ValueError("unsupported feature request identity")
    subject = value.get("subject_sha")
    if subject is not None and (not isinstance(subject, str) or not re.fullmatch(r"[0-9a-f]{40}", subject)):
        raise ValueError("subject_sha must be lowercase 40-hex")
    request = exact(value["request"], {"offline", "single_file", "embedded_svg", "views", "time_modes", "animations", "performance", "persistence", "testing"}, "request")
    if [request[k] for k in ("offline", "single_file", "embedded_svg")] != [True, True, True]:
        raise ValueError("offline/single_file/embedded_svg must be true")
    for key, expected in (("views", VIEWS), ("time_modes", TIME_MODES), ("animations", ANIMATIONS)):
        if request[key] != expected:
            raise ValueError(f"request.{key} drift")
    performance = exact(request["performance"], {"fps_monitor", "history_chart", "profile_system", "warning_history"}, "performance")
    persistence = exact(request["persistence"], {"schema_versions", "migrations", "downgrades", "canonical_json", "unicode_nfc"}, "persistence")
    testing = exact(request["testing"], {"property_based", "roundtrip", "idempotence", "unicode", "migration"}, "testing")
    if not all(v is True for v in performance.values()):
        raise ValueError("performance flags must be true")
    if persistence["schema_versions"] != SCHEMA_VERSIONS or not all(persistence[k] is True for k in ("migrations", "downgrades", "canonical_json", "unicode_nfc")):
        raise ValueError("persistence contract drift")
    if not all(v is True for v in testing.values()):
        raise ValueError("testing flags must be true")
    return value


def decode_request(raw: str) -> dict[str, Any]:
    try:
        return validate_feature_request(json.loads(base64.b64decode(raw.encode("ascii"), validate=True).decode("utf-8")))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("request_json_b64 must be base64 UTF-8 JSON") from exc


def request_from_event(event: dict[str, Any], event_name: str, head: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("bound head must be lowercase 40-hex")
    if event_name == "repository_dispatch":
        if event.get("action") != EVENT_TYPE:
            raise ValueError(f"repository_dispatch action must be {EVENT_TYPE}")
        request = validate_feature_request(event.get("client_payload"))
    elif event_name == "workflow_dispatch":
        inputs = event.get("inputs")
        if not isinstance(inputs, dict) or inputs.get("task") != TASK:
            raise ValueError(f"workflow_dispatch task must be {TASK}")
        raw = str(inputs.get("request_json_b64") or "").strip()
        request = decode_request(raw) if raw else json.loads(canonical_json(CANONICAL_REQUEST))
        subject = str(inputs.get("subject_sha") or "").strip()
        if subject:
            request["subject_sha"] = subject
            validate_feature_request(request)
    else:
        raise ValueError(f"unsupported event: {event_name}")
    if request.get("subject_sha") not in (None, head):
        raise ValueError(f"subject_sha mismatch requested={request['subject_sha']} actual={head}")
    return request


def render_html() -> str:
    contract = canonical_json(CANONICAL_REQUEST)
    views = canonical_json(VIEWS)
    modes = canonical_json(TIME_MODES)
    animations = canonical_json(ANIMATIONS)
    html = f'''<!doctype html>
<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0; Copyright 2026 Ingolf Lohmann. -->
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QIK-VRT Interactive Evidence Sphere</title>
<style>
:root{{--bg:#071018;--panel:#0d1a24;--line:#29495d;--text:#e8f1f6;--muted:#9fb4c1;--accent:#76d7ff}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:14px ui-monospace,monospace}}header,footer{{padding:12px 16px;background:#09151e}}main{{display:grid;grid-template-columns:260px 1fr 300px;min-height:78vh}}aside{{padding:12px;background:var(--panel)}}#stage{{min-height:560px;position:relative;border-inline:1px solid var(--line)}}svg{{width:100%;height:100%}}button,select,input{{margin:3px;padding:6px;background:#102432;color:var(--text);border:1px solid var(--line)}}.node circle{{fill:#17384c;stroke:var(--accent);stroke-width:2}}.node text{{fill:var(--text);font-size:12px}}.edge{{stroke:#4b7087;stroke-width:1.5}}.future{{stroke-dasharray:5 4}}pre{{white-space:pre-wrap;color:var(--muted);font-size:11px}}@media(max-width:900px){{main{{grid-template-columns:1fr}}aside{{border-bottom:1px solid var(--line)}}#stage{{border:0}}}}
</style></head><body>
<header><b>QIK-VRT Interactive Evidence Sphere</b><div>KNOWN(E_n) ⊆ KNOWN(E_(n+1)) · REFERENCE_LINK ≠ EVIDENCE_TRANSFER ≠ EFFECT_ACK · PREDECESSOR_EVIDENCE_TRANSFER = FALSE</div></header>
<main><aside><h3>View</h3><div id="views"></div><h3>Time</h3><select id="mode"></select><input id="time" type="range" min="0" max="1000" value="1000"><button id="play">play/pause</button><h3>Animation</h3><div id="animations"></div><h3>Persistence</h3><button id="save">save</button><button id="load">load</button><button id="clear">clear</button></aside>
<div id="stage"><svg viewBox="0 0 900 600" role="img" aria-label="interactive evidence sphere"><circle cx="450" cy="300" r="245" fill="none" stroke="#254154"/><g id="edges"></g><g id="nodes"></g></svg></div>
<aside><h3>Performance</h3><div>FPS <b id="fps">0</b></div><svg viewBox="0 0 260 90"><polyline id="historyLine" fill="none" stroke="#76d7ff" points=""/></svg><button id="profileBtn">profile 120 frames</button><pre id="profile">idle</pre><h3>Warnings</h3><pre id="warningList">none</pre><h3>Self tests</h3><button id="selfTest">run</button><pre id="testResult">not run</pre></aside></main>
<footer>offline single-file embedded SVG · schema v1/v2/v3/v4 · canonical JSON · Unicode NFC</footer>
<script>
'use strict';const CONTRACT={contract};const VIEWS={views};const MODES={modes};const ANIMS={animations};const STORE='qikvrt-evidence-sphere-v4';
const N=[['difference','Unterschied',.05,-.55,-.15],['relation','Relation',.15,.45,-.25],['leibniz','Leibniz / Monaden',.24,-.15,.48],['temdd','TEMDD',.36,.52,.38],['canonical','Canonical Store',.46,-.5,.30],['transputer','Universal Transputer',.58,.15,-.52],['meta','Meta-Transistor',.67,-.3,-.48],['authority','Authority',.76,.58,-.05],['mirror','Mirror',.79,-.58,.02],['evidence','Evidence Sphere',.88,.05,.58],['zenodo','Zenodo',.95,.44,.5],['future','Future projection',1,-.4,.55]];
const E=[['difference','relation'],['difference','leibniz'],['relation','temdd'],['temdd','canonical'],['temdd','transputer'],['transputer','meta'],['canonical','authority'],['canonical','mirror'],['authority','evidence'],['mirror','evidence'],['evidence','zenodo'],['evidence','future']];
let S={{schemaVersion:4,view:'isometric',timeMode:'snapshot',time:1,yaw:.55,pitch:.35,animations:{{rotation:false,orbit:false,pulse:false,growth:true,focus:true}},fpsHistory:[],warnings:[]}},playing=false,last=performance.now(),frames=[],profileFrames=0;
const $=id=>document.getElementById(id),clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function stable(v){{if(Array.isArray(v))return'['+v.map(stable).join(',')+']';if(v&&typeof v==='object')return'{{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}}';return JSON.stringify(typeof v==='string'?v.normalize('NFC'):v)}}
function migrate(v){{v=JSON.parse(JSON.stringify(v));let n=Number(v.schemaVersion||1);while(n<4){{n++;v.schemaVersion=n;if(n===2)v.animations=v.animations||{{}};if(n===3)v.fpsHistory=v.fpsHistory||[];if(n===4)v.warnings=v.warnings||[]}}return v}}function downgrade(v,target){{v=JSON.parse(JSON.stringify(v));v.schemaVersion=target;if(target<4)delete v.warnings;if(target<3)delete v.fpsHistory;if(target<2)delete v.animations;return v}}
function warn(m){{S.warnings.unshift(new Date().toISOString()+' '+m);S.warnings=S.warnings.slice(0,12);$('warningList').textContent=S.warnings.join('\n')||'none'}}function persist(){{localStorage.setItem(STORE,stable(S))}}function restore(){{S=migrate(JSON.parse(localStorage.getItem(STORE)));sync();render()}}
function project(x,y,z){{let yaw=S.yaw,p=S.pitch,cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(p),sp=Math.sin(p),x1=x*cy-z*sy,z1=x*sy+z*cy,y1=y*cp-z1*sp,z2=y*sp+z1*cp;return[450+x1*250,300+y1*250,1+z2*.22]}}
function render(now=performance.now()){{const visible=N.filter(n=>S.timeMode==='future_projection'||n[1]!=='Future projection').filter(n=>n[2]<=S.time+.0001);const map=new Map(visible.map(n=>[n[0],project(n[3],n[4],Math.sin(n[2]*7)*.2)]));$('edges').innerHTML=E.filter(e=>map.has(e[0])&&map.has(e[1])).map(e=>{{let a=map.get(e[0]),b=map.get(e[1]);return`<line class="edge ${{e[1]==='future'?'future':''}}" x1="${{a[0]}}" y1="${{a[1]}}" x2="${{b[0]}}" y2="${{b[1]}}"/>`}}).join('');$('nodes').innerHTML=visible.map(n=>{{let p=map.get(n[0]),r=7*p[2]*(S.animations.pulse?1+.15*Math.sin(now/350):1)*(S.animations.growth?.75+.25*S.time:1);return`<g class="node" transform="translate(${{p[0]}} ${{p[1]}})"><circle r="${{r}}"/><text x="${{r+5}}" y="4">${{n[1]}}</text></g>`}}).join('')}}
function sync(){{$('mode').value=S.timeMode;$('time').value=Math.round(S.time*1000);document.querySelectorAll('[data-view]').forEach(b=>b.disabled=b.dataset.view===S.view);document.querySelectorAll('[data-anim]').forEach(c=>c.checked=!!S.animations[c.dataset.anim])}}
VIEWS.forEach(v=>{{let b=document.createElement('button');b.textContent=v;b.dataset.view=v;b.onclick=()=>{{S.view=v;const m={{front:[0,0],side:[Math.PI/2,0],top:[0,-Math.PI/2],bottom:[0,Math.PI/2],isometric:[.55,.35]}};if(m[v])[S.yaw,S.pitch]=m[v];sync();render()}};$('views').appendChild(b)}});MODES.forEach(v=>{{let o=document.createElement('option');o.value=v;o.textContent=v;$('mode').appendChild(o)}});ANIMS.forEach(v=>{{let l=document.createElement('label'),c=document.createElement('input');c.type='checkbox';c.dataset.anim=v;c.onchange=()=>S.animations[v]=c.checked;l.append(c,document.createTextNode(v));$('animations').appendChild(l)}});
$('mode').onchange=e=>{{S.timeMode=e.target.value;render()}};$('time').oninput=e=>{{S.time=Number(e.target.value)/1000;render()}};$('play').onclick=()=>playing=!playing;$('save').onclick=persist;$('load').onclick=()=>{{try{{restore()}}catch(e){{warn(e.message)}}}};$('clear').onclick=()=>{{localStorage.removeItem(STORE)}};$('profileBtn').onclick=()=>{{profileFrames=120;frames=[];$('profile').textContent='profiling…'}};
function tick(now){{let dt=now-last;last=now,fps=dt?1000/dt:0;S.fpsHistory.push(fps);S.fpsHistory=S.fpsHistory.slice(-60);$('fps').textContent=fps.toFixed(1);$('historyLine').setAttribute('points',S.fpsHistory.map((v,i)=>`${{i*4.3}},${{88-clamp(v,0,90)}}`).join(' '));if(fps<20)warn('FPS below 20');if(profileFrames){{frames.push(dt);if(--profileFrames===0)$('profile').textContent=`120 frames avg=${{(frames.reduce((a,b)=>a+b,0)/frames.length).toFixed(2)}}ms`}}if(playing&&S.timeMode!=='snapshot'){{S.time=(S.time+dt/12000)%1;$('time').value=Math.round(S.time*1000)}}if(S.animations.rotation)S.yaw+=dt*.00008;if(S.animations.orbit)S.pitch=.35+.1*Math.sin(now/2000);render(now);requestAnimationFrame(tick)}}
function selfTests(){{let out=[];const ok=(n,c)=>{{if(!c)throw Error(n);out.push('PASS '+n)}};try{{let x={{schemaVersion:1,z:'e\u0301',a:[3,2,1]}},m=migrate(x);ok('unicode',JSON.parse(stable(x)).z==='é');ok('migration',m.schemaVersion===4);for(let v=1;v<=4;v++)ok('roundtrip-v'+v,migrate(downgrade(m,v)).schemaVersion===4);for(let i=0;i<128;i++){{let q={{i,s:'x'+i,a:[i%7,(i*i)%11]}};ok('property-'+i,stable(JSON.parse(stable(q)))===stable(q))}}localStorage.setItem(STORE,stable(S));ok('idempotence',stable(JSON.parse(localStorage.getItem(STORE)))===stable(S));$('testResult').textContent=out.slice(0,8).join('\n')+'\nPASS property-based samples=128\nPASS total='+out.length}}catch(e){{$('testResult').textContent='FAIL '+e.message}}}}
$('selfTest').onclick=selfTests;sync();render();requestAnimationFrame(tick);
</script></body></html>'''
    return unicodedata.normalize("NFC", html)


def artifact_bytes() -> bytes:
    return render_html().encode("utf-8")


def write_artifact(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(artifact_bytes())


def check_artifact(path: pathlib.Path) -> None:
    actual = path.read_bytes()
    expected = artifact_bytes()
    if actual != expected:
        raise ValueError(f"artifact drift actual={sha256(actual)} expected={sha256(expected)}")


def load_event(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("event JSON must be an object")
    return value


def request_summary(request: dict[str, Any], head: str) -> dict[str, Any]:
    return {"schema":"qikvrt_interactive_evidence_sphere_request_receipt_v1","event_type":EVENT_TYPE,"task":TASK,"artifact":ARTIFACT,"subject_sha":head,"request_sha256":sha256((canonical_json(request)+"\n").encode()),"offline":True,"single_file":True,"embedded_svg":True,"effect_scope":"deterministic-build-test-artifact-only","repository_mutation":False,"effect_ack_done":False}


def build_receipt(request: dict[str, Any], head: str, tree: str, artifact: pathlib.Path) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise ValueError("tree must be lowercase 40-hex")
    check_artifact(artifact)
    data = artifact.read_bytes()
    return {**request_summary(request, head),"schema":"qikvrt_interactive_evidence_sphere_build_receipt_v1","tree_sha":tree,"artifact_sha256":sha256(data),"artifact_bytes":len(data),"tests_required":["property_based","roundtrip","idempotence","unicode","migration"],"transport_ack_is_effect_ack":False,"predecessor_evidence_transfer":False}


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    g=sub.add_parser("generate"); g.add_argument("--output",default=ARTIFACT)
    c=sub.add_parser("check"); c.add_argument("--path",default=ARTIFACT)
    v=sub.add_parser("validate-event"); v.add_argument("--event-path",required=True); v.add_argument("--event-name",required=True); v.add_argument("--head",required=True)
    r=sub.add_parser("receipt"); r.add_argument("--event-path",required=True); r.add_argument("--event-name",required=True); r.add_argument("--head",required=True); r.add_argument("--tree",required=True); r.add_argument("--artifact",required=True); r.add_argument("--output",required=True)
    a=p.parse_args(argv)
    try:
        if a.cmd=="generate": write_artifact(pathlib.Path(a.output)); print(f"PASS generated {a.output} sha256={sha256(pathlib.Path(a.output).read_bytes())}")
        elif a.cmd=="check": check_artifact(pathlib.Path(a.path)); print(f"PASS deterministic artifact {a.path}")
        else:
            req=request_from_event(load_event(pathlib.Path(a.event_path)),a.event_name,a.head)
            if a.cmd=="validate-event": print(canonical_json(request_summary(req,a.head)))
            else:
                out=pathlib.Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(canonical_json(build_receipt(req,a.head,a.tree,pathlib.Path(a.artifact)))+"\n",encoding="utf-8"); print(f"PASS receipt {out}")
    except (OSError,ValueError,UnicodeError,json.JSONDecodeError) as exc:
        print(f"BLOCK {exc}",file=sys.stderr); return 2
    return 0

if __name__ == "__main__": raise SystemExit(main())
