(() => {
  "use strict";

  const MAX_FRAME_BYTES = 256 * 1024;
  const FRAME_KIND = "QIKVRT_TERMINAL_FRAME";
  const FRAME_SCHEMA = "qikvrt_terminal_frame_v1";
  const SHA40 = /^[0-9a-f]{40}$/;

  function plainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function normalizeFrame(candidate) {
    if (!plainObject(candidate) || candidate.schema !== FRAME_SCHEMA) {
      throw new Error("proxy frame schema mismatch");
    }
    const source = candidate.source;
    if (!plainObject(source) || typeof source.repository !== "string" || typeof source.ref !== "string") {
      throw new Error("proxy frame source binding missing");
    }
    if (source.head !== undefined && source.head !== null && !SHA40.test(source.head)) {
      throw new Error("proxy frame head invalid");
    }
    if (source.tree !== undefined && source.tree !== null && !SHA40.test(source.tree)) {
      throw new Error("proxy frame tree invalid");
    }

    const encoded = JSON.stringify(candidate);
    if (new TextEncoder().encode(encoded).byteLength > MAX_FRAME_BYTES) {
      throw new Error("proxy frame exceeds bounded display size");
    }

    const frame = JSON.parse(encoded);
    frame.proxy = {
      ...(plainObject(frame.proxy) ? frame.proxy : {}),
      renderer: "QIKVRT_FIREFOX_TERMINAL_PROXY_V2",
      imported_at: new Date().toISOString(),
      display_only: true
    };
    frame.terminal_semantics = {
      ...(plainObject(frame.terminal_semantics) ? frame.terminal_semantics : {}),
      rendering_is_authorization: false,
      proxy_frame_can_prepare: false,
      proxy_frame_can_commit: false,
      ordinary_release_requires: "VALID_EFFECT_ACK_DONE_FROM_SEPARATE_EFFECT_TRANSACTION"
    };
    return frame;
  }

  function renderFrame(frame) {
    const host = document.getElementById("qikvrt-ai-terminal-host");
    if (!host) throw new Error("terminal host unavailable");
    const output = host.querySelector("[data-role=output]");
    const status = host.querySelector("[data-role=status]");
    const commit = host.querySelector("[data-act=commit]");
    if (!output || !status || !commit) throw new Error("terminal render surface incomplete");

    // Imported frames are observation/rendering only. Invalidate any visible
    // commit affordance so a rendered third-party state can never promote
    // itself into the separately gated Prepare/Commit transaction.
    commit.disabled = true;
    output.textContent = JSON.stringify(frame, null, 2);
    status.textContent = "PROXY · DISPLAY_ONLY";
    status.dataset.state = "OBSERVE";
    host.dispatchEvent(new CustomEvent("qikvrt-proxy-frame-rendered", {
      detail: {schema: frame.schema, source: frame.source, display_only: true}
    }));
  }

  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data;
    if (!plainObject(message) || message.kind !== FRAME_KIND) return;
    try {
      renderFrame(normalizeFrame(message.frame));
    } catch (error) {
      const host = document.getElementById("qikvrt-ai-terminal-host");
      const output = host && host.querySelector("[data-role=output]");
      const status = host && host.querySelector("[data-role=status]");
      const commit = host && host.querySelector("[data-act=commit]");
      if (commit) commit.disabled = true;
      if (output) output.textContent = JSON.stringify({state: "HOLD", reason: error.message, ordinary_release: false}, null, 2);
      if (status) {
        status.textContent = `HOLD · ${error.message}`;
        status.dataset.state = "HOLD";
      }
    }
  });
})();
