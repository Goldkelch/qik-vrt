# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic, local-only foundation for QIK-VRT IP services.

This module deliberately models authoritative DNS and read-only SNMP management
semantics before binding them to a socket, credential, or external network.
Transport success is never service execution, and management writes remain
fail-closed until a separately authorized service adapter exists.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

DNS_ALLOWED_TYPES = frozenset({"A", "AAAA", "NS", "SOA", "TXT"})
DNS_RESPONSE_ANSWER = "ANSWER"
DNS_RESPONSE_NODATA = "NODATA"
DNS_RESPONSE_NXDOMAIN = "NXDOMAIN"
DNS_RESPONSE_REFUSED = "REFUSED"
SNMP_NO_SUCH_OBJECT = "NO_SUCH_OBJECT"
SNMP_END_OF_MIB_VIEW = "END_OF_MIB_VIEW"
SNMP_SET_BLOCKED = "SET_BLOCKED"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def canonical_dns_name(value: str) -> str:
    """Return a strict ASCII FQDN or reject the name before any lookup."""
    if not isinstance(value, str):
        raise ValueError("DNS name must be a string")
    name = value.strip().lower()
    if not name or not name.endswith("."):
        raise ValueError("DNS name must be an absolute FQDN")
    if name == ".":
        return name
    labels = name[:-1].split(".")
    if len(name.encode("ascii")) > 255:
        raise ValueError("DNS name exceeds 255 octets")
    for label in labels:
        if not label or len(label.encode("ascii")) > 63:
            raise ValueError("DNS label length invalid")
        if label[0] == "-" or label[-1] == "-":
            raise ValueError("DNS label edge hyphen invalid")
        if not all(character.isascii() and (character.isalnum() or character == "-") for character in label):
            raise ValueError("DNS label contains unsupported character")
    return name


def canonical_oid(value: str | Iterable[int]) -> tuple[int, ...]:
    """Parse a dotted OBJECT IDENTIFIER into its ordered non-negative arcs."""
    if isinstance(value, str):
        if not value or value.startswith(".") or value.endswith("."):
            raise ValueError("OID must be a non-empty dotted sequence")
        parts = value.split(".")
        if any(not part.isdigit() for part in parts):
            raise ValueError("OID arcs must be decimal integers")
        arcs = tuple(int(part) for part in parts)
    else:
        arcs = tuple(value)
    if len(arcs) < 2 or any(not isinstance(arc, int) or arc < 0 for arc in arcs):
        raise ValueError("OID must contain at least two non-negative arcs")
    if arcs[0] > 2 or (arcs[0] < 2 and arcs[1] > 39):
        raise ValueError("OID root arcs invalid")
    return arcs


def oid_text(value: tuple[int, ...]) -> str:
    return ".".join(str(arc) for arc in value)


@dataclass(frozen=True)
class DNSRecord:
    owner: str
    record_type: str
    ttl: int
    rdata: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "owner", canonical_dns_name(self.owner))
        object.__setattr__(self, "record_type", self.record_type.upper())
        if self.record_type not in DNS_ALLOWED_TYPES:
            raise ValueError("unsupported DNS record type")
        if not isinstance(self.ttl, int) or self.ttl < 0 or self.ttl > 0x7FFFFFFF:
            raise ValueError("DNS TTL invalid")
        if not isinstance(self.rdata, str) or not self.rdata:
            raise ValueError("DNS RDATA must be non-empty text")


@dataclass(frozen=True)
class DNSResponse:
    status: str
    answers: tuple[DNSRecord, ...]
    authoritative: bool
    zone_digest: str


