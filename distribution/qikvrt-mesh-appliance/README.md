# QIK-VRT Mesh Appliance

Reproducible appliance distribution containing official Mozilla Firefox ESR, the QIK-VRT Firefox adapter, the complete repository Responsibility Protocol evaluator, and a loopback-only Effect-Acknowledgement gateway.

## Formats

The release workflow produces a multi-platform OCI image (`linux/amd64`, `linux/arm64`) and an amd64 VM in QEMU/KVM QCOW2, VMware VMDK, Hyper-V VHDX and OVA form for VirtualBox/VMware. Apple Silicon can run the amd64 VM through x86-64 emulation; the OCI image has a native arm64 variant.

## Browser and protocol identity

Firefox is the official ESR binary verified against Mozilla-signed checksums. The QIK-VRT adapter is installed temporarily at every appliance start through geckodriver, then a real Firefox extension page evaluates and cryptographically validates a complete `qikvrt_responsibility_protocol_v1` record before the appliance becomes ready. This is not represented as a Firefox/Gecko fork or product-equivalence result.

The wire profile is bound to `draft-lohmann-qikvrt-effect-ack-00`, an Experimental individual Internet-Draft rather than an IETF standard. The appliance implements all five repository states and the full Responsibility Protocol. The protected effect in this release remains only loopback `terminal_input` with `external_effect=NONE`.

## Immutable identity

Use the SHA-bearing release tag, asset SHA-256 manifest and GHCR manifest digest. A `latest` alias is convenience only and is never evidence identity.

```sh
docker run --rm -p 127.0.0.1:6080:6080 -e QIKVRT_VNC_PASSWORD='replace-me' -v qikvrt-state:/var/lib/qikvrt ghcr.io/goldkelch/qik-vrt-mesh-appliance@sha256:RELEASE_DIGEST
```

Open `http://127.0.0.1:6080/vnc.html`. No physical Atari execution, general Internet reachability, publication, deployment, `PASS`, `FINAL_PASS`, or general `EFFECT_ACK_DONE` follows from this appliance candidate.
