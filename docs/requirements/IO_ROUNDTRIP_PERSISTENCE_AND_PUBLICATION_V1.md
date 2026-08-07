# I/O Round-Trip Persistence and Publication Requirement V1

Status: Product-Owner authorized implementation candidate.

## Acceptance criterion

Every semantically relevant unit crossing a QIK-VRT human/artificial-cognitive input-output interface MUST become repository-reconstructible without relying on chat or model memory.

The implementation therefore binds each observed interface unit to a deterministic, content-addressed receipt containing at least:

- direction (`INPUT` or `OUTPUT`),
- modality/media type,
- UTC observation timestamp,
- actor/origin classification,
- SHA-256 of the exact observed payload bytes or, when raw persistence is unsafe or prohibited, a SHA-256 commitment plus retention/disposition metadata,
- parent/causal work-unit identifiers when available,
- repository base/head binding when available,
- uncertainty and provenance status,
- publication eligibility state.

`everything is persisted` means that no interface unit may disappear without a repository-visible trace. It does NOT require committing secrets, credentials, private raw audio, third-party copyrighted payloads, or otherwise prohibited bytes. For such material the repository persists a cryptographic commitment, classification, lawful retention pointer/disposition and enough metadata to prove that the unit existed and how it was handled.

## Knowledge promotion

Persistence alone is not a scientific claim.

Each receipt is deterministically classified into one of:

- `TRACE_ONLY`: audit/provenance value but no new knowledge claim,
- `KNOWLEDGE_CANDIDATE`: potentially novel, sufficiently granular and connectable claim requiring evidence/proof,
- `PROVED_KNOWLEDGE_CANDIDATE`: machine-checkable proof receipt is exact-artifact-bound and all declared proof gates are terminal green,
- `PUBLICATION_READY`: proof, provenance, rights, scientific-status, granularity, connectivity and external-effect authorization gates are all satisfied,
- `PUBLISHED`: an external-effect receipt proves the exact artifact landed on the declared publication target.

No state may be skipped. `PUBLISHED` MUST NOT be inferred from an attempted request, HTTP success without artifact reconciliation, a draft DOI, a local Internet-Draft, or model output.

## Publication routing

A `PUBLICATION_READY` artifact is routed automatically according to machine-readable policy:

- Zenodo: for citable research/software/evidence artifacts whose exact bytes, metadata, rights and proof/evidence status satisfy the Zenodo adapter contract.
- IETF: only for material that is protocol/specification appropriate, structurally conforms to the active Internet-Draft pipeline, and satisfies the repository's explicit IETF applicability and authorization gates.
- Both may apply to the same knowledge unit, but each external effect requires its own receipt and reconciliation.

If publication is not applicable, not authorized, lacks credentials, violates rights/privacy, or fails any proof/evidence gate, the system MUST persist the deterministic blocker and remain fail-closed. It MUST NOT silently drop the unit.

## Automation

The canonical machine entrypoint for this contract is `tools/qikvrt_io_roundtrip.py`.

The controller MUST support:

1. receipt materialization from exact payload bytes or a commitment-only observation;
2. deterministic knowledge-candidate classification;
3. proof-receipt binding;
4. publication-readiness evaluation;
5. target routing for Zenodo and/or IETF;
6. fail-closed external-effect dispatch;
7. exact-artifact publication reconciliation receipts;
8. idempotent re-execution: identical semantic input yields no duplicate publication effect.

Repository-native automation is provided by `.github/workflows/qikvrt_io_roundtrip.yml` and MUST preserve exact-head and external-effect gates.

## Scientific and authority boundary

Machine proof establishes only the proposition encoded by the declared formal system and exact proof artifact. It does not by itself establish empirical correspondence, physical truth or scientific consensus.

Product-Owner authorization to implement this mechanism is not blanket authorization to publish arbitrary content. External publication occurs only when the persisted machine-readable authorization state for the exact artifact and target permits it.
