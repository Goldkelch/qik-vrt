import unittest
from tools.qikvrt_temdd import parse
GOOD='''temdd 0.1; authority owner = "Goldkelch/qik-vrt"; subject s { repository = "Goldkelch/qik-vrt"; binding = exact; } request r { target = CUSTOM_DOD; } on event { follow exact; classify causal; } on blocker { learn smallest_sound_successor; execute successor; } until { ZERO_BUGS && FRESH_EFFECT_READBACK; }'''
class TEMDDTests(unittest.TestCase):
 def test_deterministic_ir(self): self.assertEqual(parse(GOOD),parse(GOOD))
 def test_exact_binding(self): self.assertEqual(parse(GOOD)['subject']['binding'],'exact')
 def test_dod_conjunction(self): self.assertEqual(parse(GOOD)['dod'],['ZERO_BUGS','FRESH_EFFECT_READBACK'])
 def test_missing_authority_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('authority owner = "Goldkelch/qik-vrt";',''))
 def test_nonexact_binding_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('binding = exact','binding = floating'))
 def test_missing_repository_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('repository = "Goldkelch/qik-vrt";',''))
 def test_subject_scope_not_global(self):
  bad=GOOD.replace('repository = "Goldkelch/qik-vrt";','')+' repository = "evil/global";'
  with self.assertRaises(ValueError): parse(bad)
 def test_missing_handler_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('on event { follow exact; classify causal; }','').replace('on blocker { learn smallest_sound_successor; execute successor; }',''))
 def test_qikvrt_dod_is_complete(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('CUSTOM_DOD','QIKVRT_DOD'))
 def test_duplicate_dod_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('ZERO_BUGS &&','ZERO_BUGS && ZERO_BUGS &&'))
if __name__=='__main__': unittest.main()
