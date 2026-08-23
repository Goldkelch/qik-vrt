# QIK-VRT Mesh Virtual Appliance V1

This work unit packages already observed virtual QIK-VRT evidence into a reproducible distribution surface for third parties.

## Exact inputs

- Authority Atari/Hatari generation: `3cb6273924f3de310e3bd1cd5b827e8e3529220a` / tree `864b7728c1c4b932c42fb97c063162dca14646ee`.
- ANSI C89 browser capsule: `cba166e45a0ea4b5d5dd2ef9cde0ad96ff57554b` / tree `23586fd719627a6e508724239a71b71fea7e9847`.
- Firefox bounded Effect-Ack source: `b7c9fa5f74cb963ba7cfefed2a0d0a071e6515a9`.
- Firefox live-observation source: `42eab8223988c9576b3c4be7f9a70c3cba45c5e9`.
- Guest TCP/IP source: `a71484ba02f6ebe9169af5a291244e99468caec3`.

The committed deterministic source bundle is:

```text
distribution/qikvrt-mesh-appliance-v1-source.tar.gz
sha256:665bbbaeeebee250e64faa900075d72f345069b0eac2ecaa7682488dc9e4c005
```

A commit-pinned raw GitHub URL to that file is immutable after this branch commit is created. After legitimate Authority-main effect, the workflow publishes:

1. an amd64 bootable ISO for QEMU, VirtualBox and VMware;
2. an OCI archive usable by Docker or Podman on Linux, macOS and Windows;
3. a GHCR image addressed by exact commit and registry digest;
4. the deterministic source bundle, lock file and SHA-256 indexes as a one-time GitHub Release.

The release tag includes the Authority commit prefix and assets are never overwritten. No mutable `latest` tag is used.

## Runtime commands

After extracting the source bundle:

```sh
./launch-linux.sh verify
./launch-linux.sh atari
./launch-linux.sh firefox-effect-ack
./launch-linux.sh all
```

On macOS use `launch-macos.sh`; on Windows with Docker Desktop use `launch-windows.ps1`.

The image contains a Debian-derived QIK-VRT Mesh Live appliance, not a new Linux kernel lineage. It includes the bounded QIK-VRT Firefox extension, loopback Effect-Ack backend, Hatari, EmuTOS acquisition with pinned archive SHA-256, the five-kernel MLP.TOS builder, and the clean-room ANSI C89 browser capsule.

## Evidence boundary

`repository evidence != virtual Hatari/Mega-ST execution != Firefox browser observation != physical hardware execution`.

The Effect-Ack implementation is the current repository-bound QIK-VRT HTTP prepare/commit draft profile. The demonstrated acknowledgement is restricted to `BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY` with `external_effect=NONE`. This work unit does not claim IETF adoption, general Effect-Acknowledgement, general Internet reachability, physical Mega-ST execution, publication before an observed release, deployment, PASS or FINAL_PASS.
