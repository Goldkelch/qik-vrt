import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "qikvrt_metagrammar_causal_ir_ansic.c"

class CausalIRAnsiCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / "qikvrt-causal-ir"
        subprocess.run(["cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror", str(SOURCE), "-o", str(cls.binary)], check=True, cwd=ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_graph(self, text):
        return subprocess.run([str(self.binary)], input=text, text=True, capture_output=True, cwd=ROOT)

    def test_independent_nodes_are_stably_serialized_not_source_ordered(self):
        r = self.run_graph("z -\na -\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[1:], ["EMIT a", "EMIT z"])

    def test_causal_edge_overrides_lexical_order(self):
        r = self.run_graph("a z\nz -\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[1:], ["EMIT z", "EMIT a"])

    def test_cycle_fails_closed(self):
        r = self.run_graph("a b\nb a\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Kausalzyklus", r.stderr)

    def test_unknown_cause_fails_closed(self):
        r = self.run_graph("a missing\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unbekannte Ursache", r.stderr)

if __name__ == "__main__":
    unittest.main()
