import importlib.util,pathlib,unittest
P=pathlib.Path(__file__).resolve().parents[1]/'tools/qikvrt_monitorhook.py';S=importlib.util.spec_from_file_location('mh',P);mh=importlib.util.module_from_spec(S);S.loader.exec_module(mh)
class MonitorHookTests(unittest.TestCase):
 def test_event_exact_subject_and_universal_fields(self):
  e=mh.event(7); self.assertEqual(e['sequence'],7); self.assertEqual(e['subject']['head_sha'],e['head_sha']); self.assertEqual(e['subject']['tree_sha'],e['tree_sha']); self.assertEqual(e['validity'],'CURRENT'); self.assertIn('provenance',e)
 def test_contract_is_read_only(self):
  import json
  c=json.loads((P.parents[1]/'contracts/QIKVRT_MONITORHOOK_V1.json').read_text()); self.assertFalse(c['mutation_allowed']); self.assertEqual(c['methods'],['GET','HEAD']); self.assertFalse(c['semantics']['predecessor_evidence_transfer'])
if __name__=='__main__': unittest.main()
