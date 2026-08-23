/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
(() => {
  "use strict";
  const STATES = new Set(["EFFECT_NACK", "EFFECT_ACK_CONTINUE", "EFFECT_ACK_DONE", "EFFECT_ACK_ISOLATE", "EFFECT_ACK_BLOCK"]);
  const SHA = /^sha256:[0-9a-f]{64}$/;
  const BOOLS = ["transport_ack", "origin_checked", "context_checked", "semantics_reconstructed", "effect_anticipated", "risk_classified", "responsibility_assigned", "connection_decided", "policy_allows_release", "ordinary_release"];
  const ARRAYS = ["reasons", "evidence_refs", "required_evidence_refs", "open_questions", "next_required_checks"];
  function fail(reason) { return {ok: false, reason}; }
  function canonical(value) {
    if (value === null || typeof value === "boolean" || Number.isInteger(value)) return JSON.stringify(value);
    if (typeof value === "string") return JSON.stringify(value.normalize("NFC"));
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    if (typeof value === "object") return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key.normalize("NFC"))}:${canonical(value[key])}`).join(",")}}`;
    throw new Error("non-canonical JSON value");
  }
  async function sha256Hex(text) {
    const bytes = new TextEncoder().encode(text);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  }
  async function verify(protocol) {
    if (!protocol || typeof protocol !== "object") return fail("responsibility protocol missing");
    if (protocol.schema !== "qikvrt_responsibility_protocol_v1") return fail("unsupported protocol schema");
    if (!STATES.has(protocol.state)) return fail("unknown Effect-Ack state");
    if (!Number.isInteger(protocol.protocol_version) || protocol.protocol_version < 1) return fail("invalid protocol version");
    if (protocol.protocol_id !== `${protocol.protocol_root_id}:v${protocol.protocol_version}`) return fail("protocol id mismatch");
    if (!SHA.test(protocol.protocol_hash || "")) return fail("invalid protocol hash");
    if (protocol.input_hash !== "UNAVAILABLE" && !SHA.test(protocol.input_hash || "")) return fail("invalid input hash");
    for (const name of BOOLS) if (typeof protocol[name] !== "boolean") return fail(`${name} is not boolean`);
    for (const name of ARRAYS) if (!Array.isArray(protocol[name]) || protocol[name].some(item => typeof item !== "string")) return fail(`${name} is not a string array`);
    const expectedRelease = protocol.state === "EFFECT_ACK_DONE";
    if (protocol.ordinary_release !== expectedRelease) return fail("ordinary release invariant violated");
    for (const required of protocol.required_evidence_refs) if (!SHA.test(required) || !protocol.evidence_refs.includes(required)) return fail("required evidence absent");
    const projection = {...protocol};
    delete projection.created_utc;
    delete projection.protocol_hash;
    const calculated = `sha256:${await sha256Hex(canonical(projection))}`;
    if (calculated !== protocol.protocol_hash) return fail("protocol hash mismatch");
    if (expectedRelease) {
      const gates = [protocol.transport_ack, SHA.test(protocol.input_hash), protocol.origin_checked, protocol.context_checked, protocol.semantics_reconstructed, protocol.effect_anticipated, protocol.risk_classified, protocol.risk_level !== "UNKNOWN", protocol.responsibility_assigned, Boolean(protocol.responsibility_owner), protocol.connection_decided, protocol.connection_decision === "RELEASE", protocol.policy_allows_release, protocol.open_questions.length === 0, protocol.next_required_checks.length === 0];
      if (gates.some(value => value !== true)) return fail("false EFFECT_ACK_DONE");
    }
    return {ok: true, state: protocol.state, protocol_hash: protocol.protocol_hash};
  }
  globalThis.QIKVRTProtocol = Object.freeze({verify, canonical});
})();
