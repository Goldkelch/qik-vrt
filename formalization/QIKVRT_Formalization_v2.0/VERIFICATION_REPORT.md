# Verification report — QIK-VRT manuscript formalization v2.0

Verification date: 2026-07-24  
Status: formal-environment coverage complete with explicit conditional boundaries

## Locked manuscript

- TeX SHA-256: `c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf`
- PDF SHA-256: `b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f`
- Physical PDF pages: 62

## Completed formal coverage

- formal LaTeX environments inventoried: 40 / 40
- theorem-like environments inventoried: 20 / 20
- definition environments source-bound and kernel-checked: 20 / 20
- theorem-like environments formally closed: 20 / 20
- explicit proof blocks attached: 17 / 17
- appendix matrix rows epistemically classified: 34 / 34
- strong source-bound Lean bindings: 42
- conditional checked bindings: 6
- pending formal definition/theorem nodes: 0

## Verification gates

- immutable TeX/PDF source lock and 62-page verification
- deterministic TeX inventory and claim-graph regeneration
- deterministic human proof-map regeneration
- source-span, SHA-256, graph-ID, dependency-cycle and epistemic-promotion validation
- full Lean 4.19.0 `lake build`
- proposition-indexed claim registry for every formal binding
- unified `#print axioms` audit
- comment-aware proof-escape scan and Lean `-E hasSorry` audit
- positive and negative Python tests
- persistent proof-object manifest and runtime SHA-256 receipts

The axiom allowlist remains limited to Lean/Std foundations `propext`, 
`Classical.choice` and `Quot.sound`. No project axiom, `sorry`, `admit` 
or unchecked `constant` declaration is accepted.

## Conditional proof boundary

- `ESC-004` is `CONDITIONAL_CHECKED`; every additional premise is explicit in `QIKVRT.V2.Completion.ESC004Statement`.
- `ESC-005` is `CONDITIONAL_CHECKED`; every additional premise is explicit in `QIKVRT.V2.Completion.ESC005Statement`.
- `ESC-003` is `CONDITIONAL_CHECKED`; every additional premise is explicit in `QIKVRT.V2.Completion.ESC003Statement`.
- `QUA-004` is `CONDITIONAL_CHECKED`; every additional premise is explicit in `QIKVRT.V2.Completion.QUA004Statement`.
- `QUA-005` is `CONDITIONAL_CHECKED`; every additional premise is explicit in `QIKVRT.V2.Completion.QUA005Statement`.
- `DIM-006` is `CONDITIONAL_CHECKED`; every additional premise is explicit in `QIKVRT.V2.Completion.DIM006Statement`.

## Scientific claim boundary

Completion means that every formal definition and theorem-like manuscript 
environment has a source-bound machine-checkable status. It does not turn 
empirical, interpretive, background, metaphysical, spiritual, retrocausal, 
or quantum-gravitational statements into mathematical theorems. Conditional 
proofs remain conditional, and the repository preserves those assumptions 
rather than suppressing them.
