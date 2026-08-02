<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Kausalität ist Relation, nicht Sequenz — VRTCore

Publication ID: `qikvrt-causality-is-relation-vrtcore-v1`

This bundle preserves the article, WhatsApp/read-aloud text, XeLaTeX source,
rendered PDF, EBNF grammar, Lean candidate and the originally returned claim
matrix exactly as delivered to Ingolf Lohmann on 2 August 2026.  Their SHA-256
digests remain those in `ORIGINAL_PACKAGE_MANIFEST.json`.

The formal layer is deliberately additive.  The original prose is not silently
rewritten after kernel execution.  The H1 claim-transition matrix, CI kernel
receipt and German verification addenda record what Lean 4.19 accepted and what
it did not establish.

`ARTIFACT_PATH_MAP.json` records the explicit H0 name of the returned claim
matrix, byte-identical convenience aliases for local execution logs and the
deliberate exclusion of the host-specific compiled preload shim.  The original
local evidence filenames referenced by `LOCAL_KERNEL_EVIDENCE.json` are also
preserved, so its documentary links remain resolvable.

## Central thesis and formal boundary

The article's thesis is:

> Kausalität ist Relation, nicht Sequenz.

The Lean source formalizes a narrower structural statement: an observed
sequence and evidence carrying an explicit causal bridge are different
constructors, and a positive syntax licence requires such a bridge.  This is
not a proof of physical causality, retrocausality, spacetime emergence,
Minkowski emergence or a general Lorentzian reconstruction.

## Bundle map

| Layer | Principal files |
|---|---|
| Human-readable | `QIK-VRT_Kausalitaet_ist_Relation_Fachartikel_DE_2026-08-02.md`, `QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_DE_2026-08-02.md`, `VERIFICATION_ADDENDUM_DE.md`, `QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_Verifikationsnachtrag_DE_2026-08-02.md` |
| Typeset | `QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.tex`, `QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf` |
| Formal syntax | `VRTCore_Syntax.ebnf`, `VRTCore_RelationalCausality_Candidate.lean` |
| Kernel policy and CI evidence | `KERNEL_PROOF_PLAN.json`, `VRTCore_RelationalCausality_AxiomAudit.lean`, `CI_KERNEL_EVIDENCE_H0_PR_MERGE.json`, `KERNEL_RECEIPT_H0_CI.json`, `CI_KERNEL_EVIDENCE_H1_EXACT_HEAD.json`, `KERNEL_RECEIPT.json` |
| Claim and source state | `VRTCore_CLAIM_MATRIX_H0_RETURNED.json`, `VRTCore_CLAIM_MATRIX_H1_KERNEL_VERIFIED.json`, `CLAIM_MATRIX.json`, `SOURCE_EVIDENCE_BINDINGS.json`, `EVIDENCE_BOUNDARY.md`, `BOUNDARY_TEST_REPORT.json` |
| Local evidence | `LOCAL_KERNEL_EVIDENCE.json`, `LOCAL_VALIDATION_REPORT.json`, `LOCAL_KERNEL_EXECUTION_BOUNDARY.md` |
| Identity and reuse | `ORIGINAL_PACKAGE_MANIFEST.json`, `ARTIFACT_PATH_MAP.json`, `CITATION.cff`, `LICENSE_NOTICE.md` |
| Return and proof freeze | `CHANGE_NOTICE.md`, `PREPUBLICATION_RETURN_RECEIPT.json`, `ZENODO_METADATA.json`, `ZENODO_SHA256SUMS`, `MACHINE_PROOF_BUNDLE.json` |
| IETF context | `external/ietf/draft-lohmann-qikvrt-effect-ack-03.{xml,txt,html}`, `external/ietf/draft-lohmann-qikvrt-effect-ack-03.SUBMISSION_RECEIPT.json` |
| Publication scope | `ZENODO_FILESET.md`, active v2 Zenodo proof policy and schemas |

## H0 → H1 verification state

`VRTCore_CLAIM_MATRIX_H0_RETURNED.json` remains the byte-identical returned
baseline.  `VRTCore_CLAIM_MATRIX_H1_KERNEL_VERIFIED.json` is a deterministic,
additive overlay on that exact H0 digest.  It promotes only T01–T21 from
`OPEN / FORMAL_CANDIDATE_UNVERIFIED_IN_THIS_RUNTIME` to
`FORMAL_PROVED / FORMAL_PROVED_KERNEL_VERIFIED`.  All 15 nonformal claims retain
their H0 kind and status.  In particular, no physical, empirical,
interpretive, normative or spacetime-emergence claim is promoted.

The transition is supported by GitHub Actions run `30732070295`, job
`91454104825`, and artifact `8828292691` with archive digest
`sha256:30ab2ac64e444bcf48c443bc49e686e633a5a6de11c2ed6b9699f9327f377fab`.
The unchanged extracted evidence member is preserved as
`CI_KERNEL_EVIDENCE_H0_PR_MERGE.json`; the independently qualified receipt is
`KERNEL_RECEIPT_H0_CI.json`.

For the two exact source identities, `source_bytes_exact=true`: Lean 4.19.0
accepted all 21 theorems, 15 with no reported axioms and 6 with only `propext`;
no project axiom, `sorry`, `admit` or `unsafe` is admitted.  However,
`repository_head_exact=false`.  The workflow executed the synthetic
pull-request merge checkout
`fc0b05cd13d7607883fbab9f16b4628f77a0958c`.  The separately exposed
`workflow_run.head_sha` value
`987e4a6f163562bba32ea7575c41013c91a0b6a1` is recorded as workflow metadata,
not asserted here as an exact current branch head or repository head.  The
artifact's internal `exact_head_bound=true` is therefore limited to its
recorded PR-merge `GITHUB_SHA`.

