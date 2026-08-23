# QIK-VRT Mesh Appliance Release V1

The immutable distribution identity is a versioned GitHub release tag containing the exact source SHA, an asset checksum manifest, and a GHCR manifest digest. The moving `latest` alias is not evidence identity.

The Linux layer is a QIK-VRT appliance composition based on a digest-pinned Ubuntu 24.04 LTS image and a timestamp-pinned package snapshot; it is not represented as an independently developed Linux kernel. The browser layer is official Mozilla Firefox ESR plus an exact QIK-VRT adapter, not a Firefox/Gecko fork. The adapter is loaded and self-tested in a real Firefox process before readiness.

The Effect-Acknowledgement gateway uses the repository's complete Responsibility Protocol data model and five-state decision surface. Its network effect remains bounded to local terminal input with `external_effect=NONE`. The referenced IETF document is an Experimental individual Internet-Draft, not an IETF standard.
