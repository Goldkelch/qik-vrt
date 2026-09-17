import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_lean_v2_m68000_d3_compiler.py"
LEAN = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "QIKVRTFormalization" / "Hardware" / "D3FixedPoint.lean"

spec = importlib.util.spec_from_file_location("qikvrt_lean_v2_m68000_d3_compiler", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class V2D3CompilerTests(unittest.TestCase):
    def test_exact_machine_code(self):
        self.assertEqual(mod.MACHINE.hex(), "0c020002620a670452024e7574004e7570014e75")

    def test_exhaustive_valid_projection(self):
        report = mod.verify()
        self.assertEqual(report["valid_state_tuples_verified"], 3072)
        self.assertTrue(report["d3_preserved"])

    def test_each_phase_advances_mod_three(self):
        for phase in range(3):
            d0, d2, d3, _ = mod.execute(mod.MACHINE, 3, phase, 0x7F)
            self.assertEqual((d0, d2, d3), (3, (phase + 1) % 3, 0x7F))

    def test_invalid_phase_fails_closed_and_preserves_d3(self):
        for phase in range(3, 256):
            d0, _d2, d3, _ = mod.execute(mod.MACHINE, 0, phase, 0xA5)
            self.assertEqual(d0, 1)
            self.assertEqual(d3, 0xA5)

    def test_frozen_lean_source_contains_required_theorems(self):
        text = LEAN.read_text(encoding="utf-8")
        self.assertIn("theorem d3_projection_fixed_under_step", text)
        self.assertIn("theorem d3_projection_fixed_under_any_finite_trace", text)
        self.assertIn("theorem one_ied_cycle_returns_phase_and_preserves_d3", text)
        self.assertIn("def Decision.code", (LEAN.parent / "AuthorityMirrorWitness.lean").read_text(encoding="utf-8"))

    def test_no_physical_claim(self):
        report = mod.verify()
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["physical_speedup_measured"])


