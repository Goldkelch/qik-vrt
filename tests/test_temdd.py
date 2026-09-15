import unittest
from tools.qikvrt_temdd import parse
GOOD='''temdd 0.1; authority owner = "Goldkelch/qik-vrt"; subject s { repository = "Goldkelch/qik-vrt"; binding = exact; } request r { target = QIKVRT_DOD; } on event { follow exact; classify causal; } on blocker { learn smallest_sound_successor; execute successor; } until { ZERO_BUGS && FRESH_EFFECT_READBACK; }'''
class TEMDDTests(unittest.TestCase):
 def test_deterministic_ir(self):
  self.assertEqual(parse(GOOD),parse(GOOD))
 def test_exact_binding(self):
  self.assertEqual(parse(GOOD)['subject']['binding'],'exact')
 def test_dod_conjunction(self):
  self.assertEqual(parse(GOOD)['dod'],['ZERO_BUGS','FRESH_EFFECT_READBACK'])
 def test_missing_authority_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('authority owner = "Goldkelch/qik-vrt";',''))
 def test_nonexact_binding_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('binding = exact','binding = floating'))
 def test_missing_readback_can_be_detected(self):
  self.assertNotIn('FRESH_EFFECT_READBACK',parse(GOOD.replace(' && FRESH_EFFECT_READBACK',''))['dod'])
if __name__=='__main__': unittest.main()
