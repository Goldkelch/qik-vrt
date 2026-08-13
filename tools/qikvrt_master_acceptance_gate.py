#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Current, non-recursive QIK-VRT master acceptance gate.

The gate validates the launcher contracts, the complete immutable repository
snapshot, Python syntax and every executable standard-library test.  It never
repairs evidence while checking it and therefore cannot turn stale integrity
metadata into a false PASS.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import sys
import time
from collections.abc import Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools.qikvrt_subprocess import run_bounded

CORE_FILES = (
    "qikvrt.py",
    "tools/__init__.py",
    "tools/qikvrt_runtime_logger.py",
    "tools/qikvrt_subprocess.py",
    "tools/qikvrt_initial_acceptance_gate.py",
    "tools/qikvrt_integrity.py",
    "tools/qikvrt_master_acceptance_gate.py",
    "tools/qikvrt_cicd_publish.py",
    "tools/qikvrt_github_publish_runtime.py",
    "tools/qikvrt_validate_state_run.py",
    "src/qikvrt_api_handler.py",
    "src/qikvrt_effect_ack.py",
    "src/qikvrt_github_api_shim.py",
    "tests/test_effect_ack_conformance.py",
    "tests/test_integrity.py",
    "tests/test_handler_unit.py",
    "tests/test_tcpip_e2e.py",
    "canonical/CANONICAL_PRIMARY_ACCEPTANCE_GATE.json",
    "canonical/CONTINUE_PATH_SCHEMA.json",
    "canonical/JSONL_LOG_EVENT_SCHEMA_V21.json",
    "canonical/CANONICAL_RUN_END_EVENT_SCHEMA_V26.json",
    "canonical/LAUNCHER_EFFECT_AUTHORIZATION_RECORD_SCHEMA_V30.json",
    "canonical/INITIAL_LAUNCHER_EFFECT_AUTHORIZATION_GATE_V30.json",
    "platform/RUNTIME_ENVIRONMENT.json",
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
    "LEGACY_INTEGRITY_INVENTORIES.md",
)

Check = Callable[[], tuple[bool, str]]


def _read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files() -> tuple[bool, str]:
    missing = [relative for relative in CORE_FILES if not (ROOT / relative).is_file()]
    if missing:
        return False, "required files missing: " + ", ".join(missing)
    symlinks = [relative for relative in CORE_FILES if (ROOT / relative).is_symlink()]
    if symlinks:
        return False, "active launcher/runtime files must be regular files: " + ", ".join(symlinks)
    return True, f"{len(CORE_FILES)} required launcher/runtime files present"


