"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { canonicalDigest, canonicalJson, validateCommand, validateSession } = require("../src/voice-sso.cjs");
const { resolveWorktreeTarget } = require("../src/voice-sso-runtime.cjs");

const NOW = new Date("2026-08-10T17:00:00Z");
const TARGET = {
  repository: "Goldkelch/qik-vrt",
  ref: "refs/heads/main",
  head: "fdf83b0c6f1059843ecf08842b40f4843ea8c7eb",
  tree: "7c834f434b0477a9f574f581a5bf7cb829b428c8",
};
const { privateKey, publicKey } = crypto.generateKeyPairSync("ed25519");
const DEFAULT_PARAMETERS = { branch: "agent/product-owner-voice-sso-v1" };

function sign(value) {
  const { signature, ...unsigned } = value;
  return {
    ...unsigned,
    signature: {
      algorithm: "Ed25519",
      value: crypto.sign(null, Buffer.from(canonicalJson(unsigned), "utf8"), privateKey).toString("base64"),
    },
  };
}

function policy() {
  const repositoryPolicy = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../../../policy/PRODUCT_OWNER_VOICE_SSO_V1.json"), "utf8"));
  return {
    ...repositoryPolicy,
    registered_issuers: [{
      key_id: "po-voice-sso-test-key",
      algorithm: "Ed25519",
      public_key_pem: publicKey.export({ type: "spki", format: "pem" }),
      state: "ACTIVE",
    }],
  };
}

function session(overrides = {}) {
  const value = {
    schema: "qikvrt-voice-sso-session/1.0",
    session_id: "voice-sso-session-20260810-170000",
    issuer_key_id: "po-voice-sso-test-key",
    issued_at: "2026-08-10T16:59:00Z",
    expires_at: "2026-08-10T17:10:00Z",
    subject: { product_owner_id: "Ingolf Lohmann" },
    repositories: ["Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"],
    scope: "ALL_PRODUCT_OWNER_COMMANDS",
    biometric: {
      enrollment_id: "ingolf-voice-enrollment-v1",
      verifier_id: "local-voice-sso-adapter",
      verifier_version: "1.0.0",
      speaker_verdict: "MATCH",
      liveness_verdict: "LIVE",
      challenge_sha256: "a".repeat(64),
      audio_sha256: "b".repeat(64),
    },
    ...overrides,
  };
  return sign(value);
}

function command(boundSession, overrides = {}) {
  const parameters = { ...DEFAULT_PARAMETERS };
  const value = {
    schema: "qikvrt-voice-sso-command/1.0",
    command_id: "voice-command-20260810-170000",
    session_id: boundSession.session_id,
    issuer_key_id: boundSession.issuer_key_id,
    repository: TARGET.repository,
    target: { ref: "refs/heads/main", head: TARGET.head, tree: TARGET.tree },
    intent: {
      operation: "CREATE_REVIEW_BRANCH",
      parameters,
      parameters_sha256: canonicalDigest(parameters),
      effect_class: "REPOSITORY_MUTATION",
      artifact_sha256s: [],
    },
    issued_at: "2026-08-10T16:59:30Z",
    expires_at: "2026-08-10T17:01:00Z",
    nonce_sha256: "d".repeat(64),
    session_sha256: canonicalDigest(boundSession),
    ...overrides,
  };
  return sign(value);
}

test("accepts a live Product Owner voice SSO session and a head-bound repository command", () => {
  const validSession = session();
  assert.equal(validateSession(validSession, policy(), TARGET.repository, NOW).session_id, validSession.session_id);
  const result = validateCommand(command(validSession), validSession, policy(), TARGET, new Set(), NOW);
  assert.equal(result.effect_class, "REPOSITORY_MUTATION");
  assert.equal(result.disposition, "VOICE_SSO_IDENTITY_AND_INTENT_VERIFIED_REPOSITORY_GATES_PENDING");
});

