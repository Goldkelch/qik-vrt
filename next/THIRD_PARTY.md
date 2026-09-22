<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Documentation: OpenAI Codex. -->

# Dependency provenance

The C90 core reuses this repository's EAP and QVRT v1 sources under its existing code license.
Preserved reference sources and fixtures retain their original attribution.
New implementation is PolyForm-Noncommercial-1.0.0; documentation is CC-BY-NC-ND-4.0.

Cargo resolves the following packages under their declared licenses. Exact source checksums
are in Cargo.lock. No third-party package is relicensed by this repository.

| Package | Version | Declared license |
| --- | --- | --- |
| block-buffer | 0.10.4 | MIT OR Apache-2.0 |
| cfg-if | 1.0.5 | MIT OR Apache-2.0 |
| cpufeatures | 0.2.17 | MIT OR Apache-2.0 |
| crypto-common | 0.1.7 | MIT OR Apache-2.0 |
| digest | 0.10.7 | MIT OR Apache-2.0 |
| fs2 | 0.4.3 | MIT/Apache-2.0 |
| generic-array | 0.14.7 | MIT |
| hmac | 0.12.1 | MIT OR Apache-2.0 |
| itoa | 1.0.18 | MIT OR Apache-2.0 |
| libc | 0.2.189 | MIT OR Apache-2.0 |
| memchr | 2.8.3 | Unlicense OR MIT |
| proc-macro2 | 1.0.107 | MIT OR Apache-2.0 |
| quote | 1.0.47 | MIT OR Apache-2.0 |
| ryu | 1.0.23 | Apache-2.0 OR BSL-1.0 |
| serde | 1.0.219 | MIT OR Apache-2.0 |
| serde_derive | 1.0.219 | MIT OR Apache-2.0 |
| serde_json | 1.0.140 | MIT OR Apache-2.0 |
| sha2 | 0.10.8 | MIT OR Apache-2.0 |
| subtle | 2.6.1 | BSD-3-Clause |
| syn | 2.0.119 | MIT OR Apache-2.0 |
| typenum | 1.20.1 | MIT OR Apache-2.0 |
| unicode-ident | 1.0.26 | (MIT OR Apache-2.0) AND Unicode-3.0 |
| version_check | 0.9.5 | MIT/Apache-2.0 |
| winapi | 0.3.9 | MIT/Apache-2.0 |
| winapi-i686-pc-windows-gnu | 0.4.0 | MIT/Apache-2.0 |
| winapi-x86_64-pc-windows-gnu | 0.4.0 | MIT/Apache-2.0 |


Compiler and runtime tools remain separate dependencies. Provisioned versions, source URLs,
license metadata and archive SHA-256 digests are recorded in toolchains.lock.json.
The repository runtime registry records host tool contracts. Tool installation does not
relicense any compiler, runtime or package.
