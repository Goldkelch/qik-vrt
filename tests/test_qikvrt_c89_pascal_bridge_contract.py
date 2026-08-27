from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/C89_TURBO_PASCAL_DELPHI_BRIDGE_V1.json"
UNIT = ROOT / "pascal/qikvrt_atari_browser_pas.pas"
UNIT_ALIAS = ROOT / "pascal/qikvrtataribrowserpas.pas"
TEST_PROGRAM = ROOT / "tests/pascal/test_qikvrt_atari_browser_pas.pas"
HARNESS = ROOT / "tools/qikvrt_c89_pascal_bridge.py"
WORKFLOW = ROOT / ".github/workflows/qikvrt_c89_turbo_pascal_delphi_bridge.yml"
WORK_UNIT = ROOT / "state/work_units/C89_TURBO_PASCAL_DELPHI_BRIDGE_V1.json"
DOC = ROOT / "docs/C89_TURBO_PASCAL_DELPHI_AD_DA_BRIDGE_V1.md"


class C89TurboPascalDelphiBridgeContractTests(unittest.TestCase):
    def test_source_binding_is_exact_and_current_main_bound(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(
            policy["authority_base_head"],
            "4e9137ec9887ed23cf76f435839827329c5592fe",
        )
        self.assertEqual(
            policy["authority_base_tree"],
            "9f82a4ef226d9151ba03806105eae589b3ca0946",
        )
        source = policy["source_c89"]
        self.assertEqual(source["pull_request"], 848)
        self.assertEqual(
            source["head"],
            "cba166e45a0ea4b5d5dd2ef9cde0ad96ff57554b",
        )
        self.assertEqual(
            source["tree"],
            "23586fd719627a6e508724239a71b71fea7e9847",
        )
        self.assertEqual(source["source_blob"], "bca759d4813b9d89754e052ddcf892e9f811eca4")
        self.assertEqual(source["header_blob"], "50f2b596eb8b8b16aa5c327037d726bfdb3a1c2a")

    def test_pascal_source_is_fixed_memory_and_dual_dialect_subset(self) -> None:
        source = UNIT.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in (
            "ansistring",
            "class(",
            "class ",
            "generic ",
            "specialize ",
            "new(",
            "dispose(",
            "setlength(",
            "getmem(",
            "freemem(",
            "raise ",
            "try\n",
            "except\n",
        ):
            self.assertNotIn(forbidden, lowered)
        for required in (
            "ResponseCapacity = 8192",
            "TextCapacity = 4096",
            "LinkCapacity = 16",
            "function ParseUrl",
            "function BuildHttpGet",
            "function ParseHttpResponse",
            "function RenderHtml",
            "function DocumentTextContains",
        ):
            self.assertIn(required, source)

    def test_compiler_lookup_alias_is_byte_identical_and_registered(self) -> None:
        self.assertTrue(UNIT_ALIAS.is_file())
        self.assertEqual(UNIT.read_bytes(), UNIT_ALIAS.read_bytes())
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        lookup = policy["compiler_lookup"]
        self.assertEqual(lookup["declared_unit"], "QikVrtAtariBrowserPas")
        self.assertEqual(
            lookup["normalized_lookup_alias"],
            "pascal/qikvrtataribrowserpas.pas",
        )
        self.assertTrue(lookup["alias_must_be_byte_identical"])
        self.assertEqual(
            lookup["failure_prevented"],
            "FPC_UNIT_LOOKUP_FILENAME_MISMATCH",
        )

    def test_semantic_vectors_cover_c89_reference_surface(self) -> None:
        tests = TEST_PROGRAM.read_text(encoding="utf-8")
        for marker in (
            "http://127.0.0.1:8771/a/b?x=1#ignored",
            "https://example.org/",
            "HTTP/1.0 200 OK",
            "QIK &amp; VRT",
            "hidden script",
            "hidden style",
            'href="/two"',
            "A  B",
            "not http",
            "<p unterminated",
        ):
            self.assertIn(marker, tests)

    def test_harness_compiles_executes_both_modes_and_compares_receipts(self) -> None:
        source = HARNESS.read_text(encoding="utf-8")
        self.assertIn('compile_mode(root, build, fpc, "tp")', source)
        self.assertIn('compile_mode(root, build, fpc, "delphi")', source)
        self.assertIn('f"-M{mode}"', source)
        self.assertIn('normalized_semantic_output_equal', source)
        self.assertIn('borland_turbo_pascal_compiler_executed', source)
        self.assertIn('embarcadero_delphi_compiler_executed', source)
        self.assertIn('m68000_binary_executed', source)

    def test_workflow_is_literal_head_bound_and_artifact_preserving(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("github.event.pull_request.head.sha || github.sha", workflow)
        self.assertIn("git rev-parse --verify HEAD^{commit}", workflow)
        self.assertIn("git rev-parse --verify HEAD^{tree}", workflow)
        self.assertIn("pascal/qikvrtataribrowserpas.pas", workflow)
        self.assertIn("fp-compiler", workflow)
        self.assertIn("qikvrt_c89_pascal_bridge.py", workflow)
        self.assertIn("include-hidden-files: true", workflow)

    def test_claim_boundaries_and_work_unit_do_not_invent_target_execution(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        boundaries = policy["claim_boundaries"]
        for key in (
            "source_translation_is_binary_identity",
            "fpc_tp_mode_is_borland_turbo_pascal_execution",
            "fpc_delphi_mode_is_embarcadero_delphi_execution",
            "host_binary_is_m68000_binary",
            "m68000_binary_executed",
            "physical_megast_execution",
            "firefox_equivalence",
            "effect_ack_done",
            "pass",
            "final_pass",
        ):
            self.assertFalse(boundaries[key], key)
        self.assertEqual(boundaries["external_effect"], "NONE")
        work = json.loads(WORK_UNIT.read_text(encoding="utf-8"))
        self.assertEqual(work["issue"], 888)
        self.assertTrue(work["machine_owned"])
        self.assertIn("pascal/qikvrtataribrowserpas.pas", work["scope"])
        self.assertFalse(work["authority_effect"])
        self.assertFalse(work["deployment"])
        self.assertFalse(work["effect_ack_done"])
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("Divide-and-Conquer", doc)
        self.assertIn("A/D", doc)
        self.assertIn("D/A", doc)
        self.assertIn("Zürcher", doc)


if __name__ == "__main__":
    unittest.main()
