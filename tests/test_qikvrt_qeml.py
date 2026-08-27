# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import print_function

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import qikvrt_qeml as qeml

HEARTBEAT = os.path.join(ROOT, "examples", "qeml", "heartbeat_ring.qeml")
COMPILER = os.path.join(ROOT, "examples", "qeml", "compiler_core.qeml")
LEXER = os.path.join(ROOT, "policy", "qeml", "QEML_LEXER_V1.json")
RUNTIME = os.path.join(ROOT, "src", "qeml")


def read(path):
    with open(path, "r") as handle:
        return handle.read()


class QEMLCompilerTests(unittest.TestCase):
    def setUp(self):
        self.source = read(HEARTBEAT)
        self.model = qeml.parse_source(self.source)

    def test_lexer_is_deterministic_and_external_spec_matches(self):
        first = qeml.tokenize(self.source)
        second = qeml.tokenize(self.source, qeml.load_lexical_spec(LEXER))
        self.assertEqual(first, second)
        self.assertGreater(len(first), 20)

    def test_regex_is_not_language_semantics(self):
        tokens = qeml.tokenize("modell X")
        self.assertEqual(tokens[0]["kind"], "KEYWORD")
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.parse_source("modell X\nregel R\n  bei Missing\n")
        self.assertNotEqual(caught.exception.code, "LEXER_UNKNOWN_CHARACTER")

    def test_parse_canonical_print_round_trip(self):
        canonical = qeml.canonical_print(self.model)
        reparsed = qeml.parse_source(canonical)
        self.assertEqual(qeml.canonical_ir(self.model), qeml.canonical_ir(reparsed))

    def test_ir_is_byte_stable(self):
        first = qeml.canonical_json_bytes(qeml.canonical_ir(self.model))
        second = qeml.canonical_json_bytes(qeml.canonical_ir(qeml.parse_source(self.source)))
        self.assertEqual(first, second)

    def test_unknown_event_fails_closed(self):
        model = copy.deepcopy(self.model)
        model["rules"][0]["event"] = "Unbekannt"
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.validate_model(model)
        self.assertEqual(caught.exception.code, "RULE_UNKNOWN_EVENT")

    def test_ambiguous_transition_fails_closed(self):
        model = copy.deepcopy(self.model)
        duplicate = copy.deepcopy(model["rules"][0])
        duplicate["name"] = "Zweite_Regel"
        model["rules"].append(duplicate)
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.validate_model(model)
        self.assertEqual(caught.exception.code, "NONDETERMINISTIC_TRANSITION")

    def test_effect_requires_observer_and_receipt(self):
        model = copy.deepcopy(self.model)
        del model["effects"][0]["attrs"]["observer"]
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.validate_model(model)
        self.assertEqual(caught.exception.code, "EFFECT_CONTRACT_INCOMPLETE")

    def test_target_descriptor_is_complete(self):
        model = copy.deepcopy(self.model)
        del model["targets"][0]["attrs"]["calling"]
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.validate_model(model)
        self.assertEqual(caught.exception.code, "TARGET_ABI_INCOMPLETE")

    def test_unknown_target_fails_closed(self):
        model = copy.deepcopy(self.model)
        model["targets"][0]["name"] = "future_unknown_isa"
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.validate_model(model)
        self.assertEqual(caught.exception.code, "TARGET_UNSUPPORTED")

    def test_zero_one_eight_workers_and_reject_nine(self):
        self.assertEqual(qeml.run_workers(0)["status"], "CONTINUE")
        self.assertEqual(qeml.run_workers(1)["status"], "PASS")
        self.assertEqual(qeml.run_workers(8)["status"], "PASS")
        nine = qeml.run_workers(9)
        self.assertEqual(nine["status"], "HOLD")
        self.assertEqual(nine["hold"], "worker_limit_exceeded")
        self.assertEqual(nine["workers"], 8)

    def test_continue_pass_failure_are_distinct(self):
        self.assertNotEqual(qeml.STATUS_CONTINUE, qeml.STATUS_PASS)
        self.assertNotEqual(qeml.STATUS_CONTINUE, qeml.STATUS_FAILURE)
        self.assertNotEqual(qeml.STATUS_PASS, qeml.STATUS_FAILURE)
        self.assertEqual(qeml.run_workers(0)["status_code"], qeml.STATUS_CONTINUE)

    def test_heartbeat_is_liveness_not_work_or_polling(self):
        ok = qeml.run_heartbeat({
            "semantic_work_triggered": False,
            "polling": False,
            "blind_retry": False,
        })
        self.assertEqual(ok["status"], "CONTINUE")
        blocked = qeml.run_heartbeat({"polling": True})
        self.assertEqual(blocked["status"], "HOLD")
        self.assertEqual(blocked["hold"], "heartbeat_semantic_violation")

    def test_all_declared_tests_are_executable(self):
        results = qeml.execute_all_tests(self.model)
        self.assertEqual(len(results), 5)
        self.assertTrue(all(item["ok"] for item in results))

    def test_deterministic_reduction_ignores_arrival_order(self):
        receipts = [
            {"sequence": 2, "digest": "b", "value": "second"},
            {"sequence": 1, "digest": "a", "value": "first"},
            {"sequence": 1, "digest": "a", "value": "first"},
        ]
        forward = qeml.deterministic_reduce(receipts)
        reverse = qeml.deterministic_reduce(list(reversed(receipts)))
        self.assertEqual(forward, reverse)
        self.assertEqual([item["sequence"] for item in forward], [1, 2])

    def test_conflicting_duplicate_receipt_fails_closed(self):
        receipts = [
            {"sequence": 1, "digest": "a", "value": "first"},
            {"sequence": 1, "digest": "a", "value": "changed"},
        ]
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.deterministic_reduce(receipts)
        self.assertEqual(caught.exception.code, "REDUCTION_CONFLICT")

    def test_strict_c89_compiles_and_matches_python_trace(self):
        cases = [("workers", 0), ("workers", 1), ("workers", 8),
                 ("workers", 9), ("heartbeat", None)]
        for scenario, argument in cases:
            output = qeml.compile_c89_and_run(
                self.source, scenario, argument, runtime_dir=RUNTIME)
            result = qeml.run_workers(argument) if scenario == "workers" else qeml.run_heartbeat()
            expected = qeml.expected_c89_trace(self.model["model"], result)
            self.assertEqual(output, expected)

    def test_generated_c89_is_deterministic(self):
        first = qeml.emit_c89(self.model)
        second = qeml.emit_c89(qeml.parse_source(qeml.canonical_print(self.model)))
        self.assertEqual(first, second)

    def test_m68000_machine_code_is_emulated_not_physical(self):
        for status in (qeml.STATUS_PASS, qeml.STATUS_CONTINUE,
                       qeml.STATUS_FAILURE, qeml.STATUS_HOLD):
            artifact = qeml.emit_m68000_status(status)
            self.assertIn("moveq", artifact["assembly"])
            self.assertEqual(qeml.execute_m68000_status(artifact["machine_code"]), status)
        receipt = qeml.compile_artifacts(self.source)["receipt"]
        self.assertFalse(receipt["physical_megast_execution"])

    def test_m68000_corrupt_encoding_is_rejected(self):
        with self.assertRaises(qeml.QEMLError) as caught:
            qeml.execute_m68000_status(b"\x70\x0a\x4e\x74")
        self.assertEqual(caught.exception.code, "M68000_ENCODING")

    def test_bootstrap_fixed_point_for_supported_subset(self):
        result = qeml.bootstrap_fixed_point(read(COMPILER))
        self.assertTrue(result["fixed_point"])
        self.assertTrue(result["canonical_source_equal"])
        self.assertTrue(result["ir_equal"])
        self.assertTrue(result["c89_equal"])
        self.assertTrue(result["m68000_equal"])

    def test_receipt_is_digest_bound_and_fail_closed(self):
        receipt = qeml.compile_artifacts(
            self.source,
            expected_head="0" * 40,
            expected_tree="1" * 40,
        )["receipt"]
        self.assertEqual(receipt["schema"], qeml.SCHEMA_RECEIPT)
        self.assertTrue(qeml.DIGEST_RE.match(receipt["receipt_sha256"]))
        self.assertTrue(receipt["tests_ok"])
        self.assertFalse(receipt["self_hosting_observed"])
        self.assertFalse(receipt["authority_main_effect"])
        self.assertFalse(receipt["general_effect_ack_done"])
        self.assertFalse(receipt["pass"])
        self.assertFalse(receipt["final_pass"])

    def test_head_tree_drift_changes_receipt(self):
        first = qeml.compile_artifacts(self.source, "a" * 40, "b" * 40)["receipt"]
        second = qeml.compile_artifacts(self.source, "c" * 40, "b" * 40)["receipt"]
        self.assertNotEqual(first["receipt_sha256"], second["receipt_sha256"])

    def test_exact_head_system_receipt_observes_c89_and_m68000(self):
        with tempfile.TemporaryDirectory(prefix="qeml-system-") as tmp:
            output = os.path.join(tmp, "system-receipt.json")
            command = [sys.executable,
                       os.path.join(TOOLS, "qikvrt_qeml_systemtest.py"),
                       "--source", HEARTBEAT,
                       "--compiler-core", COMPILER,
                       "--expected-head", "0" * 40,
                       "--expected-tree", "1" * 40,
                       "--output", output]
            subprocess.check_call(command)
            with open(output, "r") as handle:
                receipt = json.load(handle)
            self.assertTrue(receipt["ansi_c89_compilation_observed"])
            self.assertTrue(receipt["m68000_emulated_primitive_execution_observed"])
            self.assertTrue(receipt["bootstrap_fixed_point_for_supported_subset"])
            self.assertFalse(receipt["self_hosting_observed"])
            self.assertFalse(receipt["physical_megast_execution"])
            self.assertFalse(receipt["general_effect_ack_done"])

    def test_cli_compile_emits_all_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="qeml-cli-") as tmp:
            prefix = os.path.join(tmp, "heartbeat")
            command = [sys.executable, os.path.join(TOOLS, "qikvrt_qeml.py"),
                       "compile", HEARTBEAT, "--output-prefix", prefix,
                       "--expected-head", "0" * 40,
                       "--expected-tree", "1" * 40]
            subprocess.check_call(command)
            for suffix in (".canonical.qeml", ".ir.json", ".c", ".m68k.s",
                           ".m68k.bin", ".receipt.json"):
                self.assertTrue(os.path.isfile(prefix + suffix), suffix)
            with open(prefix + ".receipt.json", "r") as handle:
                receipt = json.load(handle)
            self.assertTrue(receipt["tests_ok"])


if __name__ == "__main__":
    unittest.main()
