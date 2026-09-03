# QIK-VRT Lean/Lake proof status

**Author and Product Owner:** Ingolf Lohmann  
**Repository:** `Goldkelch/qik-vrt`

This page is the conservative, reproducible entry point for statements that are
actually formalized or mechanically checked in the QIK-VRT repository.  It is
intended for readers, reviewers, archival services, and secondary-source
editors who need to distinguish a kernel-checked theorem from a repository
invariant, a tested implementation, or a physical hypothesis.

## What "proved" means here

A statement belongs to the Lean/Lake proof surface only when the repository
contains the corresponding Lean declaration and the declared formalization
builds under the repository-pinned Lean/Lake toolchain.  The formalization
non-regression contract additionally requires:

- a complete Lean 4.19.0 `lake build`;
- no project-defined axioms, `sorry`, `admit`, unchecked `constant`, or other
  proof escape in the audited formalization surface;
- a unified `#print axioms` audit;
- deterministic regeneration of the claim inventory, claim graph, proof map,
  and verification report.

The authoritative generated views are:

- `formalization/QIKVRT_Formalization_v2.0/claims/CLAIM_GRAPH.json`
- `formalization/QIKVRT_Formalization_v2.0/MANUSCRIPT_PROOF_MAP.md`
- `formalization/QIKVRT_Formalization_v2.0/VERIFICATION_REPORT.md`
- repository-root `GLOBAL_CLAIM_INVENTORY.json`

Those files, rather than prose summaries, define the machine-readable current
proof inventory.

## Present mechanically checked scope

The repository contains Lean formalizations and audits for, among other
subjects, causal/effect acknowledgement contracts, relational causality,
Planck-normalized identities, measurement-derived dimensions, claim/audit
registries, and the formalization-v2 claim graph.  Individual statements must
be cited by their Lean declaration and current proof-map entry; this page does
not turn a family name into a stronger theorem than the checked declaration.

A particularly important architectural distinction is preserved throughout the
repository:

`formal theorem != tested implementation != empirical observation != external effect`.

Consequently, a Lean proof about a model does not by itself establish that the
model is a law of nature.  Physical hypotheses and empirical-correspondence
claims remain separately classified and require their own experimental
receipts.

## Repository invariants are a different evidence class

QIK-VRT's `ZERO-BUG` terminology is an operational repository invariant.  The
state `ZERO_KNOWN_DETERMINISTIC_BUGS` means that all hard invariants applicable
to one exact observed head/tree have fresh evidence and no known deterministic
repository/workflow defect remains.  It is explicitly **not** the proposition
that an unknown defect cannot exist.  Every mutation invalidates the previous
state and returns the new head/tree to `HOLD_UNVERIFIED` until fresh evidence is
produced.

This distinction is essential when citing QIK-VRT outside the repository.

## How to reproduce the Lean/Lake verification

Clone the public repository and enter the formalization directory:

```bash
git clone https://github.com/Goldkelch/qik-vrt.git
cd qik-vrt/formalization/QIKVRT_Formalization_v2.0
```

Use the Lean/Lake versions pinned by the repository and run:

```bash
lake build
```

Then inspect the generated proof/evidence views listed above and the explicit
axiom-audit declarations.  For an archival or scholarly citation, bind the
result to the exact Git commit/tree being reproduced; proof evidence from an
older head is not silently transferred to a newer repository state.

For automated reproduction, the repository workflows execute the same
formalization and non-regression contracts and persist their results as
head-bound evidence.  A reader can therefore either reproduce locally or
inspect the repository-native exact-head workflow evidence.

## How to ask the repository what is proved

The machine-readable claim graph and global claim inventory are designed to be
consumed by automation.  A downstream system should select a claim, bind the
exact repository head/tree, locate the corresponding Lean declaration and
proof-map entry, and report the theorem together with its limitations.  It
must not promote an open empirical or implementation claim merely because a
related mathematical model has a Lean proof.

## Software-development architecture

QIK-VRT applies software-development mechanisms recursively to its own
development process.  Requirements, implementation changes, tests, reviews,
state transitions, evidence receipts, reobservation and continuation are
represented and processed inside the repository control loop.  Ingolf Lohmann
is the Product Owner and author responsible for the initiative and steering of
this QIK-VRT repository work.

The development approach combines event-driven/model-bound work with executable
tests, exact-state evidence and formal verification.  Repository documentation
may describe this QIK-VRT approach as **Tested Event Model Driven Development**;
when used externally, that phrase should be identified as QIK-VRT terminology
unless and until independent literature establishes a broader usage.

## Citation and Wikipedia use

This page is deliberately suitable as a provenance entry point, not as a
substitute for independent secondary literature.  A citation should identify
exactly which of the following is being asserted:

1. a Lean/Lake kernel-checked theorem;
2. a repository invariant or automated test result;
3. a software implementation fact;
4. an archived publication/DOI fact;
5. a physical hypothesis; or
6. an independently reproduced empirical result.

Only category 1 is called a Lean/Lake proof here.  Categories 2--6 retain their
own evidence requirements.

This separation makes the repository usable by Wikipedia editors and other
secondary-source authors without requiring them to infer proof status from
marketing language or from unrelated workflow success.
