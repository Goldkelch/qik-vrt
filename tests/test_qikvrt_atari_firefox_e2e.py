from __future__ import annotations

import base64
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_atari_firefox_e2e.py"


class AtariFirefoxE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("atari_firefox_e2e", TOOL)
        cls.mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(cls.mod)

    def successful_terminal(self) -> dict[str, object]:
        return {
            "state": self.mod.TERMINAL_SUCCESS_STATE,
            "screen": (
                "$ atari.boot --firefox-extension\n"
                "ATARI_BOOT_ID 0123456789abcdef0123456789abcdef\n"
                "MLP.OPEN sha256:" + "a" * 64 + "\n"
                "HATARI.LOG sha256:" + "b" * 64 + "\n"
                "EFFECT_ACK_DONE=false\n"
            ),
        }

    def permission_receipt(self) -> dict[str, object]:
        return {
            "addonId": self.mod.EXTENSION_ID,
            "policyId": self.mod.EXTENSION_ID,
            "policyHostname": "uuid-example",
            "extensionUUID": "uuid-example",
            "principalAddonId": self.mod.EXTENSION_ID,
            "permission": "loopback-network",
            "capability": 1,
            "allowCapability": 1,
            "scope": "FIREFOX_SESSION_ONLY",
            "target": "127.0.0.1:8771",
            "actualExtensionPrincipalUsed": True,
            "reconstructedPrincipalUsed": False,
        }

    def test_candidate_url_is_exactly_extension_bound(self) -> None:
        self.assertEqual(
            self.mod.validate_candidate_url(
                "https://goldkelch.github.io/qik-vrt/atari-terminal/"
            ),
            "https://goldkelch.github.io/qik-vrt/atari-terminal/",
        )
        for unsafe in (
            "http://goldkelch.github.io/qik-vrt/atari-terminal/",
            "https://goldkelch.github.io:8443/qik-vrt/atari-terminal/",
            "https://goldkelch.github.io/qik-vrt/atari-terminal",
            "https://goldkelch.github.io/qik-vrt/atari-terminal/?x=1",
            "https://example.test/qik-vrt/atari-terminal/",
        ):
            with self.assertRaises(ValueError, msg=unsafe):
                self.mod.validate_candidate_url(unsafe)

    def test_session_payload_keeps_lna_fail_closed_and_local_dns_bound(self) -> None:
        payload = self.mod.firefox_session_payload()
        capability = payload["capabilities"]["alwaysMatch"]
        prefs = capability["moz:firefoxOptions"]["prefs"]
        self.assertTrue(capability["acceptInsecureCerts"])
        self.assertEqual(prefs["permissions.default.loopback-network"], 0)
        self.assertEqual(prefs["permissions.default.local-network"], 0)
        self.assertTrue(prefs["network.lna.enabled"])
        self.assertTrue(prefs["network.lna.blocking"])
        self.assertEqual(prefs["network.trr.mode"], 5)
        self.assertEqual(prefs["network.proxy.type"], 0)
        self.assertIn(self.mod.EXTENSION_ID, prefs["extensions.webextensions.uuids"])

    def test_grant_uses_actual_installed_extension_principal_and_restores_content(self) -> None:
        calls: list[tuple[str, str, object]] = []

        def fake_request(method, url, body=None, timeout=0.0):
            calls.append((method, url, body))
            return {"value": None}

        with mock.patch.object(self.mod, "request_json", side_effect=fake_request), mock.patch.object(
            self.mod, "execute", return_value=self.permission_receipt()
        ) as execute:
            result = self.mod.grant_exact_extension_loopback_permission(
                "http://127.0.0.1:4444", "session", "uuid-example"
            )

        self.assertTrue(result["loopback_network_permission_observed"])
        self.assertFalse(result["profile_wide_loopback_allow"])
        self.assertEqual(calls[0][2], {"context": "chrome"})
        self.assertEqual(calls[-1][2], {"context": "content"})
        script = execute.call_args.args[2]
        self.assertIn("WebExtensionPolicy.getByID", script)
        self.assertIn("policy.extension.principal", script)
        self.assertIn("Services.perms.EXPIRE_SESSION", script)
        self.assertNotIn("createContentPrincipal", script)

    def test_success_requires_visible_terminal_evidence(self) -> None:
        terminal = self.successful_terminal()
        self.assertTrue(self.mod.terminal_success(terminal))
        self.assertEqual(
            self.mod.atari_boot_id(str(terminal["screen"])),
            "0123456789abcdef0123456789abcdef",
        )
        self.assertEqual(
            self.mod.visible_terminal_digest(str(terminal["screen"]), "MLP.OPEN"),
            "a" * 64,
        )
        self.assertEqual(
            self.mod.visible_terminal_digest(str(terminal["screen"]), "HATARI.LOG"),
            "b" * 64,
        )
        for marker in ("ATARI_BOOT_ID ", "MLP.OPEN sha256:", "HATARI.LOG sha256:"):
            incomplete = dict(terminal)
            incomplete["screen"] = str(terminal["screen"]).replace(marker, "")
            self.assertFalse(self.mod.terminal_success(incomplete))

    def test_receipt_retains_all_non_claims(self) -> None:
        receipt = self.mod.build_receipt(
            candidate_url="https://goldkelch.github.io/qik-vrt/atari-terminal/",
            xpi_sha256="a" * 64,
            capabilities={"browserName": "firefox", "browserVersion": "153"},
            extension_id=self.mod.EXTENSION_ID,
            extension_uuid="uuid-example",
            lna_permission={"scope": "FIREFOX_SESSION_ONLY"},
            terminal=self.successful_terminal(),
            screenshot_sha256="b" * 64,
        )
        self.assertTrue(receipt["browser_rendering_observed"])
        self.assertTrue(receipt["universal_terminal_pattern_observed"])
        self.assertTrue(receipt["virtual_megast_execution_observed"])
        self.assertEqual(receipt["mlp_open_sha256"], "a" * 64)
        self.assertEqual(receipt["hatari_trace_sha256"], "b" * 64)
        self.assertFalse(receipt["effect_ack_done"])
        self.assertFalse(receipt["general_effect_ack_done"])
        self.assertEqual(receipt["external_effect"], "NONE")
        self.assertFalse(receipt["physical_megast_execution"])
        self.assertFalse(receipt["deployment"])
        self.assertFalse(receipt["pass"])
        self.assertFalse(receipt["final_pass"])

    def test_screenshot_is_a_nontrivial_png(self) -> None:
        raw = self.mod.PNG_SIGNATURE + b"x" * 1024
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "firefox.png"
            with mock.patch.object(
                self.mod,
                "request_json",
                return_value={"value": base64.b64encode(raw).decode("ascii")},
            ):
                digest = self.mod.save_screenshot("http://driver", "session", output)
            self.assertEqual(digest, self.mod.hashlib.sha256(raw).hexdigest())
            self.assertEqual(output.read_bytes(), raw)

    def test_source_contains_no_direct_page_loopback_or_effect_promotion(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("temporary\": True", source)
        self.assertIn('"loopback-network"', source)
        self.assertIn('"FIREFOX_SESSION_ONLY"', source)
        self.assertIn('"effect_ack_done": False', source)
        self.assertIn('"general_effect_ack_done": False', source)
        self.assertIn('"external_effect": "NONE"', source)
        self.assertIn('"physical_megast_execution": False', source)
        self.assertIn('"deployment": False', source)
        self.assertNotIn("fetch('http://127.0.0.1", source)
        self.assertNotIn("createContentPrincipal", source)

    def test_workflow_binds_real_firefox_to_candidate_local_tls_and_hatari(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "qikvrt_effect_ack_http_terminal.yml").read_text(encoding="utf-8")
        for token in (
            "atari-firefox-e2e:",
            "needs: contract-and-e2e",
            "tools/qikvrt_atari_firefox_e2e.py",
            "tools/qikvrt_candidate_tls_server.py",
            "https://goldkelch.github.io/qik-vrt/atari-terminal/",
            "--port 443",
            "qikvrt-atari-firefox-e2e",
            "qikvrt-geckodriver-v0.37.1-linux64",
            "Firefox-visible MLP.OPEN digest mismatch",
            "Firefox-visible HATARI.LOG digest mismatch",
            "candidate-local TLS boundary drift",
            "effect_ack_done': False",
            "general_effect_ack_done': False",
            "external_effect': 'NONE'",
            "physical_megast_execution': False",
            "deployment': False",
            "pass': False",
            "final_pass': False",
        ):
            self.assertIn(token, workflow)
        self.assertIn("actions/cache@caa296126883cff596d87d8935842f9db880ef25", workflow)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", workflow)
        self.assertIn("xvfb-run -a sh -c 'true'", workflow)
        self.assertNotIn("xvfb-run --help", workflow)


if __name__ == "__main__":
    unittest.main()
