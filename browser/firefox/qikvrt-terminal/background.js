const AUTHORITY = "Goldkelch/qik-vrt";
const MIRROR = "ingolf-lohmann/qik-vrt";
const OBSERVABLE_REPOSITORIES = new Set([AUTHORITY, MIRROR]);
const DEFAULT_BACKEND = "http://127.0.0.1:8771";
const MLP_TOS_SHA256 = "5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e";
const ALLOWED_BACKENDS = new Set(["http://127.0.0.1:8771", "http://localhost:8771"]);
const WATCHDOG_ALARM = "qikvrt-repository-watchdog";
const WATCHDOG_PERIOD_MINUTES = 5;
const STATE_MAP = new Map([
  ["nack", "EFFECT_NACK"],
  ["continue", "EFFECT_ACK_CONTINUE"],
  ["done", "EFFECT_ACK_DONE"],
  ["isolate", "EFFECT_ACK_ISOLATE"],
  ["block", "EFFECT_ACK_BLOCK"]
]);

function fail(reason) {
  return {ok: false, state: "HOLD", ordinary_release: false, reason};
}

function observableRepository(repository) {
  if (!OBSERVABLE_REPOSITORIES.has(repository)) throw new Error("repository outside Authority/Mirror allowlist");
  return repository;
}

