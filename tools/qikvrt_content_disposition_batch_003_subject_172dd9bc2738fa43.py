#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Terminal read-only disposition for Batch-003 subject 172dd9bc2738fa43."""
from __future__ import annotations
import argparse,base64,copy,hashlib,json,pathlib,re
from collections import Counter
from typing import Any,Iterable,Mapping
R=pathlib.Path(__file__).resolve().parents[1]
B=R/'release/zenodo-corpus-proof-2026-07-28/canonical-union'
O=B/'content-disposition-batch-003/subject-dispositions/SUBJECT-172dd9bc2738fa43'
P={n:O/n for n in ('PUBLIC_ARCHIVE_RECOVERY_RECEIPT.json','ARCHIVE_CONTENT_INVENTORY.json','INTERNAL_HASH_BINDING_AUDIT.json','CLAIM_MATRIX.json','SOURCE_TO_CLAIM_TRACEABILITY.json','ASSERTION_NODE_COVERAGE.json','CONTENT_CHANGE_DECISION.json','SUBJECT_DISPOSITION_RECEIPT.json')}
N=R/'work-units/EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_BATCH_003_SUBJECT_B4849E1A2D6B2270.json'; AP=R/'AI_PROGRESS.json'; AS=R/'AI_STATUS.md'
SID='SUBJECT-172dd9bc2738fa43'; NS='SUBJECT-b4849e1a2d6b2270'; BID='CONTENT-DISPOSITION-BATCH-003'; RID=20712301; DOI='10.5281/zenodo.20712301'
AN='QIKVRT_V8_33_REPOSITORY_AND_ANTICIPATORY_ZENODO_415_CONTENTTYPE_FIX.zip'; AH='a446a0c5b9fac78e47c3b51bc88ac81a6eaa7d15add089804d46c4f294fbd2f7'; AM='48b1f4cb1ddaf017b874e55cdefd5dbb'; AB=148269; SN=AN+'.sha256'; SH='7dbc20f4a33d727d5df9a8857e631cb29991a73f4ae38ee37243d064d29a5594'; RH='b32a71dad33b863715484d16e8d53a2aa2a307f33b4d14e24453ee9ac0357705'
AT='2026-07-30T02:11:07Z'; PH='0ecc58498215b95c65c8a2ce01af5d8b393925d9'; RUN=30507735045; ART=8745961327; ARTH='73ed2d15e0806a1a9825a1e9058545fb8d19727895f758b009bb60775a565399'; NX='EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_BATCH_003_SUBJECT_B4849E1A2D6B2270'
LIC={'classification':'machine_readable_retrospective_claim_disposition','copyright':'Copyright 2026 Ingolf Lohmann','license':'CC-BY-NC-ND-4.0','rights_holder':'Ingolf Lohmann'}
CLS={'FORMAL_PROVED','EMPIRICALLY_EVIDENCED','SOURCE_BOUND','NORMATIVE','INTERPRETATIVE','OPEN'}; CODE={'.py','.ps1','.bat','.sh','.html'}
NOR=re.compile(r'\b(must|shall|required|requires|requirement|policy|muss|müssen|soll|sollen|darf|dürfen|pflicht|grundsatz|zulässig|unzulässig)\b',re.I)
INT=re.compile(r'\b(interpretation|interpretiert|deutung|einordnung|ontolog|metapher|bedeutung|these)\b',re.I)
POS=re.compile(r'\b(PASS(?:_[A-Z0-9_]+)?|DONE|COMPLETED|COMPLETE|FINAL_PASS|EFFECT_ACK_DONE|P_NASH\s*[:=]\s*(?:TRUE|`TRUE`)|PERSISTED)\b',re.I)
OVR=re.compile(r'\b(universal(?:e|er|es|ly)?|allumfassend|vollständig(?:e|er|es)?|endgültig|unzweifelhaft|alle\s+(?:relevanten\s+)?schichten|across all relevant layers|entire system|full repository)\b',re.I)
NEG=re.compile(r'\b(BLOCK|PENDING|NOT_CREATED|NOT_COMPLETED|NOT_PUBLISHED|UNVERIFIED|MISSING|false|null|keine externe wirkung|nicht veröffentlicht|not complete|does not claim|no false done)\b',re.I)
CON=re.compile(r'\b(if|wenn|requires|nur bei|erst wenn|may not|darf nicht|kein(?:e|en|er|es)?|no |not )\b',re.I)
IDS={'schema','record_type','type','role','title','name','package','version','path','file','filename','operation','work_unit_id','claim_id','id','error_class','classification'}
class E(RuntimeError):pass
def fail(x:str):raise E(x)
def h(b:bytes):return hashlib.sha256(b).hexdigest()
def pretty(x:Any):return json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
def put(p:pathlib.Path,x:Any):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(pretty(x),encoding='utf-8',newline='\n')
def read(p:pathlib.Path):return json.loads(p.read_text(encoding='utf-8'))
def esc(x:str):return x.replace('~','~0').replace('/','~1')
def unesc(x:str):return x.replace('~1','/').replace('~0','~')
def leaves(v:Any,p:str='')->Iterable[tuple[str,Any]]:
 if isinstance(v,Mapping):
  if not v:yield p or '/',v
  for k in sorted(v):yield from leaves(v[k],f'{p}/{esc(str(k))}')
 elif isinstance(v,list):
  if not v:yield p or '/',v
  for i,x in enumerate(v):yield from leaves(x,f'{p}/{i}')
 else:yield p or '/',v
