# QIK-VRT Mesh Linux Appliance 1.0.0

This current-main-bound release work unit produces immutable, versioned software
artifacts for common host platforms:

- OCI archives and a multi-architecture GHCR image for `linux/amd64` and
  `linux/arm64`;
- QCOW2 and VHDX VM images for both architectures;
- an amd64 OVA for VMware/VirtualBox;
- an exact Firefox XPI;
- per-asset SHA-256 and a release manifest.

The appliance is assembled from the checksum-pinned Ubuntu 24.04 LTS release
`20260801`, Firefox `153.0.4` verified against Mozilla's signed SHA256SUMS, and
geckodriver `0.37.1` verified against its GitHub asset digest.

It binds three exact QIK-VRT source generations:

- bounded Firefox Effect-Ack profile:
  `b7c9fa5f74cb963ba7cfefed2a0d0a071e6515a9`;
- clean-room ANSI C89 Atari browser:
  `cba166e45a0ea4b5d5dd2ef9cde0ad96ff57554b`;
- bounded autonomous Mesh repair candidate:
  `9832f6ddf6a3ef53a7c0f9b52d2c9d8f1e7ba970`.

After an authorized final zero-diff release carrier is built successfully, the
immutable asset namespace is the versioned GitHub release tag
`qikvrt-mesh-linux-v1.0.0`. The OCI coordinate is
`ghcr.io/goldkelch/qik-vrt-mesh-linux:1.0.0`; consumers must prefer the digest
recorded in `QIKVRT_MESH_LINUX_RELEASE_MANIFEST.json`.

The VM boots the same OCI appliance as a systemd service. Its visible Firefox
session is exposed through noVNC on TCP 6080. The Effect-Ack backend remains
loopback-only inside the appliance.

## Claim boundary

The packaged browser proof is
`BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY` with `external_effect=NONE`.
This release does not establish a general/unbounded `EFFECT_ACK_DONE`, physical
Mega-ST/M68000 execution, general Internet reachability, independent review
authority, `PASS`, or `FINAL_PASS`. It is a versioned software distribution,
not evidence of physical hardware execution.

The packaged Firefox component is the QIK-VRT WebExtension plus the bounded
Effect-Ack profile. It is not a fork or complete clean-room replacement of
Firefox, Gecko, or SpiderMonkey.
