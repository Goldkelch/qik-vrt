#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations
import copy,importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'tools/qikvrt_content_disposition_batch_003_dispatch.py';WORKFLOW=ROOT/'.github/workflows/qikvrt_repository_evidence.yml';S=importlib.util.spec_from_file_location('batch003_dispatch',P);m=importlib.util.module_from_spec(S);assert S.loader is not None;S.loader.exec_module(m)
def load(path:pathlib.Path):return json.loads(path.read_text(encoding='utf-8'))
class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.dispatch=load(m.DISPATCH);cls.package=load(m.WORK_PACKAGE);cls.work=load(m.WORK_UNIT);cls.queue=load(m.QUEUE);cls.corpus=load(m.CORPUS);cls.envelope=load(m.PROOF_ENVELOPE);cls.progress=load(m.AI_PROGRESS);cls.workflow=WORKFLOW.read_text(encoding='utf-8')
 def test_positive(self):
  result=m.verify();self.assertEqual(result['batch_id'],'CONTENT-DISPOSITION-BATCH-003')
  if m.FINAL_CORPUS_RECEIPT.is_file():
   self.assertEqual(result['state'],'ALL_19_SUBJECTS_DISPOSITIONED_PROOF_CORPUS_VERIFIED_PUBLICATION_NOT_AUTHORIZED');self.assertEqual(result['active_subject'],'NONE');self.assertEqual(result['open_subject_count'],0);self.assertTrue(result['claim_extraction_complete']);self.assertIs(result['proof_corpus_published_on_zenodo'],False)
  elif m.SECOND_SUBJECT_RECEIPT.is_file():
   self.assertEqual(result['state'],'BATCH_003_DISPATCH_PRESERVED_ADVANCED_PROJECTION_CURRENT');self.assertEqual(result['active_subject'],'SUBJECT-b4849e1a2d6b2270');self.assertEqual(result['open_subject_count'],5);self.assertTrue(result['claim_extraction_complete'])
  elif m.ADVANCED_SUBJECT_RECEIPT.is_file():
   self.assertEqual(result['state'],'BATCH_003_DISPATCH_PRESERVED_ADVANCED_PROJECTION_CURRENT');self.assertEqual(result['active_subject'],'SUBJECT-172dd9bc2738fa43');self.assertEqual(result['open_subject_count'],6);self.assertTrue(result['claim_extraction_complete'])
  else:
   self.assertEqual(result['state'],'BATCH_003_DISPATCH_STATUS_PROJECTION_CURRENT');self.assertEqual(result['active_subject'],m.FIRST_SUBJECT_ID);self.assertEqual(result['open_subject_count'],7);self.assertFalse(result['claim_extraction_complete'])
  for key in ('zenodo_mutation_authorized','pass','final_pass','effect_ack_done'):self.assertIs(result[key],False)
 def test_exact_dispatch_partition_and_priority(self):
  m.validate_queue(self.queue);m.validate_corpus(self.corpus);m.validate_dispatch(self.dispatch,self.package,self.work);rows=self.dispatch['batch']['subjects'];self.assertEqual(tuple(row['subject_id'] for row in rows),m.ACTIVE_SUBJECT_IDS);self.assertEqual(rows[0]['queue_priority'],2);self.assertTrue(all(row['queue_priority']==3 for row in rows[1:]));self.assertEqual(tuple(self.dispatch['outside_active_batch']['subject_ids']),m.OUTSIDE_SUBJECT_IDS)
 def test_public_source_boundary_is_fail_closed(self):
  m.validate_public_sources(self.envelope);files={row['name']:row for row in self.package['public_source_files']};receipt=files[m.PUBLIC_RECEIPT['name']];index=files[m.PUBLIC_INDEX['name']];self.assertEqual(receipt['state'],'LOCAL_EXACT_PUBLIC_BYTES_AVAILABLE');self.assertEqual(index['state'],'PUBLIC_FREEZE_RECOVERY_REQUIRED_BEFORE_EXTRACTION');self.assertTrue(receipt['current_repository_binding']['repository_byte_match']);self.assertFalse(index['current_repository_binding']['current_repository_byte_match']);self.assertNotEqual(m.sha256_bytes(m.LIVE_INDEX.read_bytes()),m.PUBLIC_INDEX['sha256'])
 def test_immutable_dispatch_projection_is_preserved(self):
  progress,status=m.base_expected_projection();corpus=progress['scopes']['qikvrt-zenodo-canonical-union-2026-07-28-v1'];self.assertEqual(progress['percent'],63);self.assertEqual(progress['next_action'],m.NEXT_EFFECT);self.assertEqual(corpus['counts']['dispositioned_subjects'],12);self.assertEqual(corpus['counts']['open_subjects'],7);self.assertEqual(corpus['batch_003']['state'],'DISPATCHED_FIRST_SUBJECT_ACTIVE');self.assertIn(m.NEXT_EFFECT,status)
 def test_root_projection_is_owned_by_most_advanced_projector(self):
  expected,status=m.expected_projection();self.assertEqual(self.progress,expected);renderer=m.pretty
  if m.ADVANCED_SUBJECT_RECEIPT.is_file():renderer=m._advanced_module().pretty
  self.assertEqual(m.AI_PROGRESS.read_text(encoding='utf-8'),renderer(expected));self.assertEqual(m.AI_STATUS.read_text(encoding='utf-8'),status);corpus=expected['scopes']['qikvrt-zenodo-canonical-union-2026-07-28-v1']
  if m.FINAL_CORPUS_RECEIPT.is_file():
   self.assertEqual(expected['percent'],100);self.assertEqual(corpus['counts']['dispositioned_subjects'],19);self.assertEqual(corpus['counts']['open_subjects'],0);self.assertTrue(corpus['batch_003']['terminal']);self.assertIs(corpus['retrospective_proof_corpus']['published_on_zenodo'],False)
  elif m.SECOND_SUBJECT_RECEIPT.is_file():
   self.assertEqual(expected['percent'],74);self.assertEqual(corpus['counts']['dispositioned_subjects'],14);self.assertEqual(corpus['counts']['open_subjects'],5);self.assertEqual(corpus['batch_003']['active_subject'],'SUBJECT-b4849e1a2d6b2270')
  elif m.ADVANCED_SUBJECT_RECEIPT.is_file():
   self.assertEqual(expected['percent'],68);self.assertEqual(corpus['counts']['dispositioned_subjects'],13);self.assertEqual(corpus['counts']['open_subjects'],6);self.assertEqual(corpus['batch_003']['active_subject'],'SUBJECT-172dd9bc2738fa43')
 def test_repository_evidence_preserves_returned_candidate_state(self):
  remaining='if [ -f "$remaining_script" ] && [ -f "$remaining_receipt" ]; then';candidate='if [ -f "$candidate_entrypoint" ] && [ -f "$candidate_package" ]; then';older='elif [ -f "$second_script" ] && [ -f "$recursive_probe" ]; then';segment=self.workflow[self.workflow.index(remaining):self.workflow.index(older)]
  for value in (remaining,candidate,older,'--materialize --json','--check --json','python3 -B "$candidate_entrypoint" --check'):self.assertIn(value,self.workflow)
  self.assertLess(self.workflow.index(remaining),self.workflow.index(older));self.assertLess(segment.index(candidate),segment.index('else'));self.assertLess(segment.index('--check --json'),segment.index('else'));self.assertGreater(segment.index('--materialize --json'),segment.index('else'));self.assertEqual(self.workflow.count('tools.qikvrt_content_disposition_batch_003_remaining_archives'),3)
 def test_wrong_first_subject_blocks(self):
  bad=copy.deepcopy(self.dispatch);bad['batch']['subjects'][0]['subject_id']='SUBJECT-172dd9bc2738fa43'
  with self.assertRaises(m.E):m.validate_dispatch(bad,self.package,self.work)
 def test_false_completion_blocks(self):
  for key in ('all_content_claims_dispositioned','batch_003_terminal','first_subject_claim_extraction_complete','pass','final_pass','effect_ack_done','zenodo_mutation_authorized'):
   bad=copy.deepcopy(self.dispatch);bad['completion_claims'][key]=True
   with self.assertRaises(m.E,msg=key):m.validate_dispatch(bad,self.package,self.work)
 def test_live_index_substitution_blocks(self):
  bad=copy.deepcopy(self.package);row=next(item for item in bad['public_source_files'] if item['name']==m.PUBLIC_INDEX['name']);row['current_repository_binding']['current_repository_byte_match']=True
  with self.assertRaises(m.E):m.validate_work_package(bad)
 def test_projection_release_inflation_blocks(self):
  progress,_=m.expected_projection()
  if m.ADVANCED_SUBJECT_RECEIPT.is_file():advanced=m._advanced_module();validator=advanced.validate_progress_projection;error_type=advanced.SubjectDispositionError
  else:validator=m.validate_progress;error_type=m.E
  for path in ('top','corpus'):
   bad=copy.deepcopy(progress)
   if path=='top':bad['claims']['PASS']=True
   else:bad['scopes']['qikvrt-zenodo-canonical-union-2026-07-28-v1']['claims']['PASS']=True
   with self.assertRaises(error_type):validator(bad)
if __name__=='__main__':unittest.main(verbosity=2)
