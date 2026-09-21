#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build, serve, receive and boot an exact QIK-VRT network image.

The manifest digest is a caller-supplied trust anchor. Download/receipt alone
never counts as guest execution. No shell from a downloaded manifest is run.
"""
from __future__ import annotations

import argparse
import base64
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
SSH_KEY_PATH = Path("/sys/firmware/qemu_fw_cfg/by_name/opt/qikvrt/ssh-key/raw")


def ed25519_public_key(value: str) -> str:
    """Accept one plain key, never authorized_keys options or multiple keys."""
    fields = value.strip().split()
    if "\n" in value.strip() or len(fields) < 2 or fields[0] != "ssh-ed25519":
        raise ValueError("supply one plain Ed25519 public key")
    try:
        wire = base64.b64decode(fields[1], validate=True)
    except ValueError as error:
        raise ValueError("invalid Ed25519 encoding") from error
    if len(wire) != 51 or wire[:19] != b"\0\0\0\x0bssh-ed25519\0\0\0\x20":
        raise ValueError("invalid Ed25519 public key")
    return "ssh-ed25519 " + base64.b64encode(wire).decode("ascii")


def ssh_guest(authorized_key: Path = SSH_KEY_PATH) -> None:
    """Opt-in guest service; the ordinary Live ISO opens no SSH listener."""
    if not authorized_key.exists():
        return
    key = ed25519_public_key(authorized_key.read_text())
    subject = json.loads(Path("/etc/qikvrt/distribution.json").read_text())
    state = Path("/var/lib/qikvrt/ssh")
    state.mkdir(mode=0o755, parents=True, exist_ok=True)
    Path("/run/sshd").mkdir(mode=0o755, exist_ok=True)
    keys = state / "authorized_keys"
    keys.write_text(key + "\n")
    keys.chmod(0o644)  # public; sshd reads this as the unprivileged live user
    host = state / "ssh_host_ed25519_key"
    if not host.exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(host)], check=True)
    host_key = ed25519_public_key(host.with_suffix(".pub").read_text())
    command = ["/usr/sbin/sshd", "-D", "-e", "-f", "/etc/ssh/qikvrt_sshd_config",
               "-o", "PermitRootLogin=no", "-o", "AllowUsers=qikvrt"]
    subprocess.run(command + ["-t"], check=True)
    record = {"source_sha": subject["source_sha"], "source_tree": subject["source_tree"],
              "host_key": host_key, "user": "qikvrt", "port": 2222}
    # The trusted VM console carries the host public key, not a login secret.
    with open("/dev/ttyS0", "w") as serial:
        serial.write("\nQIKVRT_SSH_HOST " + json.dumps(record, sort_keys=True) + "\n")
        serial.flush()
    os.execv(command[0], command)


def ssh_host_record(serial: str, manifest: dict) -> dict:
    records = []
    for line in serial.splitlines(keepends=True):
        if not line.endswith(("\n", "\r")) or not line.startswith("QIKVRT_SSH_HOST "):
            continue
        record = json.loads(line[len("QIKVRT_SSH_HOST "):])
        if (record.get("source_sha") != manifest["source_sha"] or
                record.get("source_tree") != manifest.get("source_tree") or
                record.get("user") != "qikvrt" or record.get("port") != 2222):
            raise ValueError("SSH host witness does not match exact guest subject")
        record["host_key"] = ed25519_public_key(record["host_key"])
        records.append(record)
    if not records or any(record != records[0] for record in records):
        raise ValueError("missing or conflicting SSH host witness")
    return records[0]


def ssh_readback(directory: Path, manifest: dict, serial: str, port: int,
                 identity: Path | None, reject_identity: Path | None = None) -> dict:
    record = ssh_host_record(serial, manifest)
    known_hosts = directory / "qikvrt-netboot-known-hosts"
    known_hosts.write_text(f"[127.0.0.1]:{port} {record['host_key']}\n")
    receipt = {"schema": "qikvrt_netboot_ssh_receipt_v1", **record,
               "host_port": port, "host_bind": "127.0.0.1",
               "authenticated_readback": False, "unauthorized_key_rejected": False,
               "chatgpt_pairing": "NOT_ESTABLISHED", "effect_ack_done": False}
    if identity is not None:
        command = ["ssh", "-F", "/dev/null", "-T", "-p", str(port),
                   "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "IdentityAgent=none",
                   "-o", "StrictHostKeyChecking=yes", "-o", "GlobalKnownHostsFile=/dev/null",
                   "-o", "UserKnownHostsFile=" + str(known_hosts), "-o", "ConnectTimeout=5"]
        remote = "id -un; cat /etc/qikvrt/distribution.json"
        result = None
        # The console record precedes exec(sshd); allow only bounded startup.
        for _ in range(10):
            result = subprocess.run(command + ["-i", str(identity), "qikvrt@127.0.0.1", remote],
                                    text=True, capture_output=True, timeout=15)
            if result.returncode == 0 or "Connection refused" not in result.stderr:
                break
            time.sleep(1)
        if result.returncode != 0:
            raise ValueError("SSH authenticated readback failed: " + result.stderr[-2048:])
        user, separator, payload = result.stdout.partition("\n")
        subject = json.loads(payload) if separator else {}
        if (user != "qikvrt" or subject.get("schema") != "qikvrt_megast_distribution_v1" or
                subject.get("source_sha") != manifest["source_sha"] or
                subject.get("source_tree") != manifest["source_tree"]):
            raise ValueError("SSH readback does not match exact guest subject/user")
        receipt["authenticated_readback"] = True
        receipt["readback_sha256"] = hashlib.sha256(result.stdout.encode()).hexdigest()
        if reject_identity is not None:
            denied = subprocess.run(command + ["-i", str(reject_identity), "qikvrt@127.0.0.1", remote],
                                    text=True, capture_output=True, timeout=15)
            if denied.returncode != 255 or "Permission denied (publickey)" not in denied.stderr:
                raise ValueError("unauthorized SSH identity was not explicitly rejected")
            receipt["unauthorized_key_rejected"] = True
    (directory / "qikvrt-netboot-ssh-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


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
    if "source_tree" in manifest and not re.fullmatch(r"[0-9a-f]{40}", manifest["source_tree"]):
        raise ValueError("invalid exact source tree")
    if manifest.get("boot_method") != "linux-live-http" or set(manifest.get("files", {})) != set(FILES):
        raise ValueError("unsupported boot method/files")
    for kind, name in FILES.items():
        entry = manifest["files"][kind]
        if entry.get("name") != name or not HEX64.fullmatch(entry.get("sha256", "")):
            raise ValueError("unbound file identity")
        size = entry.get("bytes")
        if type(size) is not int or not 0 < size <= 2 * 1024 ** 3:
            raise ValueError("file size outside contract")


def make_manifest(directory: Path, source_sha: str, source_tree: str | None = None) -> dict:
    manifest = {"schema": "qikvrt_netboot_v1", "source_sha": source_sha,
                "architecture": "x86_64", "boot_method": "linux-live-http",
                "guest_m68000": "qemu-m68k-static-contract", "effect_ack_done": False,
                "files": {k: {"name": n, "bytes": (directory / n).stat().st_size, "sha256": sha256(directory / n)} for k, n in FILES.items()}}
    if source_tree is not None:
        manifest["source_tree"] = source_tree
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


def runtime_result(serial: str, source_sha: str) -> str | None:
    """Accept complete protocol lines, never quoted markers in diagnostics."""
    marker = f"QIKVRT_MEGAST_RUNTIME_OK source_sha={source_sha}"
    result = None
    for record in serial.splitlines(keepends=True):
        if not record.endswith(("\n", "\r")):
            continue
        line = record.rstrip("\r\n")
        if line == marker:
            result = "success"
        elif line.startswith("QIKVRT_RUNTIME_BLOCK "):
            # A failure must not be hidden by an earlier or later success line.
            return "failure"
    return result


def snapshot_serial(logfile: Path) -> Path:
    # QEMU can append shutdown messages and an interactive session keeps logging.
    # Bind receipts to immutable observed bytes, not the still-open console log.
    snapshot = logfile.with_name("qikvrt-netboot-witness.log")
    snapshot.write_bytes(logfile.read_bytes())
    return snapshot


class ImageHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Only serve fixed image assets; logs and private files are never routes."""
    def send_head(self):
        if self.path not in {"/" + name for name in FILES.values()}:
            self.send_error(404)
            return None
        return super().send_head()


