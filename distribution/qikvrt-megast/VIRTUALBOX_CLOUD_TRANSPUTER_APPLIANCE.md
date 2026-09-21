# QIK-VRT VirtualBox Cloud Transputer Appliance

## Purpose

This carrier turns the existing QIK-VRT Mega-ST ISO and Universal Terminal container into an explicitly testable **Oracle VirtualBox appliance contract** without claiming a VirtualBox boot before one has been observed.

The intended system is:

```text
Oracle VirtualBox VM
  -> QIK-VRT personal Linux distribution / Mega-ST surface
     -> OCI/Docker-compatible Universal Terminal + Cloud Transputer service plane
        -> Internet-facing service adapters and health/readback boundaries
           -> MC68000 executable carrier
              -> C90-defined semantics / generated MC68000 code and machine-code evidence
```

## Existing exact-subject capabilities inherited by this carrier

The product integration base already contains:

- an amd64 hybrid ISO build with exact HEAD/TREE receipts;
- QEMU boot reobservation and guest boot witness;
- Xfce/Firefox/Mega-ST session materialization;
- Podman in the live distribution;
- SSH and loopback Effect-Ack services;
- a Universal Terminal OCI image with Firefox/noVNC, nginx, SSH, DNS tooling,
  PostgreSQL, SNMP, Git, HTTP services and health checks;
- MC68000 cross-compilation plus qemu-m68k execution support;
- strict C90 Effect-Ack semantics and multi-carrier conformance evidence.

These are prerequisites. They are not evidence of a successful Oracle VirtualBox boot.

## VirtualBox acceptance contract

A candidate ISO is VirtualBox-ready only after a fresh exact-subject test performs all of the following:

1. Create an ephemeral VirtualBox VM using a documented machine profile.
2. Attach the exact ISO read from the build artifact.
3. Boot the guest without modifying the ISO after hashing.
4. Obtain a guest-originated witness that binds the candidate HEAD/TREE and ISO digest.
5. Verify network availability from inside the guest.
6. Verify the container runtime is present.
7. Build or load the exact-subject Universal Terminal / Cloud Transputer OCI image.
8. Start it inside the guest and wait for its health check.
9. Read back the Universal Terminal HTTP endpoint from the guest.
10. Execute the MC68000 self-test through the declared MC68000 runner and preserve its receipt.
11. Preserve machine-readable VM, guest, container and MC68000 evidence as one exact-subject artifact.

Until all applicable steps execute successfully:

```text
VIRTUALBOX_BOOT = NOT_ESTABLISHED
CLOUD_CONTAINER_IN_GUEST = NOT_ESTABLISHED
MC68000_GUEST_EXECUTION = NOT_ESTABLISHED
PUBLIC_CLOUD_EFFECT = NOT_ESTABLISHED
EFFECT_ACK_DONE = false
```

## Recommended VirtualBox profile

The first reproducible profile is deliberately conservative:

```text
guest architecture : amd64
firmware           : BIOS first; EFI as a separate compatibility lane
memory             : >= 2048 MiB
vCPU               : >= 2
chipset             : default VirtualBox-compatible profile
graphics           : VMSVGA
network            : NAT for outbound Internet access
serial             : COM1/file or named pipe for boot witness capture
storage            : read-only ISO + ephemeral writable disk
nested workload    : OCI/Podman container; MC68000 executed by qemu-user inside it
```

Additional bridged, host-only, EFI and cloud-init-like profiles are separate lanes and must not be inferred from the baseline result.

## Cloud scaling boundary

The Universal Terminal image is the cloud-computing unit. It must remain stateless where possible and externalize durable state behind explicit service boundaries. Horizontal replicas may be scheduled by an OCI-compatible platform, but repository evidence must distinguish:

- image build success;
- local container health;
- guest-local service readback;
- externally reachable deployment;
- independent public readback.

A local VirtualBox or Docker success is not a public-cloud effect.

## MC68000 / C90 boundary

The MC68000 claim is accepted only at the level actually executed. Cross-compilation proves production of MC68000-targeted objects/binaries. qemu-m68k execution proves execution under the emulator. It does not prove execution on physical Motorola silicon.

Where C90 is used as the semantic source, the audit must preserve:

```text
C90 source digest
-> compiler/toolchain identity
-> generated assembly/object digest
-> linked MC68000 machine-code digest
-> execution receipt
-> conformance result
```

No step may be replaced by a textual claim.

## Audit result semantics

The appliance audit is PASS only when every required lane for the selected profile is freshly bound to the same exact subject. A PASS does not establish physical-hardware execution or public-cloud DONE unless those separate lanes have also been executed and read back.

This file is the first manifest for the VirtualBox optimization lane. Implementation changes and their tests must create a successor HEAD and restart exact-subject validation.
