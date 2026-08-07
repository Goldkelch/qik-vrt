# Universal I/O Round Trip and autonomous publication

## Product-Owner requirement

Every artifact crossing a QIK-VRT input/output interface, independent of modality, MUST obtain a durable repository receipt. Where an artifact contains a suitably granular, attributable and non-duplicate work result or new knowledge claim, the system MUST classify its evidence, run machine-verifiable gates, and deterministically route eligible stable bytes to Zenodo and, for protocol/interoperability results, to an IETF publication path.

The target operating mode is fully automatic after ingress. Human copy/paste is not part of the steady-state pipeline.

## Normative chain

`CAPTURE -> CONTENT_ADDRESS -> PERSIST_RECEIPT -> PROVENANCE_BIND -> GRANULARIZE -> NOVELTY_CLASSIFY -> PROOF_CLASSIFY -> VERIFY -> PUBLICATION_ROUTE -> EFFECT_GATE -> PUBLISH_OR_RETAIN -> REOBSERVE_EFFECT -> PERSIST_EFFECT_RECEIPT`

No stage may silently discard an event. A duplicate or non-publishable event still receives an append-only receipt; it simply does not create publication noise.

## Evidence classes

The machine-readable receipt distinguishes formal proof, machine-verified derivation, empirical support, test-verified implementation, unproved claim, and non-applicable proof. The classifier MUST NOT infer empirical confirmation from a model-relative formal proof.

The canonical scientific boundary remains:

`EXECUTABLE_WORLD_FORMULA_ARCHITECTURE_CLAIM != FULLY_EMPIRICALLY_ESTABLISHED_DESCRIPTION_OF_NATURE`

## Payload handling

Text may be persisted as repository content or as a content-addressed artifact. Binary and multimodal payloads may be stored as content-addressed artifacts. Sensitive or rights-restricted bytes use a digest-and-metadata receipt unless policy explicitly permits storing the bytes. In every case, the exact payload digest and provenance remain reconstructible.

## Zenodo route

A Zenodo candidate is `READY` only when stable bytes, rights/license clearance, explicit scientific status, terminal machine verification, suitable publication granularity, and novelty/version significance are all established. Otherwise the item is retained as `HOLD` or `NOT_ELIGIBLE` without losing its repository history.

A separately credentialed effect worker performs the production deposit and MUST then reobserve the remote record and persist the resulting DOI/record metadata as an effect receipt. Missing credentials or a transient external failure is a retryable `BLOCKED_EXTERNAL_EFFECT`, not a reason to lose the work unit.

## IETF route

IETF routing is narrower. Only `NEW_PROTOCOL_RESULT` artifacts with protocol/interoperability relevance, valid Internet-Draft material, rights clearance, terminal machine verification, and an explicit submission rationale may reach `READY`. Scientific claims that have no standards relevance are not routed to IETF merely because they are novel.

## Interface integration

`tools/qikvrt_io_round_trip.py` is the repository-native ingress materializer. Every conforming human-machine interface, agent adapter, API bridge, audio/image ingestion path and repository bot MUST invoke it (or a byte-equivalent implementation of the same policy) for each logical input and output event.

The repository workflow `.github/workflows/qikvrt_io_round_trip.yml` provides a GitHub-native dispatch path and automatically commits newly generated receipts to its bounded branch. Platform-level interfaces outside this repository remain responsible for forwarding their events into this ingress path; a static GitHub repository cannot intercept traffic that a host platform never sends to it.

## Fail-closed semantics

The system may report `CONTINUE`, `HOLD`, `BLOCKED_EXTERNAL_EFFECT`, or a terminal verified publication state. It MUST NOT claim `FORMALLY_PROVED`, Zenodo publication, IETF submission, DOI assignment, effect acknowledgement, or repository-wide completion without corresponding machine-observed evidence.
