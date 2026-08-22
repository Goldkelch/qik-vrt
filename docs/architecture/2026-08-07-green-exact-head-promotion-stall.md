# Green Exact-Head Promotion Stall — Root Cause and Permanent Repair

Date: 2026-08-07

Superseding safety amendment: 2026-08-22. The original implementation below
was re-evaluated against immediate-predecessor (`HEAD^1`) semantics. GitHub's
pull-merge endpoint binds the candidate head but does not compare-and-swap the
reobserved base; automatic merge is therefore disabled. Automatic
draft-to-ready is also disabled because that mutation has no atomic
expected-base-and-head precondition and its `GITHUB_TOKEN` event cannot prove a
fresh follow-on gate cycle.

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

The original liveness defect was a missing state-machine edge between verified
eligibility and promotion. The later zero-bug audit also exposed that the
proposed automatic edge could not prove the checked base as the resulting
merge commit's immediate first parent. The permanent implementation now stops
at an evidence-bound authority request.

## Why the repair was non-trivial

Qualitative engineering difficulty: **medium-high (approximately 7/10)**.

The code needed to solve a superficially simple problem — “merge when green” — without weakening the repository's fail-closed evidence model. The difficult parts were:

1. **Historical run supersession.** A current exact head can contain older `action_required`/zero-job registrations and later successful trusted-proxy runs. The evaluator must select the newest run per workflow name rather than treating historical registrations as permanently adverse.
2. **Exact-head binding.** Eligibility must not survive head drift. A head-only
   merge precondition is necessary but insufficient because it does not bind
   the base that must become `HEAD^1`.
3. **Current-base binding.** A stale candidate must not be promoted after
   `main` advances. GitHub exposes no atomic pull-merge precondition for this
   checked base.
4. **Competing writers.** An unrelated stale PR on an old base is not a current writer, while an overlapping open PR on the exact current base is. Exact-head verification proxies sharing the candidate SHA are not independent writers.
5. **Draft-to-ready race.** Reclassifying a draft can itself register new
   checks, but `GITHUB_TOKEN`-authored events do not reliably trigger those
   follow-on workflows. The permanent repair requests authority and performs
   no automatic ready mutation.
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
→ HOLD_UNVERIFIED

if draft:
    REQUEST_HISTORY_PRESERVING_READY_RECLASSIFICATION_AUTHORITY
else:
    REQUEST_HISTORY_PRESERVING_EXACT_BASE_CAS_AUTHORITY
```

The crucial invariant is:

> `Green` does not imply `Merged`; it derives only a separately authorized,
> history-preserving continuation request.

The second crucial invariant is:

> The repository executor performs neither `DraftToReady` nor `Merge`.

## TDD repair

The regression test was persisted before the implementation. It encodes the original failure mode and the fail-closed counterexamples:

- terminal-green non-draft exact head requests exact-base-CAS authority;
- terminal-green draft exact head requests ready-reclassification authority;
- a newer success supersedes an older same-workflow `action_required` registration;
- missing required gate blocks;
- active required gate blocks;
- failed required gate blocks;
- head drift blocks;
- base drift blocks;
- current-base overlapping writer blocks;
- external-effect scope blocks;
- non-mergeable candidate blocks.

A second contract test locks the workflow-level properties, including the
absence of automatic ready/merge mutations and the external-effect boundary.

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
  - evidence-bound ready and exact-base-CAS authority requests;
  - no ready or merge mutation.
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

A promotion observer added by a pull request cannot schedule itself from `main`
before that pull request is independently accepted through the repository's
existing authority path. Once present on `main`, future marked candidates are
covered by the repository-native observer, but any state-changing promotion
still requires separately exercised exact-subject authority.

Because this repair changes the current candidate head, every previous exact-head gate result for the older head is historical only. Repository-native integrity must be rematerialized and the applicable gates must become terminal green on the new head before the bootstrap promotion is justified.
