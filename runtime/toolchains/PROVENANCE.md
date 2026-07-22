<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Runtime toolchain provenance

No executable or authentication token is stored in this directory. The files
here define independently checkable versions, upstream locations, checksums,
and license boundaries for an optional local cache.

## GitHub CLI 2.96.0

- Upstream project: <https://github.com/cli/cli>
- Release: <https://github.com/cli/cli/releases/tag/v2.96.0>
- Release assets: `https://github.com/cli/cli/releases/download/v2.96.0/`
- Upstream checksum file retrieved on 2026-07-22.
- SHA-256 of the unmodified upstream checksum file:
  `fc046371efa250e2875208341a786a35a01717d5eebec6903e199a9b8a3f3565`.
- License: MIT; copyright GitHub Inc. See `THIRD_PARTY_NOTICES.md`.

The Linux amd64 archive was independently verified against the upstream hash.
Its cleanly extracted `gh` executable had 40,722,594 bytes and SHA-256
`56b8bbbb27b066ecb33dbef9a256dc9d1314adaeff0908a752feba6c34053b40`.
A separate incomplete extraction was rejected because its size and digest did
not match and it failed its execution self-test. On every supported platform,
the bootstrap therefore verifies the cached archive against the committed
upstream SHA-256, freshly extracts it, compares the candidate executable bytes
with that extraction, and only then runs `gh --version`.

The execution check requires the exact semantic version `2.96.0` and a
well-formed upstream build date. It does not hard-code one build date across
platforms: upstream may rebuild platform assets while retaining the release
version. Byte identity remains controlled by the platform-specific committed
archive SHA-256 and, for every cached executable, fresh re-extraction and byte
comparison.

The locked Windows ZIP assets use the upstream root-relative `bin/gh.exe`
layout. The Windows bootstrap verifies that exact layout instead of assuming
the directory prefix used by other archive formats.

Authentication is deliberately outside this runtime definition. Neither
`GH_TOKEN`, `GITHUB_TOKEN`, nor the state produced by `gh auth login` may be
committed or cached by these scripts.

## xml2rfc 3.34.0

- Upstream project: <https://github.com/ietf-tools/xml2rfc>
- Package index: <https://pypi.org/project/xml2rfc/3.34.0/>
- Bound renderer interpreter: CPython 3.12.13, x64.
- Supported wheel lock targets: Linux x64, macOS x64, and Windows x64.
- Exact direct version: `xml2rfc==3.34.0`.
- License: BSD-3-Clause; copyright IETF Trust. See
  `THIRD_PARTY_NOTICES.md`.

`requirements-xml2rfc-3.34.0.txt` records all 19 exact packages, including
`pypdf==6.10.0`, and the SHA-256 values of the PyPI wheels selected by CPython
3.12.13 on the three x64 runner families. Source distributions are excluded.
The lock file itself has SHA-256
`18d213a57ee9005adaf0906c8287a04af1692f15a651c3b9c8e5cfdcebb1fd2c`,
also recorded in `TOOLCHAIN.lock.tsv`.

The hosted CI toolcache currently supplies the exact CPython 3.12.13 runtime
on Linux x64 but not on the selected macOS Intel and Windows x64 runners. Those
runners therefore execute the independently locked GitHub-CLI and bootstrap
failure contracts and report the renderer capability as unavailable. The
workflow probes the exact version on every run and automatically activates the
same XML install/render gate if it becomes available. A fallback Python 3.12
is used only for non-renderer contract checks and never satisfies the renderer
identity predicate.

Installation requires explicit third-party consent. Pip runs in isolated mode
with its configuration file set to the platform null device, an explicit PyPI
index for initial wheel retrieval, `--only-binary=:all:`, `--no-deps`, and
`--require-hashes`. A restored wheelhouse is copied through pip's offline hash
verification. The final venv is always newly derived, offline, from that
verified wheel set at its final absolute path with copied interpreter
launchers. Check-only mode never executes a pre-existing venv.

## Trust boundary

Checksums establish byte identity with named upstream assets; they do not prove
the absence of upstream defects. A cache hit is an optimization and never an
`EFFECT_ACK_DONE`, scientific result, review, authentication, or publication
authorization.

## Additional version contracts

The remaining profiles deliberately name contracts rather than inventing
archive hashes for tools supplied by an operating system, a language package
manager, or an independently managed formal toolchain:

| Profile | Required contract | Automatic installation |
|---|---|---|
| `core` | a compiler that accepts the strict ANSI-C90 probe | no |
| `ietf` | CPython 3.12.13 x64, `xml2rfc==3.34.0`, and pypdf 6.10.0 from hash-locked wheels | fresh locked environment, with consent |
| `formal` | Python 3.12.x, pytest 9.1.1, Node 24.x, Zod 4.1.12, Lean 4.19.0 and Lake | no |
| `audio` | Node 24.x, sherpa-onnx-node 1.13.4, FFmpeg and matching FFprobe | no |
| `publication` | XeLaTeX, `pdftotext`, and `pdftoppm` with reported versions | no |
| `all` | every preceding contract | xml2rfc only, with consent |

Zod and sherpa-onnx-node versions are already fixed by their respective npm
lockfiles. Pytest is fixed by the formalization requirements file. `Lean
4.19.0` is the formal kernel version used by the evidence package; Node 24 and
Python 3.12 are the corresponding execution contracts.

FFmpeg, XeLaTeX, Poppler and C compilers are commonly distribution builds with
feature- and license-dependent packaging. The repository therefore records no
false universal binary hash or license simplification for them. Check-only
mode reports `CONTINUE` until the named commands and behavioral contracts are
present. Their installation remains an operator/platform responsibility.
