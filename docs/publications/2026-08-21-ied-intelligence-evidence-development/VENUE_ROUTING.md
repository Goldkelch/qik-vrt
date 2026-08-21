# IED venue routing

Work unit: `IED-DISSEMINATION-2026-08-21-V1`

This document routes one source bundle into distinct venue-specific candidates. It does not execute any external submission.

## State model

```text
SOURCE_BOUND
→ PACKAGE_PREPARED
→ PACKAGE_FROZEN
→ SUBMITTED
→ RECEIPT_OBSERVED
→ PUBLIC_BYTES_REVERIFIED
```

No later state may be inferred from an earlier one.

## GitHub

**Role:** canonical source, development, review, history, and repository evidence.

**Current state:** `REPOSITORY_CANDIDATE`.

**Required before merge:** complete bounded bundle, deterministic checksums, repository-native integrity, fresh exact-head gates, and an explicit merge disposition.

## Zenodo

**Role:** archival record and DOI-bearing release when separately authorized.

**Package candidate:** articles, source binding, claim matrix, dissemination manifest, and checksums.

**Required before effect:** exact byte freeze, complete metadata, authorship and licence review, explicit production authorization, authenticated upload, public-record observation, and public-byte revalidation.

```text
ZENODO_READY != DOI_OBSERVED
```

Current state: `NOT_EXECUTED`.

## IETF

**Role:** protocol and interoperability material, especially the Effect-Acknowledgement lane.

The historical `EETF` token remains in the verbatim source. The authorized routing target is `IETF`.

**Required before effect:** a concrete Internet-Draft name and revision, exact XML/TXT/HTML source set, current renderer validation, authorship metadata, submission-window and account checks, submission receipt, and later Datatracker reobservation.

```text
IETF_PACKAGE_PREPARED != IETF_SUBMITTED
IETF_SUBMITTED != IETF_CONSENSUS
```

Current state: `NOT_EXECUTED`.

## arXiv

**Role:** scientific preprint.

**Required before effect:** a self-contained source archive, reproducible PDF, abstract, categories, author metadata, bibliography and figures, claim/evidence boundary review, account/endorsement readiness, submission receipt, and announced-identifier reobservation.

```text
ARXIV_READY != ARXIV_IDENTIFIER_OBSERVED
```

Current state: `NOT_EXECUTED`.

## Wikipedia

**Role:** possible neutral encyclopedic treatment only after suitable independent secondary-source coverage exists.

Repository files, author statements, project pages, Zenodo records, and self-authored preprints are primary-source material. They do not by themselves establish independent notability or neutral reception.

**Required before an edit:** a narrowly scoped topic, independent reliable secondary sources, conflict-of-interest handling, neutral language, talk-page-first consideration where appropriate, and post-edit reobservation.

```text
WIKIPEDIA_READY != WIKIPEDIA_ACCEPTED
```

Current state: `NOT_EXECUTED`.

## IEEE

**Role:** peer-reviewed journal or conference submission.

**Required before effect:** one concrete venue, scope match, venue-specific manuscript and formatting, contribution and related-work sections, reproducibility appendix, conflict and funding declarations, cover letter, single-submission check, authenticated submission, and manuscript-ID receipt.

```text
IEEE_DRAFT != IEEE_SUBMITTED
IEEE_SUBMITTED != IEEE_ACCEPTED
```

Current state: `NOT_EXECUTED`.

## E-mail correspondence

**Role:** recipient-bound requests for review, venue guidance, editorial handling, or standards discussion.

Every message requires:

```text
REAL_RECIPIENT
CONCRETE_PURPOSE
EXACT_ARTIFACT
HEAD/TREE OR FILE DIGEST
REQUESTED_ACTION
CLAIM/EVIDENCE BOUNDARY
```

A template is not a resolved draft. A resolved draft is not a sent message. A sent message is not a received or answered message.

Current state: `NOT_EXECUTED`.

## Routing decision

The next permissible edge is repository-internal:

```text
COMPLETE_BUNDLE
→ FREEZE_CHECKSUMS
→ EXACT_HEAD_VERIFY
→ REVIEW
```

External effects remain `HOLD`.
