# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

# Workflow executor / mesh-node continuity acceptance

## Purpose

This acceptance is the repository-native connection order for every future
mesh node added through `registry/node_request_queue/*.tsv`.  It moves the
workflow executor from chat-only transport into an exact-head-bound repository
controller and preserves the same boundaries at the node edge.

## Required order

1. Bind the node to the Authority contract at
   `state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json`.
2. Materialize, in the new node, the receipt at
   `state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json` from:

   ```sh
   python3 -B tools/qikvrt_workflow_executor.py node-receipt-template \
     --node-repository OWNER/REPOSITORY --node-branch BRANCH --json
   ```

3. Run the structural node receipt check:

   ```sh
   python3 -B tools/qikvrt_workflow_executor.py validate-node-receipt \
     --receipt state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json \
     --node-repository OWNER/REPOSITORY --node-branch BRANCH --json
   ```

4. Add the node only through the declared queue.  Its registration request
   must contain the `workflow_executor_continuity` declaration, whose receipt
   URL is bound to its repository and branch.  Seed acceptance fetches and
   validates that receipt before it accepts the queue row.
5. Let the repository watchdog observe the exact head.  The resulting artifact
   is evidence of this bounded run, not a global completion claim.

## Automated coverage

`tests/test_qikvrt_workflow_executor_mesh_contract.py` verifies the exact
contract, executor bindings, dynamic workflow-inventory delta, safe dispatch
envelope, receipt validation, and watcher boundaries.

`tests/test_seed_workflows.py` proves that a future queue node without the
continuity declaration is blocked and that an exact, structurally valid receipt
is required before Seed acceptance.

The `workflow-executor-mesh-contract` Make target runs both tests and an
exact-head snapshot.  The watchdog runs them again on a candidate pull request
and after the Authority executor dispatches its authorised no-effect watchdog.

## Boundary

The controller plans a dispatch only for an allowlisted workflow on a freshly
reobserved `main` head and tree, with no competing writer and no equivalent
exact-head run.  It does not mutate repository content, merge a pull request,
rerun a deterministic failure, assert a gate merely because a watchdog ended,
or cause a release, deployment, Zenodo/DOI/IETF action, publication, or other
external effect.  `action_required` and zero-job runs are not trusted execution
evidence.
