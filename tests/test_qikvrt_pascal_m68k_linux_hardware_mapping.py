from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/PASCAL_M68K_LINUX_HARDWARE_MAPPING_V1.json"
TOOL = ROOT / "tools/qikvrt_pascal_m68k_linux_reobservation.py"
WORKFLOW = ROOT / ".github/workflows/qikvrt_pascal_m68k_linux_hardware_mapping.yml"
WORK_UNIT = ROOT / "state/work_units/PASCAL_M68K_LINUX_HARDWARE_MAPPING_V1.json"
DOC = ROOT / "docs/PASCAL_M68K_LINUX_HARDWARE_MAPPING_V1.md"


class PascalM68kLinuxHardwareMappingTests(unittest.TestCase):
    def test_stack_and_toolchain_are_exactly_pinned(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["stack_parent_pr"], 895)
        self.assertEqual(policy["stack_parent_head"], "6a104554c72f189758944c55ce22f9ce0025e11d")
        self.assertEqual(policy["stack_parent_tree"], "5051694c5bc6eacb44214fb2aa3209fd74f2bfbd")
        toolchain = policy["toolchain"]
        self.assertEqual(toolchain["cross_compiler_source_commit"], "6c4d218b8d1c00cec55f889ab5fab9639a8159fe")
        self.assertEqual(toolchain["cpu_target"], "m68k")
        self.assertEqual(toolchain["os_target"], "linux")
        self.assertEqual(toolchain["binutils_prefix"], "m68k-linux-gnu-")
        self.assertEqual(toolchain["emulator"], "qemu-m68k")

    def test_tool_requires_m68k_elf_qemu_and_literal_binding(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        for marker in (
            '"-Tlinux"',
            '"-Pm68k"',
            '"-XPm68k-linux-gnu-"',
            '"qemu-m68k"',
            '"m68k-linux-gnu-readelf"',
            'os.environ.get("QIKVRT_HEAD_SHA", "LOCAL")',
            'os.environ.get("QIKVRT_TREE_SHA", "LOCAL")',
            '"m68k_machine_bytes_produced": True',
            '"m68k_emulator_execution_observed": True',
        ):
            self.assertIn(marker, source)

    def test_workflow_builds_pinned_cross_compiler_without_schedule(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("6c4d218b8d1c00cec55f889ab5fab9639a8159fe", workflow)
        self.assertIn("CPU_TARGET=m68k", workflow)
        self.assertIn("OS_TARGET=linux", workflow)
        self.assertIn("binutils-m68k-linux-gnu", workflow)
        self.assertIn("qemu-user", workflow)
        self.assertIn("QIKVRT_HEAD_SHA=%s", workflow)
        self.assertIn("QIKVRT_TREE_SHA=%s", workflow)
        self.assertIn("include-hidden-files: true", workflow)

    def test_claims_separate_isa_emulator_tos_and_physical_hardware(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        boundaries = policy["claim_boundaries"]
        self.assertEqual(boundaries["m68k_machine_bytes_produced"], "PENDING_EXECUTION")
        self.assertEqual(boundaries["m68k_emulator_execution_observed"], "PENDING_EXECUTION")
        for key in (
            "atari_tos_binary_produced",
            "atari_tos_execution_observed",
            "physical_m68000_execution_observed",
            "physical_megast_execution_observed",
            "borland_turbo_pascal_compiler_executed",
            "embarcadero_delphi_compiler_executed",
            "effect_ack_done",
            "pass",
            "final_pass",
        ):
            self.assertFalse(boundaries[key], key)
        self.assertEqual(boundaries["external_effect"], "NONE")

    def test_work_unit_and_document_bind_next_atari_ring(self) -> None:
        work = json.loads(WORK_UNIT.read_text(encoding="utf-8"))
        self.assertEqual(work["stack_parent_pr"], 895)
        self.assertTrue(work["machine_owned"])
        self.assertFalse(work["authority_effect"])
        self.assertFalse(work["physical_hardware_execution"])
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("M68K Linux ABI", text)
        self.assertIn("Atari TOS executable", text)
        self.assertIn("AD/DA", text)
        self.assertIn("Wurzeln", text)


if __name__ == "__main__":
    unittest.main()
