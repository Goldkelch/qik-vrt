<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Changelog

This file summarizes current public milestones. Git history and release pages
remain the authoritative detailed record.

## 2026.07.24 — synchronized repository mesh snapshot

- Synchronized the Authority and Mirror repositories through the consolidated
  dependency-security maintenance state and authenticated repository-native
  audio-request interface.
- Refreshed `README.md` and `STATUS.md` with the published Zenodo status
  clarification, Formalization Alpha 3, and Charter records.
- Added common annotated tag `v2026.07.24-repository-mesh-sync-1.0.0` only
  after both `main` branches expose the same Git tree and repository integrity
  verifies in each repository.
- No GitHub Release object or new Zenodo record is created by this synchronization.

## 2026.07.22 — EFFECT_ACK universality 1.0.0

- Added the EFFECT_ACK universality working paper, executable proof report,
  exact reconstruction and inversion boundaries, and a documented conclusion
  that Draft `-01` requires no normative change.
- Added a strict ANSI-C90 five-state decision core with exhaustive comparison
  against an independently structured Draft-01 priority oracle.
- Added checksum-bound GitHub CLI and `xml2rfc` runtime contracts, rebuildable
  cache policy, pinned CI dependencies, and platform-specific bootstraps that
  never persist credentials.
- Added a bounded collective-adaptive protocol: exact-key cache reuse speeds
  later environment construction automatically, while performance observations
  produce proposal-only evidence. Reordering requires a separately reviewed
  implementation; tests, review, `EFFECT_ACK_DONE`, merge, publication, release
  and tagging remain protected gates.
- Published the scientific finding as working paper
  [10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773) and the
  deterministic tagged source-tree export as software
  [10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774).
- Added annotated tag `v2026.07.22-effect-ack-universality-1.0.0` to both
  repositories with identical content trees. No GitHub Release object and no
  IETF Datatracker submission were created.
- Competition-readiness documentation, community guidance, and a no-network
  effect-haltpoint demonstration were merged into `main` through
  [PR #1](https://github.com/Goldkelch/qik-vrt/pull/1) at merge commit
  `0d9c90eaeec73405e0a360e94830e7d28db2bbc2`. The fixed release tag remains
  unchanged.

## 2026.07.22 — IETF EFFECT_ACK Draft -01

- Recorded the published `draft-lohmann-qikvrt-effect-ack-01` revision with
  official Datatracker and archive URLs, byte counts, and SHA-256 digests.
- Updated current source, documentation, and acceptance anchors to revision
  `-01` while preserving revision `-00` provenance and release evidence.
- Integrated the reviewed machine-verifiable formalization and offline
  transcription tooling across the public two-node repository mesh.
- Published tag `v2026.07.22-ietf-effect-ack-01` without moving or replacing
  any earlier tag.

## 2026.07.20 — Wirkungshaltepunkt-Evolution

- Published the five-state QIK-VRT effect-haltpoint reference implementation.
- Made `EFFECT_ACK_DONE` the sole ordinary-release state.
- Added bounded, fail-closed decision paths, canonical protocol hashes,
  versioned responsibility records, API and security controls, integrity
  tooling, and release-bound publication checks.
- Verified 102 tests in nine modules, including 41 protocol/conformance tests
  and five license-transition tests.
- Published release tag
  `v2026.07.20-wirkungshaltepunkt-evolution` at commit
  `a8a9cb2666a91411489d4fc90a5306908f8428ea`.
