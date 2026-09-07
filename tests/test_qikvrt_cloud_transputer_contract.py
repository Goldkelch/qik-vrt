# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/QIKVRT_CLOUD_TRANSPUTER_V1.json"
DOCKERFILE = ROOT / "deploy/cloud-transputer/Dockerfile"
COMPOSE = ROOT / "deploy/cloud-transputer/compose.yaml"
ENTRYPOINT = ROOT / "deploy/cloud-transputer/entrypoint.sh"
HEALTH = ROOT / "deploy/cloud-transputer/runtime-health.sh"
MIRROR = ROOT / "deploy/cloud-transputer/authority-mirror-refresh.sh"
M68K = ROOT / "src/cloud_transputer/m68k_effect_ack_probe.c"
SMTPD = ROOT / "src/cloud_transputer/smtpd.py"
PAGES = ROOT / "docs/cloud-transputer/index.html"


class CloudTransputerContractTests(unittest.TestCase):
    def test_policy_preserves_exact_effect_boundaries(self) -> None:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], "qikvrt_cloud_transputer_v1")
        self.assertEqual(
            value["introduced_from_authority"]["main_sha"],
            "3b140fd85e6723f4cc8c147c56d34d7e1ca48740",
        )
        self.assertEqual(
            value["stable_mesh_surface"]["public_entrypoint"],
            "https://goldkelch.github.io/qik-vrt/cloud-transputer/",
        )
        self.assertFalse(value["stable_mesh_surface"]["pages_is_compute_runtime"])
        self.assertTrue(value["scaling"]["replicas_allowed"])
        self.assertFalse(value["scaling"]["replicas_share_effect_authority"])
        self.assertFalse(value["m68000_boundary"]["standalone_m68000_tcp_ip_stack_claimed"])
        self.assertEqual(
            value["m68000_boundary"]["personal_posix_source_state"],
            "UNBOUND_UNTIL_ACTUAL_OWNER_SOURCE_IS_PRESENT",
        )
        self.assertFalse(value["mirror_semantics"]["polling"])
        self.assertFalse(value["mirror_semantics"]["push_to_authority"])
        for name in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            self.assertFalse(value["effect_boundary"][name])

    def test_container_has_requested_protocol_services_and_m68k_toolchain(self) -> None:
        text = DOCKERFILE.read_text(encoding="utf-8")
        for token in (
            "firefox-esr", "novnc", "nginx", "openssh-server", "postgresql",
            "dnsmasq", "snmpd", "qemu-user", "gcc-m68k-linux-gnu",
        ):
            self.assertIn(token, text)
        for exposed in ("8080/tcp", "2222/tcp", "2525/tcp", "5353/tcp", "5353/udp", "1161/udp", "5432/tcp"):
            self.assertIn(exposed, text)

    def test_compose_defaults_to_loopback_and_persistent_isolated_state(self) -> None:
        text = COMPOSE.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("${QIKVRT_BIND_ADDRESS:-127.0.0.1}"), 7)
        for target in (
            "/var/lib/qikvrt/profile", "/var/lib/qikvrt/state",
            "/var/lib/qikvrt/mirror", "/var/lib/qikvrt/personal-posix",
            "/var/lib/qikvrt/mail",
        ):
            self.assertIn(target, text)
        self.assertIn("no-new-privileges:true", text)

    def test_entrypoint_is_bounded_and_has_no_domain_polling(self) -> None:
        text = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn("m68k-linux-gnu-gcc -std=c90 -pedantic", text)
        self.assertIn("qemu-m68k", text)
        self.assertIn("QIKVRT_REQUIRE_PERSONAL_POSIX", text)
        self.assertIn("PasswordAuthentication no", text)
        self.assertIn("proxy_set_header Upgrade", text)
        self.assertIn("standalone_m68000_tcp_ip_stack_claimed", text)
        self.assertNotIn("git fetch", text)
        self.assertNotIn("while git", text)

    def test_mirror_is_one_shot_canonical_and_never_writes_authority(self) -> None:
        text = MIRROR.read_text(encoding="utf-8")
        self.assertIn("https://github.com/Goldkelch/qik-vrt.git", text)
        self.assertIn("remote update --prune", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("while ", text)
        self.assertIn('"polling": False', text)
        self.assertIn('"writeback_to_authority": False', text)

    def test_health_requires_every_requested_protocol_plane(self) -> None:
        text = HEALTH.read_text(encoding="utf-8")
        for token in (
            "vnc.html", "ssh-keyscan", "snmpget", "pg_isready",
            "SELECT 20 + 22", "dig +time", "EFFECT_ACK_STATE=EFFECT_ACK_DONE",
            "authority-mirror.json",
        ):
            self.assertIn(token, text)

    def test_c90_probe_uses_existing_effect_ack_core_without_false_arch_claim(self) -> None:
        text = M68K.read_text(encoding="utf-8")
        self.assertIn('#include "qikvrt/effect_ack.h"', text)
        self.assertIn("#ifdef __m68k__", text)
        self.assertIn("QIKVRT_EFFECT_ACK_DONE", text)
        self.assertIn("qikvrt_effect_ack_evaluate", text)

    def test_smtp_is_local_domain_only_and_persists_hash_receipt(self) -> None:
        spec = importlib.util.spec_from_file_location("qikvrt_cloud_smtpd", SMTPD)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            state = module.State(pathlib.Path(tmp), "qikvrt.mesh.local")
            self.assertTrue(state.accept_recipient(b"<user@qikvrt.mesh.local>"))
            self.assertFalse(state.accept_recipient(b"<user@example.net>"))
            digest = state.persist("sender@local", ["user@qikvrt.mesh.local"], b"Subject: test\r\n\r\nhello\r\n")
            self.assertEqual(len(digest), 64)
            receipts = list(pathlib.Path(tmp).glob("*.json"))
            self.assertEqual(len(receipts), 1)
            receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
            self.assertFalse(receipt["external_relay"])
            self.assertFalse(receipt["effect_ack_done"])

    def test_pages_surface_is_fixed_launcher_not_compute_claim(self) -> None:
        text = PAGES.read_text(encoding="utf-8")
        self.assertIn("QIK-VRT Cloud Transputer", text)
        self.assertIn("https://goldkelch.github.io/qik-vrt/cloud-transputer/", text)
        self.assertIn("runtimeOrigin", text)
        self.assertIn("/terminal/vnc.html", text)
        self.assertIn("nicht der Compute-Origin", text)


if __name__ == "__main__":
    unittest.main()
