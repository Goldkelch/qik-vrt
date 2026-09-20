#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Run the actual Lean kernel and reuse repository EFFECT_ACK conformance tests.

Receipts distinguish a local kernel execution from GitHub checks, owner
authorization, a physical experiment and a Zenodo publication.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PUBLICATION = "qikvrt-finite-channel-challenge-20260920-v1"
MODEL = HERE / "FiniteChannel.lean"
EXPECTED = [
    "segment_roundtrip", "segment_bounded", "lossless_delivery",
    "no_fixed_message_length_bound", "bidirectional_roundtrip",
    "release_requires_complete_haltpoint", "transport_alone_does_not_release",
    "append_preserves_sealed_prefix", "virtual_address_does_not_reverse_host_order",
    "identical_early_state_cannot_decode_both_choices",
]


def identity(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


def run(command, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=180)
    if result.returncode:
        raise RuntimeError(f"Failed {command}:\n{result.stdout}")
    return result.stdout


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lean = args.lean.resolve()
    version = run([str(lean), "--version"]).strip()
    if "version 4.19.0" not in version or "6caaee842e94" not in version:
        raise RuntimeError(f"Wrong Lean toolchain: {version}")
    model_text = MODEL.read_text()
    names = re.findall(r"(?m)^theorem\s+(\w+)", model_text)
    if names != EXPECTED or re.search(r"\b(sorry|admit|sorryAx)\b", model_text):
        raise RuntimeError("Theorem inventory or proof-placeholder check failed")
    if re.search(r"(?m)^\s*(axiom|unsafe|opaque)\b", model_text):
        raise RuntimeError("Unexpected trusted declaration")
    # Reuse the exact existing parser; do not invent a second receipt parser.
    parser_path = ROOT / "docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/make_qce_kernel_receipt.py"
    spec = importlib.util.spec_from_file_location("qce_receipt_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kernel = run([str(lean), MODEL.name], cwd=HERE)
    (args.output / "LEAN_KERNEL_OUTPUT.txt").write_text(kernel)
    axioms = module.parse_axioms(kernel)
    qualified = ["QIKVRTChallenge." + name for name in EXPECTED]
    if set(axioms) != set(qualified):
        raise RuntimeError("Incomplete kernel axiom output")
    if {a for values in axioms.values() for a in values} - {"propext", "Quot.sound"}:
        raise RuntimeError("Unexpected axiom dependency")
    conformance = run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
                       "-p", "test_effect_ack_conformance.py", "-v"])
    scoring = run([sys.executable, "-B", "-m", "unittest", "-v", "test_challenge"], cwd=HERE)
    (args.output / "CONFORMANCE_OUTPUT.txt").write_text(conformance)
    (args.output / "SCORER_TEST_OUTPUT.txt").write_text(scoring)
    source_paths = [MODEL, HERE / "challenge.py", HERE / "test_challenge.py", Path(__file__),
                    ROOT / "src/qikvrt_effect_ack.py", ROOT / "tests/test_effect_ack_conformance.py",
                    parser_path, HERE / "ARTICLE_DE.md", HERE / "CLAIM_MATRIX.json",
                    HERE / "CHALLENGE_PROTOCOL.md"]
    identities = [identity(path) for path in source_paths]
    head = run(["git", "rev-parse", "HEAD"]).strip()
    tree = run(["git", "rev-parse", "HEAD^{tree}"]).strip()
    exact = True
    for item in identities:
        check = subprocess.run(["git", "rev-parse", head + ":" + item["path"]], cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        exact &= check.returncode == 0 and check.stdout.strip() == item["git_blob_sha1"]
    sys.path.insert(0, str(HERE))
    from challenge import N, threshold
    checked_at = datetime.now(timezone.utc).isoformat()
    receipt = {
        "schema": "qikvrt_finite_channel_local_kernel_receipt_v1",
        "publication_id": PUBLICATION,
        "state": "KERNEL_VERIFIED" if exact else "KERNEL_EXECUTED_UNCOMMITTED_CANDIDATE",
        "executed_at": checked_at,
        "workflow": {"kind": "LOCAL_LEAN_CLI", "conclusion": "success",
                     "exact_head_bound": exact, "commit": head, "tree": tree,
                     "github_actions_run": None},
        "toolchain": {"version": version, "binary_sha256": hashlib.sha256(lean.read_bytes()).hexdigest(),
                      "archive_sha256": "6fe3ce97a58f44e2b3567d455b994eacec5bfe9ae7774f2a573444480ba813fe",
                      "release_url": "https://github.com/leanprover/lean4/releases/tag/v4.19.0",
                      "archive_checksum_origin": "locally measured; not an upstream signature",
                      "imports": ["Std"]},
        "sources": identities,
        "theorems": qualified,
        "axioms_by_theorem": axioms,
        "project_axioms": 0,
        "proof_placeholders": 0,
        "raw_output_sha256": hashlib.sha256(kernel.encode()).hexdigest(),
        "physical_future_to_past_channel_proved": False,
        "python_c_refinement_proved": False,
        "owner_exact_upload_authorization": False,
    }
    dump(args.output / "KERNEL_RECEIPT.json", receipt)
    test_count = lambda text: int(re.search(r"Ran (\d+) tests?", text).group(1))
    report = {
        "schema": "qikvrt_finite_channel_verification_v1",
        "publication_id": PUBLICATION, "executed_at": checked_at,
        "source_commit": head, "source_tree": tree, "source_bytes_bound_to_commit": exact,
        "sources": identities, "formal_theorems": len(qualified),
        "effect_ack_conformance_tests": test_count(conformance),
        "synthetic_scorer_tests": test_count(scoring),
        "test_result": "PASS_WITHIN_REPORTED_SCOPE", "physical_trials_performed": 0,
        "physical_future_to_past_result": "OPEN",
        "single_session_n": N, "single_session_minimum_correct": threshold(),
        "statistical_decision": "exact one-sided binomial tail <= 1/1000000",
        "logs": {name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()
                 for name in ("LEAN_KERNEL_OUTPUT.txt", "CONFORMANCE_OUTPUT.txt", "SCORER_TEST_OUTPUT.txt")},
        "synthetic_data_is_physical_evidence": False,
    }
    dump(args.output / "VERIFICATION_REPORT.json", report)
    print(json.dumps({"state": receipt["state"], "formal_theorems": len(qualified),
                      "conformance_tests": test_count(conformance),
                      "scorer_tests": test_count(scoring), "minimum_correct": report["single_session_minimum_correct"],
                      "physical_trials": 0}, indent=2))


if __name__ == "__main__":
    main()
