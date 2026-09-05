# Recursive Autonomy: Evidence Spiral in Depth and Breadth

Autonomy in QIK-VRT is not one successful transition and not blind repetition. It is the recursive application of the same exact-subject resolver to every causally justified successor until the observed frontier no longer carries.

## Canonical form

```text
FRONTIER_0
  -> observe exact subjects
  -> resolve every independent read-only branch deterministically
  -> select at most one bounded mutation per node
  -> execute only within delegated authority
  -> read back every attempted effect
  -> emit successor subproblems
FRONTIER_1
  -> apply exactly the same contract again
  -> ...
  -> LOCAL_FIXPOINT | OPEN_FRONTIER
```

Depth means that a successor problem is itself processed by the same resolver. Breadth means that causally independent subjects on one frontier are observed together and merged deterministically. Breadth does not authorize uncontrolled parallel mutation.

## Stop semantics

`LOCAL_FIXPOINT` means the declared observed frontier contains no pending ACTION, REOBSERVE, HOLD, REQUEST_AUTHORITY, or queued successor. It is local closure only.

`OPEN_FRONTIER` means the recursion still carries or was stopped by an explicit fail-closed bound such as maximum depth, maximum observed nodes, unavailable authority, stale subject evidence, or an unresolved dependency.

`LOCAL_FIXPOINT != GLOBAL_FINALITY`.

## Cycle prevention

Every problem receives a causal fingerprint with activity-only noise removed. Reappearance of the same causal problem is deduplicated as `CAUSAL_CYCLE_DEDUPLICATED`; it is not blindly retried.

## Self application

The resolver has no privileged status. Its own code, workflow, policy, materialization, persistence, readback, and prevention layers are ordinary exact subjects. If the resolver exposes a defect in itself, that defect is fed back through the same Evidence-Spiral contract.

## Invocation

Single cycle:

```bash
python tools/qikvrt_universal_evidence_spiral.py problem.json
```

Bounded recursive traversal:

```bash
python tools/qikvrt_universal_evidence_spiral.py problem.json --recursive --max-depth 32 --max-nodes 1024
```

The bounds are safety guards, not semantic completion. Reaching a bound yields an open frontier rather than a false final state.
