# From Exact Causal Binding to a Falsifiable Planck-Tick Gap Law

**Author:** Ingolf Lohmann  
**Date:** 2026-09-03  
**Status:** falsifiable physical hypothesis / working-paper candidate; not empirically confirmed

This publication bundle is the direct physics successor to the QIK-VRT H5 and measurement-derived-dimensions work. It freezes the v1 physical postulate

```text
i hbar [psi(t+tP)-psi(t-tP)]/(2 tP) = (H-E0 I) psi(t)
```

and the low-energy phase-frequency prediction

```text
omega_Q = asin(DeltaE/EP)/tP
Delta omega = [asin(DeltaE/EP)-DeltaE/EP]/tP > 0
```

with no free deformation coefficient.

Canonical repository artifacts:

- `physics/planck_tick_gap_law_v1.json` - machine-readable physical hypothesis and frozen numerical predictions.
- `docs/research/2026-09-03-planck-tick-gap-law/README.md` - detailed derivation and falsifier.
- `docs/research/2026-09-03-planck-tick-gap-law/QIKVRT_Planck_Tick_Gap_Law_2026-09-03.tex` - publication-grade LaTeX manuscript.
- `release/planck-tick-gap-law-zenodo-v1/ZENODO_METADATA.json` - Zenodo metadata binding.
- `release/planck-tick-gap-law-arxiv-v1/ARXIV_SUBMISSION.md` - arXiv submission metadata and category guidance.
- PR #962 - exact physical-hypothesis carrier and review surface.

Repository-native Zenodo publication is authorized once and is wired to run after legitimate promotion to `main`, using the `zenodo-production` environment and `ZENODO_ACCESS_TOKEN`. It persists the resulting DOI/record/file hashes on a separate receipt PR.

The arXiv source package is prepared from the same manuscript. arXiv submission itself requires an authenticated arXiv submitter account/moderation path and is not represented as complete until an arXiv identifier is read back.

Scientific boundary:

```text
PHYSICAL_HYPOTHESIS_BOUND=true
DIFFERENTIATING_PREDICTION_FROZEN=true
EMPIRICAL_CORRESPONDENCE=false
INDEPENDENT_REPRODUCTION=false
PASS=false
FINAL_PASS=false
EFFECT_ACK_DONE=false
```

Earlier connected QIK-VRT Zenodo anchor: `10.5281/zenodo.21488116`.
