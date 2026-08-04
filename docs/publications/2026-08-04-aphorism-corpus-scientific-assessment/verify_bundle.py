#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'BUNDLE_MANIFEST.json'
DETACHED = ROOT / 'BUNDLE_MANIFEST.json.sha256'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

errors: list[str] = []
value = json.loads(MANIFEST.read_text(encoding='utf-8'))
listed = {entry['path'] for entry in value['files']}
actual = {
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob('*')
    if p.is_file() and p.name not in {'BUNDLE_MANIFEST.json', 'BUNDLE_MANIFEST.json.sha256'}
}
for path in sorted(listed - actual):
    errors.append(f'missing:{path}')
for path in sorted(actual - listed):
    errors.append(f'unmanifested:{path}')
for entry in value['files']:
    path = ROOT / entry['path']
    if not path.is_file():
        continue
    if path.stat().st_size != entry['bytes']:
        errors.append(f"bytes:{entry['path']}")
    if sha256(path) != entry['sha256']:
        errors.append(f"sha256:{entry['path']}")
if DETACHED.read_text(encoding='ascii') != f"{sha256(MANIFEST)}  BUNDLE_MANIFEST.json\n":
    errors.append('detached-manifest-digest')

ledger = json.loads((ROOT / 'ASR_LEDGER.json').read_text(encoding='utf-8'))
if ledger.get('automatic_asr_two_pass_count') != 7 or len(ledger.get('items', [])) != 7:
    errors.append('asr-count')
if any(item.get('human_acoustic_review_status') != 'PENDING' for item in ledger['items']):
    errors.append('human-review-boundary')
if any(item.get('verbatim_status') != 'NOT_VERIFIED' for item in ledger['items']):
    errors.append('verbatim-boundary')

claims = json.loads((ROOT / 'CLAIM_MATRIX.json').read_text(encoding='utf-8'))
expected_claims = {'PASS': False, 'FINAL_PASS': False, 'EFFECT_ACK_DONE': False}
if claims.get('release_claims') != expected_claims:
    errors.append('release-claims')

receipt = json.loads((ROOT / 'PDF_RENDER_RECEIPT.json').read_text(encoding='utf-8'))
pdf = ROOT / receipt['pdf']['path']
if receipt['pdf']['sha256'] != sha256(pdf) or receipt['pdf']['bytes'] != pdf.stat().st_size:
    errors.append('pdf-binding')
if receipt['render']['status'] != 'AUTOMATED_RENDER_VERIFIED':
    errors.append('pdf-render-status')
if receipt['visual_inspection']['status'] != 'NOT_PERFORMED_IN_REPOSITORY_WORKFLOW':
    errors.append('visual-boundary')

machine = json.loads((ROOT / 'MACHINE_PROOF_BUNDLE.json').read_text(encoding='utf-8'))
pdf_proof = next((p for p in machine['proofs'] if p['id'] == 'MP-PDF'), None)
if not pdf_proof or pdf_proof.get('sha256') != sha256(pdf):
    errors.append('machine-proof-pdf')
if machine.get('release_claims') != expected_claims:
    errors.append('machine-release-claims')

for path in ROOT.rglob('*'):
    if path.is_file() and path.suffix.lower() in {'.m4a', '.wav', '.mp3', '.ogg', '.flac', '.aac'}:
        errors.append(f'raw-or-derived-audio-committed:{path.relative_to(ROOT)}')

D, G, T = True, True, False
if not (D and G and not T):
    errors.append('normative-countermodel')

result = {
    'schema': 'qikvrt-aphorism-repository-bundle-verification/2.0',
    'status': 'PASS' if not errors else 'FAIL',
    'errors': errors,
    'files_checked': len(value['files']),
    'scope': 'repository bundle bytes, automated render, declared ASR provenance and epistemic boundaries only',
    'repository_pass_claimed': False,
    'effect_ack_done_claimed': False,
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if not errors else 1)
