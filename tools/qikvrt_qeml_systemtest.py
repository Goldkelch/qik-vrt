# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-head QEML-1 system test and audit receipt producer."""
from __future__ import print_function

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import qikvrt_qeml as qeml


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("ascii")


def run(source_path, compiler_core_path, expected_head, expected_tree, output):
    with open(source_path, "r") as handle:
        source = handle.read()
    with open(compiler_core_path, "r") as handle:
        compiler_source = handle.read()
    model = qeml.parse_source(source)
    declared = qeml.execute_all_tests(model)
    if not all(item["ok"] for item in declared):
        raise qeml.QEMLError("DECLARED_TEST_FAILURE", "a declared QEML test failed")

    traces = {}
    cases = (("workers", 0), ("workers", 1), ("workers", 8),
             ("workers", 9), ("heartbeat", None))
    runtime_dir = os.path.join(ROOT, "src", "qeml")
    for scenario, argument in cases:
        c_trace = qeml.compile_c89_and_run(
            source, scenario, argument, runtime_dir=runtime_dir)
        if scenario == "workers":
            python_result = qeml.run_workers(argument)
            key = "workers_%d" % argument
        else:
            python_result = qeml.run_heartbeat()
            key = "heartbeat"
        python_trace = qeml.expected_c89_trace(model["model"], python_result)
        if c_trace != python_trace:
            raise qeml.QEMLError("TRACE_MISMATCH", "%s C89 trace differs" % key)
        traces[key] = {"interpreter": python_trace, "c89": c_trace}

    primitive = qeml.emit_m68000_status(qeml.STATUS_CONTINUE)
    executed_status = qeml.execute_m68000_status(primitive["machine_code"])
    if executed_status != qeml.STATUS_CONTINUE:
        raise qeml.QEMLError("M68000_EXECUTION", "M68000 primitive returned wrong status")

    bootstrap = qeml.bootstrap_fixed_point(compiler_source)
    if not bootstrap["fixed_point"]:
        raise qeml.QEMLError("BOOTSTRAP_FIXED_POINT", "supported subset did not reach fixed point")

    artifacts = qeml.compile_artifacts(source, expected_head, expected_tree)
    receipt = {
        "schema": "QEML_EXACT_HEAD_SYSTEM_RECEIPT_V1",
        "language": "QEML-1",
        "expected_head": expected_head,
        "expected_tree": expected_tree,
        "model": model["model"],
        "declared_test_count": len(declared),
        "declared_tests_observed": True,
        "interpreter_c89_trace_equivalence_observed": True,
        "trace_sha256": sha256_bytes(canonical_bytes(traces)),
        "ansi_c89_compilation_observed": True,
        "strict_c89_flags": "-std=c89 -pedantic -Wall -Wextra -Werror",
        "m68000_assembly_generation_observed": True,
        "m68000_encoding_validation_observed": True,
        "m68000_emulated_primitive_execution_observed": True,
        "m68000_executed_status": "CONTINUE",
        "m68000_machine_code_sha256": sha256_bytes(primitive["machine_code"]),
        "bootstrap_fixed_point_for_supported_subset": True,
        "bootstrap_trace": bootstrap,
        "self_hosting_observed": False,
        "source_sha256": artifacts["receipt"]["source_sha256"],
        "canonical_source_sha256": artifacts["receipt"]["canonical_source_sha256"],
        "ir_sha256": artifacts["receipt"]["ir_sha256"],
        "c89_sha256": artifacts["receipt"]["c89_sha256"],
        "physical_megast_execution": False,
        "future_hardware_support_observed": False,
        "authority_main_effect": False,
        "external_effect": "NONE",
        "general_effect_ack_done": False,
        "publication": False,
        "deployment": False,
        "pass": False,
        "final_pass": False
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    parent = os.path.dirname(output)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(output, "wb") as handle:
        handle.write(canonical_bytes(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--compiler-core", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = run(args.source, args.compiler_core, args.expected_head,
                      args.expected_tree, args.output)
    except qeml.QEMLError as exc:
        sys.stderr.write(json.dumps({"state": "HOLD", "error": exc.as_dict()},
                                    sort_keys=True) + "\n")
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
