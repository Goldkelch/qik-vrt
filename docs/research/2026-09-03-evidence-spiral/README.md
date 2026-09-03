# QIK-VRT evidence spiral: local fixed points, monotone evidence growth

**Author and Product Owner:** Ingolf Lohmann  
**Status:** scientific integration candidate; formal/model claims are separated from empirical claims.

## Purpose

This note integrates the 2026-09-03 low-energy/evidence formulation with the already archived QIK-VRT fixed-point structure and the current publication-control chain.

The central correction is that closure is not best represented as one final ring. A locally closed evidence state can be a fixed point of its declared admissibility/check operator while the global evidence base remains open to monotone extension. The resulting geometry is therefore a spiral: local closure plus globally open continuation.

## 1. Evidence chain

For a distinction `Delta`, relation `R`, state `S`, transition `U`, observation `O`, and reproducible evidence `E`:

```text
Delta -> R(Delta) -> S -> U:S->S' -> O(S,S') -> E
```

A distinction becomes scientifically relevant only after its identity conditions, state role, causal consequence, observation semantics, and reproducibility provenance are bound.

## 2. Finite binary representation theorem

For every finite alphabet `A` there exists an injective encoding

```text
enc : A* -> {0,1}*
```

Hence every finite symbolic evidence record can be represented losslessly by a finite bit string. This is a representation theorem. It does not, by itself, prove that continuous physical ontology, arbitrary real values, or unrestricted quantum states are finite binary objects.

## 3. Existing QIK-VRT fixed-point structure

The archived QIK-VRT fixed-point manuscript states the structural formula

```text
Omega = Fix_N(A(lim_{n->infinity} F^(n)(0->1)))
```

under its declared axioms: a complete metric effect-state space, a contractive recursive effect iteration, a continuous/idempotent connectability/admissibility operator, and the declared stability condition. Within that formal system the result is an axiomatic structure theorem. Its own status boundary remains authoritative: it is not, without additional observation maps, measurements, falsification criteria, and external reproduction, an unconditional empirical proof of all physical reality or quantum gravity.

Known archived artifact binding from the repository publication inventory:

```text
QIKVRT_Fixpunktbeweis_final.pdf
SHA-256 bf6521828db3ea52d67868b1c8ba09b0c0256562f684231df6833b1f68c2d55e
related repository DOI: 10.5281/zenodo.20712301
```

## 4. Local fixed point, globally open spiral

Let `E_n` be the accepted evidence set at stage `n`. Monotone evidence accumulation is an explicit contract, not an automatic consequence of a fixed-point theorem:

```text
E_n subseteq E_(n+1)
E_(n+1) = Closure(E_n union DeltaE_(n+1))
```

A locally closed stage satisfies

```text
A(E_n*) = E_n*
```

but this does not assert that `E_n*` is the final possible state of knowledge. New admissible evidence can create a successor stage `E_(n+1)` while preserving the bytes and proof status of already exact-bound formal artifacts.

Accordingly:

```text
local fixed point + monotone successor construction = evidence spiral
```

New evidence may narrow a theorem's applicability, invalidate an empirical interpretation, or expose a false premise. It does not retroactively alter the bytes of an immutable proof artifact or make a valid derivation under unchanged axioms cease to be a valid derivation.

## 5. Roundtrip condensate

The formal/model-level condensate is

```text
ROUNDTRIP = Fix_N o A o lim_{n->infinity} F^(n) o (0->1)
```

combined with the evidence chain

```text
Delta -> relation -> state -> effect -> observation -> reproducible evidence -> admissibility/reobservation
```

and with successor construction after every locally closed state.

The intended scientific reading is therefore:

> Fundamental is not every imagined microscopic difference, but a difference that becomes relationally defined, state-bearing, causally effective, reproducibly evidenced, and remains admissible under exact reobservation. Closure is local; scientific continuation remains open.

## 6. Low-energy connection

At observational energy `E` relative to a higher scale `M*`, define `epsilon = E/M*`. Effective descriptions organize observable behavior in the regime `epsilon -> 0`. This motivates the observational quotient

```text
W_obs(E) = {admissible microscopic models} / observational_indistinguishability_at_E
```

as an organizing principle. This is scientifically connectable to effective-field-theory and renormalization-group reasoning, but it is not asserted here as an experimentally established Theory of Everything.

## 7. Exact epistemic boundaries

The following implications are forbidden:

```text
finite binary encodability != binary physical ontology
formal theorem != empirical law of nature
tested implementation != physical confirmation
transport ACK != effect ACK
local fixed point != final state of knowledge
repository success != external publication
```

The Planck-Tick Gap Law remains a separately falsifiable physical hypothesis. Its prediction-freezing can be formally and numerically checked while empirical correspondence and independent reproduction remain separate obligations.

## 8. Publication integration order

The current publication chain is intentionally ordered:

```text
#964 proof-status material
        \
corrected #962 scientific source + Zenodo/arXiv packages
          \
#965 ledger, classifier and normalized receipt contracts
            \
this evidence-spiral/fixed-point integration
              |
              v
one reviewed and validated integration head
              |
              v
legitimate promotion to one exact Trusted Main SHA
              |
              v
fresh reobservation of that exact Main SHA
              |
              +-- Wikipedia transparent request -> authoritative readback
              +-- Zenodo publish -> public record/DOI/file-hash readback
              +-- arXiv authenticated submit -> submission/status readback
                                            -> later public-ID/version readback
```

No external delivery is complete merely because this integration note exists. Publication/effect claims require their own authoritative readbacks.

## 9. Machine-oriented invariant

A downstream algorithm should preserve the following state relation:

```text
KNOWN(E_n) subseteq KNOWN(E_(n+1))
```

only for immutable, exact-bound evidence objects whose assumptions and scope remain attached. Contradictory empirical evidence is appended as new evidence and changes the accepted interpretation/status; it is never silently erased to preserve monotonicity.

This is the evidence-sphere invariant: preserve exact prior evidence, append successor evidence, recompute the admissible closure, and bind every conclusion to its scope.
