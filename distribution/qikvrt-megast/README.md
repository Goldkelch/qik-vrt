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

## Principle

**Stay fail closed and keep future open.** Missing runtime or publication evidence leaves the lane open; it never converts transport success into effect. The return path carries the original request, material descendants, artifacts, effects, failures, repairs, successors and still-open obligations back into the evidence chain.
