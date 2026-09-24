import json
import subprocess
import sys
import unittest
from pathlib import Path

from src.temdd.v1_adapter import adapt
from tests.test_temdd import GOOD

ROOT=Path(__file__).resolve().parents[1]

class TEMDDV1Tests(unittest.TestCase):
    def test_v1_adapter_is_conservative_successor(self):
        ir=adapt(GOOD)
        self.assertEqual(ir["schema"],"temdd_ir_v1")
        self.assertEqual(ir["ir_version"],"1")
        self.assertEqual(ir["language_version"],"0.1")
        self.assertEqual(ir["context"],{"name":"c","perspective":"test"})
        self.assertEqual(ir["relations"][0]["predicate"],"observes")
        self.assertEqual(ir["subject"]["binding"],"exact")
        self.assertEqual(set(ir["semantic_contract"]),{
            "T13_CAUSAL_BINDING","T14_EVIDENCE_NON_TRANSFER",
            "T15_EFFECT_CONSTRUCTION","T16_CONFORMANCE_BINDING",
        })

    def test_adapter_process_boundary_is_executable(self):
        proc=subprocess.run(
            [sys.executable,str(ROOT/"src/temdd/v1_adapter.py"),str(ROOT/"tests/temdd/positive/minimal.temdd")],
            cwd=ROOT,text=True,capture_output=True,check=False,
        )
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["schema"],"temdd_ir_v1")

    def test_normative_runner_does_not_import_adapter(self):
        text=(ROOT/"conformance/temdd/runner.py").read_text(encoding="utf-8")
        self.assertIn("invoke_adapter",text)
        self.assertNotIn("from src.temdd.v1_adapter import",text)
        self.assertNotIn("from tools.qikvrt_temdd import",text)

if __name__=="__main__":
    unittest.main()
