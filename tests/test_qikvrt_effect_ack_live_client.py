#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Checks for the read-only Effect-Acknowledgement mesh live client."""
import json, pathlib, shutil, subprocess, textwrap, unittest
R=pathlib.Path(__file__).resolve().parents[1]
P=R/'docs/terminal/live/index.html'; C=R/'docs/assets/js/qikvrt-effect-ack-live-core.js'
J=R/'docs/assets/js/qikvrt-effect-ack-live.js'; S=R/'docs/assets/css/qikvrt-effect-ack-live.css'
Q=R/'docs/terminal/QIKVRT_EFFECT_ACK_MESH_LIVE_SNAPSHOT_V1.schema.json'
D=R/'docs/terminal/EFFECT_ACK_MESH_LIVE_CLIENT.md'

class T(unittest.TestCase):
 @classmethod
 def setUpClass(x):
  x.p=P.read_text(); x.c=C.read_text(); x.j=J.read_text(); x.s=S.read_text(); x.q=json.loads(Q.read_text()); x.d=D.read_text()
 def test_1_accessible_bilingual_view(x):
  for m in ['data-language="de"','lang="en"','id="startObservation"','id="stopObservation"','id="reobserveNow"','id="liveEffectState"','id="liveProfileState"','id="liveTransactions"','id="liveDeltaStream"','aria-live="polite"','READ_ONLY','PUBLIC_GET_ONLY','STOP_ON_STALL','CAUSALITY != SEQUENCE','PASS=false · FINAL_PASS=false · EFFECT_ACK_DONE=false']: x.assertIn(m,x.p)
  x.assertIn('prefers-reduced-motion',x.s); x.assertIn('setAttribute("role", "progressbar")',x.j); x.assertIn('aria-valuetext',x.j)
 def test_2_fixed_public_get_only(x):
  for m in ['https://api.github.com/repos/Goldkelch/qik-vrt','https://api.github.com/repos/ingolf-lohmann/qik-vrt','method: "GET"','credentials: "omit"','AbortController','REQUEST_TIMEOUT_MS = 12 * 1000','MAX_FULL_OBSERVATIONS_PER_HOUR = 8','BASE_INTERVAL_MS = 60 * 1000','PRIORITY_PULL_REQUESTS = Object.freeze([684, 690, 694, 698])','STOPPED_ON_STALL']: x.assertIn(m,x.j)
  for m in ['"Authorization":','localStorage','sessionStorage','innerHTML','eval(','Function(','method: "POST"','method: "PUT"','method: "PATCH"','method: "DELETE"']: x.assertNotIn(m,x.j)
 def test_3_states_stages_schema_fail_closed(x):
  for m in ['EFFECT_NACK','EFFECT_ACK_CONTINUE','EFFECT_ACK_DONE','EFFECT_ACK_ISOLATE','EFFECT_ACK_BLOCK','STALL_THRESHOLD = 3','provisional.profile_state = "STALL"']: x.assertIn(m,x.c)
  x.assertIn('STALL is not a sixth canonical state',x.d); p=x.q['properties']; x.assertEqual(p['retry_policy']['properties']['stall_threshold_observations']['const'],3)
  x.assertEqual(x.q['$defs']['transaction']['properties']['stage_coverage']['properties']['total']['const'],11)
  for k in ['PASS','FINAL_PASS','EFFECT_ACK_DONE']: x.assertIs(p['completion_claims']['properties'][k]['const'],False)
 @unittest.skipUnless(shutil.which('node'),'node required')
 def test_4_activity_retry_does_not_move_effect_and_third_snapshot_stalls(x):
  z=textwrap.dedent(f"""const a=require('node:assert/strict'),C=require({json.dumps(str(C))});
  const cm=(s,t,r)=>({{sha:s,html_url:'https://github.com/'+r+'/commit/'+s,commit:{{tree:{{sha:t}}}}}}),h='b'.repeat(40),pr={{number:698,title:'c',html_url:'https://github.com/Goldkelch/qik-vrt/pull/698',state:'open',draft:true,merged:false,user:{{login:'o'}},requested_reviewers:[],base:{{ref:'main',sha:'a'.repeat(40)}},head:{{ref:'x',sha:h}}}},run=(i,n)=>({{id:i,name:n,head_sha:h,status:'completed',conclusion:'action_required',html_url:'https://github.com/x/'+i,head_commit:{{tree_id:'c'.repeat(40)}}}}),r=[run(1,'QIKVRT CI'),run(2,'QIKVRT repository evidence materialization')],snap=(p,rr,t)=>C.buildSnapshot({{observed_at:t,authority_commit:cm('a'.repeat(40),'1'.repeat(40),'Goldkelch/qik-vrt'),mirror_commit:cm('d'.repeat(40),'1'.repeat(40),'ingolf-lohmann/qik-vrt'),pull_requests:[pr],workflow_runs:rr,reviews_by_pr:{{698:[]}}}},p);(async()=>{{let o=await snap(null,r,'2026-08-19T00:00:00Z'),q=await snap(o,r.concat(run(3,'QIKVRT CI')),'2026-08-19T00:01:00Z'),w=await snap(q,r.concat(run(4,'QIKVRT CI')),'2026-08-19T00:02:00Z');a.equal(o.effect_state,'EFFECT_ACK_BLOCK');a.equal(o.transactions[0].first_deterministic_blocker,'EXACT_HEAD_ACTION_REQUIRED_PRE_JOB');a.equal(o.transactions[0].stage_coverage.total,11);a.equal(q.causal_fingerprint,o.causal_fingerprint);a.equal(w.profile_state,'STALL');a.equal(w.stall_since,o.last_relevant_progress);a.ok(C.diffSnapshots(q,w).some(v=>v.code==='PROFILE_STATE_CHANGED'))}})().catch(e=>{{console.error(e);process.exit(1)}});""")
  v=subprocess.run(['node','-e',z],cwd=R,text=True,capture_output=True,timeout=30); x.assertEqual(v.returncode,0,v.stdout+v.stderr)
 @unittest.skipUnless(shutil.which('node'),'node required')
 def test_5_bot_comment_is_not_independent_approval(x):
  z=f"const a=require('node:assert/strict'),C=require({json.dumps(str(C))}),b={{state:'COMMENTED',user:{{login:'github-actions[bot]',type:'Bot'}},body:'APPROVE'}},h={{state:'APPROVED',user:{{login:'Goldkelch',type:'User'}}}};a.equal(C.latestIndependentReviewDisposition([b],'o').state,'PENDING');a.equal(C.latestIndependentReviewDisposition([b,h],'o').state,'APPROVED');"
  v=subprocess.run(['node','-e',z],cwd=R,text=True,capture_output=True,timeout=15); x.assertEqual(v.returncode,0,v.stdout+v.stderr)
 @unittest.skipUnless(shutil.which('node'),'node required')
 def test_6_javascript_syntax(x):
  for p in [C,J]:
   v=subprocess.run(['node','--check',str(p)],text=True,capture_output=True,timeout=15); x.assertEqual(v.returncode,0,v.stdout+v.stderr)
if __name__=='__main__': unittest.main()
