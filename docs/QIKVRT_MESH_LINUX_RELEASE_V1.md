# QIK-VRT Mesh Linux Appliance 1.0.0

This current-main-bound release work unit produces immutable, versioned software
artifacts for common host platforms:

- OCI archives and a multi-architecture GHCR image for `linux/amd64` and
  `linux/arm64`;
- QCOW2 and VHDX VM images for both architectures;
- an amd64 OVA for VMware/VirtualBox;
- an exact Firefox XPI;
- per-asset SHA-256, architecture build receipts, bounded runtime receipts, and
  a release manifest.

The appliance is assembled from the checksum-pinned Ubuntu 24.04 LTS release
`20260801`, Firefox `153.0.4` verified against Mozilla's signed SHA256SUMS, and
geckodriver `0.37.1` verified against its GitHub asset digest. The Ubuntu rootfs
and cloud-image checksums are the exact values published in that release's
signed transport namespace and are regression-tested in the repository.

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

## Build acceptance

Each architecture-specific OCI image must be started on its native GitHub
runner before any artifact is accepted for publication. The build waits for a
real Firefox/WebDriver/WebExtension session to produce
`firefox-effect-ack-receipt.json`, copies the receipt out of the running
container, and requires all of the following:

```text
firefox_terminal_execution_observed = true
bounded_loopback_effect_ack_done     = true
effect_ack_done_scope                = BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY
external_effect                      = NONE
physical_megast_execution            = false
general_internet_reachability        = false
backend event                        = TERMINAL_INPUT_ACCEPTED
```

The architecture artifact set includes that receipt and the captured container
log. Pull-request and manual preflight runs execute both native architecture
builds even though they cannot publish. A successful preflight therefore cannot
be produced by a prepare-only run with skipped build jobs. The generated
Firefox launcher is compiled during the repository contract test before either
native build starts. The packaged non-root self-test performs its Python syntax
checks entirely in memory; it must not attempt to create bytecode beneath the
root-owned `/usr/local/bin` tree.

Before the appliance modifies either cloud image, each native runner installs
an architecture-matched Ubuntu virtual kernel, makes that kernel readable to
the unprivileged supermin builder, and passes `libguestfs-test-tool` with the
direct backend. A missing or unusable host appliance kernel therefore blocks
before the long image build reaches `virt-customize`.
If the runner does not expose readable and writable `/dev/kvm`, the preflight
and subsequent image customization explicitly use libguestfs `force_tcg`;
this avoids an invalid ARM `gic-version=host` fallback while retaining KVM on
runners that actually provide it.
The host gate selects the freshly installed `*-generic` kernel explicitly via
the `SUPERMIN_KERNEL`, `SUPERMIN_KERNEL_VERSION`, and `SUPERMIN_MODULES`
contract instead of allowing supermin to prefer the hosted runner's newer
Azure kernel. It rejects a kernel with built-in `CONFIG_IPV6_SIT`, keeps a
fresh job-local appliance cache, and requires the Noble appliance's
`dhcpcd-base` client plus the QEMU `efi-virtio.rom` supplied by `ipxe-qemu`.
The host command alone does not prove that supermin copied that client into its
appliance, and adding a package name alone does not copy dpkg-managed
configuration files into a prebuilt supermin base. Before creating the fresh
cache, the gate therefore writes and read-verifies two architecture-neutral
inputs in every installed libguestfs `supermin.d`: a package fragment naming
the installed binary package `dhcpcd-base`, and a hostfiles fragment naming
`/etc/dhcpcd.conf`. Omitting recommended packages otherwise leaves the
appliance without DHCP/DNS or makes ARM QEMU abort as soon as the virtio network
device is added. After launch, the probe independently requires the appliance's
DHCP configuration, `dhcpcd` command, an IPv4 address on `eth0`, a default route,
and resolver configuration. It then proves DNS plus an outbound TCP connection to the architecture's Ubuntu mirror with noninteractive
`guestfish --network` against a real scratch disk before the expensive image
build. The probe script is uploaded into the appliance and executed explicitly
by Bash, so its `/dev/tcp` check cannot fall through to the appliance's POSIX
shell; distinct exit diagnostics identify DNS and TCP failures. Debug and
trace output are enabled for this network launch and for the
real `virt-customize` call. The gate makes the observed DHCP/DNS omission fail
closed while preserving the actionable QEMU/libguestfs cause of any later
appliance launch failure, rather than only the generic `guestfs_launch failed`
wrapper. Only a successful amd64 and arm64 native preflight establishes the
client, address, route, resolver, DNS, and TCP observations for that exact run.
On native ARM, QEMU may boot the libguestfs appliance with `efi-rtc=noprobe`
and an epoch clock even though networking is healthy. Because Ubuntu Noble's
signed archive metadata does not itself provide a bounded current-time source,
the preflight first obtains a TLS-authenticated `Date` header from the GitHub
API and requires runner UTC to agree within 30 seconds. It then runs the host
APT update with date and `Valid-Until` verification explicitly enabled and
`APT::Update::Error-Mode=any`, so a partial or cached-index warning cannot
silently validate the anchor. Global or `apt-get`-specific settings that
disable either date check, and every per-source override of those checks, are
rejected. Subsequent job time is bounded to two hours from that checked epoch.
The appliance clock is set to current runner UTC plus a five-minute rotation
cushion; the immediate observation may advance by at most 30 seconds and must
remain between the pinned Ubuntu `20260801` release epoch and 2100. The real
`virt-customize` action repeats the anchored,
cushioned synchronization as its first in-guest command, repeats the same
global, binary-specific, and per-source APT checks, and only then executes
`--install docker.io`.

