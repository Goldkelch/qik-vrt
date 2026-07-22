# Verification status

**Snapshot date:** 2026-07-22

**Public repository heads inspected:**

- `Goldkelch/qik-vrt` at
  `a37cc450447d8095df71c07ecef6dd13d242dd8c`
- `ingolf-lohmann/qik-vrt` at
  `41e1ee0b31dcfad15fd35c6c68d221ba9d926ea5`
- common content tree:
  `c2fb00c593baea2652092c454e60161e7cf2b56f`

**Current verified object:** the unpublished 2026-07-22 working-tree repair set
based on that common public content tree. The two public commits have different
identities but identical content trees.

**License transition:** the public baseline and earlier Apache-2.0 grants remain
under Apache-2.0. Current QIK-VRT-controlled repair-set code carrying the new
notice is licensed prospectively under `PolyForm-Noncommercial-1.0.0`;
commercial use requires separate written permission. See
`LICENSE_TRANSITION.md` for the rights-chain boundary.

## Demonstrated locally

- The existing Python suite passes all 102 tests across nine modules containing
  test cases, with no failures or skips. Ten `test_*.py` files are matched; the
  tenth is the command-line offline-render verifier exercised separately.
- The strict ANSI-C90 Draft-01 core implementation matches an independently
  structured oracle over all 2,621,440 valid abstract snapshots. Its complete
  run performs 7,864,387 checks and passes.
- The exact five-state `EFFECT_ACK` priority model and DONE-only ordinary
  release behavior are executable and test covered.
- Bounded, fail-closed decision behavior, deterministic canonical protocol
  hashes, predecessor validation, and repository-scoped ingest, verify, stage,
  and release-status paths are covered by the local implementation and tests.
- The release path binds authorization, responsibility, provenance, workflow
  identity, planned asset bytes, local `HEAD`, remote digest evidence, and
  durable publication journals. Negative tests cover malformed, oversized,
  unauthenticated, expired, conflicting, tampered, and timeout inputs.
- The collective-adaptive cognition runtime emits evidence and reviewable
  proposals while remaining in `EFFECT_ACK_CONTINUE`. It does not assert human,
  organizational, causal, or identity consensus from observer identifiers.
- Automatic acceleration is limited to exact-key reuse of a verified runtime
  cache. Performance measurements can produce a reviewable proposal only; they
  do not autonomously reorder work, skip a mandatory gate, approve a change, or
  authorize a repository, publication, protocol, network, or physical effect.
- POSIX bootstrap, cache-manipulation, cleanup, and platform-simulation tests
  pass. The PowerShell implementation has static coverage but remains pending
  real execution in Windows CI.
- The reproducible scientific bundle passes its finite-model proof while
  explicitly separating process universalizability, semantic factorization on
  observation fibres, conditional historical inversion, and conditional
  cyberphysical effect control.
- A durable local gate regenerates the proof report byte-for-byte, rejects
  optimized Python mode, and verifies complete SHA-256 coverage of the bundle.
- Python 3.12.13 and `xml2rfc` 3.34.0 validate the Draft-01 XML and reproduce
  the clean TXT and HTML renderings. The existing versioned bytes are preserved
  because the fresh outputs are identical; no normative Draft-01 change is
  required.
- The locked offline renderer is also exercised by the adaptive-runtime CI
  contract on Linux x64, macOS Intel, and Windows x64 pull requests.
- The scientific PDF renders as six A4 pages and passes local visual inspection.

The exact component commands and counts are recorded in
[BUILD_SUMMARY.md](BUILD_SUMMARY.md). The canonical integrity files are current
for this snapshot, and the final aggregate `make test` passes against them.

Authorization behavior is covered by local tests. No claim is made that a real
externally authorized publication `master-gate` execution occurred in this
workspace state.

## Current external state

The 2026-07-22 working-tree repair set has not yet been pushed, merged, or
tagged in either GitHub repository. The connected GitHub authorization and the
existing `ZENODO_ACCESS_TOKEN` Actions secret have been verified; GitHub
publication and Zenodo deposition remain pending execution by the bound remote
automation. A tag, GitHub CI run, Zenodo record, or DOI for this exact state
must not be inferred from local results.

No IETF Datatracker submission has been performed. XML, TXT, and HTML rendering
and validation are local preservation and submission-preview steps only.

## Not demonstrated

- Zenodo ingestion or a DOI for this exact scientific finding.
- A GitHub commit, merge, tag, release object, or CI result for this exact
  working-tree state.
- Windows PowerShell execution of the new runtime bootstrap outside static
  inspection; that check remains pending Windows CI.
- Non-bypassability across every possible downstream software or hardware
  integration.
- Production internet-service hardening, independent security audit, formal
  verification, or cross-platform certification.
- Historical priority, scientific novelty, peer review, standards status,
  external adoption, or correctness of every archived claim.
- A universal decoder, recovery of lost or never-observed information,
  guaranteed termination, eventual `EFFECT_ACK_DONE`, or unconditional
  cyberphysical safety.
- Truth of legal, medical, psychological, physical, metaphysical, religious,
  historical, UAP, or personal-event assertions supplied to the software.

## Precise haltpoint and reconstruction claim

The repair set makes the QIK-VRT effect haltpoint **defined, described,
executable, testable, and applicable as a bounded policy/effect gate**. This is
not a solution of the classical undecidable halting problem. The mechanism can
organize a reverse-engineering process where observations, access, semantic
models, resources, authorization, and effective computation are sufficient. It
does not prove that every computational artifact or every lost historical state
is recoverable from arbitrary observations.

Calling the architecture a paradigm shift, revolution, or evolution is a
theoretical and historical assessment whose field-wide status depends on
independent review, reproduction, and adoption.

## Current authority

Current verification authority consists of the active source files and tests,
this status, `BUILD_SUMMARY.*`, and the current canonical integrity trio:

- `REPOSITORY_FILE_MANIFEST.json`
- `SHA256SUMS.txt`
- `REPOSITORY_FILE_MANIFEST.json.sha256`

Earlier `PASS`, `READY`, delivery, or test reports are retained as historical
records only. They do not override a current failure or the boundaries above.
The detailed classification is recorded in
[HISTORICAL_ARTIFACT_BOUNDARIES.md](HISTORICAL_ARTIFACT_BOUNDARIES.md).

Copyright 2026 Ingolf Lohmann. Non-source content: CC BY-NC-ND 4.0 unless a
file states otherwise.