def split(q:str):
 if '!/' not in q:fail(f'bad qualified path: {q}')
 return q.rsplit('!/',1)
def text(e:Mapping[str,Any]):
 try:return base64.b64decode(e['text_content_base64_utf8'],validate=True).decode()
 except Exception as x:raise E(f'bad retained text {e.get("qualified_path")}: {x}') from x
def target(es:Mapping[str,Mapping[str,Any]],a:str,s:str,t:str):
 n=t.replace('\\','/').lstrip('./');par=pathlib.PurePosixPath(s).parent
 for r in dict.fromkeys(((par/pathlib.PurePosixPath(n)).as_posix(),pathlib.PurePosixPath(n).as_posix())):
  q=f'{a}!/{r}'
  if q in es:return q,es[q]
 return f'{a}!/{(par/pathlib.PurePosixPath(n)).as_posix()}',None
def report(p:pathlib.Path):
 raw=p.read_bytes()
 if h(raw)!=RH:fail('recursive report digest drift')
 x=json.loads(raw)
 if x.get('schema')!='qikvrt_batch003_recursive_public_archive_probe_v1' or x.get('subject_id')!=SID or x.get('record',{}).get('record_id')!=RID or x.get('record',{}).get('doi')!=DOI or x.get('record',{}).get('public_file_set_exact') is not True:fail('report identity drift')
 a=x.get('public_archive',{})
 if any(a.get(k)!=v for k,v in {'name':AN,'bytes':AB,'md5':AM,'sha256':AH}.items()):fail('archive identity drift')
 obs=x.get('record',{}).get('public_file_observations',{})
 if set(obs)!={AN,SN} or obs[SN].get('sha256')!=SH:fail('public file set drift')
 s=x.get('recursive_summary',{});c=x.get('completion_claims',{})
 if (s.get('total_entry_count'),s.get('total_text_file_count'),s.get('total_nested_zip_count'),s.get('observed_maximum_depth'))!=(210,190,18,4) or c.get('nested_archive_content_extracted') is not True or c.get('all_text_sources_retained_for_claim_extraction') is not True or any(c.get(k) is not False for k in ('claim_disposition_complete','pass','final_pass','effect_ack_done','proof_corpus_published_on_zenodo','zenodo_mutation_authorized')):fail('recursive boundary drift')
 return x
