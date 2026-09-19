#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Bounded PR1128 publication preparation and independent PR1120 readback.

The literal owner instruction is retained separately from its technical hash
encoding. This script does not supply a native review or cryptographic signature.
Production effects remain subject to the unchanged repository v2 publisher.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, pathlib, secrets, subprocess, sys
import urllib.parse, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = 'ee8c95af54a7d6035b3ca5d204cc02121dc3199c'
TREE = '1306d1a313ab9998d0708042cb93c4d3c5b8eb9d'
PACKAGE = 'docs/publications/2026-09-19-truth-needs-no-conspiracy-theory'
CONTROL = 'release/zenodo-catchup-20260919/pr1128'
OWNER_QUOTE = 'Dann hol das mal schleunigst nach.'
ARTICLE_SHA256 = 'fb865db33137a184e059f7caa0b532ffbe15680aae7098c62f05d3f0d4254cf8'
NAMES = ['Die_Wahrheit_braucht_keine_Verschwoerungstheorie.txt', 'CLAIM_MATRIX.json', 'SOURCE_BINDINGS.json', 'QUELLEN_UND_GELTUNGSBEREICH.md', 'verify_publication_scope.py', 'BOUNDARY_TEST_REPORT.json', 'PREPUBLICATION_RETURN_RECEIPT.json', 'README.md', 'ZENODO_METADATA.json', 'MACHINE_PROOF_BUNDLE.json']

def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, timeout=90).strip()

