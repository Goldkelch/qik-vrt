"use strict";

const childProcess = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const LEDGER_SCHEMA = "qikvrt-voice-sso-nonce-ledger/1.0";
const POLICY_PATH = "policy/PRODUCT_OWNER_VOICE_SSO_V1.json";
const SHA256_RE = /^[0-9a-f]{64}$/u;
const ISO_UTC_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/u;
const MAX_ACTIVE_NONCES = 100000;
const STALE_LOCK_MILLISECONDS = 300000;

function git(repoRoot, args) {
  try {
    return childProcess.execFileSync("git", ["-C", repoRoot, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
  } catch (error) {
    const detail = error.stderr ? String(error.stderr).trim() : error.message;
    throw new Error(`git worktree observation failed: ${detail}`);
  }
}

function repositoryFromRemote(remote) {
  const patterns = [
    /^https:\/\/github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git)?$/u,
    /^git@github\.com:([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git)?$/u,
    /^ssh:\/\/git@github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git)?$/u,
  ];
  for (const pattern of patterns) {
    const match = remote.match(pattern);
    if (match) return `${match[1]}/${match[2]}`;
  }
  throw new Error("origin must be an exact github.com repository remote");
}

function resolveWorktreeTarget(repoRoot) {
  const requestedRoot = fs.realpathSync(path.resolve(repoRoot));
  const observedRoot = fs.realpathSync(git(requestedRoot, ["rev-parse", "--show-toplevel"]));
  if (requestedRoot !== observedRoot) throw new Error("verifier root must name the exact Git worktree root");
  const ref = git(observedRoot, ["symbolic-ref", "--quiet", "HEAD"]);
  const head = git(observedRoot, ["rev-parse", "--verify", "HEAD^{commit}"]);
  const tree = git(observedRoot, ["rev-parse", "--verify", `${head}^{tree}`]);
  if (git(observedRoot, ["symbolic-ref", "--quiet", "HEAD"]) !== ref || git(observedRoot, ["rev-parse", "--verify", "HEAD^{commit}"]) !== head) {
    throw new Error("Git ref or head moved during target observation");
  }
  if (git(observedRoot, ["status", "--porcelain=v1", "--untracked-files=all"]) !== "") {
    throw new Error("voice SSO requires a clean exact-head worktree");
  }
  const repository = repositoryFromRemote(git(observedRoot, ["remote", "get-url", "origin"]));
  const pushUrls = git(observedRoot, ["remote", "get-url", "--push", "--all", "origin"]).split(/\r?\n/u).filter(Boolean);
  if (pushUrls.length !== 1) throw new Error("origin must have exactly one push URL");
  if (repositoryFromRemote(pushUrls[0]) !== repository) throw new Error("origin fetch and push repository identities differ");
  return { repo_root: observedRoot, repository, ref, head, tree };
}

function readHeadPolicy(target) {
  const raw = git(target.repo_root, ["show", `${target.head}:${POLICY_PATH}`]);
  if (Buffer.byteLength(raw, "utf8") > 1048576) throw new Error("canonical voice SSO policy exceeds 1 MiB");
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`canonical voice SSO policy is invalid JSON: ${error.message}`);
  }
}

