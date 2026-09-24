import json, pathlib, unittest
from tools.qikvrt_proof_closure import evaluate

ROOT=pathlib.Path(__file__).resolve().parents[1]
FIX=ROOT/"tests"/"fixtures"/"proof_closure"

class ProofClosureTests(unittest.TestCase):
    def load(self,name):
        return json.loads((FIX/name).read_text(encoding="utf-8"))
    def test_closed(self):
        r=evaluate(self.load("pass.json"))
        self.assertEqual(r["status"],"PASS")
        self.assertTrue(r["proof_closure"])
    def test_open_obligation_blocks(self):
        r=evaluate(self.load("fail_open_obligation.json"))
        self.assertEqual(r["status"],"BLOCK")
        self.assertFalse(r["proof_closure"])
    def test_subject_mutation_blocks_inheritance(self):
        r=evaluate(self.load("fail_subject_mutation.json"))
        self.assertEqual(r["status"],"BLOCK")
    def test_predecessor_transfer_blocks(self):
        r=evaluate(self.load("fail_predecessor_transfer.json"))
        self.assertEqual(r["status"],"BLOCK")

if __name__=="__main__":
    unittest.main()