class AuthoritativeDNSZone:
    """Deterministic in-memory authoritative zone; no recursion or transport."""

    def __init__(self, origin: str, serial: int, records: Iterable[DNSRecord]) -> None:
        self.origin = canonical_dns_name(origin)
        if not isinstance(serial, int) or not 0 <= serial <= 0xFFFFFFFF:
            raise ValueError("SOA serial must be an unsigned 32-bit integer")
        self.serial = serial
        ordered = tuple(sorted(records, key=lambda record: (record.owner, record.record_type, record.rdata, record.ttl)))
        if not ordered:
            raise ValueError("authoritative zone requires records")
        if any(not (record.owner == self.origin or record.owner.endswith("." + self.origin)) for record in ordered):
            raise ValueError("record owner outside zone")
        self.records = ordered
        self._by_owner: dict[str, tuple[DNSRecord, ...]] = {}
        for record in ordered:
            self._by_owner.setdefault(record.owner, tuple())
            self._by_owner[record.owner] += (record,)
        self.digest = _sha256({
            "schema": "qikvrt_authoritative_dns_zone_v1",
            "origin": self.origin,
            "serial": self.serial,
            "records": [record.__dict__ for record in ordered],
        })

    def query(self, qname: str, qtype: str) -> DNSResponse:
        name = canonical_dns_name(qname)
        record_type = qtype.upper()
        if record_type not in DNS_ALLOWED_TYPES:
            raise ValueError("unsupported DNS query type")
        if not (name == self.origin or name.endswith("." + self.origin)):
            return DNSResponse(DNS_RESPONSE_REFUSED, (), False, self.digest)
        owner_records = self._by_owner.get(name, ())
        if not owner_records:
            return DNSResponse(DNS_RESPONSE_NXDOMAIN, (), True, self.digest)
        answers = tuple(record for record in owner_records if record.record_type == record_type)
        if not answers:
            return DNSResponse(DNS_RESPONSE_NODATA, (), True, self.digest)
        return DNSResponse(DNS_RESPONSE_ANSWER, answers, True, self.digest)


@dataclass(frozen=True)
class ManagedObject:
    oid: tuple[int, ...]
    syntax: str
    value: str | int
    access: str = "read-only"

    def __post_init__(self) -> None:
        object.__setattr__(self, "oid", canonical_oid(self.oid))
        if self.syntax not in {"Integer32", "OctetString", "ObjectIdentifier"}:
            raise ValueError("unsupported management syntax")
        if self.access != "read-only":
            raise ValueError("foundation only permits read-only managed objects")
        if self.syntax == "Integer32" and (not isinstance(self.value, int) or not -(2**31) <= self.value < 2**31):
            raise ValueError("Integer32 value invalid")
        if self.syntax != "Integer32" and not isinstance(self.value, str):
            raise ValueError("textual management value required")


@dataclass(frozen=True)
class SNMPReadResult:
    status: str
    object: ManagedObject | None
    mib_digest: str


class ReadOnlyMIB:
    """Ordered management-information view for SNMP GET/NEXT/BULK semantics."""

    def __init__(self, objects: Iterable[ManagedObject]) -> None:
        ordered = tuple(sorted(objects, key=lambda item: item.oid))
        if not ordered:
            raise ValueError("MIB requires at least one managed object")
        if len({item.oid for item in ordered}) != len(ordered):
            raise ValueError("duplicate managed object OID")
        self.objects = ordered
        self._by_oid = {item.oid: item for item in ordered}
        self.digest = _sha256({
            "schema": "qikvrt_read_only_mib_v1",
            "objects": [
                {"oid": oid_text(item.oid), "syntax": item.syntax, "value": item.value, "access": item.access}
                for item in ordered
            ],
        })

    def get(self, oid: str | Iterable[int]) -> SNMPReadResult:
        item = self._by_oid.get(canonical_oid(oid))
        return SNMPReadResult("VALUE" if item else SNMP_NO_SUCH_OBJECT, item, self.digest)

    def get_next(self, oid: str | Iterable[int]) -> SNMPReadResult:
        requested = canonical_oid(oid)
        for item in self.objects:
            if item.oid > requested:
                return SNMPReadResult("VALUE", item, self.digest)
        return SNMPReadResult(SNMP_END_OF_MIB_VIEW, None, self.digest)

    def get_bulk(self, oid: str | Iterable[int], max_repetitions: int) -> tuple[SNMPReadResult, ...]:
        if not isinstance(max_repetitions, int) or not 0 <= max_repetitions <= 128:
            raise ValueError("max_repetitions outside bounded range")
        current = canonical_oid(oid)
        values: list[SNMPReadResult] = []
        for _unused in range(max_repetitions):
            result = self.get_next(current)
            values.append(result)
            if result.object is None:
                break
            current = result.object.oid
        return tuple(values)

    def set_is_permitted(self) -> bool:
        return False

    def set_result(self) -> dict[str, Any]:
        return {
            "state": SNMP_SET_BLOCKED,
            "ordinary_release": False,
            "reason": "no writable MIB object or effect-authorized adapter exists",
            "mib_digest": self.digest,
        }
