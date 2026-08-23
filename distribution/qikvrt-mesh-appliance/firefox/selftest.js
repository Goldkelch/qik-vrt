/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
(async () => {
  "use strict";
  const node = document.getElementById("qikvrt-selftest");
  try {
    const payload = new TextEncoder().encode("QIK-VRT Mesh Appliance browser selftest");
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", payload)), b => b.toString(16).padStart(2, "0")).join("");
    const evidence = `sha256:${hash}`;
    const request = {
      protocol_root_id: "qikvrt:appliance:browser-selftest",
      input_id: "firefox-esr-adapter-selftest",
      payload_b64: btoa(String.fromCharCode(...payload)),
      declared_input_hash: evidence,
      transport_ack: true,
      origin_checked: true,
      context_checked: true,
      semantics_reconstructed: true,
      effect_anticipated: true,
      risk_classified: true,
      risk_level: "LOW",
      responsibility_assigned: true,
      responsibility_owner: "QIKVRT_MESH_APPLIANCE",
      connection_decision: "RELEASE",
      policy_allows_release: true,
      evidence_refs: [evidence],
      required_evidence_refs: [evidence],
      open_questions: [],
      next_required_checks: []
    };
    const response = await fetch("http://127.0.0.1:8771/v1/evaluate", {
      method: "POST",
      headers: {"Content-Type": "application/json", "Effect-Ack-Request": "v=1, mode=evaluate"},
      body: JSON.stringify(request),
      cache: "no-store"
    });
    const record = await response.json();
    const verification = await globalThis.QIKVRTProtocol.verify(record.responsibility_protocol);
    if (!response.ok || !verification.ok || record.state !== "EFFECT_ACK_DONE" || record.ordinary_release !== true) throw new Error(verification.reason || `unexpected state ${record.state}`);
    node.dataset.state = "EFFECT_ACK_DONE";
    node.textContent = JSON.stringify({
      schema: "qikvrt_firefox_effect_ack_selftest_v1",
      browser_execution_observed: true,
      protocol_validation_observed: true,
      state: record.state,
      protocol_hash: record.responsibility_protocol.protocol_hash,
      external_effect: "NONE"
    }, null, 2);
  } catch (error) {
    node.dataset.state = "HOLD";
    node.textContent = JSON.stringify({
      schema: "qikvrt_firefox_effect_ack_selftest_v1",
      state: "HOLD",
      reason: String(error),
      external_effect: "NONE"
    }, null, 2);
  }
})();
