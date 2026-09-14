from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = ROOT / "browser" / "firefox" / "qikvrt-terminal"
MANIFEST = TERMINAL / "manifest.json"
ADAPTER = TERMINAL / "authenticated_delivery.js"
LEDGER = ROOT / "state" / "delivery" / "ACTIVE_DELIVERY_OBLIGATIONS_V1.json"
ARXIV_REQUEST = ROOT / "state" / "delivery" / "requests" / "ARXIV_PLANCK_TICK_GAP_LAW_V1.json"
WIKIPEDIA_REQUEST = ROOT / "state" / "delivery" / "requests" / "WIKIPEDIA_LEAN_LAKE_PROOF_STATUS_V1.json"


class AuthenticatedWebDeliveryProxyTests(unittest.TestCase):
    def test_manifest_admits_bound_authenticated_surfaces(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("https://arxiv.org/*", manifest["host_permissions"])
        self.assertIn("https://*.wikipedia.org/*", manifest["host_permissions"])
        self.assertIn("https://auth.wikimedia.org/*", manifest["host_permissions"])
        self.assertIn("https://*/*", manifest["optional_host_permissions"])
        delivery_scripts = [
            entry
            for entry in manifest["content_scripts"]
            if "authenticated_delivery.js" in entry.get("js", [])
        ]
        self.assertEqual(len(delivery_scripts), 1)
        matches = delivery_scripts[0]["matches"]
        self.assertIn("https://arxiv.org/*", matches)
        self.assertIn("https://*.wikipedia.org/*", matches)

    def test_delivery_requests_and_ledger_bind_the_same_proxy(self) -> None:
        arxiv = json.loads(ARXIV_REQUEST.read_text(encoding="utf-8"))
        wikipedia = json.loads(WIKIPEDIA_REQUEST.read_text(encoding="utf-8"))
        request_by_platform = {"arxiv": arxiv, "wikipedia": wikipedia}
        for request in request_by_platform.values():
            self.assertEqual(request["schema"], "qikvrt_external_delivery_request_v1")
            self.assertTrue(request["preconditions"]["exact_main_reobservation_required"])
            self.assertFalse(request["preconditions"]["predecessor_evidence_transfer"])
            self.assertTrue(request["effect_ack"]["required"])
            self.assertTrue(request["effect_ack"]["readback_required"])
            self.assertFalse(request["completion_claims"]["PASS"])
            self.assertFalse(request["completion_claims"]["FINAL_PASS"])
            self.assertFalse(request["completion_claims"]["EFFECT_ACK_DONE"])

        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        bound = {
            item["delivery"]["platform"]: item
            for item in ledger["obligations"]
            if item.get("delivery", {}).get("platform") in request_by_platform
        }
        self.assertEqual(set(bound), {"arxiv", "wikipedia"})
        for platform, obligation in bound.items():
            self.assertEqual(obligation["delivery"]["adapter"], "QIKVRT_FIREFOX_TERMINAL_PROXY_V1")
            self.assertTrue(obligation["delivery"]["effect_ack_required"])
            self.assertEqual(obligation["main_reobservation"]["binding"], "EXACT_MAIN_HEAD")
            self.assertEqual(
                obligation["delivery"]["request"],
                f"state/delivery/requests/{request_by_platform[platform]['id']}.json",
            )

    def test_adapter_is_fail_closed_and_credential_isolating(self) -> None:
        source = ADAPTER.read_text(encoding="utf-8")
        required = (
            'const ADAPTER = "QIKVRT_FIREFOX_TERMINAL_PROXY_V1"',
            'const DELIVERY_LEDGER = "state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json"',
            'AUTHORIZED_EXTERNAL_PUBLICATION_EFFECT',
            'AUTHORIZED_EXTERNAL_WEB_EFFECT',
            'bound delivery obligation unavailable',
            'delivery obligation exact-main binding missing',
            'exact-main reobservation not required by request',
            'predecessor evidence boundary missing',
            'trusted main drift; reprepare required',
            'delivery request drift',
            'form changed after prepare',
            'readback_required: true',
            'qikvrt_authenticated_web_readback_v1',
            'authoritative_subject_observed',
            'completion_claims: {PASS: false, FINAL_PASS: false, EFFECT_ACK_DONE: false}',
        )
        for marker in required:
            self.assertIn(marker, source)
        self.assertIn('type === "password"', source)
        self.assertIn('/token|secret|otp|totp|captcha/', source)
        self.assertIn('descriptor.value_sha256 = null', source)
        self.assertNotIn('localStorage.setItem', source)
        self.assertNotIn('control.value =', source)
        self.assertNotIn('document.cookie', source)

    def test_commit_is_explicit_two_phase_and_same_origin(self) -> None:
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn('function prepare()', source)
        self.assertIn('function commit()', source)
        self.assertIn('action.origin === location.origin', source)
        self.assertIn('submit.click()', source)
        self.assertIn('sessionStorage.setItem(PENDING_KEY', source)
        self.assertIn('reobservePending()', source)
        self.assertNotIn('form.submit()', source)


if __name__ == "__main__":
    unittest.main()
