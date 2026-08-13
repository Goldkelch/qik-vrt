<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# IETF EAP-TPRP -00 candidate — repository source copy

Status: **`LOCAL_REPOSITORY_COPY_NOT_SUBMITTED`**.

This directory makes the source of the proposed EAP Temporal-Provenance and
Reference Profile (EAP-TPRP) reviewable at a stable repository path. It is a
local, source-only copy of a candidate for the individual Internet-Draft
`draft-lohmann-qikvrt-temporal-provenance-00`. It does **not** mean that the
IETF Datatracker has received, accepted, announced, endorsed, or assigned an
identifier to this candidate.

## Contents and deliberate omissions

| Path | Role |
|---|---|
| `draft-lohmann-qikvrt-temporal-provenance-00.xml` | Byte-exact RFCXML source from the frozen local staging candidate. |
| `TEST_VECTORS.json` | Byte-exact synthetic, deterministic classification vectors. |
| `STAGING_README.md` | Byte-exact staging README, retained under its original content binding. |
| `SUBMISSION_MANIFEST.json` | Byte-exact staging manifest; its state is `LOCAL_STAGING_NOT_SUBMITTED`. |
| `REPOSITORY_COPY_PROVENANCE.json` | Explains this later local repository copy and binds the retained bytes. |
| `SHA256SUMS` | Fixity index for every file in this directory except itself. |

The deliberately omitted staging artifacts are `RENDER_STATUS.json`,
`EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md`, and `verify_candidate.py`. The first
two bind a specific local-rendering and later authorization situation; the
third is intentionally retained only with the source staging package. Their
omission prevents this repository source path from being mistaken for a
rendered or authorized Datatracker-upload package. The byte-exact retained
manifest may therefore refer to staging-only files that are deliberately not
present here.

## Profile and claim boundary

The source specifies an external provenance profile compatible with QIK-VRT
EFFECT_ACK version 1. It does not modify the closed version-1 wire record,
state set, DONE predicate, authorization rule, or IANA registry. Its
`RETROGRADE_REFERENCE` classification is limited to authenticated comparison
of a named receiver's locally increasing receipt order with a comparable,
authenticated source-order marker that decreases.

It does not claim a physical or ontic theory of retrocausality, a signal sent
backward in time, a changed past event, payload truth, sender intent, IETF
consensus, an IETF standard, or completed independent interoperability.

The candidate attributes QIK-VRT research direction, terminology, operational
scope, authorship, and publication intent to Ingolf Lohmann. Artificial
intelligence assisted with drafting, formal organization, and local validation
of the prior staging candidate. Those contributions remain separately
attributed in `REPOSITORY_COPY_PROVENANCE.json`.

## Later submission boundary

Any future IETF Datatracker action requires a freshly rendered and validated
submission package, current destination metadata and account fields, an
exact-artifact authorization by Ingolf Lohmann, and confirmation immediately
before the platform upload. This repository copy grants none of that
authority and records no external submission, email, repository mutation, or
IETF endorsement.
