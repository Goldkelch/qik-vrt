"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const test = require("node:test");
const { decodeGitBlobPayload, MAX_AUDIO_BYTES, validateRequest } = require("../src/request.cjs");

function validRequest(audio = Buffer.from("qik-vrt-audio")) {
  return {
    schemaVersion: "1.0.0",
    requestId: "audio-20260724-103937",
    source: {
      kind: "github-git-blob",
      repository: "Goldkelch/qik-vrt",
      blobSha: "a".repeat(40),
      sha256: crypto.createHash("sha256").update(audio).digest("hex"),
      bytes: audio.length,
      filename: "AUDIO-2026-07-24-10-39-37(1).m4a",
    },
    transcription: { language: "de" },
    response: { instruction: "Prüfe das akustisch gegebene Kommando am Repositorystand." },
  };
}

test("validates and fills bounded defaults", () => {
  const result = validateRequest(validRequest(), "Goldkelch/qik-vrt");
  assert.deepEqual(result.transcription, { language: "de", chunkSeconds: 28, overlapSeconds: 1.5, threads: 4 });
});

test("rejects repository substitution", () => {
  assert.throws(() => validateRequest(validRequest(), "ingolf-lohmann/qik-vrt"), /workflow repository/u);
});

test("rejects path traversal and hidden filenames", () => {
  const traversal = validRequest();
  traversal.source.filename = "../audio.m4a";
  assert.throws(() => validateRequest(traversal, "Goldkelch/qik-vrt"), /basename/u);
  const hidden = validRequest();
  hidden.source.filename = ".audio.m4a";
  assert.throws(() => validateRequest(hidden, "Goldkelch/qik-vrt"), /leading dot/u);
});

test("rejects oversized input and unknown fields", () => {
  const oversized = validRequest();
  oversized.source.bytes = MAX_AUDIO_BYTES + 1;
  assert.throws(() => validateRequest(oversized, "Goldkelch/qik-vrt"), /between/u);
  const unknown = validRequest();
  unknown.source.url = "https://example.invalid/audio";
  assert.throws(() => validateRequest(unknown, "Goldkelch/qik-vrt"), /unknown field/u);
});

test("decodes a GitHub blob only when byte count and SHA-256 match", () => {
  const audio = Buffer.from("verified audio bytes");
  const request = validateRequest(validRequest(audio), "Goldkelch/qik-vrt");
  const payload = { content: audio.toString("base64"), encoding: "base64", size: audio.length };
  assert.deepEqual(decodeGitBlobPayload(payload, request), audio);
  payload.content = Buffer.from("different").toString("base64");
  assert.throws(() => decodeGitBlobPayload(payload, request), /byte count|SHA-256/u);
});

test("rejects malformed base64 instead of accepting a lossy decode", () => {
  const audio = Buffer.from("verified audio bytes");
  const request = validateRequest(validRequest(audio), "Goldkelch/qik-vrt");
  assert.throws(
    () => decodeGitBlobPayload({ content: "@@@=", encoding: "base64" }, request),
    /invalid base64/u,
  );
});