The native build writes its complete command output to an
architecture-specific runner log instead of flooding the GitHub job stream
with repetitive libguestfs transfer traces. On failure the job emits a bounded
4,000-line tail and uploads only that diagnostic log under a `-diagnostics`
artifact name. The ordinary release-asset artifact remains success-only, and
publication still requires both successful native builds.

## Publication guards

Pull-request, manual, and release-branch push runs execute both native
architecture builds. Only a push whose exact subject is
`release: reattest QIK-VRT Mesh Linux v1.0.0 exact tree` may publish. That
carrier must have exactly one parent and the same tree as its parent. The
publish job repeats that check and verifies repeatedly that the release branch
still points to the workflow head. A non-carrier release-branch push completes
the native builds but ends with an explicit `HOLD`, so a green release
workflow cannot mean merely “prepare/build succeeded while publication was
skipped.” Eligible publication jobs share a constant, non-cancelling
concurrency group.

The merged build output must be an exact 16-file set before external effects.
Uncompressed QCOW2 working images are removed, the XPI occurs once, every file
must be regular and nonempty, and every release asset must be smaller than
2 GiB. After the release manifest and global checksum file are generated, the
exact final set is 18 regular files. `SHA256SUMS` excludes itself and is
validated against every other final asset.

All namespace checks are fail-closed. Only an exact absent-ref response is
vacant; GHCR additionally requires a Distribution error document whose code is
`MANIFEST_UNKNOWN`. Generic 404, authentication, transport, rate-limit, and
server errors are `BLOCK`. The GitHub tag/release and the three GHCR version
coordinates must all be vacant. Existing production coordinates are never overwritten and
require explicit reconciliation after any partial external effect.

GHCR must already be positively public before a carrier is created. Repository
variables `QIKVRT_GHCR_PUBLIC_PROBE_TAG` and
`QIKVRT_GHCR_PUBLIC_PROBE_DIGEST` bind an anonymously readable probe in the
same package. The first GHCR package version is not used as a visibility
experiment by the release run.

The workflow uses repository-locked GitHub CLI 2.96.0. It separates an
Administration-read-only `QIKVRT_IMMUTABLE_ADMIN_READ_TOKEN` from the
`QIKVRT_RELEASE_WRITE_WORKFLOWS_TOKEN` needed to create a Release whose
target changes workflow files. It verifies the immutable-release repository
setting before mutation.

After GHCR upload, the workflow discards its earlier anonymous bearer and
acquires a fresh credential-free bearer. That fresh token must read back the
top digest and exactly the `linux/amd64` and `linux/arm64` descriptors
before the GitHub Release is created. The final Release must then report
`isImmutable=true`, pass release-attestation and per-asset verification, and
return the exact 18 asset names and byte sizes. A failed guard is not
publication evidence.

## Claim boundary

The packaged browser proof is
`BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY` with `external_effect=NONE`.
This release does not establish a general/unbounded `EFFECT_ACK_DONE`, physical
Mega-ST/M68000 execution, general Internet reachability, independent review
authority, `PASS`, or `FINAL_PASS`. It is a versioned software distribution,
not evidence of physical hardware execution.

The packaged Firefox component is Mozilla Firefox plus the QIK-VRT WebExtension
and bounded Effect-Ack profile. It is not a fork or complete clean-room
replacement of Firefox, Gecko, or SpiderMonkey. The separately included Atari
ANSI C89 browser capsule is a bounded clean-room implementation and is not
represented as Firefox-equivalent or M68000-executed in this release.
