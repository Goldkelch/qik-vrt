<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# Transactional GitHub workflow trigger protocol

Canonical failure class: `NON_ATOMIC_MULTI_COMMIT_WORKFLOW_TRIGGER_ORDERING_RACE`.

Repository transactions are assembled as payload writes, exact manifest/hash binding, and one final JSON ready-marker write. Workflows watch only the ready marker and invoke `tools/qikvrt_transactional_workflow_trigger.py verify` before any effect. Missing or malformed markers, missing or unexpected changed paths, absent files, hash divergence and false completion claims block execution.

A verified trigger proves only transaction completeness. It does not prove task completion, merge, publication, Authority/Mirror equality, `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE`.
