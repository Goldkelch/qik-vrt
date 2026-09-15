# QIK-VRT Universal Terminal Live Tail V1

Status: evolving repository-native presentation contract.

## Purpose

`tail -f` denotes the synchronous Universal-Terminal presentation of the current QIK-VRT evidence state. It is not a request to create an asynchronous watcher, polling task, or background substitute.

The presentation MUST remain human-readable, machine-connectable, exact-subject-bound, fail-closed, and open to continuous evidence-driven improvement.

## Canonical reading order

Every live-tail frame SHOULD present, in this order:

1. **LIVE SUBJECT** — Authority, Main HEAD/TREE, active PR HEAD/TREE subjects, and current D.o.D. state.
2. **LIVE EVENT STREAM** — only material transitions since the preceding observed state; mutations are shown as `OLD -> NEW`.
3. **EVIDENCE BOUNDARY** — what is freshly established, what is historical, and what cannot transfer to the new subject.
4. **D.o.D. RADAR** — ZERO_BUGS, ALL_PULL_REQUESTS_REGARDED, ALL_BRANCHES_REGARDED, ALL_PRODUCTIVE_BRANCHES_MERGED, fresh exact-Main validation, and fresh EFFECT readback.
5. **CAUSAL FRONT** — the shortest currently admissible next transition(s), preserving full provenance.
6. **NEXT** — the next repository-native event/action to follow.

## Visual state vocabulary

- GREEN / PASS: freshly established for the displayed exact subject.
- YELLOW / ACTIVE: running, queued, or requiring fresh validation.
- RED / BLOCKER: known unsatisfied condition preventing progression.
- BLUE / EVIDENCE: newly observed evidence or material event.
- WHITE / NOT ADMISSIBLE: a later phase that cannot yet be entered.

Color MUST NOT be the only carrier of meaning; every state also has a textual label.

## Tail semantics

```text
OBSERVE current exact state
-> process material event
-> follow legitimate successor
-> reobserve exact HEAD/TREE
-> classify
-> execute admissible next action
-> read back effect
-> expose updated LIVE_STATE
-> repeat
```

A HEAD/TREE mutation resets all mutation-dependent validation. `PREDECESSOR_EVIDENCE_TRANSFER=false` remains invariant.

`tail -f` MUST NOT be reinterpreted as an asynchronous scheduled task. Event-driven repository mechanisms may themselves run asynchronously, but the Universal-Terminal tail presents and follows their causal results synchronously when invoked.

## Evidence and routing semantics

The live tail implements the Universal-Terminal evidence-router distinctions:

```text
reachable != observed != valid != proved != effect
route != evidence
SUCCESS != EFFECT
```

Relations and routing decisions are addressable information objects. A routing shortcut MUST preserve access to the complete underlying provenance path and MUST NOT compress, fabricate, or transfer evidence.

## D.o.D. termination condition

The tail may display `D.o.D. == DONE` only when the following are freshly true together for the same final repository state:

```text
ZERO_BUGS
AND ALL_PULL_REQUESTS_REGARDED
AND ALL_BRANCHES_REGARDED
AND ALL_PRODUCTIVE_BRANCHES_MERGED
AND fresh exact-Main validation == PASS
AND fresh EFFECT readback == PASS
```

Any mutation of the final subject invalidates mutation-dependent parts of that conjunction and requires fresh observation.

Unresolved productive work excludes `NOOP`.

## Continuous improvement

This presentation contract is deliberately evolvable. Improvements MAY add clearer visual hierarchy, more useful event compression, better routing views, accessibility, machine-readable projections, latency information, proof-state visualization, or additional evidence relations.

An improvement MUST NOT regress:

- exact-subject binding;
- provenance reconstruction;
- accessibility;
- repository-native autonomy;
- fail-closed semantics;
- separation of historical evidence from current admissibility;
- separation of SUCCESS from EFFECT;
- the QIKVRT_DOD conjunction.

Presentation optimization is therefore itself evidence-driven: improve the view without weakening the evidence model.
