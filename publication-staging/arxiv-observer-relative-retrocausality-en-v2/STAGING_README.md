<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# arXiv v2 local upload package — current synthesis

Status: **`LOCAL_STAGING_READY_FOR_TARGET_REOBSERVATION_NOT_SUBMITTED`**.

This staging directory contains the frozen upload candidate for the current
English successor manuscript.  It is not the historical
`arxiv-en-candidate/` and does not replace its bytes.

Its current clarification distinguishes a coordinate assignment of a
spacelike-separated source observer's local-present event to another
observer's coordinate future from a causal-future relation.  No source-bound
record is available until future-directed delivery reaches the receiver.

## Exact candidate

| Artifact | SHA-256 | Role |
|---|---|---|
| `arxiv-source.tar.gz` | `5202c13e8a9e4934de0c09b7f238fc80073410c5d52ef231e0c05d035c00322a` | Minimal deterministic arXiv source archive (self-contained `main.tex` only). |
| `main.pdf` | `943331e2297b9663b02471d51d9adcb277f191fafb1e9d15f8ef2ba63730b12c` | 8-page rendering built from the frozen archive. |
| `main.tex` | `dfc5852e5986ab54b392acaddfe5b7a478e25b9589bd6d59eef035f51a1107cd` | Exact TeX source. |
| `README.md` | `9025a2cfa090e21dd11840d17bd7e1d834beed006c62ed0bf5ef64fe5bbd561b` | Staging/source claim-scope guide; not an upload-archive member. |

The rendered PDF was built twice using pdfLaTeX with
`SOURCE_DATE_EPOCH=1786665600` and `FORCE_SOURCE_DATE=1`.  Rebuilding from a
fresh extraction of the exact compressed archive produced a byte-identical PDF.
The visual-rendering receipt records the page-level check.

`ARXIV_LOCAL_COMPATIBILITY_VALIDATION.json` adds a fresh archive-level
preflight: the archive has only the declared `main.tex` member, no unsafe paths or
links, no external source dependencies, and a clean two-pass pdfLaTeX rebuild.
It records local compatibility evidence only; it is not an arXiv service
receipt.

## Submission boundary

The author has released the Zenodo/arXiv/IETF publication work in the shared
work context.  Before this package is actually transmitted, the arXiv account
and final title, author/affiliation, category, cross-list, comments, and
distribution-license fields must be freshly observed and bound with the exact
archive digest in `EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md`.

No arXiv upload, identifier, acceptance, announcement, endorsement, or other
external effect is represented by this directory.
