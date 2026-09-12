#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Compile Pascal sources to m68k-linux and reobserve under qemu-m68k."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

PARENT_PR = 895
PARENT_HEAD = "6a104554c72f189758944c55ce22f9ce0025e11d"
PARENT_TREE = "5051694c5bc6eacb44214fb2aa3209fd74f2bfbd"
FPC_SOURCE_COMMIT = "6c4d218b8d1c00cec55f889ab5fab9639a8159fe"
EXPECTED_TEST_OUTPUT = "QIKVRT Atari browser Pascal: PASS (bounded dialect bridge)\n"
EXPECTED_SHELL_OUTPUT = (
    "HOST=127.0.0.1\n"
    "PORT=8771\n"
    "PATH=/a/b?x=1\n"
    "LOOPBACK=true\n"
    "GET /a/b?x=1 HTTP/1.0\n"
    "Host: 127.0.0.1:8771\n"
    "Connection: close\n"
    "User-Agent: QIKVRT-Atari-Pascal/1\n"
    "Accept: text/html,text/plain\n\n"
)


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "command failed: " + " ".join(command) + "\n" + result.stdout
        )
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_exact_binding() -> tuple[str, str]:
    head = os.environ.get("QIKVRT_HEAD_SHA", "LOCAL")
    tree = os.environ.get("QIKVRT_TREE_SHA", "LOCAL")
    for label, value in (("head", head), ("tree", tree)):
        if value != "LOCAL" and re.fullmatch(r"[0-9a-f]{40}", value) is None:
            raise RuntimeError(f"invalid literal {label}: {value!r}")
    return head, tree


def find_cross_compiler(search_root: Path) -> Path:
    candidates = sorted(
        path
        for path in search_root.rglob("ppcross68k")
        if path.is_file() and os.access(path, os.X_OK)
    )
    if not candidates:
        raise RuntimeError("FPC_M68K_CROSS_COMPILER_NOT_FOUND")
    return candidates[0]


