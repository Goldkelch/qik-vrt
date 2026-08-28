<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT Mesh Linux proof runtime V1

## Exact result

V1 is a reproducible **OCI application image**, not a new Linux kernel and not
yet a complete Linux distribution.  The image contains one statically linked
POSIX process, `qikvrt-meshd`, and uses the Linux kernel supplied by the OCI
host.  It is deliberately small enough to establish the build, serialization,
HTTP and container boundary before adding protocol adapters.

The daemon is written in the common ANSI C89 / ISO C90 language subset and is
compiled twice, once with each compiler mode.  ANSI C89 and ISO C90 describe
substantially the same language revision; these are two conformance receipts
for one source, not two independent implementations.  Python remains the
independent high-level reference surface.  The proof target also assumes a
modern POSIX ABI: its external identifiers exceed the six significant external
characters that a minimal historical C90 implementation was required to
distinguish.

## Implemented path

`qikvrt-meshd` uses blocking POSIX sockets.  It waits in `accept(2)` and in
bounded reads; there is no periodic scan, sleep loop, blind retry or busy
polling.  A monotonic total I/O deadline (five seconds by default) prevents a
client from extending one request indefinitely byte by byte.  Every HTTP
connection carries exactly one request and is then closed.  No session state
is retained between requests.

The V1 endpoints are:

| Method | Target | Result |
|---|---|---|
| `GET` | `/healthz` | Process liveness and bounded candidate status |
| `GET` | `/.well-known/effect-ack` | Machine-readable capability boundary |
| `POST` | `/v1/effect-ack/evaluate` | Pure five-state evaluation of one closed 20-octet snapshot |

The POST body is `application/octet-stream`.  Octets
0..19 map in the declaration order of `qikvrt_effect_ack_input`; octet 12 is
the closed decision value 0..4 and every other octet is exactly 0 or 1.  This
is a deliberately bounded transport profile.  It is not the complete
Responsibility Record from the Internet-Draft and it never serializes native C
structure bytes.

The unauthenticated HTTP projection always reports `ordinary_release=false`.
It can expose `EFFECT_ACK_DONE` only as a client-supplied
`core_ordinary_release_candidate`; it has no release authority.  The image
contains no authenticator, full Responsibility-Record consumer, effect
executor, actuator, repository writer, deployment client or publication
credential.  Therefore a candidate state is not general `EFFECT_ACK_DONE` and
cannot itself cause an external effect.

## Reproducible build

From the repository root:

```text
python3 -B tools/qikvrt_mesh_linux_oci.py build --output-dir out/mesh-linux
python3 -B tools/qikvrt_mesh_linux_oci.py verify --output-dir out/mesh-linux
```

The builder performs strict C89 and C90 compilation, executes the native
self-test, creates an uncompressed deterministic root filesystem layer, emits
an OCI image layout and a Docker-load archive, and writes a SHA-256 receipt.
It performs no network access and no registry push.  `SOURCE_DATE_EPOCH`
controls archive timestamps.  The resulting image runs as UID/GID 65532 and
starts `/usr/bin/qikvrt-meshd --bind 0.0.0.0 --port 8080`.

Because the runtime binary is statically linked against the build host's C
library, redistribution is blocked until the exact compiler/libc provenance,
corresponding source/relinking obligations and third-party notices have been
reviewed for that produced artifact.  A locally generated archive is build
evidence, not release authorization.  For that reason CI currently retains
only the non-binary receipt; the OCI, Docker and ELF bytes are generated and
reobserved inside the job, then deliberately not published.  This is a
buildable image delivery in source form, not a registry image delivery.

## Standards relation

RFC 9110 is the current HTTP Semantics Internet Standard (STD 97), not an
expired draft.  It provides stateless request/response semantics but does not
define QIK-VRT Effect Acknowledgment.  The separate HTTPAPI
`Idempotency-Key` Internet-Draft addresses duplicate handling of non-idempotent
requests; expiration of one revision does not by itself mean that the idea was
technically rejected.  `draft-lohmann-qikvrt-effect-ack-03` is a separate
individual experimental proposal and has no IETF endorsement merely because
it is present in the Datatracker.

These standards supply relevant prior art and interoperability context.  They
do not establish patent novelty.  Novelty and inventive step require a
claim-by-claim prior-art search against all public disclosures and a legal
assessment by qualified patent counsel.

## Hardware evidence boundary

The existing VHDL admission gate, framed quadratic codec and iCE40UP5K target
remain source-level prototype material.  The state-machine alignment in this
work unit preserves their admission predicate and therefore does not justify a
new RTL result.  Static RTL contracts pass, but executable VHDL evidence is
currently blocked by `GHDL_NOT_DECLARED_IN_TOOLCHAIN_LOCK`.  Synthesis,
place-and-route, timing closure, bitstream generation, board programming and
physical observation remain false until the exact OSS CAD Suite/GHDL binaries
are digest-locked, licensed, cached and executed on the declared target.

## Staged route to the requested terminal

1. Close Python/C state-machine and wire-vector equivalence.
2. Replace the 20-octet proof profile with the complete versioned,
   authenticated Responsibility Record codec.
3. Add TLS/mTLS identity, freshness, replay and policy-anchor profiles.
4. Add DNS and SNMP as separately tested protocol adapters.  SNMP SET must use
   Prepare, Commit and post-effect GET reobservation; no SET is implied by V1.
5. Add a signed package format, dependency solver, provenance, SBOM and
   rollback before calling it a package manager.
6. Integrate the existing Firefox WebExtension in a real Firefox runtime, then
   develop and test a browser fork only if extension boundaries are
   insufficient.
7. Build native amd64 and arm64 artifacts, test Docker/Podman/cloud runtimes,
   complete license review, and authorize registry publication separately.

The exact capability truth table is
`policy/QIKVRT_MESH_LINUX_CAPABILITY_MATRIX_V1.json`.