def check_runtime_contracts() -> tuple[bool, str]:
    try:
        runtime = json.loads(_read_text(ROOT / "platform/RUNTIME_ENVIRONMENT.json"))
        primary = json.loads(_read_text(ROOT / "canonical/CANONICAL_PRIMARY_ACCEPTANCE_GATE.json"))
        continuation = json.loads(_read_text(ROOT / "canonical/CONTINUE_PATH_SCHEMA.json"))
        jsonl = json.loads(_read_text(ROOT / "canonical/JSONL_LOG_EVENT_SCHEMA_V21.json"))
        run_end = json.loads(_read_text(ROOT / "canonical/CANONICAL_RUN_END_EVENT_SCHEMA_V26.json"))
        acceptance = json.loads(_read_text(ROOT / "canonical/LAUNCHER_EFFECT_AUTHORIZATION_RECORD_SCHEMA_V30.json"))
        effect_gate = json.loads(_read_text(ROOT / "canonical/INITIAL_LAUNCHER_EFFECT_AUTHORIZATION_GATE_V30.json"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return False, f"runtime contract is unreadable: {exc}"
    if tuple(runtime.get("python_min_version", ())) < (3, 10):
        return False, "declared minimum Python version is below 3.10"
    if runtime.get("standard_library_only") is not True:
        return False, "runtime is not declared standard-library-only"
    required_block = set(primary.get("every_block_must_include", ()))
    if not required_block or required_block != set(continuation.get("required_fields", ())):
        return False, "primary BLOCK contract and CONTINUE schema disagree"
    exits = continuation.get("valid_exit_semantics", {})
    if not {"0", "1", "20"}.issubset(exits):
        return False, "canonical exit semantics are incomplete"
    if not {"run_start", "command_start", "run_end"}.issubset(jsonl.get("required_events", ())):
        return False, "JSONL required-event contract is incomplete"
    canonical_run_end = {"event", "status", "exit_code", "error_class", "continue_path", "repair_hint", "logfile"}
    if canonical_run_end != set(run_end.get("required_fields", ())):
        return False, "canonical run_end field contract changed or is incomplete"
    required_acceptance = set(acceptance.get("required_fields", ()))
    if not {"effect_authorized", "operator_effect_authorization", "accepted_by", "accepted_utc"}.issubset(required_acceptance):
        return False, "launcher effect-authorization schema is incomplete"
    if effect_gate.get("authorization_record_path") != ".qikvrt/runtime/launcher_acceptance_record.json":
        return False, "launcher effect-authorization path is inconsistent"
    if effect_gate.get("authorization_is_not_license_acceptance") is not True:
        return False, "launcher effect authorization is incorrectly coupled to license acceptance"
    return True, "runtime, BLOCK, logging and effect-authorization contracts agree"


def check_command_targets() -> tuple[bool, str]:
    try:
        import qikvrt
    except Exception as exc:  # import itself is an acceptance condition
        return False, f"launcher import failed: {exc!r}"
    if not qikvrt.COMMANDS:
        return False, "launcher contains no commands"
    for name, parts in qikvrt.COMMANDS.items():
        if not isinstance(parts, list) or not parts or not all(isinstance(item, str) for item in parts):
            return False, f"invalid command mapping: {name}"
        target = ROOT.joinpath(*parts)
        if not target.is_file() or target.is_symlink():
            return False, f"launcher target missing for {name}: {target.relative_to(ROOT)}"
    return True, f"all {len(qikvrt.COMMANDS)} launcher command targets exist"


def check_repository_integrity() -> tuple[bool, str]:
    """Use the exact deterministic implementation used by the generator."""
    from tools import qikvrt_integrity

    result = qikvrt_integrity.verify(ROOT)
    return result.ok, result.message


def check_python_syntax_and_tests() -> tuple[bool, str]:
    test_files = sorted((ROOT / "tests").glob("test_*.py"))
    if not test_files:
        return False, "no executable Python tests found"
    if any(path.is_symlink() for path in test_files):
        return False, "active test modules must be regular files, not symlinks"
    python_files = sorted(
        path for path in ROOT.rglob("*.py")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )
    for path in python_files:
        try:
            tree = ast.parse(_read_text(path), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            return False, f"Python syntax failure in {path.relative_to(ROOT)}: {exc}"
        if path in test_files:
            text = _read_text(path)
            if re.search(r"\bassert\s+True\b", text):
                return False, f"placeholder assertion in {path.relative_to(ROOT)}"
            has_test = any(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test")
                for node in ast.walk(tree)
            )
            has_executable_test_exit = any(
                isinstance(node, ast.Raise)
                and isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and node.exc.func.id == "SystemExit"
                for node in ast.walk(tree)
            )
            if not has_test and not has_executable_test_exit:
                return False, f"no test method/function in {path.relative_to(ROOT)}"
    return True, f"Python syntax valid; {len(test_files)} non-placeholder test modules discovered"


def run_test_modules(timeout: int = 180) -> tuple[bool, str]:
    test_files = sorted((ROOT / "tests").glob("test_*.py"))
    environment = os.environ.copy()
    # The sentinel belongs only to the immediate launcher -> master-gate
    # relationship.  Letting it leak into the test processes makes direct-entry
    # tests suppress their own logs and can turn the real master gate red even
    # though the same suite passes outside the launcher.
    environment.pop("QIKVRT_LAUNCHED_BY_QIKVRT", None)
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
    for path in test_files:
        module_name = f"tests.{path.stem}"
        try:
            process = run_bounded(
                [sys.executable, "-B", "-m", "unittest", "-v", module_name],
                cwd=ROOT,
                env=environment,
                timeout=timeout,
                max_output_bytes=2 * 1024 * 1024,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            return False, f"test execution failed for {path.name}: {exc}"
        if process.stdout:
            print(process.stdout, end="")
        if process.stderr:
            print(process.stderr, end="", file=sys.stderr)
        if process.timed_out:
            return False, f"test module timed out: {path.name}"
        if process.output_limit_exceeded:
            return False, f"test module output limit exceeded: {path.name}"
        if process.returncode != 0:
            return False, f"test module failed ({process.returncode}): {path.name}"
    return True, f"all {len(test_files)} test modules executed with exit code 0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QIK-VRT non-recursive master acceptance gate")
    parser.add_argument("--test-timeout", type=int, default=180, metavar="SECONDS")
    return parser


def main(argv: list[str] | None = None) -> int:
    log_managed_by_parent = os.environ.get("QIKVRT_LAUNCHED_BY_QIKVRT") == "1"
    if not log_managed_by_parent:
        from tools import qikvrt_runtime_logger as qlog
        qlog.reset_log("tools/qikvrt_master_acceptance_gate.py")
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        code = int(exc.code or 0)
        if not log_managed_by_parent:
            return qlog.finish(
                code,
                status="PASS" if code == 0 else "BLOCK",
                error_class="NONE" if code == 0 else "INVALID_MASTER_GATE_ARGUMENT",
                continue_path="NONE" if code == 0 else "CORRECT_ARGUMENT_AND_RERUN",
                repair_hint="NONE" if code == 0 else "Run with --help for valid arguments.",
            )
        return code
    if not 1 <= args.test_timeout <= 900:
        print("BLOCK test timeout must be between 1 and 900 seconds", file=sys.stderr)
        if not log_managed_by_parent:
            return qlog.finish(
                1,
                error_class="INVALID_MASTER_GATE_ARGUMENT",
                continue_path="CORRECT_ARGUMENT_AND_RERUN",
                repair_hint="Use a test timeout between 1 and 900 seconds.",
            )
        return 1

    from tools import qikvrt_initial_acceptance_gate as initial_acceptance

    if not initial_acceptance.require_acceptance("master-gate"):
        print("CONTINUE persisted launcher effect authorization is required", file=sys.stderr)
        if not log_managed_by_parent:
            return qlog.finish(
                20,
                status="CONTINUE",
                error_class="CONTINUE_ACCEPTANCE_REQUIRED",
                continue_path="PERSIST_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT",
                repair_hint="Run 'python qikvrt.py --accept'.",
            )
        return 20

    from tools import qikvrt_runtime_logger as qlog
    qlog.log_command_start("master-gate authorized checks")

    checks: list[Check] = [
        check_required_files,
        check_runtime_contracts,
        check_command_targets,
        check_repository_integrity,
        check_python_syntax_and_tests,
        lambda: run_test_modules(args.test_timeout),
        check_repository_integrity,
    ]
    started = time.monotonic()
    for check in checks:
        ok, message = check()
        if not ok:
            print("BLOCK " + message, file=sys.stderr)
            qlog.log_check_result(check.__name__, "BLOCK", 1, error=message)
            qlog.log_repair_hint(
                "MASTER_ACCEPTANCE_CHECK_FAILED",
                message,
                "BLOCK",
                "REPAIR_REPORTED_CHECK_AND_RERUN_MASTER_GATE",
            )
            if not log_managed_by_parent:
                return qlog.finish(
                    1,
                    error_class="MASTER_ACCEPTANCE_CHECK_FAILED",
                    continue_path="REPAIR_REPORTED_CHECK_AND_RERUN_MASTER_GATE",
                    repair_hint=message,
                )
            return 1
        print("PASS " + message)
        qlog.log_check_result(check.__name__, "PASS", 0)
    duration_ms = int((time.monotonic() - started) * 1000)
    print(f"PASS QIK-VRT master acceptance gate ({duration_ms} ms)")
    if not log_managed_by_parent:
        return qlog.finish(0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
