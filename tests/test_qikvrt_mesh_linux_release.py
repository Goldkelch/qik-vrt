import json
import pathlib
import runpy
import sys
import tempfile
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
        self.assertTrue(policy["build_acceptance"]["pr_native_build_required"])
        guards = policy["publication_guards"]
        self.assertTrue(guards["single_parent_zero_diff_carrier_required"])
        self.assertTrue(guards["branch_head_compare_and_swap_required"])
        self.assertTrue(guards["immutable_github_releases_setting_required"])
        self.assertTrue(guards["anonymous_ghcr_readback_required"])
        self.assertTrue(guards["fail_closed_namespace_probes_required"])
        self.assertTrue(guards["public_ghcr_namespace_precondition_required"])
        self.assertTrue(
            guards["anonymous_ghcr_readback_before_github_release_required"]
        )
        self.assertEqual(guards["final_release_asset_count"], 18)
        self.assertEqual(guards["repository_locked_gh_cli_version"], "2.96.0")
        self.assertEqual(guards["release_asset_max_bytes_exclusive"], 2 * 1024**3)
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
            "needs.prepare.outputs.build_ready == 'true'",
            "github.event.pull_request.head.sha || github.sha",
            "validate-build-assets dist",
            "validate-release-assets dist",
            "validate-release-readback",
            "single-parent zero-diff carrier",
            "git ls-remote --exit-code",
            "immutable-releases",
            "QIKVRT_IMMUTABLE_ADMIN_READ_TOKEN",
            "QIKVRT_RELEASE_WRITE_WORKFLOWS_TOKEN",
            "QIKVRT_GHCR_PUBLIC_PROBE_DIGEST",
            "bootstrap-gh.sh --install --accept-third-party",
            "--json isImmutable",
            "release verify-asset",
            "published-index.json",
        ]:
            self.assertIn(text, raw)
        self.assertNotIn(":latest", raw)
        self.assertNotIn("--clobber", raw)

    def test_generated_launcher_and_release_asset_contract(self):
        base_namespace = runpy.run_path(
            str(TOOL), run_name="qikvrt_mesh_linux_release_contract"
        )
        compile(
            base_namespace["LAUNCH_FIREFOX"],
            "qikvrt-launch-firefox",
            "exec",
        )
        base_raw = TOOL.read_text()
        self.assertIn("LAUNCH_FIREFOX=r'''", base_raw)
        self.assertIn("qcow.unlink()", base_raw)
        self.assertIn('if arch=="amd64":shutil.copy2', base_raw)

        tools_path = str(TOOL.parent)
        sys.path.insert(0, tools_path)
        try:
            v2_namespace = runpy.run_path(
                str(TOOL2), run_name="qikvrt_mesh_linux_release_v2_contract"
            )
        finally:
            sys.path.remove(tools_path)

        expected = v2_namespace["expected_release_asset_names"]()
        self.assertEqual(len(expected), 16)
        self.assertNotIn("qikvrt-mesh-linux-1.0.0-amd64.qcow2", expected)
        self.assertNotIn("qikvrt-mesh-linux-1.0.0-arm64.qcow2", expected)
        self.assertEqual(
            [name for name in expected if name == "qikvrt-terminal-1.0.0.xpi"],
            ["qikvrt-terminal-1.0.0.xpi"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = pathlib.Path(temporary)
            assets = temporary_root / "assets"
            assets.mkdir()
            for name in expected:
                (assets / name).write_bytes(b"x")
            v2_namespace["validate_release_assets"](assets)
            first = assets / sorted(expected)[0]
            first.write_bytes(b"")
            with self.assertRaises(RuntimeError):
                v2_namespace["validate_release_assets"](assets)
            first.write_bytes(b"x")
            unexpected = assets / "unexpected"
            unexpected.write_bytes(b"x")
            with self.assertRaises(RuntimeError):
                v2_namespace["validate_release_assets"](assets)
            unexpected.unlink()
            unexpected.mkdir()
            with self.assertRaises(RuntimeError):
                v2_namespace["validate_release_assets"](assets)
            unexpected.rmdir()

            manifest_name = v2_namespace["RELEASE_MANIFEST_NAME"]
            sums_name = v2_namespace["RELEASE_SUMS_NAME"]
            (assets / manifest_name).write_bytes(b"x")
            checksum_targets = sorted(
                path for path in assets.iterdir() if path.name != sums_name
            )
            (assets / sums_name).write_text(
                "".join(
                    f"{base_namespace['sha256'](path)}  {path.name}\n"
                    for path in checksum_targets
                )
            )
            v2_namespace["validate_release_assets"](assets, final=True)
            bad_readback = temporary_root / "bad-release-readback.json"
            bad_readback.write_text(json.dumps({"assets": []}))
            with self.assertRaises(RuntimeError):
                v2_namespace["validate_release_readback"](assets, bad_readback)
            readback = temporary_root / "release-readback.json"
            readback.write_text(
                json.dumps(
                    {
                        "assets": [
                            {"name": path.name, "size": path.stat().st_size}
                            for path in assets.iterdir()
                        ]
                    }
                )
            )
            v2_namespace["validate_release_readback"](assets, readback)

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
