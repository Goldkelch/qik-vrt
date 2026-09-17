(() => {
  "use strict";
  const AUTHORITY = "Goldkelch/qik-vrt";
  const REQUEST_PATH = "state/delivery/requests/ARXIV_ACCOUNT_PROVISIONING_V1.json";
  const LEDGER_PATH = "state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json";
  const ADAPTER = "QIKVRT_FIREFOX_TERMINAL_PROXY_V1";
  const AUTHORIZATION = "AUTHORIZED_EXTERNAL_ACCOUNT_PROVISIONING_EFFECT";
  const OPERATION = "AUTHENTICATED_ACCOUNT_PROVISIONING";
  const PANEL_ID = "qikvrt-account-provisioning-terminal";
  let prepared = null;

  const decode = value => new TextDecoder().decode(Uint8Array.from(atob(String(value || "").replace(/\n/g, "")), c => c.charCodeAt(0)));
  async function github(path) {
    const r = await fetch(`https://api.github.com/repos/${AUTHORITY}${path}`, {credentials:"omit", cache:"no-store", headers:{Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}});
    if (!r.ok) throw new Error(`github ${r.status}`);
    return r.json();
  }
  async function authority() {
    const ref = await github("/git/ref/heads/main");
    const head = ref?.object?.sha;
    const commit = await github(`/git/commits/${head}`);
    const tree = commit?.tree?.sha;
    if (!/^[0-9a-f]{40}$/.test(head || "") || !/^[0-9a-f]{40}$/.test(tree || "")) throw new Error("exact Main unavailable");
    return {head, tree};
  }
  async function jsonAt(path, a) {
    const p = path.split("/").map(encodeURIComponent).join("/");
    const f = await github(`/contents/${p}?ref=${a.head}`);
    if (f?.type !== "file" || f.encoding !== "base64") throw new Error(`bound file unavailable: ${path}`);
    return JSON.parse(decode(f.content));
  }
  function secret(c) {
    const t = String(c.type || "").toLowerCase();
    const n = String(c.name || c.id || "").toLowerCase();
    const ac = String(c.autocomplete || "").toLowerCase();
    return t === "password" || t === "file" || ac.includes("password") || /token|secret|otp|totp|captcha/.test(n);
  }
  async function bind(a) {
    const req = await jsonAt(REQUEST_PATH, a);
    if (req.schema !== "qikvrt_external_delivery_request_v1" || req.platform !== "arxiv") throw new Error("request subject mismatch");
    if (req.authority?.authorization !== AUTHORIZATION) throw new Error("account provisioning effect not authorized");
    if (req.operation?.type !== OPERATION || req.operation?.adapter !== ADAPTER) throw new Error("operation/adapter mismatch");
    if (req.preconditions?.exact_main_reobservation_required !== true || req.preconditions?.predecessor_evidence_transfer !== false || req.preconditions?.existing_account_state_must_be_observed !== true) throw new Error("precondition boundary missing");
    const ledger = await jsonAt(LEDGER_PATH, a);
    const obligation = (ledger.obligations || []).find(x => x?.delivery?.request === REQUEST_PATH && x?.delivery?.adapter === ADAPTER);
    if (!obligation || obligation.main_reobservation?.binding !== "EXACT_MAIN_HEAD" || obligation.delivery?.effect_ack_required !== true) throw new Error("bound account obligation unavailable");
    return req;
  }
  function form() {
    return Array.from(document.forms || []).find(f => {
      try { return new URL(f.action || location.href, location.href).origin === location.origin && f.getClientRects().length > 0; } catch (_) { return false; }
    }) || null;
  }
  async function digestForm(f) {
    const fields = Array.from(f.elements || []).map(c => ({name:String(c.name || ""), type:String(c.type || "").toLowerCase(), required:Boolean(c.required), secret:secret(c), value:secret(c) ? null : String(c.value || "")}));
    const data = new TextEncoder().encode(JSON.stringify(fields));
    const d = await crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(d), b => b.toString(16).padStart(2,"0")).join("");
  }
  async function prepare() {
    if (!(location.hostname === "arxiv.org" || location.hostname.endsWith(".arxiv.org"))) throw new Error("outside arXiv");
    const a = await authority();
    const req = await bind(a);
    const f = form();
    if (!f) throw new Error("account form not observed");
    prepared = {a, request_id:req.id, path:location.pathname, digest:await digestForm(f), expires:Date.now()+600000};
    return {state:"PREPARED", request_id:req.id, authority:a, secret_values_persisted:false, completion_claims:{PASS:false,FINAL_PASS:false,EFFECT_ACK_DONE:false}};
  }
  async function commit() {
    if (!prepared || Date.now() > prepared.expires) throw new Error("fresh prepare required");
    const a = await authority();
    if (a.head !== prepared.a.head || a.tree !== prepared.a.tree || location.pathname !== prepared.path) throw new Error("subject drift; reprepare required");
    await bind(a);
    const f = form();
    if (!f || await digestForm(f) !== prepared.digest) throw new Error("form drift; reprepare required");
    const missingSecret = Array.from(f.elements || []).some(c => secret(c) && c.required && !c.value);
    if (missingSecret) throw new Error("required browser/human-owned secret input missing");
    const submit = f.querySelector('button[type="submit"],input[type="submit"],button:not([type])');
    if (!submit || submit.disabled) throw new Error("submit unavailable");
    sessionStorage.setItem("qikvrt-account-provisioning-pending-v1", JSON.stringify({schema:"qikvrt_account_provisioning_pending_v1", authority:a, request_id:prepared.request_id, committed_at:new Date().toISOString()}));
    prepared = null;
    submit.click();
    return {state:"COMMIT_DISPATCHED", readback_required:true};
  }
  async function readback() {
    const raw = sessionStorage.getItem("qikvrt-account-provisioning-pending-v1");
    if (!raw) return {state:"NO_PENDING_EFFECT"};
    const p = JSON.parse(raw); const a = await authority();
    if (a.head !== p.authority.head || a.tree !== p.authority.tree) throw new Error("Main drift before readback");
    await bind(a);
    const text = String(document.body?.innerText || "").slice(0,100000);
    const authenticated = /logout|sign out|my account|account settings/i.test(text);
    const verification = /verify|verification|confirm.*email|email.*confirm/i.test(text);
    const receipt = {schema:"qikvrt_account_provisioning_readback_v1", platform:"arxiv", request_id:p.request_id, authority:a, account_identity_non_secret:null, account_status:authenticated?"AUTHENTICATED":verification?"VERIFICATION_REQUIRED":"NOT_ESTABLISHED", created_or_existing:authenticated?"CREATED_OR_EXISTING_AUTHENTICATED":"UNKNOWN", observed_at:new Date().toISOString(), authoritative_subject_observed:authenticated||verification, completion_claims:{PASS:false,FINAL_PASS:false,EFFECT_ACK_DONE:false}};
    await browser.storage.local.set({qikvrtAccountProvisioningReadbackV1:receipt});
    return receipt;
  }
  function panel() {
    if (document.getElementById(PANEL_ID)) return;
    const p=document.createElement("aside"); p.id=PANEL_ID; p.style.cssText="position:fixed;right:12px;top:12px;z-index:2147483647;width:350px;background:#111;color:#eee;border:1px solid #777;padding:10px;font:12px monospace";
    p.innerHTML='<strong>QIKVRT account provisioning</strong><div><button data-p>Prepare</button> <button data-c>Commit</button> <button data-r>Readback</button></div><pre data-s>OBSERVE</pre>'; document.documentElement.appendChild(p);
    const s=p.querySelector("[data-s]"); const show=x=>s.textContent=JSON.stringify(x,null,2);
    p.querySelector("[data-p]").onclick=()=>prepare().then(show).catch(e=>show({state:"HOLD",reason:e.message}));
    p.querySelector("[data-c]").onclick=()=>commit().then(show).catch(e=>show({state:"HOLD",reason:e.message}));
    p.querySelector("[data-r]").onclick=()=>readback().then(show).catch(e=>show({state:"HOLD",reason:e.message}));
  }
  panel(); readback().catch(()=>undefined);
})();
