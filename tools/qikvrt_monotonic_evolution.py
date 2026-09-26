#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed comparison of two externally attested, exact-subject observations.

This is a necessary admission predicate, NOT a measurement producer, signature
verifier, promotion executor, or proof about unregistered workloads. Callers
must independently attest the supplied observation digests and subject bindings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.qikvrt_anticipation import classify_monotonic_transition  # noqa: E402

SCHEMA = "qikvrt_monotonic_observation_v1"
HEX = re.compile(r"^[0-9a-f]+$")


class GateError(ValueError):
    def __init__(self, code: str, disposition: str = "HOLD"):
        super().__init__(code)
        self.code, self.disposition = code, disposition


def require(condition: bool, code: str, disposition: str = "HOLD") -> None:
    if not condition:
        raise GateError(code, disposition)


def digest(value: Any, length: int = 64) -> bool:
    return isinstance(value, str) and len(value) == length and bool(HEX.fullmatch(value))


def exact_keys(value: Any, keys: set[str], label: str) -> None:
    require(isinstance(value, dict) and set(value) == keys, f"INVALID_{label}")


def subject(value: Any) -> None:
    exact_keys(value, {"repository", "head", "tree"}, "SUBJECT")
    require(isinstance(value["repository"], str) and bool(value["repository"]), "INVALID_REPOSITORY")
    require(digest(value["head"], 40) and digest(value["tree"], 40), "INVALID_EXACT_SUBJECT")


def mapping(value: Any, label: str, nonempty: bool = True) -> None:
    require(isinstance(value, dict) and (bool(value) or not nonempty), f"MISSING_{label}")
    require(all(isinstance(k, str) and bool(k) for k in value), f"INVALID_{label}_IDS")


def witness(value: Any, expected: dict[str, str]) -> None:
    exact_keys(value, {"subject", "execution_id", "sha256"}, "WITNESS")
    subject(value["subject"])
    require(value["subject"] == expected, "WITNESS_SUBJECT_MISMATCH")
    require(digest(value["sha256"]), "INVALID_WITNESS_HASH")
    require(isinstance(value["execution_id"], str) and bool(value["execution_id"]), "MISSING_EXECUTION_ID")


def observation(value: Any, expected: dict[str, str]) -> None:
    exact_keys(value, {"schema", "subject", "nodes", "edges", "capabilities", "performance"}, "OBSERVATION")
    require(value["schema"] == SCHEMA, "SCHEMA_MISMATCH")
    subject(value["subject"])
    require(value["subject"] == expected, "OBSERVATION_SUBJECT_MISMATCH")
    for name in ("nodes", "edges", "capabilities", "performance"):
        mapping(value[name], name.upper(), nonempty=(name != "edges"))
    require(all(digest(v) for v in value["nodes"].values()), "INVALID_NODE_DIGEST")
    for edge in value["edges"].values():
        exact_keys(edge, {"source", "target", "relation", "sha256"}, "EDGE")
        require(isinstance(edge["source"], str) and isinstance(edge["target"], str), "INVALID_EDGE_ENDPOINT")
        require(edge["source"] in value["nodes"] and edge["target"] in value["nodes"], "DANGLING_EDGE")
        require(isinstance(edge["relation"], str) and bool(edge["relation"]) and digest(edge["sha256"]), "INVALID_EDGE")
    for cap in value["capabilities"].values():
        exact_keys(cap, {"contract_sha256", "status", "witness"}, "CAPABILITY")
        require(digest(cap["contract_sha256"]), "INVALID_CAPABILITY_CONTRACT")
        require(cap["status"] == "PASS", "CAPABILITY_NOT_PASSED", "REJECTED_REGRESSION")
        witness(cap["witness"], expected)
    for metric in value["performance"].values():
        exact_keys(metric, {"direction", "unit", "workload_sha256", "environment_sha256", "protocol_sha256", "samples", "witness"}, "METRIC")
        require(metric["direction"] in ("min", "max"), "INVALID_METRIC_DIRECTION")
        require(isinstance(metric["unit"], str) and bool(metric["unit"]), "MISSING_UNIT")
        for key in ("workload_sha256", "environment_sha256", "protocol_sha256"):
            require(digest(metric[key]), "INVALID_METRIC_BINDING")
        samples = metric["samples"]
        require(isinstance(samples, list) and len(samples) >= 5, "INSUFFICIENT_SAMPLES")
        require(all(type(x) is int and x >= 0 for x in samples), "INVALID_SAMPLE")
        witness(metric["witness"], expected)


def fresh(previous: dict[str, Any], candidate: dict[str, Any]) -> None:
    require(previous["witness"]["execution_id"] != candidate["witness"]["execution_id"], "PREDECESSOR_EXECUTION_REUSED")
    require(previous["witness"]["sha256"] != candidate["witness"]["sha256"], "PREDECESSOR_RECEIPT_REUSED")


