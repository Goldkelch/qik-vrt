#!/usr/bin/env python3
"""Run the admission, protected-codec and prototype-top testbenches via GHDL.

The script never provisions a compiler.  A missing lock/registry entry, absent
binary, or version mismatch is a concrete BLOCK, not a source-level PASS.  When
the toolchain is later added to the repository runtime contract, the commands
are deterministic and run in a temporary work library so they do not mutate
the checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv"
REGISTRY = ROOT / "runtime/toolchains/CACHE_REGISTRY.json"
GATE = ROOT / "hardware/vhdl/qikvrt_deterministic_admission_gate.vhd"
ADMISSION_TESTBENCH = ROOT / "hardware/vhdl/qikvrt_deterministic_admission_gate_tb.vhd"
ADMISSION_TESTBENCH_ENTITY = "qikvrt_deterministic_admission_gate_tb"
CODEC = ROOT / "hardware/vhdl/qikvrt_mesh_quadratic_codec.vhd"
PROTOTYPE_TOP = ROOT / "hardware/fpga/ice40up5k_breakout/qikvrt_mesh_prototype_top.vhd"
PROTOTYPE_TOP_TESTBENCH = ROOT / "hardware/fpga/ice40up5k_breakout/qikvrt_mesh_prototype_top_tb.vhd"
PROTOTYPE_TOP_TESTBENCH_ENTITY = "qikvrt_mesh_prototype_top_tb"
CODEC_TESTBENCH = ROOT / "hardware/vhdl/qikvrt_mesh_quadratic_codec_tb.vhd"
CODEC_TESTBENCH_ENTITY = "qikvrt_mesh_quadratic_codec_tb"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def locked_ghdl_version(root: pathlib.Path = ROOT) -> tuple[str | None, str | None]:
    """Return the declared GHDL version or a stable blocking reason."""
    lock = root / "runtime/toolchains/TOOLCHAIN.lock.tsv"
    registry = root / "runtime/toolchains/CACHE_REGISTRY.json"
    try:
        rows = [
            line.split("\t")
            for line in lock.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
    except OSError:
        return None, "GHDL_TOOLCHAIN_LOCK_UNREADABLE"
    matches = [row for row in rows if len(row) >= 2 and row[0] == "ghdl"]
    if len(matches) != 1:
        return None, "GHDL_NOT_DECLARED_IN_TOOLCHAIN_LOCK"
    try:
        components = json.loads(registry.read_text(encoding="utf-8"))["components"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None, "GHDL_CACHE_REGISTRY_UNREADABLE"
    entry = components.get("ghdl")
    if not isinstance(entry, dict):
        return None, "GHDL_NOT_DECLARED_IN_CACHE_REGISTRY"
    version = matches[0][1]
    if not isinstance(entry.get("version"), str) or entry["version"] != version:
        return None, "GHDL_LOCK_AND_CACHE_VERSION_MISMATCH"
    if version in {"", "reported-version", "VERSION_CONTRACT_ONLY"}:
        return None, "GHDL_VERSION_NOT_EXACTLY_LOCKED"
    return version, None


def _ghdl_lock_row(root: pathlib.Path) -> list[str] | None:
    try:
        rows = [
            line.split("\t")
            for line in (root / "runtime/toolchains/TOOLCHAIN.lock.tsv")
            .read_text(encoding="utf-8")
            .splitlines()
            if line and not line.startswith("#")
        ]
    except OSError:
        return None
    matches = [row for row in rows if len(row) >= 7 and row[0] == "ghdl"]
    if len(matches) != 1:
        return None
    return matches[0]


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locked_ghdl_binary(
    root: pathlib.Path = ROOT,
) -> tuple[pathlib.Path | None, str | None, str | None]:
    """Resolve only an exact cache-bound GHDL executable.

    A version string on an arbitrary executable is not a locked toolchain.  A
    future GHDL registry entry must name the archive hash from the lock and an
    exact, repository-local cache binary with its own SHA-256.  Until then this
    returns a stable BLOCK reason and never falls back to PATH.
    """
    version, blocking_reason = locked_ghdl_version(root)
    if blocking_reason is not None:
        return None, None, blocking_reason
    assert version is not None
    row = _ghdl_lock_row(root)
    if row is None:
        return None, None, "GHDL_TOOLCHAIN_LOCK_MALFORMED"
    archive_sha256 = row[4]
    if HEX64.fullmatch(archive_sha256) is None:
        return None, None, "GHDL_ARCHIVE_DIGEST_NOT_EXACTLY_LOCKED"
    try:
        entry = json.loads(
            (root / "runtime/toolchains/CACHE_REGISTRY.json").read_text(encoding="utf-8")
        )["components"]["ghdl"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None, None, "GHDL_CACHE_REGISTRY_UNREADABLE"
    if entry.get("archive_sha256") != archive_sha256:
        return None, None, "GHDL_LOCK_AND_CACHE_ARCHIVE_DIGEST_MISMATCH"
    binary_path_value = entry.get("binary_path")
    binary_sha256 = entry.get("binary_sha256")
    if not isinstance(binary_path_value, str) or not binary_path_value:
        return None, None, "GHDL_LOCKED_BINARY_PATH_NOT_DECLARED"
    if not isinstance(binary_sha256, str) or HEX64.fullmatch(binary_sha256) is None:
        return None, None, "GHDL_LOCKED_BINARY_DIGEST_NOT_DECLARED"
    declared_path = pathlib.PurePosixPath(binary_path_value)
    if declared_path.is_absolute() or ".." in declared_path.parts:
        return None, None, "GHDL_LOCKED_BINARY_PATH_NOT_REPOSITORY_LOCAL"
    candidate = root / pathlib.Path(*declared_path.parts)
    cache_root = root / ".qikvrt" / "toolchains"
    try:
        candidate.relative_to(cache_root)
    except ValueError:
        return None, None, "GHDL_LOCKED_BINARY_PATH_OUTSIDE_CACHE"
    if not candidate.is_file():
        return None, None, "GHDL_LOCKED_BINARY_NOT_PRESENT"
    # A symlink would permit a mutable binary outside the declared cache path.
    cursor = candidate
    while cursor != cache_root:
        if cursor.is_symlink():
            return None, None, "GHDL_LOCKED_BINARY_PATH_HAS_SYMLINK"
        cursor = cursor.parent
    if cache_root.is_symlink():
        return None, None, "GHDL_LOCKED_BINARY_PATH_HAS_SYMLINK"
    if (root / ".qikvrt").is_symlink():
        return None, None, "GHDL_LOCKED_BINARY_PATH_HAS_SYMLINK"
    if _sha256(candidate) != binary_sha256:
        return None, None, "GHDL_LOCKED_BINARY_DIGEST_MISMATCH"
    return candidate, version, None


def run_checked(command: list[str], *, cwd: pathlib.Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode == 0:
        return
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    raise RuntimeError("GHDL_COMMAND_FAILED: " + " ".join(command))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-lock-only",
        action="store_true",
        help="validate the GHDL lock/cache contract without invoking a compiler",
    )
    arguments = parser.parse_args()

    if "QIKVRT_GHDL" in os.environ:
        print("BLOCK GHDL_ENVIRONMENT_OVERRIDE_FORBIDDEN", file=sys.stderr)
        return 2
    executable, version, blocking_reason = locked_ghdl_binary()
    if blocking_reason is not None:
        print(f"BLOCK {blocking_reason}", file=sys.stderr)
        return 2
    assert executable is not None and version is not None
    if arguments.check_lock_only:
        print(f"PASS GHDL_LOCKED version={version}")
        return 0

    version_result = subprocess.run(
        [str(executable), "--version"], text=True, capture_output=True
    )
    version_text = version_result.stdout + version_result.stderr
    exact_version = re.compile(
        rf"(?<![0-9A-Za-z_.-]){re.escape(version)}(?![0-9A-Za-z_.-])"
    )
    if version_result.returncode != 0 or exact_version.search(version_text) is None:
        print("BLOCK GHDL_BINARY_VERSION_DOES_NOT_MATCH_LOCK", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="qikvrt-ghdl-admission-codec-") as directory:
        work = pathlib.Path(directory)
        try:
            run_checked([str(executable), "-a", "--std=08", str(GATE)], cwd=work)
            run_checked([str(executable), "-a", "--std=08", str(CODEC)], cwd=work)
            run_checked([str(executable), "-a", "--std=08", str(PROTOTYPE_TOP)], cwd=work)
            run_checked([str(executable), "-a", "--std=08", str(PROTOTYPE_TOP_TESTBENCH)], cwd=work)
            run_checked([str(executable), "-a", "--std=08", str(ADMISSION_TESTBENCH)], cwd=work)
            run_checked([str(executable), "-a", "--std=08", str(CODEC_TESTBENCH)], cwd=work)
            run_checked([str(executable), "-e", "--std=08", ADMISSION_TESTBENCH_ENTITY], cwd=work)
            run_checked(
                [str(executable), "-r", "--std=08", ADMISSION_TESTBENCH_ENTITY, "--assert-level=error"],
                cwd=work,
            )
            run_checked([str(executable), "-e", "--std=08", CODEC_TESTBENCH_ENTITY], cwd=work)
            run_checked(
                [str(executable), "-r", "--std=08", CODEC_TESTBENCH_ENTITY, "--assert-level=error"],
                cwd=work,
            )
            run_checked([str(executable), "-e", "--std=08", PROTOTYPE_TOP_TESTBENCH_ENTITY], cwd=work)
            run_checked(
                [str(executable), "-r", "--std=08", PROTOTYPE_TOP_TESTBENCH_ENTITY, "--assert-level=error"],
                cwd=work,
            )
        except RuntimeError as error:
            print(f"BLOCK {error}", file=sys.stderr)
            return 2

    print(f"PASS QIKVRT_VHDL_ADMISSION_CODEC_AND_TOP_TESTBENCHES version={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
