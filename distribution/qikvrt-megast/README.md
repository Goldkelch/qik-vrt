# QIK-VRT Mega ST Distribution

This directory defines the downloadable QIK-VRT Linux distribution whose desktop deliberately recalls an Atari Mega ST while remaining a modern GNU/Linux workstation and QIK-VRT Universal Terminal.

## Definition of Done for this distribution

The distribution lane is not complete merely because an ISO builds. Its terminal predicate requires all of the following on one exact trusted-Main subject:

1. a reproducible bootable amd64 ISO is built from the repository;
2. the ISO contains the QIK-VRT TEMDD/Effect-ACK contract and Universal Terminal client surface;
3. a graphical session presents a deliberately Mega-ST/GEM-inspired visual shell;
4. Hatari is installed so an Atari ST/Mega ST class machine can run when the user supplies a legally usable TOS image; no proprietary Atari ROM is redistributed by this project;
5. modern software remains available through native Debian packages, Flatpak, OCI/Podman and the web browser instead of being trapped inside the 68k guest;
6. build manifest, ISO SHA-256 and exact git subject are emitted as receipts;
7. the released asset is downloadable from the stable release path and independently read back after publication;
8. EFFECT_ACK_DONE is claimed only after that download, checksum and boot/runtime contract have been reobserved.

Canonical download target after a legitimate trusted-Main publication:

`https://github.com/Goldkelch/qik-vrt/releases/latest/download/qikvrt-megast-amd64.iso`

## Architecture

The host is Debian Live. Xfce is the modern desktop substrate. `qikvrt-megast-session` applies a restrained GEM/Mega-ST visual vocabulary (light grey work surface, dark borders, compact controls, monospaced terminal) while keeping ordinary Linux applications usable. Hatari supplies the MC68000-era Atari hardware environment. QIK-VRT services stay on the Linux side and therefore can evolve without pretending that contemporary applications execute natively on a 1980s 68000.

Compatibility is intentionally layered:

- **Atari layer:** Hatari, user-provided legal TOS/EmuTOS-compatible ROM media;
- **native Linux layer:** Debian packages;
- **portable desktop layer:** Flatpak;
- **service/container layer:** Podman/OCI;
- **universal application layer:** Firefox/Web;
- **QIK-VRT layer:** TEMDD, exact-subject receipts, Effect Acknowledgement, Mesh/Universal Terminal integration.

This is a compatibility envelope, not a claim that literally every existing program can execute on every CPU or license regime.

## Local build

Run as root or in a Debian runner with `live-build`, `debootstrap`, `xorriso` and `squashfs-tools` installed:

```sh
sudo ./distribution/qikvrt-megast/build.sh
```

The script writes `out/qikvrt-megast-amd64.iso`, `out/qikvrt-megast-amd64.iso.sha256` and `out/qikvrt-megast-build-receipt.json`.

## Network image and executing receiver

The same build now exports `qikvrt-megast-vmlinuz`, `qikvrt-megast-initrd`,
`qikvrt-megast-filesystem.squashfs` and `QIKVRT_BOOT.BIN`. The machine-readable
`qikvrt-netboot.json` binds their byte counts, SHA-256 values, source commit,
host architecture and fixed boot method. `qikvrt-netboot-client.py` downloads
only those files, validates the caller-provided manifest digest and starts
QEMU with the exact kernel/initrd and an HTTP-fetched live root filesystem.
It attaches no CD-ROM. No command supplied by the remote manifest is executed.

After legitimate publication, use the exact release's client and manifest hash:

```sh
python3 qikvrt-netboot-client.py receive MANIFEST_URL EXPECTED_MANIFEST_SHA256 ./qikvrt-received --boot
```

The client needs Python 3.11+ and `qemu-system-x86_64` on Linux x86_64. HTTPS is
required for public downloads; an explicit private IP supports an isolated test
network. It reobserves the network-booted guest's Xfce/Firefox window, loopback
Effect-Ack endpoint, 7,864,387 C90 assertions, restored Smalltalk image and the
received MC68000 program's actual execution under `qemu-m68k`. The serial log
and receipt retain source and manifest hashes. This is an emulated CPU-family
witness, not a physical Atari boot or an independent human release approval.

The C90 bootstrap receiver additionally implements the existing fixed file-id 1
UDP route: discover, offer, request, data, done; 128-byte chunks, FNV1A32 frame
checks, two-second receive timeout and three bounded attempts. It binds every
reply to nonce, offset and total size, verifies a separately supplied full-image
SHA-256 and re-reads the persisted file. The maximum bootstrap program is 4 MiB;
large operating-system images use the manifest/HTTP lane. A content `done`
datagram is never the guest-execution receipt.

Build and test sources:
`src/cloud_transputer/qikvrt_boot_receive.c`, `src/smalltalk/`, `boot.py` and
`runtime-witness.py`. The existing distribution workflow runs the complete
C90/Smalltalk comparison and the real network boot before its Main-only
publication step.

## Principle

**Stay fail closed and keep future open.** Missing runtime or publication evidence leaves the lane open; it never converts transport success into effect. The return path carries the original request, material descendants, artifacts, effects, failures, repairs, successors and still-open obligations back into the evidence chain.