class ExactSubjectKernelWorkflowTests(unittest.TestCase):
    """Synthetic receipt fixtures test binding, never substitute for Lean execution."""

    WORKFLOW = ".github/workflows/qikvrt_lean_v2_m68000_d3.yml"

    @classmethod
    def setUpClass(cls):
        import textwrap
        cls.workflow = (ROOT / cls.WORKFLOW).read_text(encoding="utf-8")
        cls.receipt_code = textwrap.dedent(cls.workflow.split(
            "          # BEGIN_EXACT_SUBJECT_KERNEL_RECEIPT\n", 1
        )[1].split("          # END_EXACT_SUBJECT_KERNEL_RECEIPT", 1)[0])

    def test_head_checkout_is_explicit_and_permissions_remain_read_only(self):
        self.assertIn("ref: ${{ github.event.pull_request.head.sha || github.sha }}", self.workflow)
        self.assertIn("EXPECTED_HEAD: ${{ github.event.pull_request.head.sha || github.sha }}", self.workflow)
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pull_request_target:", self.workflow)

    def test_job_environment_uses_only_pre_runner_contexts(self):
        import re
        environment = self.workflow.split("    env:\n", 1)[1].split("    steps:\n", 1)[0]
        allowed = {"github", "needs", "strategy", "matrix", "vars", "secrets", "inputs"}
        for expression in re.findall(r"\$\{\{(.*?)\}\}", environment):
            for context in re.findall(r"\b([A-Za-z_][A-Za-z_0-9]*)\.", expression):
                # The only expressions used here are github.* chains.
                if context not in {"event", "pull_request", "head", "base"}:
                    self.assertIn(context, allowed)
        self.assertNotIn("runner.", environment)
        self.assertIn("path: ${{ env.EVIDENCE_DIR }}/", self.workflow)

    def test_megast_and_terminal_events_cover_pr_and_main(self):
        events = self.workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        pr, push = events.split("  push:", 1)
        for block in (pr, push):
            for path in ("distribution/qikvrt-megast/**", "src/cloud_transputer/**",
                         "deploy/universal-terminal/**", self.WORKFLOW):
                self.assertIn('"' + path + '"', block)
        self.assertIn("branches: [main]", push)

    def test_proof_and_frozen_source_gates_are_not_bypassed(self):
        self.assertIn("if: github.event_name == 'pull_request'", self.workflow)
        self.assertIn('git diff --exit-code "$EXPECTED_BASE" HEAD --', self.workflow)
        self.assertLess(self.workflow.index("lake clean"), self.workflow.index("lake build 2>&1"))
        for script in ("audit_lean_axioms.py", "audit_completion_axioms.py", "audit_proof_escapes.py",
                       "materialize_completion.py --check", "render_completion_proof_map.py --check",
                       "render_completion_verification_report.py --check", "validate_completion_claim_graph.py",
                       "validate_effect_ack_claims.py"):
            self.assertIn("python3 scripts/" + script, self.workflow)
        self.assertNotIn("continue-on-error:", self.workflow)
        self.assertLess(self.workflow.index("Reject proof-hole syntax"), self.workflow.index("Seal exact-subject"))
        self.assertIn("if: always()", self.workflow)

    def exercise_receipt(self, *, head="1" * 40, tree="2" * 40,
                         expected="1" * 40, dirty=False, changes=None, missing=None,
                         environment=None, existing=False):
        import contextlib
        import hashlib
        import io
        import json
        import os
        import subprocess
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = root / self.WORKFLOW
            workflow.parent.mkdir(parents=True)
            workflow.write_text(self.workflow, encoding="utf-8")
            lock = root / "formalization/QIKVRT_Formalization_v2.0/lean-toolchain"
            lock.parent.mkdir(parents=True)
            lock.write_text("leanprover/lean4:v4.19.0\n", encoding="utf-8")
            evidence = root / "evidence"
            evidence.mkdir()
            names = ["d3_projection_fixed_under_step", "d3_projection_fixed_under_any_finite_trace",
                     "one_ied_cycle_returns_phase_and_preserves_d3"]
            contents = {
                "lake-version.log": "Lake version 5.0.0-6caaee8 (Lean version 4.19.0)\n",
                "lean-version.log": "Lean (version 4.19.0, fixture, Release)\n",
                "lean-githash.log": "3" * 40 + "\n",
                "lake-build.log": "synthetic fixture: not real kernel evidence\n",
                "proof-audits.log": "synthetic fixture: binding tests only\n",
                "d3-axioms.lean": "-- synthetic fixture\n",
                "d3-axioms.log": "\n".join("'QIKVRT.V2.D3FixedPoint." + name +
                     "' does not depend on any axioms" for name in names) + "\n",
                "compiler-report.json": json.dumps({"valid_state_tuples_verified": 3072,
                    "invalid_phase_values_fail_closed": 253, "d3_preserved": True,
                    "physical_m68000_execution_observed": False}),
            }
            contents.update(changes or {})
            for name, text in contents.items():
                if name == "toolchain":
                    lock.write_text(text, encoding="utf-8")
                elif name != missing:
                    (evidence / name).write_text(text, encoding="utf-8")
            if existing:
                (evidence / "kernel-receipt.json").write_text("existing evidence\n")
            env = {"EXPECTED_HEAD": expected, "EVIDENCE_DIR": str(evidence),
                   "GITHUB_REPOSITORY": "fixture/qik-vrt", "GITHUB_RUN_ID": "123",
                   "GITHUB_RUN_ATTEMPT": "1", "GITHUB_EVENT_NAME": "pull_request"}
            env.update(environment or {})
            files = [self.WORKFLOW, lock.relative_to(root).as_posix()]

            def output(args, **kwargs):
                if args == ["git", "rev-parse", "HEAD"]:
                    return head + "\n"
                if args == ["git", "rev-parse", "HEAD^{tree}"]:
                    return tree + "\n"
                if args[:4] == ["git", "ls-files", "-z", "--"]:
                    return ("\0".join(files) + "\0").encode()
                raise AssertionError(args)

            def run(args, **kwargs):
                self.assertEqual(args, ["git", "diff", "--exit-code", "HEAD", "--"])
                self.assertTrue(kwargs.get("check"))
                if dirty:
                    raise subprocess.CalledProcessError(1, args)
                return subprocess.CompletedProcess(args, 0)

            with patch.dict(os.environ, env, clear=True), patch.object(Path, "cwd", return_value=root), \
                    patch.object(subprocess, "check_output", side_effect=output), \
                    patch.object(subprocess, "run", side_effect=run), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(self.receipt_code, self.WORKFLOW + ":receipt", "exec"), {})
            result = json.loads((evidence / "kernel-receipt.json").read_text())
            for item in result["outputs"]:
                self.assertEqual(item["sha256"], hashlib.sha256((evidence / item["path"]).read_bytes()).hexdigest())
            return result

    def test_receipt_binds_subject_bytes_and_retains_effect_boundary(self):
        result = self.exercise_receipt()
        self.assertEqual(result["source_sha"], "1" * 40)
        self.assertEqual(result["source_tree"], "2" * 40)
        self.assertEqual(result["run_id"], "123")
        self.assertEqual(len(result["outputs"]), 8)
        self.assertEqual(len(result["d3_axioms_by_theorem"]), 3)
        for field in ("effect_ack_done", "physical_atari_boot", "independent_code_owner_approval",
                      "predecessor_evidence_transfer"):
            self.assertIs(result[field], False)

    def test_head_or_tree_drift_fails_closed(self):
        for args in ({"head": "4" * 40}, {"tree": "not-a-tree"}, {"expected": "main"}):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.exercise_receipt(**args)

    def test_dirty_tracked_source_fails_closed(self):
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError):
            self.exercise_receipt(dirty=True)

    def test_wrong_toolchain_or_executable_identity_fails_closed(self):
        for changes in ({"toolchain": "leanprover/lean4:v4.20.0\n"},
                        {"lean-version.log": "Lean (version 4.20.0, fixture)\n"},
                        {"lean-githash.log": "unknown\n"}):
            with self.subTest(changes=changes), self.assertRaises(SystemExit):
                self.exercise_receipt(changes=changes)

    def test_missing_duplicate_or_nonempty_axiom_dependencies_fail_closed(self):
        for text in ("", "unexpected\n", "'QIKVRT.V2.D3FixedPoint.d3_projection_fixed_under_step' depends on axioms: [sorryAx]\n"):
            with self.subTest(text=text), self.assertRaises(SystemExit):
                self.exercise_receipt(changes={"d3-axioms.log": text})

    def test_incomplete_machine_projection_fails_closed(self):
        with self.assertRaises(SystemExit):
            self.exercise_receipt(changes={"compiler-report.json": "{}"})

    def test_missing_log_or_native_run_binding_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            self.exercise_receipt(missing="proof-audits.log")
        with self.assertRaises(SystemExit):
            self.exercise_receipt(environment={"GITHUB_RUN_ID": ""})

    def test_receipt_never_overwrites_previous_bytes(self):
        with self.assertRaises(FileExistsError):
            self.exercise_receipt(existing=True)


if __name__ == "__main__":
    unittest.main()
