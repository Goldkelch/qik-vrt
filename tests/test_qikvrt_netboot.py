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
import urllib.error
import urllib.request
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

    def test_terminal_protocol_rejects_quoted_and_foreign_head_markers(self):
        marker = "QIKVRT_MEGAST_RUNTIME_OK source_sha=" + "a" * 40
        quoted = "QIKVRT_GRAPHICS_DIAGNOSTICS " + json.dumps({"runtime-witness.log": marker + "\n"})
        self.assertIsNone(boot.runtime_result(quoted, "a" * 40))
        self.assertIsNone(boot.runtime_result(marker, "a" * 40))
        self.assertIsNone(boot.runtime_result(marker + "x\n", "a" * 40))
        self.assertIsNone(boot.runtime_result(marker + "\n", "b" * 40))
        self.assertEqual(boot.runtime_result(marker + "\r\n", "a" * 40), "success")
        self.assertEqual(boot.runtime_result(marker + "\nQIKVRT_RUNTIME_BLOCK return failed\n", "a" * 40), "failure")

    def test_early_boot_marker_never_substitutes_for_runtime_and_failure_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in boot.FILES.values(): (root / name).write_bytes(b"image")
            manifest = boot.make_manifest(root, "a" * 40)
            fake = root / "qemu-stub"
            fake.write_text("#!/bin/sh\necho QIKVRT_MEGAST_BOOT_OK source_sha=" + "a" * 40 + "\n")
            fake.chmod(0o700)
            (root / "qikvrt-netboot-receipt.json").write_text('{"stale_previous_attempt": true}')
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

    def test_receipt_serial_hash_survives_qemu_shutdown_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in boot.FILES.values(): (root / name).write_bytes(b"image")
            manifest = boot.make_manifest(root, "a" * 40)
            fake = root / "qemu-stub"
            fake.write_text("#!/usr/bin/env python3\nimport signal,sys,time\n"
                            "def stop(*args):\n print('QEMU shutdown output', flush=True)\n sys.exit(0)\n"
                            "signal.signal(signal.SIGTERM, stop)\n"
                            "print('QIKVRT_MEGAST_RUNTIME_OK source_sha=" + "a" * 40 + "', flush=True)\n"
                            "while True: time.sleep(1)\n")
            fake.chmod(0o700)
            def display(directory, screenshot):
                screenshot.write_bytes(b"P6\n16 1\n255\n" + b"".join(bytes([i, i, i]) for i in range(16)))
            with patch.object(boot.shutil, "which", return_value=str(fake)), patch.object(boot, "capture_display", side_effect=display):
                receipt = boot.boot(root, manifest, timeout=5, verify_only=True)
            persisted = json.loads((root / "qikvrt-netboot-receipt.json").read_text())
            self.assertEqual(persisted, receipt)
            self.assertEqual(receipt["serial_sha256"], boot.sha256(root / receipt["serial_evidence_file"]))
            self.assertNotEqual(receipt["serial_sha256"], boot.sha256(root / "qikvrt-netboot-serial.log"))
            self.assertIn("QEMU shutdown output", (root / "qikvrt-netboot-serial.log").read_text())
            self.assertFalse(receipt["effect_ack_done"])


class SSHBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.identity = Path(cls.temp.name) / "identity"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(cls.identity)], check=True)
        cls.public_key = boot.ed25519_public_key(cls.identity.with_suffix(".pub").read_text())
        cls.manifest = {"source_sha": "a" * 40, "source_tree": "b" * 40}
        cls.record = {**cls.manifest, "host_key": cls.public_key, "user": "qikvrt", "port": 2222}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def serial(self, record=None):
        return "QIKVRT_SSH_HOST " + json.dumps(record or self.record) + "\n"

    def test_only_a_single_plain_key_can_activate_ssh(self):
        self.assertEqual(boot.ed25519_public_key(self.public_key + " owner,comment"), self.public_key)
        for value in ("command=evil " + self.public_key, self.public_key + "\n" + self.public_key,
                      "ssh-ed25519 AAAA", "ssh-ed25519 %%%", "ssh-rsa AAAA"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                boot.ed25519_public_key(value)

    def test_missing_or_invalid_owner_key_never_launches_sshd(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(boot.os, "execv") as launch:
            key = Path(tmp) / "key"
            boot.ssh_guest(key)
            key.write_text("command=evil " + self.public_key)
            with self.assertRaises(ValueError):
                boot.ssh_guest(key)
            launch.assert_not_called()

    def test_host_trust_requires_complete_unquoted_exact_subject_witness(self):
        self.assertEqual(boot.ssh_host_record(self.serial(), self.manifest), self.record)
        for serial in (self.serial().rstrip(), "diagnostic " + self.serial(),
                       self.serial({**self.record, "source_tree": "c" * 40}),
                       self.serial({**self.record, "user": "root"})):
            with self.subTest(serial=serial), self.assertRaises(ValueError):
                boot.ssh_host_record(serial, self.manifest)

    def test_successful_ssh_with_foreign_subject_never_creates_receipt(self):
        for change in ({"source_sha": "c" * 40}, {"source_tree": "c" * 40}):
            payload = {"schema": "qikvrt_megast_distribution_v1", **self.manifest, **change}
            result = subprocess.CompletedProcess([], 0, "qikvrt\n" + json.dumps(payload), "")
            with tempfile.TemporaryDirectory() as tmp, patch.object(boot.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(ValueError, "exact guest subject"):
                    boot.ssh_readback(Path(tmp), self.manifest, self.serial(), 2222, self.identity)
                self.assertFalse((Path(tmp) / "qikvrt-netboot-ssh-receipt.json").exists())

    def test_wrong_identity_success_or_transport_failure_cannot_count_as_rejection(self):
        payload = {"schema": "qikvrt_megast_distribution_v1", **self.manifest}
        good = subprocess.CompletedProcess([], 0, "qikvrt\n" + json.dumps(payload), "")
        for denied in (good, subprocess.CompletedProcess([], 255, "", "Connection refused")):
            with tempfile.TemporaryDirectory() as tmp, patch.object(boot.subprocess, "run", side_effect=[good, denied]):
                with self.assertRaisesRegex(ValueError, "explicitly rejected"):
                    boot.ssh_readback(Path(tmp), self.manifest, self.serial(), 2222, self.identity, self.identity)
                self.assertFalse((Path(tmp) / "qikvrt-netboot-ssh-receipt.json").exists())

    def test_verified_ssh_still_does_not_claim_chatgpt_pairing(self):
        payload = {"schema": "qikvrt_megast_distribution_v1", **self.manifest}
        good = subprocess.CompletedProcess([], 0, "qikvrt\n" + json.dumps(payload), "")
        denied = subprocess.CompletedProcess([], 255, "", "Permission denied (publickey).")
        with tempfile.TemporaryDirectory() as tmp, patch.object(boot.subprocess, "run", side_effect=[good, denied]) as run:
            receipt = boot.ssh_readback(Path(tmp), self.manifest, self.serial(), 2222, self.identity, self.identity)
            self.assertTrue(receipt["authenticated_readback"])
            self.assertTrue(receipt["unauthorized_key_rejected"])
            self.assertEqual(receipt["chatgpt_pairing"], "NOT_ESTABLISHED")
            self.assertFalse(receipt["effect_ack_done"])
            self.assertIn("StrictHostKeyChecking=yes", run.call_args_list[0].args[0])
            self.assertIn("IdentityAgent=none", run.call_args_list[0].args[0])

    def test_private_keys_are_rejected_in_the_served_image_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in boot.FILES.values(): (directory / name).write_bytes(b"image")
            manifest = boot.make_manifest(directory, "a" * 40, "b" * 40)
            private = directory / "secret"
            private.write_bytes(self.identity.read_bytes())
            with self.assertRaisesRegex(ValueError, "outside the HTTP-served"):
                boot.boot(directory, manifest, ssh_public_key=self.identity.with_suffix(".pub"), ssh_identity=private)

    def test_image_http_server_never_serves_keys_logs_or_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / boot.FILES["kernel"]).write_bytes(b"kernel")
            (directory / "secret").write_text("private")
            handler = lambda *a, **kw: boot.ImageHTTPHandler(*a, directory=tmp, **kw)
            with boot.http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
                url = f"http://127.0.0.1:{server.server_address[1]}"
                try:
                    with urllib.request.urlopen(url + "/" + boot.FILES["kernel"]) as response:
                        self.assertEqual(response.read(), b"kernel")
                    for path in ("/secret", "/", "/%2e%2e/secret", "/" + boot.FILES["kernel"] + "/../secret"):
                        with self.assertRaises(urllib.error.HTTPError) as raised:
                            urllib.request.urlopen(url + path)
                        self.assertEqual(raised.exception.code, 404)
                finally:
                    server.shutdown(); thread.join()


if __name__ == "__main__":
    unittest.main()
