<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Autonomous PR continuation

## Purpose

The repository may independently continue deterministic, repository-internal
repairs on an explicitly opted-in same-repository draft pull request. The
continuation is bounded by the active owner delegation and never substitutes
an external scientific review or a separately authorized publication effect.

## Opt-in

A draft pull request is eligible only when its body contains the exact marker:

```text
<!-- qikvrt-autonomous-self-heal:enabled -->
```

The scheduled worker processes at most one eligible pull request per run. The
head repository must equal the executing repository, the head must still equal
the immediately reobserved SHA, and history rewriting is forbidden.

## Deterministic sequence

```text
REOBSERVE_MAIN_AND_PR_HEAD
→ MERGE_CURRENT_MAIN_HISTORY_PRESERVING
→ RESOLVE_ONLY_ALLOWLISTED_REGENERABLE_PROJECTION_CONFLICTS
→ COMMIT_THE_HISTORY_PRESERVING_MERGE
→ RUN_ALLOWLISTED_SELF_HEAL_HANDLERS
→ VERIFY_PUBLICATION_OVERVIEW
→ VERIFY_REPOSITORY_NATIVE_INTEGRITY
→ RUN_CONTROLLER_TESTS
→ RUN_FULL_REPOSITORY_SUITE
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

After an allowlisted temporary resolution, the worker must complete the merge
locally, run every allowlisted deterministic self-heal handler, regenerate the
publication overview and repository-native integrity for the combined tree,
run the complete repository suite, and only then push the fast-forward
successor. The temporary selected bytes are therefore never accepted as final
evidence merely because Git could create a merge commit.

This policy deliberately excludes anticipation history and all scientific
source files. Those paths require a separate, semantics-aware reconciliation
contract rather than an automatic side selection.

## Trigger semantics

A push performed with the workflow-provided `GITHUB_TOKEN` does not recursively
start ordinary push or pull-request workflows. The worker therefore emits the
explicit repository-dispatch event
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
- a natural-person decision authorizing a concrete Zenodo payload;
- credentials and authorization for a cross-repository Mirror mutation.

The worker stops before these gates. A future cross-repository continuation may
use a separately configured GitHub App installation credential with access to
both repositories, but no such credential value is stored in the repository
and no Mirror or Zenodo effect is authorized by this contract.

## Prohibited effects

- force push or history rewrite;
- direct mutation of `main` by the proposal worker;
- unconditional automatic merge;
- branch-protection change;
- release or tag creation;
- deployment;
- Zenodo or IETF mutation;
- repository-wide `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` claims.
