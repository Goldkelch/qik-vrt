"use strict";

const crypto = require("node:crypto");

const SESSION_SCHEMA = "qikvrt-voice-sso-session/1.0";
const COMMAND_SCHEMA = "qikvrt-voice-sso-command/1.0";
const SHA256_RE = /^[0-9a-f]{64}$/u;
const GIT_SHA1_RE = /^[0-9a-f]{40}$/u;
const REPOSITORY_RE = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/u;
const ID_RE = /^[a-z0-9][a-z0-9._-]{2,127}$/u;
const ISO_UTC_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/u;

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function assertExactKeys(object, required, optional, label) {
  if (!isPlainObject(object)) throw new Error(`${label} must be an object`);
  const allowed = new Set([...required, ...optional]);
  for (const key of Object.keys(object)) {
    if (!allowed.has(key)) throw new Error(`${label} contains unknown field: ${key}`);
  }
  for (const key of required) {
    if (!(key in object)) throw new Error(`${label} is missing required field: ${key}`);
  }
}

function assertString(value, label, pattern, maximum = 4096) {
  if (typeof value !== "string" || value.length === 0 || value.length > maximum) {
    throw new Error(`${label} must be a non-empty string no longer than ${maximum} characters`);
  }
  if (pattern && !pattern.test(value)) throw new Error(`${label} has an invalid format`);
  return value;
}

function assertArray(value, label, minimum, maximum) {
  if (!Array.isArray(value) || value.length < minimum || value.length > maximum) {
    throw new Error(`${label} must be an array with ${minimum} to ${maximum} items`);
  }
  return value;
}

function parseUtc(value, label) {
  assertString(value, label, ISO_UTC_RE, 20);
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) throw new Error(`${label} is not a valid UTC timestamp`);
  return milliseconds;
}

function canonicalJson(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("canonical JSON does not allow non-finite numbers");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (!isPlainObject(value)) throw new Error("canonical JSON accepts only plain objects, arrays and primitives");
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}

function withoutSignature(value) {
  const { signature, ...unsigned } = value;
  return unsigned;
}

function canonicalDigest(value) {
  return crypto.createHash("sha256").update(canonicalJson(value), "utf8").digest("hex");
}

function effectClassForOperation(policyVoice, operation) {
  const classification = policyVoice.effect_classification;
  assertExactKeys(classification, ["default", "operations"], [], "policy.voice_sso.effect_classification");
  if (classification.default !== "EXTERNAL_EFFECT") {
    throw new Error("unknown operations must default to EXTERNAL_EFFECT");
  }
  if (!isPlainObject(classification.operations) || Object.keys(classification.operations).length > 256) {
    throw new Error("effect classification operations must be a bounded object");
  }
  for (const [name, effectClass] of Object.entries(classification.operations)) {
    assertString(name, "effect classification operation", /^[A-Z][A-Z0-9_]{2,127}$/u, 128);
    if (!new Set(["READ_ONLY", "REPOSITORY_MUTATION", "EXTERNAL_EFFECT"]).has(effectClass)) {
      throw new Error(`invalid effect classification for operation: ${name}`);
    }
  }
  return Object.prototype.hasOwnProperty.call(classification.operations, operation)
    ? classification.operations[operation]
    : classification.default;
}

function assertOperationPermitted(policy, operation) {
  const boundary = policy.command_boundary;
  assertExactKeys(
    boundary,
    ["required_binding", "head_or_tree_drift", "ordinary_repository_actions", "external_effects", "prohibited_actions_remain_prohibited"],
    [],
    "policy.command_boundary",
  );
  const prohibited = assertArray(boundary.prohibited_actions_remain_prohibited, "policy prohibited operations", 1, 64);
  for (const name of prohibited) assertString(name, "policy prohibited operation", /^[A-Z][A-Z0-9_]{2,127}$/u, 128);
  if (prohibited.includes(operation)) throw new Error(`operation is prohibited by policy: ${operation}`);
}

