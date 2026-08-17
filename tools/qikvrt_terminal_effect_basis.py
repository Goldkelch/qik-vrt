#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed evaluator for the QIK-VRT terminal effect evidence basis."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPOSITORY = "Goldkelch/qik-vrt"
SCHEMA = "qikvrt_terminal_effect_basis_evaluation_v1"
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TRUSTED_MATERIALIZATION = {"REPOSITORY_NATIVE", "TREE_IDENTICAL_TRUSTED_CARRIER"}
KINDS = ("publication", "release", "deployment")
COMPLETION_CLAIMS = {
    "MERGE_DONE": False,
    "PUBLICATION_DONE": False,
    "RELEASE_DONE": False,
    "DEPLOYMENT_DONE": False,
    "PASS": False,
    "FINAL_PASS": False,
    "EFFECT_ACK_DONE": False,
}


def obj(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def sha1(value: Any) -> bool:
    return isinstance(value, str) and SHA1.fullmatch(value) is not None


def sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def exact_gates(value: Any, head: Any, tree: Any) -> tuple[bool, list[str]]:
    gates = value if isinstance(value, list) else []
    applicable = [g for g in gates if isinstance(g, Mapping) and g.get("applicable") is True]
    blockers: list[str] = []
    if not applicable:
        return False, ["no applicable exact-head workflow evidence"]
    for gate in applicable:
        name = gate.get("name") if text(gate.get("name")) else "unnamed gate"
        if gate.get("head_sha") != head:
            blockers.append(f"{name}: head mismatch")
        if gate.get("tree_sha") != tree:
            blockers.append(f"{name}: tree mismatch")
        if gate.get("status") != "completed":
            blockers.append(f"{name}: nonterminal")
        if gate.get("conclusion") != "success":
            blockers.append(f"{name}: conclusion is not success")
        jobs = gate.get("job_count")
        if not isinstance(jobs, int) or isinstance(jobs, bool) or jobs <= 0:
            blockers.append(f"{name}: zero-job or unavailable job evidence")
    return not blockers, list(dict.fromkeys(blockers))


def authorization(
    value: Any,
    *,
    repository: Any,
    head: Any,
    tree: Any,
    scope: Any,
    artifact: Any | None = None,
) -> bool:
    auth = obj(value)
    return (
        auth.get("authorized") is True
        and auth.get("repository") == repository
        and auth.get("candidate_head") == head
        and auth.get("candidate_tree") == tree
        and auth.get("scope_sha256") == scope
        and sha256(auth.get("authorization_sha256"))
        and auth.get("force") is False
        and (artifact is None or auth.get("artifact_sha256") == artifact)
    )


def artifact(value: Any, kind: str) -> bool:
    item = obj(value)
    if not sha256(item.get("artifact_sha256")):
        return False
    if kind == "publication":
        return (
            sha256(item.get("metadata_sha256"))
            and item.get("rights_cleared") is True
            and item.get("scientific_status_bound") is True
        )
    if kind == "release":
        return (
            text(item.get("version"))
            and sha256(item.get("sbom_sha256"))
            and sha256(item.get("provenance_sha256"))
        )
    return text(item.get("environment")) and sha256(item.get("rollback_plan_sha256"))


def effect_receipt(
    value: Any,
    *,
    basis: bool,
    head: Any,
    tree: Any,
    artifact_sha: Any,
    auth_sha: Any,
) -> bool:
    receipt = obj(value)
    return (
        basis
        and receipt.get("verified") is True
        and receipt.get("request_head") == head
        and receipt.get("request_tree") == tree
        and receipt.get("artifact_sha256") == artifact_sha
        and receipt.get("authorization_sha256") == auth_sha
        and text(receipt.get("effect_id"))
        and text(receipt.get("target"))
        and sha256(receipt.get("receipt_sha256"))
        and receipt.get("effect_ack") is True
        and receipt.get("live_readback") is True
    )


def evaluate(evidence: Mapping[str, Any]) -> dict[str, Any]:
    repository = evidence.get("repository")
    binding = obj(evidence.get("binding"))
    head, tree = binding.get("candidate_head"), binding.get("candidate_tree")
    scope = binding.get("scope_sha256")

    binding_ok = (
        repository == REPOSITORY
        and all(
            sha1(binding.get(key))
            for key in (
                "authority_head",
                "authority_tree",
                "base_head",
                "base_tree",
                "candidate_head",
                "candidate_tree",
            )
        )
        and sha256(scope)
    )
    integrity = obj(evidence.get("integrity"))
    integrity_ok = (
        integrity.get("verified") is True
        and integrity.get("head_sha") == head
        and integrity.get("tree_sha") == tree
        and integrity.get("materialization_state") in TRUSTED_MATERIALIZATION
        and integrity.get("scope_clear") is True
        and integrity.get("provenance_clear") is True
    )
    gates_ok, gate_blockers = exact_gates(evidence.get("gates"), head, tree)
    writer = obj(evidence.get("writer"))
    writer_ok = writer.get("competing") is False and writer.get("lease_clear") is True
    pass_basis = binding_ok and integrity_ok and gates_ok and writer_ok
    pass_blockers = []
    if not binding_ok:
        pass_blockers.append("exact binding invalid")
    if not integrity_ok:
        pass_blockers.append("integrity, materialization, scope, or provenance not clear")
    pass_blockers.extend(gate_blockers)
    if not writer_ok:
        pass_blockers.append("writer or lease state not clear")

    review = obj(evidence.get("review"))
    review_ok = (
        review.get("mergeable") is True
        and review.get("draft") is False
        and review.get("ruleset_satisfied") is True
        and review.get("required_reviews_satisfied") is True
    )
    auths, artifacts = obj(evidence.get("authorizations")), obj(evidence.get("artifacts"))
    merge_auth = authorization(
        auths.get("merge"), repository=repository, head=head, tree=tree, scope=scope
    )
    merge_basis = pass_basis and review_ok and merge_auth

    bases: dict[str, bool] = {}
    for kind in KINDS:
        digest = obj(artifacts.get(kind)).get("artifact_sha256")
        bases[kind] = (
            pass_basis
            and artifact(artifacts.get(kind), kind)
            and authorization(
                auths.get(kind),
                repository=repository,
                head=head,
                tree=tree,
                scope=scope,
                artifact=digest,
            )
        )
    release_digest = obj(artifacts.get("release")).get("artifact_sha256")
    deploy_digest = obj(artifacts.get("deployment")).get("artifact_sha256")
    bases["deployment"] = bases["deployment"] and bases["release"] and deploy_digest == release_digest

    receipts = obj(evidence.get("receipts"))
    merge_receipt = obj(receipts.get("merge"))
    merge_receipt_ok = (
        merge_receipt.get("verified") is True
        and merge_receipt.get("candidate_head") == head
        and merge_receipt.get("candidate_tree") == tree
        and sha1(merge_receipt.get("result_head"))
        and sha1(merge_receipt.get("result_tree"))
        and sha256(merge_receipt.get("receipt_sha256"))
        and merge_receipt.get("live_readback") is True
    )
    effect_receipts: dict[str, bool] = {}
    for kind in KINDS:
        effect_receipts[kind] = effect_receipt(
            receipts.get(kind),
            basis=bases[kind],
            head=head,
            tree=tree,
            artifact_sha=obj(artifacts.get(kind)).get("artifact_sha256"),
            auth_sha=obj(auths.get(kind)).get("authorization_sha256"),
        )

    result_head = merge_receipt.get("result_head")
    result_tree = merge_receipt.get("result_tree")
    post = obj(evidence.get("post_promotion"))
    post_gates_ok, _ = exact_gates(post.get("gates"), result_head, result_tree)
    post_ok = (
        post.get("verified") is True
        and post.get("authority_head") == result_head
        and post.get("authority_tree") == result_tree
        and post.get("integrity_verified") is True
        and post_gates_ok
    )
    final_basis = (
        merge_basis
        and all(bases.values())
        and merge_receipt_ok
        and all(effect_receipts.values())
        and post_ok
    )

    effect_ids = sorted(
        obj(receipts.get(kind)).get("effect_id")
        for kind in KINDS
        if text(obj(receipts.get(kind)).get("effect_id"))
    )
    closure = obj(receipts.get("closure"))
    closure_ok = (
        evidence.get("pending_required_effects") == 0
        and not isinstance(evidence.get("pending_required_effects"), bool)
        and closure.get("verified") is True
        and closure.get("authority_head") == result_head
        and closure.get("authority_tree") == result_tree
        and closure.get("required_effect_ids") == effect_ids
        and sha256(closure.get("receipt_sha256"))
        and closure.get("live_readback") is True
    )
    effect_ack_basis = final_basis and closure_ok

    readiness = {
        "PASS_basis_ready": pass_basis,
        "merge_basis_ready": merge_basis,
        "publication_basis_ready": bases["publication"],
        "release_basis_ready": bases["release"],
        "deployment_basis_ready": bases["deployment"],
        "FINAL_PASS_basis_ready": final_basis,
        "EFFECT_ACK_DONE_basis_ready": effect_ack_basis,
    }
    blockers = {
        "PASS_basis_ready": pass_blockers,
        "merge_basis_ready": [] if merge_basis else pass_blockers + ["review/ruleset or merge authorization missing"],
        "publication_basis_ready": [] if bases["publication"] else pass_blockers + ["publication artifact or authorization missing"],
        "release_basis_ready": [] if bases["release"] else pass_blockers + ["release artifact or authorization missing"],
        "deployment_basis_ready": [] if bases["deployment"] else pass_blockers + ["deployment/release artifact or authorization missing"],
        "FINAL_PASS_basis_ready": [] if final_basis else ["merge/effect receipt or post-promotion evidence missing"],
        "EFFECT_ACK_DONE_basis_ready": [] if effect_ack_basis else ["final basis or exact closure receipt missing"],
    }
    return {
        "schema": SCHEMA,
        "repository": repository,
        "binding": dict(binding),
        "classification": "ALL_BASES_READY" if all(readiness.values()) else "HOLD_MISSING_EVIDENCE",
        "readiness": readiness,
        "blockers": blockers,
        "completion_claims": dict(COMPLETION_CLAIMS),
        "semantic_boundaries": {
            "basis_ready_is_completion": False,
            "transport_ack_is_effect_ack": False,
            "workflow_success_is_external_effect": False,
            "gate_transfer_between_heads": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("evaluate")
    command.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.evidence.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("evidence root must be a JSON object")
        result = evaluate(value)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
