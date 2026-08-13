<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# arXiv v2 local upload package — current synthesis

Status: **`LOCAL_STAGING_READY_FOR_TARGET_REOBSERVATION_NOT_SUBMITTED`**.

This staging directory contains the frozen upload candidate for the current
English successor manuscript.  It is not the historical
`arxiv-en-candidate/` and does not replace its bytes.

## Exact candidate

| Artifact | SHA-256 | Role |
|---|---|---|
| `arxiv-source.tar.gz` | `95cb42a7e586b75c96d5fd10e462f04166c25a14e7223899344a01ef02371f1f` | Minimal deterministic arXiv source archive (self-contained `main.tex` only). |
| `main.pdf` | `1210f4aae243ae799dcf43533f73eef3c4f63995a1441b167333767821c0cd89` | 8-page rendering built from the frozen archive. |
| `main.tex` | `e6e147cfe5a9d7dda7041797278a259f7d9b91fb810a7207b952fb2f2fbdfdc7` | Exact TeX source. |
| `README.md` | `9025a2cfa090e21dd11840d17bd7e1d834beed006c62ed0bf5ef64fe5bbd561b` | Staging/source claim-scope guide; not an upload-archive member. |

The rendered PDF was built twice using pdfLaTeX with
`SOURCE_DATE_EPOCH=1786543200` and `FORCE_SOURCE_DATE=1`.  Rebuilding from a
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
