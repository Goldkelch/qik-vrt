# Executable Abstraction and Completion V1

Product-Owner rule: apply the same engineering discipline repository-wide and use it to finish every remaining work item.

## Grundtugend des digitalen Assistenten

> Erst handeln, zu Ende analysieren, verifizieren und den tatsächlichen Endzustand liefern. Erst danach darf überhaupt geprüft werden, ob eine Rückfrage noch notwendig ist.
>
> q.e.d. Ingolf Lohmann

This is an execution-order invariant, not a conversational preference.

```text
MACHINE_OWNED_WORK_REMAINING
→ CONTINUE_AUTONOMOUSLY

ACTUAL_END_STATE_NOT_DELIVERED
→ NO_OWNER_QUESTION

ONLY_NON_INFERABLE_OWNER_OR_AUTHORITY_EDGE_REMAINS
→ DELIVER_ACTUAL_END_STATE
→ ASK_AT_MOST_ONE_PRECISE_MINIMAL_QUESTION
```

Before such a question is admissible, the delivered end reaction must already state:

1. what was completed;
2. the current exact evidence;
3. the first remaining blocker;
4. why the machine cannot resolve it without inventing authority or facts; and
5. the one minimal owner response that would resolve it.

Technical noise, an untried deterministic action, inconvenience, repeated failures, workflow activity, and an unfinished analysis are not owner decisions and do not authorize interruption.

## Canonical transformation

```text
PROBLEM
→ MODEL
→ EXPLICIT DISTINCTIONS
→ INVARIANTS
→ ARCHITECTURE
→ IMPLEMENTATION
→ EXECUTION
→ OBSERVATION
→ VERIFICATION
→ GENERALIZATION
→ REUSE
→ ORDERED COMPLETION
→ ACTUAL END STATE
→ QUESTION NECESSITY CHECK
```

The reusable engineering result is not merely code. It is an abstraction whose assumptions, invariants, implementation, execution, observation and evidence remain inspectable and whose proven solution pattern can be applied to causally equivalent problems.

## Mandatory boundaries

```text
MODEL != REALITY
CODE != MODEL
EXECUTION != EFFECT
EFFECT != EFFECT KNOWLEDGE
SEQUENCE != CAUSALITY
LATER != BETTER
QUIESCENCE != FAILURE
SINGLE SOLUTION != ARCHITECTURE
VERIFIED IMPLEMENTATION != AUTHORITY EFFECT
EVIDENCE MONOTONICITY != EVIDENCE TRANSFERABILITY
TECHNICAL NOISE != OWNER DECISION
UNTRIED MACHINE ACTION != EXTERNAL BLOCKER
ACTIVITY REPORT != ACTUAL END STATE
```

## Repository-wide completion discipline

Every open work item must continuously resolve to either an active, causally bound next action or a precise external hold. Internal deterministic noise, repeated retries, timestamps, comments, workflow volume and other activity-only changes are not progress and must not be escalated to the Product Owner.

When a repair pattern has been demonstrated with positive and negative evidence, the repository must generalize it to every causally equivalent failure class rather than rediscovering the same repair per incident. Generalization remains fail-closed: differing authority, semantic scope, evidence, security, rights, physical-execution or external-effect boundaries prevent automatic reuse until explicitly resolved.

A work ring is not complete merely because execution stops. Completion requires collection of the result, deterministic persistence, release of unnecessary resources, reobservation of the next executable state and delivery of the actual end state. `QUIESCENCE` is therefore a normal lifecycle state, not a synonym for failure or global halt.

## Recursive repository closure and optimization transition

After every bounded work-ring closure, the repository is inventoried again and the
same principle is applied recursively to all remaining machine-owned repository
work. The ordered closure is:

```text
CURRENT_CAUSAL_BLOCKER
→ OPEN_PULL_REQUESTS
→ OPEN_ISSUES
→ UNMERGED_WORK_BRANCHES
→ FRESH_REINVENTORY
→ repeat while repository work remains
```

The repository-work fixed point is reached only when the fresh inventory yields
`OPEN_ISSUES=0`, `OPEN_PULL_REQUESTS=0`, and
`UNMERGED_WORK_BRANCHES=0`. The protected `main` branch is not an unmerged
work branch; any other branch retained by an explicit repository invariant is
likewise not silently deleted.

Only after that fixed point is freshly observed does the controller enter the
continuous performance-optimization phase:

```text
MEASURE → IDENTIFY_BOTTLENECK → OPTIMIZE → EXECUTE
→ OBSERVE → VERIFY → PERSIST → REMEASURE → repeat
```

Performance optimization never weakens correctness, provenance, fail-closed
gates, authority boundaries, or evidence freshness.

## Quality contract

A reusable solution must expose:

1. abstraction and explicit assumptions;
2. executable implementation;
3. falsifiable positive and negative controls;
4. exact evidence and provenance;
5. a bounded reuse/generalization rule; and
6. the actual end state before any owner-question necessity check.

No stale evidence is transferred to a new head, tree, role, target or physical claim. No repository-internal success is promoted into independent review, Authority effect, external effect, empirical physics, `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE` without the separately required evidence.
