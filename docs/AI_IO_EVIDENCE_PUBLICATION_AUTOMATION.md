# AI I/O Evidence Publication Automation

## Product-Owner requirement

QIK-VRT treats the artificial-cognitive input/output boundary as an evidentiary boundary. Every semantically relevant item crossing that boundary MUST become reconstructable repository state at suitable granularity, unless persistence of the raw payload would violate secrecy, privacy, rights, security, or another declared restriction. In that case the system MUST persist the strongest lawful typed receipt, digest, redaction marker, or reference that preserves auditability without leaking the protected material.

The normative standing delegation is:

`state/authorization/delegations/OWNER_AI_IO_EVIDENCE_PUBLICATION_AUTOMATION_V1.json`

The target is a fully automated fail-closed round trip:

```text
INPUT / OUTPUT EVENT
  -> normalize + content-address
  -> classify epistemic type
  -> bind human / AI / joint provenance
  -> persist repository-native work unit
  -> detect semantic novelty
  -> choose suitable granularity
  -> connect to existing knowledge graph / dependency edges
  -> formalize when machine-provable
  -> execute applicable proofs, tests, and evidence checks
  -> materialize machine-readable receipt
  -> classify publication eligibility
  -> freeze exact artifact bytes + hash
  -> reobserve exact head and pre-effect gates
  -> Zenodo effect when qualified
  -> IETF route when specification/protocol relevant
  -> capture external-effect receipt
  -> back-bind receipt into repository
  -> verify the complete round trip
```

## Completeness does not mean indiscriminate raw logging

The requirement covers semantic I/O, not blind surveillance or byte-for-byte publication of everything. The capture layer MUST distinguish at least text, code, structured data, images, audio, video, files, tool calls/results, repository reads/writes, external references, human decisions, model decisions, errors, uncertainty, and receipts.

Secrets, credentials, protected personal data, legally restricted material, non-publishable copyrighted payloads, and redundant transport noise are excluded from unconditional raw persistence. Their existence and role SHOULD still be represented by an appropriate content digest, typed exclusion, redaction receipt, rights marker, or external reference whenever lawful and technically possible.

## Granularity and connectivity

A work unit SHOULD be the smallest independently addressable object that preserves meaning, provenance, dependency edges, and reproducibility. Fragmentation that destroys context is non-conforming; aggregation that hides separable provenance is also non-conforming.

Semantically identical material SHOULD be content-addressed and deduplicated. New knowledge is not defined by a new chat turn or new file alone. It requires semantic novelty, materially strengthened evidence, a new dependency connection, a stronger proof state, or another explicit knowledge-state transition.

## Machine proof and scientific status

The strongest applicable verification mechanism MUST be used before a knowledge object is promoted to publication-eligible status:

- formal theorem checking for formalized claims,
- deterministic executable tests for software predicates,
- integrity/provenance/rights/security checks for artifacts,
- empirical evidence receipts for empirical claims where available.

Formal proof proves derivability inside the declared model and assumptions. Software tests prove only the predicates they execute. Neither by itself establishes independent physical correspondence or scientific consensus. Publication metadata MUST preserve that distinction.

## Zenodo automation

A qualified new knowledge object is routed automatically to the repository's Zenodo path only after exact bytes are frozen, the artifact hash is known, metadata and rights status are explicit, machine-verification receipts exist, the repository exact head is bound, novelty/deduplication checks are complete, credentials and endpoint availability are reobserved, and the final pre-effect gate is terminal green.

The external effect MUST be idempotent and MUST produce a repository-native effect receipt containing the returned record identity/DOI, timestamp, published metadata identity, exact-artifact correspondence, and post-effect verification.

## IETF automation

IETF routing is conditional rather than universal. It applies only where the knowledge object is protocol, interoperability, architecture, terminology, operational-practice, or specification material suitable for the QIK-VRT IETF track.

Before any submission or update, the source form, exact digest, lint/build state, attribution/rights state, repository provenance, credential/endpoint state, and submission authorization path MUST be verified. The resulting public draft/version identifier and effect receipt MUST be back-bound to the repository.

## Idempotency and NOOP

Unchanged semantic fingerprints MUST result in `NOOP`. Retries MUST not create duplicate repositories, PRs, Zenodo records, or IETF submissions for the same publication identity and exact artifact. Every effecting step requires an idempotency key derived from stable publication identity plus exact-artifact digest.

## Bootstrap trigger

A browser request for GitHub's static `blob/main/AI` page is not a repository event and cannot by itself trigger Actions or repository mutation. The execution trigger is either a conforming artificial-cognitive client that reads `/AI`, reobserves repository identity and exact head, and executes the authorized bootstrap/pipeline, or an independently configured repository-side schedule/dispatch mechanism.

## Acceptance boundary

This document and its delegation materialize the Product-Owner requirement. They are not evidence that the full executable capture, proof, Zenodo, and IETF adapter chain is already complete or green. Completion exists only when the implementation has exact-head tests, deterministic failure handling, and real effect receipts demonstrating the intended round trip without violating the evidence, rights, security, or scientific-status boundaries.