def audit(es:Mapping[str,Mapping[str,Any]],ts:list[Mapping[str,Any]]):
 rows=[];loc={};pat=re.compile(r'^\s*([0-9a-fA-F]{64})\s+[* ]?(.+?)\s*$')
 for e in ts:
  q=e['qualified_path'];a,r=split(q);n=pathlib.PurePosixPath(r).name.lower()
  if n!='sha256sums.txt' and not n.endswith('.sha256'):continue
  for ln,line in enumerate(text(e).splitlines(),1):
   m=pat.match(line)
   if not m:continue
   tq,o=target(es,a,r,m.group(2).strip());row={'assertion_type':'CHECKSUM_LINE','expected_sha256':m.group(1).lower(),'match':bool(o) and o.get('sha256')==m.group(1).lower(),'observed_sha256':o.get('sha256') if o else None,'source_file':q,'source_locator':{'line':ln},'target_file':tq};rows.append(row);loc[(q,'line',ln)]=row
 def walk(v:Any,q:str,a:str,r:str,p:str=''):
  if isinstance(v,Mapping):
   if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str) and re.fullmatch(r'[0-9a-fA-F]{64}',v['sha256']):
    tq,o=target(es,a,r,v['path']);hp=f'{p}/sha256' or '/sha256';row={'assertion_type':'MANIFEST_PATH_SHA256','expected_sha256':v['sha256'].lower(),'match':bool(o) and o.get('sha256')==v['sha256'].lower(),'observed_sha256':o.get('sha256') if o else None,'source_file':q,'source_locator':{'json_pointer':hp},'target_file':tq};rows.append(row);loc[(q,'json',hp)]=row
   for k in sorted(v):walk(v[k],q,a,r,f'{p}/{esc(str(k))}')
  elif isinstance(v,list):
   for i,z in enumerate(v):walk(z,q,a,r,f'{p}/{i}')
 for e in ts:
  q=e['qualified_path'];a,r=split(q)
  if not r.lower().endswith('.json'):continue
  try:v=json.loads(text(e))
  except json.JSONDecodeError:continue
  walk(v,q,a,r)
 cs=[x for x in rows if x['assertion_type']=='CHECKSUM_LINE'];ms=[x for x in rows if x['assertion_type']=='MANIFEST_PATH_SHA256'];bad=[x for x in rows if not x['match']]
 out={'_license':LIC,'assertion_count':len(rows),'assertions':rows,'batch_id':BID,'completion_claims':{'all_checksum_lines_resolved':all(x['observed_sha256'] for x in cs),'all_checksum_lines_match':all(x['match'] for x in cs),'all_manifest_path_hashes_resolved':all(x['observed_sha256'] for x in ms),'all_manifest_path_hashes_match':all(x['match'] for x in ms),'pass':False,'final_pass':False,'effect_ack_done':False,'zenodo_mutation_authorized':False},'counts':{'checksum_assertions':len(cs),'checksum_matches':sum(x['match'] for x in cs),'manifest_path_hash_assertions':len(ms),'manifest_path_hash_matches':sum(x['match'] for x in ms),'manifest_path_hash_mismatches':sum(not x['match'] for x in ms),'total_mismatches':len(bad)},'mismatches':bad,'schema':'qikvrt_recursive_internal_hash_binding_audit_v1','state':'CHECKSUM_SIDECARS_VALID_MANIFEST_HASH_MISMATCHES_FOUND' if bad else 'ALL_INTERNAL_HASH_BINDINGS_MATCH','subject_id':SID}
 return out,loc
