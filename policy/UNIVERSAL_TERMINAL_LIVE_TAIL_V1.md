# QIK-VRT Universal Terminal Live Tail V2

Status: evolving repository-native execution and presentation contract.
Supersedes the V1 snapshot-oriented presentation semantics while preserving its evidence boundaries.

## Purpose

`tail -f` denotes synchronous continuation from a persistent evidence cursor. It is not a dashboard refresh, snapshot with a LIVE label, asynchronous watcher, polling task, or background substitute.

The terminal MUST emit only newly observed material transitions after its cursor, execute admissible consequences, read back their effects, advance the cursor, and immediately continue while another causal event is observable.

## Persistent cursor

The cursor is an addressable information object containing at least:

```text
last_event_identity
last_observed_main_HEAD/TREE
last_observed_PR_HEAD/TREE map
last_observed_workflow terminal states
last_observed_branch disposition state
last_DOD_vector
```

A resumed invocation starts AFTER this cursor. It MUST NOT redraw the complete state unless explicitly requested or reconstruction is necessary after cursor invalidation.

## Append-only output semantics

Each emitted record is a delta, not a replacement snapshot:

```text
TIMESTAMP  TYPE       SUBJECT              TRANSITION / EVIDENCE
          MUTATION   PR#N                  old_HEAD -> new_HEAD
          PASS       exact HEAD/TREE       newly satisfied gate
          BLOCK      exact HEAD/TREE       first causal blocker
          EFFECT     exact subject         fresh effect readback
          DOD        final Main            changed D.o.D. component
```

Visual vocabulary MAY use color, but textual TYPE is mandatory:

- GREEN / PASS
- YELLOW / ACTIVE
- RED / BLOCK
- BLUE / EVIDENCE or MUTATION
- PURPLE / EFFECT
- WHITE / NOT_ADMISSIBLE

Color is never the sole information carrier.

## Execution loop

```text
CURSOR := persisted_cursor

LOOP:
  OBSERVE events strictly after CURSOR
  if material event exists:
      EMIT delta only
      BIND exact subject HEAD/TREE
      CLASSIFY evidence and admissibility
      EXECUTE admissible repository-native consequence when available
      READBACK resulting effect/state
      MATERIALIZE resulting receipt/evidence
      ADVANCE CURSOR
      CONTINUE LOOP immediately
  else:
      END current synchronous invocation at EVENT_GATE

STOP permanently only if QIKVRT_DOD == DONE
```

A chat transport may terminate an invocation when no further event is presently observable. That transport boundary MUST NOT be represented as completion, NOOP, or a repository halt. The next invocation resumes after the persisted cursor.

## Event-driven rule

`tail -f` MUST NOT be implemented by an asynchronous scheduled substitute. Repository-native systems may generate asynchronous events, but the terminal consumes causal events synchronously when invoked and advances from event to event.

No repeated unchanged-state output is useful evidence. An unchanged observation MAY be recorded only when a contract explicitly requires fresh negative readback or freshness proof.

## Evidence boundaries

```text
PREDECESSOR_EVIDENCE_TRANSFER = false
reachable != observed != valid != proved != effect
route != evidence
SUCCESS != EFFECT
```

HEAD/TREE mutation resets every mutation-dependent validation component.

Relations, routes, cursors and routing decisions are addressable information objects. Routing shortcuts preserve the complete underlying provenance path; they never compress, fabricate, or transitively manufacture evidence.

## D.o.D. vector

The cursor tracks changes to:

```text
ZERO_BUGS
ALL_PULL_REQUESTS_REGARDED
ALL_BRANCHES_REGARDED
ALL_PRODUCTIVE_BRANCHES_MERGED
MAIN_EXACT_VALIDATION
EFFECT_READBACK
```

The tail emits a DOD record only when one of these components changes.

`D.o.D. == DONE` is admissible iff all components are freshly true together for the same final Main HEAD/TREE and no subject mutation occurred between their required observations.

Unresolved productive work excludes NOOP.

## Continuous improvement

The tail itself is subject to evidence-driven improvement. New versions may improve event compression, human readability, proof-state visualization, routing visualization, accessibility, latency, machine-readable projections, cursor recovery, and causal prioritization.

Improvements MUST NOT regress:

- append-only evidence history;
- exact-subject binding;
- persistent cursor semantics;
- provenance reconstruction;
- accessibility;
- repository-native autonomy;
- fail-closed behavior;
- historical-evidence/current-admissibility separation;
- routing/evidence separation;
- SUCCESS/EFFECT separation;
- QIKVRT_DOD.

Presentation optimization changes distance to information, never the evidence required to justify it.
