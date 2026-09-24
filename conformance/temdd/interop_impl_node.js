#!/usr/bin/env node
"use strict";

const fs = require("fs");
const KEY = /^[A-Za-z0-9_.:-]+$/u;
const DECISIONS = new Set(["ACCEPT", "REJECT", "HOLD_UNVERIFIED"]);

function fail(code) { throw new Error(code); }

function validUnicodeScalarString(s) {
  for (let i = 0; i < s.length; i++) {
    const u = s.charCodeAt(i);
    if (u >= 0xD800 && u <= 0xDBFF) {
      if (i + 1 >= s.length) return false;
      const v = s.charCodeAt(++i);
      if (v < 0xDC00 || v > 0xDFFF) return false;
    } else if (u >= 0xDC00 && u <= 0xDFFF) {
      return false;
    }
  }
  return true;
}

function validateDomain(value) {
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "string") {
    if (!validUnicodeScalarString(value)) fail("UNPAIRED_SURROGATE");
    return;
  }
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) fail("NON_CANONICAL_NUMBER");
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) validateDomain(item);
    return;
  }
  if (typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (!KEY.test(key)) fail("NON_CANONICAL_OBJECT_KEY");
      validateDomain(item);
    }
    return;
  }
  fail("UNSUPPORTED_JSON_VALUE");
}

function canonicalize(value) {
  validateDomain(value);
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonicalize).join(",") + "]";
  const keys = Object.keys(value).sort();
  return "{" + keys.map(k => JSON.stringify(k) + ":" + canonicalize(value[k])).join(",") + "}";
}

function sameJson(a, b) {
  return canonicalize(a) === canonicalize(b);
}

function evaluate(inp) {
  if (inp === null || typeof inp !== "object" || Array.isArray(inp)) fail("INPUT_OBJECT_REQUIRED");
  if (inp.canonicalization !== "temdd_canonical_json_v1") fail("CANONICAL_PROFILE_MISMATCH");
  const data = inp.data;
  const policy = inp.policy;
  const subjectValue = inp.subject;
  const evidence = inp.evidence;
  if (data === null || typeof data !== "object" || Array.isArray(data) ||
      policy === null || typeof policy !== "object" || Array.isArray(policy) ||
      subjectValue === null || typeof subjectValue !== "object" || Array.isArray(subjectValue) ||
      !Array.isArray(evidence)) fail("INPUT_MODEL_INVALID");
  if (policy.evaluation_semantics !== "temdd_decision_v1") fail("EVALUATION_SEMANTICS_MISMATCH");
  const dataEquals = policy.data_equals;
  const required = policy.required_evidence_types;
  if (dataEquals === null || typeof dataEquals !== "object" || Array.isArray(dataEquals) ||
      !Array.isArray(required) || !required.every(x => typeof x === "string")) fail("POLICY_MODEL_INVALID");
  if (new Set(required).size !== required.length) fail("DUPLICATE_REQUIRED_EVIDENCE_TYPE");
  for (const [key, expected] of Object.entries(dataEquals)) {
    if (!Object.prototype.hasOwnProperty.call(data, key) || !sameJson(data[key], expected)) return "REJECT";
  }
  for (const evidenceType of required) {
    const candidates = evidence.filter(item => item !== null && typeof item === "object" && !Array.isArray(item) && item.type === evidenceType);
    if (candidates.length !== 1) return "HOLD_UNVERIFIED";
    const item = candidates[0];
    if (item.fresh !== true || !sameJson(item.subject, subjectValue)) return "HOLD_UNVERIFIED";
    if (item.assertion !== true) {
      if (item.assertion === false) return "REJECT";
      return "HOLD_UNVERIFIED";
    }
  }
  return "ACCEPT";
}

try {
  const inp = JSON.parse(fs.readFileSync(0, "utf8"));
  const result = {canonical: canonicalize(inp), decision: evaluate(inp)};
  if (!DECISIONS.has(result.decision)) fail("DECISION_DOMAIN_VIOLATION");
  process.stdout.write(JSON.stringify(result) + "\n");
} catch (err) {
  process.stderr.write("HOLD_UNVERIFIED " + err.message + "\n");
  process.exit(2);
}
