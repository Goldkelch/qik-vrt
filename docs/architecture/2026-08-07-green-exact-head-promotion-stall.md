# Green Exact-Head Promotion Stall — Root Cause and Permanent Repair

Date: 2026-08-07

## Incident class

`AUTHORITY_GREEN_EXACT_HEAD_WITHOUT_PROMOTION_EFFECT`

The observed symptom was a pull request whose current exact head had terminal-green repository-native materialization and review/CI gates while the pull request remained `open + draft + mergeable` and no promotion execution remained active.

This was not a Lean, kernel, integrity, or runner failure. The productive chain had reached the promotion boundary and then had no repository-native executor responsible for crossing that boundary.

## Root cause

The repository already contained the *authorization semantics* for expected-head-bound promotion:

- promotion is allowed only after current-base reobservation;
- the candidate head must remain unchanged;
- the diff must remain repository-contract compliant;
- no external effect may be involved;
- every applicable exact-head gate must be terminal green;
- no current competing writer may overlap the candidate.

However, the existing autonomous self-heal workflow intentionally stopped after creating a draft candidate. Its contract explicitly set `proposal_workflow_may_merge=false`, and the workflow text stated that the proposal workflow itself does not merge.

That safety boundary was correct, but there was no separate promotion executor implementing the already-authorized next state transition. The result was a liveness gap:

```
DRAFT_CANDIDATE
→ MATERIALIZED_EXACT_HEAD
→ TERMINAL_GREEN
→ [NO EXECUTOR]
→ OPEN_DRAFT_FOREVER
```

The defect was therefore not an unsafe merge implementation; it was a missing state-machine edge between verified eligibility and expected-head-bound promotion.

## Why the repair was non-trivial

Qualitative engineering difficulty: **medium-high (approximately 7/10)**.

The code needed to solve a superficially simple problem — “merge when green” — without weakening the repository's fail-closed evidence model. The difficult parts were:

1. **Historical run supersession.** A current exact head can contain older `action_required`/zero-job registrations and later successful trusted-proxy runs. The evaluator must select the newest run per workflow name rather than treating historical registrations as permanently adverse.
2. **Exact-head binding.** Eligibility must not survive head drift. The merge endpoint therefore receives the exact reobserved SHA as a precondition.
3. **Current-base binding.** A stale candidate must not be promoted after `main` advances.
4. **Competing writers.** An unrelated stale PR on an old base is not a current writer, while an overlapping open PR on the exact current base is. Exact-head verification proxies sharing the candidate SHA are not independent writers.
5. **Draft-to-ready race.** Reclassifying a draft can itself register new checks. A one-pass `ready → merge` sequence would therefore be epistemically unsafe. The permanent repair uses two separate cycles.
6. **External-effect separation.** Repository promotion remains pre-effect work. Zenodo, DOI, IETF, release, deployment, `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, and Authority/Mirror equality remain outside this executor.
7. **Liveness without busy waiting.** The executor is triggered by relevant workflow completions and has a ten-minute scheduled fallback. It does not monopolize a runner while waiting.

## Permanent state machine

The repaired promotion path is:

```
MARKED_CURRENT_BASE_CANDIDATE
→ EXACT_HEAD_SNAPSHOT
→ REQUIRED_GATES_COLLAPSED_TO_LATEST_RUN
→ ALL_APPLICABLE_GATES_TERMINAL_NON_ADVERSE
→ NO_CURRENT_BASE_OVERLAPPING_WRITER
→ PROMOTABLE

if draft:
    DRAFT_TO_READY
    → STOP
    → REOBSERVE_ON_LATER_CYCLE
else:
    REOBSERVE_BASE_AND_HEAD
    → REST_MERGE_WITH_SHA_PRECONDITION
    → REOBSERVE_PROMOTED_MAIN
```

The crucial invariant is:

> `Green` does not imply `Merged`; it authorizes exactly one further reobserved transition.

The second crucial invariant is:

> `DraftToReady` does not imply `Merge`; readiness is followed by a new exact-head gate observation cycle.

## TDD repair

The regression test was persisted before the implementation. It encodes the original failure mode and the fail-closed counterexamples:

- terminal-green exact head is `PROMOTABLE`;
- a newer success supersedes an older same-workflow `action_required` registration;
- missing required gate blocks;
- active required gate blocks;
- failed required gate blocks;
- head drift blocks;
- base drift blocks;
- current-base overlapping writer blocks;
- external-effect scope blocks;
- non-mergeable candidate blocks.

A second contract test locks the workflow-level properties, including the two-phase transition, SHA-bound merge and external-effect boundary.

## Files introduced or changed

- `tools/qikvrt_expected_head_promotion.py`
  - pure fail-closed decision core;
  - no GitHub mutation;
  - deterministic first-blocker classification.
- `tests/test_qikvrt_expected_head_promotion.py`
  - behavioral regression suite.
- `tests/test_qikvrt_expected_head_promotion_contract.py`
  - machine-readable contract/workflow regression suite.
- `.github/workflows/qikvrt_expected_head_promotion.yml`
  - repository-native promotion executor;
  - relevant `workflow_run` triggers plus `*/10` fallback;
  - one candidate per serialized run;
  - two-phase ready/reobserve/merge;
  - REST merge bound to exact SHA.
- `.github/workflows/qikvrt_autonomous_self_heal.yml`
  - future self-heal candidates opt in with a pre-effect promotion marker;
  - proposal workflow remains non-merging.
- `state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json`
  - explicit promotion-executor contract.

## Safety boundary

The executor is repository-internal only. It must not perform or infer:

- Zenodo publication or mutation;
- DOI creation;
- IETF submission or revision;
- GitHub release/tag creation;
- deployment;
- credentialed external effects;
- physical correspondence or scientific confirmation;
- `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`;
- Authority/Mirror equality.

Any missing, ambiguous, stale, active, failed, conflicting, or externally scoped evidence remains a blocker.

## Bootstrap and migration note

A promotion executor added by a pull request cannot schedule itself from `main` before that pull request is first promoted. Therefore the pull request carrying this repair must pass its ordinary exact-head gates and be promoted once through the existing repository-authorized path. After that bootstrap merge, future marked candidates are covered by the repository-native executor and the original liveness gap no longer depends on a chat session or repeated Product Owner interaction.

Because this repair changes the current candidate head, every previous exact-head gate result for the older head is historical only. Repository-native integrity must be rematerialized and the applicable gates must become terminal green on the new head before the bootstrap promotion is justified.
