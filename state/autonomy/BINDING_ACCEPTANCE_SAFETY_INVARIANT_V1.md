# Binding / Acceptance Safety Invariant — Canonical Instance v1

Author: Ingolf Lohmann
Status: normative repository candidate

## Normative language

The key words **MUSS (MUST)**, **DARF NICHT (MUST NOT)**, **ERFORDERLICH (REQUIRED)**, **SOLLTE (SHOULD)** and **KANN (MAY)** are to be interpreted as described in BCP 14, RFC 2119 and RFC 8174, if and only if they appear in the explicitly normative uppercase form used here.

## 1. Canonical ABNF

The canonical instance syntax MUST conform to RFC 5234 as updated by RFC 7405. All fixed literals below are case-sensitive.

```abnf
binding-acceptance =
  %s"artifact" SP filename SP algorithm SP digest SP scope CRLF
  %s"acceptance" SP byte-id 7(SP boolean) SP status CRLF

filename  = %s"NDR_DSN_ACCEPTANCE_DELTA_V1(1).json"
algorithm = %s"sha256"
digest    = %s"936686c7b6c1e249e8b31215d5111b76"
            %s"a78e494d0ea822a505bd309f946e278e"
scope     = %s"EXACT_FILE_BYTES"

byte-id   = %s"VERIFIED" / %s"NOT_VERIFIED" / %s"UNKNOWN"
boolean   = %s"true" / %s"false"
status    = %s"OPEN" / %s"ACCEPTED"
```

The seven booleans MUST be interpreted, in order, as:
1. requirements_approved
2. acceptance_tests_executed
3. end_to_end_validated
4. communication_effect_ack_done
5. same_subject_binding
6. current_evidence
7. no_contradictory_required_evidence

## 2. Validation layers

A conforming validator MUST distinguish four outcomes:

```text
ABNF_REJECT
BINDING_REJECT
SEMANTIC_REJECT
VALID
```

ABNF_REJECT means the record does not match the canonical grammar.

BINDING_REJECT means the record matches the grammar, but validation against the actual artifact bytes or exact subject cannot establish the asserted binding. This includes missing/unreadable bytes, SHA-256 mismatch, subject mismatch, or a byte-id assertion inconsistent with the completed byte comparison.

SEMANTIC_REJECT means syntax and binding are established but the status violates the Acceptance invariant.

VALID means syntax, artifact binding, exact-subject binding and semantic invariants all hold.

No lower layer MAY substitute evidence for a higher layer.

## 3. Byte identity

Let:

```text
D_actual = SHA256(actual artifact bytes)
D_bound  = 936686c7b6c1e249e8b31215d5111b76a78e494d0ea822a505bd309f946e278e
```

When a reliable comparison completes:
- D_actual = D_bound => byte-id MUST be VERIFIED.
- D_actual != D_bound => byte-id MUST be NOT_VERIFIED and validation MUST NOT yield VALID.
- If comparison cannot reliably complete, byte-id MUST be UNKNOWN and validation MUST NOT yield VALID.

The filename alone MUST NOT establish byte identity. Parsing the bound digest literal MUST NOT establish byte identity.

## 4. Acceptance invariant

```text
ACCEPTED iff
    byte-id = VERIFIED
    AND requirements_approved
    AND acceptance_tests_executed
    AND end_to_end_validated
    AND communication_effect_ack_done
    AND same_subject_binding
    AND current_evidence
    AND no_contradictory_required_evidence
```

Therefore:

```text
VERIFIED does NOT imply ACCEPTED
```

If any required condition is false, unknown, stale, contradictory, or not bound to the same subject, status MUST be OPEN.

A fully true conjunction with status OPEN is SEMANTIC_REJECT under this bidirectional rule. If a deployment requires an additional manual approval, that approval MUST be modeled as another explicit Acceptance predicate rather than hidden outside the state model.

## 5. Bound instance

```text
artifact NDR_DSN_ACCEPTANCE_DELTA_V1(1).json sha256 936686c7b6c1e249e8b31215d5111b76a78e494d0ea822a505bd309f946e278e EXACT_FILE_BYTES
acceptance VERIFIED false false false false false false true OPEN
```

This record asserts the canonical byte-identity state and an OPEN Acceptance state. The VERIFIED assertion is valid only when independently recomputed from the actual artifact bytes. It MUST NOT be promoted to Acceptance.

## 6. Mandatory negative classes

A conformance suite MUST cover at least:
- wrong filename, algorithm, digest literal, scope, byte-id token, boolean count/value, status, or case => ABNF_REJECT;
- canonical record with unavailable/mismatching bytes, mismatching exact subject, or inconsistent byte-id => BINDING_REJECT;
- VERIFIED plus any false Acceptance predicate plus ACCEPTED => SEMANTIC_REJECT;
- NOT_VERIFIED or UNKNOWN plus ACCEPTED => SEMANTIC_REJECT;
- missing same-subject binding, stale evidence, or contradictory required evidence plus ACCEPTED => SEMANTIC_REJECT;
- complete conjunction plus OPEN => SEMANTIC_REJECT;
- canonical bytes, exact subject, consistent byte-id and status matching the complete conjunction => VALID.

## 7. Safety property

```text
SyntaxValid != ByteIdentityVerified
ByteIdentityVerified != EffectVerified
EffectVerified != Acceptance

HashPass MUST NOT open the Acceptance gate by itself.
```

This is an instance-specific safety contract, not a generic artifact grammar.

## References

- BCP 14 / RFC 2119, Key words for use in RFCs to Indicate Requirement Levels.
- RFC 8174, Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words.
- RFC 5234, Augmented BNF for Syntax Specifications: ABNF.
- RFC 7405, Case-Sensitive String Support in ABNF.
