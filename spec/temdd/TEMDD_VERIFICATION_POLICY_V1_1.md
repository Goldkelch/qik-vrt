# TEMDD 1.1 Verification Policy Semantics

Status: `RC1_NORMATIVE_POLICY_CANDIDATE`

## Meta-Axiom

`Verification SHALL be policy-driven, not implementation-defined.`

JSON Schema defines serializable structure. Runtime predicates remain normative evaluator semantics and MUST NOT be inferred from schema validation alone.

## Deterministic evaluation input

A verification decision is a pure function of the complete bound input:

`Decision = Evaluate(Transaction, EvidenceSet, Policy, VerificationContext)`

The VerificationContext MUST bind evaluation time, trust-root set, algorithm profile, canonicalization profile and acceptance evaluator identities. Two conforming implementations receiving byte-equivalent canonical inputs MUST return the same predicate vector and terminal/non-terminal verification result.

## Fresh

For evidence E and context V:

`Fresh(E) iff 0 <= V.evaluationTime - E.capturedAt <= Policy.freshness.maxAgeSeconds`

If `requireAfterExecution=true`, E MUST be temporally compatible with the bound execution after applying only the declared `maxClockSkewSeconds`. Timestamp order alone does not establish causality.

## Trusted

`Trusted(E)` requires the evidence class to meet the declared minimum, the source to satisfy the declared source/trust-root rules, and — where required — a valid signature under an allowed algorithm and key binding.

Evidence classes are ordered only for the class predicate: `E3 > E2 > E1`. A higher class does not create quorum or independence automatically.

## Bound

Binding predicates are evaluated independently:

- subject identity;
- transaction identity;
- execution identity;
- challenge/nonce identity where required.

A mismatch MUST fail the binding predicate. Predecessor evidence MUST NOT be rebound to a mutated successor.

## Quorum

The quorum requirement MUST be fixed before EXECUTE.

Supported modes are `NONE`, `SINGLE`, `K_OF_N`, `MAJORITY`, `TWO_THIRDS` and `ALL`. A source may count at most once. Evidence that fails Fresh, Trusted or Bound MUST NOT count toward quorum.

## Evaluation order and result

The normative predicate vector is emitted in this order:

`FRESHNESS -> TRUST -> BINDING -> QUORUM -> DOMAIN_VERIFICATION -> ACCEPTANCE`

The overall verification result is conjunction, never incremental terminal success.

`VERIFIED = all(required predicates == true)`

`EFFECT_ACK_DONE` still additionally requires the transaction's explicit acceptance transition and all other TEMDD_SUCCESS predicates. A successful policy evaluation is therefore not itself EFFECT_ACK_DONE.

## Serialization

Policy and verification-context hashes use RFC 8785 JSON Canonicalization Scheme and SHA-256 in the 1.1 Core profile unless a later version explicitly defines another mandatory profile.

## Failure semantics

Missing required inputs fail closed. Stale evidence is rejected as evidence for the current evaluation; obtaining a new observation/readback creates fresh evidence rather than making stale bytes trustworthy through retry.

q.e.d.  
Ingolf Lohmann
