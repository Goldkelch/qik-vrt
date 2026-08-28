# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import itertools
import pathlib
import re
import unittest

from tools.qikvrt_mesh_quadratic_codec import (
    DeterministicDisposition,
    deserialize_lanes,
    deterministic_disposition,
    frame_bits,
    ideal_raw_frame_rate,
    lane_count,
    serial_payload_handshakes,
    serialize_lanes,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
VHDL = ROOT / "hardware/vhdl/qikvrt_mesh_quadratic_codec.vhd"
ADMISSION_VHDL = ROOT / "hardware/vhdl/qikvrt_deterministic_admission_gate.vhd"
CONTRACT = ROOT / "state/mesh/QIKVRT_MESH_NONPOLLING_QUADRATIC_CODEC_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_mesh_nonpolling_quadratic_codec.yml"
PROTOTYPE = ROOT / "hardware/fpga/ice40up5k_breakout/PROTOTYPE_REQUIREMENTS.json"
PATENT = ROOT / "state/patent/QIKVRT_DETERMINISTIC_MESH_DISCLOSURE_V1.json"
PRIOR_ART = ROOT / "state/patent/QIKVRT_DETERMINISTIC_MESH_PRIOR_ART_SEARCH_V1.json"


class QuadraticCodecTests(unittest.TestCase):
    def test_quadratic_row_major_round_trip(self) -> None:
        for nodes in (1, 2, 3, 4):
            lanes = tuple((index * 17 + 3) % 256 for index in range(lane_count(nodes)))
            stream = serialize_lanes(lanes, nodes, 8)
            self.assertEqual(len(stream), frame_bits(nodes, 8))
            self.assertEqual(deserialize_lanes(stream, nodes, 8), lanes)

    def test_codec_rejects_partial_or_noncanonical_frames(self) -> None:
        with self.assertRaises(ValueError):
            serialize_lanes((1, 2, 3), 2, 8)
        with self.assertRaises(ValueError):
            deserialize_lanes((0,) * 31, 2, 8)
        with self.assertRaises(ValueError):
            deserialize_lanes((0,) * 31 + (2,), 2, 8)

    def test_serial_throughput_unit_is_payload_frames_not_receipts(self) -> None:
        self.assertEqual(serial_payload_handshakes(2, 8), 32)
        self.assertEqual(ideal_raw_frame_rate(12_000_000, 2, 8), 375_000)
        self.assertEqual(ideal_raw_frame_rate(3_500_000_000, 2, 8), 109_375_000)

    def test_deterministic_admission_is_total_and_fail_closed(self) -> None:
        self.assertEqual(deterministic_disposition(False, False, False), DeterministicDisposition.CONTINUE)
        self.assertEqual(deterministic_disposition(True, True, True), DeterministicDisposition.HOLD)
        self.assertEqual(deterministic_disposition(True, True, False), DeterministicDisposition.ACCEPT)
        self.assertEqual(deterministic_disposition(True, False, False), DeterministicDisposition.BLOCK)
        with self.assertRaises(ValueError):
            deterministic_disposition(1, True, False)

    def test_deterministic_admission_exhaustively_covers_all_boolean_inputs(self) -> None:
        expected = {
            (False, False, False): DeterministicDisposition.CONTINUE,
            (False, False, True): DeterministicDisposition.CONTINUE,
            (False, True, False): DeterministicDisposition.CONTINUE,
            (False, True, True): DeterministicDisposition.CONTINUE,
            (True, False, False): DeterministicDisposition.BLOCK,
            (True, False, True): DeterministicDisposition.HOLD,
            (True, True, False): DeterministicDisposition.ACCEPT,
            (True, True, True): DeterministicDisposition.HOLD,
        }
        observed = {
            args: deterministic_disposition(*args)
            for args in itertools.product((False, True), repeat=3)
        }
        self.assertEqual(observed, expected)

    def test_all_workflows_are_non_polling(self) -> None:
        for workflow in (ROOT / ".github/workflows").glob("*.yml"):
            text = workflow.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"^  schedule:\\s*$", text, re.MULTILINE), workflow)
            self.assertIsNone(re.search(r"^    - cron:", text, re.MULTILINE), workflow)

    def test_vhdl_is_clocked_synthesis_oriented_rtl(self) -> None:
        text = VHDL.read_text(encoding="utf-8").lower()
        self.assertIn("entity qikvrt_mesh_quadratic_codec", text)
        self.assertIn("constant frame_bits", text)
        self.assertIn("rising_edge(clk)", text)
        self.assertIn("nodes * nodes * word_bits", text)
        self.assertIn("serial_payload_handshakes_per_frame", text)
        self.assertNotIn("\n  wait", text)
        self.assertNotIn(" after ", text)

    def test_admission_gate_has_no_sampling_path(self) -> None:
        text = ADMISSION_VHDL.read_text(encoding="utf-8").lower()
        self.assertIn("entity qikvrt_deterministic_admission_gate", text)
        self.assertIn("decision_hold", text)
        self.assertIn("decision_accept", text)
        self.assertIn("decision_block", text)
        self.assertNotIn("uniform", text)
        self.assertNotIn("math_real", text)

    def test_contract_keeps_physical_claims_open(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["operation_model"], "EVENT_DRIVEN_NO_PERIODIC_POLLING")
        self.assertEqual(contract["quadratic_scaling"]["lane_count"], "N*N")
        self.assertEqual(contract["serial_transport_accounting"]["payload_handshakes_per_complete_frame"], "N*N*WORD_BITS")
        self.assertEqual(contract["serial_transport_accounting"]["prohibited_inference"], "RAW_FRAME_RATE_IS_NOT_RECEIPT_RATE_OR_COGNITIVE_WORKLOAD_THROUGHPUT")
        self.assertEqual(contract["deterministic_admission"]["forbidden_mechanisms"], ["sampling", "random_choice", "implicit_ambiguity_resolution"])
        self.assertEqual(contract["hardware"]["admission_vhdl_source"], "hardware/vhdl/qikvrt_deterministic_admission_gate.vhd")
        self.assertEqual(contract["canonical_mapping"]["round_trip"], "deserialize(serialize(lanes))=lanes")
        self.assertFalse(contract["hardware"]["physical_manufacture_or_measurement"])

    def test_entrypoint_and_event_workflow_bind_the_same_contract(self) -> None:
        self.assertIn("NON-POLLING MESH OPERATION", (ROOT / "AI").read_text(encoding="utf-8"))
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("push:", workflow)
        self.assertNotIn("\n  schedule:", workflow)

    def test_prototype_target_has_concrete_constraints_and_open_evidence_boundary(self) -> None:
        value = json.loads(PROTOTYPE.read_text(encoding="utf-8"))
        self.assertEqual(value["target"], {"board": "iCE40UP5K-B-EVN", "device": "iCE40UP5K", "package": "SG48"})
        self.assertIn("hardware/vhdl/qikvrt_deterministic_admission_gate.vhd", value["rtl"])
        self.assertIn("set_io clock_12mhz 35", (PROTOTYPE.parent / "qikvrt_mesh_prototype.pcf").read_text(encoding="utf-8"))
        self.assertFalse(value["claims"]["physical_prototype_observed"])

    def test_patent_material_is_technical_and_does_not_preclaim_a_legal_result(self) -> None:
        disclosure = json.loads(PATENT.read_text(encoding="utf-8"))
        prior_art = json.loads(PRIOR_ART.read_text(encoding="utf-8"))
        self.assertFalse(disclosure["claims"]["patentability_determined"])
        self.assertFalse(disclosure["claims"]["application_filed"])
        self.assertEqual(prior_art["status"], "PRELIMINARY_SEARCH_NOT_A_NOVELTY_OPINION")
        self.assertFalse(prior_art["claims"]["novelty_established"])


if __name__ == "__main__":
    unittest.main()
