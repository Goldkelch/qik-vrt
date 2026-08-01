#!/usr/bin/env python3
"""Deterministic, proposal-only evaluation of bounded scientific claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
from typing import Any


SCHEMA = "qikvrt_scientific_claim_envelope_v1"
CORPUS_SCHEMA = "qikvrt_scientific_fact_corpus_v1"
REPORT_SCHEMA = "qikvrt_scientific_claim_evaluation_v1"
MERGE_SCHEMA = "qikvrt_scientific_fact_mesh_merge_v1"
CLASSES = {
    "FORMAL_PROVED": "PROVED",
    "EMPIRICALLY_EVIDENCED": "EVIDENCED",
    "SOURCE_BOUND": "BOUND",
    "NORMATIVE": "DECLARED",
    "INTERPRETATIVE": "DECLARED",
    "OPEN": "OPEN",
}
CLAIM_KEYS = {
    "schema", "claim_id", "statement", "classification", "status",
    "scope", "boundary", "sources", "evidence", "proofs",
    "dependencies", "negates", "novelty",
}
NOVELTY_KEYS = {"method", "claimed"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CLAIM_ID = re.compile(r"^[A-Z][A-Z0-9-]{2,63}$")


class ValidationError(ValueError):
    """Input is malformed rather than merely epistemically incomplete."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def canonical_statement(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).strip().split())


def statement_sha256(value: str) -> str:
    return hashlib.sha256(canonical_statement(value).encode("utf-8")).hexdigest()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: top level must be an object")
    return value


def write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def require_list(value: dict[str, Any], key: str) -> list[Any]:
    item = value.get(key)
    if not isinstance(item, list):
        raise ValidationError(f"{key} must be an array")
    return item


def validate_claim_shape(claim: dict[str, Any]) -> None:
    unknown = set(claim) - CLAIM_KEYS
    missing = CLAIM_KEYS - set(claim)
    if unknown or missing:
        raise ValidationError(
            f"claim keys differ: missing={sorted(missing)} unknown={sorted(unknown)}")
    if claim["schema"] != SCHEMA:
        raise ValidationError("unsupported claim schema")
    if not isinstance(claim["claim_id"], str) or not CLAIM_ID.fullmatch(claim["claim_id"]):
        raise ValidationError("invalid claim_id")
    for key in ("statement", "scope", "boundary"):
        if not isinstance(claim[key], str) or not claim[key].strip():
            raise ValidationError(f"{key} must be non-empty text")
    if claim["classification"] not in CLASSES:
        raise ValidationError("unsupported classification")
    if claim["status"] != CLASSES[claim["classification"]]:
        raise ValidationError("classification/status mismatch")
    for key in ("sources", "evidence", "proofs", "dependencies", "negates"):
        require_list(claim, key)
    for key in ("dependencies", "negates"):
        values = claim[key]
        if len(values) != len(set(values)) or not all(
                isinstance(item, str) and CLAIM_ID.fullmatch(item) for item in values):
            raise ValidationError(f"{key} must contain unique claim identifiers")
    novelty = claim["novelty"]
    if not isinstance(novelty, dict) or set(novelty) != NOVELTY_KEYS:
        raise ValidationError("invalid novelty object")
    if novelty["method"] != "CORPUS_RELATIVE_EXACT_CANONICAL_STATEMENT":
        raise ValidationError("unsupported novelty method")
    if not isinstance(novelty["claimed"], bool):
        raise ValidationError("novelty.claimed must be boolean")


def validate_corpus(value: dict[str, Any]) -> list[dict[str, Any]]:
    if set(value) != {"schema", "corpus_id", "claims"}:
        raise ValidationError("corpus must contain exactly schema, corpus_id and claims")
    if value["schema"] != CORPUS_SCHEMA or not isinstance(value["corpus_id"], str):
        raise ValidationError("unsupported corpus")
    claims = require_list(value, "claims")
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValidationError("every corpus claim must be an object")
        validate_claim_shape(claim)
    return claims


def formal_receipt_ok(proof: Any) -> bool:
    if not isinstance(proof, dict):
        return False
    required = {"kind", "kernel_status", "compiler", "theorem",
                "source_sha256", "receipt_sha256", "axioms"}
    return (
        set(proof) == required
        and proof["kind"] == "LEAN_KERNEL_RECEIPT"
        and proof["kernel_status"] == "VERIFIED"
        and proof["compiler"] == "Lean 4.19.0"
        and isinstance(proof["theorem"], str) and bool(proof["theorem"])
        and isinstance(proof["source_sha256"], str) and bool(SHA256.fullmatch(proof["source_sha256"]))
        and isinstance(proof["receipt_sha256"], str) and bool(SHA256.fullmatch(proof["receipt_sha256"]))
        and isinstance(proof["axioms"], list)
        and all(isinstance(item, str) for item in proof["axioms"])
    )


def observation_ok(item: Any) -> bool:
    required = {"kind", "source_sha256", "method", "uncertainty",
                "calibration", "provenance"}
    return (
        isinstance(item, dict)
        and set(item) == required
        and item["kind"] == "OBSERVATION"
        and isinstance(item["source_sha256"], str)
        and bool(SHA256.fullmatch(item["source_sha256"]))
        and all(isinstance(item[key], str) and item[key].strip()
                for key in ("method", "uncertainty", "calibration", "provenance"))
    )


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"check": name, "passed": passed, "detail": detail}


