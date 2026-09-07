#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socketserver
import time

MAX_MESSAGE_BYTES = 1024 * 1024


class SMTPHandler(socketserver.StreamRequestHandler):
    def send_line(self, value: str) -> None:
        self.wfile.write(value.encode("ascii") + b"\r\n")
        self.wfile.flush()

    def handle(self) -> None:
        self.send_line("220 qik-vrt.mesh QIKVRT SMTP sink ready")
        mail_from = None
        rcpt_to: list[str] = []
        while True:
            raw = self.rfile.readline(8192)
            if not raw:
                return
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            upper = line.upper()
            if upper.startswith("EHLO ") or upper.startswith("HELO "):
                self.send_line("250-qik-vrt.mesh")
                self.send_line("250 SIZE 1048576")
            elif upper.startswith("MAIL FROM:"):
                mail_from = line[10:].strip()
                rcpt_to = []
                self.send_line("250 2.1.0 sender accepted")
            elif upper.startswith("RCPT TO:"):
                if mail_from is None:
                    self.send_line("503 5.5.1 MAIL required")
                else:
                    rcpt_to.append(line[8:].strip())
                    self.send_line("250 2.1.5 recipient accepted")
            elif upper == "DATA":
                if mail_from is None or not rcpt_to:
                    self.send_line("503 5.5.1 MAIL and RCPT required")
                    continue
                self.send_line("354 end with <CRLF>.<CRLF>")
                chunks: list[bytes] = []
                size = 0
                while True:
                    data = self.rfile.readline(8192)
                    if not data:
                        return
                    if data in (b".\n", b".\r\n"):
                        break
                    if data.startswith(b".."):
                        data = data[1:]
                    size += len(data)
                    if size > MAX_MESSAGE_BYTES:
                        self.send_line("552 5.3.4 message too large")
                        return
                    chunks.append(data)
                payload = b"".join(chunks)
                digest = hashlib.sha256(payload).hexdigest()
                stamp = "%d-%s" % (int(time.time()), digest)
                data_path = os.path.join(self.server.spool, stamp + ".eml")
                meta_path = os.path.join(self.server.spool, stamp + ".json")
                with open(data_path, "wb") as stream:
                    stream.write(payload)
                meta = {
                    "schema": "qikvrt_smtp_sink_receipt_v1",
                    "mail_from": mail_from,
                    "rcpt_to": rcpt_to,
                    "sha256": digest,
                    "bytes": len(payload),
                    "relay_performed": False,
                }
                with open(meta_path, "w", encoding="utf-8") as stream:
                    json.dump(meta, stream, indent=2, sort_keys=True)
                    stream.write("\n")
                self.send_line("250 2.0.0 queued " + digest)
                mail_from = None
                rcpt_to = []
            elif upper == "RSET":
                mail_from = None
                rcpt_to = []
                self.send_line("250 2.0.0 reset")
            elif upper == "NOOP":
                self.send_line("250 2.0.0 ok")
            elif upper == "QUIT":
                self.send_line("221 2.0.0 bye")
                return
            else:
                self.send_line("502 5.5.1 command not implemented")


class SMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], spool: str) -> None:
        super().__init__(address, SMTPHandler)
        self.spool = spool


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=2525)
    parser.add_argument("--spool", required=True)
    args = parser.parse_args()
    os.makedirs(args.spool, exist_ok=True)
    with SMTPServer((args.host, args.port), args.spool) as server:
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
