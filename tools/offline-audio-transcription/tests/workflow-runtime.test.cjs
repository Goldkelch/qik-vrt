// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repositoryRoot = path.resolve(__dirname, "../../..");
const workflowPath = path.join(repositoryRoot, ".github/workflows/qikvrt_audio_request.yml");

function workflow() {
  return fs.readFileSync(workflowPath, "utf8");
}

test("audio request installs a missing media runtime before materializing source bytes", () => {
  const value = workflow();
  const install = value.indexOf("Install and verify required media runtime before input materialization");
  const materialize = value.indexOf("Materialize authenticated Git blob and verify source bytes");

  assert.notEqual(install, -1);
  assert.notEqual(materialize, -1);
  assert.ok(install < materialize, "media provisioning must precede source materialization");
  assert.match(value, /command -v ffmpeg/);
  assert.match(value, /command -v ffprobe/);
  assert.match(value, /apt-get update -o Acquire::Retries=3/);
  assert.match(value, /apt-get install --yes --no-install-recommends ffmpeg/);
  assert.match(value, /contents: read/);
});

test("media installation occurs before the productive blob materialization and transcription", () => {
  const value = workflow();
  const install = value.indexOf("apt-get install --yes --no-install-recommends ffmpeg");
  const blob = value.lastIndexOf("node src/materialize-request.cjs");
  const transcribe = value.lastIndexOf("./bin/transcribe-audio");

  assert.ok(install >= 0 && blob >= 0 && transcribe >= 0);
  assert.ok(install < blob);
  assert.ok(blob < transcribe);
});
