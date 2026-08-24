# QIK-VRT IP Services Foundation V1

## Scope

This first implementation step establishes deterministic, local-only data-plane
semantics for two infrastructure services:

- authoritative DNS zones with absolute ASCII FQDNs and the response classes
  `ANSWER`, `NODATA`, `NXDOMAIN`, and `REFUSED`;
- ordered read-only SNMP management information with `GET`, `GETNEXT`, and
  bounded `GETBULK` semantics.

It is intentionally free of sockets, credentials, recursive resolution,
dynamic update, DHCP, writable MIB objects, SNMP message encoding, SNMPv3
USM/VACM, traps, Internet reachability, and physical-device claims.

## Semantic and effect boundary

A DNS answer or SNMP response is a transport-level information result. It does
not authorize configuration change. The present MIB has no writable object:
every `SET` path reports `SET_BLOCKED` and
`ordinary_release = false`. Service events remain separable as requested,
transported, executed, observed, and confirmed; reobservation is required
before any broader state claim.

## Standards basis

The model takes its DNS naming, authoritative-zone, and resource-record
structure from [RFC 1034](https://www.rfc-editor.org/info/rfc1034) and
[RFC 1035](https://www.rfc-editor.org/info/rfc1035). Its SNMP separation of
architecture, protocol operations, and access control follows
[RFC 3411](https://www.rfc-editor.org/info/rfc3411),
[RFC 3416](https://www.rfc-editor.org/info/rfc3416), and
[RFC 3415](https://www.rfc-editor.org/info/rfc3415).

No RFC conformance claim follows from this foundation.

## Deterministic build order

1. **DNS authoritative wire adapter:** bounded UDP/TCP parsing and response
   serialization for the existing zone core, with compression-loop, size, and
   malformed-packet tests.
2. **SNMPv3 engine:** BER codec, message dispatcher, USM, VACM and a
   repository-local management transport; no default community strings and no
   unauthenticated write path.
3. **Configuration lifecycle:** a fail-closed policy adapter that separates
   management request, prepared change, authorized commit, local application,
   and reobservation.
4. **Addressing and bootstrap:** DHCP client/server simulation, lease journal,
   DNS service-discovery records, and deterministic topology receipts.
5. **Time, routing, and observability:** NTP-like bounded time source,
   route/neighbor model, SNMP notifications, structured logs and metrics.
6. **Target adapters:** each emulator, M68000 and later physical target needs
   its own exact-head execution and reobservation evidence.

Every stage must be testable without a public listener or an external effect.
