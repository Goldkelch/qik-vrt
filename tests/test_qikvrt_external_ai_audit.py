import json, tempfile, unittest
from pathlib import Path
from tools.qikvrt_external_ai_audit import audit

ROOT=Path(__file__).resolve().parents[1]

class ExternalAIAuditTests(unittest.TestCase):
    def setUp(self):
        self.policy=json.loads((ROOT/"policy"/"QIKVRT_EXTERNAL_AI_AUDIT_V1.json").read_text())
    def load(self,name):
        return json.loads((ROOT/"tests"/"fixtures"/"external_ai_audit"/name).read_text())
    def test_pass_trace(self):
        r=audit(self.load("pass_trace.json"),self.policy)
        self.assertEqual(r["audit_status"],"PASS")
        self.assertTrue(r["effect_ack_done"])
        self.assertEqual(r["finding_count"],0)
    def test_silent_omission_blocks_false_done(self):
        r=audit(self.load("fail_silent_omission.json"),self.policy)
        self.assertEqual(r["audit_status"],"BLOCK")
        self.assertFalse(r["effect_ack_done"])
        self.assertTrue(any("READBACK" in x or "open obligations" in x for x in r["findings"]))
    def test_unauthorized_effect_blocks(self):
        r=audit(self.load("fail_unauthorized_execute.json"),self.policy)
        self.assertEqual(r["audit_status"],"BLOCK")
        self.assertTrue(any("unauthorized effect" in x for x in r["findings"]))

if __name__=="__main__":
    unittest.main()