def nodes(ts:list[Mapping[str,Any]]):
 out=[]
 for e in sorted(ts,key=lambda z:z['qualified_path']):
  q=e['qualified_path'];_,r=split(q);ext=pathlib.PurePosixPath(r).suffix.lower();t=text(e)
  if ext=='.json':
   try:v=json.loads(t)
   except json.JSONDecodeError:v=None
   if v is not None:
    for p,x in leaves(v):out.append({'json_key':unesc(p.rsplit('/',1)[-1]),'locator':p,'locator_type':'json','qualified_path':q,'source_sha256':e['sha256'],'source_value':x,'statement':f'{unesc(p.rsplit("/",1)[-1])} = {json.dumps(x,ensure_ascii=False,sort_keys=True)}'})
    continue
  for ln,line in enumerate(t.splitlines(),1):
   if line.strip():out.append({'json_key':None,'locator':ln,'locator_type':'line','qualified_path':q,'source_sha256':e['sha256'],'statement':line.strip()})
 return out
def classify(n:Mapping[str,Any],b:Mapping[str,Any]|None):
 q=n['qualified_path'];_,r=split(q);ext=pathlib.PurePosixPath(r).suffix.lower();s=n['statement'];k=str(n.get('json_key') or '').lower()
 if b:return ('EMPIRICALLY_EVIDENCED','EMPIRICAL_EVIDENCE_BOUND','SUPPORTED_BY_RECURSIVE_BYTE_AUDIT','COMPATIBLE_WITH_DISPOSITION','Exact only for target bytes named by the checksum assertion.') if b.get('match') else ('OPEN','OPEN','CONTRADICTED_BY_RECURSIVE_BYTE_AUDIT','REQUIRES_VERSIONED_CORRECTION','Archived manifest hash contradicts recursively observed target bytes.')
 if 'template' in r.lower():return 'SOURCE_BOUND','OUT_OF_SCOPE','TEMPLATE_OR_PLACEHOLDER_SOURCE_BOUND','COMPATIBLE_WITH_DISPOSITION','A template is not evidence of an external effect.'
 if ext in CODE:return 'SOURCE_BOUND','SOURCE_BOUND','IMPLEMENTATION_SOURCE_BOUND','COMPATIBLE_WITH_DISPOSITION','Implementation source is not proof that an external effect occurred.'
 if NEG.search(s) or n.get('source_value') is False or (n['locator_type']=='json' and n.get('source_value') is None):return 'SOURCE_BOUND','NEGATIVE_BOUNDARY','EXPLICIT_NEGATIVE_OR_NON_COMPLETION_BOUNDARY','COMPATIBLE_WITH_DISPOSITION','Explicit negative, pending, blocked, absent or non-complete state.'
 if NOR.search(s):return 'NORMATIVE','NORMATIVE','NORMATIVE_SOURCE_STATEMENT','COMPATIBLE_WITH_DISPOSITION','Policy, requirement or permission constraint.'
 if INT.search(s):return 'INTERPRETATIVE','INTERPRETIVE','INTERPRETATIVE_SOURCE_STATEMENT','COMPATIBLE_WITH_DISPOSITION','Interpretation bound to exact source wording.'
 if k in IDS:return 'SOURCE_BOUND','SOURCE_BOUND','SOURCE_IDENTITY_OR_LABEL','COMPATIBLE_WITH_DISPOSITION','Identity label bound to exact source.'
 if POS.search(s) or OVR.search(s):
  if CON.search(s):return 'NORMATIVE','NORMATIVE','CONDITIONAL_OR_NEGATIVE_STATUS_RULE','COMPATIBLE_WITH_DISPOSITION','Condition or prohibition, not evidence that positive status occurred.'
  return 'OPEN','OPEN','HISTORICAL_POSITIVE_COMPLETION_OR_UNIVERSALITY_ASSERTION_NOT_REVALIDATED','REQUIRES_VERSIONED_CORRECTION','Positive completion or universality assertion lacks independent retrospective proof binding.'
 if re.search(r'\b(sha-?256|md5|bytes|size|hash)\b',s,re.I):return 'SOURCE_BOUND','SOURCE_BOUND','SOURCE_RECORDED_INTEGRITY_ASSERTION','COMPATIBLE_WITH_DISPOSITION','Recorded integrity value; only separately matched assertions are empirical.'
 return 'SOURCE_BOUND','SOURCE_BOUND','EXACT_PUBLIC_SOURCE_BOUND','COMPATIBLE_WITH_DISPOSITION','No extension beyond exact frozen public source.'
