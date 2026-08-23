# QIK-VRT Mesh Appliance Release V1

## Product identity

The immutable distribution identity is the exact source commit, the versioned GitHub release tag, the release-asset SHA-256 manifest and the GHCR OCI manifest digest. A moving convenience tag is never evidence identity.

Release tag:

```text
qikvrt-mesh-appliance-v0.1.0-rc1
```

Stable asset URL pattern:

```text
https://github.com/Goldkelch/qik-vrt/releases/download/qikvrt-mesh-appliance-v0.1.0-rc1/<asset-name>
```

Expected cross-hypervisor assets:

```text
QIKVRT-Mesh-Appliance-v0.1.0-rc1-amd64.qcow2.xz
QIKVRT-Mesh-Appliance-v0.1.0-rc1-amd64.vmdk.xz
QIKVRT-Mesh-Appliance-v0.1.0-rc1-amd64.vhdx.xz
QIKVRT-Mesh-Appliance-v0.1.0-rc1-amd64.ova
QIKVRT-Mesh-Appliance-v0.1.0-rc1-SHA256SUMS.txt
QIKVRT-Mesh-Appliance-v0.1.0-rc1-release.json
```

The public URLs become factual only after the release workflow publishes and reobserves the assets. A source file or workflow definition alone is not publication evidence.

## Distribution composition

The Linux layer is a QIK-VRT appliance composition based on a digest-pinned Ubuntu 24.04 LTS image and timestamp-bounded package inputs. It is not represented as an independently developed Linux kernel.

The browser layer is an official Mozilla Firefox ESR build plus the exact QIK-VRT WebExtension adapter. It is not a Firefox/Gecko fork and does not claim browser-product equivalence.

The appliance contains both the strict ANSI-C90 Effect-Ack core and the complete Python Responsibility Protocol evaluator. The Firefox adapter must execute discovery, prepare, full-record validation, single-use commit and a separate post-effect backend reobservation before the image becomes healthy.

## Docker or Podman

After publication, read the exact OCI digest from the release manifest and run by digest:

```sh
podman pull ghcr.io/goldkelch/qik-vrt-mesh-appliance@sha256:<manifest-digest>
podman run --rm --network=host \
  -e QIKVRT_VNC_PASSWORD=qikvrt \
  -v qikvrt-state:/var/lib/qikvrt \
  ghcr.io/goldkelch/qik-vrt-mesh-appliance@sha256:<manifest-digest>
```

Open the noVNC interface at `http://127.0.0.1:6080/vnc.html`. The reference Effect-Ack endpoint remains loopback-bound at `http://127.0.0.1:8771/.well-known/effect-ack`.

## Virtual-machine formats

- QEMU/KVM, GNOME Boxes, UTM: decompress the QCOW2 image.
- Hyper-V: decompress the VHDX image.
- VMware: decompress the VMDK image or import the OVA.
- VirtualBox: import the OVA.

The VM embeds the exact OCI archive and loads it locally at first boot. It does not depend on a registry pull to start the packaged release.

Recommended resources are 2 virtual CPUs, 4 GiB RAM and a NAT network. The appliance service exposes noVNC on guest TCP port 6080. The default VNC password for the prerelease is `qikvrt` and should be replaced for non-ephemeral use.

## Verification

Download the release checksum file and verify in the asset directory:

```sh
sha256sum -c QIKVRT-Mesh-Appliance-v0.1.0-rc1-SHA256SUMS.txt
```

The release workflow independently downloads its own published assets, verifies that manifest and reobserves the OCI image by immutable digest. The build also boots the generated QCOW2 appliance and requires the noVNC surface to become reachable.

## Evidence boundary

The Effect-Acknowledgement gateway implements the repository's five-state Responsibility Protocol surface and the Experimental `draft-lohmann-qikvrt-effect-ack-00` profile. It is not represented as an IETF standard.

The protected reference effect is bounded to loopback `terminal_input` with `external_effect=NONE`. This release does not imply physical Mega-ST execution, general Internet reachability, external publication beyond the release assets themselves, independent review authority, `PASS`, `FINAL_PASS`, or general `EFFECT_ACK_DONE`.
