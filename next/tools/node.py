#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Mutually authenticated TLS adapter for the existing durable C90 repository bus.

No replacement wire, queue or acknowledgement protocol: QVRT1/QXT2 and the
existing HMAC bus run unchanged inside TLS. The router is a trusted endpoint.
Private keys/configuration remain outside source and evidence artifacts.
"""
import argparse
import asyncio
import contextlib
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
import stat
import sys


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_file(path):
    path = Path(path)
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o077:
        raise ValueError("OWNER_ONLY_REGULAR_FILE_REQUIRED")
    return path


def read_private(path):
    path = private_file(path)
    if path.stat().st_size > 16384:
        raise ValueError("PRIVATE_CONFIG_BOUND")
    return json.loads(path.read_text())


def fingerprint(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("CERTIFICATE_SHA256_REQUIRED")
    return value


def tls_context(ca, certificate, key, *, server=False):
    private_file(key)
    context = ssl.create_default_context(
        ssl.Purpose.CLIENT_AUTH if server else ssl.Purpose.SERVER_AUTH,
        cafile=str(ca))
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(str(certificate), str(key))
    if not server:
        context.check_hostname = True
        context.hostname_checks_common_name = False
    return context


def certificate_digest(writer):
    session = writer.get_extra_info("ssl_object")
    if session is None or session.version() != "TLSv1.3":
        raise ValueError("TLS13_REQUIRED")
    certificate = session.getpeercert(binary_form=True)
    if not certificate:
        raise ValueError("PEER_CERTIFICATE_REQUIRED")
    return digest(certificate)


async def close(writer):
    writer.close()
    with contextlib.suppress(Exception):
        await asyncio.wait_for(writer.wait_closed(), 3)


async def pump(left_reader, left_writer, right_reader, right_writer):
    async def copy(reader, writer):
        while block := await reader.read(16384):
            writer.write(block)
            await writer.drain()
    tasks = [asyncio.create_task(copy(left_reader, right_writer)),
             asyncio.create_task(copy(right_reader, left_writer))]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(close(left_writer), close(right_writer))
    # Disconnects are not delivery ACKs. Persisted frames replay on re-entry.


class RouterRelay:
    def __init__(self, backend, certificates):
        if not 1 <= len(certificates) <= 16:
            raise ValueError("PEER_DIRECTORY_BOUND")
        self.backend = backend
        self.allowed = {fingerprint(value): key for key, value in certificates.items()}
        if len(self.allowed) != len(certificates):
            raise ValueError("DISTINCT_PEER_CERTIFICATES_REQUIRED")
        self.active = set()

    async def handle(self, reader, writer):
        remote = None
        peer = None
        owned = False
        try:
            peer = self.allowed.get(certificate_digest(writer))
            if peer is None or peer in self.active:
                raise ValueError("UNADMITTED_OR_DUPLICATE_TLS_PEER")
            self.active.add(peer)
            owned = True
            upstream, remote = await asyncio.wait_for(
                asyncio.open_connection(*self.backend, limit=8192), 5)
            challenge = await asyncio.wait_for(upstream.readline(), 5)
            if not challenge.endswith(b"\n") or len(challenge) > 4096:
                raise ValueError("BUS_CHALLENGE_BOUND")
            writer.write(challenge)
            await writer.drain()
            join = await asyncio.wait_for(reader.readline(), 5)
            if (not join.endswith(b"\n") or len(join) > 4096
                    or json.loads(join).get("id") != peer):
                raise ValueError("TLS_CERTIFICATE_BUS_IDENTITY_MISMATCH")
            remote.write(join)
            await remote.drain()
            await pump(reader, writer, upstream, remote)
        except (OSError, ValueError, TimeoutError, ssl.SSLError, json.JSONDecodeError):
            pass  # No admission, store mutation, ACK or secret-bearing log.
        finally:
            if owned:
                self.active.discard(peer)
            await close(writer)
            if remote is not None:
                await close(remote)


class PeerRelay:
    def __init__(self, address, hostname, context, server_digest):
        self.address, self.hostname, self.context = address, hostname, context
        self.server_digest = fingerprint(server_digest)
        self.active = False

    async def handle(self, reader, writer):
        remote = None
        owned = False
        try:
            if self.active:
                raise ValueError("ONE_LOCAL_PEER_REQUIRED")
            self.active = owned = True
            upstream, remote = await asyncio.wait_for(asyncio.open_connection(
                *self.address, ssl=self.context, server_hostname=self.hostname,
                ssl_handshake_timeout=5, ssl_shutdown_timeout=3, limit=8192), 8)
            if certificate_digest(remote) != self.server_digest:
                raise ValueError("ROUTER_CERTIFICATE_PIN_MISMATCH")
            await pump(reader, writer, upstream, remote)
        except (OSError, ValueError, TimeoutError, ssl.SSLError):
            pass
        finally:
            if owned:
                self.active = False
            await close(writer)
            if remote is not None:
                await close(remote)


def address(value):
    host, port = value.rsplit(":", 1)
    host = host.strip("[]")
    ipaddress.ip_address(host)
    port = int(port)
    if not 0 <= port <= 65535:
        raise ValueError("PORT_BOUND")
    return host, port


def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)


async def run(args):
    binary = args.binary.resolve()
    if digest(binary.read_bytes()) != fingerprint(args.binary_sha256):
        raise ValueError("INSTALLED_BINARY_MISMATCH")
    config = read_private(args.config)
    context = tls_context(args.ca, args.certificate, args.key, server=args.mode == "router")
    process = None
    listener = None
    try:
        if args.mode == "router":
            certificates = json.loads(args.peer_certificates.read_text())
            if set(certificates) != {peer["id"] for peer in config["peers"]}:
                raise ValueError("TLS_BUS_DIRECTORY_MISMATCH")
            process = await asyncio.create_subprocess_exec(str(binary), "bus-serve",
                str(args.store), str(args.config), "127.0.0.1:0", "--supervised",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
            line = await asyncio.wait_for(process.stdout.readline(), 10)
            ready = json.loads(line)
            if ready.get("state") != "LISTENING":
                raise ValueError("BUS_NOT_READY")
            relay = RouterRelay(address(ready["address"]), certificates)
            listener = await asyncio.start_server(relay.handle, *address(args.address),
                ssl=context, ssl_handshake_timeout=5, ssl_shutdown_timeout=3,
                limit=8192, backlog=16)
            emit({"state": "TLS_ROUTER_LISTENING", "address": listener.sockets[0].getsockname()[:2],
                  "binary_sha256": args.binary_sha256, "effect_ack_done": False})
        else:
            if not config.get("repositories") or config["id"] not in config["repositories"]:
                raise ValueError("BOUND_REPOSITORY_DIRECTORY_REQUIRED")
            subject = json.loads(args.subject.read_text())
            if subject != config["repositories"][config["id"]]:
                raise ValueError("INSTALLED_REPOSITORY_SUBJECT_MISMATCH")
            relay = PeerRelay(address(args.address), args.server_name, context,
                              args.server_certificate_sha256)
            listener = await asyncio.start_server(relay.handle, "127.0.0.1", 0,
                                                  limit=8192, backlog=1)
            port = listener.sockets[0].getsockname()[1]
            process = await asyncio.create_subprocess_exec(str(binary), "bus-peer",
                str(args.store), str(args.config), f"127.0.0.1:{port}",
                "--worker", "--terminal", args.terminal,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
            # Retain stdin: service lifetime is not tied to an interactive shell.
        async for line in process.stdout:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        code = await process.wait()
        if code:
            raise ValueError("BUS_STOPPED_HISTORY_RETAINED")
    finally:
        if listener:
            listener.close()
            await listener.wait_closed()
        if process and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("router", "peer"):
        p = sub.add_parser(mode)
        for name in ("binary", "store", "config", "ca", "certificate", "key"):
            p.add_argument("--" + name, type=Path, required=True)
        p.add_argument("--binary-sha256", required=True)
        p.add_argument("--address", required=True)
        if mode == "router":
            p.add_argument("--peer-certificates", type=Path, required=True)
        else:
            p.add_argument("--subject", type=Path, required=True)
            p.add_argument("--server-name", required=True)
            p.add_argument("--server-certificate-sha256", required=True)
            p.add_argument("--terminal", default="127.0.0.1:8772")
    argv = sys.argv[1:]
    if len(argv) == 2 and argv[0] == "profile":
        profile = read_private(argv[1])
        if profile.pop("schema", None) != "qikvrt-repository-node-profile-v1":
            raise ValueError("NODE_PROFILE_SCHEMA")
        mode = profile.pop("mode", None)
        if mode not in ("router", "peer") or any(not isinstance(v, str) for v in profile.values()):
            raise ValueError("NODE_PROFILE_FIELDS")
        argv = [mode]
        for key, value in profile.items():
            argv.extend(["--" + key.replace("_", "-"), value])
    args = parser.parse_args(argv)
    try:
        asyncio.run(run(args))
    except (ValueError, OSError, TimeoutError) as error:
        emit({"state": "HOLD", "reason": str(error), "effect_ack_done": False})
        raise SystemExit(2)


if __name__ == "__main__":
    main()
