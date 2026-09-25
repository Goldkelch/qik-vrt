#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed QIK-VRT epistemic output contract.

Every conforming repository/Mesh node output carries exact bindings to the
canonical proof-and-thought article and to the ontological-origin proof:
"Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts."

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
ORIGIN_PROOF_PATH = ROOT / "docs/ONTOLOGICAL_ORIGIN_OF_DIFFERENCE_DE.md"
KNOWLEDGE_MANIFEST_PATH = (
    ROOT / "state/mesh/QIKVRT_REQUIRED_KNOWLEDGE_ARTIFACTS_20260925_V1.json"
)

BINDING_KEY = "_qikvrt_epistemic_output"
BINDING_SCHEMA = "qikvrt_epistemic_output_binding_v1"
POLICY_ID = "QIKVRT-UNIVERSAL-PROOF-THOUGHT-SCHEMA-V1"
ARTICLE_GIT_BLOB_SHA1 = "339ad05606ee4d74185c72d006608cff7aea5f37"
ORIGIN_PROOF_GIT_BLOB_SHA1 = "d128c6fecf672abfd0fee1d1ef3cfa5dcf20fb33"
KNOWLEDGE_MANIFEST_GIT_BLOB_SHA1 = "302a0ac6741bcd6665a2551052269e693808be65"
ORIGIN_STATEMENT = (
    "Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts."
)
ORIGIN_PROOF_CONSTANTS = (
    "QIKVRT.UniversalOntology.determinateReality_requires_difference",
    "QIKVRT.UniversalOntology.noDifference_excludes_determinateReality",
    "QIKVRT.UniversalOntology.noDifference_excludes_information",
)

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


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _bound_file_identity(path: pathlib.Path, expected_blob: str) -> dict[str, Any]:
    raw = path.read_bytes()
    observed = _git_blob_sha1(raw)
    if observed != expected_blob:
        raise OutputContractError(
            f"canonical file git blob mismatch for {path.name}: "
            f"{observed} != {expected_blob}"
        )
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "git_blob_sha1": observed,
    }


def canonical_article_identity() -> dict[str, Any]:
    return _bound_file_identity(ARTICLE_PATH, ARTICLE_GIT_BLOB_SHA1)


def canonical_origin_proof_identity() -> dict[str, Any]:
    identity = _bound_file_identity(
        ORIGIN_PROOF_PATH, ORIGIN_PROOF_GIT_BLOB_SHA1
    )
    return {
        **identity,
        "statement": ORIGIN_STATEMENT,
        "proof_constants": list(ORIGIN_PROOF_CONSTANTS),
        "interpretation": "ONTOLOGICAL_PRIORITY_NOT_FIRST_PHYSICAL_TIME",
    }


def canonical_knowledge_artifacts_identity() -> dict[str, Any]:
    identity = _bound_file_identity(
        KNOWLEDGE_MANIFEST_PATH, KNOWLEDGE_MANIFEST_GIT_BLOB_SHA1
    )
    value = json.loads(KNOWLEDGE_MANIFEST_PATH.read_text(encoding="utf-8"))
    if value.get("manifest_id") != "QIKVRT-REQUIRED-KNOWLEDGE-ARTIFACTS-20260925-V1":
        raise OutputContractError("required knowledge manifest id mismatch")
    if value.get("mandatory_for_current_and_future_repository_nodes") is not True:
        raise OutputContractError("required knowledge artifacts are not mandatory")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 3:
        raise OutputContractError("required knowledge artifact count mismatch")
    for item in artifacts:
        path_text = item.get("path")
        if not isinstance(path_text, str):
            raise OutputContractError("required knowledge artifact path missing")
        artifact_path = ROOT / path_text
        if not artifact_path.is_file():
            raise OutputContractError(f"required knowledge artifact missing: {path_text}")
        raw = artifact_path.read_bytes()
        if len(raw) != item.get("bytes"):
            raise OutputContractError(f"required knowledge artifact byte mismatch: {path_text}")
        if hashlib.sha256(raw).hexdigest() != item.get("sha256"):
            raise OutputContractError(f"required knowledge artifact sha256 mismatch: {path_text}")
        if _git_blob_sha1(raw) != item.get("git_blob_sha1"):
            raise OutputContractError(f"required knowledge artifact git blob mismatch: {path_text}")
        if path_text.endswith(".pdf"):
            if not raw.startswith(b"%PDF-1.4") or not raw.rstrip().endswith(b"%%EOF"):
                raise OutputContractError("required scientific PDF structure invalid")
    return {
        **identity,
        "manifest_id": value["manifest_id"],
        "artifact_ids": [item["id"] for item in artifacts],
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
    for key, expected in canonical_article_identity().items():
        if article.get(key) != expected:
            raise OutputContractError(
                f"policy canonical article {key} mismatch"
            )

    proof = value.get("ontological_origin_proof")
    if not isinstance(proof, dict):
        raise OutputContractError("policy ontological-origin proof missing")
    expected_proof = canonical_origin_proof_identity()
    if proof.get("document_path") != expected_proof["path"]:
        raise OutputContractError("origin proof document path mismatch")
    if proof.get("document_git_blob_sha1") != expected_proof["git_blob_sha1"]:
        raise OutputContractError("origin proof document blob mismatch")
    if proof.get("statement") != ORIGIN_STATEMENT:
        raise OutputContractError("origin proof statement mismatch")
    if proof.get("proof_constants") != list(ORIGIN_PROOF_CONSTANTS):
        raise OutputContractError("origin proof constants mismatch")
    if proof.get("mandatory_for_every_node") is not True:
        raise OutputContractError("origin proof is not mandatory for every node")
    if proof.get("mandatory_for_every_node_output") is not True:
        raise OutputContractError(
            "origin proof is not mandatory for every node output"
        )
    required = value.get("required_knowledge_artifacts")
    if not isinstance(required, dict):
        raise OutputContractError("required knowledge artifact binding missing")
    expected_knowledge = canonical_knowledge_artifacts_identity()
    if required.get("manifest_path") != expected_knowledge["path"]:
        raise OutputContractError("required knowledge manifest path mismatch")
    if required.get("manifest_git_blob_sha1") != expected_knowledge["git_blob_sha1"]:
        raise OutputContractError("required knowledge manifest blob mismatch")
    if required.get("mandatory_for_every_node") is not True:
        raise OutputContractError("required knowledge is not mandatory for every node")
    if required.get("mandatory_for_every_node_output") is not True:
        raise OutputContractError("required knowledge is not mandatory for every output")
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
        raise OutputContractError(
            f"unknown epistemic state: {epistemic_state}"
        )
    if effect_state not in EFFECT_STATES:
        raise OutputContractError(f"unknown effect state: {effect_state}")
    if effect_ack_done and effect_state != "DONE_WITHIN_DECLARED_SCOPE":
        raise OutputContractError(
            "effect_ack_done requires scoped DONE state"
        )
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
        "article_binding": canonical_article_identity(),
        "ontological_origin_proof_binding": (
            canonical_origin_proof_identity()
        ),
        "knowledge_artifacts_binding": (
            canonical_knowledge_artifacts_identity()
        ),
    }


