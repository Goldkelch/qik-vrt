from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERMINAL = ROOT / "browser" / "firefox" / "qikvrt-terminal"


class FirefoxV2TerminalPeerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.background = (TERMINAL / "background.js").read_text(encoding="utf-8")
        self.content = (TERMINAL / "content.js").read_text(encoding="utf-8")
        self.options = (TERMINAL / "options.js").read_text(encoding="utf-8")
        self.readme = (TERMINAL / "README.md").read_text(encoding="utf-8")
        self.document = (ROOT / "docs" / "terminal" / "FIREFOX_EFFECT_ACK_TERMINAL_PROXY_V1.md").read_text(encoding="utf-8")
        self.manifest = json.loads((TERMINAL / "manifest.json").read_text(encoding="utf-8"))
        self.policy = json.loads((ROOT / "policy" / "QIKVRT_HTTP_TERMINAL_PEER_V2.json").read_text(encoding="utf-8"))

    def test_v2_peer_is_explicit_local_and_policy_bound(self) -> None:
        self.assertIn("http://127.0.0.1:8771/*", self.manifest["host_permissions"])
        self.assertNotIn("http://127.0.0.1:8772/*", self.manifest["host_permissions"])
        self.assertIn('const V2_ALLOWED_BACKENDS = new Set(["http://127.0.0.1:8771"])', self.background)
        self.assertIn('const V2_POLICY_ID = "QIKVRT_HTTP_TERMINAL_PEER_V2"', self.background)
        self.assertIn(f'const V2_POLICY_SHA256 = "{self.policy["policy_sha256"]}"', self.background)
        self.assertIn("normalizePeerV2Config", self.background)
        self.assertIn("V2 source and target nodes must differ", self.background)
        self.assertIn("PREPARE_PEER_V2", self.background)
        self.assertIn("COMMIT_PEER_V2", self.background)
        self.assertIn("explicit V2 commit confirmation and validated prepare are required", self.background)
        self.assertIn("local_commit_receipt: true, ordinary_release: false", self.background)
        self.assertIn("external_effect: \"NONE\"", self.background)

    def test_v2_serialization_and_reobservation_are_closed(self) -> None:
        self.assertIn("function canonicalJsonV2", self.background)
        self.assertIn("function isCanonicalObject", self.background)
        self.assertIn("compareUnicodeScalars", self.background)
        self.assertIn("Number.isSafeInteger", self.background)
        self.assertIn("peerMediaDescriptorV2", self.background)
        self.assertIn("sha256HexV2", self.background)
        self.assertIn("deterministicRequestIdV2", self.background)
        self.assertIn("Idempotency-Key", self.background)
        self.assertIn("validatePeerPreparedV2", self.background)
        self.assertIn("(v !== 1 && v !== 2)", self.background)
        self.assertIn("The GET is an explicit user-triggered reobservation", self.background)
        self.assertIn("canonicalJsonV2(envelope)", self.background)
        self.assertNotIn("browser.alarms", self.background)
        self.assertNotIn("setInterval", self.background)
        self.assertNotIn("setTimeout", self.background)
        self.assertNotIn("browser.storage.onChanged", self.background)

    def test_content_and_options_require_explicit_operator_actions(self) -> None:
        self.assertIn('data-act="peer-prepare"', self.content)
        self.assertIn('data-act="peer-commit"', self.content)
        self.assertIn('send("PREPARE_PEER_V2", request)', self.content)
        self.assertIn('send("COMMIT_PEER_V2", {confirmed: true, prepared: peerPrepared})', self.content)
        self.assertNotIn("applyPreferences().then(peerPrepare)", self.content)
        self.assertNotIn("applyPreferences().then(peerCommit)", self.content)
        self.assertIn("qikvrtPeerV2Config", self.options)
        self.assertIn("peerV2Enabled", self.options)
        self.assertIn("peerV2TargetNode", self.options)

    def test_documentation_keeps_runtime_and_external_boundaries_open(self) -> None:
        for text in (self.readme, self.document):
            self.assertIn("TLS/mTLS", text)
            self.assertIn("external effect", text)
            self.assertIn("no alarm, timer", text.lower())
        self.assertIn("Firefox runtime operation", " ".join(self.document.split()))
        self.assertIn("not promoted to a repository write", self.readme)


if __name__ == "__main__":
    unittest.main()
