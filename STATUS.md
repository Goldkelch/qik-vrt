# Verification status

**Snapshot date:** 2026-07-21

**Baseline inspected:** public checkout at commit
`8ae1884116221087bdcc75eed9905bb80bdd9e95`, followed by the repair set carried
by the repository commit that publishes this status.

**License transition:** the public baseline and earlier Apache-2.0 grants remain
under Apache-2.0. Current QIK-VRT-controlled repair-set code carrying the new
notice is licensed prospectively under `PolyForm-Noncommercial-1.0.0`;
commercial use requires separate written permission. See
`LICENSE_TRANSITION.md` for the rights-chain boundary.

## Demonstrated locally

- Exact five-state `EFFECT_ACK` model and DONE-only ordinary release.
- Bounded, fail-closed decision behavior, deterministic canonical protocol
  hashes, immutable protocol versions, predecessor validation, and optional
  external trusted hash anchors.
- Authenticated, repository-scoped API paths for ingest, verify, stage, and
  release status.
- Explicit effect authorization and responsibility binding before non-dry mutation.
- Content-addressed storage/staging, append-only provenance, idempotent replay,
  replay-conflict isolation, transaction recovery, symlink/path rejection,
  and hash-linked audit records.
- HMAC-authenticated, repository- and artifact-bound remote release
  attestation before DONE.
- Authorization-before-effect launcher, master gate, safe publication planner,
  durable publication effect journal, bounded subprocess execution, unique
  per-run logging, and deterministic repository-integrity tooling.
- Release assets bound to their planned bytes and local `HEAD`, with symlink
  rejection and post-effect comparison against GitHub's remote SHA-256 and size.
- Descendant process-group termination, crash-recoverable integrity locking,
  byte-safe JSONL logging, and bounded symlink-safe authorization records with
  fail-closed operation-scope parsing.
- Exact prior-run binding before workflow state restoration: authenticated API
  metadata must match the repository, workflow path, source commit, allowed
  event, completed status, and successful conclusion.
- Canonically encoded 32--128 byte bearer/HMAC secrets with role separation,
  plus exact cross-binding of ingest provenance, receipt, recovery transaction,
  effect set, result hash, and responsibility protocol.
- Negative tests for malformed, oversized, unauthenticated, expired,
  conflicting, tampered, and timeout inputs.

The exact command and final counts are recorded in [BUILD_SUMMARY.md](BUILD_SUMMARY.md)
after the canonical manifest has been regenerated and the final test run has
completed.

The final local `make test`, canonical integrity verification, and the real
authorization-bound launcher `master-gate` all pass on this workspace state.

## Demonstrated remotely for the fixed public release

- Public release tag
  [`v2026.07.20-wirkungshaltepunkt-evolution`](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.20-wirkungshaltepunkt-evolution)
  resolves to commit `a8a9cb2666a91411489d4fc90a5306908f8428ea`.
- That commit carries tree
  `c5cefebd20b5836d730a4e9da82eeaa5c9363ebf`.
- [QIKVRT-CI run 29764193906](https://github.com/Goldkelch/qik-vrt/actions/runs/29764193906)
  completed successfully; its test job and every recorded step concluded
  `success`.
- [GitHub Pages run 29764192834](https://github.com/Goldkelch/qik-vrt/actions/runs/29764192834)
  completed successfully; build, status reporting, and deployment concluded
  `success`.
- The main document's recorded SHA-256 is
  `b4d3601c831db8bb70704a3dbed1e95deb47779de9a15bac8ea463f2693f89fe`.
- The `ingolf-lohmann/qik-vrt` mirror carries the same content tree at commit
  `5ecd01c3f2ed2a5222d2de22686f64dfcfcf1c92`. This proves mirror content
  equality for that tree, not independent third-party reproduction.

## Not demonstrated

- Zenodo ingestion or a DOI for this exact release.
- Non-bypassability across every possible downstream software or hardware
  integration.
- Production internet-service hardening, independent security audit, formal
  verification, or cross-platform certification.
- Historical priority, scientific novelty, peer review, standards status,
  external adoption, or correctness of every archived claim.
- Truth of legal, medical, psychological, physical, metaphysical, religious,
  historical, UAP, or personal-event assertions supplied to the software.

## Precise haltpoint claim

The repair set makes the QIK-VRT effect haltpoint **defined, described,
executable, testable, and applicable as a bounded policy/effect gate**. This is
not a solution of the classical undecidable halting problem. Calling the
architecture a paradigm shift, revolution, or evolution is a theoretical and
historical assessment whose field-wide status depends on independent review,
reproduction, and adoption.

The public baseline commit named above does not contain the complete repaired
state described here. The exact repaired state is the content tree of the
fixed public release commit named above; it must not be attributed
retroactively to the baseline. Branch, release, CI, Pages, mirror, and future
archival status remain separately verifiable external effects.

## Current authority

Current verification authority consists of the active source files and tests,
this status, `BUILD_SUMMARY.*`, and the canonical integrity trio:

- `REPOSITORY_FILE_MANIFEST.json`
- `SHA256SUMS.txt`
- `REPOSITORY_FILE_MANIFEST.json.sha256`

Earlier `PASS`, `READY`, delivery, or test reports are retained as historical
records only. They do not override a current failure or the boundaries above.
The detailed classification is recorded in
[HISTORICAL_ARTIFACT_BOUNDARIES.md](HISTORICAL_ARTIFACT_BOUNDARIES.md).

Copyright 2026 Ingolf Lohmann. Non-source content: CC BY-NC-ND 4.0 unless a
file states otherwise.
