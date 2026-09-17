# QIK-VRT Intelligence Development Environment Framework V1

The framework projects one exact repository event through four independent language perspectives and fuses only freshly bound evidence into a new candidate.

## Common subject

Every request and receipt binds `repository + HEAD + TREE + input digest + metagrammar digest`. A perspective may not inherit current validity from another perspective or predecessor.

## REST surface

```text
/qik-vrt/ide/v1
  /subject
  /metagrammar
  /python
    /observe /validate /test /analyze /materialize /receipt
  /c90
    /observe /validate /compile /test /execute /receipt
  /smalltalk
    /observe /inspect /reflect /adapt /test /receipt
  /m68k
    /capabilities /vectors /execute /benchmark /receipt
  /fusion
    /observe /conflicts /candidate /receipt
  /live
  /effect-ack
```

Python exposes semantic/tooling orchestration. C90 exposes the portable deterministic core. Smalltalk exposes the persistent object/event/reflection perspective. Motorola 68000 assembler exposes a deliberately bounded static REST projection for high-performance machine-state primitives; its API describes a fixed admitted operation vocabulary rather than arbitrary remote machine-code execution.

## Perspective semantics

All four perspectives consume the same exact subject but execute independently. Their output is a language-neutral receipt containing assertions, counterexamples, artifact digests and an explicit effect boundary. Disagreement is evidence.

Fusion is not voting. Counterevidence cannot be overridden by a majority. A conflict remains `HOLD_UNVERIFIED` until resolved by a new evidence-producing mutation. Successful fusion creates a new candidate only; it is not Main integration and not EFFECT.

## CI closure

The complete CI target is:

```text
exact event
  -> metagrammar validation
  -> Python perspective
  -> C90 perspective
  -> Smalltalk perspective
  -> M68K perspective
  -> receipt cross-validation
  -> conflict/fusion validation
  -> candidate
  -> complete make test
  -> exact-head readback
```

Each perspective is required to have a deterministic toolchain admission, repository-native tests, cache/registry coverage where applicable, and a real runtime/compile witness. Smalltalk is not considered implemented merely because this contract exists: its runtime, bootstrap, tests and API carrier must be materialized and admitted before the four-perspective gate can pass.

## Intelligence Development Environment

The environment is an evidence-producing development framework rather than a conventional editor. Human, browser, Mesh and machine clients can address the same exact information through different computational perspectives. Validated fusion may become the next common Main basis while historical perspective receipts remain reconstructible.
