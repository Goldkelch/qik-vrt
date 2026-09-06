#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build the pinned SNAP bridge from an explicitly provisioned clean checkout.

No network, package installation, repository write, or silent source fallback.
Build into a new output path. Delete only disposable build output to roll back.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.qikvrt_snap_mesh import AnalysisError, LOCK, digest, native_metrics, read_json


def git(source: pathlib.Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(source), *args],
        text=True, timeout=30).strip()


def build(source: pathlib.Path, binary: pathlib.Path) -> dict:
    source, binary = source.resolve(), binary.resolve()
    lock = read_json(LOCK)
    if sys.platform != lock["platform"]:
        raise AnalysisError("UNSUPPORTED_SNAP_BUILD_PLATFORM")
    if any(p.exists() for p in (binary, binary.with_suffix(".build.json"),
                                binary.with_suffix(".LICENSE.txt"))):
        raise AnalysisError("BUILD_OUTPUT_EXISTS")
    if source == binary.parent or source in binary.parents:
        raise AnalysisError("BUILD_OUTPUT_INSIDE_SOURCE")
    if (git(source, "rev-parse", "HEAD") != lock["commit"] or
        git(source, "rev-parse", "HEAD^{tree}") != lock["tree"] or
        git(source, "status", "--porcelain", "--untracked-files=all")):
        raise AnalysisError("SNAP_SOURCE_NOT_EXACT_CLEAN_PIN")
    notice = (source / "License.txt").read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(notice)).encode() + b"\0" + notice).hexdigest()
    if blob != lock["license_blob"]:
        raise AnalysisError("SNAP_LICENSE_MISMATCH")
    compiler = shutil.which("g++")
    if not compiler:
        raise AnalysisError("CXX_COMPILER_UNAVAILABLE")
    compiler_version = subprocess.check_output([compiler, "--version"], text=True, timeout=15)
    flags = ["-std=c++98", "-O2", "-DNDEBUG", "-fopenmp"]
    bridge = ROOT / "tools/qikvrt_snap_mesh.cpp"
    binary.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qikvrt-snap-build-", dir=binary.parent) as tmp:
        candidate = pathlib.Path(tmp) / "qikvrt-snap"
        command = [compiler, *flags, "-I" + str(source / "glib-core"),
                   "-I" + str(source / "snap-core"), str(bridge),
                   str(source / "snap-core/Snap.cpp"), "-lrt", "-o", str(candidate)]
        subprocess.run(command, check=True, timeout=600)
        graph = {"node_ids": ["a", "b", "c", "d", "isolated"],
                 "edges": [[0, 1], [0, 3], [1, 2], [2, 3]]}
        metrics = native_metrics(candidate, graph)
        if metrics != {"nodes": 5, "edges": 4, "components": 2,
                       "max_component_diameter": 2,
                       "unreachable_ordered_pairs": 8, "degrees": [2, 2, 2, 2, 0]}:
            raise AnalysisError("NATIVE_SNAP_SELF_TEST_FAILED")
        if (git(source, "rev-parse", "HEAD") != lock["commit"] or
            git(source, "rev-parse", "HEAD^{tree}") != lock["tree"] or
            git(source, "status", "--porcelain", "--untracked-files=all")):
            raise AnalysisError("SOURCE_CHANGED_DURING_BUILD")
        receipt = {"schema": "qikvrt_snap_build_receipt_v1", "source_commit": lock["commit"],
                   "source_tree": lock["tree"], "license_blob": blob,
                   "binary_sha256": digest(candidate.read_bytes()),
                   "bridge_sha256": digest(bridge.read_bytes()),
                   "lock_sha256": digest(LOCK.read_bytes()), "compiler": compiler_version,
                   "flags": flags, "native_self_test": metrics,
                   "identity_scope": "LOCAL_BUILD_PROVENANCE_NOT_ATTESTATION"}
        # Exclusive creation; a failed build never replaces a prior backend.
        with binary.open("xb") as output:
            output.write(candidate.read_bytes())
        binary.chmod(0o755)
        with binary.with_suffix(".build.json").open("x", encoding="utf-8") as output:
            json.dump(receipt, output, sort_keys=True, indent=2)
            output.write("\n")
        with binary.with_suffix(".LICENSE.txt").open("xb") as output:
            output.write(notice)
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.source, args.output), sort_keys=True, indent=2))
        return 0
    except (AnalysisError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"state": "HOLD", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
