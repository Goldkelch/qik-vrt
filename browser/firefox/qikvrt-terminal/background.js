const AUTHORITY = "Goldkelch/qik-vrt";
const DEFAULT_BACKEND = "http://127.0.0.1:8771";
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

async function github(path) {
  const response = await fetch(`https://api.github.com/repos/${AUTHORITY}${path}`, {
    method: "GET",
    credentials: "omit",
    headers: {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    cache: "no-store"
  });
  if (!response.ok) throw new Error(`github ${response.status}`);
  return response.json();
}

async function observeAuthority() {
  const ref = await github("/git/ref/heads/main");
  const head = ref && ref.object && ref.object.sha;
  if (!/^[0-9a-f]{40}$/.test(head || "")) return fail("main head unavailable");
  const commit = await github(`/git/commits/${head}`);
  const tree = commit && commit.tree && commit.tree.sha;
  if (!/^[0-9a-f]{40}$/.test(tree || "")) return fail("main tree unavailable");
  const runs = await github("/actions/runs?branch=main&per_page=30");
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
    source: {repository: AUTHORITY, ref: "refs/heads/main", head, tree},
    workflows: latest,
    terminal_semantics: {
      rendering_is_authorization: false,
      ordinary_release_requires: "VALID_EFFECT_ACK_DONE"
    }
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
  if (!current) {
    await browser.alarms.create(WATCHDOG_ALARM, {periodInMinutes: WATCHDOG_PERIOD_MINUTES});
  }
  return persistWatchdogFrame();
}

function parseEffectAck(raw) {
  if (typeof raw !== "string" || !raw.trim()) return null;
  const members = new Map();
  for (const part of raw.split(",")) {
    const [k, ...rest] = part.trim().split("=");
    if (!k || !rest.length) continue;
    members.set(k.trim().toLowerCase(), rest.join("=").trim());
  }
  const v = Number(members.get("v"));
  const token = (members.get("state") || "").replace(/^"|"$/g, "").toLowerCase();
  const state = STATE_MAP.get(token);
  if (v !== 1 || !state) return null;
  return {v, state, raw};
}

async function backendBase() {
  const stored = await browser.storage.local.get("qikvrtBackend");
  const value = stored.qikvrtBackend || DEFAULT_BACKEND;
  if (!ALLOWED_BACKENDS.has(value)) throw new Error("backend outside allowlist");
  return value;
}

async function backendRequest(path, init) {
  const base = await backendBase();
  const response = await fetch(`${base}${path}`, {
    credentials: "omit",
    cache: "no-store",
    ...init
  });
  const effect = parseEffectAck(response.headers.get("Effect-Ack"));
  let body = null;
  const type = response.headers.get("content-type") || "";
  if (type.includes("application/json")) body = await response.json();
  else body = {text: await response.text()};
  return {http_status: response.status, effect_ack: effect, body};
}

async function discover() {
  const result = await backendRequest("/.well-known/effect-ack", {method: "GET"});
  return {...result, discovered: result.http_status >= 200 && result.http_status < 300};
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
  return {...result, ordinary_release: false};
}

async function commitEffect(payload) {
  if (!payload || payload.confirmed !== true) return fail("explicit commit confirmation required");
  const prepared = payload.prepared;
  if (!prepared || !prepared.effect_ack || prepared.effect_ack.state !== "EFFECT_ACK_DONE") {
    return fail("validated DONE prepare result required");
  }
  const token = prepared.body && prepared.body.commit_token;
  const hash = prepared.body && prepared.body.record_hash;
  if (typeof token !== "string" || typeof hash !== "string") return fail("prepare binding unavailable");
  const result = await backendRequest("/terminal/commit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Effect-Ack-Request": "v=1, mode=commit",
      "X-QIKVRT-Commit-Token": token,
      "X-QIKVRT-Record-Hash": hash
    },
    body: JSON.stringify(payload.request || {})
  });
  const done = result.effect_ack && result.effect_ack.state === "EFFECT_ACK_DONE";
  return {...result, ordinary_release: Boolean(done)};
}

browser.runtime.onInstalled.addListener(() => {
  ensureWatchdog().catch(() => undefined);
});
browser.runtime.onStartup.addListener(() => {
  ensureWatchdog().catch(() => undefined);
});
browser.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === WATCHDOG_ALARM) persistWatchdogFrame().catch(() => undefined);
});
ensureWatchdog().catch(() => undefined);

browser.runtime.onMessage.addListener(message => {
  if (!message || typeof message.kind !== "string") return Promise.resolve(fail("invalid message"));
  if (message.kind === "OBSERVE_AUTHORITY") return persistWatchdogFrame().catch(error => fail(error.message));
  if (message.kind === "DISCOVER_EFFECT_ACK") return discover().catch(error => fail(error.message));
  if (message.kind === "PREPARE_EFFECT") return prepareEffect(message.payload).catch(error => fail(error.message));
  if (message.kind === "COMMIT_EFFECT") return commitEffect(message.payload).catch(error => fail(error.message));
  return Promise.resolve(fail("unknown message kind"));
});
