# Universal I/O Knowledge Publication Pipeline

## Product-Owner requirement

Every datum that crosses a QIK-VRT input/output interface, regardless of modality, is an auditable work event. A conforming interface adapter MUST persist a content-addressed repository receipt automatically. Where the payload itself cannot safely or lawfully be committed, the repository MUST still persist a hash-bound receipt that identifies the governed external/private payload location without exposing secrets or restricted bytes.

Persistence is only the first stage. Each persisted event MUST be deterministically classified for epistemic type, novelty, granularity and connection to the existing QIK-VRT knowledge graph. A candidate that is formalizable MUST be routed into the applicable machine-proof path. A machine proof is model-relative: it proves the declared formal statement under its declared assumptions and MUST NOT be promoted into physical correspondence, empirical confirmation or scientific consensus without the corresponding external evidence.

Publication is conditional rather than indiscriminate. An event is not automatically a new scientific result and not every persisted event is public. A stable, rights-cleared, provenance-bound and suitably granular knowledge unit may become a Zenodo publication candidate. Material that is additionally protocol/standards relevant may become an IETF candidate. Zenodo and IETF writes remain irreversible external effects and therefore require their separately persisted exact-effect authorization and post-effect receipt.

## Required automated state machine

`CAPTURE -> NORMALIZE -> HASH -> ATTRIBUTE -> PERSIST -> REOBSERVE -> CLASSIFY -> EXTRACT -> PROVE_OR_BOUND -> GRANULARITY -> CONNECTIVITY -> RIGHTS/PRIVACY/SECURITY -> SCIENTIFIC_STATUS -> PUBLICATION_CANDIDATE -> EXACT_HEAD_GATES -> EXTERNAL_EFFECT_AUTHORIZATION -> ZENODO/IETF_EFFECT -> EFFECT_REOBSERVATION -> RECEIPT`

A conforming implementation is fail-closed and idempotent. Replaying the same event MUST not create publication noise. Missing proof, rights, provenance, exact-head, effect authorization or external acknowledgement prevents advancement past the corresponding gate.

## Interface contract

The capture boundary includes text, audio, images, video, documents, code, structured data, tool calls/results, metadata and derived artifacts. The minimum durable receipt contains: event identifier, direction, timestamp, modality, SHA-256, byte length, actor class, epistemic type, source binding and retention class.

The interface adapter is responsible for automatic invocation. Manual copying from a chat transcript into the repository does not satisfy the fully automated acceptance criterion. Repository-native workers are responsible for deterministic continuation from the persisted receipt onward.

## Publication semantics

Zenodo eligibility requires stable exact bytes, provenance, rights clearance, scientific-status classification, accepted granularity/connectivity, applicable terminal-green checks and a separate exact external-effect authorization. IETF eligibility additionally requires protocol/standards relevance, a materialized Internet-Draft candidate and the applicable reference/IPR checks.

The resulting public artifact MUST link back to the exact repository provenance and the repository MUST persist the resulting DOI, draft/version identifier, external timestamps and response digests as effect receipts.

## Acceptance criterion

The end-to-end requirement is satisfied only when the deployed interface adapter automatically emits the capture receipt for every supported I/O event and the repository-native controller can resume and drive eligible candidates through the above gates without ad-hoc human copying. Human authority remains required only where the governing effect contract explicitly requires it, especially irreversible external publication effects.

Canonical machine-readable contract: `policy/UNIVERSAL_IO_KNOWLEDGE_PUBLICATION_PIPELINE_V1.json`.
