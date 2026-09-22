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

SP and CRLF are the core rules from RFC 5234 Appendix B.1. The wire encoding
is US-ASCII: SP is one octet 0x20 and CRLF is the two octets 0x0D 0x0A.
Both lines, including the last, MUST end with CRLF. A parser MUST consume the
entire record and MUST NOT normalize whitespace, case, line endings or a BOM.
Presentation wrapping in this Markdown file is not wire folding.

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

The final outcome MUST use this precedence, stopping at the first failing layer:

```text
syntax -> actual-byte binding -> state and evidence consistency -> VALID
```

ABNF_REJECT means the complete record does not match the canonical grammar.

BINDING_REJECT means syntax is valid but actual bytes are unavailable, unsafe to
read, mismatching, or inconsistent with the record's asserted byte-id. The
expected artifact is the exact digest-bound object; a filename or digest printed
in the record MUST NOT substitute for reading that object.

SEMANTIC_REJECT means byte binding is verified but the claimed status does not
match the conjunction, or the seven flags do not match independently assessed
evidence. Application-level same_subject_binding is one of those seven predicates,
not a prerequisite for truthfully reporting an OPEN state.

VALID means the record is a consistent, byte-bound report. VALID with status OPEN
is permitted and MUST NOT authorize Acceptance. VALID is not synonymous with
ACCEPTED. An honestly negative or unknown byte-binding report may be retained as
such, but the full validator returns BINDING_REJECT, not VALID.

When several layers fail, the earlier failure MUST determine the final outcome.
For example, NOT_VERIFIED or UNKNOWN plus ACCEPTED violates the pure state rule,
but a full validation returns BINDING_REJECT first. Isolated state-rule tests MAY
report the semantic violation separately; they MUST NOT call it a complete binding
validation. Evidence from a lower layer MUST NOT substitute for evidence required
by a higher layer.

## 2.1. Evidence input and UNKNOWN projection

The record contains assertions, not self-authenticating proofs. The validator MUST
compare every flag with an independently obtained evidence assessment. The
assessment producer MUST establish origin, authority, policy, freshness, scope,
subject binding and contradiction coverage before returning true. Copying flags
from the record into its own evidence input is forbidden.

Each assessed predicate has one of three values: true, false or unknown. Wire true
means established true. False or unknown, including a missing assessment, MUST map
to wire false. Thus wire false means not established true, not necessarily that an
external effect did not occur. Detailed reasons MUST remain in the evidence ledger.
A flag that disagrees with this projection MUST cause SEMANTIC_REJECT. In particular,
no_contradictory_required_evidence MUST NOT default to true merely because no
contradiction was observed; the required evidence set must have been assessed.

This pure validator does not authenticate the assessment producer, consult a clock,
inspect remote systems or discover evidence by itself. A deployment MUST supply
that trusted boundary. Untrusted dictionaries MUST NOT be treated as verified
evidence. The standalone CLI supplies no affirmative assessments and cannot grant
ACCEPTED. It does not execute effects.

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

This is an asserted example, not a fresh execution receipt. Its VERIFIED assertion
requires an actual successful digest comparison; its last true flag additionally
requires assessed contradiction coverage. Without the original artifact bytes,
full validation returns BINDING_REJECT. This document does not assert that the
artifact is available or independently reverified in any particular execution.

## 6. Mandatory negative classes

A conformance suite MUST cover at least:
- wrong filename, algorithm, digest literal, scope, byte-id token, boolean count/value,
  status, case, whitespace, CRLF framing, BOM or trailing data => ABNF_REJECT;
- canonical syntax with unavailable/mismatching bytes or inconsistent byte-id =>
  BINDING_REJECT, even if its asserted Acceptance state is also inconsistent;
- verified actual bytes and VERIFIED plus any false predicate plus ACCEPTED =>
  SEMANTIC_REJECT;
- verified actual bytes and a complete true conjunction plus OPEN => SEMANTIC_REJECT;
- verified actual bytes and flags not supported by their assessed evidence =>
  SEMANTIC_REJECT;
- verified actual bytes, flags equal to assessed evidence and matching OPEN status =>
  VALID, accepted=false;
- verified actual bytes, all seven independently assessed predicates true and
  matching ACCEPTED status => VALID, accepted=true.

The isolated projection suite MUST cover all 768 combinations of three byte-id
values, 128 seven-boolean vectors and two status values. These finite model tests
are not evidence that any real communication, approval or End-to-End effect occurred.

## 7. Safety property

```text
SyntaxValid != ByteIdentityVerified
ByteIdentityVerified != EffectVerified
EffectVerified != Acceptance

HashPass MUST NOT open the Acceptance gate by itself.
```

This is an instance-specific safety contract, not a generic artifact grammar.

## 8. Executable reference and scope

The fixed-profile reference is `tools/qikvrt_binding_acceptance.py`. Regression tests
are `tests/test_qikvrt_binding_acceptance.py`, included in the existing
`repository-writer-contract` target of `make test`.

The CLI accepts `--record` and `--artifact`. Exit 0 means record VALID, not
Acceptance; callers MUST inspect the explicit accepted field and evidence boundary.
There is no CLI evidence override. The Python API's evidence mapping must come from
the trusted assessment producer specified above.

The tests use separate fixture bytes and a private fixture profile for positive
binding tests. They do not relabel fixture hashes as the canonical artifact hash.
Installing this module does not establish deployment at every Mesh node, implement
node admission, submit an IETF document or publish a Zenodo record.

## References

- BCP 14 / RFC 2119, Key words for use in RFCs to Indicate Requirement Levels.
- RFC 8174, Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words.
- RFC 5234, Augmented BNF for Syntax Specifications: ABNF.
- RFC 7405, Case-Sensitive String Support in ABNF.
