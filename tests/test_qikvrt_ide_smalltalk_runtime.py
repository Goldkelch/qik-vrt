import json,pathlib,unittest
R=pathlib.Path(__file__).resolve().parents[1]
class SmalltalkRuntimeTests(unittest.TestCase):
 def test_contract_and_sources_are_bound(self):
  c=json.loads((R/'runtime/smalltalk/QIKVRT_SMALLTALK_RUNTIME_V1.json').read_text())
  self.assertEqual(c['language'],'Smalltalk'); self.assertFalse(c['predecessor_evidence_transfer'])
  src=(R/c['source']).read_text(); self.assertIn('QIKVRTIDEPerspective',src); self.assertIn("'smalltalk'",src)
  drv=(R/'runtime/smalltalk/qikvrt_ide_smalltalk_driver.st').read_text(); self.assertIn('QIKVRT_SMALLTALK_RUNTIME_V1',drv); self.assertIn('CANDIDATE_ONLY',drv)
 def test_required_api_operations(self):
  c=json.loads((R/'runtime/smalltalk/QIKVRT_SMALLTALK_RUNTIME_V1.json').read_text())
  self.assertEqual(c['operations'],['observe','inspect','reflect','adapt','test','receipt'])
if __name__=='__main__': unittest.main()
