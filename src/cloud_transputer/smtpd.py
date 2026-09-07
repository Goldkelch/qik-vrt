#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded local SMTP service for the QIK-VRT cloud-transputer image.

The daemon intentionally has no relay path.  It accepts mail only for the
configured local mesh domain and stores the RFC-5322 bytes in persistent
operator-owned state.  Network delivery beyond the container is a separate
protected effect and is not implemented here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import socketserver
import time
from typing import BinaryIO

MAX_MESSAGE = 1024 * 1024
ADDRESS_RE = re.compile(rb"^<([^<>\r\n]+)>$")


class State:
    def __init__(self, root: pathlib.Path, domain: str) -> None:
        self.root = root
        self.domain = domain.lower()
        self.root.mkdir(parents=True, exist_ok=True)

    def accept_recipient(self, raw: bytes) -> bool:
        match = ADDRESS_RE.fullmatch(raw.strip())
        if not match:
            return False
        address = match.group(1).decode("utf-8", "strict")
        if "@" not in address:
            return False
        _local, domain = address.rsplit("@", 1)
        return domain.lower() == self.domain

    def persist(self, sender: str, recipients: list[str], payload: bytes) -> str:
        digest = hashlib.sha256(payload).hexdigest()
        stamp = int(time.time() * 1_000_000)
        stem = f"{stamp}-{digest[:16]}"
        message_path = self.root / f"{stem}.eml"
        receipt_path = self.root / f"{stem}.json"
        message_path.write_bytes(payload)
        receipt = {
            "schema": "qikvrt_local_smtp_receipt_v1",
            "sha256": digest,
            "bytes": len(payload),
            "mail_from": sender,
            "rcpt_to": recipients,
            "external_relay": False,
            "stored_at_unix": int(time.time()),
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        }
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return digest


class Handler(socketserver.StreamRequestHandler):
    state: State

    def send(self, text: str) -> None:
        self.wfile.write(text.encode("ascii") + b"\r\n")
        self.wfile.flush()

    def handle(self) -> None:
        self.send("220 qikvrt.mesh.local ESMTP QIKVRT")
        sender = ""
        recipients: list[str] = []
        greeted = False
        while True:
            line = self.rfile.readline(8192)
            if not line:
                return
            if len(line) >= 8192 and not line.endswith(b"\n"):
                self.send("500 line too long")
                return
            command = line.rstrip(b"\r\n")
            upper = command.upper()
            if upper.startswith(b"EHLO ") or upper.startswith(b"HELO "):
                greeted = True
                self.send("250-qikvrt.mesh.local")
                self.send(f"250-SIZE {MAX_MESSAGE}")
                self.send("250 8BITMIME")
            elif upper == b"NOOP":
                self.send("250 2.0.0 ok")
            elif upper == b"RSET":
                sender = ""
                recipients = []
                self.send("250 2.0.0 reset")
            elif upper == b"QUIT":
                self.send("221 2.0.0 bye")
                return
            elif upper.startswith(b"MAIL FROM:"):
                if not greeted:
                    self.send("503 5.5.1 send HELO/EHLO first")
                    continue
                raw = command[len(b"MAIL FROM:") :].strip()
                match = ADDRESS_RE.fullmatch(raw)
                if not match:
                    self.send("501 5.1.7 bad sender")
                    continue
                sender = match.group(1).decode("utf-8", "strict")
                recipients = []
                self.send("250 2.1.0 sender ok")
            elif upper.startswith(b"RCPT TO:"):
                if not sender:
                    self.send("503 5.5.1 MAIL required")
                    continue
                raw = command[len(b"RCPT TO:") :].strip()
                if not self.state.accept_recipient(raw):
                    self.send("550 5.7.1 local mesh domain only")
                    continue
                address = ADDRESS_RE.fullmatch(raw).group(1).decode("utf-8", "strict")  # type: ignore[union-attr]
                recipients.append(address)
                self.send("250 2.1.5 recipient ok")
            elif upper == b"DATA":
                if not sender or not recipients:
                    self.send("503 5.5.1 MAIL and RCPT required")
                    continue
                self.send("354 end with <CRLF>.<CRLF>")
                chunks: list[bytes] = []
                total = 0
                while True:
                    data_line = self.rfile.readline(8192)
                    if not data_line:
                        return
                    if data_line in {b".\r\n", b".\n"}:
                        break
                    if data_line.startswith(b".."):
                        data_line = data_line[1:]
                    total += len(data_line)
                    if total > MAX_MESSAGE:
                        self.send("552 5.3.4 message too large")
                        return
                    chunks.append(data_line)
                digest = self.state.persist(sender, recipients, b"".join(chunks))
                sender = ""
                recipients = []
                self.send(f"250 2.0.0 stored sha256={digest}")
            else:
                self.send("502 5.5.1 command not implemented")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("QIKVRT_SMTP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("QIKVRT_SMTP_PORT", "2525")))
    parser.add_argument("--domain", default=os.environ.get("QIKVRT_MESH_DOMAIN", "qikvrt.mesh.local"))
    parser.add_argument("--mail-root", default=os.environ.get("QIKVRT_MAIL_DIR", "/var/lib/qikvrt/mail"))
    args = parser.parse_args()
    state = State(pathlib.Path(args.mail_root), args.domain)
    Handler.state = state
    with Server((args.host, args.port), Handler) as server:
        server.serve_forever(poll_interval=0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