def claims(ns:list[Mapping[str,Any]],lm:Mapping[tuple[str,str,Any],Mapping[str,Any]]):
 out=[]
 for i,n in enumerate(ns,1):
  ep,di,st,la,bo=classify(n,lm.get((n['qualified_path'],n['locator_type'],n['locator'])));sr={'doi':DOI,'record_id':RID,'qualified_path':n['qualified_path'],'sha256':n['source_sha256'],'locator':{'type':n['locator_type'],'value':n['locator']}};c={'boundary':bo,'claim_id':f'B3S172-{i:05d}','epistemic_class':ep,'proof_refs':[],'publication_language_status':la,'source_refs':[sr],'statement':n['statement'],'status':st,'terminal_disposition':di}
  if n['locator_type']=='json':c['source_value']=n.get('source_value')
  out.append(c)
 return out
def materialize(rp:pathlib.Path):
 x=report(rp);allr=x['flat_entries'];es={z['qualified_path']:z for z in allr};ts=[z for z in allr if z.get('content_class')=='TEXT']
 if len(es)!=210 or len(ts)!=190:fail('content cardinality drift')
 au,lm=audit(es,ts);cs=claims(nodes(ts),lm);cc=Counter(c['epistemic_class'] for c in cs);dc=Counter(c['terminal_disposition'] for c in cs);op=sum(c['epistemic_class']=='OPEN' for c in cs);corr=[c['claim_id'] for c in cs if c['publication_language_status']=='REQUIRES_VERSIONED_CORRECTION']
 inv={'_license':LIC,'subject_id':SID,'schema':'qikvrt_recursive_archive_content_inventory_v1','entry_count':len(allr),'content_class_counts':dict(sorted(Counter(z.get('content_class','DIRECTORY') for z in allr).items())),'entries':[{k:z.get(k) for k in ('qualified_path','archive_depth','content_class','bytes','sha256','git_blob_sha1','uncompressed_bytes')} for z in allr]}
 rec={'_license':LIC,'schema':'qikvrt_public_archive_recovery_receipt_v1','subject_id':SID,'batch_id':BID,'observed_at':AT,'state':'EXACT_PUBLIC_ARCHIVE_RECOVERED_RECURSIVELY_INSPECTED','record':{'record_id':RID,'doi':DOI},'archive':{'name':AN,'bytes':AB,'md5':AM,'sha256':AH},'probe_evidence':{'exact_head':PH,'run_id':RUN,'artifact_id':ART,'artifact_sha256':ARTH,'recursive_report_sha256':RH},'recovery':{'method':'READ_ONLY_ZENODO_REOBSERVATION_AND_RECURSIVE_FAIL_CLOSED_ZIP_INSPECTION','public_record_file_set_exact':True,'nested_archive_content_extracted':True,'historical_public_bytes_rewritten':False},'completion_claims':{'subject_terminally_dispositioned':True,'all_content_claims_dispositioned':False,'pass':False,'final_pass':False,'effect_ack_done':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False}}
 mat={'_license':LIC,'schema':'qikvrt_retrospective_claim_matrix_v1','subject_id':SID,'batch_id':BID,'record_ids':[RID],'claim_count':len(cs),'claims':cs,'classification_summary':{k:cc.get(k,0) for k in sorted(CLS)},'terminal_disposition_counts':dict(sorted(dc.items())),'epistemic_open_count':op,'publication_correction_claim_count':len(corr),'terminally_classified_claim_count':len(cs),'unclassified_claim_count':0,'content_change_decision':{'required':bool(corr),'state':'VERSIONED_CORRECTION_REQUIRED' if corr else 'NO_CONTENT_CHANGE_REQUIRED'},'completion_claims':{'all_assertion_nodes_classified':True,'all_claims_terminally_classified_or_explicitly_open':True,'claim_disposition_complete':True,'formal_claims_have_proof_bindings':True,'pass':False,'final_pass':False,'effect_ack_done':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False}}
 tr={'_license':LIC,'schema':'qikvrt_source_to_claim_traceability_v1','subject_id':SID,'batch_id':BID,'claim_count':len(cs),'untraced_claim_count':0,'entries':[{'claim_id':c['claim_id'],'source_refs':c['source_refs'],'status':c['status'],'terminal_disposition':c['terminal_disposition']} for c in cs]}
 cov={'_license':LIC,'schema':'qikvrt_assertion_node_coverage_v1','subject_id':SID,'assertion_node_count':len(cs),'covered_assertion_node_count':len(cs),'covered_text_source_count':len(ts),'unclassified_node_count':0,'source_coverage':[{'qualified_path':z['qualified_path'],'sha256':z['sha256'],'claim_count':sum(c['source_refs'][0]['qualified_path']==z['qualified_path'] for c in cs)} for z in ts]}
 dec={'_license':LIC,'schema':'qikvrt_content_change_decision_v1','subject_id':SID,'batch_id':BID,'decision':{'required':True,'state':'VERSIONED_CORRECTION_REQUIRED','correction_claim_count':len(corr),'correction_claim_ids':corr,'manifest_hash_mismatch_count':au['counts']['manifest_path_hash_mismatches'],'public_bytes_must_remain_unchanged':True,'repository_evidence_addition_required':True,'owner_review_required_before_any_later_upload':True,'zenodo_mutation_authorized':False,'smallest_repair':'Create a versioned corrected candidate that regenerates manifests and narrows unbound PASS/P_nash/persistence/universality wording, then return it to the owner.'}}
 rc={'_license':LIC,'schema':'qikvrt_content_disposition_subject_receipt_v1','subject_id':SID,'batch_id':BID,'record_id':RID,'observed_at':AT,'state':'TERMINALLY_DISPOSITIONED_CORRECTION_REQUIRED_NEXT_SUBJECT_READY','claim_counts':{'total':len(cs),'terminally_classified':len(cs),'explicit_open':op,'unclassified':0},'content_change_decision':'VERSIONED_CORRECTION_REQUIRED','artifacts':{k.lower().replace('.json',''):v.relative_to(R).as_posix() for k,v in P.items()},'preserved_corpus':{'subject_count':19,'dispositioned_subject_count':14,'open_subject_count':5},'next_deterministic_effect':NX,'completion_claims':{'subject_terminally_dispositioned':True,'all_content_claims_dispositioned':False,'batch_003_terminal':False,'pass':False,'final_pass':False,'effect_ack_done':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False}}
 nu={'_license':{**LIC,'classification':'machine_readable_work_unit'},'schema':'qikvrt_work_unit_v1','work_unit_id':'EXTRACT-ARCHIVE-CONTENT-THEN-DISPOSITION-CLAIMS-BATCH-003-SUBJECT-B4849E1A2D6B2270-20260730','batch_id':BID,'subject_id':NS,'representative_record_id':21244412,'operation':'EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS','state':'READY','dependencies':{'prior_subject_receipt':P['SUBJECT_DISPOSITION_RECEIPT.json'].relative_to(R).as_posix(),'prior_subject_state':rc['state']},'requirements':['retrieve exact public archive bytes read-only','verify complete public file set and every expected digest','recursively reject unsafe archive structures','classify every scalar JSON leaf and every non-empty text line terminally or explicitly OPEN','preserve PASS, FINAL_PASS, EFFECT_ACK_DONE and Zenodo mutation as false'],'next_deterministic_effect':NX}
 for n,v in [('PUBLIC_ARCHIVE_RECOVERY_RECEIPT.json',rec),('ARCHIVE_CONTENT_INVENTORY.json',inv),('INTERNAL_HASH_BINDING_AUDIT.json',au),('CLAIM_MATRIX.json',mat),('SOURCE_TO_CLAIM_TRACEABILITY.json',tr),('ASSERTION_NODE_COVERAGE.json',cov),('CONTENT_CHANGE_DECISION.json',dec),('SUBJECT_DISPOSITION_RECEIPT.json',rc)]:put(P[n],v)
 put(N,nu);progress(len(cs),op);status(len(cs),op);check()