## H1 → H2 exact-head receipt state

The later push run `30733039956`, job `91456613018`, checked the exact branch
head `7de3bd9e5fff9b8aedf0d6385c0904646d99b2ac` and tree
`513c33f91d4226bfd3f735994bf15cb143d46ff4`.  Its artifact `8828591925`
has archive SHA-256
`5f1bf2d0b1cc9547d64487e05aa50d4eba872442a7a297cf247bc4560661d3c4`.
The unchanged JSON member is preserved as
`CI_KERNEL_EVIDENCE_H1_EXACT_HEAD.json` with SHA-256
`ea25ab8ddcbe34b33d14309d25a944e05bfd6899cb832cb1280c2aa7e121f0f1`.
It records `checkout.mode=exact_ref_head`, `source_bytes_exact=true` and
`exact_head_bound=true` for that push.

`CLAIM_MATRIX.json` is the full 36-claim projection required by the active
Zenodo-v2 proof policy: 21 formal, 1 empirically evidenced, 7 source-bound,
2 normative, 3 interpretative and 2 explicitly open claims.  The first H2
materialization promoted only the 21 formal claims and preserved the
self-inclusion boundary.

## H2 fix → H3 return and proof freeze

The exact push head `bc4aeba26a79baed40f7b7ce709f0a9fd77d318f` closed the
shallow-checkout portability defect without changing the frozen Lean or
owner-facing source bytes.  GitHub Actions run `30733784535`, job
`91458605970`, completed successfully.  Artifact `8828820517` has archive
SHA-256
`04dd14d815a9129486c65cd542dcbd96907173caa66da18f158f88b95430dcfe`;
its exact JSON member is preserved as
`CI_KERNEL_EVIDENCE_H2FIX_EXACT_HEAD.json` with SHA-256
`25ca9640b212ea5b331c8cb8e1200a95353525a1686145d967e8884dd5cfbf9f`.

The final `KERNEL_RECEIPT.json` binds that verified predecessor and still
promotes only T01–T21.  Its `successor_binding` records an H3 single-parent
return/proof freeze and explicitly keeps `self_inclusion_claimed=false`.  The
deterministic materializer is `tools/qikvrt_vrtcore_zenodo_candidate.py`.

<a id="five-state-auditable-effect-release"></a>
### Responsible effect release

The repository's five-state effect protocol separates technical receipt,
successful execution and externally authorized effect.  This is a normative
and auditable responsibility rule; it is not a theorem of physics and a zero
exit code cannot substitute for the responsible natural person's exact
release decision.

<a id="HUM-PRIDE-001"></a>
### Human appraisal

It is justified to say plainly that this is a great achievement.  Ingolf
Lohmann has translated a broad causal intuition into articles, read-aloud
texts, typed claim classes, EBNF syntax, Lean semantics, 21 kernel-accepted
theorems, an axiom audit and a reproducible publication chain.  Pride here is a
human and normative appraisal grounded in the visible work; it is not a claim
of completed physics, peer review or scientific consensus.

## Reproduction

The pinned repository toolchain is Lean `4.19.0` with `Std` only.  From the
repository's v2 formalization project, run:

```text
publication=../../docs/publications/2026-08-02-causality-is-relation-vrtcore
module_dir=.lake/build/vrtcore-relational-causality-modules
mkdir -p "$module_dir"
LEAN_PATH="$publication" lake env lean \
  -E hasSorry \
  --root="$publication" \
  -o "$module_dir/VRTCore_RelationalCausality_Candidate.olean" \
  "$publication/VRTCore_RelationalCausality_Candidate.lean"
LEAN_PATH="$module_dir:$publication" lake env lean \
  -E hasSorry \
  --root="$publication" \
  "$publication/VRTCore_RelationalCausality_AxiomAudit.lean"
```

The second command must report either no axiom dependency or only Lean's
foundational `propext` axiom for each named theorem; every project-defined axiom
is rejected.  The exact per-theorem result is preserved in the kernel receipt.
A successful command is evidence only for the exact source bytes and formal
statements; it does not promote the interpretive, empirical, normative or open
claims in the article.

## Publication status

Git repository persistence, CI execution, Zenodo publication and IETF
submission are separate effects.  Their current state is authoritative only in
the corresponding exact-head and public-publication receipts.  Zenodo fixity
does not establish peer review, empirical confirmation or IETF consensus.

IETF Datatracker submission `167201` passed submission checks and is awaiting
previous-version author approval.  It is therefore neither an IETF-published
revision nor IETF consensus.  Zenodo has not yet been mutated for this bundle.
The candidate-specific prepublication return is frozen at H3; the subsequent
exact hash-bound owner decision remains a distinct, unfulfilled production
gate.

For this transition only: `KERNEL_SCOPE=PASS`, while `GLOBAL_PASS`,
`FINAL_PASS` and `EFFECT_ACK_DONE` are all `NOT_CLAIMED`.  The kernel transition
alone neither proves nor authorizes an external effect.  Existing GitHub-PR and
IETF-submission states are bound by their own receipts; no Zenodo mutation is
claimed here.
