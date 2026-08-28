const AUTHORITY = "Goldkelch/qik-vrt";
const DEFAULT_BACKEND = "http://127.0.0.1:8771";
const ALLOWED_BACKENDS = new Set(["http://127.0.0.1:8771", "http://localhost:8771"]);
// V2 deliberately has a narrower transport allowlist than the legacy V1
// renderer.  The browser may contact only its own explicitly configured
// loopback daemon.  A stored value cannot turn it into a generic HTTP client
// or a remote terminal peer.
const V2_ALLOWED_BACKENDS = new Set(["http://127.0.0.1:8771"]);
const V2_CONFIG_KEY = "qikvrtPeerV2Config";
const V2_POLICY_ID = "QIKVRT_HTTP_TERMINAL_PEER_V2";
const V2_POLICY_SHA256 = "sha256:4a0d59cc17ccc5750b17cb66a9be3e83f36631e739f9974e27b44252655b8af4";
const V2_IDENTIFIER_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const V2_REQUEST_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._=-]{0,127}$/;
const V2_SHA256_RE = /^[0-9a-f]{64}$/;
const V2_RFC3339_UTC_RE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{3})?Z$/;
const V2_MEDIA_TYPE_RE = /^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}\/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}$/;
const V2_BASE64_RE = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
const V2_MAX_MEDIA_BYTES = 512 * 1024;
const V2_MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER;
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

// Observation advances only from an explicit UI/client message.  This event
// page owns no alarm, timer, startup fetch, periodic repository scan or retry.
async function persistObservedFrame() {
  let frame;
  try {
    frame = await observeAuthority();
  } catch (error) {
    frame = fail(error.message);
    frame.observed_at = new Date().toISOString();
  }
  const previous = await browser.storage.local.get("qikvrtObservedFrame");
  const prior = previous.qikvrtObservedFrame || null;
  const materialChange = !prior || !frame.ok || !prior.ok ||
    !prior.source || !frame.source ||
    prior.source.head !== frame.source.head ||
    prior.source.tree !== frame.source.tree ||
    JSON.stringify(prior.workflows || {}) !== JSON.stringify(frame.workflows || {});
  await browser.storage.local.set({
    qikvrtObservedFrame: frame,
    qikvrtObservedMaterialChange: Boolean(materialChange)
  });
  return frame;
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

function ownExactKeys(value, expected) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return actual.length === wanted.length && actual.every((key, index) => key === wanted[index]);
}

function scalarLength(value) {
  return Array.from(value).length;
}

function assertUnicodeScalarText(value, field, maximum, allowEmpty = false) {
  if (typeof value !== "string" || (!allowEmpty && value.length === 0) || scalarLength(value) > maximum) {
    throw new Error(`${field} is outside bounded UTF-8 text`);
  }
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) throw new Error(`${field} contains an unpaired surrogate`);
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      throw new Error(`${field} contains an unpaired surrogate`);
    }
  }
  return value;
}

function compareUnicodeScalars(left, right) {
  const a = Array.from(left);
  const b = Array.from(right);
  const length = Math.min(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    const delta = a[index].codePointAt(0) - b[index].codePointAt(0);
    if (delta !== 0) return delta;
  }
  return a.length - b.length;
}

function isCanonicalObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  // Structured-clone values may originate in another extension realm.  Accept
  // only a null prototype or an ordinary Object prototype with a null parent;
  // reject class instances and deeper/custom prototype chains.
  return prototype === null || (
    Object.prototype.toString.call(value) === "[object Object]" &&
    Object.getPrototypeOf(prototype) === null
  );
}

