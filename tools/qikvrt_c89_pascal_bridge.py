#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Compile and reobserve the bounded C89 -> Pascal dialect bridge."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

SOURCE_HEAD = "cba166e45a0ea4b5d5dd2ef9cde0ad96ff57554b"
SOURCE_TREE = "23586fd719627a6e508724239a71b71fea7e9847"
SOURCE_C_BLOB = "bca759d4813b9d89754e052ddcf892e9f811eca4"
SOURCE_H_BLOB = "50f2b596eb8b8b16aa5c327037d726bfdb3a1c2a"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed: " + " ".join(command) + "\n" + completed.stdout
        )
    return completed


def compile_mode(root: Path, build: Path, fpc: str, mode: str) -> dict[str, Any]:
    mode_dir = build / mode
    unit_dir = mode_dir / "units"
    mode_dir.mkdir(parents=True, exist_ok=True)
    unit_dir.mkdir(parents=True, exist_ok=True)
    test_source = root / "tests/pascal/test_qikvrt_atari_browser_pas.pas"
    shell_source = root / "runtime/pascal/qikbrow_pas.pas"
    common = [
        fpc,
        "-B",
        f"-M{mode}",
        "-O1",
        "-Ci",
        "-Co",
        "-Cr",
        "-Ct",
        f"-Fu{root / 'pascal'}",
        f"-FU{unit_dir}",
        f"-FE{mode_dir}",
    ]
    compile_test = run(common + [f"-otest_{mode}", str(test_source)], cwd=root)
    compile_shell = run(common + [f"-oqikbrow_{mode}", str(shell_source)], cwd=root)
    test_binary = mode_dir / f"test_{mode}"
    shell_binary = mode_dir / f"qikbrow_{mode}"
    test_run = run([str(test_binary)], cwd=root)
    shell_run = run(
        [str(shell_binary), "http://127.0.0.1:8771/a/b?x=1#ignored"],
        cwd=root,
    )
    return {
        "mode": mode,
        "compiler_output": compile_test.stdout + compile_shell.stdout,
        "test_output": test_run.stdout,
        "shell_output": shell_run.stdout,
        "test_binary": str(test_binary.relative_to(root)),
        "test_binary_sha256": sha256(test_binary),
        "shell_binary": str(shell_binary.relative_to(root)),
        "shell_binary_sha256": sha256(shell_binary),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--build", default=".qikvrt/c89-pascal-bridge/build")
    parser.add_argument("--receipt", default=".qikvrt/c89-pascal-bridge/receipt.json")
    parser.add_argument("--fpc", default="fpc")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    build = (root / args.build).resolve()
    receipt_path = (root / args.receipt).resolve()
    fpc = shutil.which(args.fpc)
    if fpc is None:
        raise SystemExit("BLOCK FPC_COMPILER_UNAVAILABLE")

    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    version = run([fpc, "-iV"], cwd=root).stdout.strip()
    tp = compile_mode(root, build, fpc, "tp")
    delphi = compile_mode(root, build, fpc, "delphi")

    if tp["test_output"] != delphi["test_output"]:
        raise RuntimeError("dialect test outputs differ")
    if tp["shell_output"] != delphi["shell_output"]:
        raise RuntimeError("dialect shell outputs differ")
    expected_test = "QIKVRT Atari browser Pascal: PASS (bounded dialect bridge)\n"
    if tp["test_output"] != expected_test:
        raise RuntimeError(f"unexpected test receipt: {tp['test_output']!r}")

    receipt = {
        "schema": "qikvrt_c89_turbo_pascal_delphi_bridge_receipt_v1",
        "repository": os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"),
        "head_sha": os.environ.get("GITHUB_SHA", "LOCAL"),
        "tree_sha": os.environ.get("QIKVRT_TREE_SHA", "LOCAL"),
        "source_c89": {
            "pr": 848,
            "head": SOURCE_HEAD,
            "tree": SOURCE_TREE,
            "source_blob": SOURCE_C_BLOB,
            "header_blob": SOURCE_H_BLOB,
        },
        "compiler": {
            "implementation": "Free Pascal Compiler",
            "version": version,
            "turbo_pascal_mode": "-Mtp",
            "delphi_mode": "-Mdelphi",
        },
        "observations": {
            "turbo_pascal_dialect_compiled": True,
            "turbo_pascal_dialect_executed": True,
            "delphi_dialect_compiled": True,
            "delphi_dialect_executed": True,
            "normalized_semantic_output_equal": True,
            "url_parse_observed": True,
            "http_get_serialization_observed": True,
            "http_response_split_observed": True,
            "html_text_projection_observed": True,
            "entity_decode_observed": True,
            "script_style_suppression_observed": True,
            "link_extraction_observed": True,
            "preformatted_whitespace_observed": True,
            "invalid_input_fail_closed_observed": True,
        },
        "artifacts": {"tp": tp, "delphi": delphi},
        "claim_boundaries": {
            "borland_turbo_pascal_compiler_executed": False,
            "embarcadero_delphi_compiler_executed": False,
            "m68000_binary_produced": False,
            "m68000_binary_executed": False,
            "physical_megast_execution": False,
            "c89_binary_equivalence_proved": False,
            "source_semantic_vector_equivalence_observed": True,
            "external_effect": "NONE",
            "effect_ack_done": False,
            "pass": False,
            "final_pass": False,
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
