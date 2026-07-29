# QIK-VRT Work Status

Repository: `Goldkelch/qik-vrt`

Post-acceptance overlay: `release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/post-acceptance/POST_ACCEPTANCE_STATUS_PROJECTION.json`

Batch-003 dispatch receipt: `release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-003/dispatch/BATCH_003_DISPATCH_RECEIPT.json`

Updated at: `2026-07-29T23:05:40Z`

Snapshot state: **`WORKING`**. Overall effect state:
**`EFFECT_ACK_CONTINUE`**. No unqualified repository-wide
`PASS`, `FINAL_PASS`, Zenodo publication or corpus completion is claimed.

`[████████████░░░░░░░] 63%` — Zenodo-Subject-Disposition
(12/19)

- ✓ Canonical 24-record union and 19 claim subjects bound
- ✓ Batch 001 terminally dispositioned
- ✓ Batch 002 correction accepted, promoted and reciprocally bound
- ✓ Batch 003 dispatched with six subjects
- ▶ First work package active: `SUBJECT-2581811b342e505d`
- □ Exact public `equality-receipts-index.json` freeze recovery
- □ Six Batch-003 subjects and one later subject remain disposition-incomplete
- □ Retrospective proof corpus and any later publication effect

## Bounded global claim scope

`qikvrt-global-claim-scope-v1`: **`FINAL_PASS`**, 100% inside its declared
finite boundary (92 claims,
54 primary kernel receipts,
3 claims retained `OPEN`). This bounded historical
scope does not establish completion of the Zenodo corpus or any unregistered
statement.

## Zenodo canonical-union corpus

`qikvrt-zenodo-canonical-union-2026-07-28-v1`: **`CONTINUE`**,
12/19 subjects dispositioned
(63%), 7 open.

- Batch 002: `TERMINALLY_DISPOSITIONED`; post-acceptance chain `CORRECTION_ACCEPTED_PROMOTED_AND_RECIPROCALLY_BOUND`.
- Batch 003: `DISPATCHED_FIRST_SUBJECT_ACTIVE` with 6 subjects.
- Active subject: `SUBJECT-2581811b342e505d`.
- Active work package: `release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-003/dispatch/subjects/SUBJECT-2581811b342e505d/CLAIM_EXTRACTION_WORK_PACKAGE.json`.
- Claim extraction complete: `false`.
- Corpus `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, Zenodo mutation and
  proof-corpus publication: **not established**.

## Active evidence boundary

The exact historical receipt bytes are already repository-bound. The live
`evidence/receipts/index.json` contains later receipts and therefore cannot
substitute for the published `equality-receipts-index.json` freeze. Recovery and
hash verification of that exact public freeze is the first active technical
effect.

## NEXT

`RECOVER_EXACT_PUBLIC_INDEX_BYTES_AND_EXTRACT_CLASSIFY_BATCH_003_SUBJECT_2581811B342E505D`
