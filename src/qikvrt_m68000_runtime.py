# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Registered MC68000 execution behind the existing authenticated REST adapter.

V1 exposes the finite Spark plan kernel. The backend executes its actual opcodes
with the repository's bounded instruction interpreter, not a complete machine.
No supplied program, shell command, repository write or ordinary effect runs.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_spark_branch_m68000_compiler as compiler

API_PATH = "/qik-vrt/mesh/v1/m68000"
KERNEL_ID = "lean_spark_branch_plan_v1"
REGISTRY = "runtime/m68000/QIKVRT_COMPILED_KERNELS_V1.json"
HEX_PATH = "runtime/m68000/qikvrt_spark_branch_plan_v1.hex"
CATALOG = "runtime/m68000/QIKVRT_SPARK_BRANCH_PLANS_V1.json"
SOURCE_PATHS = (
    REGISTRY, HEX_PATH, CATALOG,
    "src/qikvrt_m68000_runtime.py", "src/qikvrt_github_api_shim.py",
    "src/qikvrt_api_handler.py", "src/qikvrt_effect_ack.py",
    "scripts/qikvrt_api_client.py", "tools/qikvrt_spark_branch_work_unit.py",
    "tools/qikvrt_spark_branch_m68000_compiler.py",
    "src/m68000/qikvrt_spark_branch_plan_v1.s",
    "formalization/QIKVRT_Spark_v2/QIKVRTSparkV2.lean",
)


class RuntimeConflict(ValueError):
    """A request or running process no longer matches its source binding."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def source_binding(root: Path, repository: str) -> dict[str, Any]:
    """Observe local commit AND loaded-source bytes; dirty bytes are not a commit."""
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True,
            text=True, timeout=5,
        ).stdout.strip()

    head, tree = git("rev-parse", "HEAD", "HEAD^{tree}").splitlines()
    files = {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
             for path in SOURCE_PATHS}
    status = git("status", "--porcelain", "--untracked-files=all")
    if git("rev-parse", "HEAD", "HEAD^{tree}").splitlines() != [head, tree]:
        raise RuntimeConflict("checkout moved during source observation")
    return {
        "repository": repository, "head_sha": head, "tree_sha": tree,
        "checkout_clean": not bool(status), "source_files": files,
        "runtime_sha256": digest(files),
    }


class M68000Runtime:
    """One immutable kernel load, serialized execution, bounded receipt readback."""

    def __init__(self, root: Path, repository: str, *, capacity: int = 256):
        self.root = root.resolve()
        if self.root != ROOT:
            raise ValueError("MC68000 runtime must execute from its own checkout")
        if type(capacity) is not int or not 1 <= capacity <= 4096:
            raise ValueError("receipt capacity must be between 1 and 4096")
        self.binding = source_binding(self.root, repository)
        self.machine = bytes.fromhex((self.root / HEX_PATH).read_text("ascii"))
        registry = json.loads((self.root / REGISTRY).read_text())
        entries = [item for item in registry["kernels"] if item["id"] == KERNEL_ID]
        if (len(entries) != 1 or entries[0]["hex_path"] != HEX_PATH
                or entries[0]["machine_bytes"] != len(self.machine)
                or self.machine != compiler.MACHINE):
            raise ValueError("registered Spark kernel does not match compiler bytes")
        self.kernel_sha256 = hashlib.sha256(self.machine).hexdigest()
        self.capacity = capacity
        self.receipts: OrderedDict[str, bytes] = OrderedDict()
        self.lock = threading.RLock()
        self._ensure_current()

    def _ensure_current(self) -> None:
        if source_binding(self.root, self.binding["repository"]) != self.binding:
            raise RuntimeConflict("runtime source changed; restart and reobserve")

    def discovery(self) -> dict[str, Any]:
        self._ensure_current()
        return {
            "schema": "qikvrt_m68000_api_v1", "runtime": self.binding,
            "backend": "bounded_m68000_instruction_interpreter_v1",
            "kernels": [{"id": KERNEL_ID, "sha256": self.kernel_sha256,
                         "machine_bytes": len(self.machine),
                         "input": "D0.b: eight Spark observation flags",
                         "output": "D0: Spark plan code 0..11"}],
            "receipt_capacity": self.capacity,
            "receipt_retention": "process lifetime, oldest evicted at capacity",
            "full_machine_emulation": False,
            "physical_speedup_measured": False,
        }

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        if (not isinstance(request, dict) or set(request) != {
                "schema", "runtime", "kernel_id", "kernel_sha256", "registers"}):
            raise ValueError("execution request fields must match v1 exactly")
        if request["schema"] != "qikvrt_m68000_execution_request_v1":
            raise ValueError("unsupported execution schema")
        if request["kernel_id"] != KERNEL_ID:
            raise ValueError("kernel is not exposed by API v1")
        if request["kernel_sha256"] != self.kernel_sha256:
            raise RuntimeConflict("kernel digest mismatch")
        if canonical_bytes(request["runtime"]) != canonical_bytes(self.binding):
            raise RuntimeConflict("repository, head, tree or runtime binding mismatch")
        registers = request["registers"]
        if (not isinstance(registers, dict) or set(registers) != {"d0"}
                or type(registers["d0"]) is not int
                or not 0 <= registers["d0"] <= 255):
            raise ValueError("registers must contain exactly one unsigned byte d0")
        # Freeze caller data before hashing, execution and storage.
        request = json.loads(canonical_bytes(request))
        request_sha256 = digest(request)
        with self.lock:
            self._ensure_current()
            if request_sha256 in self.receipts:
                return json.loads(self.receipts[request_sha256])
            plan_code, count = compiler.execute_kernel(self.machine, request["registers"]["d0"])
            self._ensure_current()
            receipt = {
                "schema": "qikvrt_m68000_execution_receipt_v1",
                "request": request, "request_sha256": request_sha256,
                "registers": {"d0": plan_code},
                "dynamic_m68000_instructions": count,
                "backend": "bounded_m68000_instruction_interpreter_v1",
                "registered_machine_bytes_executed": True,
                "higher_level_rule_reinterpreted_for_decision": False,
                "full_machine_emulation": False,
                "physical_m68000_execution_observed": False,
                "physical_speedup_measured": False,
                "host_effects_executed": False,
                "native_approval_observed": False,
                "effect_state": "EFFECT_ACK_CONTINUE",
                "ordinary_release": False, "effect_ack_done_claimed": False,
            }
            receipt["receipt_sha256"] = digest(receipt)
            self.receipts[request_sha256] = canonical_bytes(receipt)
            while len(self.receipts) > self.capacity:
                self.receipts.popitem(last=False)
            return json.loads(self.receipts[request_sha256])

    def readback(self, request_sha256: str) -> dict[str, Any] | None:
        with self.lock:
            self._ensure_current()
            raw = self.receipts.get(request_sha256)
            return json.loads(raw) if raw is not None else None
