#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Finite, source-bound translation preparation. Never updates a Git ref.

Generated text is an unreviewed draft. The only authenticated write supported
by this module is content-addressed Git blob creation for an allowlisted path.
Reviews, commits, refs, releases, Pages and external publication are excluded.
"""
from __future__ import annotations
import argparse
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
REPO = 'Goldkelch/qik-vrt'
BRANCH = 'publication/self-explanation-47-homepage-v1'
SOURCE_SHA = '181314375effc68933baec365e7973a14ad3981605bb192f93a62c37a321f487'
OLD_SOURCE_SHA = '89759f800a1c372a0774ddd909b20d452b08bc4f10d214fb7d2593c8bcf7290d'
MEDIA = 'https://open.spotify.com/track/1lr7QGyV5RohlODzAqnuZA'
MODEL = 'facebook/nllb-200-distilled-600M'
REVISION = 'f8d333a098d19b4fd9a8b18f94170487ad3f821d'
RECOVER = {
 'fr':'f049fd945957222ba4bca2f18c33ea8f89d96074',
 'es':'77955c0db02f1a180b1836831a92ca8c2878eda2',
 'it':'cb1612538237c442672a2a282c58df162769c33d',
 'pt':'8cd176453ef2269d5493ba90ea90535a4076e58a',
 'nl':'d43e2aac6237be9ce3bb417679350e7a330d43fb',
 'sv':'556481cca89e902fa29fe9d6cbdcf8db29c96b07',
 'da':'79ccb8a9265a37b2366a598fc1b1cf7cc17f4c1f',
 'no':'e31195518c8fe9ea1c2b7fd68f4449f9c40087a2',
}
TARGETS = {
 'ar':'arb_Arab','ast':'ast_Latn','bg':'bul_Cyrl','bn':'ben_Beng',
 'ca':'cat_Latn','cs':'ces_Latn','el':'ell_Grek','eo':'epo_Latn',
 'et':'est_Latn','eu':'eus_Latn','fa':'pes_Arab','fi':'fin_Latn',
 'gl':'glg_Latn','he':'heb_Hebr','hr':'hrv_Latn','hu':'hun_Latn',
 'id':'ind_Latn','is':'isl_Latn','ja':'jpn_Jpan','kk':'kaz_Cyrl',
 'ko':'kor_Hang','lv':'lvs_Latn','pl':'pol_Latn','ro':'ron_Latn',
 'ru':'rus_Cyrl','sk':'slk_Latn','sl':'slv_Latn','sr':'srp_Cyrl',
 'th':'tha_Thai','tr':'tur_Latn','uk':'ukr_Cyrl','vi':'vie_Latn',
 'zh-yue':'yue_Hant','zh':'zho_Hans',
}
MODEL_FILES = ('config.json','generation_config.json','pytorch_model.bin',
               'sentencepiece.bpe.model','special_tokens_map.json',
               'tokenizer.json','tokenizer_config.json','README.md')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n').encode()


def split(data: bytes) -> list[str]:
    text = data.decode('utf-8', errors='strict')
    if '\r' in text or '\x00' in text:
        raise ValueError('UNSUPPORTED_ENCODING')
    return re.split(r'\n\s*\n', text.strip())


def emit(event: str, **fields: object) -> None:
    print(json.dumps({'event':event, **fields}, ensure_ascii=False), flush=True)


def read_file(path: Path, maximum: int = 3_000_000) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('INVALID_INPUT_FILE: '+str(path))
    return path.read_bytes()


def source() -> tuple[bytes,list[str]]:
    data = read_file(ROOT/'docs/reise/source.de.txt')
    values = split(data)
    if sha(data) != SOURCE_SHA or len(values) != 540 or values[1] != MEDIA:
        raise ValueError('SOURCE_CHANGED_REBIND_REQUIRED')
    return data,values


def get_json(path: str, token: str | None = None, payload: dict | None = None) -> dict:
    # No user/model-produced URL can reach the authenticated transport.
    if not path.startswith('/repos/'+REPO+'/'):
        raise ValueError('REPOSITORY_ENDPOINT_FORBIDDEN')
    if payload is not None and path != '/repos/'+REPO+'/git/blobs':
        raise ValueError('ONLY_CONTENT_ADDRESSED_BLOB_WRITES_ALLOWED')
    request = urllib.request.Request('https://api.github.com'+path,
        data=encoded(payload) if payload is not None else None,
        headers={'Accept':'application/vnd.github+json','User-Agent':'qikvrt-journey-v1',
                 **({'Authorization':'Bearer '+token} if token else {}),
                 **({'Content-Type':'application/json'} if payload is not None else {})},
        method='POST' if payload is not None else 'GET')
    # No retry, identity switching or permission escalation. Preserve the
    # server's reason and quota headers rather than guessing from HTTP 403.
    try:
        with urllib.request.urlopen(request,timeout=60) as response:
            data=response.read(8_000_001)
            if len(data)>8_000_000:
                raise ValueError('API_RESPONSE_TOO_LARGE')
            return json.loads(data)
    except urllib.error.HTTPError as exc:
        raw=exc.read(8192).decode('utf-8',errors='replace')
        if token:
            raw=raw.replace(token,'[REDACTED]')
        try:
            message=json.loads(raw).get('message','')
        except (ValueError,AttributeError):
            message='NON_JSON_ERROR_RESPONSE'
        emit('GITHUB_API_ERROR',method=request.method,path=path,http_status=exc.code,
             message=str(message)[:1000],
             rate_remaining=exc.headers.get('X-RateLimit-Remaining'),
             rate_reset=exc.headers.get('X-RateLimit-Reset'),
             retry_after=exc.headers.get('Retry-After'))
        raise


def exact_head(*, remote: bool) -> str:
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    expected=os.environ.get('GITHUB_SHA',actual)
    if actual != expected or not re.fullmatch('[0-9a-f]{40}',actual):
        raise ValueError('CHECKOUT_HEAD_DRIFT')
    if os.environ.get('GITHUB_REPOSITORY') != REPO or os.environ.get('GITHUB_REF') != 'refs/heads/'+BRANCH:
        raise ValueError('WRONG_EXECUTION_ENVELOPE')
    if os.environ.get('GITHUB_RUN_ATTEMPT') != '1':
        raise ValueError('BLIND_RERUN_FORBIDDEN')
    if remote:
        ref=get_json('/repos/'+REPO+'/git/ref/heads/'+BRANCH,os.environ.get('GH_TOKEN'))
        if ref['object']['sha'] != actual:
            raise ValueError('REMOTE_HEAD_DRIFT')
    return actual


def recovered_input(code: str) -> bytes:
    """Read immutable archived input, not a published or reviewed edition."""
    if code not in RECOVER:
        raise ValueError('UNKNOWN_RECOVERY_INPUT')
    data=read_file(ROOT/'docs/reise/recovery-inputs'/(code+'.txt'))
    if blob(data) != RECOVER[code]:
        raise ValueError('RECOVERED_BLOB_MISMATCH: '+code)
    return data


def validate_text(values: list[str], original: list[str]) -> None:
    if len(values) != len(original) or values == original:
        raise ValueError('INCOMPLETE_TEXT_OR_SILENT_SOURCE_FALLBACK')
    for i,(a,b) in enumerate(zip(original,values)):
        if not b.strip() or '\x00' in b:
            raise ValueError('EMPTY_TRANSLATION_BLOCK: '+str(i))
        protected=a == '⸻' or a == MEDIA or a.startswith('q.e.d.')
        if (protected and a != b) or (b == '⸻' and a != '⸻'):
            raise ValueError('PROTECTED_BLOCK_CHANGED: '+str(i))


def store_edition(output: Path, code: str, values: list[str], original: list[str], provenance: dict) -> None:
    validate_text(values,original)
    data=('\n\n'.join(values)+'\n').encode()
    root=output/'files/docs/reise/translations'
    root.mkdir(parents=True,exist_ok=True)
    (root/(code+'.txt')).write_bytes(data)
    meta={
        'schema':'qikvrt_journey_translation_v1','language':code,
        'source_language':'de','source_sha256':SOURCE_SHA,
        'sha256':sha(data),'bytes':len(data),'git_blob_sha1':blob(data),
        'status':'AI_TRANSLATION_DRAFT_UNREVIEWED',
        'translator':provenance['translator'],'generation':provenance,
        'human_language_review':False,'formal_semantic_equivalence_proof':False,
        'copyright':'Copyright 2026 Ingolf Lohmann','license':'CC-BY-NC-ND-4.0',
    }
    (root/(code+'.json')).write_bytes(encoded(meta))
    emit('EDITION_DRAFT_CREATED',code=code,blocks=len(values),bytes=len(data),sha256=sha(data))


def prepare(output: Path) -> None:
    # Pure preparation is bound to this immutable checkout. It neither needs
    # current-branch authority nor a credentialed API read. Live-head CAS is
    # still required at the subsequent content writer/integration boundary.
    head=exact_head(remote=False)
    raw,original=source()
    old=raw.replace(('\n\n\n'+MEDIA+'\n\n\n').encode(),b'\n\n',1)
    if sha(old) != OLD_SOURCE_SHA:
        raise ValueError('PREDECESSOR_CONTENT_RECONSTRUCTION_FAILED')
    old_blocks=split(old)
    corrections={
      'da':('På lange tankelevnedsveje opstår der egne begreber.','På lange tankerejser opstår der egne begreber.'),
      'no':('Jeg kan ikke vite noe.','Jeg kan akseptere å ikke vite noe.'),
      'sv':('Jag kan låta bli att veta något.','Jag kan tillåta mig att inte veta något.'),
    }
    for code,identifier in RECOVER.items():
        data=recovered_input(code)
        values=split(data)
        validate_text(values,old_blocks)
        change=[]
        if code in corrections:
            a,b=corrections[code]
            if sum(v.count(a) for v in values)!=1:
                raise ValueError('CORRECTION_ANCHOR_DRIFT: '+code)
            values=[v.replace(a,b) for v in values]
            change.append({'old':a,'new':b,'kind':'AI_EDITORIAL_CORRECTION_NOT_HUMAN_REVIEW'})
        values.insert(1,MEDIA)
        store_edition(output,code,values,original,{
            'translator':'ChatGPT','method':'RECOVERED_FULL_DRAFT_WITH_EXPLICIT_CURRENT_SOURCE_REBIND',
            'recovered_git_blob_sha1':identifier,'recovered_sha256':sha(data),
            'previous_source_sha256':OLD_SOURCE_SHA,
            'mechanical_change':'Insert current owner-supplied media URL after the translated title.',
            'editorial_changes':change,'predecessor_validation_transfer':False,
        })
    # The new optional runtime is declared before any inference is executed.
    from tools import qikvrt_tool_cache as cache
    lock=ROOT/'runtime/toolchains/TOOLCHAIN.lock.tsv'
    registry=ROOT/'runtime/toolchains/CACHE_REGISTRY.json'
    coverage=ROOT/'runtime/toolchains/CACHE_COVERAGE.json'
    original_runtime={p:p.read_bytes() for p in (lock,registry,coverage)}
    component='journey-nllb-runtime'
    new_lock=original_runtime[lock].decode().rstrip('\n')+'\n'+'\t'.join([
        component,'1.0.0','cpython-3.12.13-linux-x64-cpu',
        'docs/reise/TRANSLATION_RUNTIME.json','VERSION_AND_MODEL_REVISION_CONTRACT',
        'MODEL_CC-BY-NC-4.0_AND_DEPENDENCY_LICENSES','optional_journey_translation_drafts'])+'\n'
    doc=json.loads(original_runtime[registry])
    if component in doc['components']:
        raise ValueError('RUNTIME_ALREADY_PREPARED_REOBSERVE')
    doc['components'][component]={
        'version':'1.0.0','profiles':['journey-translation-drafts'],
        'cache_class':'ecosystem-cache','provider':'Meta model revision on Hugging Face; PyTorch CPU wheels and PyPI',
        'cache_locations':['$RUNNER_TEMP/qikvrt-nllb-payload'],
        'authority_files':['docs/reise/TRANSLATION_RUNTIME.json','tools/qikvrt_journey_translation.py','.github/workflows/qikvrt_journey_translation.yml'],
        'verification':['python3 -B tools/qikvrt_journey_translation.py verify-model --model-root "$RUNNER_TEMP/qikvrt-nllb-payload"',
                        'Immutable provider revision and per-file payload checks precede inference; output is never semantic proof.'],
        'trusted_save':True,
    }
    try:
        lock.write_bytes(new_lock.encode());registry.write_bytes(encoded(doc))
        cov=cache.build_coverage()
        target=output/'files/runtime/toolchains';target.mkdir(parents=True,exist_ok=True)
        (target/lock.name).write_bytes(lock.read_bytes())
        (target/registry.name).write_bytes(registry.read_bytes())
        (target/coverage.name).write_bytes(cache.canonical_json(cov).encode())
    finally:
        for p,data in original_runtime.items():p.write_bytes(data)
    # A real public read, not inference from a search-engine cache failure.
    url='https://goldkelch.github.io/qik-vrt/reise/'
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'qikvrt-readback-v1'}),timeout=30) as response:
            body=response.read(10_000_001)
            observed={'http_status':response.status,'bytes':len(body),'sha256':sha(body),
                      'expected_title_present':original[0].encode() in body}
    except urllib.error.HTTPError as exc:
        observed={'http_status':exc.code,'expected_title_present':False}
    except (urllib.error.URLError,TimeoutError) as exc:
        observed={'http_status':None,'error':str(exc),'expected_title_present':False}
    (output/'PUBLIC_BASELINE.json').write_bytes(encoded({'url':url,'observation':observed,'source_head':head,'delivery_claimed':False}))
    emit('PUBLIC_BASELINE',**observed)
    # Provide local inspection context without exporting .git or credentials.
    with zipfile.ZipFile(output/'TRACKED_SOURCE.zip','w',zipfile.ZIP_DEFLATED) as archive:
        paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
        for name in paths:
            p=ROOT/name
            if name and p.is_file() and not p.is_symlink():archive.write(p,name)
    finish_manifest(output,head)


def finish_manifest(output: Path,head: str) -> None:
    entries=[]
    for p in sorted((output/'files').rglob('*')):
        if p.is_file():
            data=read_file(p,10_000_000)
            entries.append({'path':p.relative_to(output/'files').as_posix(),'bytes':len(data),'sha256':sha(data),'git_blob_sha1':blob(data)})
    (output/'FILESET.json').write_bytes(encoded({'schema':'qikvrt_journey_generated_files_v1','source_head':head,
        'source_sha256':SOURCE_SHA,'files':entries,'native_review':False,'public_delivery':False,'EFFECT_ACK_DONE':False}))


def verify_runtime() -> dict:
    import importlib.metadata
    spec=json.loads((ROOT/'docs/reise/TRANSLATION_RUNTIME.json').read_bytes())
    for name,version in spec['python_packages'].items():
        actual=importlib.metadata.version(name)
        if actual != version:raise ValueError('RUNTIME_VERSION_MISMATCH: '+name+'='+actual)
    if sys.version_info[:3] != (3,12,13):
        raise ValueError('PYTHON_VERSION_MISMATCH: '+sys.version)
    return {'python':sys.version,'packages':dict(spec['python_packages']),
        'pip_freeze':subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines()}


def verify_model(folder: Path, expected: str | None = None) -> dict:
    raw=read_file(folder/'PAYLOAD.json')
    if expected and sha(raw)!=expected:raise ValueError('MODEL_MANIFEST_DRIFT')
    obj=json.loads(raw)
    if obj.get('model')!=MODEL or obj.get('revision')!=REVISION:
        raise ValueError('WRONG_MODEL')
    if set(obj['files'])!=set(MODEL_FILES):raise ValueError('MODEL_FILESET_CHANGED')
    for name,entry in obj['files'].items():
        path=folder/name
        if path.is_symlink() or not path.is_file():raise ValueError('MODEL_FILE_MISSING')
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for piece in iter(lambda:stream.read(4_194_304),b''):h.update(piece)
        if h.hexdigest()!=entry['sha256'] or path.stat().st_size!=entry['bytes']:
            raise ValueError('MODEL_BYTES_CHANGED: '+name)
    return obj


def warm_model(folder: Path,output: Path) -> None:
    exact_head(remote=True);source();runtime=verify_runtime()
    from huggingface_hub import snapshot_download
    folder.mkdir(parents=True,exist_ok=True)
    snapshot_download(repo_id=MODEL,revision=REVISION,allow_patterns=list(MODEL_FILES),
        local_dir=folder,token=False,max_workers=4)
    files={}
    for name in MODEL_FILES:
        path=folder/name;h=hashlib.sha256()
        with path.open('rb') as stream:
            for piece in iter(lambda:stream.read(4_194_304),b''):h.update(piece)
        files[name]={'bytes':path.stat().st_size,'sha256':h.hexdigest()}
    payload={'model':MODEL,'revision':REVISION,'files':files,'license':'CC-BY-NC-4.0'}
    raw=encoded(payload);(folder/'PAYLOAD.json').write_bytes(raw)
    verify_model(folder,sha(raw))
    (output/'MODEL_RUNTIME.json').write_bytes(encoded({'payload':payload,'runtime':runtime,'manifest_sha256':sha(raw)}))
    with open(os.environ['GITHUB_OUTPUT'],'a') as stream:stream.write('manifest_sha256='+sha(raw)+'\n')
    emit('PINNED_MODEL_PAYLOAD_OBSERVED',manifest_sha256=sha(raw),revision=REVISION)


def translate(code: str,folder: Path,output: Path) -> None:
    if code not in TARGETS:raise ValueError('UNSUPPORTED_LANGUAGE_NO_FALLBACK')
    head=exact_head(remote=False);_,original=source();runtime=verify_runtime()
    model_manifest=verify_model(folder,os.environ.get('MODEL_MANIFEST_SHA256'))
    import torch
    from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
    torch.set_num_threads(4)
    tokenizer=AutoTokenizer.from_pretrained(folder,src_lang='deu_Latn',local_files_only=True,trust_remote_code=False)
    model=AutoModelForSeq2SeqLM.from_pretrained(folder,local_files_only=True,trust_remote_code=False,weights_only=True).eval()
    # CPU-only dynamic int8 linear inference, explicitly part of the draft runtime.
    model=torch.ao.quantization.quantize_dynamic(model,{torch.nn.Linear},dtype=torch.qint8)
    target_id=tokenizer.convert_tokens_to_ids(TARGETS[code])
    if target_id in (None,tokenizer.unk_token_id):raise ValueError('UNSUPPORTED_TARGET_TOKEN')
    protected=lambda s:s=='⸻' or s==MEDIA or s.startswith('q.e.d.')
    unique=list(dict.fromkeys(s for s in original if not protected(s)))
    lengths={s:len(tokenizer(s,add_special_tokens=True)['input_ids']) for s in unique}
    if any(n>512 for n in lengths.values()):raise ValueError('SOURCE_TOO_LONG_NO_TRUNCATION')
    ordered=sorted(unique,key=lambda s:(lengths[s],s))
    results={};t0=time.monotonic();batch_size=8
    for start in range(0,len(ordered),batch_size):
        batch=ordered[start:start+batch_size]
        inputs=tokenizer(batch,return_tensors='pt',padding=True,truncation=False)
        with torch.inference_mode():
            tokens=model.generate(**inputs,forced_bos_token_id=target_id,max_new_tokens=512,
                do_sample=False,num_beams=1,use_cache=True)
        for src,seq in zip(batch,tokens.tolist()):
            # Decoder start may itself be EOS: require a generated terminal EOS.
            if tokenizer.eos_token_id not in seq[2:]:raise ValueError('OUTPUT_TRUNCATED_NO_ACCEPTANCE')
            text=tokenizer.decode(seq,skip_special_tokens=True).strip()
            if not text or '\n\n' in text:raise ValueError('EMPTY_OR_MALFORMED_OUTPUT_BLOCK')
            results[src]=text
        emit('TRANSLATION_BATCH',language=code,completed=min(start+batch_size,len(ordered)),
             total=len(ordered),elapsed_seconds=round(time.monotonic()-t0,1))
    values=[s if protected(s) else results[s] for s in original]
    # Translation is probabilistic in quality even though greedy decoding is used.
    store_edition(output,code,values,original,{
        'translator':'Meta NLLB-200 distilled 600M; repository-local draft generation',
        'method':'PARAGRAPH_ALIGNED_CPU_DYNAMIC_INT8_GREEDY_DRAFT',
        'model':MODEL,'model_revision':REVISION,'model_payload':model_manifest,
        'runtime':runtime,'target_token':TARGETS[code],'source_token':'deu_Latn',
        'source_head':head,'no_truncation':True,'human_quality_review':False,
        'model_scope_notice':'Research model; not a certified or independently reviewed document translation.',
    })
    finish_manifest(output,head)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def artifact_bytes(identifier: int,token: str) -> bytes:
    url=f'https://api.github.com/repos/{REPO}/actions/artifacts/{identifier}/zip'
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'qikvrt-journey-v1'})
    try:
        urllib.request.build_opener(NoRedirect).open(req,timeout=30)
    except urllib.error.HTTPError as exc:
        if exc.code not in (301,302,303,307,308):raise
        location=exc.headers['Location']
    else:
        raise ValueError('EXPECTED_SIGNED_ARTIFACT_REDIRECT')
    parsed=urllib.parse.urlparse(location)
    if parsed.scheme!='https' or parsed.username or parsed.password:raise ValueError('UNSAFE_ARTIFACT_REDIRECT')
    # Never forward the GitHub Authorization header to the signed blob origin.
    with urllib.request.urlopen(location,timeout=120) as response:
        data=response.read(150_000_001)
        if len(data)>150_000_000:raise ValueError('ARTIFACT_TOO_LARGE')
        return data


def allowed_file(path: str,phase: str) -> bool:
    if re.fullmatch(r'docs/reise/translations/([a-z]+(?:-[a-z]+)?)\.(txt|json)',path):
        code=Path(path).stem
        return code in (RECOVER if phase=='recover' else TARGETS)
    return phase=='recover' and path in {
      'runtime/toolchains/TOOLCHAIN.lock.tsv','runtime/toolchains/CACHE_REGISTRY.json',
      'runtime/toolchains/CACHE_COVERAGE.json'}


def objects(output: Path,phase: str) -> None:
    head=exact_head(remote=True);source();token=os.environ['GH_TOKEN'];run=int(os.environ['GITHUB_RUN_ID'])
    collection=get_json(f'/repos/{REPO}/actions/runs/{run}/artifacts?per_page=100',token)
    if collection['total_count']>100:raise ValueError('ARTIFACT_BOUND_EXCEEDED')
    prefix='journey-'+phase+'-'
    items=[a for a in collection['artifacts'] if a['name'].startswith(prefix) and a['name'].endswith('-'+head)]
    expected={'bundle'} if phase=='recover' else set(TARGETS)
    found={a['name'][len(prefix):-(len(head)+1)] for a in items}
    if len(items)!=len(found) or found!=expected:raise ValueError('INCOMPLETE_ARTIFACT_SET')
    prepared={}
    for item in sorted(items,key=lambda a:a['name']):
        if item.get('expired') or item.get('workflow_run',{}).get('head_sha')!=head:
            raise ValueError('STALE_ARTIFACT')
        data=artifact_bytes(item['id'],token)
        if item.get('digest')!='sha256:'+sha(data):raise ValueError('ARTIFACT_DIGEST_MISMATCH')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names=archive.namelist()
            if len(names)!=len(set(names)):raise ValueError('DUPLICATE_ZIP_MEMBER')
            if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):
                raise ValueError('UNSAFE_ZIP_MEMBER')
            if archive.getinfo('FILESET.json').file_size>500_000:raise ValueError('FILESET_TOO_LARGE')
            manifest=json.loads(archive.read('FILESET.json'))
            if manifest['source_head']!=head or manifest['source_sha256']!=SOURCE_SHA:
                raise ValueError('WRONG_ARTIFACT_SUBJECT')
            for entry in manifest['files']:
                path=entry['path']
                if not allowed_file(path,phase) or path in prepared:raise ValueError('UNEXPECTED_OUTPUT_PATH')
                info=archive.getinfo('files/'+path)
                if info.file_size>10_000_000:raise ValueError('OUTPUT_TOO_LARGE')
                raw=archive.read(info)
                if len(raw)!=entry['bytes'] or sha(raw)!=entry['sha256'] or blob(raw)!=entry['git_blob_sha1']:
                    raise ValueError('OUTPUT_DIGEST_MISMATCH')
                raw.decode('utf-8',errors='strict');prepared[path]=(entry,raw)
    _,original=source()
    codes=RECOVER if phase=='recover' else TARGETS
    for code in codes:
        path='docs/reise/translations/'+code
        meta=json.loads(prepared[path+'.json'][1]);raw=prepared[path+'.txt'][1]
        if meta['source_sha256']!=SOURCE_SHA or meta['sha256']!=sha(raw) or meta['language']!=code:
            raise ValueError('OUTPUT_SIDECAR_MISMATCH')
        validate_text(split(raw),original)
        if meta['human_language_review'] is not False or meta['status']!='AI_TRANSLATION_DRAFT_UNREVIEWED':
            raise ValueError('UNAUTHORIZED_REVIEW_ASSERTION')
    # Git blobs are content addressed; creation is not a branch/promotion effect.
    exact_head(remote=True)
    receipt={'schema':'qikvrt_journey_git_object_receipt_v1','source_head':head,'source_sha256':SOURCE_SHA,
       'phase':phase,'files':[],'git_ref_mutation':False,'native_review':False,'public_delivery':False,'EFFECT_ACK_DONE':False}
    for path,(entry,raw) in sorted(prepared.items()):
        result=get_json('/repos/'+REPO+'/git/blobs',token,{'encoding':'base64','content':base64.b64encode(raw).decode()})
        if result['sha']!=entry['git_blob_sha1']:raise ValueError('CREATED_BLOB_ID_MISMATCH')
        readback=get_json('/repos/'+REPO+'/git/blobs/'+result['sha'],token)
        if base64.b64decode(readback['content'])!=raw:raise ValueError('GIT_BLOB_READBACK_MISMATCH')
        receipt['files'].append(entry)
        emit('GIT_BLOB_READ_BACK',path=path,sha=result['sha'])
    exact_head(remote=True)
    (output/'GIT_OBJECTS.json').write_bytes(encoded(receipt))
    emit('CONTENT_ADDRESSED_OBJECTS_READY',files=receipt['files'],source_head=head)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['prepare','warm-model','verify-model','translate','objects'])
    parser.add_argument('--output',type=Path,default=Path('/tmp/qikvrt-journey-generation'))
    parser.add_argument('--model-root',type=Path,default=Path('/tmp/qikvrt-nllb-payload'))
    parser.add_argument('--language',choices=sorted(TARGETS))
    parser.add_argument('--phase',choices=['recover','translate'])
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    try:
        if args.mode=='prepare':prepare(args.output)
        elif args.mode=='warm-model':warm_model(args.model_root,args.output)
        elif args.mode=='verify-model':verify_model(args.model_root,os.environ.get('MODEL_MANIFEST_SHA256'))
        elif args.mode=='translate':
            if not args.language:raise ValueError('LANGUAGE_REQUIRED')
            translate(args.language,args.model_root,args.output)
        else:
            if not args.phase:raise ValueError('PHASE_REQUIRED')
            objects(args.output,args.phase)
        return 0
    except Exception as exc:
        failure={'event':'HOLD_UNVERIFIED','mode':args.mode,
                 'source_head':os.environ.get('GITHUB_SHA'),
                 'error_type':type(exc).__name__,'error':str(exc),
                 'EFFECT_ACK_DONE':False}
        # A failed prepare must leave diagnostics, not an empty artifact path.
        token=os.environ.get('GH_TOKEN')
        if token:
            failure['error']=failure['error'].replace(token,'[REDACTED]')
        (args.output/'FAILURE.json').write_bytes(encoded(failure))
        emit('HOLD_UNVERIFIED',**{k:v for k,v in failure.items() if k!='event'})
        return 2

if __name__=='__main__':raise SystemExit(main())
