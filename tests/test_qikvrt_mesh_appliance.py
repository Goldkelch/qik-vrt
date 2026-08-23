# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "distribution/qikvrt-mesh-appliance"
WORKFLOW = ROOT / ".github/workflows/qikvrt_mesh_appliance_release.yml"
POLICY = ROOT / "policy/QIKVRT_MESH_APPLIANCE_V1.json"
LOCK = DIST / "release-lock.json"


class MeshApplianceReleaseTests(unittest.TestCase):
    def test_single_canonical_distribution_surface(self) -> None:
        required = (
            DIST / "Containerfile",
            DIST / "build_extension.py",
            DIST / "effect_ack_gateway.py",
            DIST / "entrypoint.sh",
            DIST / "generate_release_manifest.py",
            DIST / "launch_firefox.py",
            DIST / "firefox/effect_ack_protocol.js",
            DIST / "firefox/selftest.html",
            DIST / "firefox/selftest.js",
            DIST / "systemd/qikvrt-mesh-appliance.service",
            DIST / "vm/build_vm_assets.sh",
            WORKFLOW,
            POLICY,
            LOCK,
        )
        for path in required:
            self.assertTrue(path.is_file(), path)
        self.assertFalse((ROOT / "appliance/qikvrt-mesh-v1").exists())
        self.assertFalse((ROOT / ".github/workflows/qikvrt_mesh_appliance_release_v1.yml").exists())
        self.assertFalse((ROOT / "policy/QIKVRT_MESH_APPLIANCE_RELEASE_V1.json").exists())

    def test_policy_and_release_lock_are_truth_bounded(self) -> None:
        policy = json.loads(POLICY.read_text())
        lock = json.loads(LOCK.read_text())
        self.assertEqual(policy["release_candidate"], "0.1.0-rc1")
        self.assertEqual(lock["appliance_version"], "0.1.0-rc1")
        self.assertEqual(policy["distribution"]["oci_platforms"], ["linux/amd64", "linux/arm64"])
        self.assertEqual(policy["effect_ack"]["external_effect"], "NONE")
        self.assertFalse(policy["effect_ack"]["ietf_standard_claimed"])
        self.assertFalse(policy["firefox"]["firefox_fork_claimed"])
        for key in ("physical_megast_execution", "general_internet_reachability", "general_effect_ack_done", "pass", "final_pass"):
            self.assertFalse(policy["claims"][key])
            self.assertFalse(lock["claims"][key])

    def test_container_binds_firefox_protocol_and_nonroot_runtime(self) -> None:
        text = (DIST / "Containerfile").read_text()
        for needle in (
            "ubuntu:24.04@sha256:",
            "FIREFOX_VERSION=153.1.0esr",
            "GECKODRIVER_VERSION=0.37.1",
            "gpg --batch --verify /tmp/SHA256SUMS.asc /tmp/SHA256SUMS",
            "libqikvrt-effect-ack.a",
            "USER qikvrt",
            "HEALTHCHECK",
            "qikvrt-terminal.xpi",
        ):
            self.assertIn(needle, text)

    def test_firefox_selftest_is_full_prepare_commit_reobserve_cycle(self) -> None:
        text = (DIST / "firefox/selftest.js").read_text()
        for needle in (
            "DISCOVER_EFFECT_ACK",
            "PREPARE_EFFECT",
            "COMMIT_EFFECT",
            "OBSERVE_EFFECT_STATE",
            "post_effect_reobservation_observed",
            "bounded_loopback_terminal_input_acknowledged",
            'external_effect: "NONE"',
        ):
            self.assertIn(needle, text)
        launcher = (DIST / "launch_firefox.py").read_text()
        self.assertIn("--allow-system-access", launcher)
        self.assertIn("QIKVRT_FIREFOX_PREPARE_COMMIT_REOBSERVATION_DONE", launcher)

    def test_deterministic_xpi_contains_protocol_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.xpi"
            second = Path(directory) / "b.xpi"
            for output in (first, second):
                subprocess.run(
                    [sys.executable, str(DIST / "build_extension.py"), "--output", str(output)],
                    cwd=ROOT,
                    check=True,
                )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                self.assertTrue({"manifest.json", "background.js", "effect_ack_protocol.js", "selftest.html", "selftest.js"} <= names)
                background = archive.read("background.js").decode()
                self.assertIn("OBSERVE_EFFECT_STATE", background)
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["browser_specific_settings"]["gecko"]["id"], "qikvrt-ai-terminal@goldkelch.local")

    def test_c90_protocol_core_remains_strictly_compilable(self) -> None:
        subprocess.run(
            [
                "cc", "-std=c90", "-pedantic", "-Wall", "-Wextra", "-Werror",
                "-Iinclude", "-fsyntax-only", "src/effect_ack_core.c",
            ],
            cwd=ROOT,
            check=True,
        )

    def test_vm_builder_emits_cross_hypervisor_formats_and_boot_service(self) -> None:
        vm = (DIST / "vm/build_vm_assets.sh").read_text()
        for needle in (
            "ubuntu-cloudimage-keyring.gpg",
            "qikvrt-mesh-appliance.service",
            ".qcow2.xz",
            ".vmdk.xz",
            ".vhdx.xz",
            ".ova",
            "sha256sum",
        ):
            self.assertIn(needle, vm)
        service = (DIST / "systemd/qikvrt-mesh-appliance.service").read_text()
        self.assertIn("podman load", service)
        self.assertIn("--network=host", service)
        self.assertIn("StandardOutput=journal+console", service)

    def test_release_workflow_builds_and_reobserves_public_effects(self) -> None:
        text = WORKFLOW.read_text()
        for needle in (
            "distribution/qikvrt-mesh-appliance/Containerfile",
            "Execute real Firefox prepare commit and post-effect reobservation",
            "Build QCOW2 VMDK VHDX and OVA appliance assets",
            "Publish immutable multi-architecture GHCR manifest",
            "Publish immutable GitHub prerelease assets",
            "Reobserve public assets and OCI digest",
            "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        ):
            self.assertIn(needle, text)
        self.assertNotIn("appliance/qikvrt-mesh-v1", text)

    def test_release_manifest_is_canonical_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "QIKVRT-Mesh-Appliance-v0.1.0-rc1-amd64.qcow2.xz"
            asset.write_bytes(b"bounded-appliance")
            output = root / "QIKVRT-Mesh-Appliance-v0.1.0-rc1-release.json"
            subprocess.run(
                [
                    sys.executable,
                    str(DIST / "generate_release_manifest.py"),
                    "--assets", str(root),
                    "--version", "0.1.0-rc1",
                    "--tag", "qikvrt-mesh-appliance-v0.1.0-rc1",
                    "--source-head", "a" * 40,
                    "--source-tree", "b" * 40,
                    "--container-reference", "ghcr.io/goldkelch/qik-vrt-mesh-appliance:v0.1.0-rc1",
                    "--container-digest", "sha256:" + "c" * 64,
                    "--output", str(output),
                ],
                cwd=ROOT,
                check=True,
            )
            document = json.loads(output.read_text())
            self.assertEqual(document["assets"][0]["sha256"], hashlib.sha256(asset.read_bytes()).hexdigest())
            self.assertEqual(document["oci"]["digest"], "sha256:" + "c" * 64)
            self.assertTrue(document["assets"][0]["download_url"].startswith("https://github.com/Goldkelch/qik-vrt/releases/download/"))
            checksum = output.with_suffix(output.suffix + ".sha256")
            self.assertTrue(checksum.is_file())


if __name__ == "__main__":
    unittest.main()
