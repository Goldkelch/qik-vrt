# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

D0 = {0: "NOOP", 1: "HOLD", 2: "REOBSERVE", 3: "REQUEST_AUTHORITY"}
OBJECTIVES = [
    "DETERMINISTIC_CORRECTNESS",
    "FALSE_AUTHORITY_OR_EFFECT_INFERENCE",
    "SELF_CONTINUATION_LIVENESS",
    "EXACT_BINDING_AND_REPRODUCIBILITY",
    "DUPLICATE_OR_STALE_WORK",
    "LATENCY_AND_RESOURCE_WASTE",
    "IMPLEMENTATION_SIMPLICITY",
    "TESTABILITY_AND_OBSERVABILITY",
    "PUBLICATION_WORTHINESS",
]
ACTIVITY_ONLY = {
    "observed_at",
    "updated_at",
    "run_count",
    "comment_count",
    "retry_count",
    "queue_position",
}
FORBIDDEN_CLAIMS = {
    "MERGE",
    "DEPLOYMENT",
    "PUBLICATION",
    "APPROVAL",
    "PASS",
    "FINAL_PASS",
    "EFFECT_ACK_DONE",
    "EMPIRICAL_CONFIRMATION",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def strip_activity(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: strip_activity(v) for k, v in sorted(value.items()) if k not in ACTIVITY_ONLY}
    if isinstance(value, list):
        return [strip_activity(v) for v in value]
    return value


def causal_fingerprint(problem: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(strip_activity(problem))).hexdigest()


def exact_subject(problem: dict[str, Any]) -> tuple[bool, list[str]]:
    subject = problem.get("subject")
    if not isinstance(subject, dict):
        return False, ["subject"]
    missing = [key for key in ("repository", "identity", "head", "tree") if not subject.get(key)]
    return not missing, missing


def unresolved_dependencies(problem: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for dep in problem.get("dependencies", []):
        if isinstance(dep, dict) and dep.get("state") not in {"SATISFIED", "INDEPENDENT"}:
            result.append(str(dep.get("id", "UNKNOWN_DEPENDENCY")))
    return sorted(result)


def objective_rank(name: str) -> int:
    try:
        return OBJECTIVES.index(name)
    except ValueError:
        return len(OBJECTIVES)


def reject_reason(move: dict[str, Any]) -> str | None:
    if move.get("transfers_predecessor_evidence") is True:
        return "PREDECESSOR_EVIDENCE_TRANSFER_FORBIDDEN"
    if move.get("widens_authority") is True:
        return "AUTHORITY_WIDENING_FORBIDDEN"
    if move.get("weakens_invariant") is True:
        return "INVARIANT_WEAKENING_FORBIDDEN"
    if not move.get("expected_readback"):
        return "EXPECTED_READBACK_REQUIRED"
    claims = {str(v) for v in move.get("claims_without_readback", [])}
    if claims & FORBIDDEN_CLAIMS:
        return "UNREADBACK_EXTERNAL_OR_TERMINAL_CLAIM_FORBIDDEN"
    return None


def resolve(problem: dict[str, Any]) -> dict[str, Any]:
    ok, missing = exact_subject(problem)
    fingerprint = causal_fingerprint(problem)
    base: dict[str, Any] = {
        "schema": "qikvrt_universal_evidence_spiral_receipt_v1",
        "causal_fingerprint": fingerprint,
        "subject": problem.get("subject"),
        "executed_move": None,
        "rejected_moves": [],
        "predecessor_evidence_transfer": False,
        "external_effect_claimed": False,
    }
    if not ok:
        return {**base, "d0": 2, "state": D0[2], "reason": "EXACT_SUBJECT_INCOMPLETE", "missing": missing}
    if problem.get("subject_state") == "STALE":
        return {**base, "d0": 2, "state": D0[2], "reason": "EXACT_SUBJECT_STALE"}

    deps = unresolved_dependencies(problem)
    if deps:
        return {**base, "d0": 1, "state": D0[1], "reason": "UNRESOLVED_DEPENDENCY", "dependencies": deps}

    admissible: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for raw in problem.get("candidate_moves", []):
        if not isinstance(raw, dict) or not raw.get("id"):
            rejected.append({"id": "UNKNOWN", "reason": "MALFORMED_MOVE"})
            continue
        reason = reject_reason(raw)
        if reason:
            rejected.append({"id": str(raw["id"]), "reason": reason})
            continue
        admissible.append(raw)

    base["rejected_moves"] = sorted(rejected, key=lambda item: (item["id"], item["reason"]))
    if not admissible:
        return {**base, "d0": 0, "state": D0[0], "reason": "NO_ADMISSIBLE_MOVE"}

    admissible.sort(
        key=lambda move: (
            objective_rank(str(move.get("objective", ""))),
            int(move.get("risk", 0)),
            str(move["id"]),
        )
    )
    chosen = admissible[0]
    authority = str(chosen.get("authority", "NONE"))
    granted = {str(v) for v in problem.get("granted_authorities", [])}
    if authority not in {"NONE", "REPOSITORY_READ", "REPOSITORY_INTERNAL"} and authority not in granted:
        return {
            **base,
            "d0": 3,
            "state": D0[3],
            "reason": "BEST_MOVE_REQUIRES_AUTHORITY",
            "requested_authority": authority,
            "selected_move": chosen["id"],
        }

    return {
        **base,
        "d0": 0,
        "state": "ACTION",
        "reason": "ONE_BOUNDED_MOVE_SELECTED",
        "selected_move": chosen["id"],
        "action": chosen.get("action"),
        "authority": authority,
        "expected_readback": chosen.get("expected_readback"),
        "closure_predicate": problem.get("closure_predicate", "EXPLICIT_SUCCESSOR_READBACK_REQUIRED"),
        "mutation_budget": 1 if chosen.get("mutating", False) else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve one exact QIK-VRT problem cycle deterministically.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    problem = json.loads(args.input.read_text(encoding="utf-8"))
    receipt = resolve(problem)
    rendered = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
