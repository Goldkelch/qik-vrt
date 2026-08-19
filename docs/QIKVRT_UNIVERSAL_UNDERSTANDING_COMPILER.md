# QIK-VRT Universal Understanding Compiler Language V1

## 1. Purpose

This language turns a human- or machine-authored semantic statement into a bounded, machine-checkable decision plan without conflating description, authority, evidence, causality, sequence, execution, observation, or acknowledgement.

Its universal claim is structural: the same source form can describe different domains as long as each domain provides explicit identity, version/state binding, authority, evidence, state, effect, next action, proof, and causal predecessor information. It is not an empirical claim that every phenomenon, every mind, or the physical universe is completely modeled.

The semantic invariant remains:

```text
MEANING = INTENT + BINDING + AUTHORITY + EVIDENCE + STATE + EFFECT + PROOF
```

The minimal formal distinction calculus carried by every validated plan is:

```text
1 - 0 = 1
1 - 1 = 0
x = y
z = 0
x = 1
y = 1
```

Its compiler-level interpretation is deliberately typed:

- `1 - 0 = 1` is the canonical preserved-difference identity.
- `1 - 1 = 0` is the canonical eliminated-difference identity for equal bound values.
- `x = y` is a relation/equality only inside an explicitly bound domain.
- `z = 0` is a distinguished formal zero result; it is not automatically `NOOP`, absence of physical effect, or absence of authority.
- `x = 1` and `y = 1` witness one assignment satisfying `x = y`.

The operational semantic chain is:

```text
DISTINCTION
-> RELATION
-> BINDING / CONTEXT
-> AUTHORITY
-> CAUSAL_ORDER
-> PERMITTED_EFFECT_OR_FAIL_CLOSED
-> REOBSERVATION
-> PROOF
```

The following type boundaries are normative:

```text
DISTINCTION != RELATION
RELATION != CAUSALITY
CAUSALITY != SEQUENCE
ZERO_RESULT != NO_EFFECT
FORMAL_DISTINCTION_CALCULUS != EMPIRICAL_QUANTUM_CAUSALITY
ARITHMETIC_IDENTITY != PHYSICAL_LAW
```

Thus the calculus is a formal semantic kernel. A physical interpretation such as "Quantenkausalitaet" requires a separately specified empirical model and evidence boundary; the compiler does not manufacture that bridge.

The central ordering rule remains:

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

The distinction calculus is a language invariant rather than a per-message user-supplied field. This prevents a source message from redefining the semantic kernel while keeping the source form domain-neutral.

## 3. Universal frontend versus target profile

The frontend accepts subject schemes as opaque identifiers and therefore remains domain-neutral. A backend may impose stricter constraints.

The QIK-VRT Atari Mega ST target profile is intentionally narrow:

```text
SUBJECT scheme      = repo
SUBJECT identity    = owner/repository
SUBJECT version     = exact 40-hex HEAD
SUBJECT state       = exact 40-hex root TREE
NEXT                = NOOP | HOLD | REOBSERVE | REQUEST_AUTHORITY
```

Only this bounded decision surface is lowered to the existing M68000 capsule ABI:

```text
NOOP               -> MOVEQ #0,D0 ; RTS
HOLD               -> MOVEQ #1,D0 ; RTS
REOBSERVE          -> MOVEQ #2,D0 ; RTS
REQUEST_AUTHORITY  -> MOVEQ #3,D0 ; RTS
```

An unsupported productive target action is rejected before binary emission. The backend never turns an unknown or unsupported action into an optimistic machine effect. The formal zero result `z = 0` never aliases the runtime `NOOP` code merely because both contain a zero symbol.

## 4. Fail-closed semantic rules

The ANSI-C frontend enforces at least these invariants:

1. Productive intent (`EXECUTE`, `CREATE`, `UPDATE`, `CLOSE`, `DISPATCH`, `PERSIST`) requires `AUTH BOUND ...`.
2. `STATE UNKNOWN` cannot drive productive intent.
3. Non-bound authority permits only `HOLD`, `NOOP`, `REOBSERVE`, or `REQUEST_AUTHORITY` as the next action.
4. `EFFECT ACKNOWLEDGED ...` requires `KIND ACK`.
5. `PROOF` and evidence digests are exactly 64 lowercase hexadecimal characters.
6. A unit cannot name itself as its own causal predecessor.
7. Distinction, relation, causal dependence and serialization remain separate semantic types.
8. A formal zero result does not imply no effect or no authority.
9. In Mega-ST target mode, repository HEAD/TREE binding must be exact 40-lowercase-hex values.
10. In Mega-ST target mode, only the four bounded nonproductive decision actions may reach the existing lowerer/emitter.

## 5. Compiler pipeline

The repository-native pipeline is:

```text
QIKU1 source
  -> strict ANSI-C89 universal frontend
  -> validated plan carrying the distinction-kernel invariants
  -> existing QIK-VRT M68000 lowerer
  -> existing minimal M68000 emitter
  -> deterministic decision bytes
  -> existing Mega-ST TOS wrapper / capsule
  -> virtualized exact-head observation when the dedicated gate executes
```

The frontend emits a textual plan containing `DISTINCTION_KERNEL=`, `SEMANTIC_CHAIN=`, `ZERO_RESULT_SEMANTICS=`, `NEXT_ACTION=` and `ADMISSION=VALIDATED`. This intentionally reuses the already implemented fail-closed M68000 lowerer instead of introducing a second target semantics. The lowerer consumes only its bounded action contract; the additional semantic lines remain audit evidence and do not widen the four-action ABI.

## 6. Causality and composition

A single QIKU1 unit names at most one immediate predecessor in V1. Multiple units are composed by the existing causal-IR scheduler. The scheduler derives a deterministic topological serialization from explicit dependency edges. Lexical order is only an input presentation order and has no causal meaning.

Therefore:

```text
SOURCE_ORDER != CAUSAL_ORDER
CAUSAL_ORDER != WALL_CLOCK_ORDER
SERIALIZATION IN TOPOLOGICAL_SORTS(CAUSAL_GRAPH)
```

The distinction calculus does not create graph edges. A relation does not become a causal dependency until an explicit causal binding establishes that dependency.

## 7. Atari Mega ST boundary

The target is the QIK-VRT reference profile already defined for the Atari Mega ST / Motorola 68000 path. The new frontend does not widen hardware authority. It only supplies a universal source-language layer above the existing bounded ABI.

No claim is made here about execution on physical Mega-ST hardware, measured performance, deployment, publication, release, review approval, empirical quantum causality, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`. Those remain separately evidenced gates.