async function github(repository, path) {
  const selected = observableRepository(repository);
  const response = await fetch(`https://api.github.com/repos/${selected}${path}`, {
    method: "GET",
    credentials: "omit",
    headers: {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    cache: "no-store"
  });
  if (!response.ok) throw new Error(`github ${response.status}`);
  return response.json();
}

async function observeRepository(repository) {
  const selected = observableRepository(repository);
  const ref = await github(selected, "/git/ref/heads/main");
  const head = ref && ref.object && ref.object.sha;
  if (!/^[0-9a-f]{40}$/.test(head || "")) return fail("main head unavailable");
  const commit = await github(selected, `/git/commits/${head}`);
  const tree = commit && commit.tree && commit.tree.sha;
  if (!/^[0-9a-f]{40}$/.test(tree || "")) return fail("main tree unavailable");
  const runs = await github(selected, "/actions/runs?branch=main&per_page=30");
  const wanted = [
    "QIK-VRT autonomous bounded self-heal",
    "QIKVRT reflexive repository watchdog",
    "QIKVRT self-heal terminal monitor"
  ];
  const latest = {};
  for (const name of wanted) {
    const run = (runs.workflow_runs || []).find(item => item.name === name);
    latest[name] = run ? {
      id: run.id,
      status: run.status,
      conclusion: run.conclusion,
      head_sha: run.head_sha,
      html_url: run.html_url
    } : null;
  }
  return {
    ok: true,
    schema: "qikvrt_terminal_frame_v1",
    observed_at: new Date().toISOString(),
    source: {repository: selected, ref: "refs/heads/main", head, tree},
    workflows: latest,
    terminal_semantics: {
      rendering_is_authorization: false,
      ordinary_release_requires: "VALID_EFFECT_ACK_DONE"
    }
  };
}

async function observeAuthority() {
  return observeRepository(AUTHORITY);
}

async function observePullRequest(payload) {
  const repository = observableRepository(payload && payload.repository);
  const number = payload && payload.number;
  if (!/^\d+$/.test(String(number || ""))) return fail("invalid pull-request number");
  const pull = await github(repository, `/pulls/${number}`);
  const head = pull && pull.head && pull.head.sha;
  if (!/^[0-9a-f]{40}$/.test(head || "")) return fail("pull-request head unavailable");
  const commit = await github(repository, `/git/commits/${head}`);
  const tree = commit && commit.tree && commit.tree.sha;
  if (!/^[0-9a-f]{40}$/.test(tree || "")) return fail("pull-request tree unavailable");
  return {
    ok: true,
    schema: "qikvrt_terminal_pr_frame_v1",
    observed_at: new Date().toISOString(),
    source: {repository, pull_request: Number(number), head, tree, base: pull.base && pull.base.ref},
    review: {state: pull.state, draft: Boolean(pull.draft), mergeable: pull.mergeable},
    terminal_semantics: {rendering_is_authorization: false, ordinary_release_requires: "VALID_EFFECT_ACK_DONE"}
  };
}

async function persistWatchdogFrame() {
  let frame;
  try {
    frame = await observeAuthority();
  } catch (error) {
    frame = fail(error.message);
    frame.observed_at = new Date().toISOString();
  }
  const previous = await browser.storage.local.get("qikvrtWatchdogFrame");
  const prior = previous.qikvrtWatchdogFrame || null;
  const materialChange = !prior || !frame.ok || !prior.ok ||
    !prior.source || !frame.source ||
    prior.source.head !== frame.source.head ||
    prior.source.tree !== frame.source.tree ||
    JSON.stringify(prior.workflows || {}) !== JSON.stringify(frame.workflows || {});
  await browser.storage.local.set({
    qikvrtWatchdogFrame: frame,
    qikvrtWatchdogMaterialChange: Boolean(materialChange)
  });
  return frame;
}

async function ensureWatchdog() {
  const current = await browser.alarms.get(WATCHDOG_ALARM);
  if (!current) await browser.alarms.create(WATCHDOG_ALARM, {periodInMinutes: WATCHDOG_PERIOD_MINUTES});
  return persistWatchdogFrame();
}

function decodeSfBytes(value) {
  if (typeof value !== "string" || value.length < 2 || value[0] !== ":" || value[value.length - 1] !== ":") return null;
  try {
    const binary = atob(value.slice(1, -1));
    return Uint8Array.from(binary, ch => ch.charCodeAt(0));
  } catch (_) {
    return null;
  }
}

function bytesToHex(bytes) {
  return Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
}

function asciiFromBytes(bytes) {
  if (!bytes || bytes.some(byte => byte > 0x7f)) return null;
  return String.fromCharCode(...bytes);
}

function sfBytesFromAscii(value) {
  if (typeof value !== "string" || !/^[\x20-\x7e]+$/.test(value)) throw new Error("non-ASCII commit token");
  return `:${btoa(value)}:`;
}

function sfBytesFromHex(hex) {
  if (!/^[0-9a-f]{64}$/.test(hex || "")) throw new Error("invalid record hash");
  let binary = "";
  for (let i = 0; i < hex.length; i += 2) binary += String.fromCharCode(parseInt(hex.slice(i, i + 2), 16));
  return `:${btoa(binary)}:`;
}

function parseStructuredDictionary(raw) {
  if (typeof raw !== "string" || !raw.trim()) return null;
  const members = new Map();
  for (const part of raw.split(",")) {
    const index = part.indexOf("=");
    if (index <= 0) return null;
    const key = part.slice(0, index).trim().toLowerCase();
    const value = part.slice(index + 1).trim();
    if (!/^[a-z*][a-z0-9_.*-]*$/.test(key) || members.has(key)) return null;
    members.set(key, value);
  }
  return members;
}

function parseEffectAck(raw) {
  const members = parseStructuredDictionary(raw);
  if (!members) return null;
  const v = Number(members.get("v"));
  const stateToken = (members.get("state") || "").toLowerCase();
  const state = STATE_MAP.get(stateToken);
  const hashBytes = decodeSfBytes(members.get("hash"));
  const tokenBytes = members.has("token") ? decodeSfBytes(members.get("token")) : null;
  if (v !== 1 || !state || !hashBytes || hashBytes.length !== 32) return null;
  const commitToken = tokenBytes ? asciiFromBytes(tokenBytes) : null;
  if (members.has("token") && !commitToken) return null;
  return {v, state, record_hash: bytesToHex(hashBytes), commit_token: commitToken, raw};
}

async function backendBase() {
  const stored = await browser.storage.local.get("qikvrtBackend");
  const value = stored.qikvrtBackend || DEFAULT_BACKEND;
  if (!ALLOWED_BACKENDS.has(value)) throw new Error("backend outside allowlist");
  return value;
}

async function backendRequest(path, init) {
  const base = await backendBase();
  const response = await fetch(`${base}${path}`, {credentials: "omit", cache: "no-store", ...init});
  const effect = parseEffectAck(response.headers.get("Effect-Ack"));
  const type = response.headers.get("content-type") || "";
  const body = type.includes("application/json") ? await response.json() : {text: await response.text()};
  return {http_status: response.status, effect_ack: effect, body};
}

async function discover() {
  const result = await backendRequest("/.well-known/effect-ack", {method: "GET"});
  return {...result, discovered: result.http_status >= 200 && result.http_status < 300};
}

async function atariBoot(payload) {
  if (!payload || payload.schema !== "qikvrt.atari-terminal-boot.v1" || payload.mlp_sha256 !== MLP_TOS_SHA256) {
    return fail("exact MLP.TOS boot binding required");
  }
  return backendRequest("/qikvrt/atari/boot", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
}

async function atariStatus(payload) {
  if (!payload || payload.schema !== "qikvrt.atari-terminal-status.v1" || !/^[0-9a-f]{32}$/.test(payload.boot_id || "")) {
    return fail("exact Atari boot identifier required");
  }
  return backendRequest(`/qikvrt/atari/status/${payload.boot_id}`, {method: "GET"});
}

function isAtariTerminalSender(sender) {
  try {
    const url = new URL(sender && sender.url);
    return url.origin === "https://goldkelch.github.io" && url.pathname === "/qik-vrt/atari-terminal/";
  } catch (_) {
    return false;
  }
}

async function validatePreparedRecord(result) {
  const effect = result.effect_ack;
  const body = result.body;
  if (!effect || effect.state !== "EFFECT_ACK_DONE") return fail("prepare is not DONE");
  if (!body || typeof body.record_hash !== "string" || !/^[0-9a-f]{64}$/.test(body.record_hash)) return fail("prepare record hash unavailable");
  if (body.record_hash !== effect.record_hash) return fail("compact/full record hash mismatch");
  if (!effect.commit_token || body.commit_token !== effect.commit_token) return fail("compact/full commit token mismatch");
  if (typeof body.record_url !== "string" || !body.record_url.startsWith("/effect-ack/records/")) return fail("bound record URL unavailable");
  const recordResult = await backendRequest(body.record_url, {method: "GET"});
  const record = recordResult.body;
  if (recordResult.http_status !== 200 || !recordResult.effect_ack || !record) return fail("full record unavailable");
  if (recordResult.effect_ack.record_hash !== body.record_hash) return fail("record response hash mismatch");
  if (record.state !== "EFFECT_ACK_DONE" || record.ordinary_release !== true) return fail("full record is not release-eligible DONE");
  if (record.record_hash !== `sha256:${body.record_hash}`) return fail("full record self-binding mismatch");
  return {...result, record_validated: true, full_record: record, ordinary_release: false};
}

async function prepareEffect(payload) {
  const discovery = await discover();
  if (!discovery.discovered) return fail("effect-ack capability not discovered");
  const result = await backendRequest("/terminal/prepare", {
    method: "POST",
    headers: {"Content-Type": "application/json", "Effect-Ack-Request": "v=1, mode=prepare"},
    body: JSON.stringify(payload)
  });
  if (!result.effect_ack) return fail("missing or malformed Effect-Ack response");
  if (result.effect_ack.state !== "EFFECT_ACK_DONE") return {...result, record_validated: false, ordinary_release: false};
  return validatePreparedRecord(result);
}

async function commitEffect(payload) {
  if (!payload || payload.confirmed !== true) return fail("explicit commit confirmation required");
  const prepared = payload.prepared;
  if (!prepared || prepared.record_validated !== true || !prepared.effect_ack || prepared.effect_ack.state !== "EFFECT_ACK_DONE") return fail("validated DONE prepare result required");
  const token = prepared.effect_ack.commit_token;
  const hash = prepared.effect_ack.record_hash;
  if (typeof token !== "string" || typeof hash !== "string") return fail("prepare binding unavailable");
  const effectAckRequest = `v=1, mode=commit, token=${sfBytesFromAscii(token)}, hash=${sfBytesFromHex(hash)}`;
  const result = await backendRequest("/terminal/commit", {
    method: "POST",
    headers: {"Content-Type": "application/json", "Effect-Ack-Request": effectAckRequest},
    body: JSON.stringify(payload.request || {})
  });
  const done = result.effect_ack && result.effect_ack.state === "EFFECT_ACK_DONE";
  return {...result, ordinary_release: Boolean(done && result.body && result.body.ordinary_release === true)};
}

browser.runtime.onInstalled.addListener(() => { ensureWatchdog().catch(() => undefined); });
browser.runtime.onStartup.addListener(() => { ensureWatchdog().catch(() => undefined); });
browser.alarms.onAlarm.addListener(alarm => { if (alarm.name === WATCHDOG_ALARM) persistWatchdogFrame().catch(() => undefined); });
ensureWatchdog().catch(() => undefined);

browser.runtime.onMessage.addListener((message, sender) => {
  if (!message || typeof message.kind !== "string") return Promise.resolve(fail("invalid message"));
  if (message.kind === "OBSERVE_AUTHORITY") return persistWatchdogFrame().catch(error => fail(error.message));
  if (message.kind === "OBSERVE_REPOSITORY") return observeRepository(message.payload).catch(error => fail(error.message));
  if (message.kind === "OBSERVE_PR") return observePullRequest(message.payload).catch(error => fail(error.message));
  if (message.kind === "ATARI_BOOT") return isAtariTerminalSender(sender) ? atariBoot(message.payload).catch(error => fail(error.message)) : Promise.resolve(fail("Atari boot sender outside terminal page"));
  if (message.kind === "ATARI_STATUS") return isAtariTerminalSender(sender) ? atariStatus(message.payload).catch(error => fail(error.message)) : Promise.resolve(fail("Atari status sender outside terminal page"));
  if (message.kind === "DISCOVER_EFFECT_ACK") return discover().catch(error => fail(error.message));
  if (message.kind === "PREPARE_EFFECT") return prepareEffect(message.payload).catch(error => fail(error.message));
  if (message.kind === "COMMIT_EFFECT") return commitEffect(message.payload).catch(error => fail(error.message));
  return Promise.resolve(fail("unknown message kind"));
});