function verifySignature(value, publicKeyPem, label) {
  assertExactKeys(value.signature, ["algorithm", "value"], [], `${label}.signature`);
  if (value.signature.algorithm !== "Ed25519") throw new Error(`${label}.signature.algorithm must be Ed25519`);
  const encodedSignature = assertString(value.signature.value, `${label}.signature.value`, /^[A-Za-z0-9+/]+={0,2}$/u, 1024);
  const signature = Buffer.from(encodedSignature, "base64");
  if (signature.length === 0 || signature.toString("base64") !== encodedSignature) {
    throw new Error(`${label}.signature.value is not canonical base64`);
  }
  if (!crypto.verify(null, Buffer.from(canonicalJson(withoutSignature(value)), "utf8"), publicKeyPem, signature)) {
    throw new Error(`${label} signature verification failed`);
  }
}

function registeredIssuer(policy, keyId) {
  assertExactKeys(
    policy,
    ["schema", "policy_id", "product_owner", "voice_sso", "registered_issuers"],
    ["_license", "version", "enrollment", "privacy", "command_boundary", "collective_observer_boundary", "release_claims"],
    "policy",
  );
  if (policy.schema !== "qikvrt-product-owner-voice-sso-policy/1.0") throw new Error("unsupported policy schema");
  const issuers = assertArray(policy.registered_issuers, "policy.registered_issuers", 1, 16);
  const issuer = issuers.find((candidate) => candidate && candidate.key_id === keyId);
  if (!issuer) throw new Error("issuer key is not registered by policy");
  assertExactKeys(issuer, ["key_id", "algorithm", "public_key_pem", "state"], [], "registered issuer");
  if (issuer.state !== "ACTIVE") throw new Error("issuer key is not active");
  if (issuer.algorithm !== "Ed25519") throw new Error("registered issuer algorithm must be Ed25519");
  assertString(issuer.public_key_pem, "registered issuer public_key_pem", null, 8192);
  return issuer;
}

function validateSession(session, policy, expectedRepository, now = new Date()) {
  assertExactKeys(
    session,
    ["schema", "session_id", "issuer_key_id", "issued_at", "expires_at", "subject", "repositories", "scope", "biometric", "signature"],
    [],
    "voice SSO session",
  );
  if (session.schema !== SESSION_SCHEMA) throw new Error(`unsupported session schema: ${session.schema}`);
  const sessionId = assertString(session.session_id, "session_id", ID_RE, 128);
  const issuerKeyId = assertString(session.issuer_key_id, "issuer_key_id", ID_RE, 128);
  const issuedAt = parseUtc(session.issued_at, "issued_at");
  const expiresAt = parseUtc(session.expires_at, "expires_at");
  const policyVoice = policy.voice_sso;
  assertExactKeys(
    policyVoice,
    ["primary_factor", "session_max_seconds", "command_max_seconds", "allow_all_product_owner_commands", "allow_external_effect_command_authorization", "external_effect_gate_resolution", "effect_classification"],
    ["semantic", "required_local_verifier_evidence"],
    "policy.voice_sso",
  );
  if (policyVoice.primary_factor !== "VOICE_BIOMETRIC_SSO") throw new Error("policy does not enable voice biometric SSO");
  if (!policyVoice.allow_all_product_owner_commands) throw new Error("policy does not allow all Product Owner commands");
  if (policyVoice.external_effect_gate_resolution !== "INDEPENDENT_EXECUTOR_REQUIRED") {
    throw new Error("external-effect gate resolution must remain independent");
  }
  if (expiresAt <= issuedAt || expiresAt - issuedAt > policyVoice.session_max_seconds * 1000) {
    throw new Error("voice SSO session lifetime is invalid");
  }
  const nowMilliseconds = now instanceof Date ? now.getTime() : Date.parse(now);
  if (!Number.isFinite(nowMilliseconds) || nowMilliseconds < issuedAt || nowMilliseconds >= expiresAt) {
    throw new Error("voice SSO session is not currently valid");
  }
  assertExactKeys(policy.product_owner, ["id", "role"], [], "policy.product_owner");
  if (policy.product_owner.role !== "PRODUCT_OWNER") throw new Error("configured subject is not a Product Owner");
  assertExactKeys(session.subject, ["product_owner_id"], [], "subject");
  if (session.subject.product_owner_id !== policy.product_owner.id) throw new Error("session subject is not the configured Product Owner");
  const repositories = assertArray(session.repositories, "repositories", 1, 8);
  for (const repository of repositories) assertString(repository, "repositories item", REPOSITORY_RE, 200);
  if (!repositories.includes(expectedRepository)) throw new Error("voice SSO session is not authorized for this repository");
  if (session.scope !== "ALL_PRODUCT_OWNER_COMMANDS") throw new Error("voice SSO session lacks Product Owner command scope");
  assertExactKeys(
    session.biometric,
    ["enrollment_id", "verifier_id", "verifier_version", "speaker_verdict", "liveness_verdict", "challenge_sha256", "audio_sha256"],
    [],
    "biometric",
  );
  assertString(session.biometric.enrollment_id, "biometric.enrollment_id", ID_RE, 128);
  assertString(session.biometric.verifier_id, "biometric.verifier_id", ID_RE, 128);
  assertString(session.biometric.verifier_version, "biometric.verifier_version", null, 160);
  if (session.biometric.speaker_verdict !== "MATCH") throw new Error("voice SSO requires a speaker match");
  if (session.biometric.liveness_verdict !== "LIVE") throw new Error("voice SSO requires a live presentation");
  assertString(session.biometric.challenge_sha256, "biometric.challenge_sha256", SHA256_RE, 64);
  assertString(session.biometric.audio_sha256, "biometric.audio_sha256", SHA256_RE, 64);
  const issuer = registeredIssuer(policy, issuerKeyId);
  verifySignature(session, issuer.public_key_pem, "voice SSO session");
  return { session_id: sessionId, issuer_key_id: issuerKeyId, issued_at: issuedAt, expires_at: expiresAt };
}

