# QIK-VRT IETF next-submission scope — 2026-09-23

Status: repository planning artifact only. No IETF Datatracker mutation is performed by this file.

## Public baseline

The active individual Internet-Draft is `draft-lohmann-qikvrt-effect-ack-03`,
published 2026-08-02 with intended status Experimental. It remains an
individual Internet-Draft, not an RFC, not an IETF standard, and not IETF
consensus.

## Delta assessment against revision -03

Revision -03 already establishes several boundaries that this planning note must
not present as new protocol inventions:

- an evidence digest identifies content but is not evidence validation;
- policy-defined evidence validators are required for DONE;
- absence, retrieval failure, digest mismatch, or validator failure prevent
  DONE;
- typed claims may remain external evidence-profile objects without changing
  the closed version-1 wire record;
- security considerations already include evidence omission, digest confusion,
  stale-DONE replay, and downgrade to weaker semantics.

Therefore a revision -04 MUST NOT be submitted merely to repeat the
requirements-carrier observation in different words. A -04 is justified only
if it adds a real normative protocol delta, for example a standardized
machine-checkable evidence-scope relation or a backward-compatible extension
mechanism that is not already expressible through the policy descriptor and
its validator.

If no such normative delta survives conformance review, the 25,361-byte
requirements carrier and its negative completion state should instead become a
machine-readable conformance vector/profile, while broad deployment mappings
belong in a separate applicability/profile Internet-Draft.

## Candidate revision -04: narrow protocol delta

A revision `draft-lohmann-qikvrt-effect-ack-04` should be prepared only if it
adds a protocol-relevant clarification beyond revision -03. The preferred
delta is the explicit separation of evidence identity from evidence meaning
and from downstream effect authorization.

The revision candidate SHOULD make the following points machine-checkable:

1. A content digest proves byte identity of the bound object only.
2. Evidence MUST carry an explicit evidence kind and claim scope.
3. A receiver MUST NOT upgrade a requirements-carrier identity receipt into an
   implementation, acceptance, end-to-end, or effect-acknowledgement claim.
4. The release predicate MUST validate that every evidence item is admissible
   for the predicate it is used to satisfy.
5. Missing or scope-incompatible evidence MUST fail closed; it MUST NOT be
   silently interpreted as a weaker positive result.
6. The requirements-carrier example with SHA-256
   `936686c7b6c1e249e8b31215d5111b76a78e494d0ea822a505bd309f946e278e`
   SHOULD appear as a non-normative test vector demonstrating:
   `DOCUMENT_BYTE_IDENTITY=VERIFIED` while
   `IMPLEMENTATION_VERIFIED=false`,
   `ACCEPTANCE_TESTS_EXECUTED=false`,
   `END_TO_END_VALIDATED=false`, and
   `EFFECT_ACK_DONE=false`.

## Wire/schema question to resolve before -04

Prefer a backward-compatible extension if revision -03 already provides a
suitable extension point. Candidate fields are:

- `evidence_kind`
- `claim_scope`
- `subject_hash`
- `subject_media_type`
- `verified_predicates`
- `unverified_predicates`

If adding these fields would change the version-1 wire contract incompatibly,
publish the evidence-scope rule as a separate profile or companion draft
instead of silently changing version 1.

## Companion document candidate

Broader applicability across HTTP APIs, message buses, SNMP-like management,
industrial digital-twin exchange, enterprise integration, automotive gateway
boundaries, and human/machine or AI-agent control planes should be kept out of
the compact core protocol unless it changes wire semantics.

A separate applicability/profile Internet-Draft may therefore be preferable,
for example:

`draft-lohmann-qikvrt-effect-ack-applicability-00`

It can define transport-neutral integration patterns, threat models,
interoperability expectations, and worked mappings without claiming that
non-IETF protocols are standardized by the IETF.

## Evidence-scope threat model

The next protocol work should explicitly test at least these failure classes:

- **CLAIM_ELEVATION:** byte identity or schema validity is reused as evidence for
  a stronger predicate such as implementation, acceptance, end-to-end
  validation, or completed downstream effect.
- **SUBJECT_SUBSTITUTION:** valid evidence for one subject hash, media type,
  revision, or execution is attached to another subject.
- **PREDICATE_CONFUSION:** an evidence kind is syntactically accepted for a
  predicate it is not semantically authorized to satisfy.
- **REPLAY_OR_STALE_EVIDENCE:** an otherwise valid earlier receipt is reused
  after the bound subject, policy, execution, or target state has changed.
- **DOWNGRADE_OR_OMISSION:** a peer omits claim-scope information or falls back
  to a representation in which the distinction between verified and
  unverified predicates is lost.
- **PARTIAL_EVIDENCE_COMPLETION:** a subset of required receipts is treated as
  sufficient for a conjunctive release predicate.

Receivers should fail closed for these cases and should expose a diagnostic
that identifies the rejected evidence item, its claimed scope, the predicate
being evaluated, and the current subject binding. This is a protocol-safety
requirement; it is distinct from whether any particular implementation has
already passed acceptance testing.

## Submission quality gate

Before any Datatracker mutation:

- bind the exact candidate XML bytes and SHA-256;
- render with the repository-pinned xml2rfc v3 toolchain;
- run repository regression and interoperability tests;
- run current IETF validation/idnits checks;
- verify that revision numbering and dates are current;
- create a submission receipt candidate before external mutation;
- submit only the exact hash-bound XML;
- perform public Datatracker readback and persist the resulting receipt.

## Current disposition

IETF_REVISION_04_PREPARED = FALSE
IETF_REVISION_04_SUBMITTED = FALSE
IETF_APPLICABILITY_00_PREPARED = FALSE
IETF_APPLICABILITY_00_SUBMITTED = FALSE
EFFECT_ACK_DONE = FALSE
