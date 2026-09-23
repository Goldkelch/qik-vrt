# TEMDD 1.1 Security and Assurance Profiles

Status: `RC1_NORMATIVE_PROFILE_CANDIDATE`

This document concretizes the additive profiles defined by TEMDD 1.1-rc1.

## Level 1 — Core

MUST provide authenticated write operations, authorization, exact subject and transaction binding, readback, policy evaluation, acceptance and audit. OpenAPI deployments MUST advertise at least one authenticated security scheme and MUST reject anonymous writes.

## Level 2 — Enhanced

In addition to Core, MUST support signed evidence, challenge/response where required by policy, evidence classification, bounded retry semantics and Effect Certificates.

## Level 3 — High Assurance

In addition to Enhanced, MUST support independent evidence, separation of duties, a hardware root of trust or an explicitly documented equivalent, secure or attested time, and hardware attestation where applicable.

## Level 4 — Critical Systems

In addition to High Assurance, MUST support policy-bound multi-evidence quorum, formal verification of declared critical invariants, a cryptographic audit chain, explicit trust-root governance and a fail-closed algorithm/profile registry.

## Security-profile binding

The selected level, security scheme, trust roots, algorithm profile, time basis, canonicalization profile and verification-policy digest MUST be fixed before EXECUTE and included in the verification context.

A profile label alone is not evidence of conformance. A level MAY be claimed only after the corresponding conformance suite passes on the exact implementation subject.

## API mapping

The TEMDD 1.1 OpenAPI profile defines Bearer/JWT and mutual TLS as reference transport authentication schemes. Other credentials such as TPM-, HSM-, FIDO2- or passkey-backed credentials MAY be integrated, but their proof semantics and key binding MUST be explicitly profiled.

## Invariant

`transport authentication != evidence trust != effect acceptance`

Authentication of the API channel never substitutes for evidence provenance, freshness, transaction binding, verification or acceptance.
