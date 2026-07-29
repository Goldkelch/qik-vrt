<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Owner-return package: corrected candidate for Batch 002

**Responsible owner:** Ingolf Lohmann  
**Return state:** `RETURNED_FOR_OWNER_ACCEPTANCE`  
**Authority base:** `6a1555cd5ad418d9b243e2514d3271fb6c3a1585`

## Corpus correction requiring the owner decision

The exact correction target is:

```text
batch      = CONTENT-DISPOSITION-BATCH-002
subject    = SUBJECT-43c59da1cfd26267
record     = 21582781
doi        = 10.5281/zenodo.21582781
reason     = Potential evidence-overreach without an explicit boundary artifact
```

The published bytes remain unchanged. The candidate adds an explicit,
versioned boundary for the three machine-bound overclaim findings and preserves
the original article as historical evidence.

Candidate artifacts:

```text
publications/ontology-des-unterschieds-reverse-engineering/corrections/v2/CLAIM_BOUNDARY.md
sha256 b5852d0dc81c989875df4467eea270f64547b1e38f7317ec0c43e6f9251763bd

publications/ontology-des-unterschieds-reverse-engineering/corrections/v2/PUBLICATION_CORRECTION.json
sha256 b3eac6126cc3b1b209c98ecf760de2e0c3b3830082b9c652ae1d312fb28751dd

publications/ontology-des-unterschieds-reverse-engineering/corrections/v2/README.md
sha256 9b57f554b1a475b8ab38e4c6da8d2c448dd32ced8bf73d36636e6180fd4c47fe

release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/corrected-candidate/SUBJECT-43c59da1cfd26267/CORRECTED_CLAIM_DISPOSITION.json
sha256 c36a1a6d21b52bb4cc5f838b6fa2f2b84009b67fbde44b5397586cef0acd9447
```

## Separately returned Denk-Mengenlehre candidate

The supplied mathematical correction is materialized separately at:

```text
docs/axiome/denk_mengenlehre_corrected_candidate_v2.md
sha256 873ffe4bf893bf09dae73636da0d18ae86a86cc680b9dd18d165c614da685689
scope  DENK-MENGENLEHRE-BATCH-002
```

It is not falsely used to discharge the different Zenodo subject
`SUBJECT-43c59da1cfd26267`.

## Decision requested from Ingolf Lohmann

Record exactly one decision:

- `ACCEPT` — the additive boundary candidate is accepted for the next
  versioned publication preparation;
- `REQUEST_CHANGES` — the candidate remains blocked and the requested changes
  must be stated;
- `REJECT` — the candidate is not used.

No decision is inferred from repository creation or from this return package.
Until an explicit decision exists:

```text
OWNER_ACCEPTANCE                  = PENDING
CONTENT_CORRECTION_REVIEW_COMPLETE = false
ZENODO_MUTATION_AUTHORIZED         = false
PASS                               = false
FINAL_PASS                         = false
EFFECT_ACK_DONE                    = false
```
