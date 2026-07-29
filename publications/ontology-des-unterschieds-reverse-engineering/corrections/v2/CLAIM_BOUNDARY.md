<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Claim boundary for the versioned correction candidate

## Exact source binding

This boundary artifact belongs only to the versioned correction candidate for:

- batch: `CONTENT-DISPOSITION-BATCH-002`
- subject: `SUBJECT-43c59da1cfd26267`
- Zenodo record: `21582781`
- DOI: `10.5281/zenodo.21582781`
- frozen original article SHA-256: `0cc8077b032d805406f5cafe599dfa91f90e28a5bfa68292aaf4aaa232058589`
- frozen meta-review SHA-256: `855687ec791c5d054ea235ad0388217954fdc0dc2d3e053684820a46289ac629`

The already published bytes are historical evidence and are not rewritten by this
candidate. The correction is additive and versioned.

## Bound overclaim findings

The retrospective claim matrix detected evidence-overreach because the frozen
record contains boundary-sensitive expressions recognized by the deterministic
Batch-002 classifier. The correction binds these exact extracted claims:

1. `21582781-META-REVIEW-md-0002` — referential use of the article title.
2. `21582781-ORIGINAL-ARTICLE-md-0001` — the article title.
3. `21582781-ORIGINAL-ARTICLE-md-0067` — “Ein universaler
   Reverse-Engineering-Mechanismus muss nicht jedes Ergebnis erraten.”
4. `21582781-ORIGINAL-ARTICLE-md-0211` — “Alles Erkennbare beginnt damit,
   dass etwas nicht dasselbe ist.”

The fourth statement is read as a scope-bounded methodological premise about
recognition in this model, not as an empirically established universal law over
all possible cognition or reality.

## Corrected scientific reading

In this candidate, *universal* and *universalisierbar* mean only that the
following structural questions can be posed across explicitly modeled domains:

- Which distinctions, states and relations are represented?
- Which transition or effect is being claimed?
- Which evidence supports that claim?
- Which information was lost?
- Which reconstruction boundary follows?
- Which responsible release state is justified?

This does **not** establish:

- a universal solver for arbitrary problems;
- a completeness theorem for science or informatics;
- automatic historical inversion from non-injective observations;
- empirical confirmation of every domain-specific statement;
- replacement of domain models, measurements or laws;
- repository-wide `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE`.

Every application remains conditional on an explicit state space, observation
map, target semantics, assumptions, evidence and domain-specific validation.

## Reconstruction boundary

Let an observation be a map \(o:X\to Y\). Exact historical inversion requires
injectivity on the relevant domain or additional distinguishing evidence.
A target semantics \(s:X\to S\) can still be reconstructed from an observation
when it is constant on every observation fibre:

\[
o(x_1)=o(x_2) \Longrightarrow s(x_1)=s(x_2).
\]

Otherwise the result remains `AMBIGUOUS`, `EVIDENCE_MISSING`,
`PARTIALLY_RECONSTRUCTABLE` or `IRREVERSIBLY_LOST`.

## Planck and physics boundary

The identities

\[
\ell_P/t_P=c,\qquad E_P/p_P=c,\qquad
\ell_Pp_P=\hbar,\qquad t_PE_P=\hbar
\]

follow from the selected conventional definitions of the Planck units. The
statement that exactly one elementary effect difference is transmitted per
elementary spacetime unit remains an interpretive hypothesis. It is not promoted
to a kernel-proved or empirically confirmed claim by this correction.

## Owner gate

This artifact creates a reviewable corrected candidate. It does not modify the
Zenodo record and does not complete the correction until Ingolf Lohmann records
an explicit owner decision.
