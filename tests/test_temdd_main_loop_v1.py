# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "spec/temdd/TEMDD_MAIN_LOOP_V1.json"
CONTEXT = ROOT / "AI_CONTEXT.json"
PY_IMPL = ROOT / "runtime/temdd/main_loop.py"

def load_py():
    spec = importlib.util.spec_from_file_location("qikvrt_temdd_main_loop", PY_IMPL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

class FakeRuntime:
    def __init__(self, module, evidence):
        self.module = module
        self.evidence = evidence
    def cycle(self, subject):
        return self.evidence, subject + 1
    def bind_successor(self, predecessor, successor):
        return successor

class TEMDDMainLoopV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.mod = load_py()

    def test_contract_chain_and_outer_main(self):
        self.assertEqual(
            self.contract["canonical_chain"],
            ["COMPILE","BIND","RESOLVE","EXECUTE","TEST","OBSERVE","READBACK","ACCEPT","EFFECT_ACK_DONE"],
        )
        outer = self.contract["outer_main"]
        self.assertTrue(outer["potentially_unbounded"])
        self.assertTrue(outer["effect_ack_done_terminates_subject_not_runtime"])
        self.assertTrue(outer["accepted_successor_becomes_next_bound_input"])
        self.assertFalse(outer["predecessor_evidence_transfer"])

    def test_all_eight_required_and_successor_rebound(self):
        E = self.mod.StageEvidence
        full = E(True, True, True, True, True, True, True, True)
        runtime = FakeRuntime(self.mod, full)
        done, subject = self.mod.run_one(runtime, 41)
        self.assertTrue(done)
        self.assertEqual(subject, 42)
        fields = list(full.__dataclass_fields__)
        for field in fields:
            values = {name: True for name in fields}
            values[field] = False
            partial = E(**values)
            done, subject = self.mod.run_one(FakeRuntime(self.mod, partial), 41)
            self.assertFalse(done, field)
            self.assertEqual(subject, 41, field)

    def test_bounded_harness_does_not_redefine_program_done(self):
        E = self.mod.StageEvidence
        full = E(True, True, True, True, True, True, True, True)
        completed, subject = self.mod.run_bounded(FakeRuntime(self.mod, full), 0, 3)
        self.assertEqual((completed, subject), (3, 3))

    def test_every_node_inherits_main_loop_contract(self):
        context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        self.assertIn("spec/temdd/TEMDD_MAIN_LOOP_V1.md", context["required_read_order"])
        self.assertIn("spec/temdd/TEMDD_MAIN_LOOP_V1.json", context["required_read_order"])
        self.assertTrue(context["temdd_main_loop"]["production_main_potentially_unbounded"])
        self.assertFalse(context["temdd_main_loop"]["predecessor_evidence_transfer"])

    def test_all_declared_carriers_exist_and_preserve_core_markers(self):
        carriers = self.contract["carriers"]
        self.assertEqual(
            set(carriers),
            {"python","rust","smalltalk","m68000","ada_spark","lean","vhdl"},
        )
        markers = {
            "python": "while True",
            "rust": "pub fn main_loop",
            "smalltalk": "runForeverOn:",
            "m68000": "temdd_effect_ack_done_m68000",
            "ada_spark": "Effect_Ack_Done",
            "lean": "done_iff_all",
            "vhdl": "effect_ack_done_o",
        }
        for name, relative in carriers.items():
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertIn(markers[name], path.read_text(encoding="utf-8"), relative)

if __name__ == "__main__":
    unittest.main()
