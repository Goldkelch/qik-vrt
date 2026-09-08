# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import base64
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/QIKVRT_CLOUD_TRANSPUTER_POSIX_TCPIP_V2.json"
DOCKERFILE = ROOT / "deploy/cloud-transputer/Dockerfile"
ENTRYPOINT = ROOT / "deploy/cloud-transputer/v2-entrypoint.sh"
HEALTH = ROOT / "deploy/cloud-transputer/v2-runtime-health.sh"
C90 = ROOT / "src/cloud_transputer/personal_posix_tcpip.c"
CORE = ROOT / "src/effect_ack_core.c"
INCLUDE = ROOT / "include"
SQL = ROOT / "src/cloud_transputer/sql92_gateway.py"
COMPOSER = ROOT / "src/cloud_transputer/runtime_v2_compose.py"

sys.path.insert(0, str(SQL.parent))
import runtime_v2_compose  # noqa: E402
import sql92_gateway  # noqa: E402


class CloudTransputerV2Tests(unittest.TestCase):
    def test_policy_keeps_realization_and_effect_boundaries_explicit(self) -> None:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], "qikvrt_cloud_transputer_posix_tcpip_v2")
        self.assertEqual(value["predecessor_runtime"]["head"], "7f639df8ba8cca3fd8d84b63c95575faaa15c1e6")
        self.assertFalse(value["predecessor_runtime"]["evidence_transfer"])
        lane = value["personal_posix_m68000"]
        self.assertEqual(lane["language_contract"], "STRICT_ISO_C90")
        self.assertTrue(lane["standalone_packet_engine"]["ipv4"])
        self.assertTrue(lane["standalone_packet_engine"]["tcp"])
        self.assertTrue(lane["standalone_packet_engine"]["udp"])
        self.assertFalse(lane["standalone_packet_engine"]["host_socket_api_used_by_packet_engine"])
        self.assertFalse(lane["bare_metal_nic_driver_claimed"])
        self.assertFalse(lane["full_posix_1_conformance_claimed"])
        self.assertFalse(lane["physical_m68000_execution_claimed"])
        self.assertEqual(value["scale_contract"]["minimum_candidate_scale_readback_replicas"], 2)
        for name in ("approval", "merge", "publication", "PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            self.assertFalse(value["delivery_boundaries"][name])

    def test_strict_c90_profile_builds_and_exercises_packet_engine_natively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / "qikvrt-personal-posix-native"
            subprocess.run(
                [
                    "cc", "-std=c90", "-pedantic", "-Wall", "-Wextra", "-Werror",
                    f"-I{INCLUDE}", str(CORE), str(C90), "-o", str(binary),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            run = subprocess.run([str(binary)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertIn("ARCH=NON_M68000_BUILD", run.stdout)
        self.assertIn("PERSONAL_POSIX_SELFTEST=PASS", run.stdout)
        self.assertIn("STANDALONE_M68000_TCPIP_PACKET_ENGINE=PASS", run.stdout)
        self.assertIn("TCP_HANDSHAKE_SELFTEST=PASS", run.stdout)
        self.assertIn("TCP_HTTP_BOOTSTRAP_SELFTEST=PASS", run.stdout)
        self.assertIn("UDP_SELFTEST=PASS", run.stdout)
        self.assertIn("EFFECT_ACK_STATE=EFFECT_ACK_DONE", run.stdout)
        self.assertIn("EFFECT_ACK_NEGATIVE_STATE=EFFECT_ACK_CONTINUE", run.stdout)

    def test_packet_engine_has_no_host_socket_dependency(self) -> None:
        text = C90.read_text(encoding="utf-8")
        for forbidden in ("<sys/socket.h>", "socket(", "connect(", "gethostbyname(", "send(", "recv("):
            self.assertNotIn(forbidden, text)
        for required in ("qv_ipv4_packet", "qv_tcp_segment", "qv_udp_segment", "QV_TCP_SYN", "QIKVRT_EFFECT_ACK_DONE"):
            self.assertIn(required, text)

    def test_v2_wrapper_cross_compiles_composes_then_reobserves(self) -> None:
        entry = ENTRYPOINT.read_text(encoding="utf-8")
        for token in (
            "m68k-linux-gnu-gcc -std=c90 -pedantic -Wall -Wextra -Werror -static",
            "qemu-m68k",
            "STANDALONE_M68000_TCPIP_PACKET_ENGINE=PASS",
            "EXTERNAL_PACKET_IO=LINUX_OCI_HOST_ADAPTER_REQUIRED",
            "physical_m68000_execution_claimed':False",
            "global_effect_ack_done':False",
            "sql92_gateway.py",
            "runtime_v2_compose.py",
            "QIKVRT_V2_STARTUP_PRECOMPOSE=1",
            "QIKVRT_CLOUD_TRANSPUTER_V2_READY",
            "qikvrt-cloud-transputer-health",
        ):
            self.assertIn(token, entry)
        subprocess.run(["sh", "-n", str(ENTRYPOINT), str(HEALTH)], check=True)

    def test_runtime_composer_reconciles_verified_profile_without_amplifying_claims(self) -> None:
        runtime = {
            "schema": "qikvrt_cloud_transputer_runtime_v1",
            "runtime_id": "replica-a",
            "effect_ack_done": False,
            "external_effect_claimed": False,
            "pass": False,
            "final_pass": False,
            "standalone_m68000_tcp_ip_stack_claimed": False,
            "kernel_backed_posix_tcp_ip": True,
            "personal_posix_state": "UNBOUND_OWNER_SOURCE_ABSENT",
        }
        receipt = {
            "schema": "qikvrt_personal_posix_m68000_tcpip_receipt_v1",
            "profile": "QIKVRT_PERSONAL_POSIX_C90_V1",
            "source_sha256": "11" * 32,
            "m68000_binary_sha256": "22" * 32,
            "m68000_machine_execution_observed": True,
            "posix_profile_selftest": "PASS",
            "standalone_tcp_ip_scope": "IPV4_TCP_UDP_PACKET_ENGINE_WITH_TCP_HTTP_BOOTSTRAP_V1",
            "standalone_tcp_ip_packet_engine": "PASS",
            "existing_effect_ack_core_linked": True,
            "effect_ack_done_local_selftest": True,
            "negative_effect_ack_fail_closed": True,
            "external_packet_io_adapter": "LINUX_OCI_HOST_ADAPTER",
            "bare_metal_nic_driver_claimed": False,
            "full_posix_1_conformance_claimed": False,
            "physical_m68000_execution_claimed": False,
            "repository_or_publication_effect_claimed": False,
            "pass": False,
            "final_pass": False,
            "global_effect_ack_done": False,
        }
        value = runtime_v2_compose.compose(runtime, receipt, observed_at_unix=123)
        self.assertEqual(value["schema"], "qikvrt_cloud_transputer_runtime_v1")
        self.assertEqual(value["runtime_overlay_schema"], "qikvrt_cloud_transputer_runtime_v2_overlay_v1")
        self.assertEqual(value["personal_posix_state"], "REPOSITORY_C90_M68000_PROFILE_VERIFIED")
        self.assertEqual(value["personal_posix_authority"], "REPOSITORY_EXACT_BOUND_IMPLEMENTATION")
        self.assertEqual(value["personal_posix_source_sha256"], "11" * 32)
        self.assertEqual(value["personal_posix_m68000_binary_sha256"], "22" * 32)
        self.assertTrue(value["standalone_m68000_tcp_ip_packet_engine_verified"])
        self.assertEqual(value["external_packet_io_adapter"], "LINUX_OCI_HOST_ADAPTER")
        self.assertFalse(value["standalone_m68000_tcp_ip_stack_claimed"])
        self.assertFalse(value["bare_metal_nic_driver_claimed"])
        self.assertFalse(value["full_posix_1_conformance_claimed"])
        self.assertFalse(value["physical_m68000_execution_claimed"])
        self.assertFalse(value["external_effect_claimed"])
        self.assertFalse(value["pass"])
        self.assertFalse(value["final_pass"])
        self.assertFalse(value["effect_ack_done"])

    def test_runtime_composer_rejects_global_effect_amplification(self) -> None:
        runtime = {
            "schema": "qikvrt_cloud_transputer_runtime_v1",
            "effect_ack_done": False,
            "external_effect_claimed": False,
            "pass": False,
            "final_pass": False,
            "standalone_m68000_tcp_ip_stack_claimed": False,
            "kernel_backed_posix_tcp_ip": True,
        }
        receipt = {
            "schema": "qikvrt_personal_posix_m68000_tcpip_receipt_v1",
            "profile": "QIKVRT_PERSONAL_POSIX_C90_V1",
            "source_sha256": "11" * 32,
            "m68000_binary_sha256": "22" * 32,
            "m68000_machine_execution_observed": True,
            "posix_profile_selftest": "PASS",
            "standalone_tcp_ip_scope": "IPV4_TCP_UDP_PACKET_ENGINE_WITH_TCP_HTTP_BOOTSTRAP_V1",
            "standalone_tcp_ip_packet_engine": "PASS",
            "existing_effect_ack_core_linked": True,
            "effect_ack_done_local_selftest": True,
            "negative_effect_ack_fail_closed": True,
            "external_packet_io_adapter": "LINUX_OCI_HOST_ADAPTER",
            "bare_metal_nic_driver_claimed": False,
            "full_posix_1_conformance_claimed": False,
            "physical_m68000_execution_claimed": False,
            "repository_or_publication_effect_claimed": False,
            "pass": False,
            "final_pass": False,
            "global_effect_ack_done": True,
        }
        with self.assertRaises(ValueError):
            runtime_v2_compose.compose(runtime, receipt)

    def test_docker_keeps_sql_ui_inside_firefox_proxy_boundary(self) -> None:
        text = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("QIKVRT_SQL_UI_PORT=8772", text)
        self.assertIn("QIKVRT_START_URL=http://127.0.0.1:8772/", text)
        self.assertIn("v2-entrypoint.sh", text)
        self.assertIn("v2-runtime-health.sh", text)
        expose = next(line for line in text.splitlines() if line.startswith("EXPOSE "))
        self.assertNotIn("8772", expose)
        self.assertIn("8080/tcp", expose)

    def test_sql_request_is_single_statement_and_readback_is_select(self) -> None:
        normalized = sql92_gateway.validate_request({
            "schema": "qikvrt_sql92_request_v1",
            "sql": "UPDATE terminal_state SET value='v2' WHERE key='schema'",
            "readback_sql": "SELECT value FROM terminal_state WHERE key='schema'",
        })
        self.assertEqual(normalized["sql_class"], "UPDATE")
        with self.assertRaises(ValueError):
            sql92_gateway.normalize_sql("SELECT 1; SELECT 2")
        with self.assertRaises(ValueError):
            sql92_gateway.normalize_sql("VACUUM")
        with self.assertRaises(ValueError):
            sql92_gateway.normalize_sql("UPDATE terminal_state SET value='x'", readback=True)

    def test_sql_effect_ack_header_requires_exact_hash_and_single_use_token_shape(self) -> None:
        digest = bytes.fromhex("11" * 32)
        token = b"example-token"
        header = (
            "v=1, mode=commit, token=:"
            + base64.b64encode(token).decode("ascii")
            + ":, hash=:"
            + base64.b64encode(digest).decode("ascii")
            + ":"
        )
        parsed = sql92_gateway.parse_effect_ack_request(header)
        self.assertEqual(parsed["mode"], "commit")
        self.assertEqual(parsed["token"], token.decode("ascii"))
        self.assertEqual(parsed["hash"], digest.hex())
        with self.assertRaises(ValueError):
            sql92_gateway.parse_effect_ack_request("v=1, mode=commit")

    def test_v2_health_reobserves_sql_effect_authority_and_runtime_overlay(self) -> None:
        text = HEALTH.read_text(encoding="utf-8")
        self.assertIn("qikvrt-cloud-transputer-health-v1", text)
        self.assertIn("mode=prepare", text)
        self.assertIn("mode=commit", text)
        self.assertIn("EFFECT_ACK_DONE", text)
        self.assertIn("LOCAL_QIKVRT_DATABASE_ONLY", text)
        self.assertIn("authority_repository", text)
        self.assertIn("receipt_count", text)
        self.assertIn("REPOSITORY_C90_M68000_PROFILE_VERIFIED", text)
        self.assertIn("qikvrt_cloud_transputer_runtime_v2_overlay_v1", text)
        self.assertIn("QIKVRT_V2_STARTUP_PRECOMPOSE", text)


if __name__ == "__main__":
    unittest.main()
