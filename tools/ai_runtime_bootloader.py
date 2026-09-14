#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed QIK-VRT repository runtime bootloader.

The bootloader reconstructs a new session from repository evidence. It is
standard-library only, performs no network access, and does not modify tracked
files. Runtime installation and task effects remain separate, explicit actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json"
ADAPTATION_POLICY_PATH = ROOT / "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json"
ADAPTATION_MATRIX_PATH = ROOT / "state/interface_adaptation/EVALUATION_MATRIX.json"
BOOT_SOURCE_PATHS = (
    "tools/ai_runtime_bootloader.py",
    "tools/ai_handoff.py",
    "tools/qikvrt_integrity.py",
    "tools/qikvrt_tool_cache.py",
    "tools/bootstrap-runtime.sh",
    "tools/bootstrap-gh.sh",
    "policy/CANONICAL_UPSTREAM_REMOTE_V1.json",
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)


class BootBlock(RuntimeError):
    """A required repository-runtime gate failed."""

    def __init__(self, message: str, gate: dict[str, Any] | None = None):
        super().__init__(message)
        self.gate = gate


def run_gate(name: str, command: list[str], accepted: set[int] | None = None) -> dict[str, Any]:
    accepted = accepted or {0}
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1",
                 "GIT_TERMINAL_PROMPT": "0"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootBlock(f"{name}: execution failed: {exc}", {
            "name": name, "command": command, "exit_code": None,
            "stdout": "", "stderr": str(exc), "state": "BLOCK",
        }) from exc
    result = {
        "name": name,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "state": "PASS" if completed.returncode == 0 else "CONTINUE",
    }
    if completed.returncode not in accepted:
        result["state"] = "BLOCK"
        detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic"
        raise BootBlock(f"{name}: exit {completed.returncode}: {detail}", result)
    return result


