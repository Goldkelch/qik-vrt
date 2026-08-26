from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_HTML = ROOT / "docs/AI/index.html"
AI_JS = ROOT / "docs/assets/js/qikvrt-ai-entrypoint.js"
MANIFEST = ROOT / "browser/firefox/qikvrt-terminal/manifest.json"
OPTIONS = ROOT / "browser/firefox/qikvrt-terminal/options.js"
BACKEND = ROOT / "src/qikvrt_effect_ack_http_terminal.py"
POLICY = ROOT / "policy/CANONICAL_AI_FIREFOX_TERMINAL_V1.json"
HARNESS = ROOT / "tools/qikvrt_canonical_ai_firefox_reobservation.py"
WORKFLOW = ROOT / ".github/workflows/qikvrt_canonical_ai_firefox_reobservation.yml"


class CanonicalAIFirefoxTerminalContractTests(unittest.TestCase):
    def test_canonical_ai_route_is_visible_same_origin_and_no_fetch(self) -> None:
        html = AI_HTML.read_text(encoding="utf-8")
        script = AI_JS.read_text(encoding="utf-8")
        self.assertIn('data-qikvrt-entrypoint="canonical-ai-v1"', html)
        self.assertIn('id="terminalRoute"', html)
        self.assertIn('href="../terminal/?qikvrt_ai_entry=1"', html)
        self.assertIn('id="meshFallback"', html)
        self.assertIn("AI_ROUTE_READY", script)
        self.assertIn('parameters.get("navigate") === "terminal"', script)
        self.assertIn("route.origin !== window.location.origin", script)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("XMLHttpRequest", script)
        self.assertNotIn("WebSocket", script)

    def test_extension_e2e_reuses_exact_declared_loopback_permissions(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        options = OPTIONS.read_text(encoding="utf-8")
        backend = BACKEND.read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "1.0.1")
        self.assertIn("http://127.0.0.1:8771/*", manifest["host_permissions"])
        self.assertIn("http://localhost:8771/*", manifest["host_permissions"])
        self.assertNotIn("http://127.0.0.1/*", manifest["host_permissions"])
        self.assertNotIn("http://localhost/*", manifest["host_permissions"])
        self.assertIn("Access-Control-Allow-Origin", backend)
        self.assertIn("Access-Control-Allow-Private-Network", backend)
        self.assertIn("NON_CREDENTIALED_LOOPBACK_ONLY", backend)
        self.assertIn('searchParams.get("qikvrt_e2e") === "1"', options)
        self.assertIn("QIKVRT-FIREFOX-E2E-NONCE-0001", options)
        self.assertIn(
            'const E2E_HOST_PERMISSION = "http://127.0.0.1:8771/*"',
            options,
        )
        self.assertIn('network_effect_path: "BACKGROUND_DISCOVER_PREPARE_COMMIT"', options)
        self.assertIn("browser.runtime.sendMessage({kind: \"DISCOVER_EFFECT_ACK\"})", options)
        self.assertIn("browser.runtime.sendMessage({kind: \"PREPARE_EFFECT\"", options)
        self.assertIn('kind: "COMMIT_EFFECT"', options)
        self.assertNotIn("await fetch(", options)
        self.assertIn('external_effect: committed.body', options)

    def test_lna_grant_targets_actual_webextension_principal_only(self) -> None:
        source = HARNESS.read_text(encoding="utf-8")
        self.assertIn('prefs["permissions.default.loopback-network"] = 0', source)
        self.assertIn('prefs["permissions.default.local-network"] = 0', source)
        self.assertIn("WebExtensionPolicy.getByID", source)
        self.assertIn("policy.extension.principal", source)
        self.assertIn("principalAddonId", source)
        self.assertIn("actualExtensionPrincipalUsed", source)
        self.assertIn("reconstructedPrincipalUsed", source)
        self.assertIn("profile_wide_loopback_allow", source)
        self.assertNotIn("createContentPrincipal", source)
        self.assertNotIn('prefs["permissions.default.loopback-network"] = 1', source)
        self.assertIn('"FIREFOX_SESSION_ONLY"', source)
        self.assertIn('"ISOLATED_WEBDRIVER_PROFILE"', source)

    def test_policy_preserves_observation_and_effect_boundaries(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["authority_repository"], "Goldkelch/qik-vrt")
        self.assertEqual(policy["routes"]["pages_path"], "/qik-vrt/AI/")
        self.assertTrue(policy["routes"]["same_origin_required"])
        self.assertTrue(
            policy["literal_exact_head_observation"]["real_firefox_process_required"]
        )
        self.assertTrue(
            policy["literal_exact_head_observation"]["terminal_interaction_required"]
        )
        self.assertFalse(policy["event_model"]["schedule"])
        self.assertFalse(policy["event_model"]["polling"])
        self.assertEqual(
            policy["bounded_effect_ack"]["scope"],
            "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
        )
        self.assertEqual(policy["bounded_effect_ack"]["external_effect"], "NONE")
        self.assertFalse(policy["bounded_effect_ack"]["general_effect_ack_done"])

    def test_workflow_is_event_driven_and_literal_head_bound(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertIn(
            "github.event.pull_request.head.sha || github.sha",
            workflow,
        )
        self.assertIn("git rev-parse --verify HEAD^{commit}", workflow)
        self.assertIn("git rev-parse --verify HEAD^{tree}", workflow)
        self.assertIn("firefox --version", workflow)
        self.assertIn(
            "tools/qikvrt_canonical_ai_firefox_reobservation.py",
            workflow,
        )
        self.assertIn("/terminal/state", workflow)
        self.assertIn("bounded", workflow.lower())

    def test_harness_requires_each_distinct_observation(self) -> None:
        source = HARNESS.read_text(encoding="utf-8")
        for marker in (
            "canonical_ai_route_observed",
            "browser_rendering_observed",
            "browser_javascript_observed",
            "terminal_interaction_observed",
            "bounded_loopback_effect_ack_done",
            '"general_effect_ack_done": False',
            '"external_effect": "NONE"',
            '"physical_megast_execution": False',
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