function privatePathOutsideWorktree(candidate, repoRoot, label, mustExist) {
  const resolvedRoot = fs.realpathSync(repoRoot);
  const requested = path.resolve(candidate);
  const parent = fs.realpathSync(path.dirname(requested));
  const resolved = path.join(parent, path.basename(requested));
  if (resolved === resolvedRoot || resolved.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error(`${label} must remain outside the Git worktree`);
  }
  assertOwnerOnly(fs.statSync(parent), `${label} parent directory`);
  if (fs.existsSync(resolved)) {
    const stat = fs.lstatSync(resolved);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${label} must be a regular non-symlink file`);
    assertOwnerOnly(stat, label);
  } else if (mustExist) {
    throw new Error(`${label} does not exist`);
  }
  return resolved;
}

function assertOwnerOnly(stat, label) {
  if (typeof process.getuid === "function" && stat.uid !== process.getuid()) throw new Error(`${label} must be owned by the current user`);
  if ((stat.mode & 0o077) !== 0) throw new Error(`${label} must have owner-only permissions`);
}

function readPrivateJson(candidate, repoRoot, label) {
  const resolved = privatePathOutsideWorktree(candidate, repoRoot, label, true);
  const stat = fs.statSync(resolved);
  if (stat.size > 1048576) throw new Error(`${label} exceeds 1 MiB`);
  try {
    return JSON.parse(fs.readFileSync(resolved, "utf8"));
  } catch (error) {
    throw new Error(`cannot read ${label}: ${error.message}`);
  }
}

function readLedger(ledgerPath, nowMilliseconds) {
  if (!fs.existsSync(ledgerPath)) return [];
  const stat = fs.lstatSync(ledgerPath);
  if (stat.isSymbolicLink() || !stat.isFile() || stat.size > 16777216) throw new Error("nonce ledger must be a bounded regular file");
  assertOwnerOnly(stat, "nonce ledger");
  let value;
  try {
    value = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));
  } catch (error) {
    throw new Error(`nonce ledger is invalid JSON: ${error.message}`);
  }
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).sort().join(",") !== "consumed_nonces,schema") {
    throw new Error("nonce ledger has an invalid shape");
  }
  if (value.schema !== LEDGER_SCHEMA || !Array.isArray(value.consumed_nonces) || value.consumed_nonces.length > 200000) {
    throw new Error("nonce ledger has an invalid schema or size");
  }
  const seen = new Set();
  const active = [];
  for (const entry of value.consumed_nonces) {
    if (!entry || typeof entry !== "object" || Array.isArray(entry) || Object.keys(entry).sort().join(",") !== "expires_at,nonce_sha256") {
      throw new Error("nonce ledger entry has an invalid shape");
    }
    if (typeof entry.nonce_sha256 !== "string" || !SHA256_RE.test(entry.nonce_sha256) || seen.has(entry.nonce_sha256)) {
      throw new Error("nonce ledger contains an invalid or duplicate nonce");
    }
    if (typeof entry.expires_at !== "string" || !ISO_UTC_RE.test(entry.expires_at) || !Number.isFinite(Date.parse(entry.expires_at))) {
      throw new Error("nonce ledger contains an invalid expiry");
    }
    seen.add(entry.nonce_sha256);
    if (Date.parse(entry.expires_at) > nowMilliseconds) active.push(entry);
  }
  return active;
}

function fsyncDirectory(directory) {
  const descriptor = fs.openSync(directory, "r");
  try {
    fs.fsyncSync(descriptor);
  } finally {
    fs.closeSync(descriptor);
  }
}

function processIsAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    if (error.code === "ESRCH") return false;
    return true;
  }
}

function acquireLock(lockPath, nowMilliseconds) {
  const directory = path.dirname(lockPath);
  const create = () => {
    const token = crypto.randomUUID();
    const descriptor = fs.openSync(lockPath, "wx", 0o600);
    try {
      fs.writeFileSync(descriptor, `${JSON.stringify({ pid: process.pid, created_at: nowMilliseconds, token })}\n`, "utf8");
      fs.fsyncSync(descriptor);
      fsyncDirectory(directory);
      return { descriptor, token };
    } catch (error) {
      fs.closeSync(descriptor);
      if (fs.existsSync(lockPath)) fs.unlinkSync(lockPath);
      throw error;
    }
  };
  try {
    return create();
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  const stat = fs.lstatSync(lockPath);
  if (stat.isSymbolicLink() || !stat.isFile() || stat.size > 4096) throw new Error("nonce ledger lock is invalid");
  assertOwnerOnly(stat, "nonce ledger lock");
  let stale;
  try {
    stale = JSON.parse(fs.readFileSync(lockPath, "utf8"));
  } catch (error) {
    throw new Error(`nonce ledger lock is unreadable: ${error.message}`);
  }
  if (!stale || !Number.isSafeInteger(stale.pid) || stale.pid <= 0 || !Number.isFinite(stale.created_at) || typeof stale.token !== "string") {
    throw new Error("nonce ledger lock has an invalid shape");
  }
  if (nowMilliseconds - stale.created_at <= STALE_LOCK_MILLISECONDS || processIsAlive(stale.pid)) {
    throw new Error("nonce ledger is locked by another verifier");
  }
  fs.unlinkSync(lockPath);
  fsyncDirectory(directory);
  return create();
}

function consumeNonce(ledgerCandidate, repoRoot, command, callback, now = new Date()) {
  const ledgerPath = privatePathOutsideWorktree(ledgerCandidate, repoRoot, "nonce ledger", false);
  const lockPath = `${ledgerPath}.lock`;
  let lock;
  let temporaryPath;
  try {
    const nowMilliseconds = now instanceof Date ? now.getTime() : Date.parse(now);
    if (!Number.isFinite(nowMilliseconds)) throw new Error("nonce ledger observation time is invalid");
    lock = acquireLock(lockPath, nowMilliseconds);
    const activeEntries = readLedger(ledgerPath, nowMilliseconds);
    if (activeEntries.length >= MAX_ACTIVE_NONCES) throw new Error("nonce ledger active-entry capacity is exhausted");
    const consumed = new Set(activeEntries.map((entry) => entry.nonce_sha256));
    const result = callback(consumed);
    if (!consumed.has(command.nonce_sha256)) throw new Error("validator did not consume the command nonce");
    activeEntries.push({ nonce_sha256: command.nonce_sha256, expires_at: command.expires_at });
    activeEntries.sort((left, right) => left.nonce_sha256.localeCompare(right.nonce_sha256));
    temporaryPath = `${ledgerPath}.tmp-${process.pid}`;
    const temporaryDescriptor = fs.openSync(temporaryPath, "wx", 0o600);
    try {
      fs.writeFileSync(temporaryDescriptor, `${JSON.stringify({ schema: LEDGER_SCHEMA, consumed_nonces: activeEntries }, null, 2)}\n`, "utf8");
      fs.fsyncSync(temporaryDescriptor);
    } finally {
      fs.closeSync(temporaryDescriptor);
    }
    fs.renameSync(temporaryPath, ledgerPath);
    fsyncDirectory(path.dirname(ledgerPath));
    temporaryPath = undefined;
    return result;
  } finally {
    if (temporaryPath && fs.existsSync(temporaryPath)) fs.unlinkSync(temporaryPath);
    if (lock !== undefined) {
      fs.closeSync(lock.descriptor);
      if (fs.existsSync(lockPath)) {
        const current = JSON.parse(fs.readFileSync(lockPath, "utf8"));
        if (current.token !== lock.token) throw new Error("nonce ledger lock ownership changed unexpectedly");
        fs.unlinkSync(lockPath);
        fsyncDirectory(path.dirname(lockPath));
      }
    }
  }
}

module.exports = {
  consumeNonce,
  readHeadPolicy,
  readPrivateJson,
  resolveWorktreeTarget,
};
