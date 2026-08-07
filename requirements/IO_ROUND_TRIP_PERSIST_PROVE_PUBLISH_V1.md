# I/O Round-Trip Persist–Prove–Publish Requirement V1

Status: PRODUCT_OWNER_APPROVED_IMPLEMENTATION_REQUIREMENT
Date: 2026-08-07
Authority: Ingolf Lohmann (Product Owner)

## Normative requirement

Every artifact that crosses the human–machine input/output boundary, irrespective of modality, MUST enter a repository-native, provenance-bound processing path.

The path MUST be fully automatable and MUST preserve the following state machine:

`INPUT_OR_OUTPUT -> CAPTURE -> CONTENT_ADDRESS -> CLASSIFY -> PERSIST -> DERIVE -> VERIFY -> PROVE_WHEN_FORMALIZABLE -> PACKAGE_WHEN_NOVEL_AND_CONNECTABLE -> PUBLICATION_GATES -> ZENODO -> IETF_WHEN_APPLICABLE -> RECEIPT -> REOBSERVE`

### Acceptance criteria

1. **Universal I/O capture.** Text, audio, image, document, code, structured data, tool results, generated artifacts, and other supported I/O modalities are represented by a durable work-unit record. Raw bytes need not be publicly committed when privacy, rights, size, or security constraints prohibit it; in that case the repository MUST persist a content-addressed manifest, provenance, retention/location class, and processing state sufficient to bind the exact artifact.
2. **No chat-only knowledge.** A semantically relevant input or output MUST NOT remain solely in transient chat/model memory. The repository record is the durable authority for subsequent automation.
3. **Provenance.** Each work unit distinguishes human contribution, artificial-cognitive contribution, separable joint components, and unresolved origin. It binds timestamps, hashes where bytes exist, source/target modality, tool/model identity where applicable, and predecessor/successor relations.
4. **Granularity.** Automation MUST split or aggregate work units at a granularity that permits stable provenance, independent verification, deduplication, theorem/reference binding, and publication without manufacturing artificial novelty.
5. **Machine proof.** Claims that are formalizable MUST be routed to the repository's machine-verification/proof path. A proof establishes only the proposition encoded in the formal model. Non-formalizable, empirical, interpretive, or source-attributed claims MUST retain their proper evidence class and MUST NOT be relabeled as formally proved.
6. **Novelty and connectability gate.** Publication candidacy requires an explicit machine-readable determination of novelty/relevance and sufficient connection to the existing corpus. `NEW_KNOWLEDGE_CANDIDATE` is not equivalent to independent empirical confirmation or scientific consensus.
7. **Zenodo.** A publication-ready knowledge unit MUST be packaged for Zenodo only after exact-artifact, rights, provenance, scientific-status, integrity, and credential/pre-effect gates pass. Production publication MUST produce a durable effect receipt and subsequent reobservation.
8. **IETF.** IETF routing occurs only when the knowledge unit is suitable for Internet standardization or protocol/architecture documentation. Scientific or personal material MUST NOT be sent to IETF merely because it is novel. Applicable candidates follow the repository's Internet-Draft workflow and its separate authorization/effect gates.
9. **Automation.** After an I/O event has been admitted, all deterministic repository-internal steps MUST proceed without requiring repeated human prompting. Human intervention is reserved for unresolved provenance/rights, acoustic or semantic verification where required, scientific judgment not safely automatable, conflicts, credentials, and consequential external-effect authorization unless a valid standing delegation explicitly covers that exact effect.
10. **Fail closed.** Missing bytes, ambiguous identity, failed verification, insufficient rights, unstable exact head, unavailable credentials, or an inapplicable publication target MUST yield an explicit non-terminal state such as `PENDING`, `HOLD`, `BLOCK`, `NOOP`, or `NOT_APPLICABLE`; automation MUST NOT fabricate `PASS`, proof, publication, or receipt.
11. **Idempotence and deduplication.** Repeated ingestion of byte-identical or semantically unchanged I/O MUST converge on existing content-addressed work units and MUST NOT create publication/comment/PR loops.
12. **Round-trip receipt.** Completion of any externally published unit requires repository evidence linking source I/O, derived artifact, proof/verification receipts, exact published bytes, external identifier/URL/DOI or draft identifier, effect acknowledgement, and post-effect reobservation.

## Current-turn Product Owner directive

The Product Owner states that the prior interaction did not satisfy this acceptance criterion and grants implementation authorization for the repository-internal implementation work needed to close the gap.

This authorization does **not** by itself assert that Zenodo or IETF production effects have occurred, that credentials are available, that uploaded audio has been acoustically transcribed, or that every I/O modality is already covered. Those states require their own exact evidence and receipts.

## Current supplied audio batch binding

The 2026-08-07 interaction supplied ten M4A inputs. The repository implementation MUST admit them as I/O work units using these exact SHA-256 bindings (filenames are labels, not transcripts):

- `13b9e27f5b106af71980df056ed0a20bb90d4a298df89e065e77817e34e6767a` — `Das ist Anwenderfreundlichkeit! q.e.d. Ingolf Lohmann.m4a`
- `298c0de7c2e9b4a1012aa64f03dc7be79c57481272054dc72afbaadd5718fa45` — `Das ist Fabelhaftung! q.e.d. Ingolf Lohmann(20260807-135117).m4a`
- `30ea5e3341ea9fb1c8e1836a77f6a617e46730fb6f08c80a7eccdc50b84cc278` — `Das ist ModelDrivenDevelopment! q.e.d. Ingolf Lohmann.m4a`
- `9fb81a316b2dad69eb0ad85a25394b61c880ec4cf5f07440b00f1d156aa318b8` — `Das ist Rechnerarchitektur! q.e.d. Ingolf Lohmann.m4a`
- `615fb3d85cbb5fb7c8386a29de4d7e880cb6eaf694bd7b9b63b927c2063788ef` — `Das ist Zeitgeist 🐦‍🔥 q.e.d. Ingolf Lohmann.m4a`
- `a8984267ce2e837d1f08d6a1bb512ddba8d5b1c6b58d6a6c4f703a662e55bf31` — `Das ist mein Beweis! q.e.d. Ingolf Lohmann(1).m4a`
- `0079e12fa8c617e1571bf716b0d8b598181d7bd7de7f2faf9e5adbc100b4c173` — `Das ist meine Kugel! q.e.d. Ingolf Lohmann(3).m4a`
- `4e43966861ec309cf5de03957c01e1f2602801b1cec720faaaf64b003b72d913` — `Das ist 🌊 q.e.d. Ingolf Lohmann.m4a`
- `077eaa97522045fda9ff8f4649118ac9211d1b8c486388b74cd6786df26d69f5` — `Mein Wunsch …! q.e.d. Ingolf Lohmann(4).m4a`
- `c0cb3b7bff5bca57a5b716fe4796a32012ad2b814e5c455b62af2243e16c89d7` — `🌊♾️🌊♾️🌊.     q.e.d. Ingolf Lohmann.m4a`

Until repository-native ASR binds these exact hashes to model/tool receipts, their semantic content remains `BOUND_PENDING_ASR`.

## Definition of done

This requirement is satisfied only when executable ingestion, persistence, derivation, verification/proof routing, publication qualification, external-effect gating, receipts, reobservation, and regression tests demonstrate the complete path for every supported I/O class. Merely documenting this requirement is progress, not completion.
