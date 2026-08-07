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
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json"


class BootBlock(RuntimeError):
    """A required repository-runtime gate failed."""


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
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootBlock(f"{name}: execution failed: {exc}") from exc
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
        raise BootBlock(f"{name}: exit {completed.returncode}: {detail}")
    return result


def git_value(*args: str) -> str:
    gate = run_gate("git " + " ".join(args), ["git", *args])
    return str(gate["stdout"])


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootBlock(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise BootBlock(f"{label} must contain an object")
    return value


def load_context() -> dict[str, Any]:
    return load_json_object(ROOT / "AI_CONTEXT.json", "AI_CONTEXT.json")


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit one JSON document")
    parser.add_argument(
        "--profile",
        default="all",
        choices=("core", "ietf", "formal", "audio", "publication", "all"),
        help="runtime profile checked without installation",
    )
    parser.add_argument("--task", default="", help="task label recorded in the boot report")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema": "qikvrt-ai-runtime-boot/1.1",
        "repository_root": str(ROOT),
        "task": args.task,
        "state": "RUNNING",
        "gates": [],
        "lifecycle": [
            "read AI and AI_CONTEXT.json",
            "load personal-origin and contribution-attribution contract",
            "load supplied bootstrap knowledge corpus with epistemic boundaries",
            "verify repository identity and Git ref",
            "verify handoff and required repository evidence",
            "verify integrity authorities",
            "verify declared tool/cache contracts",
            "check runtime profile without hidden installation",
            "hand control to the authorized task executor",
            "persist verified improvements through reviewed repository changes",
        ],
    }

    try:
        context = load_context()
        corpus = load_bootstrap_corpus()
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
        report["repository"] = git_value("config", "--get", "remote.origin.url")
        report["git_ref"] = git_value("rev-parse", "--abbrev-ref", "HEAD")
        report["git_commit"] = git_value("rev-parse", "HEAD")

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
            run_gate("AI handoff", [sys.executable, "-B", "tools/ai_handoff.py"])
        )
        report["gates"].append(
            run_gate(
                "repository integrity",
                [sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"],
            )
        )

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

        has_continue = any(gate["state"] == "CONTINUE" for gate in report["gates"])
        report["state"] = "CONTINUE" if has_continue else "PASS"
        report["next_action"] = (
            "Install explicitly accepted missing runtime components, then rerun the bootloader."
            if has_continue
            else "Execute the authorized task with corpus claim boundaries; persist improvements only through tests, integrity, review, and merge."
        )
    except BootBlock as exc:
        report["state"] = "BLOCK"
        report["blocker"] = str(exc)
        report["next_action"] = "Repair the named repository gate and rerun the bootloader."

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"AI_RUNTIME_BOOT_STATE={report['state']}")
        print(f"REPOSITORY={report.get('repository', 'unavailable')}")
        print(f"GIT_REF={report.get('git_ref', 'unavailable')}")
        print(f"GIT_COMMIT={report.get('git_commit', 'unavailable')}")
        corpus_report = report.get("knowledge_corpus", {})
        if corpus_report:
            print(f"KNOWLEDGE_CORPUS_ARTIFACTS={corpus_report.get('artifact_count', 0)}")
            print(f"KNOWLEDGE_CORPUS_UNTRANSCRIBED_AUDIO={corpus_report.get('untranscribed_audio_count', 0)}")
        for gate in report["gates"]:
            print(f"GATE_{gate['name'].upper().replace(' ', '_')}={gate['state']}")
        if "blocker" in report:
            print(f"BLOCKER={report['blocker']}")
        print(f"NEXT_ACTION={report['next_action']}")

    return 0 if report["state"] in {"PASS", "CONTINUE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