def git_value(*args: str) -> str:
    gate = run_gate("git " + " ".join(args), ["git", *args])
    return str(gate["stdout"])


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootBlock(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise BootBlock(f"{label} must contain an object")
    return value


def load_context() -> dict[str, Any]:
    return load_json_object(ROOT / "AI_CONTEXT.json", "AI_CONTEXT.json")


def validate_entrypoint(context: dict[str, Any]) -> dict[str, Any]:
    entry = context.get("entrypoint_contract")
    if not isinstance(entry, dict) or entry.get("schema") != "qikvrt-ai-entrypoint-contract/1.0":
        raise BootBlock("ENTRYPOINT_CONTRACT_INVALID")
    policy = load_json_object(ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json", "canonical upstream policy")
    canonical = policy.get("canonical_upstream")
    if not isinstance(canonical, dict):
        raise BootBlock("ENTRYPOINT_AUTHORITY_INVALID")
    repository = canonical.get("repository")
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise BootBlock("ENTRYPOINT_AUTHORITY_INVALID")
    expected = {
        "authority_repository": repository,
        "authority_policy": "policy/CANONICAL_UPSTREAM_REMOTE_V1.json",
        "discovery_url": f"https://github.com/{repository}/blob/main/AI",
        "raw_context_url": f"https://raw.githubusercontent.com/{repository}/main/AI_CONTEXT.json",
        "resolve_ref_url": f"https://api.github.com/repos/{repository}/commits/main",
        "pinned_raw_url_template": f"https://raw.githubusercontent.com/{repository}/{{commit}}/{{path}}",
        "read_order_field": "required_read_order",
    }
    if any(entry.get(key) != value for key, value in expected.items()):
        raise BootBlock("ENTRYPOINT_AUTHORITY_BINDING_DRIFT")
    if entry.get("http_get_executes_task") is not False or entry.get("mutable_urls_are_discovery_only") is not True:
        raise BootBlock("ENTRYPOINT_DISCOVERY_BOUNDARY_DRIFT")
    effect = entry.get("effect_gate")
    receipt = entry.get("boot_receipt")
    if (not isinstance(effect, dict) or effect.get("bootstrap_may_issue_done") is not False
            or effect.get("implementation") != "src/qikvrt_effect_ack.py"
            or effect.get("adapter") != "src/qikvrt_api_handler.py"
            or effect.get("protocol_schema") != "qikvrt_responsibility_protocol_v1"
            or not isinstance(receipt, dict) or receipt.get("scope") != "LOCAL_BOOTSTRAP_ONLY"
            or receipt.get("schema") != "qikvrt-ai-runtime-boot/1.3"
            or receipt.get("ordinary_release") is not False
            or receipt.get("remote_state_observed") is not False):
        raise BootBlock("ENTRYPOINT_EFFECT_BOUNDARY_DRIFT")
    routes = entry.get("routes")
    if not isinstance(routes, dict) or set(routes) != {
        "orientation", "provenance", "capabilities", "runtime", "repository_change", "publications", "effect_gate"
    }:
        raise BootBlock("ENTRYPOINT_ROUTES_INVALID")
    for paths in routes.values():
        if not isinstance(paths, list) or not 1 <= len(paths) <= 8 or any(not isinstance(path, str) for path in paths):
            raise BootBlock("ENTRYPOINT_ROUTES_INVALID")
    return entry


def capture_subject(context: dict[str, Any]) -> dict[str, Any]:
    """Bind local source bytes, not the mutable remote or a past progress report."""
    paths = context.get("required_read_order")
    if (not isinstance(paths, list) or not 1 <= len(paths) <= 64
            or any(not isinstance(path, str) for path in paths)
            or len(set(paths)) != len(paths)):
        raise BootBlock("SOURCE_READ_ORDER_INVALID")
    entry = context.get("entrypoint_contract", {})
    if not isinstance(entry, dict) or not isinstance(entry.get("routes", {}), dict):
        raise BootBlock("ENTRYPOINT_ROUTES_INVALID")
    route_paths = []
    for group in entry.get("routes", {}).values():
        if (not isinstance(group, list) or not 1 <= len(group) <= 8
                or any(not isinstance(path, str) for path in group)):
            raise BootBlock("ENTRYPOINT_ROUTES_INVALID")
        route_paths.extend(group)
    paths = sorted(set(paths) | set(BOOT_SOURCE_PATHS) | set(route_paths))
    for path in paths:
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", path)
                or path.startswith("-") or any(p in {".", "..", ".git"} for p in Path(path).parts)):
            raise BootBlock("SOURCE_PATH_INVALID")
        current = ROOT
        for part in Path(path).parts:
            current = current / part
            if current.is_symlink():
                raise BootBlock(f"SOURCE_PATH_INVALID: {path}")
    if Path(git_value("rev-parse", "--show-toplevel")).resolve() != ROOT.resolve():
        raise BootBlock("SOURCE_REPOSITORY_ROOT_MISMATCH")
    head = git_value("rev-parse", "--verify", "HEAD^{commit}")
    tree = git_value("rev-parse", "--verify", f"{head}^{{tree}}")
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (head, tree)):
        raise BootBlock("SOURCE_GIT_IDENTITY_INVALID")
    entries = git_value("ls-tree", "-r", "-z", "--full-tree", head, "--", *paths)
    blobs = {}
    for entry in entries.split("\0"):
        if entry:
            metadata, path = entry.split("\t", 1)
            mode, kind, digest = metadata.split()
            if kind == "blob" and mode in {"100644", "100755"}:
                blobs[path] = digest
    inputs = []
    for path in paths:
        target = ROOT / path
        try:
            if not target.is_file() or target.stat().st_size > 2 * 1024 * 1024:
                raise BootBlock(f"SOURCE_FILE_UNAVAILABLE_OR_OVERSIZED: {path}")
            with target.open("rb") as stream:
                raw = stream.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise BootBlock(f"SOURCE_FILE_UNAVAILABLE_OR_OVERSIZED: {path}")
        except OSError as exc:
            raise BootBlock(f"SOURCE_FILE_UNREADABLE: {path}") from exc
        blob = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
        if blobs.get(path) != blob:
            raise BootBlock(f"SOURCE_BYTES_NOT_COMMIT_BOUND: {path}")
        inputs.append({"path": path, "bytes": len(raw), "git_blob_sha1": blob,
                       "sha256": hashlib.sha256(raw).hexdigest()})
    subject = {
        "commit": head, "tree": tree,
        "ref": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git_value("status", "--porcelain=v1", "--untracked-files=normal")),
        "inputs": inputs, "remote_state_observed": False,
    }
    if git_value("rev-parse", "--verify", "HEAD^{commit}") != head:
        raise BootBlock("SOURCE_CHANGED_DURING_OBSERVATION")
    return subject


