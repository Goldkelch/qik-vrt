#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/'tools/qikvrt_content_disposition_batch_002_terminal.py'
spec=importlib.util.spec_from_file_location('b2',P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class T(unittest.TestCase):
 def test_open_boundary(self): self.assertEqual(m.classify('Diese Frage bleibt offen.'),'OPEN')
 def test_normative(self): self.assertEqual(m.classify('Jede Veröffentlichung muss geprüft werden.'),'NORMATIVE')
 def test_interpretative(self): self.assertEqual(m.classify('Dies ist eine ontologische Interpretation.'),'INTERPRETATIVE')
 def test_empirical(self): self.assertEqual(m.classify('Der SHA-256-Redownload wurde verifiziert.'),'EMPIRICALLY_EVIDENCED')
 def test_plain_source(self): self.assertEqual(m.classify('Das Dokument enthält sieben Dateien.'),'SOURCE_BOUND')
 def test_formal_requires_binding(self):
  self.assertNotEqual(m.classify('Satz','KERNEL_PROVED','',[]),'FORMAL_PROVED')
  self.assertEqual(m.classify('Satz','KERNEL_PROVED','',['Theorem.x']),'FORMAL_PROVED')
 def test_overclaim_detector(self): self.assertTrue(m.OVERCLAIM.search('Damit ist alles vollständig bewiesen.'))
 def test_false_completion_constants(self):
  text=P.read_text(encoding='utf-8')
  self.assertIn('"pass":False',text); self.assertIn('"final_pass":False',text); self.assertIn('"effect_ack_done":False',text)
if __name__=='__main__': unittest.main()
