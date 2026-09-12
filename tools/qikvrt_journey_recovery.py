#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Recover only complete, exact-run journey translation drafts.

This adapter never updates a Git ref. It validates the complete translation-job
inventory, accepts content only from independently successful matrix jobs,
revalidates every accepted byte against the current frozen source, creates only
content-addressed Git blobs, reads those blobs back, and preserves failed jobs as
explicit blockers in the receipt.
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


def select_completed_drafts(jobs: dict, input_head: str, input_run: int) -> tuple[set[str], dict[str,str]]:
    total=jobs.get('total_count')
    rows=jobs.get('jobs')
    if isinstance(total,bool) or not isinstance(total,int) or total < 0 or total > 100 or not isinstance(rows,list) or len(rows)!=total:
        raise ValueError('INCOMPLETE_JOB_INVENTORY')
    observed: dict[str,str]={}
    for job in rows:
        match=re.fullmatch(r'translate \(([a-z]+(?:-[a-z]+)?)\)',str(job.get('name','')))
        if not match:
            continue
        code=match[1]
        if code not in worker.TARGETS or code in observed:
            raise ValueError('WRONG_OR_DUPLICATE_LANGUAGE_JOB')
        if job.get('head_sha')!=input_head or job.get('run_id')!=input_run or job.get('status')!='completed':
            raise ValueError('UNBOUND_OR_ACTIVE_INPUT_JOB')
        conclusion=job.get('conclusion')
        if not isinstance(conclusion,str) or not conclusion:
            raise ValueError('INVALID_JOB_CONCLUSION')
        observed[code]=conclusion
    if set(observed)!=set(worker.TARGETS):
        raise ValueError('INCOMPLETE_LANGUAGE_JOB_INVENTORY')
    eligible={code for code,result in observed.items() if result=='success'}
    if not eligible:
        raise ValueError('NO_COMPLETE_DRAFTS')
    return eligible,{code:result for code,result in observed.items() if result!='success'}


def _artifact_code(name: str, head: str) -> str | None:
    prefix='journey-translate-';suffix='-'+head
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    return name[len(prefix):-len(suffix)]