def progress(n:int,o:int):
 p=copy.deepcopy(read(AP));p.update(state='WORKING',effect_state='EFFECT_ACK_CONTINUE',percent=74,current_action=f'{SID} terminally classified from exact recursive public bytes with {n} assertion nodes and {o} explicit OPEN claims; versioned correction required; {NS} is next.',pending_steps=['Process the four remaining Batch-003 archive subjects and the final queued subject','Create and return versioned corrected candidates where public wording exceeds evidence','Build and verify the retrospective proof corpus before any publication effect'],blockers=[{'failure_class':'BATCH003_SUBJECT_172DD_HISTORICAL_MANIFEST_HASH_AND_POSITIVE_STATUS_CORRECTION_REQUIRED','affected_artifacts':[P['CONTENT_CHANGE_DECISION.json'].relative_to(R).as_posix(),P['INTERNAL_HASH_BINDING_AUDIT.json'].relative_to(R).as_posix(),P['CLAIM_MATRIX.json'].relative_to(R).as_posix()],'smallest_repair':'Create a versioned corrected candidate that regenerates manifests and narrows unbound PASS/P_nash/persistence/universality wording, then return it to the owner.'}],next_action=NX,updated_at=AT,union_receipt_state='CONTENT_DISPOSITION_BATCH_003_SECOND_SUBJECT_TERMINAL_CORRECTION_REQUIRED_NEXT_SUBJECT_READY')
 step=f'Recover exact recursive archive content and terminally classify {SID}; record versioned correction required without Zenodo mutation'
 if step not in p['completed_steps']:p['completed_steps'].append(step)
 s=p['scopes']['qikvrt-zenodo-canonical-union-2026-07-28-v1'];s['percent']=74;s['counts'].update(dispositioned_subjects=14,open_subjects=5,dispositioned_claims=1747+n);s.update(active_batch={'active_subject':NS,'active_work_package':N.relative_to(R).as_posix(),'batch_id':BID,'dispositioned_subjects':2,'open_subjects':4,'state':'IN_PROGRESS_CORRECTION_REQUIRED_FOR_PRIOR_SUBJECT','subjects':6},queued_after_active=1,boundary='Four active Batch-003 subjects, one later subject, the required versioned correction candidate, the retrospective proof corpus and any Zenodo mutation remain open.',next_action=NX,batch_003={'active_subject':NS,'active_work_package':N.relative_to(R).as_posix(),'claim_extraction_complete':False,'correction_required_subjects':[SID],'dispositioned_subjects':2,'first_subject_claim_extraction_complete':True,'latest_subject_receipt':P['SUBJECT_DISPOSITION_RECEIPT.json'].relative_to(R).as_posix(),'next_action':NX,'open_subjects':4,'state':'SECOND_SUBJECT_TERMINAL_CORRECTION_REQUIRED_NEXT_SUBJECT_READY','subjects':6,'terminal':False});p['projection_owner']={'check_command':'python3 -B tools/qikvrt_content_disposition_batch_003_subject_172dd9bc2738fa43.py --check','tool':'tools/qikvrt_content_disposition_batch_003_subject_172dd9bc2738fa43.py'};put(AP,p)