def identity(path: str) -> dict:
    data = (ROOT/path).read_bytes()
    return {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob_sha': hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()}

def write(path: str, value: dict) -> None:
    target = ROOT/path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')

def prepare() -> None:
    from tools import qikvrt_zenodo_publish as publisher
    from tools import qikvrt_zenodo_machine_proof as proof_gate
    from tools import qikvrt_zenodo_actions as transport
    if git('rev-parse', SOURCE+'^{tree}') != TREE:
        raise RuntimeError('SOURCE_TREE_MISMATCH')
    git('merge-base', '--is-ancestor', SOURCE, 'HEAD')
    paths = [PACKAGE+'/'+name for name in NAMES]
    if len(paths) != 10 or len(set(paths)) != 10:
        raise RuntimeError('EXACT_TEN_FILES_REQUIRED')
    for path in paths:
        if git('rev-parse', SOURCE+':'+path) != identity(path)['git_blob_sha']:
            raise RuntimeError('SOURCE_PAYLOAD_CHANGED: '+path)
    if identity(paths[0])['sha256'] != ARTICLE_SHA256:
        raise RuntimeError('FROZEN_ARTICLE_CHANGED')
    original_proof = proof_gate.validate_bundle(ROOT, ROOT/paths[-1], upload_paths=paths)
    fresh_report = json.loads(subprocess.check_output([sys.executable, '-B', str(ROOT/PACKAGE/'verify_publication_scope.py')], cwd=ROOT, text=True, timeout=120))
    if fresh_report != json.loads((ROOT/PACKAGE/'BOUNDARY_TEST_REPORT.json').read_text()):
        raise RuntimeError('FRESH_BOUNDARY_REPORT_DIFFERS')
    metadata_path = PACKAGE+'/ZENODO_METADATA.json'
    metadata = json.loads((ROOT/metadata_path).read_text())
    metadata['prereserve_doi'] = True
    write(metadata_path, metadata)
    bundle = json.loads((ROOT/paths[-1]).read_text())
    for artifact in bundle['artifacts']:
        observed = identity(artifact['path'])
        if artifact['path'] != metadata_path and (artifact['git_blob_sha1'] != observed['git_blob_sha'] or artifact['sha256'] != observed['sha256']):
            raise RuntimeError('UNAUTHORIZED_COMPANION_CHANGE: '+artifact['path'])
        artifact['git_blob_sha1'] = observed['git_blob_sha']
        artifact['sha256'] = observed['sha256']
    write(paths[-1], bundle)
    fresh_proof = proof_gate.validate_bundle(ROOT, ROOT/paths[-1], upload_paths=paths)
    principal = {'name': 'Ingolf Lohmann', 'type': 'NATURAL_PERSON'}
    return_identity = identity(PACKAGE+'/PREPUBLICATION_RETURN_RECEIPT.json')
    proof_identity = identity(paths[-1])
    metadata_digest = hashlib.sha256(transport._json_bytes(metadata)).hexdigest()
    authorization_id = 'pr1128-truth-catchup-20260919-v2'
    publication_id = fresh_proof['publication_id']
    statement = publisher._canonical_authorization_statement(authorization_id, publication_id, return_identity['sha256'], metadata_digest, proof_identity['sha256'])
    recorded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    evidence_path = CONTROL+'/zenodo-publication.json'
    request_path = CONTROL+'/OWNER_REQUEST.json'
    write(request_path, {
        'schema': 'qikvrt_delegated_publication_request_v1',
        'principal': principal, 'literal_user_instruction': OWNER_QUOTE,
        'request_context': 'Explicit instruction to complete the previously identified missing Zenodo publications; PR1128 original essay and its ten-file companion set are the scope of this execution.',
        'recorded_at': recorded_at,
        'source_head': SOURCE, 'source_tree': TREE,
        'canonical_statement': statement,
        'canonical_statement_origin': 'ASSISTANT_GENERATED_TECHNICAL_ENCODING_NOT_A_VERBATIM_USER_QUOTE',
        'native_review': False, 'cryptographic_person_signature': False,
        'article_bytes_changed': False,
        'allowed_wrapper_repairs': ['Set prereserve_doi=true', 'Rebind that metadata in the proof bundle', 'Create exact v2 manifest and repository-side execution authorization'],
        'excluded': ['Protected Main promotion', 'Native review synthesis', 'Changing essay wording', 'Changing other published records', 'Treating publication as empirical or institutional endorsement']
    })
    uploads = [{**identity(path), 'name': pathlib.PurePosixPath(path).name} for path in paths]
    authorization_path = CONTROL+'/OWNER_ZENODO_AUTHORIZATION.json'
    write(authorization_path, {
        '_license': {'classification': 'owner_effect_authorization', 'copyright': 'Copyright 2026 Ingolf Lohmann.', 'license': 'CC-BY-NC-ND-4.0', 'license_text_ref': 'LICENSES/CC-BY-NC-ND-4.0.txt', 'rights_holder': 'Ingolf Lohmann'},
        'schema': publisher.OWNER_AUTHORIZATION_SCHEMA, 'authorization_id': authorization_id,
        'nonce': secrets.token_hex(32), 'single_use': True, 'single_use_scope': publisher.SINGLE_USE_SCOPE,
        'principal': principal, 'publication_id': publication_id, 'repository': 'Goldkelch/qik-vrt', 'source_head': SOURCE,
        'candidate_return_receipt': return_identity, 'canonical_metadata_sha256': metadata_digest,
        'uploads': uploads, 'machine_proof': proof_identity,
        'authorized_effects': list(publisher.OWNER_AUTHORIZED_EFFECTS), 'publication_evidence_path': evidence_path,
        'authorization_event': {
            'channel': 'ChatGPT explicit owner request; assistant-encoded exact binding; literal instruction in OWNER_REQUEST.json',
            'authorized_at': recorded_at, 'decision': 'AUTHORIZE_EXACT_UPLOAD', 'exact_statement': statement,
            'statement_sha256': hashlib.sha256(statement.encode()).hexdigest(), 'principal': principal,
            'candidate_return_receipt_sha256': return_identity['sha256']
        }
    })
    manifest_path = CONTROL+'/publication-manifest.json'
    write(manifest_path, {
        'schema': publisher.SCHEMA_V2, 'state': 'publish', 'confirm': 'PUBLISH_TO_PRODUCTION_ZENODO',
        'repository': 'Goldkelch/qik-vrt', 'source_head': SOURCE, 'metadata': metadata,
        'files': [{key: upload[key] for key in ('path', 'name', 'git_blob_sha')} for upload in uploads],
        'machine_proof': {'path': paths[-1], 'git_blob_sha': proof_identity['git_blob_sha'], 'policy_id': proof_gate.POLICY_ID},
        'owner_authorization': identity(authorization_path), 'evidence_path': evidence_path
    })
    validated = publisher.load_manifest(ROOT/manifest_path, ROOT)
    if len(validated['files']) != 10:
        raise RuntimeError('PUBLISHER_FILESET_MISMATCH')
    write(CONTROL+'/PREPARATION_RESULT.json', {
        'schema': 'qikvrt_pr1128_catchup_preparation_v1', 'recorded_at': recorded_at,
        'source_head': SOURCE, 'source_tree': TREE, 'carrier_head': git('rev-parse','HEAD'),
        'article_sha256': ARTICLE_SHA256, 'article_unchanged': True,
        'fresh_boundary_report': fresh_report, 'fresh_machine_proof': fresh_proof,
        'upload_count': 10, 'manifest_sha256': validated['manifest_sha256'],
        'publication_performed': False, 'native_review_established': False,
        'PREDECESSOR_EVIDENCE_TRANSFER': False
    })
    print('PR1128_V2_PREFLIGHT_OK files=10 article_sha256='+ARTICLE_SHA256, flush=True)
    print('MANIFEST='+manifest_path, flush=True)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('REDIRECT_NOT_ACCEPTED')

def public_get(url: str, limit: int) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'zenodo.org' or parsed.username or parsed.password:
        raise RuntimeError('UNSAFE_PUBLIC_READBACK_URL')
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'qikvrt-catchup-readback/1'})
    with opener.open(request, timeout=90) as response:
        if response.status != 200:
            raise RuntimeError('PUBLIC_READBACK_NOT_200')
        data = response.read(limit+1)
    if len(data)>limit:
        raise RuntimeError('PUBLIC_RESPONSE_TOO_LARGE')
    return data

