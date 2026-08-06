<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Autonomous PR continuation

## Purpose

The repository may independently continue deterministic, repository-internal
repairs on an explicitly opted-in same-repository draft pull request. The
continuation is bounded by the active owner delegation and never substitutes
an external scientific review, a cross-repository authorization, or a
separately authorized publication effect.

## Opt-in

A draft pull request is eligible only when its body contains the exact marker:

```text
<!-- qikvrt-autonomous-self-heal:enabled -->
```

The scheduled worker processes at most one eligible pull request per run. The
head repository must equal the executing repository, the base must be `main`,
the head must still equal the immediately reobserved SHA, and history rewriting
is forbidden.

## Versioned execution surface

The workflow is intentionally thin. It performs checkout, Python setup, a
syntax-and-contract preflight, and then executes the versioned repository
script:

```text
tools/qikvrt_autonomous_pr_continue.sh
```

Moving the state machine out of a large YAML-embedded shell block makes the
actual continuation logic directly syntax-checkable with `bash -n`, testable by
the repository suite, hash-bound by repository integrity, and reusable during
exact-head verification. A shell parse failure therefore becomes a normal
preflight failure instead of appearing only after an opted-in PR has been
selected.

## Deterministic sequence

```text
SELECT_ONE_EXACT_OPTED_IN_DRAFT
→ REOBSERVE_MAIN_AND_PR_HEAD
→ MERGE_CURRENT_MAIN_HISTORY_PRESERVING
→ RESOLVE_ONLY_ALLOWLISTED_REGENERABLE_PROJECTION_CONFLICTS
→ COMMIT_THE_HISTORY_PRESERVING_MERGE
→ RUN_ALLOWLISTED_SELF_HEAL_HANDLERS
→ VERIFY_EVERY_TEMPORARILY_RESOLVED_PROJECTION_WAS_REGENERATED
→ VERIFY_PUBLICATION_OVERVIEW
→ VERIFY_REPOSITORY_NATIVE_INTEGRITY
→ RUN_CONTROLLER_TESTS
→ RUN_FULL_REPOSITORY_SUITE
→ REOBSERVE_MAIN_AND_OLD_PR_HEAD
→ PUSH_FAST_FORWARD_SUCCESSOR
→ REPOSITORY_DISPATCH_EXACT_HEAD_REVERIFICATION
→ PERSIST_COMMIT_STATUS_AND_PR_COMMENT
```

The first added repair class is `PUBLICATION_OVERVIEW_DRIFT`. It detects a
local `docs/publications/*/README.md` that is absent from either
`docs/publications/index.json` or `docs/publications/index.html`, adds only the
missing index entries, and then lets repository-native integrity regeneration
bind the changed bytes.

## Generated projection merge conflicts

A history-preserving merge may encounter conflicts in files that are wholly
repository-generated projections. Such a conflict is not resolved by choosing
an arbitrary semantic version of the underlying scientific content.

The worker may temporarily select the current-main version only for this exact
allowlist:

```text
REPOSITORY_FILE_MANIFEST.json
REPOSITORY_FILE_MANIFEST.json.sha256
SHA256SUMS.txt
docs/publications/index.html
docs/publications/index.json
```

Every other conflicted path is a hard block. The worker aborts the merge and
performs no branch mutation.

After an allowlisted temporary resolution, the worker commits the local
history-preserving merge and must then run every allowlisted deterministic
self-heal handler. Every temporarily selected conflict path must appear in the
controller's repaired-path set. The publication overview and repository-native
integrity are regenerated for the combined tree, and the complete repository
suite must finish successfully before any branch push. Temporary merge bytes
are therefore never accepted as final evidence merely because Git could create
a merge commit.

This policy deliberately excludes anticipation history, scientific sources,
claims, receipts, formal sources, and review records. Those paths require a
separate semantics-aware reconciliation contract rather than automatic side
selection.

## Push credential boundary

The workflow uses `GITHUB_TOKEN` by default. A repository administrator may
configure the optional Actions secret
`QIKVRT_AUTONOMY_WORKFLOW_TOKEN` when a narrowly scoped credential is required
for an otherwise permitted same-repository branch update. The secret value is
never printed or persisted. If no optional credential exists, the workflow
falls back to `GITHUB_TOKEN`; any rejected push remains a fail-closed blocker.

This credential option does not authorize main-branch mutation, force pushes,
external publication, Mirror mutation, or any operation outside the declared
same-repository continuation scope.

## Trigger semantics

A push performed with a workflow-provided token does not serve as sufficient
evidence that every ordinary pull-request workflow was re-executed. The worker
therefore emits the explicit repository-dispatch event
`qikvrt_autonomous_exact_head_verify`. The receiving workflow checks out the
exact candidate SHA, runs the full repository suite, re-executes the QCE finite
formal package when present, and writes a distinct status to the candidate
commit.

This mechanism does not impersonate pre-existing workflow contexts and does
not alter branch protection.

## External boundaries

The following gates cannot be manufactured by repository automation:

- an identified independent Human Physics Review when the candidate requires
  one;
- authorization and credentials for a cross-repository Mirror mutation;
- a natural-person decision authorizing a concrete Zenodo payload.

The worker stops before these gates. A future cross-repository continuation may
use a separately configured GitHub App installation credential with access to
both repositories, but no credential value is stored in the repository and no
Mirror or Zenodo effect is authorized by this contract.

## Prohibited effects

- force push or history rewrite;
- direct mutation of `main` by the proposal worker;
- unconditional automatic merge;
- branch-protection change;
- release or tag creation;
- deployment;
- Zenodo or IETF mutation;
- repository-wide `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` claims.
