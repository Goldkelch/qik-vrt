#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations
import copy, importlib.util, json, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/"tools/qikvrt_content_disposition_batch_002_corrected_candidate.py"
S=importlib.util.spec_from_file_location("b2c",P)
m=importlib.util.module_from_spec(S)
assert S.loader is not None
S.loader.exec_module(m)

def load(path): return json.loads(path.read_text(encoding="utf-8"))

class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.matrix=load(m.MATRIX)
  cls.candidate=load(m.DISPOSITION)
  cls.publication=load(m.PUBLICATION_CORRECTION)
  cls.receipt=load(m.OWNER_RECEIPT)
  cls.boundary=m.BOUNDARY.read_text(encoding="utf-8")
  cls.denk=m.DENK.read_text(encoding="utf-8")

 def test_positive(self):
  result=m.verify()
  self.assertEqual(result["state"],"CORRECTED_CANDIDATE_READY_FOR_OWNER_ACCEPTANCE")
  self.assertEqual(result["owner_acceptance"],"PENDING")
  self.assertFalse(result["historical_bytes_mutated"])
  self.assertTrue(result["completion_claims"]["candidate_returned_to_owner"])
  for key in ("owner_acceptance_recorded","pass","final_pass","effect_ack_done"):
   self.assertIs(result["completion_claims"][key],False)

 def test_exact_overclaims(self):
  rows=m.detected_overclaims(self.matrix)
  self.assertEqual(tuple(x["claim_id"] for x in rows),m.EXPECTED_OVERCLAIM_IDS)
  self.assertEqual(
   tuple(x["claim_id"] for x in self.candidate["detected_overclaim_bindings"]),
   m.EXPECTED_OVERCLAIM_IDS,
  )

 def test_wrong_subject_blocks(self):
  bad=copy.deepcopy(self.candidate)
  bad["source_binding"]["subject_id"]="SUBJECT-WRONG"
  with self.assertRaises(m.E):
   m.verify_candidate(bad,self.matrix,self.boundary,self.publication,self.denk)

 def test_missing_boundary_blocks(self):
  bad=self.boundary.replace("a universal solver for arbitrary problems","a solver")
  with self.assertRaises(m.E): m.verify_boundary(bad)

 def test_pending_owner_gate(self):
  self.assertEqual(self.receipt["owner_decision"]["state"],"PENDING")
  self.assertIs(self.receipt["completion_claims"]["owner_acceptance_recorded"],False)
  self.assertIs(self.receipt["completion_claims"]["zenodo_mutation_authorized"],False)

 def test_scope_separation(self):
  row=self.candidate["scope_separation"]
  self.assertEqual(row["content_disposition_scope"],"CONTENT-DISPOSITION-BATCH-002")
  self.assertEqual(row["user_supplied_text_scope"],"DENK-MENGENLEHRE-BATCH-002")
  self.assertIs(row["scopes_equal"],False)
  self.assertIs(row["denk_candidate_resolves_zenodo_subject"],False)
  m.verify_denk_candidate(self.denk)

 def test_historical_bytes_immutable(self):
  m.verify_source_files()
  row=self.candidate["regenerated_disposition"]
  self.assertIs(row["historical_public_bytes_mutated"],False)
  self.assertIs(row["historical_claim_matrix_mutated"],False)

 def test_false_completion_rejected(self):
  bad=copy.deepcopy(self.candidate)
  bad["completion_claims"]["final_pass"]=True
  with self.assertRaises(m.E):
   m.verify_candidate(bad,self.matrix,self.boundary,self.publication,self.denk)

if __name__=="__main__": unittest.main(verbosity=2)
