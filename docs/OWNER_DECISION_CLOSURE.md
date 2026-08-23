<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Deterministic owner-decision closure

This repository-native coordinator carries one exact Product-Owner decision
through the existing verification and review machinery. It does not turn the
Product Owner into an independent reviewer and does not authorize merge,
publication, deployment, tagging, release, or an `EFFECT_ACK_DONE` claim.

The accepted decision is an exact `APPROVED` comment from the configured
Product Owner on a review-ready pull request. The trusted-main workflow binds
that decision to the live base commit, head commit, head commit's root tree,
and the complete sorted changed-path set. The binding and all evidence are
reobserved before each continuation.

The pure classifier in `tools/qikvrt_owner_decision_closure.py` emits exactly
one of:

- `AUTO_RESOLVABLE`: one declared repository-native continuation is uniquely
  determined, such as dispatching a missing gate or requesting the configured
  Code Owner once;
- `WAITING`: a previously requested workflow or independent review is still
  pending observation;
- `TRUE_BLOCKER`: exact evidence is adverse, contradictory, or semantically
  drifted and a new human decision is required; or
- `CONTINUE`: the exact-head verification and independent-review prerequisites
  are current, so a separately authorized executor/observer may consume the
  receipt.

Any base, head, tree, or scope drift invalidates former-head workflow, status,
and review evidence. A direct descendant whose only intervening paths are the
declared integrity projections may be rebound automatically, but the classifier
still marks all former-head evidence stale and restarts verification. Semantic,
scope, divergent, or non-projection drift returns one `TRUE_BLOCKER` with the
smallest history-preserving next action.

The workflow checks out its implementation from trusted `main`, treats comment
text as data, uses exact workflow-dispatch input names from the policy, and
never executes candidate code with a privileged token. A bot receipt or
workflow disposition remains orchestration evidence only; native GitHub
approval from the configured Code Owner on the current head is independently
required.
