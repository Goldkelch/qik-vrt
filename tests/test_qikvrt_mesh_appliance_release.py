# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLIANCE = ROOT / "appliance/qikvrt-mesh-v1"
WORKFLOW = ROOT / ".github/workflows/qikvrt_mesh_appliance_release_v1.yml"


class MeshApplianceReleaseTests(unittest.TestCase):
    def test_policy_is_truth_bounded(self) -> None:
        policy = json.loads(
            (ROOT / "policy/QIKVRT_MESH_APPLIANCE_RELEASE_V1.json").read_text()
        )
        self.assertEqual(
            policy["browser"]["implementation"],
            "UPSTREAM_FIREFOX_ESR_PLUS_QIKVRT_WEBEXTENSION",
        )
        self.assertFalse(policy["browser"]["firefox_fork_claimed"])
        self.assertEqual(
            policy["effect_ack"]["scope"],
            "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
        )
        self.assertFalse(policy["artifacts"]["latest_alias_is_evidence"])
        self.assertTrue(all(value is False for value in policy["claims"].values()))

    def test_container_has_firefox_and_loopback_service(self) -> None:
        text = (APPLIANCE / "Containerfile").read_text()
        self.assertIn("firefox-esr", text)
        self.assertIn("snapshot.debian.org", text)
        self.assertIn("qikvrt-terminal.xpi", text)
        self.assertIn("BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY", text)
        self.assertNotIn("curl http", text)

    def test_entrypoint_orders_backend_before_firefox(self) -> None:
        text = (APPLIANCE / "entrypoint.sh").read_text()
        serve = text.index("  serve)")
        section = text[serve:]
        self.assertLess(section.index("start_backend"), section.index("start_firefox"))
        self.assertIn("firefox_probe.py", text)
        self.assertIn(
            "127.0.0.1", (APPLIANCE / "protocol_probe.py").read_text()
        )

    def test_extension_build_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "manifest.json").write_text(
                json.dumps(
                    {
                        "manifest_version": 3,
                        "name": "QIKVRT",
                        "version": "1.0",
                        "background": {"scripts": ["background.js"]},
                        "browser_specific_settings": {
                            "gecko": {"id": "qikvrt-ai-terminal@goldkelch.local"}
                        },
                    }
                ),
                encoding="utf-8",
            )
            (source / "background.js").write_text(
                "function prepareEffect(){}\nfunction commitEffect(){}\n",
                encoding="utf-8",
            )
            bootstrap = root / "bootstrap.js"
            bootstrap.write_text("void 0;\n", encoding="utf-8")
            one, two = root / "one.xpi", root / "two.xpi"
            for output in (one, two):
                subprocess.run(
                    [
                        "python3",
                        str(APPLIANCE / "build_extension.py"),
                        "--source",
                        str(source),
                        "--bootstrap",
                        str(bootstrap),
                        "--output",
                        str(output),
                    ],
                    check=True,
                )
            self.assertEqual(
                hashlib.sha256(one.read_bytes()).digest(),
                hashlib.sha256(two.read_bytes()).digest(),
            )

    def test_release_manifest_uses_versioned_urls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            (assets / "image.qcow2").write_bytes(b"test")
            output = assets / "release.json"
            subprocess.run(
                [
                    "python3",
                    str(APPLIANCE / "generate_release_manifest.py"),
                    "--assets",
                    str(assets),
                    "--tag",
                    "qikvrt-mesh-appliance-v1.0.0-test",
                    "--version",
                    "1.0.0",
                    "--source-head",
                    "a" * 40,
                    "--source-tree",
                    "b" * 40,
                    "--authority-base",
                    "c" * 40,
                    "--base-image",
                    "debian@sha256:" + "d" * 64,
                    "--output",
                    str(output),
                ],
                check=True,
            )
            value = json.loads(output.read_text())
            self.assertIn(
                "/releases/download/qikvrt-mesh-appliance-v1.0.0-test/image.qcow2",
                value["assets"][0]["immutable_url"],
            )
            self.assertFalse(value["mutable_convenience_aliases_are_evidence"])

    def test_workflow_has_build_and_explicit_publish_boundary(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("pull_request:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("qikvrt-mesh-appliance-v*", text)
        self.assertIn("gh release create", text)
        self.assertIn("ghcr.io/goldkelch/qik-vrt-mesh-appliance", text)
        self.assertIn(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            text,
        )
        self.assertIn(
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            text,
        )
        self.assertIn("publish == 'true'", text)

    def test_scripts_are_syntactically_valid(self) -> None:
        scripts = [
            "build_extension.py",
            "protocol_probe.py",
            "firefox_probe.py",
            "generate_release_manifest.py",
        ]
        subprocess.run(
            ["python3", "-m", "py_compile", *[str(APPLIANCE / name) for name in scripts]],
            check=True,
        )
        subprocess.run(["bash", "-n", str(APPLIANCE / "build_vm.sh")], check=True)
        subprocess.run(["sh", "-n", str(APPLIANCE / "entrypoint.sh")], check=True)


if __name__ == "__main__":
    unittest.main()