function validateCommand(command, session, policy, expectedTarget, consumedNonces = new Set(), now = new Date()) {
  if (!isPlainObject(expectedTarget)) throw new Error("expectedTarget must be an object");
  assertExactKeys(expectedTarget, ["repository", "ref", "head", "tree"], [], "expectedTarget");
  const verifiedSession = validateSession(session, policy, expectedTarget.repository, now);
  const policyVoice = policy.voice_sso;
  assertExactKeys(
    command,
    ["schema", "command_id", "session_id", "issuer_key_id", "repository", "target", "intent", "issued_at", "expires_at", "nonce_sha256", "session_sha256", "signature"],
    [],
    "voice SSO command",
  );
  if (command.schema !== COMMAND_SCHEMA) throw new Error(`unsupported command schema: ${command.schema}`);
  const commandId = assertString(command.command_id, "command_id", ID_RE, 128);
  if (command.session_id !== verifiedSession.session_id) throw new Error("command is not bound to the supplied voice SSO session");
  if (command.issuer_key_id !== verifiedSession.issuer_key_id) throw new Error("command issuer does not match the voice SSO session");
  if (command.repository !== expectedTarget.repository) throw new Error("command repository does not match the expected repository");
  assertExactKeys(command.target, ["ref", "head", "tree"], [], "command.target");
  assertString(command.target.ref, "command.target.ref", /^refs\/(heads|tags)\/[A-Za-z0-9._/-]+$/u, 255);
  if (command.target.ref !== expectedTarget.ref || command.target.head !== expectedTarget.head || command.target.tree !== expectedTarget.tree) {
    throw new Error("command target does not match the exact expected ref, head and tree");
  }
  assertString(command.target.head, "command.target.head", GIT_SHA1_RE, 40);
  assertString(command.target.tree, "command.target.tree", GIT_SHA1_RE, 40);
  assertExactKeys(command.intent, ["operation", "parameters", "parameters_sha256", "effect_class", "artifact_sha256s"], ["external_authorization"], "command.intent");
  const operation = assertString(command.intent.operation, "command.intent.operation", /^[A-Z][A-Z0-9_]{2,127}$/u, 128);
  assertOperationPermitted(policy, operation);
  if (!isPlainObject(command.intent.parameters)) throw new Error("command.intent.parameters must be an object");
  const canonicalParameters = canonicalJson(command.intent.parameters);
  if (Buffer.byteLength(canonicalParameters, "utf8") > 65536) throw new Error("command intent parameters exceed 65536 bytes");
  assertString(command.intent.parameters_sha256, "command.intent.parameters_sha256", SHA256_RE, 64);
  if (command.intent.parameters_sha256 !== canonicalDigest(command.intent.parameters)) {
    throw new Error("command intent parameters do not match parameters_sha256");
  }
  const artifactSha256s = assertArray(command.intent.artifact_sha256s, "command.intent.artifact_sha256s", 0, 64);
  for (const digest of artifactSha256s) assertString(digest, "command.intent.artifact_sha256s item", SHA256_RE, 64);
  if (!new Set(["READ_ONLY", "REPOSITORY_MUTATION", "EXTERNAL_EFFECT"]).has(command.intent.effect_class)) {
    throw new Error("command.intent.effect_class is invalid");
  }
  const classifiedEffect = effectClassForOperation(policyVoice, operation);
  if (command.intent.effect_class !== classifiedEffect) {
    throw new Error(`command effect class differs from policy classification: ${classifiedEffect}`);
  }
  if (command.intent.effect_class === "EXTERNAL_EFFECT") {
    if (!policy.voice_sso.allow_external_effect_command_authorization) throw new Error("policy does not allow voice SSO external-effect authorization");
    if (artifactSha256s.length === 0) throw new Error("external-effect commands require exact artifact digests");
    assertExactKeys(command.intent.external_authorization, ["single_use_authorization_id", "exact_artifact_sha256s"], [], "command.intent.external_authorization");
    assertString(command.intent.external_authorization.single_use_authorization_id, "external authorization id", ID_RE, 128);
    const exactArtifacts = assertArray(command.intent.external_authorization.exact_artifact_sha256s, "external authorization artifacts", 1, 64);
    for (const digest of exactArtifacts) assertString(digest, "external authorization artifact", SHA256_RE, 64);
    if (exactArtifacts.length !== artifactSha256s.length || exactArtifacts.some((digest, index) => digest !== artifactSha256s[index])) {
      throw new Error("external authorization artifacts do not exactly bind the command artifacts");
    }
  } else if (command.intent.external_authorization !== undefined) {
    throw new Error("external authorization is only valid for EXTERNAL_EFFECT commands");
  }
  const issuedAt = parseUtc(command.issued_at, "command.issued_at");
  const expiresAt = parseUtc(command.expires_at, "command.expires_at");
  const nowMilliseconds = now instanceof Date ? now.getTime() : Date.parse(now);
  if (expiresAt <= issuedAt || expiresAt - issuedAt > policy.voice_sso.command_max_seconds * 1000 || expiresAt > verifiedSession.expires_at) {
    throw new Error("voice SSO command lifetime is invalid");
  }
  if (!Number.isFinite(nowMilliseconds) || nowMilliseconds < issuedAt || nowMilliseconds >= expiresAt) {
    throw new Error("voice SSO command is not currently valid");
  }
  const nonce = assertString(command.nonce_sha256, "command.nonce_sha256", SHA256_RE, 64);
  if (consumedNonces.has(nonce)) throw new Error("voice SSO command nonce has already been consumed");
  if (command.session_sha256 !== canonicalDigest(session)) throw new Error("command session_sha256 does not bind the supplied voice SSO session");
  const issuer = registeredIssuer(policy, verifiedSession.issuer_key_id);
  verifySignature(command, issuer.public_key_pem, "voice SSO command");
  consumedNonces.add(nonce);
  return {
    command_id: commandId,
    command_sha256: canonicalDigest(command),
    effect_class: command.intent.effect_class,
    disposition: command.intent.effect_class === "EXTERNAL_EFFECT"
      ? "VOICE_SSO_IDENTITY_AND_INTENT_VERIFIED_EXTERNAL_EFFECT_GATES_PENDING"
      : "VOICE_SSO_IDENTITY_AND_INTENT_VERIFIED_REPOSITORY_GATES_PENDING",
  };
}

module.exports = {
  COMMAND_SCHEMA,
  SESSION_SCHEMA,
  canonicalDigest,
  canonicalJson,
  validateCommand,
  validateSession,
};
