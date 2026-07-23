# Verification report — QIK-VRT manuscript formalization v2.0

Verification date: 2026-07-23  
Status: partial formalization with explicit boundaries

## Locked manuscript

- TeX SHA-256: `c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf`
- PDF SHA-256: `b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f`
- Physical PDF pages: 62

## Verified coverage

- formal LaTeX environments inventoried: 40 / 40
- theorem-like environments inventoried: 20 / 20
- definitions inventoried: 20 / 20
- explicit proof blocks attached: 17 / 17
- appendix matrix rows epistemically classified: 34 / 34
- kernel-checked atomic claim bindings: 12
- complete source-claim bindings: 9, covering 10 / 20 theorem-like environments
- checked source subclaims with pending parents: 3
- pending aggregate theorem claims: 10
- pending definition bindings: 20

## Checks passed

- locked-source and 62-page verification
- deterministic TeX inventory regeneration
- deterministic human proof-map regeneration
- source-span, SHA-256, graph-ID, cycle and epistemic-promotion validation
- 17 positive and negative Python tests
- full Lean 4.19.0 `lake build`
- unified `#print axioms` audit for all 12 checked theorem constants
- comment-aware lexical escape scan and Lean `-E hasSorry` over 23 Lean files

The axiom allowlist is limited to Lean/Std foundations `propext`,
`Classical.choice` and `Quot.sound`. No project axiom, `sorry`, `admit` or
`constant` declaration is accepted.

## Completion boundary

The checked subclaims `QUA-003A`, `DIM-006A` and `DIM-007A` do not discharge
their aggregate manuscript parents. The generated `MANUSCRIPT_PROOF_MAP.md`
lists every remaining obligation. No empirical, interpretive or normative
claim is promoted to a mathematical theorem.
