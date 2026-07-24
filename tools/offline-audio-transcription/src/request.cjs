"use strict";

const crypto = require("node:crypto");
const path = require("node:path");

const SCHEMA_VERSION = "1.0.0";
const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set([
  ".aac", ".flac", ".m4a", ".mov", ".mp3", ".mp4", ".ogg", ".wav", ".webm",
]);

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

function assertString(value, label, pattern, maxLength) {
  if (typeof value !== "string" || value.length === 0 || value.length > maxLength) {
    throw new Error(`${label} must be a non-empty string no longer than ${maxLength} characters`);
  }
  if (pattern && !pattern.test(value)) throw new Error(`${label} has an invalid format`);
  return value;
}

function assertNumber(value, label, minimum, maximum, integer = false) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < minimum || value > maximum) {
    throw new Error(`${label} must be between ${minimum} and ${maximum}`);
  }
  if (integer && !Number.isInteger(value)) throw new Error(`${label} must be an integer`);
  return value;
}

function validateFilename(filename) {
  assertString(filename, "source.filename", null, 180);
  const normalized = filename.normalize("NFKC");
  if (normalized !== filename) throw new Error("source.filename must already be NFKC-normalized");
  if (path.basename(filename) !== filename || filename === "." || filename === "..") {
    throw new Error("source.filename must be a basename without path components");
  }
  if (/^[.]/u.test(filename) || /[\u0000-\u001f\u007f]/u.test(filename)) {
    throw new Error("source.filename contains a forbidden leading dot or control character");
  }
  if (!/^[\p{L}\p{N}][\p{L}\p{N} ._()\-]+$/u.test(filename)) {
    throw new Error("source.filename contains unsupported characters");
  }
  const extension = path.extname(filename).toLowerCase();
  if (!ALLOWED_EXTENSIONS.has(extension)) throw new Error(`source.filename extension is not allowed: ${extension}`);
  return filename;
}

function validateRequest(value, expectedRepository) {
  assertExactKeys(value, ["schemaVersion", "requestId", "source", "transcription"], ["response"], "request");
  if (value.schemaVersion !== SCHEMA_VERSION) throw new Error(`unsupported schemaVersion: ${value.schemaVersion}`);
  const requestId = assertString(value.requestId, "requestId", /^[a-z0-9][a-z0-9._-]{2,79}$/u, 80);

  assertExactKeys(
    value.source,
    ["kind", "repository", "blobSha", "sha256", "bytes", "filename"],
    [],
    "source",
  );
  if (value.source.kind !== "github-git-blob") throw new Error("source.kind must be github-git-blob");
  const repository = assertString(
    value.source.repository,
    "source.repository",
    /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/u,
    200,
  );
  if (repository !== expectedRepository) throw new Error("source.repository must equal the workflow repository");
  const blobSha = assertString(value.source.blobSha, "source.blobSha", /^[0-9a-f]{40}$/u, 40);
  const sha256 = assertString(value.source.sha256, "source.sha256", /^[0-9a-f]{64}$/u, 64);
  const bytes = assertNumber(value.source.bytes, "source.bytes", 1, MAX_AUDIO_BYTES, true);
  const filename = validateFilename(value.source.filename);

  assertExactKeys(
    value.transcription,
    ["language"],
    ["chunkSeconds", "overlapSeconds", "threads"],
    "transcription",
  );
  const language = assertString(value.transcription.language, "transcription.language", /^[a-z]{2,3}$/u, 3);
  const chunkSeconds = value.transcription.chunkSeconds ?? 28;
  const overlapSeconds = value.transcription.overlapSeconds ?? 1.5;
  const threads = value.transcription.threads ?? 4;
  assertNumber(chunkSeconds, "transcription.chunkSeconds", 1, 29, false);
  assertNumber(overlapSeconds, "transcription.overlapSeconds", 0, chunkSeconds - Number.EPSILON, false);
  assertNumber(threads, "transcription.threads", 1, 16, true);

  let response = null;
  if (value.response !== undefined) {
    assertExactKeys(value.response, ["instruction"], [], "response");
    response = {
      instruction: assertString(value.response.instruction, "response.instruction", null, 8000),
    };
  }

  return {
    schemaVersion: SCHEMA_VERSION,
    requestId,
    source: { kind: "github-git-blob", repository, blobSha, sha256, bytes, filename },
    transcription: { language, chunkSeconds, overlapSeconds, threads },
    response,
  };
}

function decodeGitBlobPayload(payload, request) {
  assertExactKeys(payload, ["content", "encoding"], ["sha", "size", "url", "node_id"], "GitHub blob response");
  if (payload.encoding !== "base64") throw new Error("GitHub blob response encoding must be base64");
  const compact = assertString(payload.content, "GitHub blob response content", null, Math.ceil(MAX_AUDIO_BYTES * 4 / 3) + 4096)
    .replace(/\s+/gu, "");
  if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/u.test(compact)) {
    throw new Error("GitHub blob response contains invalid base64");
  }
  const audio = Buffer.from(compact, "base64");
  if (audio.length !== request.source.bytes) throw new Error("audio byte count does not match request");
  if (payload.size !== undefined && payload.size !== audio.length) throw new Error("GitHub blob size does not match decoded bytes");
  const digest = crypto.createHash("sha256").update(audio).digest("hex");
  if (digest !== request.source.sha256) throw new Error("audio SHA-256 does not match request");
  return audio;
}

module.exports = {
  ALLOWED_EXTENSIONS,
  MAX_AUDIO_BYTES,
  SCHEMA_VERSION,
  decodeGitBlobPayload,
  validateFilename,
  validateRequest,
};
