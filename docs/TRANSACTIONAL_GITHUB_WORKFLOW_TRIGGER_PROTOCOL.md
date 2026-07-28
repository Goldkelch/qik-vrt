<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Transactional GitHub workflow trigger protocol

## Problem class

GitHub Contents API writes are individual commits. A workflow that watches its own workflow file can therefore start before the remaining payload, tests, work unit, or bindings exist. Later commits may not retrigger the workflow when their paths are outside the workflow filter. Activity is then visible, but the intended technical effect is stalled.

Canonical failure class:

`NON_ATOMIC_MULTI_COMMIT_WORKFLOW_TRIGGER_ORDERING_RACE`

## Required architecture

A repository transaction is assembled in three phases:

1. **Payload phase** — create or update implementation, tests, documentation, work units, and the transaction manifest. No execution workflow may be triggered by these writes.
2. **Binding phase** — the manifest declares the exact base commit, allowed and required changed paths, SHA-256 bindings for every execution-critical file, the final marker path, and false global completion claims.
3. **Commit phase** — create the final JSON ready marker as the last repository write. The workflow watches only this marker path.

The workflow must invoke `tools/qikvrt_transactional_workflow_trigger.py verify` before any external read, write, artifact import, branch mutation, or effect execution.

## Fail-closed conditions

Execution is blocked when the marker is absent or malformed, the transaction identifier differs, a required file is absent, a SHA-256 binding differs, a required changed path is missing, an unexpected path is present, or the trigger manifest asserts `pass`, `final_pass`, or `effect_ack_done`.

## Test obligation

Every consumer must retain positive and negative tests for at least:

- missing ready marker;
- malformed or mismatched marker;
- missing required changed path;
- unexpected changed path;
- missing required file;
- required-file hash mismatch;
- false completion claim;
- valid complete transaction.

## Effect boundary

A verified trigger proves only that the declared repository transaction is complete and bound. It does not prove the task result, merge, publication, Authority/Mirror equality, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