def compile_mode(
    root: Path,
    build: Path,
    compiler: Path,
    mode: str,
) -> dict[str, Any]:
    mode_dir = build / mode
    units_dir = mode_dir / "units"
    mode_dir.mkdir(parents=True, exist_ok=True)
    units_dir.mkdir(parents=True, exist_ok=True)
    common = [
        str(compiler),
        "-Tlinux",
        "-Pm68k",
        f"-M{mode}",
        "-B",
        "-O1",
        "-Ci",
        "-Co",
        "-Cr",
        "-Ct",
        "-XPm68k-linux-gnu-",
        f"-Fu{root / 'pascal'}",
        f"-FU{units_dir}",
        f"-FE{mode_dir}",
    ]
    test_source = root / "tests/pascal/test_qikvrt_atari_browser_pas.pas"
    shell_source = root / "runtime/pascal/qikbrow_pas.pas"
    compile_test = run(common + [f"-otest_m68k_{mode}", str(test_source)], cwd=root)
    compile_shell = run(common + [f"-oqikbrow_m68k_{mode}", str(shell_source)], cwd=root)
    test_binary = mode_dir / f"test_m68k_{mode}"
    shell_binary = mode_dir / f"qikbrow_m68k_{mode}"

    file_test = run(["file", "-b", str(test_binary)], cwd=root).stdout.strip()
    file_shell = run(["file", "-b", str(shell_binary)], cwd=root).stdout.strip()
    elf_test = run(["m68k-linux-gnu-readelf", "-h", str(test_binary)], cwd=root).stdout
    elf_shell = run(["m68k-linux-gnu-readelf", "-h", str(shell_binary)], cwd=root).stdout
    for value in (file_test, file_shell, elf_test, elf_shell):
        if "68000" not in value and "MC68000" not in value and "Motorola 68000" not in value:
            raise RuntimeError(f"M68K_ELF_MACHINE_HEADER_NOT_OBSERVED: {value}")

    test_run = run(["qemu-m68k", str(test_binary)], cwd=root).stdout
    shell_run = run(
        [
            "qemu-m68k",
            str(shell_binary),
            "http://127.0.0.1:8771/a/b?x=1#ignored",
        ],
        cwd=root,
    ).stdout
    if test_run != EXPECTED_TEST_OUTPUT:
        raise RuntimeError(f"unexpected m68k test output: {test_run!r}")
    if shell_run != EXPECTED_SHELL_OUTPUT:
        raise RuntimeError(f"unexpected m68k shell output: {shell_run!r}")

    return {
        "mode": mode,
        "compile_output": compile_test.stdout + compile_shell.stdout,
        "test_binary": str(test_binary.relative_to(root)),
        "test_binary_sha256": sha256(test_binary),
        "test_file_identity": file_test,
        "test_elf_header": elf_test,
        "test_output": test_run,
        "shell_binary": str(shell_binary.relative_to(root)),
        "shell_binary_sha256": sha256(shell_binary),
        "shell_file_identity": file_shell,
        "shell_elf_header": elf_shell,
        "shell_output": shell_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--toolchain-root", required=True)
    parser.add_argument("--build", default=".qikvrt/pascal-m68k-linux/build")
    parser.add_argument("--receipt", default=".qikvrt/pascal-m68k-linux/receipt.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    toolchain_root = Path(args.toolchain_root).resolve()
    build = (root / args.build).resolve()
    receipt_path = (root / args.receipt).resolve()
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    compiler = find_cross_compiler(toolchain_root)
    compiler_version = run([str(compiler), "-iV"], cwd=root).stdout.strip()
    compiler_sha = sha256(compiler)
    qemu_version = run(["qemu-m68k", "--version"], cwd=root).stdout.splitlines()[0]
    binutils_version = run(["m68k-linux-gnu-ld", "--version"], cwd=root).stdout.splitlines()[0]

    tp = compile_mode(root, build, compiler, "tp")
    delphi = compile_mode(root, build, compiler, "delphi")
    if tp["test_output"] != delphi["test_output"]:
        raise RuntimeError("M68K_DIALECT_TEST_OUTPUT_MISMATCH")
    if tp["shell_output"] != delphi["shell_output"]:
        raise RuntimeError("M68K_DIALECT_SHELL_OUTPUT_MISMATCH")

    head, tree = require_exact_binding()
    receipt = {
        "schema": "qikvrt_pascal_m68k_linux_hardware_mapping_receipt_v1",
        "repository": os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"),
        "head_sha": head,
        "tree_sha": tree,
        "stack_parent": {"pr": PARENT_PR, "head": PARENT_HEAD, "tree": PARENT_TREE},
        "toolchain": {
            "source_repository": "https://gitlab.com/freepascal.org/fpc/source.git",
            "source_commit": FPC_SOURCE_COMMIT,
            "cross_compiler": str(compiler),
            "cross_compiler_sha256": compiler_sha,
            "cross_compiler_version": compiler_version,
            "binutils": binutils_version,
            "emulator": qemu_version,
            "target_cpu": "m68k",
            "target_os": "linux",
            "target_abi": "M68K_LINUX_ELF",
        },
        "observations": {
            "m68k_machine_bytes_produced": True,
            "m68k_elf_machine_header_observed": True,
            "m68k_emulator_execution_observed": True,
            "tp_mode_cross_compiled_and_executed": True,
            "delphi_mode_cross_compiled_and_executed": True,
            "normalized_output_equal_between_modes": True,
            "normalized_output_equal_to_parent_receipt": True,
        },
        "artifacts": {"tp": tp, "delphi": delphi},
        "claim_boundaries": {
            "atari_tos_binary_produced": False,
            "atari_tos_execution_observed": False,
            "physical_m68000_execution_observed": False,
            "physical_megast_execution_observed": False,
            "borland_turbo_pascal_compiler_executed": False,
            "embarcadero_delphi_compiler_executed": False,
            "external_effect": "NONE",
            "effect_ack_done": False,
            "pass": False,
            "final_pass": False,
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
