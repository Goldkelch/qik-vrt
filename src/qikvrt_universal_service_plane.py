#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Bounded loopback SMTP/DNS/SNMP service plane for the universal terminal.

These listeners are intentionally loopback-only.  They provide real protocol
sockets for local terminal use without creating an open relay, resolver, or
management endpoint on the public network boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import socket
import socketserver
import struct
import threading
import time
from pathlib import Path

SMTP_HOST = "127.0.0.1"
SMTP_PORT = int(os.environ.get("QIKVRT_SMTP_PORT", "1025"))
DNS_HOST = "127.0.0.1"
DNS_PORT = int(os.environ.get("QIKVRT_DNS_PORT", "1053"))
SNMP_HOST = "127.0.0.1"
SNMP_PORT = int(os.environ.get("QIKVRT_SNMP_PORT", "1161"))
MAX_SMTP_MESSAGE = 1024 * 1024
LOCAL_MAIL_DOMAIN = "qikvrt.local"
SYS_DESCR = "QIK-VRT universal terminal service plane"
SYS_NAME = "qikvrt-cloud-transputer"
SYS_DESCR_OID = (1, 3, 6, 1, 2, 1, 1, 1, 0)
SYS_NAME_OID = (1, 3, 6, 1, 2, 1, 1, 5, 0)


class ReuseThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ReuseThreadingUDPServer(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True


class SMTPHandler(socketserver.StreamRequestHandler):
    timeout = 30

    def _send(self, text: str) -> None:
        self.wfile.write(text.encode("ascii") + b"\r\n")
        self.wfile.flush()

    def _line(self) -> str:
        raw = self.rfile.readline(16 * 1024)
        if not raw:
            raise ConnectionError("client closed")
        if len(raw) >= 16 * 1024 and not raw.endswith(b"\n"):
            raise ValueError("SMTP command too long")
        return raw.decode("utf-8", errors="replace").rstrip("\r\n")

    def handle(self) -> None:
        sender = ""
        recipients: list[str] = []
        self._send("220 qikvrt.local ESMTP QIK-VRT")
        while True:
            try:
                line = self._line()
            except (ConnectionError, OSError):
                return
            except ValueError:
                self._send("500 command too long")
                return
            upper = line.upper()
            if upper.startswith("EHLO ") or upper.startswith("HELO "):
                self._send("250-qikvrt.local")
                self._send(f"250 SIZE {MAX_SMTP_MESSAGE}")
            elif upper.startswith("MAIL FROM:"):
                sender = line[10:].strip()
                recipients = []
                self._send("250 sender accepted")
            elif upper.startswith("RCPT TO:"):
                recipient = line[8:].strip()
                normalized = recipient.strip("<>").lower()
                if "@" not in normalized or normalized.rsplit("@", 1)[1] not in {
                    LOCAL_MAIL_DOMAIN,
                    "localhost",
                }:
                    self._send("550 relay denied; local recipients only")
                else:
                    recipients.append(recipient)
                    self._send("250 recipient accepted")
            elif upper == "DATA":
                if not sender or not recipients:
                    self._send("503 MAIL FROM and RCPT TO required")
                    continue
                self._send("354 end data with <CRLF>.<CRLF>")
                chunks: list[bytes] = []
                total = 0
                while True:
                    raw = self.rfile.readline(64 * 1024)
                    if not raw:
                        return
                    if raw in {b".\n", b".\r\n"}:
                        break
                    if raw.startswith(b".."):
                        raw = raw[1:]
                    total += len(raw)
                    if total > MAX_SMTP_MESSAGE:
                        self._send("552 message exceeds bound")
                        return
                    chunks.append(raw)
                body = b"".join(chunks)
                digest = hashlib.sha256(
                    sender.encode("utf-8")
                    + b"\0"
                    + "\n".join(recipients).encode("utf-8")
                    + b"\0"
                    + body
                ).hexdigest()
                mail_dir: Path = self.server.mail_dir  # type: ignore[attr-defined]
                mail_dir.mkdir(parents=True, exist_ok=True)
                target = mail_dir / f"{digest}.eml"
                envelope = (
                    f"X-QIKVRT-Envelope-From: {sender}\n"
                    f"X-QIKVRT-Envelope-To: {', '.join(recipients)}\n"
                ).encode("utf-8")
                target.write_bytes(envelope + body)
                self._send(f"250 stored sha256={digest}")
                sender = ""
                recipients = []
            elif upper == "RSET":
                sender = ""
                recipients = []
                self._send("250 reset")
            elif upper == "NOOP":
                self._send("250 ok")
            elif upper == "QUIT":
                self._send("221 bye")
                return
            else:
                self._send("502 unsupported command")


def _dns_qname(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    while True:
        if offset >= len(data):
            raise ValueError("truncated DNS name")
        length = data[offset]
        offset += 1
        if length == 0:
            break
        if length & 0xC0:
            raise ValueError("compressed query names are not accepted")
        if offset + length > len(data):
            raise ValueError("truncated DNS label")
        labels.append(data[offset : offset + length].decode("ascii").lower())
        offset += length
    return ".".join(labels), offset


def _dns_name(name: str) -> bytes:
    result = bytearray()
    for label in name.rstrip(".").split("."):
        encoded = label.encode("ascii")
        if not 1 <= len(encoded) <= 63:
            raise ValueError("invalid DNS label")
        result.append(len(encoded))
        result.extend(encoded)
    result.append(0)
    return bytes(result)


def build_dns_response(data: bytes) -> bytes:
    if len(data) < 12:
        raise ValueError("short DNS packet")
    ident, flags, qdcount, _, _, _ = struct.unpack("!HHHHHH", data[:12])
    if qdcount != 1 or flags & 0x8000:
        raise ValueError("exactly one DNS query is required")
    name, offset = _dns_qname(data, 12)
    if offset + 4 > len(data):
        raise ValueError("truncated DNS question")
    qtype, qclass = struct.unpack("!HH", data[offset : offset + 4])
    question = data[12 : offset + 4]
    authoritative_flags = 0x8000 | 0x0400 | (flags & 0x0100)
    answers: list[bytes] = []
    rcode = 0
    if name == LOCAL_MAIL_DOMAIN and qclass == 1:
        if qtype == 1:
            rdata = socket.inet_aton("127.0.0.1")
            answers.append(b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 60, len(rdata)) + rdata)
        elif qtype == 16:
            text = b"qikvrt universal terminal"
            rdata = bytes([len(text)]) + text
            answers.append(b"\xc0\x0c" + struct.pack("!HHIH", 16, 1, 60, len(rdata)) + rdata)
    else:
        rcode = 3
    header = struct.pack(
        "!HHHHHH",
        ident,
        authoritative_flags | rcode,
        1,
        len(answers),
        0,
        0,
    )
    return header + question + b"".join(answers)


class DNSUDPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data, sock = self.request
        try:
            response = build_dns_response(data)
        except ValueError:
            return
        sock.sendto(response, self.client_address)


class DNSTCPHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.read(2)
        if len(raw) != 2:
            return
        length = struct.unpack("!H", raw)[0]
        if length < 12 or length > 4096:
            return
        data = self.rfile.read(length)
        if len(data) != length:
            return
        try:
            response = build_dns_response(data)
        except ValueError:
            return
        self.wfile.write(struct.pack("!H", len(response)) + response)


def _ber_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _ber_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _ber_length(len(value)) + value


def _ber_integer(value: int) -> bytes:
    if value == 0:
        raw = b"\x00"
    else:
        width = max(1, (value.bit_length() + 7) // 8)
        raw = value.to_bytes(width, "big", signed=value < 0)
        if value >= 0 and raw[0] & 0x80:
            raw = b"\x00" + raw
    return _ber_tlv(0x02, raw)


def _ber_oid(oid: tuple[int, ...]) -> bytes:
    if len(oid) < 2:
        raise ValueError("short OID")
    out = bytearray([oid[0] * 40 + oid[1]])
    for component in oid[2:]:
        if component < 0:
            raise ValueError("negative OID component")
        stack = [component & 0x7F]
        component >>= 7
        while component:
            stack.append(0x80 | (component & 0x7F))
            component >>= 7
        out.extend(reversed(stack))
    return _ber_tlv(0x06, bytes(out))


def _read_tlv(data: bytes, offset: int = 0) -> tuple[int, bytes, int]:
    if offset >= len(data):
        raise ValueError("missing BER tag")
    tag = data[offset]
    offset += 1
    if offset >= len(data):
        raise ValueError("missing BER length")
    first = data[offset]
    offset += 1
    if first & 0x80:
        count = first & 0x7F
        if count == 0 or count > 4 or offset + count > len(data):
            raise ValueError("invalid BER length")
        length = int.from_bytes(data[offset : offset + count], "big")
        offset += count
    else:
        length = first
    end = offset + length
    if end > len(data):
        raise ValueError("truncated BER value")
    return tag, data[offset:end], end


def _parse_int(value: bytes) -> int:
    if not value:
        raise ValueError("empty BER integer")
    return int.from_bytes(value, "big", signed=bool(value[0] & 0x80))


def _parse_oid(value: bytes) -> tuple[int, ...]:
    if not value:
        raise ValueError("empty OID")
    first = value[0]
    oid = [min(2, first // 40), first - min(2, first // 40) * 40]
    number = 0
    active = False
    for byte in value[1:]:
        active = True
        number = (number << 7) | (byte & 0x7F)
        if not byte & 0x80:
            oid.append(number)
            number = 0
            active = False
    if active:
        raise ValueError("truncated OID")
    return tuple(oid)


def build_snmp_response(data: bytes) -> bytes:
    tag, outer, end = _read_tlv(data)
    if tag != 0x30 or end != len(data):
        raise ValueError("SNMP message must be one sequence")
    tag, version_raw, offset = _read_tlv(outer, 0)
    if tag != 0x02 or _parse_int(version_raw) != 1:
        raise ValueError("SNMPv2c required")
    tag, community, offset = _read_tlv(outer, offset)
    if tag != 0x04 or community != b"qikvrt":
        raise ValueError("unsupported SNMP community")
    pdu_tag, pdu, pdu_end = _read_tlv(outer, offset)
    if pdu_tag != 0xA0 or pdu_end != len(outer):
        raise ValueError("SNMP GET request required")
    tag, request_id_raw, p = _read_tlv(pdu, 0)
    if tag != 0x02:
        raise ValueError("missing request id")
    request_id = _parse_int(request_id_raw)
    tag, error_raw, p = _read_tlv(pdu, p)
    if tag != 0x02 or _parse_int(error_raw) != 0:
        raise ValueError("nonzero request error")
    tag, index_raw, p = _read_tlv(pdu, p)
    if tag != 0x02 or _parse_int(index_raw) != 0:
        raise ValueError("nonzero request error index")
    tag, varbinds, p = _read_tlv(pdu, p)
    if tag != 0x30 or p != len(pdu):
        raise ValueError("malformed varbind list")
    tag, varbind, vb_end = _read_tlv(varbinds, 0)
    if tag != 0x30 or vb_end != len(varbinds):
        raise ValueError("exactly one varbind is supported")
    tag, oid_raw, q = _read_tlv(varbind, 0)
    if tag != 0x06:
        raise ValueError("missing OID")
    oid = _parse_oid(oid_raw)
    _, _, q = _read_tlv(varbind, q)
    if q != len(varbind):
        raise ValueError("trailing varbind bytes")

    if oid == SYS_DESCR_OID:
        value = _ber_tlv(0x04, SYS_DESCR.encode("utf-8"))
        error_status = 0
    elif oid == SYS_NAME_OID:
        value = _ber_tlv(0x04, SYS_NAME.encode("utf-8"))
        error_status = 0
    else:
        value = _ber_tlv(0x80, b"")  # noSuchObject exception
        error_status = 0

    response_varbind = _ber_tlv(0x30, _ber_oid(oid) + value)
    response_list = _ber_tlv(0x30, response_varbind)
    response_pdu = _ber_tlv(
        0xA2,
        _ber_integer(request_id) + _ber_integer(error_status) + _ber_integer(0) + response_list,
    )
    return _ber_tlv(0x30, _ber_integer(1) + _ber_tlv(0x04, community) + response_pdu)


class SNMPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data, sock = self.request
        try:
            response = build_snmp_response(data)
        except ValueError:
            return
        sock.sendto(response, self.client_address)


def dns_query_packet(name: str = LOCAL_MAIL_DOMAIN) -> bytes:
    ident = 0x514B
    question = _dns_name(name) + struct.pack("!HH", 1, 1)
    return struct.pack("!HHHHHH", ident, 0x0100, 1, 0, 0, 0) + question


def snmp_get_packet(oid: tuple[int, ...] = SYS_DESCR_OID) -> bytes:
    varbind = _ber_tlv(0x30, _ber_oid(oid) + _ber_tlv(0x05, b""))
    pdu = _ber_tlv(0xA0, _ber_integer(1) + _ber_integer(0) + _ber_integer(0) + _ber_tlv(0x30, varbind))
    return _ber_tlv(0x30, _ber_integer(1) + _ber_tlv(0x04, b"qikvrt") + pdu)


def self_test() -> None:
    with socket.create_connection((SMTP_HOST, SMTP_PORT), timeout=3) as sock:
        banner = sock.recv(512)
        if not banner.startswith(b"220 "):
            raise SystemExit("BLOCK: SMTP banner missing")
        sock.sendall(b"EHLO health.qikvrt.local\r\nQUIT\r\n")
        reply = sock.recv(2048)
        if b"250-" not in reply and b"250 " not in reply:
            raise SystemExit("BLOCK: SMTP EHLO failed")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        query = dns_query_packet()
        sock.sendto(query, (DNS_HOST, DNS_PORT))
        response, _ = sock.recvfrom(4096)
        if len(response) < 12 or struct.unpack("!H", response[6:8])[0] != 1:
            raise SystemExit("BLOCK: DNS A response missing")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        request = snmp_get_packet()
        sock.sendto(request, (SNMP_HOST, SNMP_PORT))
        response, _ = sock.recvfrom(4096)
        if SYS_DESCR.encode("utf-8") not in response:
            raise SystemExit("BLOCK: SNMP sysDescr response missing")


def serve(state_dir: Path) -> None:
    mail_dir = state_dir / "mail"
    mail_dir.mkdir(parents=True, exist_ok=True)

    smtp = ReuseThreadingTCPServer((SMTP_HOST, SMTP_PORT), SMTPHandler)
    smtp.mail_dir = mail_dir  # type: ignore[attr-defined]
    dns_udp = ReuseThreadingUDPServer((DNS_HOST, DNS_PORT), DNSUDPHandler)
    dns_tcp = ReuseThreadingTCPServer((DNS_HOST, DNS_PORT), DNSTCPHandler)
    snmp = ReuseThreadingUDPServer((SNMP_HOST, SNMP_PORT), SNMPHandler)
    servers = [smtp, dns_udp, dns_tcp, snmp]
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in servers]
    for thread in threads:
        thread.start()
    print(
        "QIKVRT service plane ready "
        f"smtp={SMTP_HOST}:{SMTP_PORT} dns={DNS_HOST}:{DNS_PORT} snmp={SNMP_HOST}:{SNMP_PORT}",
        flush=True,
    )
    try:
        while all(thread.is_alive() for thread in threads):
            time.sleep(1)
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
    raise SystemExit("service-plane listener stopped")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/qikvrt/state"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    serve(args.state_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
