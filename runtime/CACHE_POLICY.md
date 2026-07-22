<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Runtime cache policy

## Purpose

Runtime caches reduce repeated downloads and environment construction. They do
not persist project cognition, proof, review, authentication, authorization, or
publication state. A cold cache and a warm cache MUST execute the same required
checks and MUST produce semantically identical project outputs.

## Authority and location

The committed authorities are the bootstrap source, toolchain lock, upstream
checksums, provenance, and third-party notices under `runtime/toolchains/`.
Downloaded archives, extracted executables, virtual environments, package
caches, timing data, and cache receipts are volatile material under
`.qikvrt/toolchains/` or an explicitly selected external cache directory. They
MUST NOT be committed and MUST NOT be included in release-integrity claims.

No credential may enter a runtime cache. This includes `GH_TOKEN`,
`GITHUB_TOKEN`, Git credential-helper state, `gh auth login` state, cookies,
SSH keys, signing keys, and package-registry credentials.

## Keys and restoration

A shared CI cache key MUST contain all of:

1. operating system and architecture;
2. a format-version prefix;
3. the exact renderer interpreter version (`3.12.13`);
4. the exact-renderer capability outcome for the selected hosted runner;
5. a digest of `runtime/toolchains/**`; and
6. digests of every runtime/GitHub-CLI bootstrap used to consume the cache.

Restoration MUST use an exact key. Broad restore prefixes and cross-OS cache
archives are prohibited. A runner without CPython 3.12.13 can warm only the
GitHub-CLI portion under a distinct capability key; it cannot seed or satisfy
the renderer cache. A GitHub CLI executable installed in or loaded from
the managed cache is compared byte-for-byte with a fresh extraction of the
repo-hash-anchored upstream archive before it is executed. Cache metadata is
not trusted merely because a hosting service returned it. In check-only mode,
an operator-selected `QIKVRT_GH` or system `gh` outside the managed cache can
only satisfy the exact-version execution check; it is not represented
as archive-derived, is never copied into the cache, and is outside the cache's
reproducibility claim.

The shared CI cache contains the hash-locked Python wheelhouse, never the
xml2rfc virtual environment. A local cache directory may contain the derived
venv for immediate use, but check-only mode deliberately does not execute it.
Every explicitly authorized install verifies the selected wheels with
`--require-hashes`, moves any prior local venv into rollback staging, and
derives a new venv at its final path before executing renderer code.

Untrusted pull requests may read a default-branch cache where GitHub permits
that behavior, but they MUST NOT publish a cache that a protected branch can
later treat as authoritative. Cache-save steps run only for reviewed code on
`main` or an explicitly dispatched trusted workflow after all contract checks
pass.

## Effect boundary

- A cache hit is never `EFFECT_ACK_DONE`.
- No test, renderer validation, security check, license check, reviewer gate,
  or release check may be skipped because a previous result is cached.
- Compiled dependencies and verified tool environments may be reused;
  mandatory project checks must execute again against the current tree.
- A mismatch, incomplete extraction, unexpected version, symlink/reparse point,
  or failed execution self-test is `BLOCK`, not a cache miss.
- Absence of an optional runtime in check-only mode is `CONTINUE` and causes no
  network or source-tree mutation.

## Installation and retention

Installation is opt-in and requires both an install flag and explicit
third-party acceptance. Downloads use named HTTPS upstreams and locked hashes
where upstream archives provide them. GitHub CLI installation is staged,
preverified, atomically moved, verified again in its final location, and rolled
back if that final verification fails. The XML renderer's wheelhouse is hash
verified before use; its venv is necessarily built at the final path because
console launchers bind that path, with the previous venv held in rollback
staging until all post-install checks pass. Python package installation runs
isolated from environment variables and user pip configuration, accepts binary
wheels only, and performs its final installation offline from the verified
wheelhouse.

GitHub-hosted caches are accelerators with service-defined retention and quota;
they are not permanent archives. Durable reproducibility comes from committed
locks and provenance, while durable releases use reviewed, content-addressed
release assets outside this cache. Owners should delete unused cache generations
through the hosting service after a lock update. Bootstrap scripts deliberately
do not perform broad recursive cache deletion.

## Bounded adaptation

Automatic adaptation is limited to exact-key cache reuse. Future timing-based
optimization may change job ordering or parallelism only through a reviewed
source change. It may never alter `EFFECT_ACK` predicates, lower review or test
requirements, modify source, merge a pull request, create a release, or submit
an Internet-Draft autonomously.