def require_bound_subject(subject: dict[str, Any], expected_head: str | None) -> None:
    if expected_head is not None and subject["commit"] != expected_head:
        raise BootBlock("EXPECTED_HEAD_MISMATCH")
    if subject["dirty"]:
        raise BootBlock("WORKTREE_NOT_COMMIT_BOUND")


def load_bootstrap_corpus() -> dict[str, Any]:
    corpus = load_json_object(CORPUS_PATH, str(CORPUS_PATH.relative_to(ROOT)))
    if corpus.get("schema") != "qikvrt_ai_bootstrap_knowledge_corpus_v1":
        raise BootBlock("bootstrap knowledge corpus schema drift")
    if corpus.get("canonical_entrypoint") != "AI":
        raise BootBlock("bootstrap knowledge corpus must bind canonical /AI")
    artifacts = corpus.get("source_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise BootBlock("bootstrap knowledge corpus lacks source artifacts")
    seen: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise BootBlock("bootstrap knowledge corpus artifact is malformed")
        name = artifact.get("name")
        digest = artifact.get("sha256")
        status = artifact.get("content_status")
        if not isinstance(name, str) or not name or name in seen:
            raise BootBlock("bootstrap knowledge corpus artifact name is invalid or duplicated")
        seen.add(name)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BootBlock(f"bootstrap knowledge corpus SHA-256 is invalid: {name}")
        if status not in {"PARSED", "VISUALLY_INTERPRETED", "UNTRANSCRIBED", "USER_DECLARED_QR_TARGET"}:
            raise BootBlock(f"bootstrap knowledge corpus status is invalid: {name}")
    required_invariants = {
        "REPOSITORY_EVIDENCE_OVERRIDES_CHAT_AND_MODEL_MEMORY",
        "FORMAL_PROOF_IS_NOT_EMPIRICAL_CONFIRMATION",
        "ARTIFICIAL_COGNITION_IS_NOT_AN_AUTOMATIC_TRUTH_MACHINE",
        "HUMAN_AND_AI_CONTRIBUTIONS_REMAIN_SEPARATELY_ATTRIBUTABLE",
    }
    invariants = corpus.get("core_invariants")
    if not isinstance(invariants, list) or not required_invariants.issubset(set(invariants)):
        raise BootBlock("bootstrap knowledge corpus is missing mandatory epistemic invariants")
    audio_policy = corpus.get("audio_policy")
    if not isinstance(audio_policy, dict) or audio_policy.get("untranscribed_audio_may_supply_semantic_claims") is not False:
        raise BootBlock("bootstrap knowledge corpus must fail closed on untranscribed audio")
    return corpus


def load_interface_adaptation() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = load_json_object(
        ADAPTATION_POLICY_PATH, str(ADAPTATION_POLICY_PATH.relative_to(ROOT))
    )
    matrix = load_json_object(
        ADAPTATION_MATRIX_PATH, str(ADAPTATION_MATRIX_PATH.relative_to(ROOT))
    )
    if policy.get("schema") != "qikvrt_human_machine_interface_adaptation_v1":
        raise BootBlock("human-machine interface adaptation policy schema drift")
    if policy.get("reuse_before_create") is not True:
        raise BootBlock("human-machine interface adaptation must enforce REUSE_BEFORE_CREATE")
    if policy.get("adaptation_mode") != "MEASURE_CACHE_RANK_PROPOSE_REVIEW":
        raise BootBlock("human-machine interface adaptation mode drift")
    never_optimize_by = policy.get("never_optimize_by")
    mandatory_prohibitions = {
        "skipping mandatory gates",
        "weakening exact-head binding",
        "dropping provenance",
        "persisting secrets",
        "treating cached output as proof authority",
        "performing external effects without authorization",
    }
    if not isinstance(never_optimize_by, list) or not mandatory_prohibitions.issubset(set(never_optimize_by)):
        raise BootBlock("adaptive optimization is missing mandatory safety prohibitions")
    cache_layers = policy.get("cache_layers")
    if not isinstance(cache_layers, list) or len(cache_layers) < 4:
        raise BootBlock("adaptive optimization cache hierarchy is incomplete")
    cache_ids = {item.get("id") for item in cache_layers if isinstance(item, dict)}
    if cache_ids != {"L0_SESSION", "L1_PERSONAL_WORKING_MEMORY", "L2_RUNTIME_TOOLCHAIN", "L3_DERIVED_KNOWLEDGE"}:
        raise BootBlock("adaptive optimization cache hierarchy drift")
    matrix_contract = policy.get("evaluation_matrix")
    if not isinstance(matrix_contract, dict):
        raise BootBlock("adaptive optimization lacks evaluation matrix contract")
    if matrix_contract.get("path") != str(ADAPTATION_MATRIX_PATH.relative_to(ROOT)):
        raise BootBlock("adaptive optimization evaluation matrix path drift")
    if matrix.get("schema") != "qikvrt_human_machine_interface_evaluation_matrix_v1":
        raise BootBlock("human-machine interface evaluation matrix schema drift")
    selection = matrix.get("selection")
    if not isinstance(selection, dict) or selection.get("quality_regression_allowed") is not False:
        raise BootBlock("evaluation matrix must fail closed on quality regression")
    if selection.get("mandatory_gate_reduction_allowed") is not False:
        raise BootBlock("evaluation matrix must not optimize by reducing mandatory gates")
    return policy, matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit one JSON document")
    parser.add_argument(
        "--profile",
        default="all",
        choices=("core", "ietf", "formal", "audio", "publication", "all"),
        help="runtime profile checked without installation",
    )
    parser.add_argument("--task", default="", help="task label recorded in the boot report")
    parser.add_argument("--expect-head", help="exact commit observed by the caller; never a branch name")
    args = parser.parse_args(argv)

    report: dict[str, Any] = {
        "schema": "qikvrt-ai-runtime-boot/1.3",
        "scope": "LOCAL_BOOTSTRAP_ONLY",
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expected_head": args.expect_head,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "ordinary_release": False,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        "remote_state_observed": False,
        "source_reobserved_unchanged": False,
        "first_blocker": None,
        "repository_root": str(ROOT),
        "task": args.task,
        "state": "RUNNING",
        "gates": [],
        "lifecycle": [
            "read AI and AI_CONTEXT.json",
            "load personal-origin and contribution-attribution contract",
            "load supplied bootstrap knowledge corpus with epistemic boundaries",
            "load adaptive human-machine interface cache and evaluation contracts",
            "verify repository identity and Git ref",
            "verify handoff and required repository evidence",
            "verify integrity authorities",
            "verify declared tool/cache contracts",
            "check runtime profile without hidden installation",
            "hand control to the authorized task executor using fastest verified reusable path",
            "measure reusable interaction and runtime evidence",
            "persist reviewed improvements through repository changes",
        ],
    }

    phase = "source binding"
    try:
        if args.expect_head is not None and not re.fullmatch(r"[0-9a-f]{40}", args.expect_head):
            raise BootBlock("EXPECTED_HEAD_INVALID")
        context = load_context()
        validate_entrypoint(context)
        subject = capture_subject(context)
        report["subject"] = subject
        report["git_commit"] = subject["commit"]
        report["git_tree"] = subject["tree"]
        report["git_ref"] = subject["ref"]
        require_bound_subject(subject, args.expect_head)
        report["source_fingerprint_sha256"] = hashlib.sha256(
            json.dumps(subject, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        report["discovery"] = context.get("entrypoint_contract", {})
        # A declared authority URL is not authenticated local/remote identity.
        # Do not print Git remotes: they can contain credentials or private URLs.
        report["repository"] = context.get("entrypoint_contract", {}).get("authority_repository", "UNAVAILABLE")
        report["repository_identity_source"] = "DECLARED_CONTEXT_NOT_REMOTE_OBSERVATION"
        phase = "bootstrap knowledge corpus"
        corpus = load_bootstrap_corpus()
        phase = "human machine interface adaptation"
        adaptation_policy, adaptation_matrix = load_interface_adaptation()
        artifacts = corpus["source_artifacts"]
        untranscribed = [item for item in artifacts if item.get("content_status") == "UNTRANSCRIBED"]
        report["context_id"] = context.get("context_id", "unknown")
        report["knowledge_corpus"] = {
            "corpus_id": corpus.get("corpus_id"),
            "artifact_count": len(artifacts),
            "untranscribed_audio_count": len(untranscribed),
            "untranscribed_audio_semantic_claims_allowed": False,
            "round_trip": corpus.get("round_trip", []),
            "epistemic_partition": corpus.get("epistemic_partition", []),
            "scientific_boundaries": corpus.get("scientific_boundaries", {}),
        }
        report["interface_adaptation"] = {
            "mode": adaptation_policy.get("adaptation_mode"),
            "default_state": adaptation_policy.get("default_state"),
            "cache_layers": [item.get("id") for item in adaptation_policy.get("cache_layers", [])],
            "routing": adaptation_policy.get("adaptive_routing", {}).get("strategy"),
            "matrix_state": adaptation_matrix.get("state"),
            "matrix_rows": len(adaptation_matrix.get("rows", [])),
            "minimum_observations_before_preference": adaptation_policy.get("evaluation_matrix", {}).get("minimum_observations_before_preference"),
        }
        report["gates"].append(
            {
                "name": "bootstrap knowledge corpus",
                "command": ["internal", str(CORPUS_PATH.relative_to(ROOT))],
                "exit_code": 0,
                "stdout": f"artifacts={len(artifacts)} untranscribed_audio={len(untranscribed)}",
                "stderr": "",
                "state": "PASS",
            }
        )
        report["gates"].append(
            {
                "name": "human machine interface adaptation",
                "command": ["internal", str(ADAPTATION_POLICY_PATH.relative_to(ROOT))],
                "exit_code": 0,
                "stdout": f"mode={adaptation_policy.get('adaptation_mode')} matrix_rows={len(adaptation_matrix.get('rows', []))}",
                "stderr": "",
                "state": "PASS",
            }
        )
        phase = "AI handoff"
        report["gates"].append(
            run_gate("AI handoff", [sys.executable, "-B", "tools/ai_handoff.py"])
        )
        phase = "repository integrity"
        report["gates"].append(
            run_gate(
                "repository integrity",
                [sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"],
            )
        )

        phase = "tool cache coverage"
        cache_verifier = ROOT / "tools/qikvrt_tool_cache.py"
        if cache_verifier.is_file():
            report["gates"].append(
                run_gate(
                    "tool cache coverage",
                    [sys.executable, "-B", str(cache_verifier.relative_to(ROOT)), "verify"],
                )
            )
        else:
            raise BootBlock("tools/qikvrt_tool_cache.py is missing")

        phase = "runtime profile"
        bootstrap = ROOT / "tools/bootstrap-runtime.sh"
        if bootstrap.is_file():
            report["gates"].append(
                run_gate(
                    "runtime profile",
                    ["sh", str(bootstrap.relative_to(ROOT)), "--check-only", "--profile", args.profile],
                    accepted={0, 20},
                )
            )
        else:
            raise BootBlock("tools/bootstrap-runtime.sh is missing")

        phase = "source reobservation"
        after = capture_subject(load_context())
        require_bound_subject(after, args.expect_head)
        if after != subject:
            raise BootBlock("SOURCE_CHANGED_DURING_BOOT")
        report["source_reobserved_unchanged"] = True
        has_continue = any(gate["state"] == "CONTINUE" for gate in report["gates"])
        report["state"] = "CONTINUE" if has_continue else "PASS"
        report["next_action"] = (
            "Install explicitly accepted missing runtime components, then rerun the bootloader."
            if has_continue
            else "Execute the authorized task using the fastest previously verified path; record comparable performance evidence and persist only reviewed improvements."
        )
    except (BootBlock, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        report["state"] = "BLOCK"
        report["blocker"] = str(exc)
        gate = (exc.gate if isinstance(exc, BootBlock) else None) or {
            "name": phase, "state": "BLOCK", "exit_code": None,
            "command": [], "stdout": "", "stderr": str(exc),
        }
        report["gates"].append(gate)
        report["first_blocker"] = gate
        report["effect_state"] = "EFFECT_ACK_BLOCK"
        report["next_action"] = "Repair the named repository gate and rerun the bootloader."

    report["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    resume = ["python3", "-B", "tools/ai_runtime_bootloader.py", "--profile", args.profile, "--json"]
    if args.task:
        resume.extend(["--task", args.task])
    report["continuation"] = {
        "state": {"BLOCK": "REPAIR_REQUIRED", "CONTINUE": "RUNTIME_REQUIREMENTS_OPEN",
                  "PASS": "TASK_AUTHORITY_REOBSERVATION_REQUIRED"}[report["state"]],
        "next_action": report["next_action"],
        "retry_condition": "The named input, gate or authorized runtime prerequisite changed; reobserve the exact subject first.",
        "resume_command": resume,
        "expected_head_rule": "Supply --expect-head from a fresh independent ref read; never transfer this report to a successor.",
        "automatic_retry": False,
        "task_execution_authorized": False,
        "required_before_effect": ["exact task and target binding", "current policy and authorization",
                                   "applicable exact-head tests and independent review"],
        "required_after_effect": ["effect execution evidence", "target postcondition readback"],
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"AI_RUNTIME_BOOT_STATE={report['state']}")
        print(f"REPOSITORY={report.get('repository', 'unavailable')}")
        print(f"GIT_REF={report.get('git_ref', 'unavailable')}")
        print(f"GIT_COMMIT={report.get('git_commit', 'unavailable')}")
        print(f"GIT_TREE={report.get('git_tree', 'unavailable')}")
        print(f"EFFECT_STATE={report['effect_state']}")
        print("ORDINARY_RELEASE=false")
        corpus_report = report.get("knowledge_corpus", {})
        if corpus_report:
            print(f"KNOWLEDGE_CORPUS_ARTIFACTS={corpus_report.get('artifact_count', 0)}")
            print(f"KNOWLEDGE_CORPUS_UNTRANSCRIBED_AUDIO={corpus_report.get('untranscribed_audio_count', 0)}")
        adaptation_report = report.get("interface_adaptation", {})
        if adaptation_report:
            print(f"INTERFACE_ADAPTATION_MODE={adaptation_report.get('mode', 'unavailable')}")
            print(f"INTERFACE_ADAPTATION_MATRIX_ROWS={adaptation_report.get('matrix_rows', 0)}")
            print(f"INTERFACE_ADAPTATION_ROUTING={adaptation_report.get('routing', 'unavailable')}")
        for gate in report["gates"]:
            print(f"GATE_{gate['name'].upper().replace(' ', '_')}={gate['state']}")
        if "blocker" in report:
            print(f"BLOCKER={report['blocker']}")
        print(f"NEXT_ACTION={report['next_action']}")

    return 0 if report["state"] in {"PASS", "CONTINUE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
