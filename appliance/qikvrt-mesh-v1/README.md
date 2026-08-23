# QIK-VRT Mesh Appliance v1

This work unit produces a Debian-based appliance containing Firefox ESR, the QIK-VRT Firefox adapter, the five-state Effect-Ack core, and the loopback-only HTTP prepare/commit profile from `draft-lohmann-qikvrt-effect-ack-01`.

It is not a Firefox fork and does not claim Gecko/SpiderMonkey equivalence. Firefox ESR is distributed with a QIK-VRT extension. The default protected effect is limited to local `terminal_input`; the backend binds only to loopback and records `external_effect=NONE`.

## Platforms

- QEMU/KVM and UTM: `*.qcow2`
- Microsoft Hyper-V: `*.vhdx`
- VirtualBox and VMware: `*.ova`
- Docker/Podman: multi-architecture GHCR image plus offline Docker archive

The VM is x86_64. Apple-Silicon hosts can use UTM x86_64 emulation; the OCI image is published for `linux/amd64` and `linux/arm64`.

## Immutable identity

The evidence URL is the version-and-source-specific GitHub Release asset URL:

```text
https://github.com/Goldkelch/qik-vrt/releases/download/<exact-tag>/<exact-asset-name>
```

The release manifest records every asset SHA-256 and the exact GHCR manifest digest. `latest` is only a mutable convenience alias and never an evidence identity.

## Runtime

Container browser UI: `http://127.0.0.1:6080/vnc.html` after publishing port 6080. The Effect-Ack service remains inside the appliance on `127.0.0.1:8771`.

The startup extension performs an exact bounded prepare/commit transaction. The smoke test succeeds only if Firefox loads the extension, the backend receives `TERMINAL_INPUT_ACCEPTED`, and post-effect state is reobserved.

## Boundaries

Repository and VM execution do not establish physical Mega-ST execution. A bounded loopback terminal-input acknowledgement is not a general `EFFECT_ACK_DONE`, publication, deployment, general Internet reachability, `PASS`, or `FINAL_PASS`.
