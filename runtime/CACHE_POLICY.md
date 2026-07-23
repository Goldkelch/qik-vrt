<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Runtime cache policy

## Purpose

The repository is the durable runtime authority. Runtime caches are reusable accelerators of that repository-defined runtime: exact tools, verified archives, wheelhouses, derived environments, receipts, and timing evidence are reused so repeated runs become faster without changing semantics or bypassing checks.

A cold cache and a warm cache MUST execute the same required checks and MUST produce semantically identical project outputs. Chat state, model memory, proof conclusions, review decisions, authentication, authorization, and publication state are never cache authority.

## Authority and location

Committed runtime authorities are the bootstrap source, toolchain locks, upstream checksums, provenance, third-party notices, cache-key definitions, validation tests, and recovery procedures under `runtime/`, `tools/`, and `tests/`.

Downloaded archives, extracted executables, virtual environments, package caches, timing data, and cache receipts are reusable material under `.qikvrt/toolchains/`, GitHub Actions caches, or an explicitly selected external cache directory. Large binary payloads SHOULD remain in content-addressed caches or reviewed release assets rather than ordinary Git history; their hashes, provenance, recipes, and receipts MUST remain reconstructable from the repository.

No credential may enter a runtime cache. This includes `GH_TOKEN`, `GITHUB_TOKEN`, Git credential-helper state, `gh auth login` state, cookies, SSH keys, signing keys, and package-registry credentials.

## Cumulative runtime rule

Each successful runtime operation SHOULD leave the repository-defined runtime more capable, faster, more diagnosable, or more reproducible by improving an existing lock, bootstrap, cache recipe, receipt, test, recovery rule, or status emitter. `REUSE_BEFORE_CREATE` applies: extend the existing runtime and cache path before adding parallel machinery.

A tool needed repeatedly MUST acquire, in order:

1. an exact version and platform declaration;
2. an upstream source and cryptographic digest;
3. a deterministic bootstrap or restore path;
4. a cache key bound to all relevant inputs;
5. an execution self-test;
6. provenance and license metadata;
7. a failure/rollback procedure; and
8. integration with step-level progress telemetry.

## Keys and restoration

A shared CI cache key MUST contain all of:

1. operating system and architecture;
2. a format-version prefix;
3. exact interpreter and tool versions;
4. capability outcomes relevant to the selected runner;
5. a digest of `runtime/toolchains/**`; and
6. digests of every bootstrap used to consume the cache.

Restoration MUST use an exact key. Broad restore prefixes and cross-OS cache archives are prohibited. Every managed executable is compared against repo-hash-anchored source material or an equivalent verified receipt before execution. Cache metadata is not trusted merely because a hosting service returned it.

The shared CI cache may contain hash-locked archives and wheelhouses. Derived environments may be cached only when their path binding, platform binding, and validation contract are explicit. Every authorized install verifies locked inputs, stages changes atomically, self-tests the final path, and restores the previous valid state on failure.

Untrusted pull requests may read a default-branch cache where GitHub permits that behavior, but they MUST NOT publish a cache that a protected branch can later treat as authoritative. Cache-save steps run only for reviewed code on `main` or an explicitly dispatched trusted workflow after all contract checks pass.

## Step-level visibility

Every cache restore, miss, verification, install, derivation, self-test, save, rollback, and eviction decision is a discrete GitHub/runtime step and MUST produce a progress frame through the existing human-machine progress protocol. Cache work may not become a hidden interval.

## Effect boundary

- A cache hit is never `EFFECT_ACK_DONE`.
- No test, renderer validation, security check, license check, reviewer gate, or release check may be skipped because a previous result is cached.
- Compiled dependencies and verified tool environments may be reused; mandatory project checks execute again against the current tree.
- A mismatch, incomplete extraction, unexpected version, symlink/reparse point, or failed execution self-test is `BLOCK`, not a cache miss.
- Absence of an optional runtime in check-only mode is `CONTINUE` and causes no network or source-tree mutation.

## Installation and retention

Installation is opt-in where third-party terms require acceptance. Downloads use named HTTPS upstreams and locked hashes. Installation is staged, verified, atomically promoted, verified again in its final location, and rolled back if final verification fails.

GitHub-hosted caches are accelerators with service-defined retention and quota; durable reproducibility comes from committed locks, provenance, recipes, and tests. Durable large payloads use reviewed, content-addressed release assets or equivalent storage. Bootstrap scripts do not perform broad recursive deletion.

## Bounded adaptation

Automatic adaptation may reuse exact-key caches and collect non-authoritative timing/diagnostic evidence. Optimization of ordering, parallelism, or cache composition occurs through reviewed repository changes. It may never alter `EFFECT_ACK` predicates, lower review or test requirements, inject credentials, accept unverified tools, or treat cache state as proof authority.
