"""Exercise the actual shell guard and ledger argv without starting GUI services."""
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "deploy/universal-terminal/entrypoint.sh"
BEGIN = "# BEGIN TEMDD deployment subject binding"
END = "# END TEMDD deployment subject binding"


class TEMDDRuntimeSubjectBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ENTRYPOINT.read_text(encoding="utf-8")
        if cls.source.count(BEGIN) != 1 or cls.source.count(END) != 1:
            raise AssertionError("The tested subject guard must occur exactly once")
        cls.guard = cls.source.split(BEGIN, 1)[1].split(END, 1)[0]
        start = cls.source.index("python3 -B /opt/qikvrt/src/qikvrt_temdd_event_ledger.py serve")
        stop = cls.source.index("\n  >", start)
        cls.command = cls.source[start:stop].replace("\\\n", " ").rstrip()

    def invoke(self, variables):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("QIKVRT_")}
        env.update(variables)
        script = ('set -eu\n' + self.guard + '\n'
                  'HTTP_HOST=127.0.0.1\nHTTP_PORT=8771\nSTATE_DIR=/tmp/state\n'
                  'python3() { printf "%s\\n" "$@"; }\n' + self.command + '\n')
        return subprocess.run(["/bin/sh", "-c", script], env=env,
                              capture_output=True, text=True, timeout=5)

    def assert_subject(self, variables, switch=None, value=None):
        result = self.invoke(variables)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = result.stdout.splitlines()
        self.assertIn("/opt/qikvrt/src/qikvrt_temdd_event_ledger.py", args)
        self.assertEqual(args.count("--pr"), int(switch == "--pr"))
        self.assertEqual(args.count("--ref"), int(switch == "--ref"))
        if switch is not None:
            self.assertEqual(args[-2:], [switch, value])

    def test_unsealed_reference_launch_keeps_compatibility(self):
        self.assert_subject({})

    def test_explicit_pr_is_passed_as_two_arguments(self):
        self.assert_subject({"QIKVRT_TEMDD_PR": "1124"}, "--pr", "1124")

    def test_explicit_main_ref_is_passed_as_two_arguments(self):
        self.assert_subject({"QIKVRT_TEMDD_REF": "main"}, "--ref", "main")

    def test_exact_head_requires_explicit_selector(self):
        result = self.invoke({"QIKVRT_EXACT_HEAD": "a" * 40})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact deployment requires", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_exact_tree_requires_explicit_selector(self):
        result = self.invoke({"QIKVRT_EXACT_TREE": "b" * 40})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact deployment requires", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_exact_subject_uses_configured_pr_not_legacy_default(self):
        self.assert_subject({"QIKVRT_EXACT_HEAD": "a" * 40,
                             "QIKVRT_EXACT_TREE": "b" * 40,
                             "QIKVRT_TEMDD_PR": "1124"}, "--pr", "1124")

    def test_exact_main_subject_uses_ref_without_false_pr_identity(self):
        self.assert_subject({"QIKVRT_EXACT_HEAD": "a" * 40,
                             "QIKVRT_EXACT_TREE": "b" * 40,
                             "QIKVRT_TEMDD_REF": "main"}, "--ref", "main")

    def test_conflicting_selectors_fail_closed(self):
        result = self.invoke({"QIKVRT_TEMDD_PR": "1124",
                              "QIKVRT_TEMDD_REF": "main"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("choose exactly one", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_pr_cannot_start_ledger(self):
        for value in ("", "0", "01124", "-1", "1124;echo BAD", " 1124", "1124\n", "abc"):
            with self.subTest(value=value):
                result = self.invoke({"QIKVRT_TEMDD_PR": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("QIKVRT_TEMDD_PR", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_invalid_ref_cannot_start_ledger(self):
        for value in ("", "master", "refs/heads/main", "main/other", " main", "main\n"):
            with self.subTest(value=value):
                result = self.invoke({"QIKVRT_TEMDD_REF": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("QIKVRT_TEMDD_REF", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_guard_precedes_runtime_side_effects(self):
        self.assertLess(self.source.index(BEGIN), self.source.index("mkdir -p"))
        self.assertIn('"$@"', self.command)
        result = subprocess.run(["/bin/sh", "-n", str(ENTRYPOINT)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
