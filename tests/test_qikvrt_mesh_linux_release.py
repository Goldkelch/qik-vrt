import json
import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/qikvrt_mesh_linux_release.yml"
TOOL = ROOT / "tools/qikvrt_mesh_linux_release.py"
TOOL2 = ROOT / "tools/qikvrt_mesh_linux_release_v2.py"
POLICY = ROOT / "policy/QIKVRT_MESH_LINUX_RELEASE_V1.json"
AUTH = ROOT / "release/QIKVRT_MESH_LINUX_1_0_0_AUTHORIZATION.json"
DOC = ROOT / "docs/QIKVRT_MESH_LINUX_RELEASE_V1.md"


class T(unittest.TestCase):
    def test_files(self):
        for path in [WF, TOOL, TOOL2, POLICY, AUTH, DOC]:
            self.assertTrue(path.is_file(), path)

    def test_policy_and_authorization(self):
        policy = json.loads(POLICY.read_text())
        authorization = json.loads(AUTH.read_text())
        self.assertEqual(policy["version"], "1.0.0")
        self.assertTrue(authorization["authorized"])
        self.assertEqual(
            authorization["authorization_text"], "Dann liefere jetzt alles aus."
        )
        self.assertFalse(policy["boundaries"]["physical_megast_execution_claimed"])
        self.assertFalse(policy["boundaries"]["general_effect_ack_done_claimed"])
        self.assertTrue(
            policy["build_acceptance"]["container_runtime_receipt_required"]
        )
        self.assertEqual(
            policy["build_acceptance"]["effect_ack_scope"],
            "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
        )
        official = {
            "amd64_rootfs_sha256": "915b4be62933475c3fb5f5031aa2e159294db95fb32aaa9e8b317aadcb6c065d",
            "amd64_cloudimg_sha256": "0533b0655c32e68b31d792ecd6ccfca95abdbc536c4446874fe0513bd4140ffe",
            "arm64_rootfs_sha256": "379cc9a78497fe96449d2d498e455d40e3e0abd8baa22781b2d67aca06c5e2c8",
            "arm64_cloudimg_sha256": "aa6da05756e85ea6dde4836b841fecb10cfd1ba3bcea320189d9af945db70476",
        }
        for key, value in official.items():
            self.assertEqual(policy["base_distribution"][key], value)

    def test_workflow(self):
        raw = WF.read_text()
        yaml.safe_load(raw)
        for text in [
            "ubuntu-24.04-arm",
            "qikvrt-mesh-linux-v1.0.0",
            "ghcr.io/goldkelch/qik-vrt-mesh-linux:1.0.0",
            "packages: write",
            "contents: write",
            "release: reattest QIK-VRT Mesh Linux v1.0.0 exact tree",
            "tools/qikvrt_mesh_linux_release_v2.py build",
            "firefox-effect-ack.json",
        ]:
            self.assertIn(text, raw)
        self.assertNotIn(":latest", raw)
        self.assertNotIn("--clobber", raw)

    def test_exact_sources_and_runtime_acceptance(self):
        raw = TOOL.read_text() + "\n" + TOOL2.read_text()
        for sha in [
            "b7c9fa5f74cb963ba7cfefed2a0d0a071e6515a9",
            "cba166e45a0ea4b5d5dd2ef9cde0ad96ff57554b",
            "9832f6ddf6a3ef53a7c0f9b52d2c9d8f1e7ba970",
            "915b4be62933475c3fb5f5031aa2e159294db95fb32aaa9e8b317aadcb6c065d",
            "0533b0655c32e68b31d792ecd6ccfca95abdbc536c4446874fe0513bd4140ffe",
            "379cc9a78497fe96449d2d498e455d40e3e0abd8baa22781b2d67aca06c5e2c8",
            "aa6da05756e85ea6dde4836b841fecb10cfd1ba3bcea320189d9af945db70476",
        ]:
            self.assertIn(sha, raw)
        for text in [
            "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
            "docker",
            "firefox-effect-ack-receipt.json",
            "TERMINAL_INPUT_ACCEPTED",
        ]:
            self.assertIn(text, raw)


if __name__ == "__main__":
    unittest.main()
