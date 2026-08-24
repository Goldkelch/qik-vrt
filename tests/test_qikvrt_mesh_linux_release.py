import json
import os
import pathlib
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
        self.assertTrue(
            policy["build_acceptance"][
                "nonroot_selftest_bytecode_write_forbidden"
            ]
        )
        self.assertTrue(
            policy["build_acceptance"]["host_libguestfs_tcg_fallback_required"]
        )
        for key in [
            "host_libguestfs_generic_kernel_required",
            "host_libguestfs_fresh_cache_required",
            "host_libguestfs_dhcp_client_required",
            "host_libguestfs_supermin_dhcp_package_and_config_required",
            "host_libguestfs_virtio_net_rom_required",
            "host_libguestfs_network_preflight_required",
            "host_libguestfs_clock_sync_required",
            "host_https_time_anchor_required",
            "host_apt_update_error_mode_any_required",
            "apt_source_date_override_rejection_required",
            "failed_native_build_diagnostic_log_required",
            "real_virt_customize_debug_trace_required",
        ]:
            self.assertTrue(policy["build_acceptance"][key])
        self.assertEqual(
            policy["build_acceptance"]["host_libguestfs_clock_cushion_seconds"],
            300,
        )
        self.assertEqual(
            policy["build_acceptance"][
                "host_libguestfs_clock_observation_window_seconds"
            ],
            30,
        )
        self.assertEqual(
            policy["build_acceptance"]["trusted_host_epoch_max_age_seconds"],
            7200,
        )
        self.assertEqual(
            policy["build_acceptance"]["trusted_host_clock_skew_seconds"],
            30,
        )
        self.assertEqual(
            policy["build_acceptance"]["failed_native_build_log_tail_lines"],
            4000,
        )
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
        self.assertEqual(guards["registry_absence_error_code"], "MANIFEST_UNKNOWN")
        self.assertTrue(guards["fresh_anonymous_token_after_push_required"])
        self.assertTrue(guards["constant_publication_concurrency_required"])
        self.assertEqual(guards["noncarrier_release_branch_disposition"], "HOLD")
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
        self.assertEqual(
            policy["base_distribution"]["release_min_epoch_utc"], 1785542400
        )
        self.assertEqual(
            policy["base_distribution"]["max_supported_build_epoch_utc"],
            4102444800,
        )

    def test_workflow(self):
        raw = WF.read_text()
        workflow = yaml.safe_load(raw)
        policy = json.loads(POLICY.read_text())
        workflow_env = workflow["env"]
        self.assertEqual(
            int(workflow_env["MIN_UBUNTU_RELEASE_EPOCH"]),
            policy["base_distribution"]["release_min_epoch_utc"],
        )
        self.assertEqual(
            int(workflow_env["MAX_SUPPORTED_BUILD_EPOCH"]),
            policy["base_distribution"]["max_supported_build_epoch_utc"],
        )
        self.assertEqual(
            int(workflow_env["TRUSTED_HOST_CLOCK_SKEW_SECONDS"]),
            policy["build_acceptance"]["trusted_host_clock_skew_seconds"],
        )
        self.assertEqual(
            int(workflow_env["TRUSTED_HOST_EPOCH_MAX_AGE_SECONDS"]),
            policy["build_acceptance"]["trusted_host_epoch_max_age_seconds"],
        )
        self.assertEqual(
            int(workflow_env["LIBGUESTFS_CLOCK_CUSHION_SECONDS"]),
            policy["build_acceptance"]["host_libguestfs_clock_cushion_seconds"],
        )
        self.assertEqual(
            int(workflow_env["LIBGUESTFS_CLOCK_OBSERVATION_WINDOW_SECONDS"]),
            policy["build_acceptance"][
                "host_libguestfs_clock_observation_window_seconds"
            ],
        )
        for text in [
            "ubuntu-24.04-arm",
            "qikvrt-mesh-linux-v1.0.0",
            "ghcr.io/goldkelch/qik-vrt-mesh-linux:1.0.0",
            "packages: write",
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
            "MANIFEST_UNKNOWN",
            "fresh anonymous GHCR token acquisition failed after push",
            "qikvrt-mesh-linux-publication-v1.0.0",
            "permissions: {contents: read, packages: write}",
            "HOLD: non-carrier release-branch head built",
            "linux-image-virtual",
            "dhcpcd-base",
            "/etc/dhcpcd.conf",
            "ipxe-qemu",
            "command -v dhcpcd",
            "zzz-qikvrt-dhcp-packages",
            "zzz-qikvrt-dhcp-hostfiles",
            "find /usr/lib -type d -path '*/guestfs/supermin.d'",
            'sort > "$supermin_dirs_file"',
            'mapfile -t supermin_dirs < "$supermin_dirs_file"',
            "printf '%s\\n' 'dhcpcd-base' | sudo tee",
            'sudo chmod 0644 "$dhcp_package_fragment" "$dhcp_hostfiles_fragment"',
            "grep -Fqx 'dhcpcd-base'",
            "grep -Fqx '/etc/dhcpcd.conf'",
            "unprivileged supermin builder cannot read DHCP inputs",
            "unprivileged supermin DHCP inputs readback failed",
            "installed libguestfs exposes no supermin.d package input",
            "Appliance DHCP configuration missing: /etc/dhcpcd.conf",
            "Appliance DHCP client missing: dhcpcd",
            "Appliance IPv4 address missing: eth0",
            "Appliance default route missing",
            "Appliance resolver configuration missing",
            "runner UTC epoch is invalid",
            "runner UTC epoch outside supported build window",
            "trusted runner UTC epoch is invalid",
            "trusted runner UTC epoch outside supported build window",
            "runner UTC epoch escaped trusted post-APT anchor",
            "trusted GitHub API time probe failed",
            "trusted GitHub API Date header is missing or invalid",
            "runner UTC epoch disagrees with trusted GitHub API time",
            "post-APT runner UTC epoch escaped trusted GitHub API time",
            "QIKVRT_TRUSTED_HOST_EPOCH",
            "https://api.github.com/rate_limit?qikvrt_clock=",
            "--proto '=https'",
            "APT::Update::Error-Mode=any",
            "host APT date verification is disabled",
            "host APT source contains a per-source date-verification override",
            "Binary::apt-get::Acquire::Check-Date/b",
            "Binary::apt-get::Acquire::Check-Valid-Until/b",
            "--include='*.list'",
            "--include='*.sources'",
            "Acquire::Check-Date=true",
            "Acquire::Check-Valid-Until=true",
            "MIN_UBUNTU_RELEASE_EPOCH: '1785542400'",
            "MAX_SUPPORTED_BUILD_EPOCH: '4102444800'",
            "TRUSTED_HOST_CLOCK_SKEW_SECONDS: '30'",
            "TRUSTED_HOST_EPOCH_MAX_AGE_SECONDS: '7200'",
            "LIBGUESTFS_CLOCK_CUSHION_SECONDS: '300'",
            "LIBGUESTFS_CLOCK_OBSERVATION_WINDOW_SECONDS: '30'",
            "Appliance UTC clock synchronization failed",
            "Appliance UTC clock outside synchronized window",
            "QIKVRT_LIBGUESTFS_CLOCK_PREFLIGHT=OK",
            "/usr/lib/ipxe/qemu/efi-virtio.rom",
            "Provision and verify native libguestfs host appliance",
            "BLOCK: linux-image-virtual installed no generic supermin appliance kernel",
            "SUPERMIN_KERNEL_VERSION",
            "CONFIG_IPV6_SIT=y",
            "LIBGUESTFS_CACHEDIR",
            'mktemp -d "$RUNNER_TEMP/qikvrt-libguestfs-cache.XXXXXX"',
            "LIBGUESTFS_BACKEND_SETTINGS=force_tcg",
            "LIBGUESTFS_BACKEND=direct libguestfs-test-tool",
            'qemu-img create -f raw "$probe_disk" 32M',
            "LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1",
            'bash -n "$probe_script"',
            'guestfish --network --rw --format=raw -a "$probe_disk"',
            'debug-upload "$probe_script" /tmp/qikvrt-libguestfs-network-probe.sh 384',
            'DNS lookup failed: $mirror',
            'TCP connect failed: $mirror:80',
            'debug sh "/bin/bash /tmp/qikvrt-libguestfs-network-probe.sh $mirror $target_epoch $MIN_UBUNTU_RELEASE_EPOCH $MAX_SUPPORTED_BUILD_EPOCH $LIBGUESTFS_CLOCK_OBSERVATION_WINDOW_SECONDS"',
            "QIKVRT_LIBGUESTFS_NETWORK_PREFLIGHT=OK",
            "bounded diagnostic tail follows",
            'tail -n 4000 "$build_log"',
            "Upload failed native-build diagnostic log",
            "qikvrt-mesh-linux-${{ matrix.arch }}-diagnostics",
        ]:
            self.assertIn(text, raw)
        build_steps = workflow["jobs"]["build"]["steps"]
        host_index = next(
            index
            for index, step in enumerate(build_steps)
            if step.get("name")
            == "Provision and verify native libguestfs host appliance"
        )
        appliance_index = next(
            index
            for index, step in enumerate(build_steps)
            if step.get("name")
            == "Build VM/OCI and execute packaged Firefox Effect-Ack acceptance"
        )
        self.assertLess(host_index, appliance_index)
        self.assertEqual(
            build_steps[host_index]["env"]["GITHUB_API_TOKEN"],
            "${{ github.token }}",
        )
        host_run = build_steps[host_index]["run"]
        for text in [
            "linux-image-virtual",
            "dhcpcd-base",
            "/etc/dhcpcd.conf",
            "ipxe-qemu",
            "command -v dhcpcd",
            "zzz-qikvrt-dhcp-packages",
            "zzz-qikvrt-dhcp-hostfiles",
            "find /usr/lib -type d -path '*/guestfs/supermin.d'",
            'sort > "$supermin_dirs_file"',
            'mapfile -t supermin_dirs < "$supermin_dirs_file"',
            "printf '%s\\n' 'dhcpcd-base' | sudo tee",
            'sudo chmod 0644 "$dhcp_package_fragment" "$dhcp_hostfiles_fragment"',
            "grep -Fqx 'dhcpcd-base'",
            "grep -Fqx '/etc/dhcpcd.conf'",
            "unprivileged supermin builder cannot read DHCP inputs",
            "unprivileged supermin DHCP inputs readback failed",
            "installed libguestfs exposes no supermin.d package input",
            "Appliance DHCP configuration missing: /etc/dhcpcd.conf",
            "Appliance DHCP client missing: dhcpcd",
            "Appliance IPv4 address missing: eth0",
            "Appliance default route missing",
            "Appliance resolver configuration missing",
            "runner UTC epoch is invalid",
            "runner UTC epoch outside supported build window",
            "trusted runner UTC epoch is invalid",
            "trusted runner UTC epoch outside supported build window",
            "runner UTC epoch escaped trusted post-APT anchor",
            "trusted GitHub API time probe failed",
            "trusted GitHub API Date header is missing or invalid",
            "runner UTC epoch disagrees with trusted GitHub API time",
            "post-APT runner UTC epoch escaped trusted GitHub API time",
            "QIKVRT_TRUSTED_HOST_EPOCH",
            "https://api.github.com/rate_limit?qikvrt_clock=",
            "--proto '=https'",
            "APT::Update::Error-Mode=any",
            "host APT date verification is disabled",
            "host APT source contains a per-source date-verification override",
            "Binary::apt-get::Acquire::Check-Date/b",
            "Binary::apt-get::Acquire::Check-Valid-Until/b",
            "Acquire::Check-Date=true",
            "Acquire::Check-Valid-Until=true",
            "Appliance UTC clock synchronization failed",
            "Appliance UTC clock outside synchronized window",
            "QIKVRT_LIBGUESTFS_CLOCK_PREFLIGHT=OK",
            "/usr/lib/ipxe/qemu/efi-virtio.rom",
            "SUPERMIN_KERNEL",
            "SUPERMIN_KERNEL_VERSION",
            "SUPERMIN_MODULES",
            "CONFIG_IPV6_SIT=y",
            "LIBGUESTFS_CACHEDIR",
            'mktemp -d "$RUNNER_TEMP/qikvrt-libguestfs-cache.XXXXXX"',
            "LIBGUESTFS_BACKEND_SETTINGS=force_tcg",
            "LIBGUESTFS_BACKEND=direct libguestfs-test-tool",
            'qemu-img create -f raw "$probe_disk" 32M',
            "LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1",
            'bash -n "$probe_script"',
            'guestfish --network --rw --format=raw -a "$probe_disk"',
            'debug-upload "$probe_script" /tmp/qikvrt-libguestfs-network-probe.sh 384',
            'DNS lookup failed: $mirror',
            'TCP connect failed: $mirror:80',
            'debug sh "/bin/bash /tmp/qikvrt-libguestfs-network-probe.sh $mirror $target_epoch $MIN_UBUNTU_RELEASE_EPOCH $MAX_SUPPORTED_BUILD_EPOCH $LIBGUESTFS_CLOCK_OBSERVATION_WINDOW_SECONDS"',
            "QIKVRT_LIBGUESTFS_NETWORK_PREFLIGHT=OK",
        ]:
            self.assertIn(text, host_run)
        self.assertNotIn("ip -4 -o addr show dev eth0 scope global | grep -q", host_run)
        self.assertNotIn("ip -4 route show default | grep -q", host_run)
        causal_order = [
            'trusted_time_headers="$RUNNER_TEMP/qikvrt-trusted-time.headers"',
            "https://api.github.com/rate_limit?qikvrt_clock=",
            'trusted_http_date="$(awk',
            'trusted_remote_epoch="$(LC_ALL=C date -u -d',
            "runner UTC epoch disagrees with trusted GitHub API time",
            "apt-config shell",
            "host APT source contains a per-source date-verification override",
            "sudo apt-get -o APT::Update::Error-Mode=any -o Acquire::Check-Date=true -o Acquire::Check-Valid-Until=true update",
            'trusted_host_epoch="$(date -u +%s)"',
            "post-APT runner UTC epoch escaped trusted GitHub API time",
            'echo "QIKVRT_TRUSTED_HOST_EPOCH=$trusted_host_epoch"',
            "sudo apt-get install",
            'find /usr/lib -type d -path \'*/guestfs/supermin.d\' -print | sort > "$supermin_dirs_file"',
            'mapfile -t supermin_dirs < "$supermin_dirs_file"',
            "printf '%s\\n' 'dhcpcd-base' | sudo tee",
            "printf '%s\\n' '/etc/dhcpcd.conf' | sudo tee",
            'sudo chmod 0644 "$dhcp_package_fragment" "$dhcp_hostfiles_fragment"',
            '[ -r "$dhcp_package_fragment" ]',
            "grep -Fqx 'dhcpcd-base'",
            "grep -Fqx '/etc/dhcpcd.conf'",
            'export LIBGUESTFS_CACHEDIR="$(mktemp -d',
            "LIBGUESTFS_BACKEND=direct libguestfs-test-tool",
            'qemu-img create -f raw "$probe_disk" 32M',
            "Appliance UTC clock synchronization failed",
            "QIKVRT_LIBGUESTFS_CLOCK_PREFLIGHT=OK",
            "Appliance DHCP configuration missing: /etc/dhcpcd.conf",
            "Appliance DHCP client missing: dhcpcd",
            "Appliance IPv4 address missing: eth0",
            "Appliance default route missing",
            "Appliance resolver configuration missing",
            'DNS lookup failed: $mirror',
            'TCP connect failed: $mirror:80',
            'bash -n "$probe_script"',
            "guestfish --network --rw --format=raw",
            'debug-upload "$probe_script"',
            'debug sh "/bin/bash /tmp/qikvrt-libguestfs-network-probe.sh $mirror $target_epoch $MIN_UBUNTU_RELEASE_EPOCH $MAX_SUPPORTED_BUILD_EPOCH $LIBGUESTFS_CLOCK_OBSERVATION_WINDOW_SECONDS"',
            "QIKVRT_LIBGUESTFS_NETWORK_PREFLIGHT=OK",
        ]
        positions = [host_run.index(text) for text in causal_order]
        self.assertEqual(positions, sorted(positions))

        appliance_step = build_steps[appliance_index]
        self.assertEqual(
            appliance_step["env"]["QIKVRT_BUILD_ARCH"], "${{ matrix.arch }}"
        )
        appliance_run = appliance_step["run"]
        for text in [
            'build_log="$RUNNER_TEMP/qikvrt-mesh-linux-$QIKVRT_BUILD_ARCH-build.log"',
            "tools/qikvrt_mesh_linux_release_v2.py build",
            '> "$build_log" 2>&1',
            'tail -n 4000 "$build_log" >&2',
            'exit "$build_status"',
        ]:
            self.assertIn(text, appliance_run)
        with tempfile.TemporaryDirectory() as directory:
            runner_temp = pathlib.Path(directory)
            stub_bin = runner_temp / "bin"
            stub_bin.mkdir()
            python_stub = stub_bin / "python3"
            python_stub.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$QIKVRT_STUB_LINE\"\n"
                "exit \"$QIKVRT_STUB_STATUS\"\n"
            )
            python_stub.chmod(0o755)
            wrapper_env = {
                **os.environ,
                "PATH": f"{stub_bin}:{os.environ['PATH']}",
                "RUNNER_TEMP": str(runner_temp),
                "QIKVRT_BUILD_ARCH": "amd64",
                "QIKVRT_STUB_LINE": "QIKVRT_WRAPPER_SENTINEL=FAILURE",
                "QIKVRT_STUB_STATUS": "37",
            }
            failed_wrapper = subprocess.run(
                ["bash", "-c", appliance_run],
                env=wrapper_env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(failed_wrapper.returncode, 37)
            self.assertIn("bounded diagnostic tail follows", failed_wrapper.stderr)
            self.assertIn("QIKVRT_WRAPPER_SENTINEL=FAILURE", failed_wrapper.stderr)
            wrapper_env.update(
                {
                    "QIKVRT_STUB_LINE": "QIKVRT_WRAPPER_SENTINEL=OK",
                    "QIKVRT_STUB_STATUS": "0",
                }
            )
            successful_wrapper = subprocess.run(
                ["bash", "-c", appliance_run],
                env=wrapper_env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(successful_wrapper.returncode, 0)
            self.assertIn("QIKVRT_WRAPPER_SENTINEL=OK", successful_wrapper.stdout)

        release_upload_index = next(
            index
            for index, step in enumerate(build_steps)
            if step.get("uses", "").startswith("actions/upload-artifact@")
            and step.get("with", {}).get("name")
            == "qikvrt-mesh-linux-${{ matrix.arch }}"
        )
        release_upload = build_steps[release_upload_index]
        self.assertNotIn("if", release_upload)
        self.assertEqual(release_upload["with"]["path"], "${{ runner.temp }}/dist/*")

        diagnostic_index = next(
            index
            for index, step in enumerate(build_steps)
            if step.get("name") == "Upload failed native-build diagnostic log"
        )
        diagnostic_step = build_steps[diagnostic_index]
        self.assertGreater(diagnostic_index, release_upload_index)
        self.assertEqual(diagnostic_step["if"], "failure()")
        self.assertEqual(
            diagnostic_step["with"]["name"],
            "qikvrt-mesh-linux-${{ matrix.arch }}-diagnostics",
        )
        self.assertEqual(
            diagnostic_step["with"]["path"],
            "${{ runner.temp }}/qikvrt-mesh-linux-${{ matrix.arch }}-build.log",
        )
        self.assertEqual(diagnostic_step["with"]["if-no-files-found"], "error")

        mode_run = next(
            step["run"]
            for step in workflow["jobs"]["prepare"]["steps"]
            if step.get("id") == "mode"
        )
        self.assertEqual(mode_run.count("publish_ready=true"), 1)
        nonpublish_modes = mode_run[
            mode_run.index("pull_request|workflow_dispatch)") : mode_run.index(
                "push)"
            )
        ]
        self.assertNotIn("publish_ready=true", nonpublish_modes)
        publish_job = workflow["jobs"]["publish"]
        self.assertEqual(publish_job["needs"], ["prepare", "build"])
        self.assertEqual(
            publish_job["if"], "needs.prepare.outputs.publish_ready == 'true'"
        )
        self.assertEqual(raw.count("anonymous_token_json="), 2)
        self.assertNotIn(":latest", raw)
        self.assertNotIn("--clobber", raw)
        self.assertNotIn("contents: write", raw)
        self.assertNotIn("guestfish --network --ro -a /dev/null", raw)
        self.assertNotIn('debug sh "/bin/bash -c', raw)

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
        self.assertNotIn("py_compile", base_namespace["SELFTEST"])
        self.assertIn(
            'compile(pathlib.Path(p).read_text(encoding="utf-8"),p,"exec")',
            base_namespace["SELFTEST"],
        )
        self.assertIn("qcow.unlink()", base_raw)
        self.assertIn('if arch=="amd64":shutil.copy2', base_raw)
        self.assertIn('"LIBGUESTFS_DEBUG":"1"', base_raw)
        self.assertIn('"LIBGUESTFS_TRACE":"1"', base_raw)
        self.assertIn('run("virt-customize","--network"', base_raw)
        accepted_now = base_namespace["UBUNTU_RELEASE_MIN_EPOCH"] + 1000
        trusted_epoch = str(accepted_now)
        with mock.patch.dict(
            os.environ, {"QIKVRT_TRUSTED_HOST_EPOCH": trusted_epoch}
        ), mock.patch.object(
            base_namespace["time"], "time", return_value=accepted_now
        ):
            clock_sync = base_namespace["libguestfs_clock_sync_command"]()
        self.assertRegex(
            clock_sync,
            r"^set -eu; date -u -s '@\d+' >/dev/null; now=\$\(date -u \+%s\)",
        )
        self.assertIn("QIKVRT_LIBGUESTFS_CLOCK_SYNC=OK", clock_sync)
        self.assertIn("guest APT date verification is disabled", clock_sync)
        self.assertIn(
            "guest APT source contains a per-source date-verification override",
            clock_sync,
        )
        self.assertIn(
            "apt-config shell check_date Acquire::Check-Date/b "
            "check_valid_until Acquire::Check-Valid-Until/b",
            clock_sync,
        )
        self.assertIn("Binary::apt-get::Acquire::Check-Date/b", clock_sync)
        self.assertIn("Binary::apt-get::Acquire::Check-Valid-Until/b", clock_sync)
        self.assertIn("--include='*.list'", clock_sync)
        self.assertIn("--include='*.sources'", clock_sync)
        self.assertIn('[ "$check_date" != true ]', clock_sync)
        self.assertIn('[ "$check_valid_until" != true ]', clock_sync)
        apt_source_regex = base_namespace["APT_SOURCE_DATE_OVERRIDE_REGEX"]
        self.assertIn(
            f"apt_source_date_override_regex='{apt_source_regex}'", clock_sync
        )
        workflow = yaml.safe_load(WF.read_text())
        host_run = next(
            step["run"]
            for step in workflow["jobs"]["build"]["steps"]
            if step.get("name")
            == "Provision and verify native libguestfs host appliance"
        )
        self.assertIn(
            f"apt_source_date_override_regex='{apt_source_regex}'", host_run
        )
        for source_override in [
            "Check-Date: no\n",
            "Check-Date: disable\n",
            "Check-Valid-Until: without\n",
            "Check-Date:\n disable\n",
            "deb [check-date=disable] http://archive.ubuntu.com/ubuntu noble main\n",
            "deb [check-valid-until=without] http://archive.ubuntu.com/ubuntu noble main\n",
            "Check-Date: yes\n",
        ]:
            self.assertEqual(
                subprocess.run(
                    ["grep", "-Eiq", apt_source_regex],
                    input=source_override,
                    text=True,
                ).returncode,
                0,
                source_override,
            )
        for default_source in [
            "# Check-Date: no\n",
            "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu\n",
            "deb http://archive.ubuntu.com/ubuntu noble main\n",
        ]:
            self.assertEqual(
                subprocess.run(
                    ["grep", "-Eiq", apt_source_regex],
                    input=default_source,
                    text=True,
                ).returncode,
                1,
                default_source,
            )
        subprocess.run(["bash", "-n", "-c", clock_sync], check=True)
        policy = json.loads(POLICY.read_text())
        self.assertEqual(
            base_namespace["UBUNTU_RELEASE_MIN_EPOCH"],
            policy["base_distribution"]["release_min_epoch_utc"],
        )
        self.assertEqual(
            base_namespace["MAX_SUPPORTED_BUILD_EPOCH"],
            policy["base_distribution"]["max_supported_build_epoch_utc"],
        )
        self.assertEqual(
            base_namespace["CLOCK_CUSHION_SECONDS"],
            policy["build_acceptance"]["host_libguestfs_clock_cushion_seconds"],
        )
        self.assertEqual(
            base_namespace["TRUSTED_HOST_EPOCH_BACKWARD_SKEW_SECONDS"],
            policy["build_acceptance"]["trusted_host_clock_skew_seconds"],
        )
        self.assertEqual(
            base_namespace["CLOCK_OBSERVATION_WINDOW_SECONDS"],
            policy["build_acceptance"][
                "host_libguestfs_clock_observation_window_seconds"
            ],
        )
        self.assertEqual(
            base_namespace["TRUSTED_HOST_EPOCH_MAX_AGE_SECONDS"],
            policy["build_acceptance"]["trusted_host_epoch_max_age_seconds"],
        )
        helper = base_namespace["libguestfs_clock_sync_command"]
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "missing or invalid"):
                helper()
        with mock.patch.dict(
            os.environ,
            {
                "QIKVRT_TRUSTED_HOST_EPOCH": str(
                    base_namespace["UBUNTU_RELEASE_MIN_EPOCH"] - 1
                )
            },
            clear=True,
        ), mock.patch.object(
            base_namespace["time"],
            "time",
            return_value=base_namespace["UBUNTU_RELEASE_MIN_EPOCH"],
        ):
            with self.assertRaisesRegex(SystemExit, "outside supported build window"):
                helper()
        anchor = base_namespace["UBUNTU_RELEASE_MIN_EPOCH"] + 10000
        for escaped_now in [
            anchor - base_namespace["TRUSTED_HOST_EPOCH_BACKWARD_SKEW_SECONDS"] - 1,
            anchor + base_namespace["TRUSTED_HOST_EPOCH_MAX_AGE_SECONDS"] + 1,
        ]:
            with mock.patch.dict(
                os.environ, {"QIKVRT_TRUSTED_HOST_EPOCH": str(anchor)}, clear=True
            ), mock.patch.object(
                base_namespace["time"], "time", return_value=escaped_now
            ):
                with self.assertRaisesRegex(SystemExit, "escaped trusted post-APT"):
                    helper()
        latest_valid_now = (
            base_namespace["MAX_SUPPORTED_BUILD_EPOCH"]
            - base_namespace["CLOCK_CUSHION_SECONDS"]
            - base_namespace["CLOCK_OBSERVATION_WINDOW_SECONDS"]
        )
        with mock.patch.dict(
            os.environ,
            {"QIKVRT_TRUSTED_HOST_EPOCH": str(latest_valid_now)},
            clear=True,
        ), mock.patch.object(
            base_namespace["time"], "time", return_value=latest_valid_now
        ):
            helper()
        with mock.patch.dict(
            os.environ,
            {"QIKVRT_TRUSTED_HOST_EPOCH": str(latest_valid_now + 1)},
            clear=True,
        ), mock.patch.object(
            base_namespace["time"], "time", return_value=latest_valid_now + 1
        ):
            with self.assertRaisesRegex(SystemExit, "exceeds supported build window"):
                helper()
        self.assertIn(
            '"--run-command",clock_sync,"--install","docker.io"', base_raw
        )
        for disabled in [
            "Acquire::Check-Date=false",
            "Acquire::Check-Valid-Until=false",
            "Acquire::Check-Date=0",
            "Acquire::Check-Valid-Until=0",
        ]:
            self.assertNotIn(disabled, base_raw)

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
