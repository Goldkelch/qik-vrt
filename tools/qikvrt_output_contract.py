#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed QIK-VRT epistemic output contract.

Every conforming repository/Mesh node output carries a binding to the canonical
article plus explicit subject, scope, epistemic-status and effect boundaries.
The binding is additive: domain payload schemas remain intact.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy/QIKVRT_UNIVERSAL_PROOF_THOUGHT_SCHEMA_V1.json"
ARTICLE_PATH = ROOT / "docs/QIKVRT_UNIVERSAL_PROOF_AND_THOUGHT_SCHEMA_DE.md"

BINDING_KEY = "_qikvrt_epistemic_output"
BINDING_SCHEMA = "qikvrt_epistemic_output_binding_v1"
POLICY_ID = "QIKVRT-UNIVERSAL-PROOF-THOUGHT-SCHEMA-V1"
ARTICLE_SHA256 = "3179af0c1a7c16bf63208a1c91e23213b7746f61f6a0d60ed100728c6064d392"
ARTICLE_BYTES = 21501

CLAIM_KINDS = frozenset({
    "DEFINITION",
    "ASSUMPTION",
    "FORMAL_THEOREM",
    "CORRESPONDENCE_POSTULATE",
    "EMPIRICAL_CLAIM",
    "SOURCE_BOUND",
    "INTERPRETATION",
    "NORMATIVE_RULE",
    "OPEN",
    "OUT_OF_SCOPE",
})

EPISTEMIC_STATES = frozenset({
    "FORMAL",
    "EMPIRICAL",
    "SOURCE_BOUND",
    "INTERPRETIVE",
    "NORMATIVE",
    "OPEN",
    "OUT_OF_SCOPE",
    "RUNTIME_EVIDENCE",
})

EFFECT_STATES = frozenset({
    "NONE",
    "CONTINUE",
    "BLOCK",
    "ISOLATE",
    "DONE_WITHIN_DECLARED_SCOPE",
})


