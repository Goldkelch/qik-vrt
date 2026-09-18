import unittest
from tools.qikvrt_temdd import parse
GOOD='''temdd 0.1; authority owner = "Goldkelch/qik-vrt"; context c { perspective = "test"; } subject s { repository = "Goldkelch/qik-vrt"; binding = exact; } relation rel { source = "a"; predicate = "observes"; target = "b"; epistemic = UNKNOWN; source_order = 2; observation_order = 1; freshness = FRESH; } request r { target = CUSTOM_DOD; } on event { follow exact; classify causal; } on blocker { learn smallest_sound_successor; execute successor; } until { ZERO_BUGS && FRESH_EFFECT_READBACK; }'''
class TEMDDTests(unittest.TestCase):
 def test_deterministic_ir(self): self.assertEqual(parse(GOOD),parse(GOOD))
 def test_exact_binding(self): self.assertEqual(parse(GOOD)['subject']['binding'],'exact')
 def test_context_perspective(self): self.assertEqual(parse(GOOD)['context'],{'name':'c','perspective':'test'})
 def test_first_class_relation(self):
  rel=parse(GOOD)['relations'][0]
  self.assertEqual((rel['source'],rel['predicate'],rel['target']),('a','observes','b'))
  self.assertEqual((rel['source_order'],rel['observation_order']),(2,1))
 def test_typed_epistemic_state(self): self.assertEqual(parse(GOOD)['relations'][0]['epistemic'],'UNKNOWN')
 def test_dod_conjunction(self): self.assertEqual(parse(GOOD)['dod'],['ZERO_BUGS','FRESH_EFFECT_READBACK'])
 def test_missing_authority_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('authority owner = "Goldkelch/qik-vrt";',''))
 def test_missing_context_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('context c { perspective = "test"; }',''))
 def test_nonexact_binding_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('binding = exact','binding = floating'))
 def test_missing_repository_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('repository = "Goldkelch/qik-vrt";',''))
 def test_missing_relation_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('relation rel { source = "a"; predicate = "observes"; target = "b"; epistemic = UNKNOWN; source_order = 2; observation_order = 1; freshness = FRESH; }',''))
 def test_invalid_epistemic_state_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('epistemic = UNKNOWN','epistemic = MAYBE'))
 def test_invalid_freshness_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('freshness = FRESH','freshness = FUTURE'))
 def test_missing_handler_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('on event { follow exact; classify causal; }','').replace('on blocker { learn smallest_sound_successor; execute successor; }',''))
 def test_qikvrt_dod_is_complete(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('CUSTOM_DOD','QIKVRT_DOD'))
 def test_duplicate_dod_blocks(self):
  with self.assertRaises(ValueError): parse(GOOD.replace('ZERO_BUGS &&','ZERO_BUGS && ZERO_BUGS &&'))
if __name__=='__main__': unittest.main()
