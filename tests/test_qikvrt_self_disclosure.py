# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
import json,pathlib,subprocess,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
DOC=ROOT/'.well-known'/'qik-vrt-self-disclosure.json'
TOOL=ROOT/'tools'/'qikvrt_self_disclosure.py'
class SelfDisclosureTests(unittest.TestCase):
 def test_discovery_document(self):
  d=json.loads(DOC.read_text(encoding='utf-8')); self.assertEqual(d['state'],'AVAILABLE'); self.assertTrue(d['capabilities']); self.assertFalse(d['completion_claims']['pass'])
 def test_machine_interaction(self):
  for command in ('show','capabilities','status'):
   p=subprocess.run([sys.executable,str(TOOL),command],text=True,capture_output=True,check=False); self.assertEqual(p.returncode,0,p.stderr); json.loads(p.stdout)
 def test_batch_002_evidence_present(self):
  base=ROOT/'release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/public-candidate-byte-freeze'
  self.assertTrue((base/'PUBLIC_CANDIDATE_BYTE_FREEZE_RECEIPT.json').is_file()); self.assertEqual(len(list((base/'records').glob('*.json'))),6); self.assertEqual(len(list((base/'files').glob('*.json'))),70)
if __name__=='__main__': unittest.main()