def boot(directory: Path, manifest: dict, *, timeout: int = 900, verify_only: bool = False,
         ssh_public_key: Path | None = None, ssh_identity: Path | None = None,
         ssh_port: int = 2222, ssh_reject_identity: Path | None = None) -> dict:
    # These fixed paths describe the current attempt, never an earlier boot.
    for name in ("qikvrt-netboot-receipt.json", "qikvrt-netboot-failure.json",
                 "qikvrt-netboot-ssh-receipt.json", "qikvrt-netboot-known-hosts"):
        (directory / name).unlink(missing_ok=True)
    validate_manifest(manifest)
    netdev = "user,id=network"
    firmware = []
    if ssh_public_key is not None:
        if "source_tree" not in manifest or not 1024 <= ssh_port <= 65535:
            raise ValueError("SSH requires an exact source tree and an unprivileged host port")
        public_key = ed25519_public_key(ssh_public_key.read_text())
        for private in (ssh_identity, ssh_reject_identity):
            if private is not None and (not private.is_file() or private.resolve().is_relative_to(directory.resolve())):
                raise ValueError("SSH private keys must exist outside the HTTP-served image directory")
        if (verify_only or ssh_reject_identity is not None) and ssh_identity is None:
            raise ValueError("SSH verification requires --ssh-identity")
        netdev += f",hostfwd=tcp:127.0.0.1:{ssh_port}-:2222"
        firmware = ["-fw_cfg", "name=opt/qikvrt/ssh-key,string=" + public_key]
    elif ssh_identity is not None or ssh_reject_identity is not None:
        raise ValueError("SSH identity requires --ssh-public-key")
    if platform.machine() not in ("x86_64", "AMD64"):
        raise ValueError("client CPU must match the amd64 host image")
    for entry in manifest["files"].values():
        path = directory / entry["name"]
        if path.is_symlink() or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError("artifact changed after verification")
    qemu = shutil.which("qemu-system-x86_64")
    if not qemu:
        raise ValueError("qemu-system-x86_64 is required to execute the image")
    handler = lambda *args, **kwargs: ImageHTTPHandler(*args, directory=str(directory), **kwargs)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    logfile = directory / "qikvrt-netboot-serial.log"
    command = [qemu, "-accel", qemu_acceleration(), "-m", str(guest_memory_mib(manifest)), "-smp", "2", "-display", "none" if verify_only or not os.environ.get("DISPLAY") else "gtk", "-serial", "stdio",
               "-qmp", "unix:" + str(directory / "qikvrt-qmp.sock") + ",server=on,wait=off",
               "-netdev", netdev, "-device", "e1000,netdev=network",
               "-kernel", str(directory / FILES["kernel"]), "-initrd", str(directory / FILES["initrd"]),
               "-append", f"boot=live components username=qikvrt hostname=qikvrt-megast ip=dhcp fetch=http://10.0.2.2:{port}/{FILES['rootfs']} console=tty0 console=ttyS0,115200n8",
               "-no-reboot"] + firmware
    try:
        with logfile.open("wb") as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + timeout
                while process.poll() is None and time.monotonic() < deadline:
                    observed = logfile.read_text(errors="replace")
                    if runtime_result(observed, manifest["source_sha"]) is not None:
                        break
                    time.sleep(1)
                if runtime_result(logfile.read_text(errors="replace"), manifest["source_sha"]) != "success":
                    try:
                        capture_display(directory, directory / "qikvrt-netboot-failure.ppm")
                    except (OSError, ValueError):
                        pass
                    witness = snapshot_serial(logfile)
                    serial = witness.read_text(errors="replace")
                    (directory / "qikvrt-netboot-failure.json").write_text(json.dumps({
                        "source_sha": manifest["source_sha"], "guest_memory_mib": guest_memory_mib(manifest),
                        "guest_runtime_reobserved": False, "serial_evidence_file": witness.name, "serial_sha256": sha256(witness),
                        "effect_ack_done": False, "reason": "GUEST_RUNTIME_BLOCKED" if runtime_result(serial, manifest["source_sha"]) == "failure" else "NO_EXACT_RUNTIME_WITNESS"}, indent=2) + "\n")
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
                ssh_receipt = None
                if ssh_public_key is not None:
                    ssh_receipt = ssh_readback(directory, manifest, logfile.read_text(errors="replace"),
                                               ssh_port, ssh_identity, ssh_reject_identity)
                witness = snapshot_serial(logfile)
                if runtime_result(witness.read_text(errors="replace"), manifest["source_sha"]) != "success":
                    raise ValueError("runtime evidence changed before receipt binding")
                receipt = {"schema": "qikvrt_netboot_receipt_v1", "source_sha": manifest["source_sha"],
                           "manifest_sha256": sha256(directory / "qikvrt-netboot.json"),
                           "serial_evidence_file": witness.name, "serial_sha256": sha256(witness),
                           "screenshot_sha256": sha256(screenshot), "observed_colors": len(colors),
                           "boot_method": "linux-live-http", "guest_memory_mib": guest_memory_mib(manifest), "cdrom_attached": False, "guest_runtime_reobserved": True,
                           "physical_atari_boot": False, "effect_ack_done": False}
                if ssh_receipt is not None:
                    receipt["ssh_receipt_sha256"] = sha256(directory / "qikvrt-netboot-ssh-receipt.json")
                    receipt["ssh_authenticated_readback"] = ssh_receipt["authenticated_readback"]
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
    make = sub.add_parser("manifest"); make.add_argument("directory", type=Path); make.add_argument("source_sha"); make.add_argument("--source-tree")
    client = sub.add_parser("receive"); client.add_argument("url"); client.add_argument("sha256"); client.add_argument("directory", type=Path); client.add_argument("--boot", action="store_true"); client.add_argument("--verify-only", action="store_true")
    execute = sub.add_parser("boot"); execute.add_argument("directory", type=Path); execute.add_argument("--verify-only", action="store_true")
    for command in (client, execute):
        command.add_argument("--ssh-public-key", type=Path)
        command.add_argument("--ssh-identity", type=Path)
        command.add_argument("--ssh-reject-identity", type=Path)
        command.add_argument("--ssh-port", type=int, default=2222)
    guest = sub.add_parser("ssh-guest"); guest.add_argument("--authorized-key", type=Path, default=SSH_KEY_PATH)
    serve = sub.add_parser("serve"); serve.add_argument("directory", type=Path); serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=7331)
    args = parser.parse_args()
    try:
        if args.command == "ssh-guest":
            ssh_guest(args.authorized_key)
            return 0
        directory = args.directory.resolve()
        ssh_options = {key: getattr(args, key) for key in ("ssh_public_key", "ssh_identity", "ssh_reject_identity", "ssh_port")} if args.command in ("receive", "boot") else {}
        if args.command == "manifest":
            make_manifest(directory, args.source_sha, args.source_tree)
        elif args.command == "receive":
            manifest = receive(args.url, args.sha256, directory)
            if args.boot:
                boot(directory, manifest, verify_only=args.verify_only, **ssh_options)
        elif args.command == "boot":
            boot(directory, json.loads((directory / "qikvrt-netboot.json").read_text()), verify_only=args.verify_only, **ssh_options)
        else:
            with BootDatagramServer((args.host, args.port), (directory / "QIKVRT_BOOT.BIN").read_bytes()) as server:
                server.serve_forever()
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("BLOCK: " + str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
