# arXiv submission candidate: Observer-Relative Retrocausality

Status: **local staging candidate only; not submitted to arXiv.**

This package contains the concise English synthesis requested for an arXiv
submission. It is deliberately separate from the QIK-VRT repository because
the repository-wide integrity bootloader was blocked during preparation. No
repository, Zenodo, arXiv, IETF, GitHub, or other external mutation was made
while producing this staging package.

## Contents

- `main.tex` - arXiv-compatible LaTeX source.
- `main.pdf` - PDF built from the exact source with pdfLaTeX.
- `arxiv_submission_manifest.json` - publication scope, proposed metadata,
  source bindings, and claim boundaries.
- `PDF_RENDER_VALIDATION.json` - PDF build and visual-rendering receipt.
- `SHA256SUMS` - SHA-256 digests for the frozen staging files.
- `arxiv-source.tar.gz` - minimal source archive for the arXiv upload step.
- `EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md` - action-time authorization form for
  the final, frozen upload archive and metadata.

## Suggested arXiv metadata

- Title: *Observer-Relative Retrocausality in Distributed Information Systems:
  A Formal Existence Result, Executable Witnesses, and Evidence-Bound Effect
  Control*
- Author: Ingolf Lohmann
- Primary category: `cs.DC` (Distributed, Parallel, and Cluster Computing)
- Suggested cross-lists: `cs.CR` and `cs.LO`
- Do not present this manuscript as a quant-ph result without an independent
  physics-focused review. The delayed-choice discussion is explicitly a
  structural connection, not a unique interpretation or a backward-signalling
  claim.

## Reproducible build

The file is designed for the standard arXiv pdfLaTeX path:

```sh
SOURCE_DATE_EPOCH=1786492800 FORCE_SOURCE_DATE=1 \
  pdflatex -interaction=nonstopmode -halt-on-error main.tex
SOURCE_DATE_EPOCH=1786492800 FORCE_SOURCE_DATE=1 \
  pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The generated PDF was rendered page-by-page for visual inspection. The
validation receipt records the exact build outcome.

## References and status boundaries

The manuscript links to the already public QIK-VRT Zenodo record
[10.5281/zenodo.21888130](https://doi.org/10.5281/zenodo.21888130) and to
immutable Authority and Mirror GitHub snapshots. It identifies QIK-VRT and its
universe-level correspondence as Ingolf Lohmann's research programme and
author-attributed thesis.

The manuscript uses *observer-relative retrocausality* as the precise
operational term defined in the paper: an inverse relation between
receiver-local order and authenticated source-reference order. It explicitly
does not claim backward-running proper time, reception before emission, past
overwrite, causal loops, superluminal signalling, a controllable message to
the past, independent empirical confirmation, or scientific consensus.

The EAP Temporal-Provenance and Reference Profile (EAP-TPRP) is described as a
local, not-yet-submitted companion proposal. The cited
`draft-lohmann-qikvrt-effect-ack-03` is an active individual Internet-Draft,
not an RFC, IETF standard, working-group product, consensus result, or IETF
endorsement.

## Before any external submission

Freeze the exact archive and metadata, bind them to a new author decision,
check account-facing fields in the destination UI, and obtain the required
action-time confirmation. A platform upload or submission must use only the
then-authorized exact files.