def recover(output: Path,input_run: int | None,input_head: str | None) -> None:
    current_head=worker.exact_head(remote=True)
    raw_source,original=worker.source()
    token=os.environ['GH_TOKEN']
    current_run=int(os.environ['GITHUB_RUN_ID'])
    run=input_run or current_run
    source_head=input_head or current_head
    if bool(input_run)!=bool(input_head):
        raise ValueError('INCOMPLETE_INPUT_BINDING')
    if run<=0 or not re.fullmatch(r'[0-9a-f]{40}',source_head):
        raise ValueError('INVALID_INPUT_SUBJECT')

    origin=worker.get_json(f'/repos/{worker.REPO}/actions/runs/{run}',token)
    allowed_status={'in_progress'} if run==current_run and source_head==current_head else {'completed'}
    if (origin.get('head_sha')!=source_head or origin.get('status') not in allowed_status
            or origin.get('head_repository',{}).get('full_name')!=worker.REPO
            or origin.get('path')!='.github/workflows/qikvrt_journey_translation.yml'
            or origin.get('head_branch')!=worker.BRANCH or origin.get('run_attempt')!=1):
        raise ValueError('WRONG_INPUT_RUN')

    source_doc=worker.get_json(f'/repos/{worker.REPO}/contents/docs/reise/source.de.txt?ref={source_head}',token)
    if source_doc.get('sha')!=worker.blob(raw_source) or base64.b64decode(source_doc.get('content',''))!=raw_source:
        raise ValueError('INPUT_SOURCE_CHANGED_NO_CONTENT_REUSE')

    jobs=worker.get_json(f'/repos/{worker.REPO}/actions/runs/{run}/jobs?per_page=100',token)
    eligible,blocked=select_completed_drafts(jobs,source_head,run)
    collection=worker.get_json(f'/repos/{worker.REPO}/actions/runs/{run}/artifacts?per_page=100',token)
    artifacts=collection.get('artifacts')
    total=collection.get('total_count')
    if isinstance(total,bool) or not isinstance(total,int) or total>100 or not isinstance(artifacts,list) or len(artifacts)!=total:
        raise ValueError('ARTIFACT_BOUND_EXCEEDED_OR_INCOMPLETE')

    by_code={}
    for item in artifacts:
        code=_artifact_code(str(item.get('name','')),source_head)
        if code is None:
            continue
        if code not in worker.TARGETS or code in by_code:
            raise ValueError('WRONG_OR_DUPLICATE_LANGUAGE_ARTIFACT')
        by_code[code]=item
    if set(by_code)!=set(worker.TARGETS):
        raise ValueError('INCOMPLETE_TRANSLATION_ARTIFACT_INVENTORY')

    blocked_artifacts={code:{'id':by_code[code].get('id'),'digest':by_code[code].get('digest'),'name':by_code[code].get('name')}
                       for code in sorted(blocked)}
    prepared={};input_artifacts=[]
    for code in sorted(eligible):
        item=by_code[code]
        if item.get('expired') or item.get('workflow_run',{}).get('head_sha')!=source_head or item.get('workflow_run',{}).get('id')!=run:
            raise ValueError('STALE_OR_WRONG_ARTIFACT')
        data=worker.artifact_bytes(int(item['id']),token)
        if item.get('digest')!='sha256:'+worker.sha(data):
            raise ValueError('ARTIFACT_DIGEST_MISMATCH')
        input_artifacts.append({'language':code,'id':item['id'],'digest':item['digest'],'name':item['name']})
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names=archive.namelist()
            if len(names)!=len(set(names)):
                raise ValueError('DUPLICATE_ZIP_MEMBER')
            if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):
                raise ValueError('UNSAFE_ZIP_MEMBER')
            if 'FILESET.json' not in names or archive.getinfo('FILESET.json').file_size>500_000:
                raise ValueError('MISSING_OR_LARGE_FILESET')
            manifest=json.loads(archive.read('FILESET.json'))
            if manifest.get('source_head')!=source_head or manifest.get('source_sha256')!=worker.SOURCE_SHA:
                raise ValueError('WRONG_ARTIFACT_SUBJECT')
            expected_paths={f'docs/reise/translations/{code}.txt',f'docs/reise/translations/{code}.json'}
            manifest_paths={entry.get('path') for entry in manifest.get('files',[])}
            if manifest_paths!=expected_paths:
                raise ValueError('UNEXPECTED_LANGUAGE_FILESET')
            for entry in manifest['files']:
                path=entry['path']
                if not worker.allowed_file(path,'translate') or path in prepared or Path(path).stem!=code:
                    raise ValueError('UNEXPECTED_OUTPUT_PATH')
                info=archive.getinfo('files/'+path)
                if info.file_size>10_000_000:
                    raise ValueError('OUTPUT_TOO_LARGE')
                raw=archive.read(info)
                if len(raw)!=entry['bytes'] or worker.sha(raw)!=entry['sha256'] or worker.blob(raw)!=entry['git_blob_sha1']:
                    raise ValueError('OUTPUT_DIGEST_MISMATCH')
                raw.decode('utf-8',errors='strict')
                prepared[path]=(entry,raw)

    for code in eligible:
        root=f'docs/reise/translations/{code}'
        meta=json.loads(prepared[root+'.json'][1]);raw=prepared[root+'.txt'][1]
        if (meta.get('source_sha256')!=worker.SOURCE_SHA or meta.get('sha256')!=worker.sha(raw)
                or meta.get('language')!=code or meta.get('bytes')!=len(raw)):
            raise ValueError('OUTPUT_SIDECAR_MISMATCH')
        worker.validate_text(worker.split(raw),original)
        if (meta.get('human_language_review') is not False
                or meta.get('formal_semantic_equivalence_proof') is not False
                or meta.get('status')!='AI_TRANSLATION_DRAFT_UNREVIEWED'):
            raise ValueError('UNAUTHORIZED_REVIEW_ASSERTION')

    worker.exact_head(remote=True)
    receipt={'schema':'qikvrt_journey_partial_git_object_receipt_v1','source_head':current_head,
        'source_sha256':worker.SOURCE_SHA,'input_head':source_head,'input_run':run,
        'input_artifacts':input_artifacts,'blocked_jobs':blocked,'blocked_artifacts':blocked_artifacts,
        'complete_languages':sorted(eligible),'blocked_languages':sorted(blocked),
        'all_targets_complete':not blocked,'content_rechecked_on_current_source':True,
        'predecessor_validation_transfer':False,'files':[],'git_ref_mutation':False,
        'native_review':False,'public_delivery':False,'EFFECT_ACK_DONE':False}
    for path,(entry,raw) in sorted(prepared.items()):
        target=output/'files'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        result=worker.get_json('/repos/'+worker.REPO+'/git/blobs',token,
            {'encoding':'base64','content':base64.b64encode(raw).decode()})
        if result.get('sha')!=entry['git_blob_sha1']:
            raise ValueError('CREATED_BLOB_ID_MISMATCH')
        readback=worker.get_json('/repos/'+worker.REPO+'/git/blobs/'+result['sha'],token)
        if base64.b64decode(readback.get('content',''))!=raw:
            raise ValueError('GIT_BLOB_READBACK_MISMATCH')
        receipt['files'].append(entry)
        (output/'GIT_OBJECTS_PARTIAL.json').write_bytes(worker.encoded({**receipt,'all_selected_objects_read_back':False}))
        worker.emit('GIT_BLOB_READ_BACK',path=path,sha=result['sha'])
    worker.exact_head(remote=True)
    receipt['all_selected_objects_read_back']=True
    (output/'GIT_OBJECTS.json').write_bytes(worker.encoded(receipt))
    worker.finish_manifest(output,current_head)
    worker.emit('CONTENT_ADDRESSED_PARTIAL_OBJECTS_READY',complete_languages=sorted(eligible),blocked_languages=sorted(blocked),source_head=current_head)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/qikvrt-journey-generation'))
    parser.add_argument('--input-run',type=int)
    parser.add_argument('--input-head')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    try:
        recover(args.output,args.input_run,args.input_head)
        return 0
    except Exception as exc:
        failure={'event':'HOLD_UNVERIFIED','mode':'recover-independent-translation-objects',
            'source_head':os.environ.get('GITHUB_SHA'),'error_type':type(exc).__name__,'error':str(exc),
            'EFFECT_ACK_DONE':False}
        token=os.environ.get('GH_TOKEN')
        if token:
            failure['error']=failure['error'].replace(token,'[REDACTED]')
        (args.output/'FAILURE.json').write_bytes(worker.encoded(failure))
        worker.emit('HOLD_UNVERIFIED',**{k:v for k,v in failure.items() if k!='event'})
        return 2


if __name__=='__main__':raise SystemExit(main())
