(() => {
  "use strict";

  const AUTHORITY = "Goldkelch/qik-vrt";
  const ADAPTER = "QIKVRT_FIREFOX_TERMINAL_PROXY_V1";
  const DELIVERY_LEDGER = "state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json";
  const AUTHORIZED_EFFECTS = new Set([
    "AUTHORIZED_EXTERNAL_PUBLICATION_EFFECT",
    "AUTHORIZED_EXTERNAL_WEB_EFFECT"
  ]);
  const REQUESTS = Object.freeze({
    arxiv: {
      id: "ARXIV_PLANCK_TICK_GAP_LAW_V1",
      path: "state/delivery/requests/ARXIV_PLANCK_TICK_GAP_LAW_V1.json",
      operation: "AUTHENTICATED_ARXIV_WEB_SUBMISSION"
    },
    wikipedia: {
      id: "WIKIPEDIA_LEAN_LAKE_PROOF_STATUS_V1",
      path: "state/delivery/requests/WIKIPEDIA_LEAN_LAKE_PROOF_STATUS_V1.json",
      operation: "TRANSPARENT_COI_EDIT_REQUEST"
    }
  });
  const PANEL_ID = "qikvrt-authenticated-delivery-terminal";
  const PENDING_KEY = "qikvrt-authenticated-delivery-pending-v1";
  const RECEIPT_KEY = "qikvrtAuthenticatedDeliveryReadbackV1";
  const TOKEN_TTL_MS = 10 * 60 * 1000;

  let prepared = null;

  function platformForHost(hostname) {
    const host = String(hostname || "").toLowerCase();
    if (host === "arxiv.org" || host.endsWith(".arxiv.org")) return "arxiv";
    if (host.endsWith(".wikipedia.org") || host === "auth.wikimedia.org" || host.endsWith(".wikimedia.org")) return "wikipedia";
    return null;
  }

  function fail(reason) {
    return {ok: false, state: "HOLD", reason, ordinary_release: false};
  }

  async function github(path) {
    const response = await fetch(`https://api.github.com/repos/${AUTHORITY}${path}`, {
      method: "GET",
      credentials: "omit",
      cache: "no-store",
      headers: {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
      }
    });
    if (!response.ok) throw new Error(`github ${response.status}`);
    return response.json();
  }

  async function observeAuthority() {
    const ref = await github("/git/ref/heads/main");
    const head = ref && ref.object && ref.object.sha;
    if (!/^[0-9a-f]{40}$/.test(head || "")) throw new Error("main head unavailable");
    const commit = await github(`/git/commits/${head}`);
    const tree = commit && commit.tree && commit.tree.sha;
    if (!/^[0-9a-f]{40}$/.test(tree || "")) throw new Error("main tree unavailable");
    return {head, tree};
  }

  function decodeBase64Utf8(value) {
    const binary = atob(String(value || "").replace(/\n/g, ""));
    const bytes = Uint8Array.from(binary, ch => ch.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  }

  async function fetchJsonAtExactHead(path, authority) {
    const encodedPath = path.split("/").map(encodeURIComponent).join("/");
    const file = await github(`/contents/${encodedPath}?ref=${authority.head}`);
    if (!file || file.type !== "file" || file.encoding !== "base64") throw new Error(`bound file unavailable: ${path}`);
    return JSON.parse(decodeBase64Utf8(file.content));
  }

  async function fetchBoundRequest(platform, authority) {
    const spec = REQUESTS[platform];
    if (!spec) throw new Error("unsupported delivery platform");
    const request = await fetchJsonAtExactHead(spec.path, authority);
    if (request.schema !== "qikvrt_external_delivery_request_v1") throw new Error("delivery schema mismatch");
    if (request.id !== spec.id || request.platform !== platform) throw new Error("delivery subject mismatch");
    if (!request.authority || !AUTHORIZED_EFFECTS.has(request.authority.authorization)) throw new Error("external effect not authorized");
    if (!request.operation || request.operation.type !== spec.operation) throw new Error("operation mismatch");
    if (request.operation.adapter && request.operation.adapter !== ADAPTER) throw new Error("request adapter mismatch");
    if (!request.preconditions || request.preconditions.exact_main_reobservation_required !== true) throw new Error("exact-main reobservation not required by request");
    if (request.preconditions.predecessor_evidence_transfer !== false) throw new Error("predecessor evidence boundary missing");
    if (!request.effect_ack || request.effect_ack.required !== true || request.effect_ack.readback_required !== true) throw new Error("authoritative readback contract missing");

    const ledger = await fetchJsonAtExactHead(DELIVERY_LEDGER, authority);
    if (ledger.schema !== "qikvrt_active_delivery_obligations_v1" || ledger.repository !== AUTHORITY) throw new Error("delivery ledger mismatch");
    const obligations = Array.isArray(ledger.obligations) ? ledger.obligations : [];
    const obligation = obligations.find(item =>
      item && item.delivery &&
      item.delivery.platform === platform &&
      item.delivery.request === spec.path &&
      item.delivery.adapter === ADAPTER
    );
    if (!obligation) throw new Error("bound delivery obligation unavailable");
    if (!obligation.main_reobservation || obligation.main_reobservation.required !== true || obligation.main_reobservation.binding !== "EXACT_MAIN_HEAD") throw new Error("delivery obligation exact-main binding missing");
    if (obligation.delivery.effect_ack_required !== true) throw new Error("delivery obligation EFFECT_ACK missing");
    return request;
  }

  function canonicalize(value) {
    if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
    if (value && typeof value === "object") {
      return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
  }

  async function sha256(value) {
    const bytes = new TextEncoder().encode(typeof value === "string" ? value : canonicalize(value));
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  }

  function isSecretControl(control) {
    const type = String(control.type || "").toLowerCase();
    const autocomplete = String(control.autocomplete || "").toLowerCase();
    const name = String(control.name || control.id || "").toLowerCase();
    return type === "password" || type === "file" || autocomplete.includes("password") || /token|secret|otp|totp|captcha/.test(name);
  }

  async function formSnapshot(form) {
    const fields = [];
    let secretFieldsPresent = false;
    for (const control of Array.from(form.elements || [])) {
      if (!control || !control.tagName) continue;
      const descriptor = {
        tag: control.tagName.toLowerCase(),
        type: String(control.type || "").toLowerCase(),
        name: String(control.name || ""),
        id: String(control.id || ""),
        required: Boolean(control.required),
        disabled: Boolean(control.disabled)
      };
      if (isSecretControl(control)) {
        secretFieldsPresent = true;
        descriptor.secret = true;
        descriptor.value_sha256 = null;
      } else {
        descriptor.secret = false;
        descriptor.value_sha256 = await sha256(String(control.value || ""));
      }
      fields.push(descriptor);
    }
    const action = new URL(form.action || location.href, location.href);
    return {
      page_origin: location.origin,
      page_path: location.pathname,
      method: String(form.method || "get").toUpperCase(),
      action_origin: action.origin,
      action_path: action.pathname,
      fields,
      secret_fields_present: secretFieldsPresent
    };
  }

  function candidateForms() {
    return Array.from(document.forms || []).filter(form => {
      try {
        const action = new URL(form.action || location.href, location.href);
        return action.origin === location.origin && Boolean(form.querySelector('button[type="submit"], input[type="submit"], button:not([type])'));
      } catch (_) {
        return false;
      }
    });
  }

  function selectForm() {
    const forms = candidateForms();
    if (!forms.length) return null;
    const visible = forms.find(form => form.getClientRects().length > 0);
    return visible || forms[0];
  }

  function randomToken() {
    const bytes = crypto.getRandomValues(new Uint8Array(24));
    return Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
  }

  async function prepare() {
    const platform = platformForHost(location.hostname);
    if (!platform) return fail("page outside authenticated delivery allowlist");
    const form = selectForm();
    if (!form) return fail("no same-origin submit form observed");
    const authority = await observeAuthority();
    const request = await fetchBoundRequest(platform, authority);
    const snapshot = await formSnapshot(form);
    const formDigest = await sha256(snapshot);
    const requestDigest = await sha256(request);
    prepared = {
      schema: "qikvrt_authenticated_web_prepare_v1",
      token: randomToken(),
      expires_at: Date.now() + TOKEN_TTL_MS,
      platform,
      request_id: request.id,
      request_digest: requestDigest,
      authority,
      page: {origin: location.origin, path: location.pathname},
      form_digest: formDigest,
      ordinary_release: false,
      completion_claims: {PASS: false, FINAL_PASS: false, EFFECT_ACK_DONE: false}
    };
    return {...prepared, token: prepared.token};
  }

  async function commit() {
    if (!prepared) return fail("prepare required");
    if (Date.now() > prepared.expires_at) {
      prepared = null;
      return fail("prepare token expired");
    }
    const platform = platformForHost(location.hostname);
    if (platform !== prepared.platform) return fail("platform drift");
    if (location.origin !== prepared.page.origin || location.pathname !== prepared.page.path) return fail("page drift");
    const authority = await observeAuthority();
    if (authority.head !== prepared.authority.head || authority.tree !== prepared.authority.tree) return fail("trusted main drift; reprepare required");
    const request = await fetchBoundRequest(platform, authority);
    if (request.id !== prepared.request_id || await sha256(request) !== prepared.request_digest) return fail("delivery request drift");
    const form = selectForm();
    if (!form) return fail("submit form disappeared");
    const snapshot = await formSnapshot(form);
    if (await sha256(snapshot) !== prepared.form_digest) return fail("form changed after prepare");
    const submit = form.querySelector('button[type="submit"], input[type="submit"], button:not([type])');
    if (!submit || submit.disabled) return fail("submit control unavailable");

    const pending = {
      schema: "qikvrt_authenticated_web_pending_readback_v1",
      platform,
      request_id: request.id,
      authority,
      committed_at: new Date().toISOString(),
      pre_effect_url: location.href,
      completion_claims: {PASS: false, FINAL_PASS: false, EFFECT_ACK_DONE: false}
    };
    sessionStorage.setItem(PENDING_KEY, JSON.stringify(pending));
    prepared = null;
    submit.click();
    return {ok: true, state: "COMMIT_DISPATCHED", ordinary_release: false, readback_required: true};
  }

  function extractArxivReadback(text) {
    const urlMatch = location.href.match(/\/submit\/(\d+)/i);
    const textMatch = text.match(/(?:submission\s*(?:id|identifier)|identifier)\s*[:#]?\s*([0-9]{5,})/i);
    const statusMatch = text.match(/\b(submitted|processing|incomplete|on hold|scheduled|announced|deleted|expired)\b/i);
    return {
      submission_id: (urlMatch && urlMatch[1]) || (textMatch && textMatch[1]) || null,
      submission_status: statusMatch ? statusMatch[1].toLowerCase() : null
    };
  }

  function extractWikipediaReadback(text) {
    const params = new URL(location.href).searchParams;
    const oldid = params.get("oldid") || params.get("diff");
    const textMatch = text.match(/(?:revision|oldid)\D{0,12}(\d{5,})/i);
    return {
      revision_id: (/^\d+$/.test(oldid || "") ? oldid : null) || (textMatch && textMatch[1]) || null,
      page_title: document.querySelector("h1")?.textContent?.trim() || document.title || null
    };
  }

  async function reobservePending() {
    const raw = sessionStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    let pending;
    try { pending = JSON.parse(raw); } catch (_) { sessionStorage.removeItem(PENDING_KEY); return null; }
    const platform = platformForHost(location.hostname);
    if (!pending || pending.schema !== "qikvrt_authenticated_web_pending_readback_v1" || pending.platform !== platform) return null;
    const authority = await observeAuthority();
    if (authority.head !== pending.authority.head || authority.tree !== pending.authority.tree) return fail("trusted main changed before post-effect readback");
    await fetchBoundRequest(platform, authority);
    const text = String(document.body?.innerText || "").slice(0, 200000);
    const observed = platform === "arxiv" ? extractArxivReadback(text) : extractWikipediaReadback(text);
    const receipt = {
      schema: "qikvrt_authenticated_web_readback_v1",
      platform,
      request_id: pending.request_id,
      authority,
      committed_at: pending.committed_at,
      observed_at: new Date().toISOString(),
      post_effect_url: location.href,
      observed,
      authoritative_subject_observed: platform === "arxiv" ? Boolean(observed.submission_id && observed.submission_status) : Boolean(observed.revision_id),
      completion_claims: {PASS: false, FINAL_PASS: false, EFFECT_ACK_DONE: false}
    };
    await browser.storage.local.set({[RECEIPT_KEY]: receipt});
    if (receipt.authoritative_subject_observed) sessionStorage.removeItem(PENDING_KEY);
    return receipt;
  }

  function renderStatus(panel, value) {
    const status = panel.querySelector("[data-qikvrt-status]");
    status.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function installPanel() {
    if (document.getElementById(PANEL_ID)) return;
    const panel = document.createElement("aside");
    panel.id = PANEL_ID;
    panel.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:2147483647;width:360px;max-height:55vh;overflow:auto;background:#111;color:#eee;border:1px solid #777;border-radius:8px;padding:10px;font:12px/1.4 monospace;box-shadow:0 3px 18px #0008";
    panel.innerHTML = '<strong>QIKVRT authenticated delivery</strong><div style="margin:8px 0"><button data-qikvrt-prepare>Prepare</button> <button data-qikvrt-commit disabled>Commit exact prepared form</button> <button data-qikvrt-readback>Readback</button></div><pre data-qikvrt-status style="white-space:pre-wrap;word-break:break-word;margin:0">OBSERVE</pre>';
    document.documentElement.appendChild(panel);
    const prepareButton = panel.querySelector("[data-qikvrt-prepare]");
    const commitButton = panel.querySelector("[data-qikvrt-commit]");
    const readbackButton = panel.querySelector("[data-qikvrt-readback]");
    prepareButton.addEventListener("click", async () => {
      try {
        const result = await prepare();
        commitButton.disabled = !result || result.ok === false;
        renderStatus(panel, result);
      } catch (error) {
        commitButton.disabled = true;
        renderStatus(panel, fail(error.message));
      }
    });
    commitButton.addEventListener("click", async () => {
      commitButton.disabled = true;
      try { renderStatus(panel, await commit()); }
      catch (error) { renderStatus(panel, fail(error.message)); }
    });
    readbackButton.addEventListener("click", async () => {
      try { renderStatus(panel, await reobservePending() || "NO_PENDING_EFFECT"); }
      catch (error) { renderStatus(panel, fail(error.message)); }
    });
  }

  installPanel();
  reobservePending().then(receipt => {
    const panel = document.getElementById(PANEL_ID);
    if (panel && receipt) renderStatus(panel, receipt);
  }).catch(() => undefined);
})();
