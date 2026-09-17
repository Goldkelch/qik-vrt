import importlib.util, pathlib, unittest
P=pathlib.Path(__file__).resolve().parents[1]/'tools/qikvrt_ide_perspectives.py'; S=importlib.util.spec_from_file_location('ide',P); ide=importlib.util.module_from_spec(S); S.loader.exec_module(ide)
class IDEPerspectiveTests(unittest.TestCase):
 def test_four_independent_receipts_bind_same_subject(self):
  rs=[ide.receipt(x,b'input') for x in ide.LANGS]
  self.assertEqual([r['language'] for r in rs],list(ide.LANGS)); self.assertEqual(len({r['receipt_sha256'] for r in rs}),4)
  self.assertEqual(len({r['head_sha'] for r in rs}),1); self.assertEqual(len({r['tree_sha'] for r in rs}),1)
 def test_smalltalk_missing_runtime_is_counterevidence(self): self.assertEqual(ide.receipt('smalltalk')['counterexamples'],['SMALLTALK_RUNTIME_NOT_ADMITTED'])
 def test_fusion_never_votes_away_counterevidence(self):
  f=ide.fuse([ide.receipt(x) for x in ide.LANGS]); self.assertEqual(f['state'],'HOLD_UNVERIFIED'); self.assertIn('SMALLTALK_RUNTIME_NOT_ADMITTED',f['conflicts']); self.assertFalse(f['predecessor_evidence_transfer'])
if __name__=='__main__': unittest.main()