def readback_1120() -> None:
    subject = 'c23b2ca377e7bd57589fc8b656fb76167bea9b6b'
    receipt = json.loads(git('show', subject+':release/legal-open-letter-zenodo-receipt.json'))
    record = json.loads(public_get('https://zenodo.org/api/records/22813431', 4*1024*1024))
    if int(record['id']) != 22813431 or record.get('doi') != receipt['doi']:
        raise RuntimeError('PUBLIC_RECORD_IDENTITY_MISMATCH')
    inventory = {f['key']: f for f in record['files']}
    if set(inventory) != {f['name'] for f in receipt['files']}:
        raise RuntimeError('PUBLIC_FILESET_MISMATCH')
    result = []
    for f in receipt['files']:
        source = subprocess.check_output(['git','show',subject+':docs/legal/2026-09-17-open-letter-rule-of-law-evidence-dossier/'+f['name']], cwd=ROOT, timeout=60)
        data = public_get(inventory[f['name']]['links']['self'], 16*1024*1024)
        if len(data)!=f['bytes'] or hashlib.sha256(data).hexdigest()!=f['sha256'] or data!=source:
            raise RuntimeError('PUBLIC_BYTE_MISMATCH: '+f['name'])
        result.append({**f, 'public_sha256': hashlib.sha256(data).hexdigest(), 'byte_equal_to_current_subject': True})
    out = 'release/zenodo-catchup-20260919/pr1120/PUBLIC_READBACK.json'
    write(out, {'schema':'qikvrt_fresh_public_zenodo_readback_v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':subject,'tree':git('rev-parse',subject+'^{tree}'),'record_id':22813431,'doi':receipt['doi'],'url':'https://zenodo.org/records/22813431','files':result,'unauthenticated':True,'production_mutations':0,'PREDECESSOR_EVIDENCE_TRANSFER':False})
    print('PR1120_PUBLIC_READBACK_OK doi='+receipt['doi']+' files=4', flush=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'readback-1120'])
    args=parser.parse_args()
    try:
        prepare() if args.mode=='prepare' else readback_1120()
    except Exception as exc:
        print('CATCHUP_STOP '+type(exc).__name__+': '+str(exc), file=sys.stderr)
        raise SystemExit(1)
