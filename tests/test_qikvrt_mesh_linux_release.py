import json, pathlib, unittest, yaml
ROOT=pathlib.Path(__file__).resolve().parents[1]
WF=ROOT/".github/workflows/qikvrt_mesh_linux_release.yml"
TOOL=ROOT/"tools/qikvrt_mesh_linux_release.py"
POLICY=ROOT/"policy/QIKVRT_MESH_LINUX_RELEASE_V1.json"
AUTH=ROOT/"release/QIKVRT_MESH_LINUX_1_0_0_AUTHORIZATION.json"
class T(unittest.TestCase):
 def test_files(self):
  for p in [WF,TOOL,POLICY,AUTH,ROOT/"docs/QIKVRT_MESH_LINUX_RELEASE_V1.md"]: self.assertTrue(p.is_file(),p)
 def test_policy(self):
  p=json.loads(POLICY.read_text()); a=json.loads(AUTH.read_text())
  self.assertEqual(p["version"],"1.0.0"); self.assertTrue(a["authorized"])
  self.assertEqual(a["authorization_text"],"Dann liefere jetzt alles aus.")
  self.assertFalse(p["boundaries"]["physical_megast_execution_claimed"])
  self.assertFalse(p["boundaries"]["general_effect_ack_done_claimed"])
 def test_workflow(self):
  raw=WF.read_text(); yaml.safe_load(raw)
  for s in ["ubuntu-24.04-arm","qikvrt-mesh-linux-v1.0.0","ghcr.io/goldkelch/qik-vrt-mesh-linux:1.0.0","packages: write","contents: write","release: reattest QIK-VRT Mesh Linux v1.0.0 exact tree"]: self.assertIn(s,raw)
  self.assertNotIn(":latest",raw); self.assertNotIn("--clobber",raw)
 def test_sources(self):
  raw=TOOL.read_text()
  for sha in ["b7c9fa5f74cb963ba7cfefed2a0d0a071e6515a9","cba166e45a0ea4b5d5dd2ef9cde0ad96ff57554b","9832f6ddf6a3ef53a7c0f9b52d2c9d8f1e7ba970","d1940f7d69d343355e183dff1e08a59852d32e7309baa7a4bad8365b11b005ac","2eaec7286c49fdea713dddabcf5012cafa7097a658e916acb48f4bc5fdc8e419"]: self.assertIn(sha,raw)
  self.assertIn("BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",raw)
if __name__=="__main__": unittest.main()