function canonicalJsonV2(value) {
  // QIKVRT_CLOSED_JSON_V2: no floats, fixed string escapes, Unicode-scalar
  // key ordering and compact separators.  Do not substitute JSON.stringify:
  // its object ordering and escaping are host-language choices.
  function encodeString(text) {
    let output = '"';
    for (const character of text) {
      const codepoint = character.codePointAt(0);
      if (character === '"') output += '\\"';
      else if (character === "\\") output += "\\\\";
      else if (character === "\b") output += "\\b";
      else if (character === "\f") output += "\\f";
      else if (character === "\n") output += "\\n";
      else if (character === "\r") output += "\\r";
      else if (character === "\t") output += "\\t";
      else if (codepoint <= 0x1f) output += `\\u${codepoint.toString(16).padStart(4, "0")}`;
      else output += character;
    }
    return output + '"';
  }

  function encode(member, path, depth) {
    if (depth > 16) throw new Error(`${path} exceeds canonical JSON nesting depth`);
    if (member === null) return "null";
    if (typeof member === "boolean") return member ? "true" : "false";
    if (typeof member === "number") {
      if (!Number.isSafeInteger(member)) throw new Error(`${path} is not a canonical JSON integer`);
      return String(member);
    }
    if (typeof member === "string") return encodeString(assertUnicodeScalarText(member, path, 2 * 1024 * 1024, true));
    if (Array.isArray(member)) {
      if (member.length > 64) throw new Error(`${path} has too many canonical JSON array items`);
      return `[${member.map((item, index) => encode(item, `${path}[${index}]`, depth + 1)).join(",")}]`;
    }
    if (isCanonicalObject(member)) {
      const keys = Object.keys(member);
      if (keys.length > 64) throw new Error(`${path} has too many canonical JSON object fields`);
      for (const key of keys) assertUnicodeScalarText(key, `${path} key`, 2 * 1024 * 1024, true);
      return `{${keys.sort(compareUnicodeScalars).map(key => `${encodeString(key)}:${encode(member[key], `${path}.${key}`, depth + 1)}`).join(",")}}`;
    }
    throw new Error(`${path} is not in the closed canonical JSON domain`);
  }

  return encode(value, "value", 0);
}

async function sha256HexV2(value) {
  if (!crypto || !crypto.subtle) throw new Error("WebCrypto SHA-256 is unavailable");
  const source = typeof value === "string" ? new TextEncoder().encode(value) : value;
  const digest = await crypto.subtle.digest("SHA-256", source);
  return bytesToHex(new Uint8Array(digest));
}

function bytesFromCanonicalBase64(value, field) {
  if (typeof value !== "string" || !V2_BASE64_RE.test(value)) throw new Error(`${field} base64 is non-canonical`);
  try {
    const binary = atob(value);
    if (btoa(binary) !== value) throw new Error(`${field} base64 spelling differs`);
    return Uint8Array.from(binary, character => character.charCodeAt(0));
  } catch (_) {
    throw new Error(`${field} base64 is malformed`);
  }
}

function validateV2Identifier(value, field, requestId = false) {
  const expression = requestId ? V2_REQUEST_ID_RE : V2_IDENTIFIER_RE;
  if (typeof value !== "string" || !expression.test(value)) throw new Error(`${field} must be a bounded identifier`);
  return value;
}

function normalizePeerV2Config(value) {
  const keys = ["enabled", "backend", "source_node_id", "target_node_id", "target_endpoint_id", "responsibility_owner"];
  if (!ownExactKeys(value, keys) || value.enabled !== true) throw new Error("V2 local peer is disabled or unconfigured");
  if (!V2_ALLOWED_BACKENDS.has(value.backend)) throw new Error("V2 peer backend is outside the exact loopback allowlist");
  const sourceNode = validateV2Identifier(value.source_node_id, "V2 source node");
  const targetNode = validateV2Identifier(value.target_node_id, "V2 target node");
  if (sourceNode === targetNode) throw new Error("V2 source and target nodes must differ");
  return {
    backend: value.backend,
    source_node_id: sourceNode,
    target_node_id: targetNode,
    target_endpoint_id: validateV2Identifier(value.target_endpoint_id, "V2 target endpoint"),
    responsibility_owner: assertUnicodeScalarText(value.responsibility_owner, "V2 responsibility owner", 256)
  };
}

async function peerV2Config() {
  const stored = await browser.storage.local.get(V2_CONFIG_KEY);
  return normalizePeerV2Config(stored[V2_CONFIG_KEY]);
}

