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
2. Bind the node to the canonical proof-and-thought policy, article and output
   carrier registry, then materialize the node receipt through the mandatory
   fail-closed wrapper:

   ```sh
   python3 -B tools/qikvrt_mesh_node_receipt.py build \
     --node-repository OWNER/REPOSITORY --node-branch BRANCH \
     > state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json
   ```

3. Run the combined structural and proof/thought binding check:

   ```sh
   python3 -B tools/qikvrt_mesh_node_receipt.py validate \
     --receipt state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json \
     --node-repository OWNER/REPOSITORY --node-branch BRANCH
   ```

   The underlying workflow-executor payload remains unchanged; the wrapper adds
   and validates the reserved `_qikvrt_epistemic_output` binding. An unbound
   legacy receipt is not admissible for a newly accepted Mesh node.

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
continuity declaration is blocked and that an exact, structurally valid,
canonically article-bound receipt is required before Seed acceptance.

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
