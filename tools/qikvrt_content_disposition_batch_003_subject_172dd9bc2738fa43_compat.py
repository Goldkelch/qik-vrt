#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic root-status compatibility layer for the second Batch-003 subject."""
from __future__ import annotations
import copy,json,pathlib
from typing import Any,Mapping
from tools import qikvrt_content_disposition_batch_003_subject_2581811b342e505d as prior
from tools import qikvrt_content_disposition_batch_003_subject_172dd9bc2738fa43 as current
ROOT=pathlib.Path(__file__).resolve().parents[1]
AI_PROGRESS=ROOT/'AI_PROGRESS.json';AI_STATUS=ROOT/'AI_STATUS.md'
SUBJECT_ID=current.SID;NEXT_SUBJECT_ID=current.NS;NEXT_EFFECT=current.NX
TOOL_REL='tools/qikvrt_content_disposition_batch_003_subject_172dd9bc2738fa43.py'
SubjectDispositionError=current.E
pretty=current.pretty

def fail(x:str):raise SubjectDispositionError(x)
def _matrix()->dict[str,Any]:return current.read(current.P['CLAIM_MATRIX.json'])
def render_status(claim_count:int,open_count:int)->str:
 return f'''# QIK-VRT Work Status\n\nRepository: `Goldkelch/qik-vrt`\n\nUpdated at: `{current.AT}`\n\nSnapshot state: **`WORKING`**. Overall effect state: **`EFFECT_ACK_CONTINUE`**. No unqualified repository-wide `PASS`, `FINAL_PASS`, Zenodo publication or corpus completion is claimed.\n\n`[██████████████░░░░░] 74%` — Zenodo-Subject-Disposition (14/19)\n\n- ✓ Exact public V8.33 archive and 18 nested ZIPs recursively inspected fail-closed\n- ✓ `{SUBJECT_ID}`: {claim_count}/{claim_count} assertion nodes classified; {open_count} explicitly `OPEN`\n- ⚠ 18 archived manifest path-hash assertions contradict exact observed bytes\n- ⚠ Versioned correction required; historical public bytes remain unchanged\n- ▶ Next work unit: `{NEXT_SUBJECT_ID}`\n- □ Four later Batch-003 subjects and one separately queued subject remain\n- □ Corrected candidate, retrospective proof corpus and any publication effect\n\n## BLOCK\n\n`BATCH003_SUBJECT_172DD_HISTORICAL_MANIFEST_HASH_AND_POSITIVE_STATUS_CORRECTION_REQUIRED`\n\nSmallest repair: create a versioned corrected candidate that regenerates manifests and narrows unbound PASS/P_nash/persistence/universality wording, then return it to the owner. Read-only disposition of remaining subjects may continue.\n\n## NEXT\n\n`{NEXT_EFFECT}`\n'''
