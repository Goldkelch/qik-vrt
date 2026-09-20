<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# QIK-VRT finite-channel challenge, 2026-09-20

This package contains a corrected German working-paper candidate, ten Lean
theorems, existing EFFECT_ACK conformance evidence and an offline experimental
scorer. **No physical future-to-past experiment has been performed.**

- Read ARTICLE_DE.md and QIKVRT_Beweis_und_Challenge.pdf for the complete candidate.
- Read CHANGE_NOTICE.md before comparing the candidate with ORIGINAL_STATEMENT_DE.md.
- CLAIM_MATRIX.json assigns every substantive claim a scope and disposition.
- CHALLENGE_PROTOCOL.md is a protocol draft, not an already registered study.
- KERNEL_RECEIPT.json binds a real local Lean execution and exact source bytes.
- PUBLICATION_STATUS.json states the remaining publication blockers.

## Reproduce the proof and checks

Use the official Lean 4.19.0 release (commit
6caaee842e9495688c1567e78c0e68dbb96942aa), Python 3 and this repository checkout.
Only Lean Std and the Python standard library are used for verification.

```sh
python3 -B docs/publications/2026-09-20-finite-channel-challenge/verify.py \
  --lean /absolute/path/to/lean-4.19.0-linux/bin/lean \
  --output /tmp/qikvrt-finite-channel-verification
```

The command runs Lean, checks the complete ten-theorem inventory and axiom
audit, then runs the existing EFFECT_ACK suite and the ten synthetic scorer
tests. On an exact committed source it emits KERNEL_VERIFIED with
workflow.kind = LOCAL_LEAN_CLI. This is not a GitHub Actions success claim.
Run outputs include timestamps and elapsed times; compare bound source hashes,
theorems and results, not incidental run timestamps.

```sh
python3 tools/qikvrt_integrity.py verify
```

The PDF renderer uses ReportLab and system DejaVu fonts. Recreate it by running
render_pdf.py in this directory. The verification boundary is the Lean source
and the attached kernel output; typography is not evidence of proof.

## Reuse decision

Existing publications at PR #1083 (537fba16f9e0d8294624204853aca4fb3082a9a8)
and PR #1085 (f30d4bcc8c54d915981abad03ed5f5985779191b) already distinguish a
virtual channel and an operational physical channel. They are reused as
sources, and their files and review state are not rewritten. The former leaves
its general finite-transport paper arguments OPEN; the latter provides no
ten-theorem kernel artifact or executable fixed-size challenge scorer. The
present additional directory supplies those missing, task-specific carriers.

verify.py imports parse_axioms from the existing QCE receipt tool and reuses
tests/test_effect_ack_conformance.py without changes. Its local receipt writer
is needed because the existing QCE writer hardcodes 36 different theorems.
render_pdf.py adapts the layout mechanism of the PR #1085 renderer with explicit
AI-contribution attribution and escaped text. The generic repository integrity
and Zenodo proof/publisher tools remain unchanged. No new GitHub workflow,
policy exception, native gate bypass, or production implementation change is
introduced.

## Licenses

Documents and JSON metadata: CC-BY-NC-ND-4.0. Python and Lean sources:
PolyForm-Noncommercial-1.0.0. See LICENSE_NOTICE.md. This is a mixed-license
repository package, not a relicensing of its sources under one document
license. AI authorship and the owner's pending decision are recorded in
state/work_units/FINITE_CHANNEL_CHALLENGE_20260920.json.

## Publication boundary

The repository branch persists the work. It is not an approval or merge into
main. Zenodo publication additionally requires the exact corrected candidate
return, canonical candidate-bound owner authorization and an authenticated
publisher. PUBLICATION_STATUS.json must be consulted before any upload.