def status(n:int,o:int):AS.write_text(f'''# QIK-VRT Work Status

Repository: `Goldkelch/qik-vrt`

Updated at: `{AT}`

Snapshot state: **`WORKING`**. Overall effect state: **`EFFECT_ACK_CONTINUE`**. No unqualified repository-wide `PASS`, `FINAL_PASS`, Zenodo publication or corpus completion is claimed.

`[██████████████░░░░░] 74%` — Zenodo-Subject-Disposition (14/19)

- ✓ Exact public V8.33 archive and 18 nested ZIPs recursively inspected fail-closed
- ✓ `{SID}`: {n}/{n} assertion nodes classified; {o} explicitly `OPEN`
- ⚠ 18 archived manifest path-hash assertions contradict exact observed bytes
- ⚠ Versioned correction required; historical public bytes remain unchanged
- ▶ Next work unit: `{NS}`
- □ Four later Batch-003 subjects and one separately queued subject remain
- □ Corrected candidate, retrospective proof corpus and any publication effect

## BLOCK

`BATCH003_SUBJECT_172DD_HISTORICAL_MANIFEST_HASH_AND_POSITIVE_STATUS_CORRECTION_REQUIRED`

Smallest repair: create a versioned corrected candidate that regenerates manifests and narrows unbound PASS/P_nash/persistence/universality wording, then return it to the owner. Read-only disposition of remaining subjects may continue.

## NEXT

`{NX}`
''',encoding='utf-8',newline='\n')
def check():
 for p in (*P.values(),N):
  if not p.is_file():fail(f'missing output {p.relative_to(R)}')
 a=read(P['INTERNAL_HASH_BINDING_AUDIT.json']);m=read(P['CLAIM_MATRIX.json']);d=read(P['CONTENT_CHANGE_DECISION.json']);r=read(P['SUBJECT_DISPOSITION_RECEIPT.json'])
 if a['counts']!={'checksum_assertions':189,'checksum_matches':189,'manifest_path_hash_assertions':219,'manifest_path_hash_matches':201,'manifest_path_hash_mismatches':18,'total_mismatches':18}:fail('hash audit count drift')
 if m['claim_count']!=5715 or m['classification_summary']!={'EMPIRICALLY_EVIDENCED':390,'FORMAL_PROVED':0,'INTERPRETATIVE':16,'NORMATIVE':90,'OPEN':175,'SOURCE_BOUND':5044} or m['unclassified_claim_count']!=0:fail('claim matrix drift')
 if d['decision']['state']!='VERSIONED_CORRECTION_REQUIRED' or d['decision']['zenodo_mutation_authorized'] is not False:fail('decision drift')
 if r['state']!='TERMINALLY_DISPOSITIONED_CORRECTION_REQUIRED_NEXT_SUBJECT_READY' or r['claim_counts']!={'explicit_open':175,'terminally_classified':5715,'total':5715,'unclassified':0} or any(r['completion_claims'][k] is not False for k in ('all_content_claims_dispositioned','batch_003_terminal','pass','final_pass','effect_ack_done','proof_corpus_published_on_zenodo','zenodo_mutation_authorized')):fail('receipt drift')
def main():
 a=argparse.ArgumentParser();a.add_argument('--report',type=pathlib.Path);a.add_argument('--materialize',action='store_true');a.add_argument('--check',action='store_true');x=a.parse_args()
 if x.materialize:
  if not x.report:fail('--materialize requires --report')
  materialize(x.report)
 if x.check:check()
 if not x.materialize and not x.check:a.error('choose --materialize or --check')
 print(f'{SID} terminal claim disposition: OK\nPASS=false\nFINAL_PASS=false\nEFFECT_ACK_DONE=false\nZENODO_MUTATION=false')
if __name__=='__main__':
 try:main()
 except (E,OSError,UnicodeError,ValueError) as x:print(f'BLOCK: {x}');raise SystemExit(2)
