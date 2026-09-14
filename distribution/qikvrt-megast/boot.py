#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build, serve, receive and boot an exact QIK-VRT network image.

The manifest digest is a caller-supplied trust anchor. Download/receipt alone
never counts as guest execution. No shell from a downloaded manifest is run.
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import socketserver
import struct
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request

FILES = {"kernel": "qikvrt-megast-vmlinuz", "initrd": "qikvrt-megast-initrd",
         "rootfs": "qikvrt-megast-filesystem.squashfs", "m68000": "QIKVRT_BOOT.BIN"}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEADER = struct.Struct("!4sB3xIIIIII")
CHUNK = 128
MAX_BOOT = 4 * 1024 * 1024


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def fnv(data: bytes) -> int:
    result = 2166136261
    for byte in data:
        result = ((result ^ byte) * 16777619) & 0xffffffff
    return result


def frame(kind: int, nonce: int, offset: int, total: int, data: bytes = b"") -> bytes:
    header = HEADER.pack(b"QBT1", kind, nonce, 1, offset, total, len(data), 0)
    return header[:28] + struct.pack("!I", fnv(header[:28] + data)) + data


class BootDatagramServer(socketserver.UDPServer):
    """Bounded, stateless retransmission for the fixed file-id 1 route."""
    def __init__(self, address: tuple[str, int], image: bytes):
        if not 0 < len(image) <= MAX_BOOT:
            raise ValueError("bootstrap image outside 4 MiB bound")
        self.image = image
        self.image_digest = hashlib.sha256(image).digest()
        self.completed: list[dict] = []
        super().__init__(address, BootDatagramHandler)


class BootDatagramHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        packet, connection = self.request
        if len(packet) != HEADER.size or packet[5:8] != b"\0\0\0":
            return
        magic, kind, nonce, file_id, offset, total, length, checksum = HEADER.unpack(packet)
        if magic != b"QBT1" or file_id != 1 or nonce == 0 or length != 0 or fnv(packet[:28]) != checksum:
            return
        image = self.server.image
        if kind == 1 and offset == 0 and total == 0:
            reply = frame(2, nonce, 0, len(image), self.server.image_digest)
        elif kind == 3 and total == len(image) and offset < total and offset % CHUNK == 0:
            reply = frame(4, nonce, offset, total, image[offset:offset + CHUNK])
        elif kind == 5 and total == len(image) and offset == total:
            reply = frame(5, nonce, offset, total)
            # A peer assertion remains a transport record, never boot evidence.
            self.server.completed.append({"nonce": nonce, "peer_reported_content_done": True, "booted": False})
            self.server.completed[:] = self.server.completed[-128:]
        else:
            return
        connection.sendto(reply, self.client_address)


def validate_manifest(manifest: dict) -> None:
    if manifest.get("schema") != "qikvrt_netboot_v1" or manifest.get("architecture") != "x86_64":
        raise ValueError("unsupported boot schema/architecture")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("source_sha", "")):
        raise ValueError("missing exact source commit")
    if manifest.get("boot_method") != "linux-live-http" or set(manifest.get("files", {})) != set(FILES):
        raise ValueError("unsupported boot method/files")
    for kind, name in FILES.items():
        entry = manifest["files"][kind]
        if entry.get("name") != name or not HEX64.fullmatch(entry.get("sha256", "")):
            raise ValueError("unbound file identity")
        size = entry.get("bytes")
        if type(size) is not int or not 0 < size <= 2 * 1024 ** 3:
            raise ValueError("file size outside contract")


def make_manifest(directory: Path, source_sha: str) -> dict:
    manifest = {"schema": "qikvrt_netboot_v1", "source_sha": source_sha,
                "architecture": "x86_64", "boot_method": "linux-live-http",
                "guest_m68000": "qemu-m68k-static-contract", "effect_ack_done": False,
                "files": {k: {"name": n, "bytes": (directory / n).stat().st_size, "sha256": sha256(directory / n)} for k, n in FILES.items()}}
    validate_manifest(manifest)
    path = directory / "qikvrt-netboot.json"
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    (directory / "qikvrt-netboot.json.sha256").write_text(sha256(path) + "  " + path.name + "\n")
    return manifest


