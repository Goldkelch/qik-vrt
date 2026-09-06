# QIK-VRT quantitative comparison article

This directory contains the German public-language comparison article requested
by the Product Owner and its machine-readable claim disposition.

## Files

- `QIKVRT_QUANTITATIVER_VERGLEICHSARTIKEL_DE_2026-08-29.md` — primary article.
- `CLAIM_MATRIX.json` — typed disposition of the article's central claims.
- `INTEGER_DGEMM_BENCHMARK.json` — one local, hash-bound reference-path run.

## Evidence boundary

The article distinguishes repository measurements, source-bound hardware and
standards facts, transparent derivations, formal results, interpretations, and
open hypotheses. It deliberately rejects a Receipt/s-to-Token/s conversion and
does not claim measured QIK-VRT speedup, hardware synthesis, physical
deployment, patent grant, market revenue, peer review, IETF consensus,
`PASS`, `FINAL_PASS`, or general `EFFECT_ACK_DONE`.

Version 1.1 integrates the Product Owner's 2026-08-29 audio instruction with
source SHA-256
`9cfcea675874a12035dee982ffea487c6666ea2569a86080a3ba9afc1c346532`.
It adds the complete empirical-to-virtual-to-real-to-empirical return path,
SKU-correct NVIDIA data, Amdahl and avoided-work scenarios, the exact
quadratic serial-frame formula, Internet-service mappings, the publication
queue audit, and the patent pre-disclosure boundary. The locally reconstructed
audio transcript is an ASR-assisted instruction record, not a
`VERBATIM_VERIFIED` artifact.

The article distinguishes the still-open PR #912 VHDL/codec candidate from the
older simulated VHDL scope already described in the repository. PR #912's
serial-frame arithmetic is not a physical board measurement and its RTL is not
the full Effect-Acknowledgement protocol.

The integer-DGEMM artifact records a portable binary64-to-INT8-limb reference
path and a native Python reference comparison. Its timings are environment
specific; native INT8 hardware, QIK-VRT speedup, energy savings, bit identity
and IEEE-754 status-flag identity remain unclaimed.

The article records PR #914's typed-executor repair as a draft exact-head
candidate. That candidate is not Authority-main until separately reviewed and
merged.

This directory remains an exact publication candidate. No Zenodo mutation,
patent filing, deployment, merge, hardware synthesis or physical effect is
created by preparing or testing it.
