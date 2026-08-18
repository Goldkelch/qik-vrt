(() => {
  "use strict";

  const MAX_FRAME_BYTES = 256 * 1024;
  const FRAME_KIND = "QIKVRT_TERMINAL_FRAME";
  const FRAME_SCHEMA = "qikvrt_terminal_frame_v1";
  const ORDINARY_RELEASE_REQUIRES = "VALID_EFFECT_ACK_DONE";
  const SHA40 = /^[0-9a-f]{40}$/;
  const RFC3339_DATE_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

  function plainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function nonEmptyString(value) {
    return typeof value === "string" && value.length > 0;
  }

  function validObservedAt(value) {
    return nonEmptyString(value) && RFC3339_DATE_TIME.test(value) && !Number.isNaN(Date.parse(value));
  }

  function normalizeFrame(candidate) {
    if (!plainObject(candidate) || candidate.schema !== FRAME_SCHEMA) {
      throw new Error("proxy frame schema mismatch");
    }
    if (!validObservedAt(candidate.observed_at)) {
      throw new Error("proxy frame observed_at invalid");
    }

    const source = candidate.source;
    if (!plainObject(source) || !nonEmptyString(source.repository) || !nonEmptyString(source.ref)) {
      throw new Error("proxy frame source binding missing");
    }
    if (!SHA40.test(source.head)) {
      throw new Error("proxy frame head invalid");
    }
    if (!SHA40.test(source.tree)) {
      throw new Error("proxy frame tree invalid");
    }

    const semantics = candidate.terminal_semantics;
    if (!plainObject(semantics) || semantics.rendering_is_authorization !== false) {
      throw new Error("proxy frame rendering authorization invariant invalid");
    }
    if (semantics.ordinary_release_requires !== ORDINARY_RELEASE_REQUIRES) {
      throw new Error("proxy frame ordinary release invariant invalid");
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
      ...frame.terminal_semantics,
      rendering_is_authorization: false,
      ordinary_release_requires: ORDINARY_RELEASE_REQUIRES,
      proxy_frame_can_prepare: false,
      proxy_frame_can_commit: false,
      proxy_effect_transaction: "SEPARATE_EFFECT_ACK_TRANSACTION_REQUIRED"
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
