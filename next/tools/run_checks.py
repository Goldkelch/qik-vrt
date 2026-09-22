#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Build and verify this exact committed target; retain bounded execution evidence."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cargo", default=os.environ.get("QIKVRT_CARGO", "cargo"))
    parser.add_argument("--ghdl", default=os.environ.get("QIKVRT_GHDL", "ghdl"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == REPO or REPO in output.parents:
        parser.error("Evidence must be outside the source repository")
    output.mkdir(parents=True, exist_ok=False)

    def git(*arguments):
        return subprocess.check_output(["git", *arguments], cwd=REPO, text=True).strip()

    head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    if git("status", "--porcelain"):
        raise SystemExit("CLEAN_COMMITTED_SOURCE_REQUIRED")
    result = {"schema": "qikvrt-c90-target-checks-v1", "head": head, "tree": tree,
              "state": "RUNNING", "checks": [], "predecessor_evidence_transfer": False,
              "sanitizer_environment": {key: os.environ.get(key, "DEFAULT")
                                        for key in ("ASAN_OPTIONS", "UBSAN_OPTIONS", "LSAN_OPTIONS")},
              "physical_hardware_tested": False, "ordinary_release": False}

    def run(name, command, timeout=600):
        print("CHECK " + name, flush=True)
        start = time.monotonic()
        with (output / (name + ".log")).open("xb") as log:
            completed = subprocess.run(list(map(str, command)), cwd=REPO,
                                       stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        result["checks"].append({"name": name, "exit_code": completed.returncode,
                                 "elapsed_seconds": time.monotonic() - start})
        if completed.returncode:
            raise RuntimeError(name + " failed; see " + str(output / (name + ".log")))

    try:
        run("cc-version", [os.environ.get("CC", "cc"), "--version"])
        run("cargo-version", [args.cargo, "--version", "--verbose"])
        run("ghdl-version", [args.ghdl, "--version"])
        run("cache", [sys.executable, "tools/qikvrt_tool_cache.py", "verify"])
        run("integrity", [sys.executable, "tools/qikvrt_integrity.py", "verify"])
        run("c90", ["make", "-C", ROOT / "core", "test", "assembly"])
        run("c90-sanitizers", ["make", "-C", ROOT / "core", "test",
                               "OUT=" + str(output / "sanitized-c90"),
                               "CFLAGS=-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"])
        common = ["--locked", "--manifest-path", ROOT / "Cargo.toml"]
        if args.offline:
            common.append("--offline")
        run("rust-tests", [args.cargo, "test", *common])
        run("release-build", [args.cargo, "build", "--release", *common])
        for check in ("bus", "exchange", "continuity", "hardware"):
            command = [sys.executable, ROOT / "tools" / ("check_" + check + ".py"),
                       "--output", output / (check + ".json")]
            if check == "hardware":
                command += ["--ghdl", args.ghdl]
            run(check, command)
        # Reuse the frozen neutral oracle without impersonating six executions.
        reference = ROOT / "reference/full-core-draft03"
        run("eap-build", [os.environ.get("CC", "cc"), "-O2", "-std=c90", "-pedantic-errors",
                          "-Wall", "-Wextra", "-Werror", "-Iinclude", "src/effect_ack_core.c",
                          reference / "c90.c", reference / "harness.c", "-o", output / "eap-c90"])
        run("eap-stream", [output / "eap-c90"])
        spec = importlib.util.spec_from_file_location("frozen_oracle", reference / "check.py")
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        contract = (reference / "contract.json").read_bytes()
        assert hashlib.sha256(contract).hexdigest() == oracle.CONTRACT_SHA256
        expected = oracle.expected(json.loads(contract))
        oracle.compare_bytes((output / "eap-stream.log").read_bytes(), expected)
        result["fresh_eap"] = {"carrier": "c90", "core_cases": oracle.CORE_CASES,
                               "consumer_cases": oracle.CONSUMER_CASES,
                               "output_sha256": hashlib.sha256(expected).hexdigest(),
                               "six_language_reexecution": False}
        if git("rev-parse", "HEAD") != head or git("status", "--porcelain"):
            raise RuntimeError("SOURCE_CHANGED_DURING_EXECUTION")
        binary = ROOT / "target/release/qikvrt-next"
        result["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
        result["state"] = "PASS"
    except Exception as exc:
        result["state"] = "FAIL"
        result["error"] = str(exc)
        raise
    finally:
        result["files"] = {p.name: {"bytes": p.stat().st_size,
                                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                           for p in sorted(output.iterdir()) if p.is_file()}
        (output / "receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