async function peerMediaDescriptorV2(value, expectedKind) {
  if (value === null) return null;
  const keys = ["media_type", "content_type", "bytes", "base64"];
  if (!ownExactKeys(value, keys) || value.media_type !== expectedKind) {
    throw new Error(`${expectedKind} input is not an exact local media payload`);
  }
  const contentType = assertUnicodeScalarText(value.content_type, `${expectedKind} content type`, 127).split(";", 1)[0].trim().toLowerCase();
  if (!V2_MEDIA_TYPE_RE.test(contentType) ||
      (expectedKind === "audio" && !contentType.startsWith("audio/")) ||
      (expectedKind === "video_snapshot" && !(contentType.startsWith("image/") || contentType.startsWith("video/")))) {
    throw new Error(`${expectedKind} content type is outside the V2 media domain`);
  }
  if (!Number.isSafeInteger(value.bytes) || value.bytes < 0 || value.bytes > V2_MAX_MEDIA_BYTES) {
    throw new Error(`${expectedKind} bytes are outside the V2 media bound`);
  }
  const bytes = bytesFromCanonicalBase64(value.base64, expectedKind);
  if (bytes.length !== value.bytes) throw new Error(`${expectedKind} byte count differs from base64`);
  return {
    schema: "qikvrt_terminal_media_descriptor_v1",
    kind: expectedKind,
    content_type: contentType,
    byte_length: bytes.length,
    sha256: `sha256:${await sha256HexV2(bytes)}`,
    base64: value.base64
  };
}

async function terminalInputV2(value) {
  const keys = ["schema", "submitted_at", "page", "text", "audio", "video"];
  if (!ownExactKeys(value, keys) || value.schema !== "qikvrt_terminal_input_v2") {
    throw new Error("V2 terminal input fields differ from the closed frame");
  }
  const submittedAt = assertUnicodeScalarText(value.submitted_at, "V2 submitted_at", 24);
  if (!V2_RFC3339_UTC_RE.test(submittedAt)) throw new Error("V2 submitted_at is not canonical UTC RFC3339");
  const input = {
    schema: "qikvrt_terminal_input_v2",
    submitted_at: submittedAt,
    page: assertUnicodeScalarText(value.page, "V2 page", 2048),
    text: assertUnicodeScalarText(value.text, "V2 text", 4096),
    audio: await peerMediaDescriptorV2(value.audio, "audio"),
    video: await peerMediaDescriptorV2(value.video, "video_snapshot")
  };
  canonicalJsonV2(input);
  return input;
}

async function validateTerminalInputV2(value) {
  const keys = ["schema", "submitted_at", "page", "text", "audio", "video"];
  if (!ownExactKeys(value, keys) || value.schema !== "qikvrt_terminal_input_v2") {
    throw new Error("persisted V2 terminal input fields differ from the closed frame");
  }
  const validateDescriptor = async (descriptor, expectedKind) => {
    if (descriptor === null) return null;
    const descriptorKeys = ["schema", "kind", "content_type", "byte_length", "sha256", "base64"];
    if (!ownExactKeys(descriptor, descriptorKeys) || descriptor.schema !== "qikvrt_terminal_media_descriptor_v1" || descriptor.kind !== expectedKind) {
      throw new Error(`persisted ${expectedKind} descriptor differs`);
    }
    const contentType = assertUnicodeScalarText(descriptor.content_type, `${expectedKind} content type`, 127);
    if (!V2_MEDIA_TYPE_RE.test(contentType) ||
        (expectedKind === "audio" && !contentType.startsWith("audio/")) ||
        (expectedKind === "video_snapshot" && !(contentType.startsWith("image/") || contentType.startsWith("video/")))) {
      throw new Error(`persisted ${expectedKind} content type differs`);
    }
    if (!Number.isSafeInteger(descriptor.byte_length) || descriptor.byte_length < 0 || descriptor.byte_length > V2_MAX_MEDIA_BYTES ||
        typeof descriptor.sha256 !== "string" || !/^sha256:[0-9a-f]{64}$/.test(descriptor.sha256)) {
      throw new Error(`persisted ${expectedKind} descriptor has invalid byte or hash binding`);
    }
    const bytes = bytesFromCanonicalBase64(descriptor.base64, expectedKind);
    if (bytes.length !== descriptor.byte_length || `sha256:${await sha256HexV2(bytes)}` !== descriptor.sha256) {
      throw new Error(`persisted ${expectedKind} bytes differ from descriptor`);
    }
    return {
      schema: descriptor.schema,
      kind: descriptor.kind,
      content_type: contentType,
      byte_length: descriptor.byte_length,
      sha256: descriptor.sha256,
      base64: descriptor.base64
    };
  };
  const submittedAt = assertUnicodeScalarText(value.submitted_at, "persisted V2 submitted_at", 24);
  if (!V2_RFC3339_UTC_RE.test(submittedAt)) throw new Error("persisted V2 submitted_at is not canonical UTC RFC3339");
  const input = {
    schema: "qikvrt_terminal_input_v2",
    submitted_at: submittedAt,
    page: assertUnicodeScalarText(value.page, "persisted V2 page", 2048),
    text: assertUnicodeScalarText(value.text, "persisted V2 text", 4096),
    audio: await validateDescriptor(value.audio, "audio"),
    video: await validateDescriptor(value.video, "video_snapshot")
  };
  canonicalJsonV2(input);
  return input;
}

