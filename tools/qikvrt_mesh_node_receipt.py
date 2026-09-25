#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build and validate proof-bound future Mesh-node continuity receipts."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_workflow_executor as workflow_executor  # noqa: E402
from tools.qikvrt_output_contract import (  # noqa: E402
    BINDING_KEY,
    OutputContractError,
    bind_output,
    validate_output,
)


class NodeReceiptContractError(ValueError):
    """A future-node receipt is not admissible under the universal schema."""


def build_bound_node_receipt(
    node_repository: str,
    node_branch: str,
    root: pathlib.Path = ROOT,
) -> dict[str, Any]:
    payload = workflow_executor.build_node_receipt(node_repository, node_branch, root)
    authority = payload["authority"]
    return bind_output(
        payload,
        node_id=f"workflow-executor-continuity:{node_repository}",
        repository=node_repository,
        subject={
            "node_repository": node_repository,
            "node_branch": node_branch,
            "contract_sha256": authority["contract_sha256"],
            "head_sha": authority["head_sha"],
            "tree_sha": authority["tree_sha"],
        },
        claim_kind="SOURCE_BOUND",
        statement=(
            "Future Mesh-node continuity receipt bound to the exact repository "
            "subject, acceptance contract and universal proof-and-thought schema."
        ),
        assumptions=[],
        definitions=["QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY"],
        dependencies=[],
        exclusions=[
            "execution evidence",
            "merge",
            "deployment",
            "external effect",
            "general EFFECT_ACK_DONE",
        ],
        evidence_refs=[authority["contract_sha256"]],
        epistemic_state="RUNTIME_EVIDENCE",
        effect_state="NONE",
        transport_ack=False,
        effect_ack_done=False,
        new_difference="NODE_CONTINUITY_RECEIPT_MATERIALIZED",
    )


def validate_bound_node_receipt(
    receipt: Mapping[str, Any],
    node_repository: str,
    node_branch: str,
    root: pathlib.Path = ROOT,
) -> dict[str, Any]:
    try:
        validate_output(receipt)
    except OutputContractError as exc:
        raise NodeReceiptContractError(
            f"universal proof/thought binding invalid: {exc}"
        ) from exc

    binding = receipt.get(BINDING_KEY)
    if not isinstance(binding, Mapping):
        raise NodeReceiptContractError("universal proof/thought binding missing")
    node = binding.get("node")
    if not isinstance(node, Mapping) or node.get("repository") != node_repository:
        raise NodeReceiptContractError(
            "universal proof/thought binding targets another repository"
        )
    subject = binding.get("subject")
    if not isinstance(subject, Mapping):
        raise NodeReceiptContractError("bound subject missing")
    if subject.get("node_repository") != node_repository:
        raise NodeReceiptContractError("bound subject repository mismatch")
    if subject.get("node_branch") != node_branch:
        raise NodeReceiptContractError("bound subject branch mismatch")

    structural = workflow_executor.validate_node_receipt(
        receipt, node_repository, node_branch, root
    )
    return bind_output(
        structural,
        node_id=f"workflow-executor-continuity-validator:{node_repository}",
        repository=node_repository,
        subject={
            "node_repository": node_repository,
            "node_branch": node_branch,
            "receipt_policy_id": binding.get("policy_id"),
            "receipt_article_sha256": binding.get("article_binding", {}).get("sha256"),
        },
        claim_kind="SOURCE_BOUND",
        statement=(
            "Future Mesh-node continuity receipt passed structural and universal "
            "proof/thought binding validation."
        ),
        assumptions=[],
        definitions=["QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY"],
        dependencies=[],
        exclusions=["execution evidence", "external effect", "general EFFECT_ACK_DONE"],
        evidence_refs=[],
        epistemic_state="RUNTIME_EVIDENCE",
        effect_state="NONE",
        transport_ack=False,
        effect_ack_done=False,
        new_difference="NODE_CONTINUITY_RECEIPT_VALIDATED",
    )


def _load(path: pathlib.Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise NodeReceiptContractError("receipt must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--node-repository", required=True)
    build.add_argument("--node-branch", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--receipt", type=pathlib.Path, required=True)
    check.add_argument("--node-repository", required=True)
    check.add_argument("--node-branch", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            value = build_bound_node_receipt(args.node_repository, args.node_branch)
        else:
            value = validate_bound_node_receipt(
                _load(args.receipt), args.node_repository, args.node_branch
            )
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        workflow_executor.ExecutorBlock,
        NodeReceiptContractError,
    ) as exc:
        print(f"BLOCK MESH_NODE_RECEIPT {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