def build_progress_projection()->tuple[dict[str,Any],str]:
 p=copy.deepcopy(prior.build_progress_projection()[0]);m=_matrix();n=int(m['claim_count']);o=int(m['epistemic_open_count'])
 p.update(state='WORKING',effect_state='EFFECT_ACK_CONTINUE',percent=74,current_action=f'{SUBJECT_ID} terminally classified from exact recursive public bytes with {n} assertion nodes and {o} explicit OPEN claims; versioned correction required; {NEXT_SUBJECT_ID} is next.',pending_steps=['Process the four remaining Batch-003 archive subjects and the final queued subject','Create and return versioned corrected candidates where public wording exceeds evidence','Build and verify the retrospective proof corpus before any publication effect'],blockers=[{'failure_class':'BATCH003_SUBJECT_172DD_HISTORICAL_MANIFEST_HASH_AND_POSITIVE_STATUS_CORRECTION_REQUIRED','affected_artifacts':[current.P['CONTENT_CHANGE_DECISION.json'].relative_to(ROOT).as_posix(),current.P['INTERNAL_HASH_BINDING_AUDIT.json'].relative_to(ROOT).as_posix(),current.P['CLAIM_MATRIX.json'].relative_to(ROOT).as_posix()],'smallest_repair':'Create a versioned corrected candidate that regenerates manifests and narrows unbound PASS/P_nash/persistence/universality wording, then return it to the owner.'}],next_action=NEXT_EFFECT,updated_at=current.AT,union_receipt_state='CONTENT_DISPOSITION_BATCH_003_SECOND_SUBJECT_TERMINAL_CORRECTION_REQUIRED_NEXT_SUBJECT_READY')
 step=f'Recover exact recursive archive content and terminally classify {SUBJECT_ID}; record versioned correction required without Zenodo mutation'
 if step not in p['completed_steps']:p['completed_steps'].append(step)
 s=p['scopes']['qikvrt-zenodo-canonical-union-2026-07-28-v1'];s['percent']=74;s['counts'].update(dispositioned_subjects=14,open_subjects=5,dispositioned_claims=1747+n);s.update(active_batch={'active_subject':NEXT_SUBJECT_ID,'active_work_package':current.N.relative_to(ROOT).as_posix(),'batch_id':current.BID,'dispositioned_subjects':2,'open_subjects':4,'state':'IN_PROGRESS_CORRECTION_REQUIRED_FOR_PRIOR_SUBJECT','subjects':6},queued_after_active=1,boundary='Four active Batch-003 subjects, one later subject, the required versioned correction candidate, the retrospective proof corpus and any Zenodo mutation remain open.',next_action=NEXT_EFFECT,batch_003={'active_subject':NEXT_SUBJECT_ID,'active_work_package':current.N.relative_to(ROOT).as_posix(),'claim_extraction_complete':False,'correction_required_subjects':[SUBJECT_ID],'dispositioned_subjects':2,'first_subject_claim_extraction_complete':True,'latest_subject_receipt':current.P['SUBJECT_DISPOSITION_RECEIPT.json'].relative_to(ROOT).as_posix(),'next_action':NEXT_EFFECT,'open_subjects':4,'state':'SECOND_SUBJECT_TERMINAL_CORRECTION_REQUIRED_NEXT_SUBJECT_READY','subjects':6,'terminal':False});p['projection_owner']={'check_command':f'python3 -B {TOOL_REL} --check','tool':TOOL_REL}
 validate_progress_projection(p)
 return p,render_status(n,o)
def validate_progress_projection(p:Mapping[str,Any])->None:
 scope=p.get('scopes',{}).get('qikvrt-zenodo-canonical-union-2026-07-28-v1',{})
 if p.get('percent')!=74 or p.get('effect_state')!='EFFECT_ACK_CONTINUE' or p.get('next_action')!=NEXT_EFFECT:fail('second-subject root projection identity drift')
 if any(p.get('claims',{}).get(k) is not False for k in ('PASS','FINAL_PASS','EFFECT_ACK_DONE')) or any(scope.get('claims',{}).get(k) is not False for k in ('PASS','FINAL_PASS','EFFECT_ACK_DONE')):fail('second-subject root projection release inflation')
 if scope.get('counts',{}).get('dispositioned_subjects')!=14 or scope.get('counts',{}).get('open_subjects')!=5 or scope.get('batch_003',{}).get('active_subject')!=NEXT_SUBJECT_ID:fail('second-subject corpus projection drift')
 blockers=p.get('blockers')
 if not isinstance(blockers,list) or len(blockers)!=1 or blockers[0].get('failure_class')!='BATCH003_SUBJECT_172DD_HISTORICAL_MANIFEST_HASH_AND_POSITIVE_STATUS_CORRECTION_REQUIRED':fail('second-subject blocker projection drift')
def verify_materialized()->dict[str,Any]:
 current.check();p,s=build_progress_projection()
 if current.read(AI_PROGRESS)!=p:fail('materialized output drift: AI_PROGRESS.json')
 if AI_STATUS.read_text(encoding='utf-8')!=s:fail('materialized output drift: AI_STATUS.md')
 return {'schema':'qikvrt_batch003_subject_projection_verification_v1','state':'SECOND_SUBJECT_TERMINAL_CORRECTION_REQUIRED_NEXT_SUBJECT_READY','subject_id':SUBJECT_ID,'active_subject':NEXT_SUBJECT_ID,'next_deterministic_effect':NEXT_EFFECT,'open_subject_count':5,'pass':False,'final_pass':False,'effect_ack_done':False,'zenodo_mutation_authorized':False}
