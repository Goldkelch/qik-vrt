# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import hashlib
import importlib.util
import itertools
import pathlib
import re
import tempfile
import unittest

from tools.qikvrt_mesh_quadratic_codec import (
    DeterministicDisposition,
    deserialize_lanes,
    deterministic_disposition,
    frame_digest,
    frame_bits,
    ideal_raw_frame_rate,
    lane_count,
    next_expected_sequence,
    serial_framed_handshakes,
    serial_payload_handshakes,
    deserialize_framed_lanes,
    serialize_framed_lanes,
    serialize_lanes,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
VHDL = ROOT / "hardware/vhdl/qikvrt_mesh_quadratic_codec.vhd"
CODEC_TESTBENCH = ROOT / "hardware/vhdl/qikvrt_mesh_quadratic_codec_tb.vhd"
PROTOTYPE_TOP = ROOT / "hardware/fpga/ice40up5k_breakout/qikvrt_mesh_prototype_top.vhd"
PROTOTYPE_TOP_TESTBENCH = ROOT / "hardware/fpga/ice40up5k_breakout/qikvrt_mesh_prototype_top_tb.vhd"
ADMISSION_VHDL = ROOT / "hardware/vhdl/qikvrt_deterministic_admission_gate.vhd"
ADMISSION_TESTBENCH = ROOT / "hardware/vhdl/qikvrt_deterministic_admission_gate_tb.vhd"
ADMISSION_TEST_CONTRACT = ROOT / "tools/qikvrt_vhdl_admission_gate_contract.py"
CONTRACT = ROOT / "state/mesh/QIKVRT_MESH_NONPOLLING_QUADRATIC_CODEC_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_mesh_nonpolling_quadratic_codec.yml"
LIVE_STATUS_WORKFLOW = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"
EXECUTOR_WORKFLOW = ROOT / ".github/workflows/qikvrt_workflow_executor.yml"
SYSTEM_VERIFICATION_WORKFLOW = ROOT / ".github/workflows/qikvrt_real_mesh_system_verification.yml"
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

    def test_session_bound_framed_codec_round_trip_and_wire_accounting(self) -> None:
        lanes = (0x31, 0xA2, 0x17, 0xC4)
        session = 0x11223344
        frame = serialize_framed_lanes(lanes, 2, 8, session=session, sequence=0)
        self.assertEqual(len(frame), serial_framed_handshakes(2, 8))
        self.assertEqual(serial_framed_handshakes(2, 8), 104)
        self.assertEqual(
            deserialize_framed_lanes(
                frame, 2, 8, expected_session=session, expected_sequence=0
            ),
            lanes,
        )
        payload = serialize_lanes(lanes, 2, 8)
        self.assertEqual(
            frame_digest(session, 0, payload),
            sum(bit << index for index, bit in enumerate(frame[-16:])),
        )
        self.assertEqual(next_expected_sequence(0), 1)
        with self.assertRaises(ValueError):
            next_expected_sequence((1 << 16) - 1)

    def test_session_bound_codec_rejects_modeled_faults_and_context_mismatches(self) -> None:
        lanes = (0x31, 0xA2, 0x17, 0xC4)
        session = 0x11223344
        frame = serialize_framed_lanes(lanes, 2, 8, session=session, sequence=0)

        with self.assertRaises(ValueError):
            deserialize_framed_lanes(
                frame[:-1], 2, 8, expected_session=session, expected_sequence=0
            )
        with self.assertRaises(ValueError):
            deserialize_framed_lanes(
                frame[:9] + (1,) + frame[9:], 2, 8, expected_session=session, expected_sequence=0
            )

        reordered = list(frame)
        payload_start = 8 + 32 + 16
        left = next(index for index in range(payload_start, payload_start + 32) if reordered[index] == 0)
        right = next(index for index in range(payload_start, payload_start + 32) if reordered[index] == 1)
        reordered[left], reordered[right] = reordered[right], reordered[left]
        with self.assertRaises(ValueError):
            deserialize_framed_lanes(
                tuple(reordered), 2, 8, expected_session=session, expected_sequence=0
            )

        digest_mismatch = list(frame)
        digest_mismatch[-1] ^= 1
        with self.assertRaises(ValueError):
            deserialize_framed_lanes(
                tuple(digest_mismatch), 2, 8, expected_session=session, expected_sequence=0
            )
        with self.assertRaises(ValueError):
            deserialize_framed_lanes(
                frame, 2, 8, expected_session=session, expected_sequence=1
            )
        with self.assertRaises(ValueError):
            deserialize_framed_lanes(
                frame, 2, 8, expected_session=0x55667788, expected_sequence=0
            )

    def test_serial_throughput_unit_is_payload_frames_not_receipts(self) -> None:
        self.assertEqual(serial_payload_handshakes(2, 8), 32)
        self.assertEqual(serial_framed_handshakes(2, 8), 104)
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

    def test_all_workflows_have_no_scheduled_trigger(self) -> None:
        for workflow in (ROOT / ".github/workflows").glob("*.yml"):
            text = workflow.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"^  schedule:\\s*$", text, re.MULTILINE), workflow)
            self.assertIsNone(re.search(r"^    - cron:", text, re.MULTILINE), workflow)

    def test_terminal_observation_is_event_bound_and_artifact_preserved(self) -> None:
        live_status = LIVE_STATUS_WORKFLOW.read_text(encoding="utf-8")
        executor = EXECUTOR_WORKFLOW.read_text(encoding="utf-8")
        codec = WORKFLOW.read_text(encoding="utf-8")
        system_verification = SYSTEM_VERIFICATION_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("workflow_run:", live_status)
        self.assertIn("types: [completed]", live_status)
        self.assertIn("QIKVRT Mesh non-polling quadratic codec", live_status)
        self.assertIn("QIKVRT real multi-pair Mesh runtime", live_status)
        self.assertIn("QIKVRT real mesh system verification", live_status)
        self.assertIn("terminal-observation-receipt.json", live_status)
        self.assertIn("qikvrt-live-status-", live_status)
        self.assertNotIn("while :", live_status)
        self.assertNotIn("sleep ", live_status)
        self.assertNotIn(".workflow_runs[0:20]", live_status)

        self.assertIn("validate-dispatch-reobservation", executor)
        self.assertIn('gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${run_id}"', executor)
        self.assertNotIn("seq 1 12", executor)
        self.assertNotIn("sleep ", executor)
        self.assertNotIn("actions/workflows/${workflow_id}/runs?event=workflow_dispatch", executor)

        self.assertIn("ref: ${{ github.event.pull_request.head.sha || github.sha }}", codec)
        self.assertIn("QIKVRT_MESH_NONPOLLING_QUADRATIC_CODEC_RECEIPT_V1.json", codec)
        self.assertIn("qikvrt-mesh-nonpolling-quadratic-codec-", codec)
        self.assertIn("qikvrt-real-mesh-system-verification-", system_verification)
        self.assertIn("AUDIT_RECEIPT.json", system_verification)

    def test_vhdl_is_clocked_synthesis_oriented_rtl(self) -> None:
        text = VHDL.read_text(encoding="utf-8").lower()
        self.assertIn("entity qikvrt_mesh_quadratic_codec", text)
        self.assertIn("constant frame_bits", text)
        self.assertIn("constant frame_wire_bits", text)
        self.assertIn("constant frame_sync", text)
        self.assertIn("constant frame_session_bits", text)
        self.assertIn("function frame_digest", text)
        self.assertIn("rx_integrity_failure_o", text)
        self.assertIn("rx_session_context", text)
        self.assertIn("candidate_session = rx_session_context", text)
        self.assertIn("rx_session_context = session_i", text)
        self.assertIn("candidate_sequence = rx_expected_sequence", text)
        self.assertIn("sequence_exhausted", text)
        self.assertIn("candidate_digest = frame_digest", text)
        self.assertIn("is_binary(candidate_wire)", text)
        self.assertIn("rising_edge(clk)", text)
        self.assertIn("nodes * nodes * word_bits", text)
        self.assertIn("serial_payload_handshakes_per_frame", text)
        self.assertNotIn("\n  wait", text)
        self.assertNotIn(" after ", text)

    def test_vhdl_framing_testbench_and_top_are_fail_closed(self) -> None:
        testbench = CODEC_TESTBENCH.read_text(encoding="utf-8").lower()
        top = PROTOTYPE_TOP.read_text(encoding="utf-8").lower()
        top_testbench = PROTOTYPE_TOP_TESTBENCH.read_text(encoding="utf-8").lower()
        self.assertIn("entity qikvrt_mesh_quadratic_codec_tb", testbench)
        self.assertIn("digest mismatch must not validate", testbench)
        self.assertIn("sequence/replay mismatch must not validate", testbench)
        self.assertIn("session mismatch must not validate", testbench)
        self.assertIn("in-frame session context change must not validate", testbench)
        self.assertIn("framing fault must not validate", testbench)
        self.assertIn("inserted wire bit must not validate", testbench)
        self.assertIn("does not claim crc-16 detects arbitrary channel faults", testbench)
        self.assertIn("must never accept", testbench)
        self.assertIn("qikvrt_mesh_quadratic_codec_tb pass", testbench)
        self.assertIn("frame_integrity_failure", top)
        self.assertIn("transport_hold", top)
        self.assertIn("launch_issued", top)
        self.assertIn("if launch_issued = '0' and transport_hold = '0' then", top)
        self.assertIn("not frame_integrity_valid", top)
        self.assertNotIn("not tx_valid and not frame_complete and not accepted", top)
        self.assertIn("entity qikvrt_mesh_prototype_top_tb", top_testbench)
        self.assertIn("reset-bound one-shot must never start a second frame", top_testbench)
        self.assertIn("qikvrt_mesh_prototype_top_tb pass", top_testbench)

    def test_admission_gate_has_no_sampling_path(self) -> None:
        text = ADMISSION_VHDL.read_text(encoding="utf-8").lower()
        self.assertIn("entity qikvrt_deterministic_admission_gate", text)
        self.assertIn("decision_hold", text)
        self.assertIn("decision_accept", text)
        self.assertIn("decision_block", text)
        self.assertIn("if frame_complete_i /= '1' then", text)
        self.assertIn("elsif ambiguity_present_i /= '0' then", text)
        self.assertNotIn("elsif ambiguity_present_i = '1' then", text)
        self.assertIn("elsif canonical_equal_i = '1' then", text)
        self.assertNotIn("uniform", text)
        self.assertNotIn("math_real", text)

    def test_admission_gate_testbench_covers_exact_and_nonbinary_boundaries(self) -> None:
        text = ADMISSION_TESTBENCH.read_text(encoding="utf-8").lower()
        self.assertIn("entity qikvrt_deterministic_admission_gate_tb", text)
        self.assertIn("not_exact_one", text)
        self.assertIn("not_exact_zero", text)
        self.assertIn("non-exact-zero ambiguity must hold", text)
        self.assertIn("non-exact-one canonical equality must block", text)
        self.assertIn("qikvrt_deterministic_admission_gate_tb pass", text)

    def test_vhdl_execution_contract_blocks_without_a_lock(self) -> None:
        specification = importlib.util.spec_from_file_location(
            "qikvrt_vhdl_admission_gate_contract", ADMISSION_TEST_CONTRACT
        )
        self.assertIsNotNone(specification)
        assert specification is not None and specification.loader is not None
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix="qikvrt-ghdl-contract-") as directory:
            temporary_root = pathlib.Path(directory)
            toolchains = temporary_root / "runtime" / "toolchains"
            toolchains.mkdir(parents=True)
            (toolchains / "TOOLCHAIN.lock.tsv").write_text(
                "# component\\tversion\\tplatform\\tarchive\\tarchive_sha256\\tlicense\\tpurpose\\n",
                encoding="utf-8",
            )
            (toolchains / "CACHE_REGISTRY.json").write_text(
                json.dumps({"components": {}}), encoding="utf-8"
            )
            version, reason = module.locked_ghdl_version(temporary_root)
        self.assertIsNone(version)
        self.assertEqual(reason, "GHDL_NOT_DECLARED_IN_TOOLCHAIN_LOCK")
        text = ADMISSION_TEST_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("TemporaryDirectory", text)
        self.assertIn('"--std=08"', text)
        self.assertIn("GHDL_BINARY_VERSION_DOES_NOT_MATCH_LOCK", text)
        self.assertIn("qikvrt_mesh_quadratic_codec_tb", text)
        self.assertIn("qikvrt_mesh_prototype_top_tb", text)
        self.assertIn("QIKVRT_VHDL_ADMISSION_CODEC_AND_TOP_TESTBENCHES", text)
        self.assertIn("GHDL_ENVIRONMENT_OVERRIDE_FORBIDDEN", text)
        self.assertNotIn("shutil.which", text)

    def test_vhdl_execution_contract_requires_cache_bound_binary_bytes(self) -> None:
        specification = importlib.util.spec_from_file_location(
            "qikvrt_vhdl_admission_gate_contract", ADMISSION_TEST_CONTRACT
        )
        self.assertIsNotNone(specification)
        assert specification is not None and specification.loader is not None
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix="qikvrt-ghdl-cache-contract-") as directory:
            temporary_root = pathlib.Path(directory)
            toolchains = temporary_root / "runtime" / "toolchains"
            toolchains.mkdir(parents=True)
            archive_sha256 = "a" * 64
            (toolchains / "TOOLCHAIN.lock.tsv").write_text(
                "# component\tversion\tplatform\tarchive\tarchive_sha256\tlicense\tpurpose\n"
                f"ghdl\t1.2.3\tlinux-amd64\tghdl.tar.gz\t{archive_sha256}\tGPL-2.0\tvhdl\n",
                encoding="utf-8",
            )
            registry = toolchains / "CACHE_REGISTRY.json"
            registry.write_text(
                json.dumps(
                    {
                        "components": {
                            "ghdl": {
                                "version": "1.2.3",
                                "archive_sha256": archive_sha256,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            binary, version, reason = module.locked_ghdl_binary(temporary_root)
            self.assertIsNone(binary)
            self.assertIsNone(version)
            self.assertEqual(reason, "GHDL_LOCKED_BINARY_PATH_NOT_DECLARED")

            binary_path = temporary_root / ".qikvrt/toolchains/ghdl/1.2.3/bin/ghdl"
            binary_path.parent.mkdir(parents=True)
            binary_path.write_bytes(b"locked-ghdl-test-binary")
            registry.write_text(
                json.dumps(
                    {
                        "components": {
                            "ghdl": {
                                "version": "1.2.3",
                                "archive_sha256": archive_sha256,
                                "binary_path": ".qikvrt/toolchains/ghdl/1.2.3/bin/ghdl",
                                "binary_sha256": hashlib.sha256(binary_path.read_bytes()).hexdigest(),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            binary, version, reason = module.locked_ghdl_binary(temporary_root)
        self.assertEqual(binary, binary_path)
        self.assertEqual(version, "1.2.3")
        self.assertIsNone(reason)

    def test_contract_keeps_physical_claims_open(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["operation_model"], "EVENT_DRIVEN_NO_PERIODIC_POLLING")
        self.assertEqual(contract["quadratic_scaling"]["lane_count"], "N*N")
        self.assertEqual(contract["serial_transport_accounting"]["payload_handshakes_per_complete_frame"], "N*N*WORD_BITS")
        self.assertEqual(contract["framing_integrity"]["wire_handshakes_per_complete_frame"], "N*N*WORD_BITS+72")
        self.assertEqual(contract["framing_integrity"]["session_mismatch"], "HOLD")
        self.assertEqual(
            contract["framing_integrity"]["session_context_stability"],
            "REQUIRED_ACROSS_ONE_RECEIVED_FRAME",
        )
        self.assertEqual(
            contract["framing_integrity"]["cross_reset_replay_separation"],
            "FRESH_SESSION_I_REQUIRED",
        )
        self.assertEqual(
            contract["framing_integrity"]["fault_handling_claim_scope"],
            "DETERMINISTIC_FOR_EXACT_RECEIVED_FRAMES_AND_MODELED_MISMATCH_CASES_ONLY",
        )
        self.assertFalse(
            contract["framing_integrity"]["crc_collision_or_unmodeled_channel_fault_nonacceptance_proven"]
        )
        self.assertEqual(contract["framing_integrity"]["sequence_mismatch"], "HOLD")
        self.assertEqual(contract["framing_integrity"]["digest_mismatch"], "HOLD")
        self.assertFalse(contract["framing_integrity"]["cryptographic_authenticity_claim"])
        self.assertFalse(contract["framing_integrity"]["session_identifier_authentication_claim"])
        self.assertEqual(contract["serial_transport_accounting"]["prohibited_inference"], "RAW_FRAME_RATE_IS_NOT_RECEIPT_RATE_OR_COGNITIVE_WORKLOAD_THROUGHPUT")
        self.assertEqual(contract["deterministic_admission"]["forbidden_mechanisms"], ["sampling", "random_choice", "implicit_ambiguity_resolution"])
        self.assertEqual(
            contract["deterministic_admission"]["std_logic_interface_rule"]["ambiguity_not_exact_0"],
            "HOLD",
        )
        self.assertFalse(
            contract["deterministic_admission"]["std_logic_interface_rule"]["physical_metastability_claim"]
        )
        self.assertEqual(contract["hardware"]["admission_vhdl_source"], "hardware/vhdl/qikvrt_deterministic_admission_gate.vhd")
        self.assertEqual(
            contract["deterministic_admission"]["vhdl_testbench_execution"],
            "OPEN_LOCKED_GHDL_REQUIRED",
        )
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
        self.assertEqual(value["vhdl_testbench"], "hardware/vhdl/qikvrt_deterministic_admission_gate_tb.vhd")
        self.assertEqual(value["framing_vhdl_testbench"], "hardware/vhdl/qikvrt_mesh_quadratic_codec_tb.vhd")
        self.assertEqual(
            value["top_vhdl_testbench"],
            "hardware/fpga/ice40up5k_breakout/qikvrt_mesh_prototype_top_tb.vhd",
        )
        self.assertEqual(value["vhdl_test_invocation"], "tools/qikvrt_vhdl_admission_gate_contract.py")
        self.assertIn("set_io clock_12mhz 35", (PROTOTYPE.parent / "qikvrt_mesh_prototype.pcf").read_text(encoding="utf-8"))
        self.assertEqual(
            value["toolchain_readiness"]["runtime_toolchain_lock"],
            "OPEN_REQUIRED_TOOLS_NOT_YET_PINNED",
        )
        self.assertEqual(
            value["toolchain_readiness"]["locked_ghdl_cache_binary"],
            "OPEN_PATH_AND_DIGEST_REQUIRED",
        )
        self.assertFalse(value["toolchain_readiness"]["vhdl_analysis_executed"])
        self.assertFalse(value["toolchain_readiness"]["vhdl_testbench_executed"])
        self.assertFalse(value["toolchain_readiness"]["framing_integrity_testbench_executed"])
        self.assertFalse(value["toolchain_readiness"]["bitstream_generated"])
        self.assertFalse(value["claims"]["external_session_provisioning_observed"])
        self.assertFalse(value["claims"]["all_channel_corruption_detection_proven"])
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
