# QIK-VRT Universal Input/Output Round Trip

## Acceptance criterion

Every item that crosses a conforming QIK-VRT input/output boundary receives a repository-bound provenance receipt. Modality does not exempt an event: text, audio, image, document, link, tool call, retrieved source, model output, decision, review and external-effect result are all events.

Persistence is not synonymous with publishing every raw byte. Raw non-secret bytes SHOULD be content-addressed when rights permit. Secrets, credentials, private keys and equivalent authentication material MUST NOT be stored. Where privacy, copyright or confidentiality prohibits raw persistence, QIK-VRT persists the exact digest, metadata, provenance and the reason the bytes are absent or redacted.

```text
INPUT / OUTPUT
→ EVENT RECEIPT
→ CONTENT IDENTITY
→ CORRELATED WORK UNIT
→ CLAIM GRANULARIZATION
→ NOVELTY + CONNECTIVITY CLASSIFICATION
→ MACHINE PROOF
→ PUBLICATION BUNDLE
→ EXACT BYTE FREEZE
→ SINGLE-USE EFFECT AUTHORIZATION
→ ZENODO
→ PUBLIC BYTE REOBSERVATION + DOI RECEIPT
→ IETF, ONLY IF NORMATIVE PROTOCOL / INTEROPERABILITY DELTA
→ POST-EFFECT RECEIPT
→ NEXT DIFFERENCE
```

## Granularity without loss of history

Atomic event receipts are never replaced by summaries. Higher levels reference lower levels by exact identifiers and digests:

```text
EVENT
→ WORK_UNIT
→ CLAIM
→ PROOF_BUNDLE
→ PUBLICATION_BUNDLE
```

A publishable claim must state its normalized proposition, claim kind, assumptions, scope, dependencies, source events, evidence, relation to existing claims and novelty basis. If those links cannot be resolved, the state is `HOLD`, not knowledge.

## What “machine proved” means

QIK-VRT accepts different proof classes because different claims require different evidence:

- `LEAN_KERNEL_PROOF` for formal derivability inside an exactly bound formal system;
- `REPRODUCIBLE_COMPUTATIONAL_PROOF` for deterministic finite/computational results whose execution and inputs are bound;
- `EVIDENCE_BOUND_CORRESPONDENCE_TEST` when the proposition concerns the relation between a model and observation.

The proof class must fit the claim kind. A Lean proof of a model theorem does not by itself prove empirical correspondence. Conversely, an observational receipt is not a proof of every theorem in the model.

## Publication routing

A claim routes to Zenodo when it is classified as new knowledge, is machine-proved by the appropriate proof class, is sufficiently connected to repository knowledge, has cleared rights and exact-head gates, and has a frozen publication bundle.

Zenodo is the durable scientific archive. The existing generic QIK-VRT publisher remains the execution authority. It requires an exact machine-proof bundle, an exact prepublication return receipt, exact metadata, exact upload bytes and a candidate-specific single-use authorization before production mutation.

IETF is not a second archive for every scientific statement. It is selected when the new knowledge changes a normative protocol, wire contract, state machine, interoperability requirement or implementer-facing specification. Scientific discoveries without such a delta remain Zenodo/repository publications and receive `NO_PROTOCOL_CHANGE_REQUIRED` for IETF.

## Standing Product Owner authorization

`OWNER-AI-IO-ROUND-TRIP-AUTOPUBLISH-V1` authorizes autonomous continuation without repeated Product Owner questions. It does not pretend to exactly authorize bytes that do not exist yet. Instead, after final bytes, metadata, machine proof and prepublication return are frozen, automation may derive the candidate-specific single-use authorization required by the existing effect controller. The derived authorization must bind the natural-person principal, repository, source head, publication ID and every relevant digest.

Credentials remain outside the repository. If a secure runtime credential is unavailable, the candidate remains durably `PUBLICATION_READY` or `HOLD_EXTERNAL_EFFECT`; it is not discarded and no publication is claimed.

## End-to-end invariant

```text
NO SILENT INPUT
∧ NO SILENT OUTPUT
∧ NO LOST PROVENANCE
∧ NO PUBLICATION WITHOUT APPROPRIATE MACHINE PROOF
∧ NO EXTERNAL EFFECT WITHOUT EXACT SINGLE-USE AUTHORIZATION
∧ NO EFFECT CLAIM WITHOUT POST-EFFECT REOBSERVATION
```

The resulting goal is not maximal repository noise. It is a lossless causal audit trail with semantic deduplication: identical or non-novel material may collapse into a NOOP classification while its I/O receipt remains preserved.
