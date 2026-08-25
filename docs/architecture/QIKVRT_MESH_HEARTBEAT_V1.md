# QIKVRT Mesh Heartbeat V1

## Contract

```text
1/s
=
HEARTBEAT

HEARTBEAT
!= POLLING
!= BLIND_RETRY
```

The one-hertz signal is a liveness and lease-freshness pulse only. It may update the last-seen lease of a bound node. It may not discover work, select work, dispatch work, repeat a failed work unit, transfer stale evidence, or manufacture completion.

The bounded candidate test begins semantic work only from one locally constructed, content-bound event. One accepted event may produce at most one bounded work unit. Reuse of the same event identity with the same bytes is idempotent; reuse with different bytes fails closed. The local payload digest is not a signer, MAC, webhook signature or proof of external ingress authentication.

```text
0
→ 1
→ ARBEIT
→ ERGEBNIS
→ REOBSERVATION
→ AUTHORITY-EFFEKT
→ 0
```

`0` is quiescence. `1` is acceptance of a locally constructed content-bound event. `ARBEIT` is the bounded deterministic work unit. `ERGEBNIS` is its exact result. `REOBSERVATION` recomputes and compares the result. `AUTHORITY-EFFEKT` in the candidate system test is deliberately restricted to a local test ledger. A repository Authority effect is never inferred from candidate execution.

## Bounded system test

The repository-native system test starts four independent heartbeat emitter processes arranged as two Authority/Mirror pairs. Each process opens one real TCP connection to a loopback collector and emits four hash-linked heartbeats on an exact one-second schedule. Every heartbeat contains the exact source head and tree, a contiguous sequence number, the previous heartbeat digest, its scheduled and actual monotonic timestamps, and explicit false values for semantic work, polling and blind retry.

The collector validates every frame and returns a digest-bound acknowledgement. After all heartbeat events have been reobserved, the test executes one locally constructed work event through the complete local lifecycle. An identical replay must return byte-identical evidence without another authority-ledger record. Rebinding the same event ID to different bytes must block.

The execution receipt binds:

- exact head and tree;
- four processes and two pairs;
- one-hertz schedule and send lateness;
- hash-linked heartbeat history;
- zero heartbeat-triggered semantic work;
- zero polling and zero blind retry;
- exact work lifecycle;
- idempotent replay and tamper blocking;
- local construction scope and explicit absence of observed external ingress authentication;
- local-test-only authority effect;
- `external_effect=NONE`;
- no publication, deployment, physical execution, `PASS`, `FINAL_PASS`, or general `EFFECT_ACK_DONE`.

## Full automation

`.github/workflows/qikvrt_mesh_heartbeat.yml` is event-driven. It runs on relevant pull-request or Authority-main push events and on explicit manual dispatch. It has no `schedule:` trigger, checks out the literal candidate head, runs the focused contract and bounded four-process system test, verifies the audit receipt, verifies repository integrity and uploads exact evidence. The candidate job has `contents: read`.

`.github/workflows/qikvrt_mesh_heartbeat_main_ledger.yml` is a separate trusted writer. It is eligible only after a successful `push` run on Authority `main`. Before any write it makes a GET-only observation of the platform-effective rules for the literal ledger branch, requires exactly one active ruleset to provide both deletion and non-fast-forward protection, then records the selected ruleset’s include/exclude and explicitly visible empty bypass list. The initial, pre-push, and post-readback snapshots are canonicalized and compared; unavailable or drifting evidence is `REOBSERVE`, while a complete but insufficient or ambiguous protection configuration is `REQUEST_AUTHORITY`. Neither state writes the ledger, and this workflow never mutates a ruleset. Only a qualified unchanged observation permits the existing source/ledger CAS and ordinary fast-forward push. It then re-fetches the exact remote ledger ref into a fresh repository, requires the remote commit to equal the intended commit, reads the source-bound target and `latest.json` from that fetched commit, byte-compares both with the intended receipt and persists a non-completion reobservation artifact. The writer is globally serialized with `cancel-in-progress:false`.

## Event-driven live status projection

The former bounded API polling loop is removed. `.github/workflows/qikvrt_live_status_watch.yml` now reacts once to a repository event and materializes one exact event-bound status snapshot. Relevant `workflow_run` transitions (`requested`, `in_progress`, `completed`), pull-request lifecycle events, an explicit command, or manual dispatch are the only triggers.

The projection performs no `gh api` crawl, no sleep loop and no repeated workflow discovery. It consumes one repository-delivered GitHub event envelope, writes one job summary and uploads one exact JSON artifact. This projection does not independently prove the envelope's webhook signature or delivery identity. It explicitly records:

```text
trigger = REPOSITORY_EVENT_ONLY
polling = false
blind_retry = false
semantic_work_triggered = false
external_effect = NONE
```

A later repository event creates a new projection; a timer does not repeatedly ask whether the state changed. This closes the observed API-rate-limit failure of the previous polling implementation without weakening the fail-closed evidence boundary.

```text
CANDIDATE_EXECUTION
!= REPOSITORY_WRITE_AUTHORITY

HEARTBEAT_LIVENESS
!= SEMANTIC_WORK_TRIGGER

EVENT_BOUND_STATUS_PROJECTION
!= POLLING

LOCAL_TEST_AUTHORITY_EFFECT
!= AUTHORITY_MAIN_EFFECT

ARTIFACT_UPLOADED
!= PUBLISHED
!= DEPLOYED
```