def safe_url(url: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.username or parts.password or parts.fragment or parts.query:
        raise ValueError("URL must not contain credentials, query or fragment")
    if parts.scheme == "https" and parts.hostname:
        return
    if parts.scheme == "http":
        if parts.hostname == "localhost":
            return
        try:
            if ipaddress.ip_address(parts.hostname).is_private:
                return
        except ValueError:
            pass
    raise ValueError("Use HTTPS or an explicit private test-network IP")


def download(url: str, path: Path, expected: str, size: int) -> None:
    safe_url(url)
    if path.exists():
        if path.stat().st_size == size and sha256(path) == expected:
            return
        raise ValueError("existing file does not match bound image")
    temp = path.with_suffix(path.suffix + ".partial")
    try:
        with urllib.request.urlopen(url, timeout=60) as source, temp.open("xb") as output:
            total = 0
            while data := source.read(1024 * 1024):
                total += len(data)
                if total > size:
                    raise ValueError("download exceeds bound size")
                output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if total != size or sha256(temp) != expected:
            raise ValueError("download hash/size mismatch")
        temp.rename(path)
    finally:
        temp.unlink(missing_ok=True)


def receive(url: str, expected: str, directory: Path) -> dict:
    if not HEX64.fullmatch(expected):
        raise ValueError("supply the expected manifest SHA256")
    safe_url(url)
    directory.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("manifest digest/size mismatch")
    manifest = json.loads(raw)
    validate_manifest(manifest)
    for entry in manifest["files"].values():
        download(urllib.parse.urljoin(url, entry["name"]), directory / entry["name"], entry["sha256"], entry["bytes"])
    (directory / "qikvrt-netboot.json").write_bytes(raw)
    return manifest


def guest_memory_mib(manifest: dict) -> int:
    # fetch= retains the compressed filesystem in RAM. The default live-boot
    # tmpfs limit is half of guest RAM; leave at least another GiB for the GUI.
    root_mib = (manifest["files"]["rootfs"]["bytes"] + 1024**2 - 1) // 1024**2
    return max(4096, ((2 * root_mib + 1024 + 255) // 256) * 256)


def qemu_acceleration() -> str:
    # Hosted runners may expose hardware virtualization only after the workflow
    # grants its unprivileged job user access to /dev/kvm.  Preserve a portable
    # multi-threaded TCG fallback for local and non-KVM execution.
    return "kvm" if os.access("/dev/kvm", os.R_OK | os.W_OK) else "tcg,thread=multi"


def capture_display(directory: Path, screenshot: Path) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as qmp:
        qmp.settimeout(10)
        qmp.connect(str(directory / "qikvrt-qmp.sock"))
        with qmp.makefile("rwb") as stream:
            json.loads(stream.readline())
            for request in ({"execute": "qmp_capabilities"}, {"execute": "screendump", "arguments": {"filename": str(screenshot)}}):
                stream.write(json.dumps(request).encode() + b"\n"); stream.flush()
                while True:
                    result = json.loads(stream.readline())
                    if "error" in result:
                        raise ValueError("QMP screenshot failed")
                    if "return" in result:
                        break


def boot(directory: Path, manifest: dict, *, timeout: int = 900, verify_only: bool = False) -> dict:
    validate_manifest(manifest)
    if platform.machine() not in ("x86_64", "AMD64"):
        raise ValueError("client CPU must match the amd64 host image")
    for entry in manifest["files"].values():
        path = directory / entry["name"]
        if path.is_symlink() or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError("artifact changed after verification")
    qemu = shutil.which("qemu-system-x86_64")
    if not qemu:
        raise ValueError("qemu-system-x86_64 is required to execute the image")
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=str(directory), **kwargs)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    logfile = directory / "qikvrt-netboot-serial.log"
    command = [qemu, "-accel", qemu_acceleration(), "-m", str(guest_memory_mib(manifest)), "-smp", "2", "-display", "none" if verify_only or not os.environ.get("DISPLAY") else "gtk", "-serial", "stdio",
               "-qmp", "unix:" + str(directory / "qikvrt-qmp.sock") + ",server=on,wait=off",
               "-netdev", "user,id=network", "-device", "e1000,netdev=network",
               "-kernel", str(directory / FILES["kernel"]), "-initrd", str(directory / FILES["initrd"]),
               "-append", f"boot=live components username=qikvrt hostname=qikvrt-megast ip=dhcp fetch=http://10.0.2.2:{port}/{FILES['rootfs']} console=tty0 console=ttyS0,115200n8",
               "-no-reboot"]
    marker = f"QIKVRT_MEGAST_RUNTIME_OK source_sha={manifest['source_sha']}"
    try:
        with logfile.open("wb") as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + timeout
                while process.poll() is None and time.monotonic() < deadline:
                    observed = logfile.read_text(errors="replace")
                    if marker in observed or "QIKVRT_RUNTIME_BLOCK" in observed:
                        break
                    time.sleep(1)
                if marker not in logfile.read_text(errors="replace"):
                    try:
                        capture_display(directory, directory / "qikvrt-netboot-failure.ppm")
                    except (OSError, ValueError):
                        pass
                    serial = logfile.read_text(errors="replace")
                    (directory / "qikvrt-netboot-failure.json").write_text(json.dumps({
                        "source_sha": manifest["source_sha"], "guest_memory_mib": guest_memory_mib(manifest),
                        "guest_runtime_reobserved": False, "serial_sha256": sha256(logfile),
                        "effect_ack_done": False, "reason": "GUEST_RUNTIME_BLOCKED" if "QIKVRT_RUNTIME_BLOCK" in serial else "NO_EXACT_RUNTIME_WITNESS"}, indent=2) + "\n")
                    print(serial[-65536:], flush=True)
                    raise ValueError("no exact-source runtime evidence from network-booted guest; serial_tail:\n" + serial[-16384:])
                screenshot = directory / "qikvrt-netboot.ppm"
                capture_display(directory, screenshot)
                pixels = screenshot.read_bytes().split(b"\n", 3)
                if len(pixels) != 4 or pixels[0] != b"P6" or pixels[2] != b"255":
                    raise ValueError("invalid graphical screenshot")
                colors = {pixels[3][i:i+3] for i in range(0, len(pixels[3]), 3)}
                if len(colors) < 16:
                    raise ValueError("graphical display lacks color UI evidence")
                receipt = {"schema": "qikvrt_netboot_receipt_v1", "source_sha": manifest["source_sha"],
                           "manifest_sha256": sha256(directory / "qikvrt-netboot.json"), "serial_sha256": sha256(logfile),
                           "screenshot_sha256": sha256(screenshot), "observed_colors": len(colors),
                           "boot_method": "linux-live-http", "guest_memory_mib": guest_memory_mib(manifest), "cdrom_attached": False, "guest_runtime_reobserved": True,
                           "physical_atari_boot": False, "effect_ack_done": False}
                (directory / "qikvrt-netboot-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                print("QIKVRT_NETWORK_BOOT_REOBSERVED source_sha=" + manifest["source_sha"], flush=True)
                if not verify_only:
                    process.wait()  # User session remains usable until its guest is closed.

            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait()
    finally:
        server.shutdown(); server.server_close()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("manifest"); make.add_argument("directory", type=Path); make.add_argument("source_sha")
    client = sub.add_parser("receive"); client.add_argument("url"); client.add_argument("sha256"); client.add_argument("directory", type=Path); client.add_argument("--boot", action="store_true"); client.add_argument("--verify-only", action="store_true")
    execute = sub.add_parser("boot"); execute.add_argument("directory", type=Path); execute.add_argument("--verify-only", action="store_true")
    serve = sub.add_parser("serve"); serve.add_argument("directory", type=Path); serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=7331)
    args = parser.parse_args()
    try:
        directory = args.directory.resolve()
        if args.command == "manifest":
            make_manifest(directory, args.source_sha)
        elif args.command == "receive":
            manifest = receive(args.url, args.sha256, directory)
            if args.boot:
                boot(directory, manifest, verify_only=args.verify_only)
        elif args.command == "boot":
            boot(directory, json.loads((directory / "qikvrt-netboot.json").read_text()), verify_only=args.verify_only)
        else:
            with BootDatagramServer((args.host, args.port), (directory / "QIKVRT_BOOT.BIN").read_bytes()) as server:
                server.serve_forever()
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("BLOCK: " + str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
