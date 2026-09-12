#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Recover independently completed drafts from an explicit workflow attempt.

Only content-addressed blobs are written. No ref, review or deployment changes.
A later green rerun is not evidence for the selected earlier attempt. A failed
sibling without an artifact does not erase a successful independent result.
"""
from __future__ import annotations
import argparse
import base64
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import zipfile
from tools import qikvrt_journey_translation as worker


def select_completed_drafts(jobs: dict, input_head: str, input_run: int,
                            input_attempt: int | None = None) -> tuple[set[str], dict[str,str]]:
    total=jobs.get('total_count'); rows=jobs.get('jobs')
    if isinstance(total,bool) or not isinstance(total,int) or not 0<=total<=100 or not isinstance(rows,list) or len(rows)!=total:
        raise ValueError('INCOMPLETE_JOB_INVENTORY')
    observed={}
    for job in rows:
        match=re.fullmatch(r'translate \(([a-z]+(?:-[a-z]+)?)\)',str(job.get('name','')))
        if not match: continue
        code=match[1]
        if code not in worker.TARGETS or code in observed:
            raise ValueError('WRONG_OR_DUPLICATE_LANGUAGE_JOB')
        if job.get('head_sha')!=input_head or job.get('run_id')!=input_run or job.get('status')!='completed':
            raise ValueError('UNBOUND_OR_ACTIVE_INPUT_JOB')
        if input_attempt is not None and job.get('run_attempt')!=input_attempt:
            raise ValueError('WRONG_INPUT_JOB_ATTEMPT')
        result=job.get('conclusion')
        if result not in {'success','failure','cancelled','skipped','timed_out','action_required','neutral','stale','startup_failure'}:
            raise ValueError('INVALID_JOB_CONCLUSION')
        observed[code]=result
    if set(observed)!=set(worker.TARGETS):
        raise ValueError('INCOMPLETE_LANGUAGE_JOB_INVENTORY')
    eligible={c for c,r in observed.items() if r=='success'}
    if not eligible: raise ValueError('NO_COMPLETE_DRAFTS')
    return eligible,{c:r for c,r in observed.items() if r!='success'}


def _artifact_code(name: str, head: str) -> str | None:
    prefix='journey-translate-';suffix='-'+head
    return name[len(prefix):-len(suffix)] if name.startswith(prefix) and name.endswith(suffix) else None


def select_artifacts(collection: dict, source_head: str, eligible: set[str],
                     requested: set[str] | None = None) -> tuple[dict,set[str]]:
    rows=collection.get('artifacts');total=collection.get('total_count')
    if isinstance(total,bool) or not isinstance(total,int) or not 0<=total<=100 or not isinstance(rows,list) or len(rows)!=total:
        raise ValueError('ARTIFACT_BOUND_EXCEEDED_OR_INCOMPLETE')
    selected=eligible if requested is None else requested
    if not selected or not selected<=eligible: raise ValueError('REQUESTED_LANGUAGE_NOT_SUCCESSFUL')
    by_code={}
    for item in rows:
        code=_artifact_code(str(item.get('name','')),source_head)
        if code is None: continue
        if code not in worker.TARGETS or code in by_code:
            raise ValueError('WRONG_OR_DUPLICATE_LANGUAGE_ARTIFACT')
        by_code[code]=item
    if not selected<=set(by_code): raise ValueError('MISSING_SUCCESSFUL_LANGUAGE_ARTIFACT')
    return by_code,selected


def recover(output: Path,input_run: int | None,input_head: str | None,
            input_attempt: int = 1,languages: set[str] | None = None) -> None:
    current_head=worker.exact_head(remote=True);raw_source,original=worker.source()
    token=os.environ['GH_TOKEN'];current_run=int(os.environ['GITHUB_RUN_ID'])
    run=input_run or current_run;source_head=input_head or current_head
    if bool(input_run)!=bool(input_head): raise ValueError('INCOMPLETE_INPUT_BINDING')
    if run<=0 or input_attempt<=0 or not re.fullmatch(r'[0-9a-f]{40}',source_head):
        raise ValueError('INVALID_INPUT_SUBJECT')
    endpoint=f'/repos/{worker.REPO}/actions/runs/{run}/attempts/{input_attempt}'
    origin=worker.get_json(endpoint,token)
    allowed={'in_progress'} if run==current_run and source_head==current_head else {'completed'}
    if (origin.get('head_sha')!=source_head or origin.get('status') not in allowed
        or origin.get('head_repository',{}).get('full_name')!=worker.REPO
        or origin.get('path')!='.github/workflows/qikvrt_journey_translation.yml'
        or origin.get('head_branch')!=worker.BRANCH or origin.get('run_attempt')!=input_attempt):
        raise ValueError('WRONG_INPUT_RUN')
    src=worker.get_json(f'/repos/{worker.REPO}/contents/docs/reise/source.de.txt?ref={source_head}',token)
    if src.get('sha')!=worker.blob(raw_source) or base64.b64decode(src.get('content',''))!=raw_source:
        raise ValueError('INPUT_SOURCE_CHANGED_NO_CONTENT_REUSE')
    jobs=worker.get_json(endpoint+'/jobs?per_page=100',token)
    eligible,blocked=select_completed_drafts(jobs,source_head,run,input_attempt)
    collection=worker.get_json(f'/repos/{worker.REPO}/actions/runs/{run}/artifacts?per_page=100',token)
    by_code,selected=select_artifacts(collection,source_head,eligible,languages)
    prepared={};input_artifacts=[]
    for code in sorted(selected):
        item=by_code[code]
        if item.get('expired') or item.get('workflow_run',{}).get('head_sha')!=source_head or item.get('workflow_run',{}).get('id')!=run:
            raise ValueError('STALE_OR_WRONG_ARTIFACT')
        # Artifact names can survive reruns. Require upload during this exact
        # completed job's lifetime, as well as immutable artifact/content hashes.
        job=next(j for j in jobs['jobs'] if j['name']==f'translate ({code})')
        created=item.get('created_at','');start=job.get('started_at','');end=job.get('completed_at','')
        if not (start and end and start<=created<=end):
            raise ValueError('ARTIFACT_OUTSIDE_SELECTED_JOB_ATTEMPT')
        data=worker.artifact_bytes(int(item['id']),token)
        if item.get('digest')!='sha256:'+worker.sha(data): raise ValueError('ARTIFACT_DIGEST_MISMATCH')
        input_artifacts.append({'language':code,'id':item['id'],'digest':item['digest'],'name':item['name'],
                               'job_id':job['id'],'run_attempt':input_attempt})
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names=archive.namelist()
            if len(names)!=len(set(names)): raise ValueError('DUPLICATE_ZIP_MEMBER')
            if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):
                raise ValueError('UNSAFE_ZIP_MEMBER')
            if 'FILESET.json' not in names or archive.getinfo('FILESET.json').file_size>500_000:
                raise ValueError('MISSING_OR_LARGE_FILESET')
            manifest=json.loads(archive.read('FILESET.json'))
            if manifest.get('source_head')!=source_head or manifest.get('source_sha256')!=worker.SOURCE_SHA:
                raise ValueError('WRONG_ARTIFACT_SUBJECT')
            expected={f'docs/reise/translations/{code}.txt',f'docs/reise/translations/{code}.json'}
            entries=manifest.get('files',[])
            if len(entries)!=2 or {e.get('path') for e in entries}!=expected:
                raise ValueError('UNEXPECTED_LANGUAGE_FILESET')
            for entry in entries:
                path=entry['path']
                if not worker.allowed_file(path,'translate') or path in prepared or Path(path).stem!=code:
                    raise ValueError('UNEXPECTED_OUTPUT_PATH')
                if archive.getinfo('files/'+path).file_size>10_000_000: raise ValueError('OUTPUT_TOO_LARGE')
                raw=archive.read('files/'+path)
                if len(raw)!=entry['bytes'] or worker.sha(raw)!=entry['sha256'] or worker.blob(raw)!=entry['git_blob_sha1']:
                    raise ValueError('OUTPUT_DIGEST_MISMATCH')
                raw.decode('utf-8',errors='strict');prepared[path]=(entry,raw)
    for code in selected:
        base=f'docs/reise/translations/{code}';meta=json.loads(prepared[base+'.json'][1]);raw=prepared[base+'.txt'][1]
        if (meta.get('source_sha256')!=worker.SOURCE_SHA or meta.get('sha256')!=worker.sha(raw)
            or meta.get('language')!=code or meta.get('bytes')!=len(raw)):
            raise ValueError('OUTPUT_SIDECAR_MISMATCH')
        worker.validate_text(worker.split(raw),original)
        if (meta.get('human_language_review') is not False or meta.get('formal_semantic_equivalence_proof') is not False
            or meta.get('status')!='AI_TRANSLATION_DRAFT_UNREVIEWED'):
            raise ValueError('UNAUTHORIZED_REVIEW_ASSERTION')
    worker.exact_head(remote=True)
    receipt={'schema':'qikvrt_journey_partial_git_object_receipt_v1','source_head':current_head,
        'source_sha256':worker.SOURCE_SHA,'input_head':source_head,'input_run':run,'input_attempt':input_attempt,
        'input_artifacts':input_artifacts,'blocked_jobs':blocked,
        'blocked_artifacts':{c:{'id':by_code.get(c,{}).get('id'),'missing':c not in by_code} for c in sorted(blocked)},
        'complete_languages':sorted(selected),'unselected_successful_languages':sorted(eligible-selected),
        'blocked_languages':sorted(blocked),'all_targets_complete':not blocked and selected==set(worker.TARGETS),
        'content_rechecked_on_current_source':True,'predecessor_validation_transfer':False,'files':[],
        'git_ref_mutation':False,'native_review':False,'public_delivery':False,'EFFECT_ACK_DONE':False}
    for path,(entry,raw) in sorted(prepared.items()):
        target=output/'files'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        result=worker.get_json('/repos/'+worker.REPO+'/git/blobs',token,
                              {'encoding':'base64','content':base64.b64encode(raw).decode()})
        if result.get('sha')!=entry['git_blob_sha1']: raise ValueError('CREATED_BLOB_ID_MISMATCH')
        readback=worker.get_json('/repos/'+worker.REPO+'/git/blobs/'+result['sha'],token)
        if base64.b64decode(readback.get('content',''))!=raw: raise ValueError('GIT_BLOB_READBACK_MISMATCH')
        receipt['files'].append(entry)
        (output/'GIT_OBJECTS_PARTIAL.json').write_bytes(worker.encoded({**receipt,'all_selected_objects_read_back':False}))
        worker.emit('GIT_BLOB_READ_BACK',path=path,sha=result['sha'])
    worker.exact_head(remote=True);receipt['all_selected_objects_read_back']=True
    (output/'GIT_OBJECTS.json').write_bytes(worker.encoded(receipt));worker.finish_manifest(output,current_head)
    worker.emit('CONTENT_ADDRESSED_PARTIAL_OBJECTS_READY',complete_languages=sorted(selected),blocked_languages=sorted(blocked),source_head=current_head)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/qikvrt-journey-generation'))
    parser.add_argument('--input-run',type=int);parser.add_argument('--input-head')
    parser.add_argument('--input-attempt',type=int,default=1)
    parser.add_argument('--languages',nargs='+',choices=sorted(worker.TARGETS))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    try:
        recover(args.output,args.input_run,args.input_head,args.input_attempt,
                set(args.languages) if args.languages is not None else None)
        return 0
    except Exception as exc:
        failure={'event':'HOLD_UNVERIFIED','mode':'recover-independent-translation-objects',
            'source_head':os.environ.get('GITHUB_SHA'),'error_type':type(exc).__name__,'error':str(exc),'EFFECT_ACK_DONE':False}
        token=os.environ.get('GH_TOKEN')
        if token:failure['error']=failure['error'].replace(token,'[REDACTED]')
        (args.output/'FAILURE.json').write_bytes(worker.encoded(failure))
        worker.emit('HOLD_UNVERIFIED',**{k:v for k,v in failure.items() if k!='event'})
        return 2

if __name__=='__main__':raise SystemExit(main())
