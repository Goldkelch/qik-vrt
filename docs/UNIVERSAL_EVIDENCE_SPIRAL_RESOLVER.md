# Universal Evidence-Spiral Resolver

This document turns the recurring QIK-VRT control pattern into one repository-wide problem-resolution discipline.

It does **not** claim that every problem has the same domain solution. It claims that every repository problem can be processed by the same control skeleton without inventing evidence or authority.

## Canonical loop

```text
OBSERVE
→ BIND exact subject
→ CLASSIFY claims and boundaries
→ DECOMPOSE true dependencies
→ PARALLELIZE only independent reads
→ ENUMERATE bounded moves
→ REJECT invariant violations
→ SELECT smallest causally justified move
→ EXECUTE only inside delegated authority
→ REOBSERVE actual effect
→ COMPARE causal delta
→ PERSIST receipt + prevention
→ EMIT successor state
```

The loop is the executable form of the Evidence Spiral:

- one local cycle can terminate;
- the knowledge process remains open to new evidence;
- new evidence produces a successor cycle instead of rewriting the historical one.

## What counts as a problem

The same wrapper applies to:

- a failing unit or integration test;
- a stale pull-request review;
- a workflow blocked by platform semantics;
- a broken publication carrier;
- missing provenance or integrity material;
- an unresolved scientific claim boundary;
- a numerical or serialization defect;
- a missing Authority/Mirror synchronization observation;
- a physical-effect request waiting for readback;
- a documentation or interoperability ambiguity.

The **domain-specific repair** can differ completely. The evidence discipline does not.

## Exact subject first

A problem is not actionable until its subject is exact enough to prevent evidence transfer. Minimum repository binding:

```text
(repository, identity, head, tree)
```

Examples of additional subject identity include PR number, workflow/run/job, file/blob digest, theorem/source digest, measurement configuration, publication package digest, device identity or external record ID.

If the binding is incomplete or stale, the correct result is `REOBSERVE`, not a guessed repair.

## Dependency decomposition

A dependency exists only when one state is genuinely required before another state can be evaluated or changed.

Independent observations may run in parallel. Mutations are serialized at real causal joins. Activity order, timestamps and run numbers are never sufficient proof of causality.

This yields the operational rule:

> Along real dependencies: sequence. Across independent branches: parallelize. At the join: canonicalize and bind.

## Candidate move simplex

Each cycle constructs a finite set of bounded moves. Each move declares:

- stable ID;
- objective class;
- action;
- authority required;
- whether it mutates state;
- exact expected readback;
- any dependencies;
- any claim boundary it could cross.

Moves that transfer predecessor evidence, widen authority, weaken invariants or claim unobserved external effects are rejected before scoring.

The surviving moves use the objective order already authorized in Issue #731:

1. deterministic correctness;
2. false authority/effect inference;
3. self-continuation/liveness;
4. exact binding/reproducibility;
5. stale or duplicate work;
6. latency/resource waste;
7. simplicity;
8. testability/observability;
9. publication-worthiness.

Lower-priority optimization never compensates for a higher-priority invariant violation.

## D0 terminal ABI

When no action is executed, the cycle terminates in the existing four-state ABI:

```text
D0=0 NOOP
D0=1 HOLD
D0=2 REOBSERVE
D0=3 REQUEST_AUTHORITY
```

`ACTION` is a selected transition, not a terminal success claim. After action, readback is mandatory.

## Readback is the closure test

A command, request, dispatch, transport acknowledgment or zero exit status is not sufficient unless the declared problem is exactly that transport operation.

Every mutation must say in advance what observation would establish its intended successor state. The resolver therefore requires `expected_readback` for every candidate move.

Examples:

- code repair → exact-head regression passes;
- ruleset mutation → live ruleset readback matches policy;
- publication → public DOI/record/files/checksums match frozen bytes;
- physical actuation → independent sensor/readback observes intended physical state;
- review route → submitted review exists on exact current head;
- merge → exact target branch contains expected commit/tree.

## Prevention is part of repair

Issue #854 supplies the second half of the universal pattern: a known deterministic defect is not fully resolved when the immediate symptom disappears.

Where technically possible, the cycle must persist a prevention mechanism such as:

- regression test;
- static invariant;
- schema constraint;
- fail-closed planner rule;
- stale-head rejection;
- event-cycle guard;
- duplicate/reorder/concurrency test;
- capability/authority check.

The recent PR-head mutation failure is the canonical example: removing one bad push repaired the current carrier; adding a repository-wide regression test prevented the same class from silently returning.

## Scientific and external-effect boundary

The resolver may classify or prepare an external effect, but it must not collapse states:

```text
REPOSITORY_EVIDENCE != EXTERNAL_PUBLICATION
EXTERNAL_PUBLICATION != EMPIRICAL_CONFIRMATION
FORMAL_VERIFIED != PHYSICAL_CORRESPONDENCE
TRANSPORT_ACK != EFFECT_ACK
```

A scientific hypothesis, a Zenodo package and a real experimental result therefore use the same control skeleton but different evidence predicates.

## Tool

The stdlib-only reference resolver is:

```bash
python3 -B tools/qikvrt_universal_evidence_spiral.py problem.json --output receipt.json
```

It is deliberately a deterministic selector, not an omnipotent executor. The caller remains responsible for executing the selected action only within its delegated authority and then feeding the readback into the successor cycle.

## Universal claim boundary

The universal claim is **structural**, not magical:

> Every repository problem must be reducible to an exact subject, explicit evidence, real dependencies, bounded admissible moves, authority boundaries and an observable closure predicate.

If a problem cannot yet be represented that way, the representation gap itself becomes the next exact problem.

That recursive property is the Evidence Spiral.
