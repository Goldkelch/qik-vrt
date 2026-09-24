# QIK-VRT Repository Handover Protocol

Copyright (c) 2026 Ingolf Lohmann.

This document makes operational stewardship transferable without silently transferring intellectual-property rights, commercial rights, credentials, or historical evidence.

## 1. Transfer modes

A handover MUST name its mode explicitly:

- `STEWARDSHIP`: operational maintenance is delegated; ownership/licensing remain unchanged.
- `PERSONAL_SUCCESSION`: repository stewardship is transferred to a named successor under a separate written rights/authority instrument where required.
- `COMMERCIAL`: commercial exploitation requires a separate written commercial agreement from the rights holder, consistent with `LICENSE`, `QIKVRT_LICENSE_AND_RIGHTS.md`, and `COMMERCIAL_USE_POLICY.md`.
- `ARCHIVAL`: custody is transferred for preservation/read-only continuity without operational or commercial authority.

Repository possession, GitHub ownership, a fork, credentials, CI success, or an EFFECT_ACK does not by itself change copyright or license rights.

## 2. Transfer bundle

A transfer candidate MUST bind at minimum:

- exact repository URL, commit SHA, and tree SHA;
- complete license map and third-party notices;
- open PR and non-Main branch disposition ledger;
- current build/test/runtime instructions and supported environments;
- deployment/service inventory, including external providers and domains;
- automation/ruleset inventory and required GitHub App/Actions permissions;
- credential *names and purposes only*, never credential values;
- backup/restore and disaster-recovery procedure;
- publication/DOI and other external-record obligations;
- known defects, holds, unresolved claims, and current D.o.D. state;
- named outgoing and incoming authority plus effective time, when an actual transfer occurs.

## 3. Secret and identity boundary

Secrets MUST NOT be committed, exported in the bundle, copied through receipts, or inferred from historical logs. Transfer uses credential rotation/re-issuance at each provider. The incoming operator proves access using non-secret readbacks. Personal credentials of the outgoing operator are revoked only after successor credentials and rollback access have been independently verified.

## 4. Evidence boundary

Historical evidence remains historical. A new owner/operator MUST establish fresh successor-local evidence for privileged effects, deployments, ruleset administration, publication, and Main validation. `TRANSPORT_ACK != EFFECT_ACK`; possession of the repository is not evidence of operational effect.

## 5. Authority matrix

The handover record MUST distinguish these authorities rather than collapsing them into "owner":

| Authority | Examples |
|---|---|
| IP/licensing | copyright, commercial license, trademarks |
| Repository | GitHub owner/admin, rulesets, CODEOWNERS |
| Release | Main integration, tags, releases |
| Runtime | Railway/Vercel/domain/DNS administration |
| Publication | Zenodo/arXiv/other external records |
| Security | secret rotation, incident response |

No authority is implied from another authority unless a separate instrument explicitly binds them.

## 6. Acceptance protocol

An actual handover is complete only when a transfer receipt records:

1. exact source HEAD/TREE;
2. selected transfer mode;
3. applicable written rights instrument(s);
4. incoming identities/roles;
5. fresh clone/build/test from successor-controlled infrastructure;
6. fresh administrative readback for required repository policy;
7. fresh runtime/deployment readback where runtime authority is transferred;
8. fresh backup restore test;
9. credential rotation completion without exposing secret values;
10. outgoing/incoming acknowledgement of the same receipt.

Until all applicable items are satisfied, the repository remains `HANDOVER_NOT_EFFECTIVE`.

## 7. Fail-closed rule

Ambiguous ownership, missing rights, unknown third-party provenance, missing credentials, unresolved security findings, or inability to reproduce the exact transfer candidate MUST result in HOLD. A handover must never weaken repository protection merely to make transfer easier.
