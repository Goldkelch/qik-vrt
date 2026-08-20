const fields = ["accent", "fontScale", "density", "position"];
const E2E_NONCE = "QIKVRT-FIREFOX-E2E-NONCE-0001";
const E2E_BACKEND = "http://127.0.0.1:8771";

async function load() {
  const stored = await browser.storage.local.get("qikvrtTerminalPreferences");
  const p = stored.qikvrtTerminalPreferences || {};
  for (const id of fields) if (p[id] !== undefined) document.getElementById(id).value = p[id];
}

async function save() {
  const value = {};
  for (const id of fields) value[id] = document.getElementById(id).value;
  value.fontScale = Number(value.fontScale);
  await browser.storage.local.set({qikvrtTerminalPreferences: value});
  document.getElementById("status").textContent = "gespeichert";
}

async function e2eNetworkDiagnostic() {
  let permission = null;
  let directFetch = null;
  try {
    permission = await browser.permissions.contains({origins: [`${E2E_BACKEND}/*`]});
  } catch (error) {
    permission = `ERROR:${error.message}`;
  }
  try {
    const response = await fetch(`${E2E_BACKEND}/.well-known/effect-ack`, {cache: "no-store", credentials: "omit"});
    directFetch = {ok: response.ok, status: response.status, text: await response.text()};
  } catch (error) {
    directFetch = {ok: false, error: error.message};
  }
  return {host_permission: permission, extension_page_direct_fetch: directFetch};
}

async function runBoundedEffectAckE2E() {
  const status = document.getElementById("status");
  status.textContent = "E2E_RUNNING";
  const request = {
    schema: "qikvrt_terminal_input_v1",
    text: E2E_NONCE,
    audio: null,
    video: null
  };
  const network = await e2eNetworkDiagnostic();
  if (network.host_permission !== true || !network.extension_page_direct_fetch || network.extension_page_direct_fetch.ok !== true) {
    throw new Error(`Effect-Ack network prerequisite failed:${JSON.stringify(network)}`);
  }
  const discovery = await browser.runtime.sendMessage({kind: "DISCOVER_EFFECT_ACK"});
  if (!discovery || discovery.discovered !== true) {
    throw new Error(`Effect-Ack discovery failed:${JSON.stringify({network, discovery})}`);
  }
  const prepared = await browser.runtime.sendMessage({kind: "PREPARE_EFFECT", payload: request});
  if (!prepared || prepared.record_validated !== true || !prepared.effect_ack || prepared.effect_ack.state !== "EFFECT_ACK_DONE") {
    throw new Error(`Effect-Ack prepare was not exact-bound DONE:${JSON.stringify(prepared)}`);
  }
  const committed = await browser.runtime.sendMessage({
    kind: "COMMIT_EFFECT",
    payload: {confirmed: true, prepared, request}
  });
  if (!committed || committed.ordinary_release !== true || !committed.effect_ack || committed.effect_ack.state !== "EFFECT_ACK_DONE") {
    throw new Error(`Effect-Ack commit was not observed DONE:${JSON.stringify(committed)}`);
  }
  const result = {
    schema: "qikvrt_firefox_terminal_effect_ack_e2e_page_v1",
    nonce: E2E_NONCE,
    host_permission_observed: network.host_permission,
    extension_page_direct_fetch_observed: network.extension_page_direct_fetch.ok,
    discovery_observed: true,
    prepare_record_validated: true,
    prepare_state: prepared.effect_ack.state,
    prepare_record_hash: prepared.effect_ack.record_hash,
    commit_state: committed.effect_ack.state,
    commit_ordinary_release: committed.ordinary_release,
    external_effect: committed.body && committed.body.post_effect ? committed.body.post_effect.external_effect : null
  };
  status.textContent = `E2E_DONE:${JSON.stringify(result)}`;
}

document.getElementById("save").addEventListener("click", () => save().catch(error => {
  document.getElementById("status").textContent = error.message;
}));

load();
if (new URL(window.location.href).searchParams.get("qikvrt_e2e") === "1") {
  runBoundedEffectAckE2E().catch(error => {
    document.getElementById("status").textContent = `E2E_FAIL:${error.message}`;
  });
}