def bind_output(
    value: Mapping[str, Any], **binding_kwargs: Any
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    result = copy.deepcopy(dict(value))
    if BINDING_KEY in result:
        validate_output(result)
        return result
    result[BINDING_KEY] = make_binding(**binding_kwargs)
    validate_output(result)
    return result


def strip_output_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return the domain payload without its additive epistemic binding."""
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    result = copy.deepcopy(dict(value))
    result.pop(BINDING_KEY, None)
    return result


def validate_output(value: Mapping[str, Any]) -> dict[str, Any]:
    load_policy()
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    binding = value.get(BINDING_KEY)
    if not isinstance(binding, Mapping):
        raise OutputContractError(
            "mandatory epistemic output binding missing"
        )
    if binding.get("schema") != BINDING_SCHEMA:
        raise OutputContractError("output binding schema mismatch")
    if binding.get("policy_id") != POLICY_ID:
        raise OutputContractError("output policy binding mismatch")
    if binding.get("article_binding") != canonical_article_identity():
        raise OutputContractError(
            "output canonical article binding mismatch"
        )
    if (
        binding.get("ontological_origin_proof_binding")
        != canonical_origin_proof_identity()
    ):
        raise OutputContractError(
            "output ontological-origin proof binding mismatch"
        )

    if (
        binding.get("knowledge_artifacts_binding")
        != canonical_knowledge_artifacts_identity()
    ):
        raise OutputContractError(
            "output required-knowledge artifact binding mismatch"
        )

    claim = binding.get("claim")
    if (
        not isinstance(claim, Mapping)
        or claim.get("kind") not in CLAIM_KINDS
    ):
        raise OutputContractError("output claim kind missing or invalid")
    scope = binding.get("scope")
    if not isinstance(scope, Mapping):
        raise OutputContractError("output scope missing")
    if scope.get("predecessor_evidence_transfer") is not False:
        raise OutputContractError(
            "predecessor evidence transfer must be false"
        )
    for key in (
        "assumptions",
        "definitions",
        "dependencies",
        "exclusions",
    ):
        if not isinstance(scope.get(key), list):
            raise OutputContractError(f"scope.{key} must be a list")

    epistemic_state = binding.get("epistemic_status")
    if epistemic_state not in EPISTEMIC_STATES:
        raise OutputContractError("invalid epistemic status")
    effect = binding.get("effect_status")
    if (
        not isinstance(effect, Mapping)
        or effect.get("state") not in EFFECT_STATES
    ):
        raise OutputContractError("invalid effect status")
    if effect.get("transport_ack_is_effect_ack") is not False:
        raise OutputContractError(
            "TRANSPORT_ACK must remain distinct from EFFECT_ACK"
        )
    done = effect.get("effect_ack_done")
    if (
        done is True
        and effect.get("state") != "DONE_WITHIN_DECLARED_SCOPE"
    ):
        raise OutputContractError(
            "unscoped effect_ack_done is forbidden"
        )
    if (
        effect.get("state") == "DONE_WITHIN_DECLARED_SCOPE"
        and done is not True
    ):
        raise OutputContractError(
            "DONE_WITHIN_DECLARED_SCOPE requires effect_ack_done"
        )
    if (
        not isinstance(binding.get("new_difference"), str)
        or not binding["new_difference"]
    ):
        raise OutputContractError("new_difference must be explicit")
    return copy.deepcopy(dict(value))


def validate_json_file(path: pathlib.Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_output(value)


def main() -> int:
    load_policy()
    print(
        json.dumps(
            {
                "schema": "qikvrt_output_contract_selfcheck_v1",
                "policy_id": POLICY_ID,
                "article": canonical_article_identity(),
                "ontological_origin_proof": (
                    canonical_origin_proof_identity()
                ),
                "required_knowledge_artifacts": (
                    canonical_knowledge_artifacts_identity()
                ),
                "status": "PASS",
                "effect_ack_done": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
