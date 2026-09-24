# TEMDD interoperability by executable proof v1

Status: normative conformance extension.
Authority repository: Goldkelch/qik-vrt.
Predecessor evidence transfer: DENY.

## Normative equation

```text
MACHINE_VERIFIABLE_STANDARD
and CANONICAL_SERIALIZATION
and DETERMINISTIC_EVALUATION
and CONFORMANCE_VECTORS
and INDEPENDENT_IMPLEMENTATIONS
and IDENTICAL_EXPECTED_DECISIONS
= INTEROPERABILITY_BY_EXECUTABLE_PROOF
```

Agreement between implementations is necessary but not sufficient. Two
implementations can reproduce the same defect. Every required vector therefore
MUST bind a normative `expected_decision`, and every implementation MUST match
that decision independently.

## Canonical serialization

The mandatory profile is `temdd_canonical_json_v1`.

A conforming serializer MUST:

- accept only JSON null, booleans, strings, arrays, objects and integers in the
  JavaScript safe-integer interval [-9007199254740991, 9007199254740991];
- reject floating-point values;
- require ASCII object keys matching `^[A-Za-z0-9_.:-]+$`;
- reject unpaired UTF-16 surrogate code points;
- sort object keys lexicographically;
- emit no insignificant whitespace;
- emit strings as JSON strings without ASCII-forcing;
- emit UTF-8 bytes without a BOM.

The conformance vectors contain the complete expected canonical serialization.
A digest match alone is not used as the oracle.

## Deterministic evaluation

The mandatory semantics identifier is `temdd_decision_v1`.

The input model binds exactly these semantic domains:

```text
INPUT =
    DATA
  and POLICY
  and SUBJECT
  and EVIDENCE
```

The policy contains `data_equals`, `required_evidence_types`, and the exact
`evaluation_semantics` identifier.

Evaluation is deterministic:

1. a data predicate mismatch returns `REJECT`;
2. a missing or non-unique required evidence type returns `HOLD_UNVERIFIED`;
3. stale evidence or evidence bound to a different subject returns
   `HOLD_UNVERIFIED`;
4. a fresh exact-subject evidence assertion of `false` returns `REJECT`;
5. only complete, fresh, exact-subject, true required evidence returns `ACCEPT`.

The decision domain is exactly:

```text
ACCEPT | REJECT | HOLD_UNVERIFIED
```

## Executable proof obligation

For every required conformance vector V and every required implementation I:

```text
Canonicalize_I(Input(V)) = ExpectedCanonical(V)
and Evaluate_I(Input(V)) = ExpectedDecision(V)
```

For the required implementation set I1..In:

```text
forall V:
    Canonicalize_I1(Input(V))
  = ...
  = Canonicalize_In(Input(V))
  = ExpectedCanonical(V)

and

    Evaluate_I1(Input(V))
  = ...
  = Evaluate_In(Input(V))
  = ExpectedDecision(V)
```

Only then may the bounded conformance result be
`INTEROPERABILITY_BY_EXECUTABLE_PROOF`.

`Decision_I1 = Decision_I2` by itself MUST NOT be treated as conformance.

## Required independent execution

This repository requires two separately implemented evaluators for this proof:

- `conformance/temdd/interop_impl_python.py`;
- `conformance/temdd/interop_impl_node.js`.

They execute in distinct runtime processes and do not import one another.
This establishes implementation-path/runtime independence for the executable
test. It does not claim independent authorship, organization, governance, or
security review.

The implementation set MAY be expanded. Removing one of the two required
runtime classes invalidates this v1 proof.

## Exact-subject and effect boundary

The proof report MUST bind repository, exact HEAD and exact TREE. Any mutation
creates a successor subject and requires a fresh proof.

```text
INTEROPERABILITY_BY_EXECUTABLE_PROOF
!= NATIVE_REVIEW
!= PROTECTED_MAIN
!= DEPLOYMENT
!= EFFECT_ACK_DONE
```

The proof runner MUST emit `effect_ack_done=false`.
