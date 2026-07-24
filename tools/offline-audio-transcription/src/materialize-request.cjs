#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const https = require("node:https");
const path = require("node:path");
const { decodeGitBlobPayload, validateRequest } = require("./request.cjs");

process.umask(0o077);
const MAX_REQUEST_BYTES = 64 * 1024;

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (["--request", "--repository", "--output-dir"].includes(argument)) result[argument.slice(2)] = argv[++index];
    else if (argument === "--help") result.help = true;
    else throw new Error(`unknown argument: ${argument}`);
  }
  return result;
}

function usage() {
  return "Usage: materialize-request --request FILE --repository OWNER/REPO --output-dir DIR\n";
}

function readJsonFile(file, maximumBytes) {
  const stat = fs.statSync(file);
  if (!stat.isFile()) throw new Error(`not a regular file: ${file}`);
  if (stat.size < 2 || stat.size > maximumBytes) throw new Error(`JSON file size is outside the accepted range: ${file}`);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function getJson(url, token) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, {
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "User-Agent": "qik-vrt-offline-audio-request/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      timeout: 30_000,
    }, (response) => {
      const chunks = [];
      let bytes = 0;
      response.on("data", (chunk) => {
        bytes += chunk.length;
        if (bytes > 40 * 1024 * 1024) {
          request.destroy(new Error("GitHub blob response exceeds the maximum accepted size"));
          return;
        }
        chunks.push(chunk);
      });
      response.on("end", () => {
        const body = Buffer.concat(chunks).toString("utf8");
        if (response.statusCode !== 200) {
          reject(new Error(`GitHub blob request failed with HTTP ${response.statusCode}`));
          return;
        }
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(new Error(`GitHub blob response is not valid JSON: ${error.message}`));
        }
      });
    });
    request.on("timeout", () => request.destroy(new Error("GitHub blob request timed out")));
    request.on("error", reject);
  });
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  if (!options.request || !options.repository || !options["output-dir"]) throw new Error("--request, --repository and --output-dir are required");
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error("GITHUB_TOKEN is required");

  const requestPath = path.resolve(options.request);
  const outputDir = path.resolve(options["output-dir"]);
  const validated = validateRequest(readJsonFile(requestPath, MAX_REQUEST_BYTES), options.repository);
  const [owner, repository] = validated.source.repository.split("/");
  const apiUrl = `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repository)}/git/blobs/${validated.source.blobSha}`;
  const payload = await getJson(apiUrl, token);
  const audio = decodeGitBlobPayload(payload, validated);

  fs.mkdirSync(outputDir, { recursive: true, mode: 0o700 });
  const audioPath = path.join(outputDir, validated.source.filename);
  const receiptPath = path.join(outputDir, `${validated.requestId}.materialized-request.json`);
  fs.writeFileSync(audioPath, audio, { flag: "wx", mode: 0o600 });
  fs.writeFileSync(receiptPath, `${JSON.stringify({
    schemaVersion: "1.0.0",
    request: validated,
    materialized: {
      filename: path.basename(audioPath),
      bytes: audio.length,
      sha256: validated.source.sha256,
      sourceBlobSha: validated.source.blobSha,
    },
  }, null, 2)}\n`, { flag: "wx", mode: 0o600 });

  process.stdout.write(`${JSON.stringify({
    requestId: validated.requestId,
    audioPath,
    receiptPath,
    transcription: validated.transcription,
    response: validated.response,
  })}\n`);
}

main().catch((error) => {
  process.stderr.write(`materialize-request: ${error.message}\n`);
  process.exitCode = 1;
});