function peerEnvelopeV2(config, terminalInput, requestId, target) {
  if (!V2_REQUEST_ID_RE.test(requestId) || !["/terminal/prepare", "/terminal/commit"].includes(target)) {
    throw new Error("V2 envelope target or request id is invalid");
  }
  return {
    schema: "qikvrt_terminal_peer_request_v2",
    request_id: requestId,
    source_node_id: config.source_node_id,
    target_node_id: config.target_node_id,
    target_endpoint_id: config.target_endpoint_id,
    effective_method: "POST",
    effective_target: target,
    policy_id: V2_POLICY_ID,
    policy_sha256: V2_POLICY_SHA256,
    responsibility_owner: config.responsibility_owner,
    terminal_input: terminalInput
  };
}

async function deterministicRequestIdV2(config, terminalInput) {
  const identity = {
    schema: "qikvrt_terminal_peer_request_identity_v2",
    source_node_id: config.source_node_id,
    target_node_id: config.target_node_id,
    target_endpoint_id: config.target_endpoint_id,
    effective_method: "POST",
    effective_target: "/terminal/commit",
    policy_id: V2_POLICY_ID,
    policy_sha256: V2_POLICY_SHA256,
    responsibility_owner: config.responsibility_owner,
    terminal_input: terminalInput
  };
  return `v2-${await sha256HexV2(canonicalJsonV2(identity))}`;
}

async function peerIntentV2(envelope) {
  const inputHash = await sha256HexV2(canonicalJsonV2(envelope.terminal_input));
  const intent = {
    request_id: envelope.request_id,
    source_node_id: envelope.source_node_id,
    target_node_id: envelope.target_node_id,
    target_endpoint_id: envelope.target_endpoint_id,
    effective_method: "POST",
    effective_target: "/terminal/commit",
    request_content_sha256: `sha256:${inputHash}`,
    policy_id: V2_POLICY_ID,
    policy_sha256: V2_POLICY_SHA256,
    responsibility_owner: envelope.responsibility_owner
  };
  return {intent, fingerprint: await sha256HexV2(canonicalJsonV2(intent)), input_hash: inputHash};
}

