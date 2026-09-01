# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "qikvrt_mlp_tos_hatari.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_mlp_tos_hatari", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

EXPECTED_BINARY_SHA256 = "5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e"
EXPECTED_TEXT_SHA256 = "0168fc5505b074889e5ca8b02015259152ec8daafb76db7ed91e7d3f3968b5b3"
EXPECTED_FRAME_SHA256 = "8f3b74fd6d2868ac24fb22ae160b1e2806650f9a8e84978a7a04c0af30a94734"


class MlpTosHatariTests(unittest.TestCase):
    def test_deterministic_binary_header_size_and_digest(self):
        image_a = MODULE.build_tos_prg()
        image_b = MODULE.build_tos_prg()
        self.assertEqual(image_a, image_b)
        self.assertEqual(len(image_a), 341)
        self.assertEqual(hashlib.sha256(image_a).hexdigest(), EXPECTED_BINARY_SHA256)
        header = struct.unpack(">HLLLLLLH", image_a[:28])
        magic, text_size, data_size, bss_size, symbols, reserved, flags, absolute = header
        self.assertEqual(magic, 0x601A)
        self.assertEqual(text_size, len(image_a) - 28)
        self.assertEqual((data_size, bss_size, symbols, reserved, flags), (0, 0, 0, 0, 0))
        self.assertEqual(absolute, 1)
        self.assertEqual(hashlib.sha256(image_a[28:]).hexdigest(), EXPECTED_TEXT_SHA256)

    def test_binary_binds_leaf_request_and_fail_closed_gemdos_surface(self):
        text = MODULE.build_text()
        self.assertEqual(text.count(MODULE.MLP_LEAF), 1)
        self.assertEqual(text.count(MODULE.TEMP_PATH), 1)
        self.assertEqual(text.count(MODULE.OPEN_PATH), 1)
        self.assertEqual(text.count(MODULE.REQUEST_FRAME), 1)
        self.assertEqual(hashlib.sha256(MODULE.REQUEST_FRAME).hexdigest(), EXPECTED_FRAME_SHA256)
        for function in (0x003C, 0x0040, 0x003E, 0x0056, 0x0041):
            self.assertIn(struct.pack(">HHH", 0x3F3C, function, 0x4E41), text)
        self.assertIn(struct.pack(">HHHHH", 0x3F3C, 0, 0x3F3C, 0x004C, 0x4E41), text)
        self.assertIn(struct.pack(">HHHHH", 0x3F3C, 1, 0x3F3C, 0x004C, 0x4E41), text)

    def test_committed_binary_and_checksum_match_builder(self):
        committed = (ROOT / "MLP.TOS" / "MLP.TOS").read_bytes()
        self.assertEqual(committed, MODULE.build_tos_prg())
        checksum = (ROOT / "MLP.TOS" / "MLP.TOS.sha256").read_text(encoding="utf-8")
        self.assertEqual(checksum, f"{EXPECTED_BINARY_SHA256}  MLP.TOS\n")

    def test_delivery_contract_matches_exact_binary_and_boundaries(self):
        contract = json.loads(
            (ROOT / "MLP.TOS" / "MLP_TOS_HATARI_V1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["schema"], "qikvrt_mlp_tos_hatari_continuous_delivery_v1")
        self.assertEqual(contract["binary"]["bytes"], 341)
        self.assertEqual(contract["binary"]["sha256"], EXPECTED_BINARY_SHA256)
        self.assertEqual(contract["binary"]["text_sha256"], EXPECTED_TEXT_SHA256)
        self.assertEqual(
            contract["semantic_binding"]["request_frame_sha256"], EXPECTED_FRAME_SHA256
        )
        self.assertEqual(contract["semantic_binding"]["m68000_leaf_hex"], MODULE.MLP_LEAF.hex())
        boundary = contract["evidence_boundary"]
        self.assertTrue(boundary["committed_binary_is_deterministically_materialized"])
        self.assertFalse(boundary["static_commit_claims_hatari_observed"])
        self.assertFalse(boundary["physical_megast_execution"])
        self.assertFalse(boundary["effect_ack_done"])
        self.assertEqual(boundary["external_effect"], "NONE")

    def test_existing_mlp_sources_match_binary_semantics(self):
        asm = (ROOT / "runtime" / "megast" / "mlp_kernel_68000.s").read_text(encoding="utf-8")
        for instruction in ("moveq   #3,d1", "moveq   #1,d2", "moveq   #3,d0", "rts"):
            self.assertIn(instruction, asm)
        for source_path in (
            ROOT / "runtime" / "megast" / "mlp_main_ansic.c",
            ROOT / "runtime" / "host" / "mlp_host_ansic.c",
        ):
            source = source_path.read_text(encoding="utf-8")
            for line in (
                '"QIKMLP1\\r\\n"',
                '"PROGRAM MLP\\r\\n"',
                '"ACTION OPEN_FIREFOX\\r\\n"',
                '"STATE REQUESTED\\r\\n"',
                '"AUTHORITY MISSING\\r\\n"',
                '"EFFECT REQUESTED\\r\\n"',
                '"END\\r\\n"',
            ):
                self.assertIn(line, source)

    def test_launcher_is_exact_profile_and_fail_closed(self):
        launcher = (ROOT / "MLP.TOS" / "Hatari").read_text(encoding="utf-8")
        for token in (
            "set -eu",
            "MLP.TOS digest mismatch",
            "EmuTOS ROM digest mismatch",
            "Hatari v2.4.1",
            "--machine megast",
            "--cpulevel 0",
            "--cpuclock 8",
            "--addr24 on",
            "--memsize 1",
            "--auto 'C:\\MLP.TOS'",
            "cmp \"$expected_frame\" \"$drive/C/MLP.OPEN\"",
            "MEGAST_VIRTUAL_EXECUTION_OBSERVED=true",
            "PHYSICAL_MEGAST_EXECUTION=false",
            "EFFECT_ACK_DONE=false",
        ):
            self.assertIn(token, launcher)

    def test_workflow_is_event_driven_scheduled_and_artifact_bound(self):
        workflow = (
            ROOT / ".github" / "workflows" / "qikvrt_mlp_tos_hatari.yml"
        ).read_text(encoding="utf-8")
        for token in (
            "pull_request:",
            "push:",
            "- main",
            "workflow_dispatch:",
            "schedule:",
            "cron: '23 3 * * *'",
            "contents: read",
            "cancel-in-progress: true",
            "cmp MLP.TOS/MLP.TOS /tmp/qikvrt-mlp-tos/MLP.TOS",
            "MLP.TOS/Hatari",
            "qikvrt_mlp_tos_hatari_execution_receipt_v1",
            "actions/upload-artifact@",
            "retention-days: 30",
        ):
            self.assertIn(token, workflow)

    def test_cli_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "MLP.TOS"
            receipt = Path(tmp) / "receipt.json"
            subprocess.run(
                [
                    "python3",
                    str(MODULE_PATH),
                    "--output",
                    str(output),
                    "--receipt",
                    str(receipt),
                    "--source-head",
                    "a" * 40,
                    "--source-tree",
                    "b" * 40,
                ],
                check=True,
                cwd=ROOT,
            )
            self.assertEqual(output.read_bytes(), (ROOT / "MLP.TOS" / "MLP.TOS").read_bytes())
            parsed = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(parsed["source_head"], "a" * 40)
            self.assertEqual(parsed["source_tree"], "b" * 40)
            self.assertEqual(parsed["binary_sha256"], EXPECTED_BINARY_SHA256)
            self.assertFalse(parsed["effect_boundary"]["observed"])
            self.assertFalse(parsed["effect_boundary"]["acknowledged"])


if __name__ == "__main__":
    unittest.main()