class OutputContractError(ValueError):
    """A fail-closed output-contract violation."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_article_identity() -> dict[str, Any]:
    raw = ARTICLE_PATH.read_bytes()
    observed = _sha256_bytes(raw)
    if len(raw) != ARTICLE_BYTES:
        raise OutputContractError(
            f"canonical article byte length mismatch: {len(raw)} != {ARTICLE_BYTES}"
        )
    if observed != ARTICLE_SHA256:
        raise OutputContractError(
            f"canonical article sha256 mismatch: {observed} != {ARTICLE_SHA256}"
        )
    return {
        "path": ARTICLE_PATH.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": observed,
    }


def load_policy() -> dict[str, Any]:
    value = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt_universal_proof_thought_schema_v1":
        raise OutputContractError("policy schema mismatch")
    if value.get("policy_id") != POLICY_ID:
        raise OutputContractError("policy id mismatch")
    article = value.get("canonical_article")
    if not isinstance(article, dict):
        raise OutputContractError("policy canonical article binding missing")
    identity = canonical_article_identity()
    for key in ("path", "bytes", "sha256"):
        if article.get(key) != identity[key]:
            raise OutputContractError(f"policy canonical article {key} mismatch")
    return value


def make_binding(
    *,
    node_id: str,
    repository: str,
    subject: Mapping[str, Any],
    claim_kind: str,
    statement: str,
    assumptions: list[str] | tuple[str, ...] = (),
    definitions: list[str] | tuple[str, ...] = (),
    dependencies: list[str] | tuple[str, ...] = (),
    exclusions: list[str] | tuple[str, ...] = (),
    evidence_refs: list[str] | tuple[str, ...] = (),
    epistemic_state: str = "RUNTIME_EVIDENCE",
    effect_state: str = "NONE",
    transport_ack: bool = False,
    effect_ack_done: bool = False,
    new_difference: str = "OUTPUT_MATERIALIZED",
) -> dict[str, Any]:
    load_policy()
    if claim_kind not in CLAIM_KINDS:
        raise OutputContractError(f"unknown claim kind: {claim_kind}")
    if epistemic_state not in EPISTEMIC_STATES:
        raise OutputContractError(f"unknown epistemic state: {epistemic_state}")
    if effect_state not in EFFECT_STATES:
        raise OutputContractError(f"unknown effect state: {effect_state}")
    if effect_ack_done and effect_state != "DONE_WITHIN_DECLARED_SCOPE":
        raise OutputContractError("effect_ack_done requires scoped DONE state")
    if effect_state == "DONE_WITHIN_DECLARED_SCOPE" and not effect_ack_done:
        raise OutputContractError("scoped DONE requires effect_ack_done")
    if not isinstance(statement, str) or not statement:
        raise OutputContractError("statement must be non-empty")
    if not isinstance(node_id, str) or not node_id:
        raise OutputContractError("node_id must be non-empty")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise OutputContractError("repository must be owner/name")
    if not isinstance(subject, Mapping) or not subject:
        raise OutputContractError("subject binding must be non-empty")
    article = canonical_article_identity()
    return {
        "schema": BINDING_SCHEMA,
        "policy_id": POLICY_ID,
        "node": {
            "node_id": node_id,
            "repository": repository,
        },
        "subject": copy.deepcopy(dict(subject)),
        "claim": {
            "kind": claim_kind,
            "statement": statement,
        },
        "scope": {
            "assumptions": list(assumptions),
            "definitions": list(definitions),
            "dependencies": list(dependencies),
            "exclusions": list(exclusions),
            "predecessor_evidence_transfer": False,
        },
        "evidence": {
            "refs": list(evidence_refs),
            "cached_output_is_proof_authority": False,
        },
        "epistemic_status": epistemic_state,
        "effect_status": {
            "state": effect_state,
            "transport_ack": bool(transport_ack),
            "effect_ack_done": bool(effect_ack_done),
            "transport_ack_is_effect_ack": False,
        },
        "new_difference": new_difference,
        "article_binding": article,
    }


def bind_output(value: Mapping[str, Any], **binding_kwargs: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    result = copy.deepcopy(dict(value))
    if BINDING_KEY in result:
        raise OutputContractError("node output is already bound")
    result[BINDING_KEY] = make_binding(**binding_kwargs)
    validate_output(result)
    return result


def validate_output(value: Mapping[str, Any]) -> dict[str, Any]:
    load_policy()
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    binding = value.get(BINDING_KEY)
    if not isinstance(binding, Mapping):
        raise OutputContractError("mandatory epistemic output binding missing")
    if binding.get("schema") != BINDING_SCHEMA:
        raise OutputContractError("output binding schema mismatch")
    if binding.get("policy_id") != POLICY_ID:
        raise OutputContractError("output policy binding mismatch")
    article = binding.get("article_binding")
    if article != canonical_article_identity():
        raise OutputContractError("output canonical article binding mismatch")
    claim = binding.get("claim")
    if not isinstance(claim, Mapping) or claim.get("kind") not in CLAIM_KINDS:
        raise OutputContractError("output claim kind missing or invalid")
    scope = binding.get("scope")
    if not isinstance(scope, Mapping):
        raise OutputContractError("output scope missing")
    if scope.get("predecessor_evidence_transfer") is not False:
        raise OutputContractError("predecessor evidence transfer must be false")
    for key in ("assumptions", "definitions", "dependencies", "exclusions"):
        if not isinstance(scope.get(key), list):
            raise OutputContractError(f"scope.{key} must be a list")
    epistemic_state = binding.get("epistemic_status")
    if epistemic_state not in EPISTEMIC_STATES:
        raise OutputContractError("invalid epistemic status")
    effect = binding.get("effect_status")
    if not isinstance(effect, Mapping) or effect.get("state") not in EFFECT_STATES:
        raise OutputContractError("invalid effect status")
    if effect.get("transport_ack_is_effect_ack") is not False:
        raise OutputContractError("TRANSPORT_ACK must remain distinct from EFFECT_ACK")
    done = effect.get("effect_ack_done")
    if done is True and effect.get("state") != "DONE_WITHIN_DECLARED_SCOPE":
        raise OutputContractError("unscoped effect_ack_done is forbidden")
    if effect.get("state") == "DONE_WITHIN_DECLARED_SCOPE" and done is not True:
        raise OutputContractError("DONE_WITHIN_DECLARED_SCOPE requires effect_ack_done")
    if not isinstance(binding.get("new_difference"), str) or not binding["new_difference"]:
        raise OutputContractError("new_difference must be explicit")
    return copy.deepcopy(dict(value))


def validate_json_file(path: pathlib.Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_output(value)


def main() -> int:
    load_policy()
    canonical_article_identity()
    print(
        json.dumps(
            {
                "schema": "qikvrt_output_contract_selfcheck_v1",
                "policy_id": POLICY_ID,
                "article": canonical_article_identity(),
                "status": "PASS",
                "effect_ack_done": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
