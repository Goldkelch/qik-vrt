from __future__ import annotations

import json
import subprocess
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EffectAckHttpTerminalV2Tests(unittest.TestCase):
    def test_http_draft_binds_current_structured_fields_and_causality(self) -> None:
        path = ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml"
        ET.parse(path)
        text = path.read_text(encoding="utf-8")
        self.assertIn('docName="draft-lohmann-qikvrt-effect-ack-http-00"', text)
        self.assertIn('reference.RFC.9651.xml', text)
        self.assertNotIn('reference.RFC.8941.xml', text)
        self.assertIn("Causality, Serialization and Metagrammar Binding", text)
        self.assertIn("MUST NOT infer causal authorization from message order", text)
        self.assertIn("wall-clock order", text)
        self.assertIn("successful status code alone", text)
        self.assertIn("deterministic topological order", text)
        self.assertIn("MUST preserve all bound non-commutative effects", text)
        self.assertIn("Transport acknowledgement MUST NOT be substituted", text)
        self.assertIn("rendering MUST remain observation-only", text)
        self.assertIn("MUST NOT enable Prepare or Commit", text)

    def test_v2_policy_is_fail_closed(self) -> None:
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V2.json").read_text(encoding="utf-8"))
        inv = policy["invariants"]
        self.assertTrue(inv["causality_is_not_sequence"])
        self.assertTrue(inv["serialization_is_topological_projection"])
        self.assertTrue(inv["parallel_projection_preserves_causal_edges"])
        self.assertTrue(inv["imported_proxy_frame_is_display_only"])
        self.assertTrue(inv["imported_proxy_frame_cannot_prepare"])
        self.assertTrue(inv["imported_proxy_frame_cannot_commit"])
        self.assertTrue(inv["watchdog_alarm_reinitialized_on_install_startup"])
        self.assertEqual(policy["http"]["structured_fields_rfc"], 9651)
        self.assertTrue(policy["http"]["html_discovery_is_advisory"])
        self.assertFalse(policy["completion_claims"]["PASS"])
        self.assertFalse(policy["completion_claims"]["FINAL_PASS"])
        self.assertFalse(policy["completion_claims"]["EFFECT_ACK_DONE"])

    def test_firefox_proxy_is_loaded_and_display_only(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        scripts = manifest["content_scripts"][0]["js"]
        self.assertEqual(scripts, ["content.js", "proxy.js"])
        proxy = (ROOT / "browser/firefox/qikvrt-terminal/proxy.js").read_text(encoding="utf-8")
        for required in (
            'FRAME_KIND = "QIKVRT_TERMINAL_FRAME"',
            'FRAME_SCHEMA = "qikvrt_terminal_frame_v1"',
            'ORDINARY_RELEASE_REQUIRES = "VALID_EFFECT_ACK_DONE"',
            'event.source !== window',
            'event.origin !== location.origin',
            'MAX_FRAME_BYTES = 256 * 1024',
            'display_only: true',
            'proxy_frame_can_prepare: false',
            'proxy_frame_can_commit: false',
            'commit.disabled = true',
        ):
            self.assertIn(required, proxy)
        self.assertNotIn('runtime.sendMessage', proxy)
        self.assertNotIn('PREPARE_EFFECT', proxy)
        self.assertNotIn('COMMIT_EFFECT', proxy)

    def test_firefox_proxy_executes_canonical_validation_fail_closed(self) -> None:
        proxy_path = ROOT / "browser/firefox/qikvrt-terminal/proxy.js"
        harness = textwrap.dedent(
            r"""
            const assert = require("assert");
            const fs = require("fs");
            const vm = require("vm");
            const proxyPath = process.argv[1];
            let listener = null;
            const output = {textContent: ""};
            const status = {textContent: "", dataset: {}};
            const commit = {disabled: false};
            const host = {
              querySelector(selector) {
                if (selector === "[data-role=output]") return output;
                if (selector === "[data-role=status]") return status;
                if (selector === "[data-act=commit]") return commit;
                return null;
              },
              dispatchEvent() {}
            };
            global.window = {addEventListener(name, fn) { if (name === "message") listener = fn; }};
            global.location = {origin: "https://github.com"};
            global.document = {getElementById(id) { return id === "qikvrt-ai-terminal-host" ? host : null; }};
            global.CustomEvent = function(type, init) { this.type = type; this.detail = init.detail; };
            vm.runInThisContext(fs.readFileSync(proxyPath, "utf8"), {filename: proxyPath});
            assert(listener, "proxy message listener not installed");

            function clone(value) { return JSON.parse(JSON.stringify(value)); }
            function send(frame) {
              output.textContent = "";
              status.textContent = "";
              status.dataset = {};
              commit.disabled = false;
              listener({
                source: window,
                origin: location.origin,
                data: {kind: "QIKVRT_TERMINAL_FRAME", frame}
              });
              return {state: status.dataset.state, text: output.textContent, disabled: commit.disabled};
            }
            const valid = {
              schema: "qikvrt_terminal_frame_v1",
              observed_at: "2026-08-18T03:00:00Z",
              source: {
                repository: "Goldkelch/qik-vrt",
                ref: "refs/heads/main",
                head: "0123456789abcdef0123456789abcdef01234567",
                tree: "89abcdef0123456789abcdef0123456789abcdef"
              },
              terminal_semantics: {
                rendering_is_authorization: false,
                ordinary_release_requires: "VALID_EFFECT_ACK_DONE"
              },
              effect_ack: {state: "EFFECT_ACK_CONTINUE", record_hash: "abc123"}
            };

            const accepted = send(valid);
            assert.strictEqual(accepted.state, "OBSERVE");
            assert.strictEqual(accepted.disabled, true);
            const rendered = JSON.parse(accepted.text);
            assert.strictEqual(rendered.schema, "qikvrt_terminal_frame_v1");
            assert.strictEqual(rendered.observed_at, valid.observed_at);
            assert.deepStrictEqual(rendered.source, valid.source);
            assert.strictEqual(rendered.effect_ack.record_hash, "abc123");
            assert.strictEqual(rendered.terminal_semantics.rendering_is_authorization, false);
            assert.strictEqual(rendered.terminal_semantics.ordinary_release_requires, "VALID_EFFECT_ACK_DONE");
            assert.strictEqual(rendered.terminal_semantics.proxy_frame_can_prepare, false);
            assert.strictEqual(rendered.terminal_semantics.proxy_frame_can_commit, false);
            assert.strictEqual(rendered.terminal_semantics.proxy_effect_transaction, "SEPARATE_EFFECT_ACK_TRANSACTION_REQUIRED");
            assert.strictEqual(rendered.proxy.display_only, true);

            const invalid = [];
            let x;
            x = clone(valid); delete x.observed_at; invalid.push(x);
            x = clone(valid); x.observed_at = "not-a-date"; invalid.push(x);
            x = clone(valid); x.source.repository = ""; invalid.push(x);
            x = clone(valid); x.source.ref = ""; invalid.push(x);
            x = clone(valid); delete x.source.head; invalid.push(x);
            x = clone(valid); delete x.source.tree; invalid.push(x);
            x = clone(valid); x.source.head = "ABCDEF"; invalid.push(x);
            x = clone(valid); delete x.terminal_semantics; invalid.push(x);
            x = clone(valid); x.terminal_semantics.rendering_is_authorization = true; invalid.push(x);
            x = clone(valid); x.terminal_semantics.ordinary_release_requires = "VALID_EFFECT_ACK_DONE_FROM_SEPARATE_EFFECT_TRANSACTION"; invalid.push(x);
            x = clone(valid); x.workflows = {padding: "x".repeat(300 * 1024)}; invalid.push(x);

            for (const frame of invalid) {
              const rejected = send(frame);
              assert.strictEqual(rejected.state, "HOLD");
              assert.strictEqual(rejected.disabled, true);
              const evidence = JSON.parse(rejected.text);
              assert.strictEqual(evidence.state, "HOLD");
              assert.strictEqual(evidence.ordinary_release, false);
            }
            """
        )
        subprocess.run(["node", "-e", harness, str(proxy_path)], check=True, cwd=ROOT)

    def test_watchdog_reinitializes_after_firefox_restart(self) -> None:
        background = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
        self.assertIn("browser.runtime.onInstalled.addListener", background)
        self.assertIn("browser.runtime.onStartup.addListener", background)
        self.assertIn("browser.alarms.get(WATCHDOG_ALARM)", background)
        self.assertIn("periodInMinutes: WATCHDOG_PERIOD_MINUTES", background)


if __name__ == "__main__":
    unittest.main()
