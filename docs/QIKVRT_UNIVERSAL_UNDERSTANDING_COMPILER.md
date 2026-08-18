# QIK-VRT Universal Understanding Compiler Language V1

## 1. Purpose

This language turns a human- or machine-authored semantic statement into a bounded, machine-checkable decision plan without conflating description, authority, evidence, causality, sequence, execution, observation, or acknowledgement.

Its universal claim is structural: the same source form can describe different domains as long as each domain provides explicit identity, version/state binding, authority, evidence, state, effect, next action, proof, and causal predecessor information. It is not an empirical claim that every phenomenon, every mind, or the physical universe is completely modeled.

The semantic invariant remains:

```text
MEANING = INTENT + BINDING + AUTHORITY + EVIDENCE + STATE + EFFECT + PROOF
```

and the central ordering rule remains:

```text
CAUSALITY != SEQUENCE
```

Source order has no causal authority. A causal predecessor must be named explicitly.

## 2. Universal source form

A V1 compilation unit contains exactly one semantic event:

```text
QIKU1
KIND OBSERVE
RID r1
SUBJECT repo Goldkelch/qik-vrt aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
INTENT OBSERVE terminal
AUTH BOUND po-1
EVID HEAD cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
STATE OBSERVED
EFFECT NONE none
NEXT REOBSERVE
PROOF dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
CAUSE -
END
```

The fields are deliberately generic:

- `KIND` says what kind of semantic message this is.
- `RID` is the stable event identifier.
- `SUBJECT <scheme> <identity> <version> <state>` binds the event to a subject. The language itself does not require a repository; `repo` is the QIK-VRT repository adapter.
- `INTENT <verb> <object>` states intended processing, not completed effect.
- `AUTH <status> <authority-id>` binds authority.
- `EVID <type> <sha256>` binds evidence bytes or canonical evidence data.
- `STATE <classification>` records the currently derived state.
- `EFFECT <state> <effect-id>` records effect progression.
- `NEXT <action>` is the smallest admitted continuation.
- `PROOF <sha256>` binds the canonical proof/digest input.
- `CAUSE <rid|->` names an explicit predecessor or declares no predecessor.

## 3. Universal frontend versus target profile

The frontend accepts subject schemes as opaque identifiers and therefore remains domain-neutral. A backend may impose stricter constraints.

The QIK-VRT Atari Mega ST target profile is intentionally narrow:

```text
SUBJECT scheme      = repo
SUBJECT identity    = owner/repository
SUBJECT version     = exact 40-hex HEAD
SUBJECT state       = exact 40-hex root TREE
NEXT                 = NOOP | HOLD | REOBSERVE | REQUEST_AUTHORITY
```

Only this bounded decision surface is lowered to the existing M68000 capsule ABI:

```text
NOOP               -> MOVEQ #0,D0 ; RTS
HOLD               -> MOVEQ #1,D0 ; RTS
REOBSERVE          -> MOVEQ #2,D0 ; RTS
REQUEST_AUTHORITY  -> MOVEQ #3,D0 ; RTS
```

An unsupported productive target action is rejected before binary emission. The backend never turns an unknown or unsupported action into an optimistic machine effect.

## 4. Fail-closed semantic rules

The ANSI-C frontend enforces at least these invariants:

1. Productive intent (`EXECUTE`, `CREATE`, `UPDATE`, `CLOSE`, `DISPATCH`, `PERSIST`) requires `AUTH BOUND ...`.
2. `STATE UNKNOWN` cannot drive productive intent.
3. Non-bound authority permits only `HOLD`, `NOOP`, `REOBSERVE`, or `REQUEST_AUTHORITY` as the next action.
4. `EFFECT ACKNOWLEDGED ...` requires `KIND ACK`.
5. `PROOF` and evidence digests are exactly 64 lowercase hexadecimal characters.
6. A unit cannot name itself as its own causal predecessor.
7. In Mega-ST target mode, repository HEAD/TREE binding must be exact 40-lowercase-hex values.
8. In Mega-ST target mode, only the four bounded nonproductive decision actions may reach the existing lowerer/emitter.

## 5. Compiler pipeline

The repository-native pipeline is:

```text
QIKU1 source
  -> strict ANSI-C89 universal frontend
  -> validated plan
  -> existing QIK-VRT M68000 lowerer
  -> existing minimal M68000 emitter
  -> deterministic decision bytes
  -> existing Mega-ST TOS wrapper / capsule
  -> virtualized exact-head observation when the dedicated gate executes
```

The frontend emits a textual plan containing `NEXT_ACTION=` and `ADMISSION=VALIDATED`; this intentionally reuses the already implemented fail-closed M68000 lowerer instead of introducing a second target semantics.

## 6. Causality and composition

A single QIKU1 unit names at most one immediate predecessor in V1. Multiple units are composed by the existing causal-IR scheduler. The scheduler derives a deterministic topological serialization from explicit dependency edges. Lexical order is only an input presentation order and has no causal meaning.

Therefore:

```text
SOURCE_ORDER != CAUSAL_ORDER
CAUSAL_ORDER != WALL_CLOCK_ORDER
SERIALIZATION IN TOPOLOGICAL_SORTS(CAUSAL_GRAPH)
```

## 7. Atari Mega ST boundary

The target is the QIK-VRT reference profile already defined for the Atari Mega ST / Motorola 68000 path. The new frontend does not widen hardware authority. It only supplies a universal source-language layer above the existing bounded ABI.

No claim is made here about execution on physical Mega-ST hardware, measured performance, deployment, publication, release, review approval, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`. Those remain separately evidenced gates.
