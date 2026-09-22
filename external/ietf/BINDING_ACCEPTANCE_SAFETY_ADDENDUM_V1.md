# IETF Candidate Addendum — Binding and Acceptance Separation

Author: Ingolf Lohmann
Status: repository candidate; NOT an IETF submission or publication

This addendum is intended for incorporation into a future revision of the QIK-VRT Effect Acknowledgement Internet-Draft. It does not change the published/submitted status of any Internet-Draft.

## Normative language

The key words MUST, MUST NOT, REQUIRED, SHOULD, and MAY in this document are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174) when, and only when, they appear in all capitals.

## Binding and Acceptance are separate gates

A conforming implementation MUST distinguish representation syntax, artifact binding, effect evidence, and Acceptance. Successful validation at a lower layer MUST NOT substitute for evidence required by a higher layer.

For an artifact-bound Acceptance record:

```text
SyntaxValid != ByteIdentityVerified
ByteIdentityVerified != EffectVerified
EffectVerified != Acceptance
```

In particular, successful verification of a content digest proves only the defined byte-identity proposition. It MUST NOT, by itself, authorize downstream effect or open an Acceptance gate.

An implementation that exposes an ACCEPTED state MUST make every predicate required for that state explicit and machine-checkable. Unknown, stale, contradictory, unavailable, or differently bound required evidence MUST fail closed.

## Validator result classes

Where a concrete profile combines a textual grammar with an external artifact, validators SHOULD distinguish at least:

```text
ABNF_REJECT
BINDING_REJECT
SEMANTIC_REJECT
VALID
```

The final result MUST use the order syntax, actual-byte binding, then state and
evidence consistency. ABNF_REJECT identifies invalid syntax. BINDING_REJECT
identifies missing/mismatching actual bytes or an inconsistent byte-id assertion.
SEMANTIC_REJECT identifies a state or evidence-projection error after byte binding
has passed. An earlier rejection takes precedence if multiple layers fail.

VALID denotes a consistent report, not automatically Acceptance. A VALID OPEN
report MUST NOT authorize an effect. Application-level subject binding remains an
explicit Acceptance predicate; a truthful OPEN report can state that it is false.

Every affirmative predicate MUST be backed by independently assessed evidence, not
copied from the submitted record. The assessment producer MUST establish its
origin, authority, policy, subject, freshness and required contradiction coverage.
Unknown or missing assessments project to false, meaning not established true.
The detailed epistemic reason MUST be retained separately. A content hash alone
neither authenticates that producer nor proves these predicates.

## Case-sensitive ABNF

Profiles that require exact case MUST use the RFC 7405 %s form for every fixed literal whose case is normative. Unprefixed ABNF quoted strings are not a substitute for a case-sensitive requirement.

## Concrete QIK-VRT profile

The repository profile `state/autonomy/BINDING_ACCEPTANCE_SAFETY_INVARIANT_V1.md` defines one instance-specific ABNF and negative conformance classes. That profile is informative to this candidate addendum unless incorporated normatively into a future Internet-Draft revision.

## Security consideration

Conflating digest equality with Acceptance creates an authorization-confusion failure: an attacker or faulty component that can reproduce or replay valid bytes may cause a consumer to infer a downstream authorization that the digest never established. Implementations MUST bind authorization to the complete current predicate set and exact subject, not merely to a filename, transport acknowledgement, successful parse, or content hash.

## References to add

Normative: RFC 2119, RFC 8174, RFC 5234, RFC 7405.

No IANA action is requested by this addendum.
