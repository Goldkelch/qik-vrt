from __future__ import annotations

import pathlib
import re
import stat
import subprocess
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "universal-terminal"


class CloudTransputerServicePlaneTests(unittest.TestCase):
    def test_fixed_mesh_path_is_single_canonical_proxy_surface(self) -> None:
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        nginx = (DEPLOY / "nginx.conf").read_text(encoding="utf-8")
        entrypoint = (DEPLOY / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:${QIKVRT_MESH_HOST_PORT:-8080}:8080", compose)
        self.assertIn("location = /qik-vrt/mesh/v1/", nginx)
        self.assertIn("location /qik-vrt/mesh/v1/terminal/", nginx)
        self.assertIn("location /qik-vrt/mesh/v1/effect-ack/", nginx)
        self.assertIn("http://qikvrt-gateway:8080/qik-vrt/mesh/v1/", entrypoint)

    def test_service_plane_is_loopback_published_and_fail_closed(self) -> None:
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        for service in (
            "qikvrt-universal-terminal",
            "qikvrt-gateway",
            "qikvrt-smtpd",
            "qikvrt-snmpd",
            "qikvrt-dnsd",
            "qikvrt-sshd",
            "qikvrt-sqld",
            "qikvrt-mirror",
        ):
            self.assertIn(service + ":", compose)
        published = re.findall(r'"([^"]+)"', compose)
        host_bindings = [value for value in published if ":" in value and ("${QIKVRT_" in value)]
        self.assertTrue(host_bindings)
        self.assertTrue(all(value.startswith("127.0.0.1:") for value in host_bindings))
        self.assertIn("QIKVRT_DB_PASSWORD: ${QIKVRT_DB_PASSWORD:-}", compose)
        self.assertNotIn("0.0.0.0:${QIKVRT_", compose)

    def test_mirror_is_read_only_network_export(self) -> None:
        script = (DEPLOY / "mirror-bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn("git clone --mirror", script)
        self.assertIn("git ls-remote", script)
        self.assertIn('"mutation_performed":False', script)
        self.assertIn("git daemon", script)
        self.assertNotIn("git push", script)

    def test_smtp_is_non_relaying_sink(self) -> None:
        script = (DEPLOY / "qikvrt_smtpd.py").read_text(encoding="utf-8")
        self.assertIn('"relay_performed": False', script)
        self.assertNotIn("smtplib", script)
        self.assertIn("MAX_MESSAGE_BYTES", script)

    def test_c90_m68000_contract_is_explicit(self) -> None:
        dockerfile = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
        source = (DEPLOY / "qikvrt_ip_bootstrap.c").read_text(encoding="utf-8")
        self.assertIn("gcc-m68k-linux-gnu", dockerfile)
        self.assertIn("-m68000 -std=c90 -pedantic-errors", dockerfile)
        self.assertIn("qikvrt_ip_bootstrap.o", dockerfile)
        self.assertIn("Strict ISO C90 source", source)
        self.assertNotIn("//", source)

    def test_profile_packaging_preserves_workdir_for_runtime_permissions(self) -> None:
        """Execute the real RUN body: an unscoped cd must fail, not pass a grep."""
        dockerfile = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
        blocks = [
            block for block in dockerfile.split("\n\n")
            if block.startswith("RUN mkdir -p /opt/qikvrt/runtime/bootstrap-profile/")
        ]
        self.assertEqual(len(blocks), 1, "locate the actual profile RUN instruction")
        with tempfile.TemporaryDirectory(prefix="qikvrt-profile-") as temporary:
            base = pathlib.Path(temporary)
            repo = base / "repo"
            extension = repo / "browser/firefox/qikvrt-terminal"
            extension.mkdir(parents=True)
            (extension / "manifest.json").write_text('{"manifest_version": 2}\n', encoding="utf-8")
            deploy = repo / "deploy/universal-terminal"
            deploy.mkdir(parents=True)
            scripts = [
                deploy / name for name in (
                    "entrypoint.sh", "runtime-health.sh", "service-entrypoint.sh",
                    "mirror-bootstrap.sh", "qikvrt_smtpd.py",
                )
            ]
            binaries = base / "bin"
            binaries.mkdir()
            scripts.append(binaries / "qikvrt-ip-bootstrap")
            for script in scripts:
                script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                script.chmod(0o644)
            # Map only absolute image paths into the fixture; preserve every
            # relative path and all shell control flow from the Dockerfile.
            command = blocks[0][len("RUN "):]
            for original, replacement in (
                ("/opt/qikvrt", repo), ("/var/lib/qikvrt", base / "data"),
                ("/usr/local/bin", binaries),
            ):
                command = command.replace(original, str(replacement))
            result = subprocess.run(
                ["/bin/sh", "-eu", "-c", command], cwd=repo, text=True,
                capture_output=True, timeout=15, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for script in scripts:
                self.assertTrue(script.stat().st_mode & stat.S_IXUSR, str(script))
            profile = repo / "runtime/bootstrap-profile"
            with zipfile.ZipFile(profile / "extensions/qikvrt-ai-terminal@goldkelch.local.xpi") as archive:
                self.assertEqual(archive.namelist(), ["manifest.json"])
            self.assertIn("browser.startup.homepage", (profile / "user.js").read_text(encoding="utf-8"))

    def test_effect_ack_is_reachable_only_through_explicit_proxy_or_terminal(self) -> None:
        entrypoint = (DEPLOY / "entrypoint.sh").read_text(encoding="utf-8")
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn('HTTP_HOST="${QIKVRT_HTTP_HOST:-127.0.0.1}"', entrypoint)
        self.assertIn("QIKVRT_HTTP_HOST: 0.0.0.0", compose)
        self.assertNotIn('\":8771\"', compose)

    def test_sql_password_has_no_repository_default(self) -> None:
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        service = (DEPLOY / "service-entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("QIKVRT_DB_PASSWORD: ${QIKVRT_DB_PASSWORD:-}", compose)
        self.assertIn("QIKVRT_DB_PASSWORD is required for sqld", service)
        self.assertIn('if [ -z "$DB_PASSWORD" ]', service)
        self.assertNotIn("postgres:postgres", compose)


if __name__ == "__main__":
    unittest.main()
