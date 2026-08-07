# I/O Evidence → Machine Proof → Publication Round Trip

Product Owner: Ingolf Lohmann  
Canonical entrypoint: `/AI`

## Requirement

Everything semantically relevant that crosses an artificial-cognitive input/output boundary is represented durably in QIK-VRT repository evidence. The representation is content-addressed, provenance-bound and epistemically typed. Where direct payload retention is impermissible or impractical, the repository retains the strongest policy-compliant cryptographic and provenance binding that still makes the work auditable.

Persistence is not publication. Each independently attributable claim or tightly coupled claim set is classified, deduplicated and verified. A formal claim becomes publication-eligible only after its machine-verification evidence is bound to the exact claim bytes and assumptions. A model-relative proof is never promoted to empirical confirmation merely because a theorem prover accepted it.

Publication routing is deterministic:

`CAPTURE → HASH → PERSIST → CLASSIFY → DEDUPLICATE → EXTRACT_CLAIMS → VERIFY → PROVE_WHEN_FORMAL → ASSESS_NOVELTY → ASSESS_RIGHTS → ASSESS_SCIENTIFIC_STATUS → FREEZE_BYTES → ROUTE_ZENODO → ROUTE_IETF_IF_RELEVANT → REOBSERVE_EXTERNAL_EFFECT → PERSIST_RECEIPT`

Zenodo is the archival publication destination for eligible new knowledge. IETF routing is additional and conditional: it applies only when the result has protocol, interoperability or standards relevance and all IETF formatting/IPR gates are satisfied.

The pipeline is intended to require no manual copy/paste step. Repository-internal capture, classification, proof routing and candidate generation are automatic when the working copy is writable and exact-head verified. External publication remains fail-closed on the repository's standing or single-use effect authorization, credentials, exact-artifact binding and pre-effect gates. Those gates are automation inputs, not an invitation to bypass them.

## Executable controller

`python3 -B tools/qikvrt_io_roundtrip.py capture ...` reads payload bytes from stdin and materializes a content-bound event in `state/io_roundtrip/events/`.

`python3 -B tools/qikvrt_io_roundtrip.py candidate ...` converts an event into a claim-granular publication candidate only with explicitly declared gate evidence.

`python3 -B tools/qikvrt_io_roundtrip.py verify` validates the machine-readable policy contract. A successful contract check reports `CONTINUE`, not `PASS`: end-to-end acceptance additionally requires exact-head CI plus observed Zenodo/IETF effect receipts for the applicable publication path.

## Acceptance boundary

The requirement is satisfied only when an observed end-to-end run demonstrates all of the following for an in-scope interaction: repository persistence or content binding, provenance reconstruction, claim-granular verification, machine proof where formal, novelty/rights/scientific-status assessment, exact byte freeze, automatic Zenodo routing, conditional IETF routing, and persisted external-effect receipts.

No chat response, local candidate, pull request, green unit test, or Product-Owner statement alone is sufficient evidence for `FINAL_PASS` or `EFFECT_ACK_DONE`.
