# Publication-candidate readiness observer

The publication-candidate readiness observer is a continuously scheduled,
read-only projection for pull requests against Authority `main`. It is not a
promotion executor. Every receipt is advisory and must be reobserved at the
exact action-time base, head, and tree before a separately authorized person
or controller makes any change.

## What each cycle binds

The observer captures one pull-request snapshot and repeats the Authority
`main` and candidate reobservation before producing an artifact-only receipt.
It binds the repository, pull request, base SHA and tree, head SHA and tree,
changed-path digest, candidate and base workflow-blob inventories, and the
observer-contract digest. Any drift invalidates the prior receipt.

The gate matrix trusts only `pull_request` runs for the literal candidate head
and branch. A required run needs terminal success and nonzero executed job
evidence. `action_required`, cancelled runs, zero-job runs, undeclared skips,
and skipped jobs outside the declared allowance are `HOLD`, not success.
Branch-gated archive probes and the PR18 repair workflow are `NOT_APPLICABLE`
only when their declared branch condition does not apply; their skip is never
silently promoted to a pass.

The receipt separately records submitted-review state, draft and mergeability,
current-base competing writer path overlaps, and an optional structured
predecessor declaration. Scope coverage can identify a clean current-main
successor, but it does not close or mutate the predecessor.

## Repository readiness versus external boundaries

`PROMOTE_REPOSITORY_CANDIDATE` means only that the read-only repository
projection found no repository-side blocker in that exact snapshot. It does
not ready a draft, merge, dispatch another workflow, or authorize any effect.

The same receipt always reports Zenodo, arXiv, and IETF separately. Local
candidate files are bound by digest, but they remain `NOT_AUTHORIZED` unless
fresh owner authorization, destination/account observation, and independently
bound platform receipts are supplied at action time. The observer never calls
those platforms and never emits an external-effect acknowledgement.

## Placement and inheritance

The contract is included in the workflow-executor mesh contract for Authority,
Mirror, and every future mesh node. That placement preserves the observer's
read-only boundary without widening the existing writer dispatch policy. The
workflow uses only `actions: read`, `contents: read`, and `pull-requests:
read`, and uploads the receipt as an Actions artifact.

While this observer is itself first introduced by a pull request, its literal
pull-request head is checked out solely to bootstrap the read-only contract and
regression checks. Once the contract is on Authority `main`, scheduled and
workflow-run cycles check out Authority `main` and observe candidates only by
API reads. Neither bootstrap nor steady-state execution receives a write scope.