test("rejects a session without a live speaker match or with biometric payload fields", () => {
  const nonLive = session({ biometric: { ...session().biometric, liveness_verdict: "REPLAY" } });
  assert.throws(() => validateSession(nonLive, policy(), TARGET.repository, NOW), /live presentation/u);
  const leaked = session({ biometric: { ...session().biometric, voice_template: "never-store-this" } });
  assert.throws(() => validateSession(leaked, policy(), TARGET.repository, NOW), /unknown field/u);
});

test("rejects a command whose parameters, envelope, nonce or exact target have drifted", () => {
  const validSession = session();
  const nonceStore = new Set();
  const signedCommand = command(validSession);
  validateCommand(signedCommand, validSession, policy(), TARGET, nonceStore, NOW);
  assert.throws(() => validateCommand(signedCommand, validSession, policy(), TARGET, nonceStore, NOW), /already been consumed/u);
  const drifted = command(validSession, { target: { ref: "refs/heads/main", head: "e".repeat(40), tree: TARGET.tree } });
  assert.throws(() => validateCommand(drifted, validSession, policy(), TARGET, new Set(), NOW), /exact expected ref, head and tree/u);
  const wrongRef = command(validSession, { target: { ref: "refs/heads/release", head: TARGET.head, tree: TARGET.tree } });
  assert.throws(() => validateCommand(wrongRef, validSession, policy(), TARGET, new Set(), NOW), /exact expected ref, head and tree/u);
  const changedParameters = command(validSession);
  changedParameters.intent.parameters.branch = "agent/different-command";
  assert.throws(() => validateCommand(changedParameters, validSession, policy(), TARGET, new Set(), NOW), /parameters do not match/u);
  const tampered = command(validSession);
  tampered.command_id = "voice-command-tampered";
  assert.throws(() => validateCommand(tampered, validSession, policy(), TARGET, new Set(), NOW), /signature verification failed/u);
});

test("verifies external-effect voice intent only with exact bindings and independent gates pending", () => {
  const validSession = session();
  const externalParameters = { publication_id: "qik-vrt-example" };
  const external = command(validSession, {
    intent: {
      operation: "ZENODO_PUBLICATION",
      parameters: externalParameters,
      parameters_sha256: canonicalDigest(externalParameters),
      effect_class: "EXTERNAL_EFFECT",
      artifact_sha256s: ["f".repeat(64)],
      external_authorization: {
        single_use_authorization_id: "zenodo-auth-20260810-170000",
        exact_artifact_sha256s: ["f".repeat(64)],
      },
    },
    nonce_sha256: "1".repeat(64),
  });
  const result = validateCommand(external, validSession, policy(), TARGET, new Set(), NOW);
  assert.equal(result.disposition, "VOICE_SSO_IDENTITY_AND_INTENT_VERIFIED_EXTERNAL_EFFECT_GATES_PENDING");
  const downgraded = command(validSession, {
    intent: {
      operation: "ZENODO_PUBLICATION",
      parameters: externalParameters,
      parameters_sha256: canonicalDigest(externalParameters),
      effect_class: "REPOSITORY_MUTATION",
      artifact_sha256s: ["f".repeat(64)],
    },
    nonce_sha256: "0".repeat(64),
  });
  assert.throws(() => validateCommand(downgraded, validSession, policy(), TARGET, new Set(), NOW), /policy classification/u);
  const prohibited = command(validSession, {
    intent: {
      operation: "FORCE_PUSH",
      parameters: { ref: "refs/heads/main" },
      parameters_sha256: canonicalDigest({ ref: "refs/heads/main" }),
      effect_class: "EXTERNAL_EFFECT",
      artifact_sha256s: ["f".repeat(64)],
      external_authorization: {
        single_use_authorization_id: "force-push-must-remain-blocked",
        exact_artifact_sha256s: ["f".repeat(64)],
      },
    },
    nonce_sha256: "4".repeat(64),
  });
  assert.throws(() => validateCommand(prohibited, validSession, policy(), TARGET, new Set(), NOW), /prohibited by policy/u);
  const missingBinding = command(validSession, {
    intent: {
      operation: "ZENODO_PUBLICATION",
      parameters: externalParameters,
      parameters_sha256: canonicalDigest(externalParameters),
      effect_class: "EXTERNAL_EFFECT",
      artifact_sha256s: ["f".repeat(64)],
    },
    nonce_sha256: "2".repeat(64),
  });
  assert.throws(() => validateCommand(missingBinding, validSession, policy(), TARGET, new Set(), NOW), /external_authorization/u);
  const mismatchedBinding = command(validSession, {
    intent: {
      operation: "ZENODO_PUBLICATION",
      parameters: externalParameters,
      parameters_sha256: canonicalDigest(externalParameters),
      effect_class: "EXTERNAL_EFFECT",
      artifact_sha256s: ["f".repeat(64)],
      external_authorization: {
        single_use_authorization_id: "zenodo-auth-20260810-170001",
        exact_artifact_sha256s: ["0".repeat(64)],
      },
    },
    nonce_sha256: "3".repeat(64),
  });
  assert.throws(() => validateCommand(mismatchedBinding, validSession, policy(), TARGET, new Set(), NOW), /do not exactly bind/u);
});

