import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location("live",ROOT/"tools/qikvrt_zenodo_personal_live_inventory.py");live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)
class T(unittest.TestCase):
 def test_creator(self):self.assertTrue(live.creator_matches({"metadata":{"creators":[{"person_or_org":{"name":"Lohmann, Ingolf"}}]}}))
 def test_successor(self):self.assertEqual(live.classify([1,2],[1,2],[1,2,3],[],[]),("SUCCESSOR_REQUIRED_NEW_PUBLIC_RECORDS",[],[3]))
 def test_match(self):self.assertEqual(live.classify([1,2],[1,2],[1,2],[],[]),("LIVE_READBACK_MATCH",[],[]))
if __name__=="__main__":unittest.main()