def evaluate(claim: dict[str, Any], corpus_value: dict[str, Any]) -> dict[str, Any]:
    validate_claim_shape(claim)
    corpus = validate_corpus(corpus_value)
    ids: dict[str, list[dict[str, Any]]] = {}
    for item in corpus:
        ids.setdefault(item["claim_id"], []).append(item)

    classification = claim["classification"]
    checks: list[dict[str, Any]] = []
    checks.append(check("classification_status", True, "exact policy mapping"))

    formal = classification == "FORMAL_PROVED"
    formal_ok = bool(claim["proofs"]) and all(formal_receipt_ok(item) for item in claim["proofs"])
    checks.append(check(
        "formal_kernel_receipt",
        formal_ok if formal else not claim["proofs"],
        "required only for FORMAL_PROVED; prohibited as promotion evidence for non-formal classes",
    ))

    empirical = classification == "EMPIRICALLY_EVIDENCED"
    empirical_ok = bool(claim["evidence"]) and all(observation_ok(item) for item in claim["evidence"])
    checks.append(check(
        "empirical_observation_envelope",
        empirical_ok if empirical else True,
        "calibration, method, provenance, source identity and uncertainty required",
    ))

    source_ok = bool(claim["sources"])
    checks.append(check(
        "source_binding",
        source_ok if classification == "SOURCE_BOUND" else True,
        "SOURCE_BOUND requires at least one attributable source object",
    ))

    missing_dependencies = sorted(item for item in claim["dependencies"] if len(ids.get(item, [])) != 1)
    checks.append(check(
        "dependency_closure",
        not missing_dependencies,
        "each dependency must resolve to exactly one corpus object",
    ))

    target_digest = statement_sha256(claim["statement"])
    corpus_digests = {statement_sha256(item["statement"]) for item in corpus}
    corpus_relative_novel = target_digest not in corpus_digests
    novelty_consistent = claim["novelty"]["claimed"] == corpus_relative_novel
    checks.append(check(
        "corpus_relative_syntactic_novelty",
        novelty_consistent,
        "exact canonical statement comparison only; no semantic or global novelty claim",
    ))

    conflicts = sorted(item for item in claim["negates"] if item in ids)
    duplicate_id = claim["claim_id"] in ids
    checks.append(check(
        "identifier_uniqueness",
        not duplicate_id,
        "an existing identifier requires a separately versioned claim identifier",
    ))

    failed = sorted(item["check"] for item in checks if not item["passed"])
    if conflicts:
        decision = "CONTESTED_PRESERVE_BOTH"
    elif failed:
        decision = "HOLD_OPEN"
    else:
        decision = "ADMIT_AS_CLASSIFIED"

    return {
        "schema": REPORT_SCHEMA,
        "claim_id": claim["claim_id"],
        "claim_sha256": digest(claim),
        "canonical_statement_sha256": target_digest,
        "corpus_sha256": digest(corpus_value),
        "decision": decision,
        "classification_retained": classification,
        "checks": checks,
        "failed_checks": failed,
        "explicit_conflicts": conflicts,
        "corpus_relative_syntactic_novel": corpus_relative_novel,
        "global_scientific_novelty_established": False,
        "universal_truth_established": False,
        "answer_to_every_question_established": False,
        "effect_ack": "EFFECT_ACK_CONTINUE",
        "ordinary_release": False,
        "publication_authorized": False,
    }


def merge_corpora(left_value: dict[str, Any], right_value: dict[str, Any]) -> dict[str, Any]:
    left = validate_corpus(left_value)
    right = validate_corpus(right_value)
    objects: dict[str, dict[str, Any]] = {}
    for claim in left + right:
        objects[digest(claim)] = claim
    ordered = [objects[key] for key in sorted(objects)]
    by_id: dict[str, set[str]] = {}
    for key, claim in objects.items():
        by_id.setdefault(claim["claim_id"], set()).add(key)
    conflicts = [
        {"claim_id": key, "object_sha256": sorted(values)}
        for key, values in sorted(by_id.items()) if len(values) > 1
    ]
    return {
        "schema": MERGE_SCHEMA,
        "merge_operation": "CONTENT_OBJECT_SET_UNION",
        "claims": ordered,
        "claim_count": len(ordered),
        "identifier_conflicts": conflicts,
        "conflicts_preserved": True,
        "effect_ack": "EFFECT_ACK_CONTINUE",
        "ordinary_release": False,
        "publication_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--claim", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--corpus", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--output", type=pathlib.Path, required=True)
    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument("--left", type=pathlib.Path, required=True)
    merge_parser.add_argument("--right", type=pathlib.Path, required=True)
    merge_parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            result = evaluate(read_json(args.claim), read_json(args.corpus))
        else:
            result = merge_corpora(read_json(args.left), read_json(args.right))
        write_json(args.output, result)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        return 1
    print(f"PASS: wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