def assess(previous: Any, candidate: Any, baseline_subject: dict[str, str], candidate_subject: dict[str, str]) -> dict[str, Any]:
    """Noncompensatory partial order. Unknown/incomparable evidence never passes."""
    result: dict[str, Any] = {"schema": "qikvrt_monotonic_gate_receipt_v1", "scope": "externally-attested registered observations only", "eligible": False, "promotion_executed": False, "effect_ack_done": False}
    try:
        subject(baseline_subject)
        subject(candidate_subject)
        require(baseline_subject["repository"] == candidate_subject["repository"], "REPOSITORY_MISMATCH")
        try:
            observation(previous, baseline_subject)
        except GateError as error:
            raise GateError("BASELINE_INVALID:" + error.code) from error
        observation(candidate, candidate_subject)
        old_receipts = {item["witness"]["sha256"] for category in ("capabilities", "performance") for item in previous[category].values()}
        old_executions = {item["witness"]["execution_id"] for category in ("capabilities", "performance") for item in previous[category].values()}
        for category in ("capabilities", "performance"):
            for item in candidate[category].values():
                require(item["witness"]["sha256"] not in old_receipts, "PREDECESSOR_RECEIPT_REUSED")
                require(item["witness"]["execution_id"] not in old_executions, "PREDECESSOR_EXECUTION_REUSED")
        for registry in ("nodes", "edges"):
            for key, entry in previous[registry].items():
                require(key in candidate[registry] and candidate[registry][key] == entry, f"{registry.upper()}_REMOVED_OR_REWRITTEN:{key}", "REJECTED_REGRESSION")
        for name, cap in previous["capabilities"].items():
            require(name in candidate["capabilities"], f"CAPABILITY_REMOVED:{name}", "REJECTED_REGRESSION")
            nxt = candidate["capabilities"][name]
            require(cap["contract_sha256"] == nxt["contract_sha256"], f"CAPABILITY_CONTRACT_CHANGED:{name}")
            fresh(cap, nxt)
        old_vector: dict[str, int] = {}
        new_vector: dict[str, int] = {}
        for name, metric in previous["performance"].items():
            require(name in candidate["performance"], f"METRIC_REMOVED:{name}", "REJECTED_REGRESSION")
            nxt = candidate["performance"][name]
            for binding in ("direction", "unit", "workload_sha256", "environment_sha256", "protocol_sha256"):
                require(metric[binding] == nxt[binding], f"INCOMPARABLE_{binding.upper()}:{name}")
            require(len(metric["samples"]) == len(nxt["samples"]), f"SAMPLE_COUNT_CHANGED:{name}")
            fresh(metric, nxt)
            sign = -1 if metric["direction"] == "min" else 1
            # Every sorted sample is compared. A better average cannot hide a worse tail.
            for i, (a, b) in enumerate(zip(sorted(metric["samples"]), sorted(nxt["samples"]))):
                old_vector[f"{name}:{i}"] = sign * a
                new_vector[f"{name}:{i}"] = sign * b
        performance_class = classify_monotonic_transition(old_vector, new_vector)
        require(performance_class != "REJECTED_REGRESSION", "PERFORMANCE_REGRESSION", "REJECTED_REGRESSION")
        additions = {name: sorted(set(candidate[name]) - set(previous[name])) for name in ("nodes", "edges", "capabilities", "performance")}
        improved = performance_class == "NON_REGRESSING_GATE_IMPROVEMENT" or bool(additions["capabilities"])
        evidence_grew = bool(additions["nodes"] or additions["edges"])
        # A new metric alone is not proof of improved performance or capability.
        require(evidence_grew, "NO_NEW_EVIDENCE", "PRESERVE_BASELINE")
        result.update(disposition="NON_REGRESSING_GATE_IMPROVEMENT" if improved else "NON_REGRESSING_EVIDENCE_EXTENSION", eligible=True, performance=performance_class, strict_capability_or_performance_improvement=improved, additions=additions)
    except GateError as error:
        result.update(disposition=error.disposition, reason=error.code)
    except (KeyError, TypeError, ValueError) as error:
        result.update(disposition="HOLD", reason="MALFORMED_OBSERVATION", detail=type(error).__name__)
    return result


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def read_bound(path: Path, expected_sha256: str) -> Any:
    require(digest(expected_sha256), "INVALID_EXPECTED_HASH")
    require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_INPUT")
    payload = path.read_bytes()
    require(hashlib.sha256(payload).hexdigest() == expected_sha256, "INPUT_DIGEST_MISMATCH")
    return json.loads(payload, object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(GateError("NONFINITE_JSON")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "bindings"):
        parser.add_argument(f"--{name}", required=True, type=Path)
        parser.add_argument(f"--{name}-sha256", required=True)
    args = parser.parse_args()
    try:
        previous, candidate, bindings = [read_bound(getattr(args, name), getattr(args, f"{name}_sha256")) for name in ("baseline", "candidate", "bindings")]
        exact_keys(bindings, {"baseline", "candidate"}, "BINDINGS")
        result = assess(previous, candidate, bindings["baseline"], bindings["candidate"])
        result["input_sha256"] = {name: getattr(args, f"{name}_sha256") for name in ("baseline", "candidate", "bindings")}
    except (GateError, OSError, ValueError) as error:
        result = {"eligible": False, "disposition": "HOLD", "reason": str(error), "promotion_executed": False, "effect_ack_done": False}
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["eligible"] else (1 if result["disposition"] == "REJECTED_REGRESSION" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