test("derives the worktree target, keeps private inputs outside Git and persists replay state across CLI processes", (t) => {
  const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), "qikvrt-voice-sso-"));
  t.after(() => fs.rmSync(temporaryRoot, { recursive: true, force: true }));
  const repositoryRoot = path.join(temporaryRoot, "repository");
  const privateRoot = path.join(temporaryRoot, "private");
  fs.mkdirSync(path.join(repositoryRoot, "policy"), { recursive: true });
  fs.mkdirSync(path.join(repositoryRoot, "tools", "offline-audio-transcription", "bin"), { recursive: true });
  fs.mkdirSync(path.join(repositoryRoot, "tools", "offline-audio-transcription", "src"), { recursive: true });
  fs.mkdirSync(privateRoot, { mode: 0o700 });
  fs.writeFileSync(
    path.join(repositoryRoot, "policy", "PRODUCT_OWNER_VOICE_SSO_V1.json"),
    `${JSON.stringify(policy(), null, 2)}\n`,
    "utf8",
  );
  const packageRoot = path.resolve(__dirname, "..");
  for (const relative of ["bin/verify-voice-sso", "src/voice-sso.cjs", "src/voice-sso-runtime.cjs"]) {
    fs.copyFileSync(path.join(packageRoot, relative), path.join(repositoryRoot, "tools", "offline-audio-transcription", relative));
  }
  const git = (args) => childProcess.execFileSync("git", ["-C", repositoryRoot, ...args], { stdio: "ignore" });
  git(["init", "-b", "main"]);
  git(["remote", "add", "origin", "https://github.com/Goldkelch/qik-vrt.git"]);
  git(["add", "."]);
  git(["-c", "user.name=QIKVRT Test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture"]);
  const observedTarget = resolveWorktreeTarget(repositoryRoot);
  const now = Date.now();
  const utc = (milliseconds) => new Date(Math.floor(milliseconds / 1000) * 1000).toISOString().replace(".000Z", "Z");
  const liveSession = session({
    issued_at: utc(now - 30000),
    expires_at: utc(now + 600000),
  });
  const liveCommand = command(liveSession, {
    repository: observedTarget.repository,
    target: { ref: observedTarget.ref, head: observedTarget.head, tree: observedTarget.tree },
    issued_at: utc(now - 15000),
    expires_at: utc(now + 90000),
  });
  const sessionPath = path.join(privateRoot, "session.json");
  const commandPath = path.join(privateRoot, "command.json");
  const ledgerPath = path.join(privateRoot, "consumed-nonces.json");
  fs.writeFileSync(sessionPath, `${JSON.stringify(liveSession)}\n`, { encoding: "utf8", mode: 0o600 });
  fs.writeFileSync(commandPath, `${JSON.stringify(liveCommand)}\n`, { encoding: "utf8", mode: 0o600 });
  const cli = path.join(repositoryRoot, "tools", "offline-audio-transcription", "bin", "verify-voice-sso");
  const args = [cli, "--session", sessionPath, "--command", commandPath, "--nonce-ledger", ledgerPath];
  const first = childProcess.spawnSync(process.execPath, args, { encoding: "utf8" });
  assert.equal(first.status, 0, first.stderr);
  assert.match(first.stdout, /IDENTITY_AND_INTENT_VERIFIED/u);
  const replay = childProcess.spawnSync(process.execPath, args, { encoding: "utf8" });
  assert.equal(replay.status, 2);
  assert.match(replay.stderr, /already been consumed/u);
  const insideWorktree = childProcess.spawnSync(process.execPath, [
    cli,
    "--session", path.join(repositoryRoot, "policy", "PRODUCT_OWNER_VOICE_SSO_V1.json"),
    "--command", commandPath,
    "--nonce-ledger", ledgerPath,
  ], { encoding: "utf8" });
  assert.equal(insideWorktree.status, 2);
  assert.match(insideWorktree.stderr, /outside the Git worktree/u);
  const nextCommand = command(liveSession, {
    repository: observedTarget.repository,
    target: { ref: observedTarget.ref, head: observedTarget.head, tree: observedTarget.tree },
    issued_at: utc(now - 15000),
    expires_at: utc(now + 90000),
    nonce_sha256: "8".repeat(64),
  });
  const nextCommandPath = path.join(privateRoot, "next-command.json");
  fs.writeFileSync(nextCommandPath, `${JSON.stringify(nextCommand)}\n`, { encoding: "utf8", mode: 0o600 });
  const staleLedgerPath = path.join(privateRoot, "stale-ledger.json");
  fs.writeFileSync(`${staleLedgerPath}.lock`, `${JSON.stringify({ pid: 99999999, created_at: now - 600000, token: "stale-test-lock" })}\n`, { encoding: "utf8", mode: 0o600 });
  const recovered = childProcess.spawnSync(process.execPath, [cli, "--session", sessionPath, "--command", nextCommandPath, "--nonce-ledger", staleLedgerPath], { encoding: "utf8" });
  assert.equal(recovered.status, 0, recovered.stderr);
  const permissiveLedgerPath = path.join(privateRoot, "permissive-ledger.json");
  fs.writeFileSync(permissiveLedgerPath, `${JSON.stringify({ schema: "qikvrt-voice-sso-nonce-ledger/1.0", consumed_nonces: [] })}\n`, { encoding: "utf8", mode: 0o644 });
  const permissive = childProcess.spawnSync(process.execPath, [cli, "--session", sessionPath, "--command", nextCommandPath, "--nonce-ledger", permissiveLedgerPath], { encoding: "utf8" });
  assert.equal(permissive.status, 2);
  assert.match(permissive.stderr, /owner-only permissions/u);
  const dirtyPath = path.join(repositoryRoot, "UNTRACKED_VOICE_SSO_INPUT.json");
  fs.writeFileSync(dirtyPath, "{}\n", "utf8");
  const dirty = childProcess.spawnSync(process.execPath, args, { encoding: "utf8" });
  assert.equal(dirty.status, 2);
  assert.match(dirty.stderr, /clean exact-head worktree/u);
  fs.unlinkSync(dirtyPath);
  git(["remote", "set-url", "--add", "--push", "origin", "https://github.com/attacker/other.git"]);
  const wrongPushRepository = childProcess.spawnSync(process.execPath, args, { encoding: "utf8" });
  assert.equal(wrongPushRepository.status, 2);
  assert.match(wrongPushRepository.stderr, /fetch and push repository identities differ/u);
});
