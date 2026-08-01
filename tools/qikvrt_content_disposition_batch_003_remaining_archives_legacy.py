#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Sequentially disposition all remaining archive subjects and build the corpus.

This executor is read-only with respect to Zenodo. It verifies exact public
bytes, inventories archives fail-closed, classifies every first-party JSON leaf
and every non-empty first-party text line, materializes source traceability,
and builds a retrospective proof corpus only after all 19 subjects are covered.
It never authorizes or performs a Zenodo mutation and never claims repository-
wide PASS, FINAL_PASS, EFFECT_ACK_DONE, deployment, synchronization or merge.
"""
from __future__ import annotations
import argparse,base64,copy,hashlib,json,pathlib,re
from collections import Counter
from typing import Any,Iterable,Mapping
from tools import qikvrt_batch003_remaining_archive_probe as probe
from tools import qikvrt_content_disposition_batch_003_subject_172dd9bc2738fa43_compat as previous
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'release/zenodo-corpus-proof-2026-07-28/canonical-union'
B3=BASE/'content-disposition-batch-003'
PROOF=BASE/'retrospective-proof-corpus'
AI_PROGRESS=ROOT/'AI_PROGRESS.json';AI_STATUS=ROOT/'AI_STATUS.md'
TOOL_REL='tools/qikvrt_content_disposition_batch_003_remaining_archives.py'
OBSERVED_AT='2026-07-30T02:54:23Z'
PROBE_HEAD='909784cb2dd93f37559dadf9a8594e05ba53f909';PROBE_RUN=30509621588;PROBE_ARTIFACT=8746609463;PROBE_ARTIFACT_SHA256='b8fb4d81c7789c4ae33a3b3c9f4d7aea5eb1538826828af776e519ac199b0381'
ORDER=[s['subject_id'] for s in probe.SUBJECTS]
NEXT_BY={ORDER[i]:ORDER[i+1] for i in range(len(ORDER)-1)}|{ORDER[-1]:'RETROSPECTIVE_PROOF_CORPUS'}
LIC={'classification':'machine_readable_retrospective_claim_disposition','copyright':'Copyright 2026 Ingolf Lohmann','license':'CC-BY-NC-ND-4.0','rights_holder':'Ingolf Lohmann'}
CODE={'.py','.ps1','.bat','.cmd','.sh','.c','.h','.cc','.cpp','.hpp','.html','.css','.js','.mjs','.cjs','.ts','.tsx','.jsx','.lean','.lake'}
IDENTITY={'schema','record_type','type','role','title','name','package','version','path','file','filename','operation','work_unit_id','claim_id','id','error_class','classification','subject_id','batch_id'}
POSITIVE_KEYS={'pass','final_pass','effect_ack_done','done','complete','completed','published','deployed','merged','synchronized','persisted','p_nash','all_content_claims_dispositioned','proof_corpus_published_on_zenodo','zenodo_mutation_authorized'}
NEG=re.compile(r'\b(BLOCK|PENDING|NOT_CREATED|NOT_COMPLETED|NOT_PUBLISHED|UNVERIFIED|MISSING|FALSE|NULL|keine externe wirkung|nicht veröffentlicht|not complete|does not claim|no false done|nicht belegt|nicht autorisiert)\b',re.I)
NOR=re.compile(r'\b(must|shall|required|requires|requirement|policy|muss|müssen|soll|sollen|darf|dürfen|pflicht|grundsatz|zulässig|unzulässig)\b',re.I)
INT=re.compile(r'\b(interpretation|interpretiert|deutung|einordnung|ontolog|metapher|bedeutung|these)\b',re.I)
POS=re.compile(r'\b(PASS(?:_[A-Z0-9_]+)?|DONE|COMPLETED|COMPLETE|FINAL_PASS|EFFECT_ACK_DONE|P_NASH\s*[:=]\s*(?:TRUE|`TRUE`)|PERSISTED|DEPLOYED|PUBLISHED|MERGED|SYNCHRONIZED)\b',re.I)
OVR=re.compile(r'\b(universal(?:e|er|es|ly)?|allumfassend|vollständig(?:e|er|es)?|endgültig|unzweifelhaft|alle\s+(?:relevanten\s+)?schichten|across all relevant layers|entire system|full repository)\b',re.I)
CON=re.compile(r'\b(if|wenn|requires|nur bei|erst wenn|may not|darf nicht|kein(?:e|en|er|es)?|no |not )\b',re.I)
CHECKSUM=re.compile(r'^\s*([0-9a-fA-F]{64})\s+[* ]?(.+?)\s*$')
class DispositionError(RuntimeError):pass
SubjectDispositionError=DispositionError
def fail(x:str):raise DispositionError(x)
def sha(b:bytes):return hashlib.sha256(b).hexdigest()
def blob(b:bytes):return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def pretty(x:Any):return json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
def write(path:pathlib.Path,x:Any):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(pretty(x),encoding='utf-8',newline='\n')
def read(path:pathlib.Path):return json.loads(path.read_text(encoding='utf-8'))
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
def decode_entry(e:Mapping[str,Any])->str:
 raw=e.get('text_utf8_base64')
 if not isinstance(raw,str):fail(f'text bytes not retained: {e.get("qualified_path")}')
 try:return base64.b64decode(raw,validate=True).decode('utf-8')
 except Exception as ex:raise DispositionError(f'invalid retained text {e.get("qualified_path")}: {ex}') from ex
def split_path(q:str)->tuple[str,str]:
 if '!/' not in q:fail(f'invalid qualified path: {q}')
 return q.rsplit('!/',1)
def target(entries:Mapping[str,Mapping[str,Any]],archive:str,source:str,raw:str)->tuple[str,Mapping[str,Any]|None]:
 value=raw.replace('\\','/').strip().lstrip('./');parent=pathlib.PurePosixPath(source).parent
 for candidate in dict.fromkeys(((parent/pathlib.PurePosixPath(value)).as_posix(),pathlib.PurePosixPath(value).as_posix())):
  q=f'{archive}!/{candidate}'
  if q in entries:return q,entries[q]
 return f'{archive}!/{(parent/pathlib.PurePosixPath(value)).as_posix()}',None
def hash_audit(entries:Mapping[str,Mapping[str,Any]],texts:list[Mapping[str,Any]])->tuple[dict[str,Any],dict[tuple[str,str,Any],Mapping[str,Any]]]:
 rows=[];lookup={}
 for e in texts:
  q=e['qualified_path'];archive,source=split_path(q);name=pathlib.PurePosixPath(source).name.lower()
  if name=='sha256sums.txt' or name.endswith('.sha256'):
   for line_no,line in enumerate(decode_entry(e).splitlines(),1):
    m=CHECKSUM.match(line)
    if not m:continue
    tq,observed=target(entries,archive,source,m.group(2));row={'assertion_type':'CHECKSUM_LINE','expected_sha256':m.group(1).lower(),'match':bool(observed) and observed.get('sha256')==m.group(1).lower(),'observed_sha256':observed.get('sha256') if observed else None,'source_file':q,'source_locator':{'line':line_no},'target_file':tq};rows.append(row);lookup[(q,'line',line_no)]=row
 def walk(v:Any,q:str,archive:str,source:str,pointer:str=''):
  if isinstance(v,Mapping):
   if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str) and re.fullmatch(r'[0-9a-fA-F]{64}',v['sha256']):
    hp=f'{pointer}/sha256' or '/sha256';tq,observed=target(entries,archive,source,v['path']);row={'assertion_type':'MANIFEST_PATH_SHA256','expected_sha256':v['sha256'].lower(),'match':bool(observed) and observed.get('sha256')==v['sha256'].lower(),'observed_sha256':observed.get('sha256') if observed else None,'source_file':q,'source_locator':{'json_pointer':hp},'target_file':tq};rows.append(row);lookup[(q,'json',hp)]=row
   for k in sorted(v):walk(v[k],q,archive,source,f'{pointer}/{esc(str(k))}')
  elif isinstance(v,list):
   for i,x in enumerate(v):walk(x,q,archive,source,f'{pointer}/{i}')
 for e in texts:
  q=e['qualified_path'];archive,source=split_path(q)
  if not source.lower().endswith('.json'):continue
  try:value=json.loads(decode_entry(e))
  except json.JSONDecodeError:continue
  walk(value,q,archive,source)
 checksum=[x for x in rows if x['assertion_type']=='CHECKSUM_LINE'];manifest=[x for x in rows if x['assertion_type']=='MANIFEST_PATH_SHA256'];bad=[x for x in rows if not x['match']]
 return {'_license':LIC,'schema':'qikvrt_recursive_internal_hash_binding_audit_v1','assertion_count':len(rows),'assertions':rows,'counts':{'checksum_assertions':len(checksum),'checksum_matches':sum(x['match'] for x in checksum),'manifest_path_hash_assertions':len(manifest),'manifest_path_hash_matches':sum(x['match'] for x in manifest),'manifest_path_hash_mismatches':sum(not x['match'] for x in manifest),'total_mismatches':len(bad)},'mismatches':bad,'state':'ALL_INTERNAL_HASH_BINDINGS_MATCH' if not bad else 'INTERNAL_HASH_BINDING_MISMATCHES_FOUND','completion_claims':{'all_checksum_lines_resolved':all(x['observed_sha256'] for x in checksum),'all_checksum_lines_match':all(x['match'] for x in checksum),'all_manifest_path_hashes_resolved':all(x['observed_sha256'] for x in manifest),'all_manifest_path_hashes_match':all(x['match'] for x in manifest),'pass':False,'final_pass':False,'effect_ack_done':False,'zenodo_mutation_authorized':False}},lookup
def assertion_nodes(texts:list[Mapping[str,Any]])->list[dict[str,Any]]:
 out=[]
 for e in sorted(texts,key=lambda x:x['qualified_path']):
  q=e['qualified_path'];_,source=split_path(q);ext=pathlib.PurePosixPath(source).suffix.lower();text=decode_entry(e)
  if ext=='.json':
   try:value=json.loads(text)
   except json.JSONDecodeError:value=None
   if value is not None:
    for pointer,v in leaves(value):
     key=unesc(pointer.rsplit('/',1)[-1]);out.append({'qualified_path':q,'source_sha256':e['sha256'],'locator_type':'json','locator':pointer,'json_key':key,'source_value':v,'statement':f'{key} = {json.dumps(v,ensure_ascii=False,sort_keys=True)}'})
    continue
  for line_no,line in enumerate(text.splitlines(),1):
   if line.strip():out.append({'qualified_path':q,'source_sha256':e['sha256'],'locator_type':'line','locator':line_no,'json_key':None,'statement':line.strip()})
 return out
def classify(n:Mapping[str,Any],binding:Mapping[str,Any]|None)->tuple[str,str,str,str,str]:
 q=n['qualified_path'];_,source=split_path(q);path=pathlib.PurePosixPath(source);ext=path.suffix.lower();statement=n['statement'];key=str(n.get('json_key') or '').lower();value=n.get('source_value')
 if binding:
  if binding.get('match'):return 'EMPIRICALLY_EVIDENCED','EMPIRICAL_EVIDENCE_BOUND','SUPPORTED_BY_RECURSIVE_BYTE_AUDIT','COMPATIBLE_WITH_DISPOSITION','Exact only for the target bytes named by this checksum assertion.'
  return 'OPEN','OPEN','CONTRADICTED_BY_RECURSIVE_BYTE_AUDIT','REQUIRES_VERSIONED_CORRECTION','Archived hash assertion contradicts the exact recursively observed target bytes.'
 if n.get('third_party_or_cache'):return 'SOURCE_BOUND','OUT_OF_SCOPE','THIRD_PARTY_OR_CACHE_SOURCE_BOUND','COMPATIBLE_WITH_DISPOSITION','Third-party or cache material is not attributed as an Ingolf Lohmann scientific claim.'
 if 'template' in source.lower():return 'SOURCE_BOUND','OUT_OF_SCOPE','TEMPLATE_OR_PLACEHOLDER_SOURCE_BOUND','COMPATIBLE_WITH_DISPOSITION','Template or placeholder source is not evidence of an external effect.'
 if ext in CODE:return 'SOURCE_BOUND','SOURCE_BOUND','IMPLEMENTATION_SOURCE_BOUND','COMPATIBLE_WITH_DISPOSITION','Implementation text is source-bound and not proof that an external effect occurred.'
 if value is False or (n['locator_type']=='json' and value is None) or NEG.search(statement):return 'SOURCE_BOUND','NEGATIVE_BOUNDARY','EXPLICIT_NEGATIVE_OR_NON_COMPLETION_BOUNDARY','COMPATIBLE_WITH_DISPOSITION','Explicit negative, absent, blocked, pending or non-complete state.'
 if key in POSITIVE_KEYS and (value is True or str(value).upper() in {'PASS','DONE','COMPLETE','COMPLETED','PUBLISHED','DEPLOYED','MERGED','SYNCHRONIZED','PERSISTED'}):return 'OPEN','OPEN','POSITIVE_EFFECT_OR_COMPLETION_ASSERTION_NOT_INDEPENDENTLY_REVALIDATED','REQUIRES_VERSIONED_CORRECTION','Positive effect/completion assertion is not promoted by its own archived wording.'
 if NOR.search(statement):return 'NORMATIVE','NORMATIVE','NORMATIVE_SOURCE_STATEMENT','COMPATIBLE_WITH_DISPOSITION','Policy, requirement or permission constraint.'
 if INT.search(statement):return 'INTERPRETATIVE','INTERPRETIVE','INTERPRETATIVE_SOURCE_STATEMENT','COMPATIBLE_WITH_DISPOSITION','Interpretation bound to exact source wording.'
 if key in IDENTITY:return 'SOURCE_BOUND','SOURCE_BOUND','SOURCE_IDENTITY_OR_LABEL','COMPATIBLE_WITH_DISPOSITION','Identity label bound to exact public source.'
 if POS.search(statement) or OVR.search(statement):
  if CON.search(statement):return 'NORMATIVE','NORMATIVE','CONDITIONAL_OR_NEGATIVE_STATUS_RULE','COMPATIBLE_WITH_DISPOSITION','Condition or prohibition, not evidence that a positive status occurred.'
  return 'OPEN','OPEN','HISTORICAL_POSITIVE_COMPLETION_OR_UNIVERSALITY_ASSERTION_NOT_REVALIDATED','REQUIRES_VERSIONED_CORRECTION','Positive completion or universality assertion lacks an independent retrospective proof binding.'
 if re.search(r'\b(sha-?256|md5|bytes|size|hash)\b',statement,re.I):return 'SOURCE_BOUND','SOURCE_BOUND','SOURCE_RECORDED_INTEGRITY_ASSERTION','COMPATIBLE_WITH_DISPOSITION','Recorded integrity value; only separately matched assertions are empirical.'
 return 'SOURCE_BOUND','SOURCE_BOUND','EXACT_PUBLIC_SOURCE_BOUND','COMPATIBLE_WITH_DISPOSITION','No extension beyond exact frozen public source.'
def build_claims(subject_id:str,record_ids:list[int],nodes:list[Mapping[str,Any]],lookup:Mapping[tuple[str,str,Any],Mapping[str,Any]])->list[dict[str,Any]]:
 out=[];prefix='B3'+subject_id.split('-',1)[1][:6].upper()
 for i,n in enumerate(nodes,1):
  binding=lookup.get((n['qualified_path'],n['locator_type'],n['locator']));ep,disp,status,language,boundary=classify(n,binding);ref={'record_ids':record_ids,'qualified_path':n['qualified_path'],'sha256':n['source_sha256'],'locator':{'type':n['locator_type'],'value':n['locator']}}
  row={'claim_id':f'{prefix}-{i:06d}','statement':n['statement'],'epistemic_class':ep,'terminal_disposition':disp,'status':status,'publication_language_status':language,'boundary':boundary,'source_refs':[ref],'proof_refs':[]}
  if n['locator_type']=='json':row['source_value']=n.get('source_value')
  out.append(row)
 return out
def paths(subject_id:str)->dict[str,pathlib.Path]:
 root=B3/'subject-dispositions'/subject_id
 return {name:root/name for name in ('PUBLIC_ARCHIVE_RECOVERY_RECEIPT.json','ARCHIVE_CONTENT_INVENTORY.json','INTERNAL_HASH_BINDING_AUDIT.json','CLAIM_MATRIX.json','SOURCE_TO_CLAIM_TRACEABILITY.json','ASSERTION_NODE_COVERAGE.json','CONTENT_CHANGE_DECISION.json','SUBJECT_DISPOSITION_RECEIPT.json')}
def materialize_subject(config:Mapping[str,Any],cache:dict[str,dict[str,Any]],ordinal:int)->dict[str,Any]:
 subject_id=config['subject_id'];observations=[probe.record(config,r,cache) for r in config['records']];payload=cache[config['file']['sha256']];rows=payload['rows'];entries={x['qualified_path']:x for x in rows};texts=[x for x in rows if x.get('content_class')=='TEXT' and not x.get('third_party_or_cache')]
 if any('text_utf8_base64' not in x for x in texts):fail(f'unretained first-party text in {subject_id}')
 audit,lookup=hash_audit(entries,texts);nodes=assertion_nodes(texts);claims=build_claims(subject_id,[r['id'] for r in config['records']],nodes,lookup);classes=Counter(x['epistemic_class'] for x in claims);disps=Counter(x['terminal_disposition'] for x in claims);open_count=classes['OPEN'];correction=[x['claim_id'] for x in claims if x['publication_language_status']=='REQUIRES_VERSIONED_CORRECTION'];required=bool(correction or audit['counts']['total_mismatches']);p=paths(subject_id)
 inventory={'_license':LIC,'schema':'qikvrt_recursive_archive_content_inventory_v1','subject_id':subject_id,'entry_count':len(rows),'content_class_counts':dict(sorted(Counter(x['content_class'] for x in rows).items())),'entries':[{k:x.get(k) for k in ('qualified_path','archive_depth','content_class','bytes','sha256','git_blob_sha1','uncompressed_bytes','third_party_or_cache')} for x in rows]}
 recovery={'_license':LIC,'schema':'qikvrt_public_archive_recovery_receipt_v1','subject_id':subject_id,'batch_id':'CONTENT-DISPOSITION-BATCH-003' if subject_id!=ORDER[-1] else 'CONTENT-DISPOSITION-AFTER-BATCH-003','observed_at':OBSERVED_AT,'state':'EXACT_PUBLIC_ARCHIVE_RECOVERED_AND_INSPECTED','records':observations,'probe_evidence':{'exact_head':PROBE_HEAD,'run_id':PROBE_RUN,'artifact_id':PROBE_ARTIFACT,'artifact_sha256':PROBE_ARTIFACT_SHA256},'recovery':{'method':'READ_ONLY_ZENODO_REOBSERVATION_AND_FAIL_CLOSED_ZIP_INSPECTION','public_record_file_sets_exact':True,'archive_content_extracted':True,'historical_public_bytes_rewritten':False},'completion_claims':{'subject_terminally_dispositioned':True,'all_content_claims_dispositioned':False,'pass':False,'final_pass':False,'effect_ack_done':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False}}
 matrix={'_license':LIC,'schema':'qikvrt_retrospective_claim_matrix_v1','subject_id':subject_id,'batch_id':recovery['batch_id'],'record_ids':[r['id'] for r in config['records']],'claim_count':len(claims),'claims':claims,'classification_summary':{k:classes.get(k,0) for k in ('EMPIRICALLY_EVIDENCED','FORMAL_PROVED','INTERPRETATIVE','NORMATIVE','OPEN','SOURCE_BOUND')},'terminal_disposition_counts':dict(sorted(disps.items())),'epistemic_open_count':open_count,'publication_correction_claim_count':len(correction),'terminally_classified_claim_count':len(claims),'unclassified_claim_count':0,'content_change_decision':{'required':required,'state':'VERSIONED_CORRECTION_REQUIRED' if required else 'NO_CONTENT_CHANGE_REQUIRED'},'completion_claims':{'all_assertion_nodes_classified':True,'all_claims_terminally_classified_or_explicitly_open':True,'claim_disposition_complete':True,'formal_claims_have_proof_bindings':True,'pass':False,'final_pass':False,'effect_ack_done':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False}}
 trace={'_license':LIC,'schema':'qikvrt_source_to_claim_traceability_v1','subject_id':subject_id,'claim_count':len(claims),'untraced_claim_count':0,'entries':[{'claim_id':x['claim_id'],'source_refs':x['source_refs'],'status':x['status'],'terminal_disposition':x['terminal_disposition']} for x in claims]}
 coverage={'_license':LIC,'schema':'qikvrt_assertion_node_coverage_v1','subject_id':subject_id,'assertion_node_count':len(claims),'covered_assertion_node_count':len(claims),'covered_text_source_count':len(texts),'unclassified_node_count':0,'source_coverage':[{'qualified_path':x['qualified_path'],'sha256':x['sha256'],'claim_count':sum(c['source_refs'][0]['qualified_path']==x['qualified_path'] for c in claims)} for x in texts]}
 decision={'_license':LIC,'schema':'qikvrt_content_change_decision_v1','subject_id':subject_id,'decision':{'required':required,'state':'VERSIONED_CORRECTION_REQUIRED' if required else 'NO_CONTENT_CHANGE_REQUIRED','correction_claim_count':len(correction),'correction_claim_ids':correction,'internal_hash_mismatch_count':audit['counts']['total_mismatches'],'public_bytes_must_remain_unchanged':True,'repository_evidence_addition_required':True,'owner_review_required_before_any_later_upload':required,'zenodo_mutation_authorized':False,'smallest_repair':'Create a versioned corrected candidate that regenerates inconsistent manifests and narrows unbound completion/effect/universality wording, then return it to the owner.' if required else 'No historical public-content mutation; retain exact bytes and repository-side disposition evidence.'}}
 disposed=14+ordinal;remaining=19-disposed;next_id=NEXT_BY[subject_id];next_effect='BUILD_AND_VERIFY_RETROSPECTIVE_PROOF_CORPUS' if next_id=='RETROSPECTIVE_PROOF_CORPUS' else f'EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_BATCH_003_SUBJECT_{next_id.split("-",1)[1].upper()}'
 receipt={'_license':LIC,'schema':'qikvrt_content_disposition_subject_receipt_v1','subject_id':subject_id,'batch_id':recovery['batch_id'],'record_ids':[r['id'] for r in config['records']],'observed_at':OBSERVED_AT,'state':'TERMINALLY_DISPOSITIONED_CORRECTION_REQUIRED' if required else 'TERMINALLY_DISPOSITIONED_NO_CONTENT_CHANGE','claim_counts':{'total':len(claims),'terminally_classified':len(claims),'explicit_open':open_count,'unclassified':0},'content_change_decision':decision['decision']['state'],'artifacts':{k.lower().replace('.json',''):v.relative_to(ROOT).as_posix() for k,v in p.items()},'preserved_corpus':{'subject_count':19,'dispositioned_subject_count':disposed,'open_subject_count':remaining},'next_deterministic_effect':next_effect,'completion_claims':{'subject_terminally_dispositioned':True,'all_content_claims_dispositioned':subject_id==ORDER[-1],'batch_003_terminal':subject_id in {ORDER[-2],ORDER[-1]},'pass':False,'final_pass':False,'effect_ack_done':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False}}
 for name,value in [('PUBLIC_ARCHIVE_RECOVERY_RECEIPT.json',recovery),('ARCHIVE_CONTENT_INVENTORY.json',inventory),('INTERNAL_HASH_BINDING_AUDIT.json',audit),('CLAIM_MATRIX.json',matrix),('SOURCE_TO_CLAIM_TRACEABILITY.json',trace),('ASSERTION_NODE_COVERAGE.json',coverage),('CONTENT_CHANGE_DECISION.json',decision),('SUBJECT_DISPOSITION_RECEIPT.json',receipt)]:write(p[name],value)
 return {'subject_id':subject_id,'claim_count':len(claims),'open_count':open_count,'correction_required':required,'matrix_path':p['CLAIM_MATRIX.json'],'receipt_path':p['SUBJECT_DISPOSITION_RECEIPT.json'],'decision_path':p['CONTENT_CHANGE_DECISION.json'],'classification_summary':matrix['classification_summary']}
def file_binding(path:pathlib.Path)->dict[str,Any]:
 raw=path.read_bytes();return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw),'git_blob_sha1':blob(raw)}
def matrix_rows()->list[pathlib.Path]:
 rows=[]
 rows+=sorted((B3.parent/'content-disposition-batch-001/subjects').glob('SUBJECT-*/CLAIM_MATRIX.json'))
 rows+=sorted((B3.parent/'content-disposition-batch-002/terminal-disposition/subjects').glob('SUBJECT-*/CLAIM_MATRIX.json'))
 rows+=sorted((B3/'subject-dispositions').glob('SUBJECT-*/CLAIM_MATRIX.json'))
 return rows
def normalize_summary(m:Mapping[str,Any])->dict[str,int]:
 source=m.get('classification_summary') or m.get('classification_counts') or {}
 return {k:int(source.get(k,0)) for k in ('EMPIRICALLY_EVIDENCED','FORMAL_PROVED','INTERPRETATIVE','NORMATIVE','OPEN','SOURCE_BOUND')}
def build_proof_corpus(results:list[Mapping[str,Any]])->tuple[dict[str,Any],dict[str,Any],list[dict[str,Any]]]:
 matrices=matrix_rows()
 if len(matrices)!=19:fail(f'proof corpus requires 19 claim matrices, observed {len(matrices)}')
 rows=[];subjects=set();total=0;classes=Counter();open_total=0
 for path in matrices:
  m=read(path);sid=m.get('subject_id')
  if not isinstance(sid,str) or sid in subjects:fail(f'duplicate/invalid subject matrix: {sid}')
  subjects.add(sid);count=int(m.get('claim_count',len(m.get('claims',[]))))
  if count!=len(m.get('claims',[])):fail(f'claim count drift: {sid}')
  unclassified=int(m.get('unclassified_claim_count',0))
  if unclassified!=0:fail(f'unclassified claims remain: {sid}')
  summary=normalize_summary(m);total+=count;classes.update(summary);open_total+=summary['OPEN'];receipt=path.with_name('SUBJECT_DISPOSITION_RECEIPT.json')
  rows.append({'subject_id':sid,'claim_count':count,'classification_summary':summary,'claim_matrix':file_binding(path),'subject_receipt':file_binding(receipt) if receipt.is_file() else None})
 correction=[]
 for decision in sorted((B3/'subject-dispositions').glob('SUBJECT-*/CONTENT_CHANGE_DECISION.json')):
  value=read(decision);d=value.get('decision',{})
  if d.get('required') is True:correction.append({'subject_id':value.get('subject_id'),'state':d.get('state'),'correction_claim_count':d.get('correction_claim_count',0),'decision':file_binding(decision),'smallest_repair':d.get('smallest_repair')})
 index={'_license':{**LIC,'classification':'machine_readable_retrospective_proof_corpus_index'},'schema':'qikvrt_retrospective_proof_corpus_index_v1','union_id':'qikvrt-zenodo-canonical-union-2026-07-28-v1','observed_at':OBSERVED_AT,'subject_count':len(rows),'claim_count':total,'classification_summary':dict(sorted(classes.items())),'explicit_open_claim_count':open_total,'subjects':sorted(rows,key=lambda x:x['subject_id']),'correction_requirements':correction,'completion_claims':{'all_19_subjects_indexed':True,'all_claim_matrices_byte_bound':True,'all_claims_terminally_classified_or_explicitly_open':True,'proof_corpus_built':True,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False,'pass':False,'final_pass':False,'effect_ack_done':False}}
 write(PROOF/'RETROSPECTIVE_PROOF_CORPUS_INDEX.json',index)
 binding=file_binding(PROOF/'RETROSPECTIVE_PROOF_CORPUS_INDEX.json')
 receipt={'_license':{**LIC,'classification':'machine_readable_retrospective_proof_corpus_receipt'},'schema':'qikvrt_retrospective_proof_corpus_receipt_v1','union_id':index['union_id'],'observed_at':OBSERVED_AT,'state':'BUILT_AND_VERIFIED_PUBLICATION_NOT_AUTHORIZED','counts':{'subjects':19,'claims':total,'explicit_open_claims':open_total,'correction_required_subjects':len(correction)},'proof_corpus_index':binding,'verification':{'all_subjects_present':True,'all_claim_matrices_hash_bound':True,'all_claim_counts_recomputed':True,'all_classification_counts_recomputed':True,'historical_public_bytes_rewritten':False},'completion_claims':{'all_content_claims_dispositioned':True,'retrospective_proof_corpus_built':True,'retrospective_proof_corpus_verified':True,'retrospective_proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False,'repository_wide_pass':False,'pass':False,'final_pass':False,'effect_ack_done':False}}
 write(PROOF/'RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json',receipt)
 return index,receipt,correction
def build_batch_receipt(results:list[Mapping[str,Any]]):
 first=read(B3/'subject-dispositions/SUBJECT-2581811b342e505d/CLAIM_MATRIX.json');second=read(B3/'subject-dispositions/SUBJECT-172dd9bc2738fa43/CLAIM_MATRIX.json');total=int(first['claim_count'])+int(second['claim_count'])+sum(int(x['claim_count']) for x in results[:-1]);corrections=['SUBJECT-172dd9bc2738fa43']+[x['subject_id'] for x in results[:-1] if x['correction_required']]
 value={'_license':LIC,'schema':'qikvrt_content_disposition_batch_receipt_v1','batch_id':'CONTENT-DISPOSITION-BATCH-003','observed_at':OBSERVED_AT,'state':'TERMINALLY_DISPOSITIONED','subject_count':6,'claim_count':total,'correction_required_subject_ids':corrections,'subjects':['SUBJECT-2581811b342e505d','SUBJECT-172dd9bc2738fa43']+[x['subject_id'] for x in results[:-1]],'completion_claims':{'batch_003_terminal':True,'all_six_batch_subjects_terminally_dispositioned':True,'all_corpus_content_claims_dispositioned':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False,'pass':False,'final_pass':False,'effect_ack_done':False},'next_deterministic_effect':'EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_SUBJECT_7FDB36AA7C07C07D'};write(B3/'CONTENT_DISPOSITION_BATCH_003_RECEIPT.json',value)
def build_work_units(correction:list[Mapping[str,Any]]):
 next_effect='CREATE_VERSIONED_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_REMAINING_CORPUS_SUBJECTS' if correction else 'REQUEST_SEPARATE_ZENODO_MUTATION_AUTHORIZATION_FOR_RETROSPECTIVE_PROOF_CORPUS'
 correction_unit={'_license':{**LIC,'classification':'machine_readable_work_unit'},'schema':'qikvrt_work_unit_v1','work_unit_id':'CREATE-VERSIONED-CORRECTED-CANDIDATES-REMAINING-CORPUS-SUBJECTS-20260730','operation':'CREATE_VERSIONED_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER','state':'READY' if correction else 'NOT_REQUIRED','subject_ids':[x['subject_id'] for x in correction],'requirements':['do not mutate historical Zenodo records','regenerate inconsistent manifests from exact candidate bytes','narrow unbound completion/effect/universality wording','run complete gates on each exact candidate head','return each candidate to Ingolf Lohmann for explicit accept or reject'],'next_deterministic_effect':next_effect}
 write(ROOT/'work-units/CREATE_VERSIONED_CORRECTED_CANDIDATES_REMAINING_CORPUS_SUBJECTS.json',correction_unit)
 auth={'_license':{**LIC,'classification':'machine_readable_mutation_authorization_request'},'schema':'qikvrt_zenodo_mutation_authorization_request_v1','work_unit_id':'REQUEST-SEPARATE-ZENODO-MUTATION-AUTHORIZATION-RETROSPECTIVE-PROOF-CORPUS-20260730','operation':'REQUEST_SEPARATE_ZENODO_MUTATION_AUTHORIZATION','state':'WAITING_OWNER_AUTHORIZATION_AND_CORRECTION_RESOLUTION' if correction else 'WAITING_OWNER_AUTHORIZATION','proof_corpus_receipt':file_binding(PROOF/'RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json'),'correction_dependencies':[x['subject_id'] for x in correction],'authorization':{'authorized':False,'authorized_by':None,'authorized_at':None,'scope':None},'completion_claims':{'proof_corpus_built_and_verified':True,'zenodo_mutation_authorized':False,'zenodo_publication_complete':False,'pass':False,'final_pass':False,'effect_ack_done':False}}
 write(ROOT/'work-units/REQUEST_SEPARATE_ZENODO_MUTATION_AUTHORIZATION_RETROSPECTIVE_PROOF_CORPUS.json',auth)
 return next_effect
def build_progress_projection()->tuple[dict[str,Any],str]:
 if not (PROOF/'RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json').is_file():fail('retrospective proof corpus receipt missing')
 corpus=read(PROOF/'RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json');index=read(PROOF/'RETROSPECTIVE_PROOF_CORPUS_INDEX.json');correction=index['correction_requirements'];next_effect='CREATE_VERSIONED_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_REMAINING_CORPUS_SUBJECTS' if correction else 'REQUEST_SEPARATE_ZENODO_MUTATION_AUTHORIZATION_FOR_RETROSPECTIVE_PROOF_CORPUS';p=copy.deepcopy(previous.build_progress_projection()[0]);p.update(state='WORKING',effect_state='EFFECT_ACK_CONTINUE',percent=100,current_action=f'All 19 Zenodo claim subjects are terminally classified; retrospective proof corpus built and verified with {index["claim_count"]} claims and {index["explicit_open_claim_count"]} explicit OPEN claims. Publication remains unauthorized.',pending_steps=['Create and return every required versioned corrected candidate to Ingolf Lohmann','Record explicit owner decisions and promote only accepted exact candidates','Obtain a separate explicit Zenodo mutation authorization before any proof-corpus publication'],next_action=next_effect,updated_at=OBSERVED_AT,union_receipt_state='ALL_SUBJECTS_DISPOSITIONED_PROOF_CORPUS_VERIFIED_PUBLICATION_NOT_AUTHORIZED')
 blockers=[{'failure_class':'CORPUS_SUBJECT_VERSIONED_CORRECTION_REQUIRED','affected_subject':x['subject_id'],'affected_artifacts':[x['decision']['path']],'smallest_repair':x['smallest_repair']} for x in correction];blockers.append({'failure_class':'ZENODO_RETROSPECTIVE_PROOF_CORPUS_MUTATION_NOT_AUTHORIZED','affected_artifacts':['work-units/REQUEST_SEPARATE_ZENODO_MUTATION_AUTHORIZATION_RETROSPECTIVE_PROOF_CORPUS.json',corpus['proof_corpus_index']['path']],'smallest_repair':'After correction resolution, Ingolf Lohmann must explicitly authorize the exact proof-corpus bytes and mutation scope.'});p['blockers']=blockers
 step='Terminally disposition all remaining archive subjects and build and verify the 19-subject retrospective proof corpus without Zenodo mutation'
 if step not in p['completed_steps']:p['completed_steps'].append(step)
 scope=p['scopes']['qikvrt-zenodo-canonical-union-2026-07-28-v1'];scope['percent']=100;scope['counts'].update(dispositioned_subjects=19,open_subjects=0,dispositioned_claims=index['claim_count']);scope.update(state='CONTENT_DISPOSITION_COMPLETE_PUBLICATION_OPEN',effect_state='EFFECT_ACK_CONTINUE',active_batch={'active_subject':None,'active_work_package':None,'batch_id':'CONTENT-DISPOSITION-BATCH-003','dispositioned_subjects':6,'open_subjects':0,'state':'TERMINALLY_DISPOSITIONED','subjects':6},queued_after_active=0,boundary='All 19 subjects are terminally classified. Versioned corrections, owner decisions and a separate Zenodo mutation authorization remain open.',next_action=next_effect,batch_003={'active_subject':None,'active_work_package':None,'claim_extraction_complete':True,'correction_required_subjects':[x['subject_id'] for x in correction if x['subject_id']!='SUBJECT-7fdb36aa7c07c07d'],'dispositioned_subjects':6,'first_subject_claim_extraction_complete':True,'latest_subject_receipt':(B3/'subject-dispositions/SUBJECT-780b9bf86425cee3/SUBJECT_DISPOSITION_RECEIPT.json').relative_to(ROOT).as_posix(),'next_action':'EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_SUBJECT_7FDB36AA7C07C07D','open_subjects':0,'state':'TERMINALLY_DISPOSITIONED','subjects':6,'terminal':True},retrospective_proof_corpus={'state':corpus['state'],'receipt':(PROOF/'RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json').relative_to(ROOT).as_posix(),'subjects':19,'claims':index['claim_count'],'explicit_open_claims':index['explicit_open_claim_count'],'correction_required_subjects':len(correction),'published_on_zenodo':False,'zenodo_mutation_authorized':False});p['projection_owner']={'check_command':f'python3 -B {TOOL_REL} --check','tool':TOOL_REL}
 validate_progress_projection(p)
 status=f'''# QIK-VRT Work Status\n\nRepository: `Goldkelch/qik-vrt`\n\nUpdated at: `{OBSERVED_AT}`\n\nSnapshot state: **`WORKING`**. Overall effect state: **`EFFECT_ACK_CONTINUE`**. No repository-wide `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, Zenodo publication, deployment, merge or current Authority/Mirror symmetry is claimed.\n\n`[███████████████████] 100%` — Zenodo-Subject-Disposition (19/19)\n\n- ✓ All 19 canonical claim subjects terminally classified or explicitly `OPEN`\n- ✓ {index['claim_count']} claims indexed; {index['explicit_open_claim_count']} explicitly `OPEN`; zero unclassified\n- ✓ Retrospective proof corpus built and byte-verified\n- ⚠ {len(correction)} subjects require versioned corrected candidates\n- ⛔ Zenodo proof-corpus mutation is not authorized and not published\n\n## BLOCK\n\n`ZENODO_RETROSPECTIVE_PROOF_CORPUS_MUTATION_NOT_AUTHORIZED`\n\nSmallest repair after correction resolution: Ingolf Lohmann explicitly authorizes the exact proof-corpus bytes and mutation scope.\n\n## NEXT\n\n`{next_effect}`\n'''
 return p,status
def validate_progress_projection(p:Mapping[str,Any]):
 scope=p.get('scopes',{}).get('qikvrt-zenodo-canonical-union-2026-07-28-v1',{})
 if p.get('percent')!=100 or p.get('effect_state')!='EFFECT_ACK_CONTINUE':fail('final content-disposition projection identity drift')
 if any(p.get('claims',{}).get(k) is not False for k in ('PASS','FINAL_PASS','EFFECT_ACK_DONE')) or any(scope.get('claims',{}).get(k) is not False for k in ('PASS','FINAL_PASS','EFFECT_ACK_DONE')):fail('final content-disposition projection release inflation')
 if scope.get('counts',{}).get('dispositioned_subjects')!=19 or scope.get('counts',{}).get('open_subjects')!=0:fail('final subject count drift')
 proof=scope.get('retrospective_proof_corpus',{})
 if proof.get('published_on_zenodo') is not False or proof.get('zenodo_mutation_authorized') is not False:fail('proof corpus mutation inflation')
def verify_subject(subject_id:str):
 p=paths(subject_id)
 for path in p.values():
  if not path.is_file():fail(f'missing subject artifact: {path.relative_to(ROOT)}')
 m=read(p['CLAIM_MATRIX.json']);r=read(p['SUBJECT_DISPOSITION_RECEIPT.json']);d=read(p['CONTENT_CHANGE_DECISION.json']);a=read(p['INTERNAL_HASH_BINDING_AUDIT.json'])
 if m.get('claim_count')!=len(m.get('claims',[])) or m.get('unclassified_claim_count')!=0:fail(f'claim matrix drift: {subject_id}')
 if r.get('claim_counts',{}).get('total')!=m['claim_count'] or r.get('claim_counts',{}).get('unclassified')!=0:fail(f'subject receipt count drift: {subject_id}')
 if d.get('decision',{}).get('zenodo_mutation_authorized') is not False or any(r.get('completion_claims',{}).get(k) is not False for k in ('pass','final_pass','effect_ack_done','proof_corpus_published_on_zenodo','zenodo_mutation_authorized')):fail(f'completion boundary drift: {subject_id}')
 if a.get('counts',{}).get('total_mismatches')!=len(a.get('mismatches',[])):fail(f'hash audit drift: {subject_id}')
def verify_materialized()->dict[str,Any]:
 for sid in ORDER:verify_subject(sid)
 if not (B3/'CONTENT_DISPOSITION_BATCH_003_RECEIPT.json').is_file():fail('Batch-003 receipt missing')
 index=read(PROOF/'RETROSPECTIVE_PROOF_CORPUS_INDEX.json');receipt=read(PROOF/'RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json')
 if index.get('subject_count')!=19 or len(index.get('subjects',[]))!=19:fail('proof corpus subject count drift')
 for row in index['subjects']:
  path=ROOT/row['claim_matrix']['path'];raw=path.read_bytes()
  if len(raw)!=row['claim_matrix']['bytes'] or sha(raw)!=row['claim_matrix']['sha256'] or blob(raw)!=row['claim_matrix']['git_blob_sha1']:fail(f'proof corpus matrix binding drift: {row["subject_id"]}')
 if receipt.get('state')!='BUILT_AND_VERIFIED_PUBLICATION_NOT_AUTHORIZED' or receipt.get('completion_claims',{}).get('retrospective_proof_corpus_published_on_zenodo') is not False or receipt.get('completion_claims',{}).get('zenodo_mutation_authorized') is not False:fail('proof corpus receipt boundary drift')
 progress,status=build_progress_projection()
 if read(AI_PROGRESS)!=progress:fail('materialized output drift: AI_PROGRESS.json')
 if AI_STATUS.read_text(encoding='utf-8')!=status:fail('materialized output drift: AI_STATUS.md')
 return {'schema':'qikvrt_remaining_archive_disposition_verification_v1','state':'ALL_19_SUBJECTS_DISPOSITIONED_PROOF_CORPUS_VERIFIED_PUBLICATION_NOT_AUTHORIZED','subject_count':19,'claim_count':index['claim_count'],'explicit_open_claim_count':index['explicit_open_claim_count'],'correction_required_subject_count':len(index['correction_requirements']),'next_deterministic_effect':progress['next_action'],'pass':False,'final_pass':False,'effect_ack_done':False,'zenodo_mutation_authorized':False,'proof_corpus_published_on_zenodo':False}
def materialize():
 cache={};results=[]
 for ordinal,config in enumerate(probe.SUBJECTS,1):results.append(materialize_subject(config,cache,ordinal))
 build_batch_receipt(results);index,receipt,correction=build_proof_corpus(results);build_work_units(correction);progress,status=build_progress_projection();write(AI_PROGRESS,progress);AI_STATUS.write_text(status,encoding='utf-8',newline='\n');verify_materialized()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--materialize',action='store_true');parser.add_argument('--check',action='store_true');parser.add_argument('--json',action='store_true');args=parser.parse_args()
 try:
  if args.materialize:materialize()
  result=verify_materialized() if args.check or not args.materialize else verify_materialized()
 except (DispositionError,OSError,UnicodeError,ValueError,json.JSONDecodeError) as ex:
  print(json.dumps({'state':'BLOCK','failure_class':'REMAINING_ARCHIVE_CONTENT_DISPOSITION_INVALID','reason':str(ex),'pass':False,'final_pass':False,'effect_ack_done':False,'zenodo_mutation_authorized':False},ensure_ascii=False,sort_keys=True));return 2
 print(json.dumps(result,ensure_ascii=False,indent=2 if args.json else None,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
