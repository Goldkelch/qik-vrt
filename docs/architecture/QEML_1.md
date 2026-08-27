# QIK-VRT Event Model Language (QEML-1)

## Purpose

QEML-1 is the human-facing executable language for Event Model Driven
Development in QIK-VRT. Regular expressions recognize lexical forms; they do
not define the model semantics.

```text
REGEX TOKEN RULES
-> LEXER
-> HUMAN-READABLE GRAMMAR
-> TYPED EVENT MODEL AST
-> CANONICAL EVENT IR
-> EXECUTABLE TEST ORACLES
-> ANSI C89 REFERENCE RUNTIME
-> TARGET BACKEND
-> EXACT RECEIPT
```

A QEML unit binds admitted events, state transitions, guards, capabilities,
invariants, tests, requested effects, observers, receipts, and target/ABI
constraints. Unsupported or ambiguous semantics fail closed before candidate
execution.

## First supported grammar

```ebnf
model       = "modell", identifier ;
state       = "zustand", identifier, "=", identifier, { "|", identifier } ;
event       = "event", identifier, "(", [ field, { ",", field } ], ")" ;
field       = identifier, ":", identifier ;
rule        = "regel", identifier, NEWLINE,
              INDENT, "bei", identifier, NEWLINE,
              INDENT, "wenn", expression, NEWLINE,
              INDENT, "dann", identifier, ":", identifier, "->", identifier,
              [ NEWLINE, INDENT, "effect", identifier ],
              NEWLINE, INDENT, "beobachte", identifier ;
invariant   = "invariante", identifier, NEWLINE, INDENT, expression ;
test        = "test", identifier, NEWLINE,
              { INDENT, "gegeben", identifier, "=", scalar, NEWLINE },
              INDENT, "wenn", identifier, NEWLINE,
              INDENT, "dann", expectation ;
effect      = "effect", identifier, attribute, { attribute } ;
target      = "target", identifier, attribute, { attribute } ;
attribute   = identifier, "=", scalar ;
```

The concrete parser is deliberately strict. Unknown events, states, effects,
targets, duplicate names, incomplete effect contracts, incomplete ABI
descriptors, and nondeterministic transitions are typed compilation errors.

## Event Model Driven Development

Every `test` and `invariante` clause belongs to the executable model. The first
tranche emits deterministic test oracles for the implemented subset. A clause
that cannot be compiled is rejected; it is never treated as silently true.

The reference Heartbeat model preserves:

```text
HEARTBEAT != POLLING != BLIND_RETRY
CONTINUE != PASS != FAILURE
0 -> Terminal -> at most 8 workers
9th worker -> HOLD worker_limit_exceeded
```

## Canonical Event IR

The canonical IR is architecture-neutral, sorted, serializable JSON with the
schema `QEML_EVENT_IR_V1`. Its byte representation is the compact canonical
JSON encoding plus one newline. Source, canonical source, IR, C89, target
assembly, machine code, and receipt are separately SHA-256 bound.

## Outer C89, inner target core

The portable envelope is strict ANSI C89 and carries the event dispatcher,
typed status values, capability boundaries, deterministic reduction, and
receipt-facing state. The first target core emits the exact M68000 encoding:

```text
MOVEQ #status,D0
RTS
```

The primitive is executed by a bounded instruction emulator in the first
tranche. This establishes emulated target machine-code execution only. It does
not establish physical Mega-ST or physical M68000 execution.

## Bootstrap and self-application boundary

The compiler-core model is compiled twice: original source to canonical source,
then canonical source through the same implemented subset. Canonical source,
IR, C89, and M68000 primitive must reach a byte-identical fixed point.

This is a supported-subset bootstrap fixed point. It is not yet a claim that
the entire QEML compiler is self-hosted. Full self-hosting additionally
requires a strict C89 Stage-0 compiler/interpreter, a Stage-1 compiler produced
from the QEML compiler core, Stage-2 production by Stage-1, and exact semantic
trace equivalence on the same candidate head.

## Fail-closed non-claims

```text
QEML_IMPLEMENTED_ON_MAIN = false until merged and reobserved
SELF_HOSTING_OBSERVED = false
PHYSICAL_MEGAST_EXECUTION = false
FUTURE_HARDWARE_SUPPORT_OBSERVED = false
GENERAL_EFFECT_ACK_DONE = false
PASS = false
FINAL_PASS = false
PUBLICATION = false
DEPLOYMENT = false
```