function peerHeadersV2(envelope, mode, token = null, recordHash = null) {
  const headers = {
    "Content-Type": "application/json",
    "Effect-Ack-Request": `v=2, mode=${mode}`,
    "Idempotency-Key": envelope.request_id,
    "X-QIKVRT-Source-Node": envelope.source_node_id,
    "X-QIKVRT-Target-Node": envelope.target_node_id,
    "X-QIKVRT-Target-Endpoint": envelope.target_endpoint_id
  };
  if (mode === "commit") {
    if (typeof token !== "string" || !V2_SHA256_RE.test(recordHash || "")) throw new Error("V2 commit binding is unavailable");
    headers["Effect-Ack-Request"] = `v=2, mode=commit, token=${sfBytesFromAscii(token)}, hash=${sfBytesFromHex(recordHash)}`;
  }
  return headers;
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
  if ((v !== 1 && v !== 2) || !state || !hashBytes || hashBytes.length !== 32) return null;
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

async function backendRequestAt(base, path, init) {
  if (typeof base !== "string" || typeof path !== "string" || !path.startsWith("/")) {
    throw new Error("invalid local backend request");
  }
  const response = await fetch(`${base}${path}`, {credentials: "omit", cache: "no-store", ...init});
  const effect = parseEffectAck(response.headers.get("Effect-Ack"));
  const type = response.headers.get("content-type") || "";
  const body = type.includes("application/json") ? await response.json() : {text: await response.text()};
  return {http_status: response.status, effect_ack: effect, body};
}

async function backendRequest(path, init) {
  return backendRequestAt(await backendBase(), path, init);
}

async function discover() {
  const result = await backendRequest("/.well-known/effect-ack", {method: "GET"});
  return {...result, discovered: result.http_status >= 200 && result.http_status < 300};
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

function exactPeerRecordPath(value) {
  if (typeof value !== "string" || !/^\/effect-ack\/records\/[0-9a-f]{64}$/.test(value)) {
    throw new Error("V2 bound record URL is unavailable");
  }
  return value;
}

async function discoverPeerV2(config) {
  const result = await backendRequestAt(config.backend, "/.well-known/effect-ack", {method: "GET"});
  const body = result.body;
  const profile = body && body.peer_profile;
  if (result.http_status !== 200 || !body || !Array.isArray(body.versions) || !body.versions.includes(2) ||
      !profile || profile.schema !== "qikvrt_terminal_peer_profile_v2" ||
      profile.policy_id !== V2_POLICY_ID || profile.policy_sha256 !== V2_POLICY_SHA256 ||
      profile.node_id !== config.target_node_id || profile.endpoint_id !== config.target_endpoint_id ||
      profile.transport_scope !== "LOOPBACK_HTTP_ONLY" || profile.external_effect !== "NONE") {
    throw new Error("V2 local peer capability does not match the exact configured target");
  }
  return result;
}

async function validatePeerPreparedV2(result, envelope, config) {
  const expected = await peerIntentV2(envelope);
  const effect = result && result.effect_ack;
  const body = result && result.body;
  if (!effect || effect.v !== 2 || effect.state !== "EFFECT_ACK_DONE" || result.http_status !== 200 ||
      !body || body.schema !== "qikvrt_terminal_prepare_v2" || body.wire_version !== 2 ||
      body.state !== "EFFECT_ACK_DONE" || body.ordinary_release !== false || body.external_effect !== "NONE" ||
      body.idempotency_key !== envelope.request_id || body.request_fingerprint !== `sha256:${expected.fingerprint}` ||
      !V2_SHA256_RE.test(body.record_hash || "") || body.record_hash !== effect.record_hash ||
      typeof body.commit_token !== "string" || !body.commit_token ||
      !Number.isSafeInteger(body.expires_at_unix) || body.expires_at_unix <= Math.floor(Date.now() / 1000)) {
    throw new Error("V2 prepared receipt differs from the exact local peer binding");
  }
  const recordPath = exactPeerRecordPath(body.record_url);
  const recordResult = await backendRequestAt(config.backend, recordPath, {method: "GET"});
  const record = recordResult.body;
  if (!recordResult.effect_ack || recordResult.effect_ack.v !== 2 || recordResult.effect_ack.state !== "EFFECT_ACK_DONE" ||
      recordResult.effect_ack.record_hash !== body.record_hash || recordResult.http_status !== 200 || !record ||
      record.schema !== "qikvrt_effect_ack_http_terminal_record_v2" || record.wire_version !== 2 ||
      record.state !== "EFFECT_ACK_DONE" || record.external_effect !== "NONE" ||
      record.policy_id !== V2_POLICY_ID || record.policy_version !== 2 ||
      record.responsibility_owner !== config.responsibility_owner || record.request_id !== envelope.request_id ||
      record.request_fingerprint !== `sha256:${expected.fingerprint}` ||
      record.input_hash !== `sha256:${expected.input_hash}` || record.record_hash !== `sha256:${body.record_hash}` ||
      canonicalJsonV2(record.node_binding) !== canonicalJsonV2(expected.intent)) {
    throw new Error("V2 full responsibility record differs from the exact local peer binding");
  }
  return {
    ...result,
    record_validated: true,
    ordinary_release: false,
    peer_config: config,
    envelope,
    peer_intent: expected.intent,
    peer_request_fingerprint: expected.fingerprint
  };
}

async function preparePeerV2(payload) {
  const config = await peerV2Config();
  await discoverPeerV2(config);
  const input = await terminalInputV2(payload);
  const requestId = await deterministicRequestIdV2(config, input);
  const envelope = peerEnvelopeV2(config, input, requestId, "/terminal/prepare");
  const result = await backendRequestAt(config.backend, "/terminal/prepare", {
    method: "POST",
    headers: peerHeadersV2(envelope, "prepare"),
    body: canonicalJsonV2(envelope)
  });
  return validatePeerPreparedV2(result, envelope, config);
}

function sameCanonicalV2(left, right) {
  try {
    return canonicalJsonV2(left) === canonicalJsonV2(right);
  } catch (_) {
    return false;
  }
}

async function commitPeerV2(payload) {
  if (!payload || payload.confirmed !== true || !payload.prepared || payload.prepared.record_validated !== true) {
    throw new Error("explicit V2 commit confirmation and validated prepare are required");
  }
  const config = await peerV2Config();
  const prepared = payload.prepared;
  if (!sameCanonicalV2(prepared.peer_config, config)) throw new Error("V2 local peer configuration changed after prepare");
  const priorEnvelope = prepared.envelope;
  if (!priorEnvelope || priorEnvelope.effective_target !== "/terminal/prepare") {
    throw new Error("V2 prepared envelope is unavailable");
  }
  const terminalInput = await validateTerminalInputV2(priorEnvelope.terminal_input);
  const expectedPrepare = peerEnvelopeV2(config, terminalInput, validateV2Identifier(priorEnvelope.request_id, "V2 request id", true), "/terminal/prepare");
  if (!sameCanonicalV2(priorEnvelope, expectedPrepare)) throw new Error("V2 prepared envelope differs from its local configuration");
  // The GET is an explicit user-triggered reobservation.  It prevents a stale
  // content-script value from becoming a Commit authority after daemon restart.
  const revalidated = await validatePeerPreparedV2(prepared, expectedPrepare, config);
  const commitEnvelope = peerEnvelopeV2(config, terminalInput, expectedPrepare.request_id, "/terminal/commit");
  const expectedCommit = await peerIntentV2(commitEnvelope);
  if (expectedCommit.fingerprint !== revalidated.peer_request_fingerprint ||
      !sameCanonicalV2(expectedCommit.intent, revalidated.peer_intent)) {
    throw new Error("V2 commit intent differs from the prepared peer binding");
  }
  const result = await backendRequestAt(config.backend, "/terminal/commit", {
    method: "POST",
    headers: peerHeadersV2(commitEnvelope, "commit", prepared.body.commit_token, prepared.body.record_hash),
    body: canonicalJsonV2(commitEnvelope)
  });
  const effect = result.effect_ack;
  const body = result.body;
  const successor = body && body.successor_record;
  const committed = result.http_status === 200 && effect && effect.v === 2 && effect.state === "EFFECT_ACK_DONE" &&
    body && body.schema === "qikvrt_terminal_peer_result_v2" && body.wire_version === 2 &&
    body.state === "EFFECT_ACK_DONE" && body.ordinary_release === true && body.external_effect === "NONE" &&
    body.idempotency_key === commitEnvelope.request_id && body.request_fingerprint === `sha256:${expectedCommit.fingerprint}` &&
    sameCanonicalV2(body.node_binding, expectedCommit.intent) && successor &&
    successor.schema === "qikvrt_effect_ack_http_terminal_record_v2" && successor.wire_version === 2 &&
    successor.state === "EFFECT_ACK_DONE" && successor.external_effect === "NONE" &&
    successor.request_id === commitEnvelope.request_id && successor.request_fingerprint === `sha256:${expectedCommit.fingerprint}` &&
    successor.record_hash === `sha256:${effect.record_hash}` &&
    sameCanonicalV2(successor.node_binding, expectedCommit.intent);
  if (!committed) throw new Error("V2 local commit receipt differs from the exact prepared peer binding");
  // The daemon's local ledger is a transport receipt only.  The extension
  // never promotes it to a repository, actuator, or external effect release.
  return {...result, local_commit_receipt: true, ordinary_release: false, external_effect: "NONE"};
}

browser.runtime.onMessage.addListener(message => {
  if (!message || typeof message.kind !== "string") return Promise.resolve(fail("invalid message"));
  if (message.kind === "OBSERVE_AUTHORITY") return persistObservedFrame().catch(error => fail(error.message));
  if (message.kind === "DISCOVER_EFFECT_ACK") return discover().catch(error => fail(error.message));
  if (message.kind === "PREPARE_EFFECT") return prepareEffect(message.payload).catch(error => fail(error.message));
  if (message.kind === "COMMIT_EFFECT") return commitEffect(message.payload).catch(error => fail(error.message));
  if (message.kind === "PREPARE_PEER_V2") return preparePeerV2(message.payload).catch(error => fail(error.message));
  if (message.kind === "COMMIT_PEER_V2") return commitPeerV2(message.payload).catch(error => fail(error.message));
  return Promise.resolve(fail("unknown message kind"));
});
