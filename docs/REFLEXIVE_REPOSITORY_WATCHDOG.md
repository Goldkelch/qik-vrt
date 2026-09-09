# Reflexive repository Gatewatch and pre-deadlock admission

The adaptive repository monitor is extended by a watchdog that observes its own repository instance every five minutes and at relevant workflow transitions. Its purpose is not to wait for a deadlock and then diagnose it. It models writer leases, runner pressure, exact-head execution evidence, and unchanged progress topology early enough to issue a deterministic `HOLD` before a second writer or replacement writer is admitted. Its observer path is read-only; a separate schedule-only job has one narrow permission to dispatch the already-declared ruleset effect workflow for an exact `MAIN` subject.

## Operational model

Each repository instance carries the same contract, controller, workflow, and regression test. The Authority remains the serialized source of the portable contract; Mirror and future mesh nodes must retain their own repository identity and integrity projections while satisfying the same structural acceptance.

The watchdog treats repository activity as a resource-allocation graph:

- `REPOSITORY_WRITE_LEASE` has capacity one;
- active repository writers hold or request that lease;
- queued productive workflows request platform runner capacity;
- a writer without a job/step transition beyond its lease is stale;
- unchanged active topology beyond the progress lease is an early stall signal;
- `action_required` and zero-job runs are untrusted execution gaps;
- no active runner is not interpreted as `PIPELINE_EMPTY`.

The first deterministic response is admission control, not destructive recovery: keep one expected-head-bound writer, coalesce only superseded observer runs, preserve an exact-head receipt, and stop before another writer is introduced. The watchdog never cancels a productive writer, mutates a ref, merges a pull request, or performs a release, deployment, Zenodo, DOI, or IETF effect.

## Continuous exact-head Gatewatch

Every scheduled or event-driven observation materializes an artifact-only
`reflexive-watchdog-receipt.json` and the identically bound
`gatewatch-receipt.json`. Both records contain the literal observed head and
tree, a trusted-workflow matrix, node-liveness observations, and the prior
receipt binding. A receipt from another head or tree is discarded rather than
being used as fresh evidence.

The Gatewatch classifies each declared trusted workflow as `SUCCESS`,
`FAILED`, `MISSING`, `ACTIVE`, `UNTRUSTED`, `NOT_OBSERVED`, or
`NOT_APPLICABLE`. A terminal execution failure is a deterministic `HOLD`; a
required pull-request gate that is missing or lacks executed job evidence is
also a `HOLD`. The contract distinguishes a pull request against `main` from
a stacked pull request: only the former requires the evidence-materialization
workflow, because that workflow is configured to trigger only for `main`-base
pull requests. A stacked successor therefore still requires exact-head CI but
never treats an impossible materializer run as proof. Main observations
distinguish an optional scheduled gate from a missing pull-request gate, so a
missing main-only run is never silently invented as a successful verification.

For repository nodes that carry the onboarding records, the same observation
parses all three exact-tree inputs:

- `SEED_ACCEPTANCE_STATUS.json` must bind the currently reobserved Authority
  `main` head;
- `NODE_REGISTRATION_RENEWAL.json` must not be overdue;
- `NODE_HEALTH.json` must not be expired.

An Authority instance without all three node-local records is explicitly
`NOT_APPLICABLE`; a partial record set, malformed record, stale seed
acceptance, overdue renewal, or expired health becomes a read-only `HOLD`.
Records approaching expiry remain visible as `EXPIRING` without a fabricated
renewal. The observer also detects a missed continuous observation only when a
previous receipt is bound to the same head and tree and exceeds the declared
fifteen-minute freshness bound. A burst of cancelled, zero-job observer runs is
coalesced only when a later exact-head receipt remains within that bound;
otherwise it is a deterministic observation-cadence `HOLD`, not a claim of
pipeline quiescence.

The observer path remains five-minute, exact-head-bound, and read-only. It
fetches the current Authority head only for comparison, materializes Action
artifacts only, never writes a repository liveness record, and never treats
its own terminality as gate success.

On a scheduled `main` observation only, the narrow dispatcher rebinds the
checked-out `main` SHA, GitHub's current `main` SHA, and the SHA-256 of
`policy/GITHUB_MAIN_RULESET_V1.json`. It then transports exactly those values
as `mode=MAIN`, `expected_main`, and `expected_policy_sha` to the sole ruleset
effect workflow. It has `actions: write` only for that dispatch: it carries no
App token, does not call the ruleset API, and cannot invoke the reconciler.
Before transport it reobserves effect-workflow runs and skips when an exact
Main-mode run, or conservatively any queued/active effect run, already exists.
It never cancels an effect run. Its receipt records either a bounded no-op,
structured `HOLD`, or accepted transport; it never claims that the downstream
effect occurred. Scheduled observations use their own non-preemptive
concurrency lane (one running plus at most the newest pending run), so the
five-minute cadence cannot repeatedly cancel the slower pre-observation before
this bounded dispatch path can run; event and pull-request observer coalescing
remain separate.

## Reflexivity

The watchdog observes the workflows that create and verify repository state, while its own executions are classified as observers rather than productive writers. Observer executions use a coalescing concurrency group so newer observations replace obsolete observations without consuming the repository write lease. A scheduled observation prevents unchanged heads from becoming permanently invisible merely because no new event occurs.

## Database comparison boundary

Conventional relational database systems already provide transaction deadlock handling techniques such as prevention, detection, ordering, and timeout policies. The QIK-VRT improvement claimed here is narrower and architectural: deadlock-risk admission is bound to versioned repository heads, workflow/job evidence, provenance receipts, Authority-to-node serialization, and external-effect boundaries across independently instantiated repositories. It is not a claim that every relational database lacks deadlock management, nor a benchmark proving universal performance superiority.

## Nonclaims

A successful watchdog run is observation evidence, not gate success. The mechanism does not prove global deadlock freedom, repository completion, Authority–Mirror equality, empirical confirmation, scientific consensus, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
