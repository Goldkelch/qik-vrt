import json, tempfile, unittest
from pathlib import Path
from tools.qikvrt_executor_claim_receipt_adapter import make_claim,reserve,append_receipt,ClaimBlock

H="1"*40; T="2"*40
class AdapterTests(unittest.TestCase):
 def claim(self):
  return make_claim({"observed":{"head_sha":H,"tree_sha":T}},"wu","carrier","authority")
 def test_claim_binds_exact_subject(self):
  c=self.claim(); self.assertEqual((c["head_sha"],c["tree_sha"]),(H,T))
 def test_atomic_reservation_rejects_competitor(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.claim(); reserve(c,Path(d))
   with self.assertRaises(ClaimBlock): reserve(c,Path(d))
 def test_receipt_is_append_only_and_read_back(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.claim(); p=Path(d)/"r.jsonl"
   r=append_receipt(c,{"head_sha":H,"tree_sha":T,"run_id":7},p)
   self.assertFalse(r["effect_ack_done"])
   self.assertEqual(json.loads(p.read_text().splitlines()[-1]),r)
 def test_subject_drift_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.claim()
   with self.assertRaises(ClaimBlock): append_receipt(c,{"head_sha":"3"*40,"tree_sha":T},Path(d)/"r")
if __name__=="__main__": unittest.main()
