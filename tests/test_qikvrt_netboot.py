# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qikvrt_netboot", ROOT / "distribution/qikvrt-megast/boot.py")
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)


class NetbootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.receiver = Path(cls.temp.name) / "receive"
        subprocess.run(["cc", "-std=c90", "-pedantic", "-Wall", "-Wextra", "-Werror", "-O2",
                        "-Isrc/cloud_transputer", "src/cloud_transputer/qikvrt_boot_receive.c",
                        "src/cloud_transputer/qikvrt_wire_v1.c", "src/cloud_transputer/qikvrt_sha256_v1.c",
                        "-o", str(cls.receiver)], cwd=ROOT, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def roundtrip(self, payload, digest=None, existing=False):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "QIKVRT_BOOT.BIN"
            if existing:
                output.write_bytes(b"preserve")
            server = boot.BootDatagramServer(("127.0.0.1", 0), payload)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                result = subprocess.run([str(self.receiver), "127.0.0.1", str(server.server_address[1]), str(output),
                                         digest or hashlib.sha256(payload).hexdigest(), "4711"], capture_output=True, timeout=15)
            finally:
                server.shutdown(); server.server_close(); thread.join()
            return result, output.read_bytes() if output.exists() else None, server.completed

    def test_c90_receiver_applies_and_reobserves_all_chunk_boundaries(self):
        for size in (1, 127, 128, 129, 4097):
            with self.subTest(size=size):
                payload = bytes(i % 256 for i in range(size))
                result, actual, ledger = self.roundtrip(payload)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(actual, payload)
                self.assertIn(b"QIKVRT_BOOT_CONTENT_VERIFIED", result.stdout)
                self.assertEqual(len(ledger), 1)
                self.assertFalse(ledger[0]["booted"])

    def test_untrusted_image_digest_never_creates_output(self):
        result, output, _ = self.roundtrip(b"image", digest="0" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(output)

    def test_existing_file_is_never_overwritten(self):
        result, output, _ = self.roundtrip(b"image", existing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output, b"preserve")

    def test_incorrect_nonce_and_corrupt_packets_have_no_effect(self):
        with boot.BootDatagramServer(("127.0.0.1", 0), b"image") as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as peer:
                    peer.settimeout(.1)
                    peer.sendto(boot.frame(1, 0, 0, 0), server.server_address)
                    with self.assertRaises(TimeoutError): peer.recv(160)
                    packet = bytearray(boot.frame(1, 4711, 0, 0)); packet[-1] ^= 1
                    peer.sendto(packet, server.server_address)
                    with self.assertRaises(TimeoutError): peer.recv(160)
            finally:
                server.shutdown(); thread.join()
            self.assertEqual(server.completed, [])

    def test_manifest_rejects_foreign_architecture_and_path_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in boot.FILES.values(): (root / name).write_bytes(b"image")
            manifest = boot.make_manifest(root, "a" * 40)
            manifest["architecture"] = "MC68000"
            with self.assertRaises(ValueError): boot.validate_manifest(manifest)
            manifest["architecture"] = "x86_64"
            manifest["files"]["kernel"]["name"] = "../kernel"
            with self.assertRaises(ValueError): boot.validate_manifest(manifest)

    def test_download_hash_mismatch_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "payload").write_bytes(b"corrupt")
            handler = lambda *a, **kw: boot.http.server.SimpleHTTPRequestHandler(*a, directory=str(root), **kw)
            with boot.http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
                try:
                    with self.assertRaises(ValueError):
                        boot.download(f"http://127.0.0.1:{server.server_address[1]}/payload", root / "received", "0" * 64, 7)
                finally:
                    server.shutdown(); thread.join()
            self.assertFalse((root / "received").exists())
            self.assertFalse((root / "received.partial").exists())

    def test_network_boot_allows_bounded_graphical_runtime_and_reports_serial_tail(self):
        source = (ROOT / "distribution/qikvrt-megast/boot.py").read_text()
        self.assertIn("timeout: int = 900", source)
        self.assertIn("serial_tail:", source)

    def test_large_rootfs_fits_half_ram_with_runtime_headroom(self):
        for size in (1, 1488416768, 2 * 1024**3):
            memory = boot.guest_memory_mib({"files": {"rootfs": {"bytes": size}}}) * 1024**2
            self.assertGreaterEqual(memory, 2 * size + 1024**3)

    def test_hardware_acceleration_is_preferred_with_multithreaded_fallback(self):
        with patch.object(boot.os, "access", return_value=True):
            self.assertEqual(boot.qemu_acceleration(), "kvm")
        with patch.object(boot.os, "access", return_value=False):
            self.assertEqual(boot.qemu_acceleration(), "tcg,thread=multi")
        workflow = (ROOT / ".github/workflows/qikvrt_megast_distribution_v1.yml").read_text()
        self.assertIn('sudo chown "$(id -u):$(id -g)" /dev/kvm', workflow)

    def test_guest_terminal_markers_bypass_the_optional_journal_relay(self):
        witness = (ROOT / "distribution/qikvrt-megast/runtime-witness.py").read_text()
        self.assertIn('with open("/dev/ttyS0", "w") as serial:', witness)
        self.assertIn("emit_serial(marker)", witness)
        self.assertLess(witness.index("emit_serial(marker)"), witness.index('subprocess.run(["logger", "-t", "qikvrt-runtime", marker]'))

    def test_early_boot_marker_never_substitutes_for_runtime_and_failure_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in boot.FILES.values(): (root / name).write_bytes(b"image")
            manifest = boot.make_manifest(root, "a" * 40)
            fake = root / "qemu-stub"
            fake.write_text("#!/bin/sh\necho QIKVRT_MEGAST_BOOT_OK source_sha=" + "a" * 40 + "\n")
            fake.chmod(0o700)
            with patch.object(boot.shutil, "which", return_value=str(fake)):
                with self.assertRaisesRegex(ValueError, "no exact-source runtime evidence"):
                    boot.boot(root, manifest, timeout=2, verify_only=True)
            failure = json.loads((root / "qikvrt-netboot-failure.json").read_text())
            self.assertFalse(failure["guest_runtime_reobserved"])
            self.assertFalse(failure["effect_ack_done"])
            self.assertFalse((root / "qikvrt-netboot-receipt.json").exists())
            self.assertIn("QIKVRT_MEGAST_BOOT_OK", (root / "qikvrt-netboot-serial.log").read_text())

    def test_explicit_guest_failure_stops_waiting_without_creating_success_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in boot.FILES.values(): (root / name).write_bytes(b"image")
            manifest = boot.make_manifest(root, "a" * 40)
            fake = root / "qemu-stub"
            fake.write_text("#!/usr/bin/env python3\nimport time\nprint('QIKVRT_RUNTIME_BLOCK graphical session failed', flush=True)\ntime.sleep(30)\n")
            fake.chmod(0o700)
            started = time.monotonic()
            with patch.object(boot.shutil, "which", return_value=str(fake)):
                with self.assertRaisesRegex(ValueError, "graphical session failed"):
                    boot.boot(root, manifest, timeout=10, verify_only=True)
            self.assertLess(time.monotonic() - started, 8)
            failure = json.loads((root / "qikvrt-netboot-failure.json").read_text())
            self.assertEqual(failure["reason"], "GUEST_RUNTIME_BLOCKED")
            self.assertFalse(failure["effect_ack_done"])
            self.assertFalse((root / "qikvrt-netboot-receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
