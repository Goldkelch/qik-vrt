import { readFileSync } from "node:fs";
import { ClaimSchema, ManifestSchema, type Claim, type Manifest } from "./schema.ts";
import { readJson, root, sha256, walkFiles } from "./common.ts";

export type CheckResult = {
  id: number;
  name: string;
  pass: boolean;
  details: string;
};

const compatibility: Record<string, Set<string>> = {
  MATHEMATICAL_THEOREM: new Set(["PROVED", "FALSE_IN_GENERAL"]),
  MODEL_DEFINITION: new Set(["DEFINED"]),
  MODEL_THEOREM: new Set(["PROVED", "PROVED_CONDITIONAL", "REFUTED_IN_MODEL"]),
  CORRESPONDENCE_HYPOTHESIS: new Set(["OPEN_EMPIRICAL", "UNSUPPORTED"]),
  EMPIRICAL_CLAIM: new Set(["ESTABLISHED_BACKGROUND", "OPEN_EMPIRICAL", "UNSUPPORTED"]),
  INTERPRETATION: new Set(["INTERPRETIVE"]),
  CAUSAL_CLAIM: new Set(["PROVED_CONDITIONAL", "OPEN_EMPIRICAL", "UNSUPPORTED", "REFUTED_IN_MODEL"]),
  ONTOLOGICAL_INTERPRETATION: new Set(["INTERPRETIVE"]),
  NORMATIVE_CONCLUSION: new Set(["NORMATIVE"])
};

export function loadPackage(): { manifest: Manifest; claims: Claim[] } {
  const manifest = ManifestSchema.parse(readJson("manifest.json"));
  const raw = readJson(manifest.claimsFile);
  if (!Array.isArray(raw)) throw new Error("claim matrix is not an array");
  return { manifest, claims: raw.map((x) => ClaimSchema.parse(x)) };
}

function leanSource(): string {
  return walkFiles("QIKVRTFormalization")
    .filter((p) => p.endsWith(".lean"))
    .concat(["QIKVRTFormalization.lean"])
    .map((p) => readFileSync(new URL(p, root), "utf8"))
    .join("\n");
}

function stripLeanComments(source: string): string {
  let previous = source;
  let current = previous.replace(/\/\-[\s\S]*?\-\//g, "");
  while (current !== previous) {
    previous = current;
    current = previous.replace(/\/\-[\s\S]*?\-\//g, "");
  }
  return current.replace(/--.*$/gm, "");
}

function referenceNames(ref: string): string[] {
  return ref.split(";").map((s) => s.trim().split(".").at(-1)!).filter(Boolean);
}

function hasDeclaration(source: string, name: string): boolean {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`\\b(?:theorem|def|structure|inductive)\\s+${escaped}\\b`).test(source);
}

export function evaluateChecks(manifest: Manifest, claims: Claim[]): CheckResult[] {
  const results: CheckResult[] = [];
  const add = (id: number, name: string, pass: boolean, details: string) =>
    results.push({ id, name, pass, details });

  add(1, "Schema", true, `manifest and ${claims.length} claims conform to Zod schemas`);

  const sourcePdf = "source/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf";
  const sourceTex = "source/Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex";
  const sourceOk = sha256(sourcePdf) === manifest.source.pdfSha256 &&
    sha256(sourceTex) === manifest.source.texSha256;
  add(2, "Source provenance and hashes", sourceOk,
    sourceOk ? "62-page Zenodo PDF and TeX match the published SHA-256 values" : "source hash mismatch");

  const ids = claims.map((c) => c.id);
  const unique = new Set(ids).size === ids.length;
  add(3, "Unique claim identifiers", unique, unique ? `${ids.length} unique IDs` : "duplicate claim IDs found");

  const incompatible = claims.filter((c) => !compatibility[c.kind]?.has(c.status));
  add(4, "Kind/status compatibility", incompatible.length === 0,
    incompatible.length ? incompatible.map((c) => c.id).join(", ") : "no epistemic category collapse");

  const proofMissing = claims.filter((c) =>
    ["PROVED", "PROVED_CONDITIONAL", "REFUTED_IN_MODEL"].includes(c.status) && !c.formalReference);
  add(5, "Formal references for theorem-level claims", proofMissing.length === 0,
    proofMissing.length ? proofMissing.map((c) => c.id).join(", ") : "all theorem-level claims name formal declarations");

  const assumptionMissing = claims.filter((c) =>
    c.status === "PROVED_CONDITIONAL" && c.assumptions.length === 0);
  add(6, "Explicit assumptions for conditional proofs", assumptionMissing.length === 0,
    assumptionMissing.length ? assumptionMissing.map((c) => c.id).join(", ") : "all conditional proofs expose assumptions");

  const falsificationMissing = claims.filter((c) =>
    ["OPEN_EMPIRICAL", "UNSUPPORTED"].includes(c.status) && c.falsification.length === 0);
  add(7, "Falsification targets for open empirical claims", falsificationMissing.length === 0,
    falsificationMissing.length ? falsificationMissing.map((c) => c.id).join(", ") : "all open empirical claims have test or failure criteria");

  const interpretiveOverclaim = claims.filter((c) =>
    ["INTERPRETATION", "ONTOLOGICAL_INTERPRETATION", "NORMATIVE_CONCLUSION"].includes(c.kind) &&
    ["PROVED", "PROVED_CONDITIONAL"].includes(c.status));
  add(8, "No interpretation or norm presented as theorem", interpretiveOverclaim.length === 0,
    interpretiveOverclaim.length ? interpretiveOverclaim.map((c) => c.id).join(", ") : "interpretive and normative claims remain typed separately");

  const correspondenceOverclaim = claims.filter((c) =>
    c.kind === "CORRESPONDENCE_HYPOTHESIS" && c.status !== "OPEN_EMPIRICAL" && c.status !== "UNSUPPORTED");
  add(9, "No model-to-reality shortcut", correspondenceOverclaim.length === 0,
    correspondenceOverclaim.length ? correspondenceOverclaim.map((c) => c.id).join(", ") : "physical correspondences remain hypotheses");

  const unguarded = claims.filter((c) =>
    ["CORRESPONDENCE_HYPOTHESIS", "EMPIRICAL_CLAIM", "CAUSAL_CLAIM", "INTERPRETATION", "ONTOLOGICAL_INTERPRETATION"].includes(c.kind) &&
    c.guardedInferences.length === 0);
  add(10, "No unguarded correlation/visualization/AI inference", unguarded.length === 0,
    unguarded.length ? unguarded.map((c) => c.id).join(", ") : "all high-risk inference classes carry explicit guards");

  const temporalIds = new Set(claims.filter((c) => c.id.startsWith("RET-")).map((c) => c.id));
  const temporalComplete = ["RET-001", "RET-003", "RET-004", "RET-005", "RET-007", "RET-008", "RET-009", "RET-010"]
    .every((id) => temporalIds.has(id));
  add(11, "Retrocausality taxonomy coverage", temporalComplete,
    temporalComplete ? "retrodiction, semantics, symmetry, ontology, signalling, and experiment are separated" : "retrocausality taxonomy incomplete");

  const dimensionClaims = claims.filter((c) => c.id.startsWith("DIM-"));
  const dimensionsComplete = dimensionClaims.length >= 5 && dimensionClaims.every((c) => c.formalReference);
  add(12, "Dimensional bridge coverage", dimensionsComplete,
    dimensionsComplete ? `${dimensionClaims.length} SI exponent theorems registered` : "dimension theorem coverage incomplete");

  const source = leanSource();
  const executable = stripLeanComments(source);
  const forbidden = manifest.proofPolicy.forbiddenTokens.filter((token) =>
    new RegExp(`\\b${token}\\b`).test(executable));
  add(13, "No unchecked Lean proof escape", forbidden.length === 0,
    forbidden.length ? `forbidden tokens: ${forbidden.join(", ")}` : "no unchecked proof escape in executable Lean code");

  const missingDecls = claims.flatMap((c) => c.formalReference ?
    referenceNames(c.formalReference).filter((name) => !hasDeclaration(source, name)).map((name) => `${c.id}:${name}`) : []);
  add(14, "Formal references resolve", missingDecls.length === 0,
    missingDecls.length ? missingDecls.join(", ") : "every registered formal reference resolves to source");

  let leanReceipt: any = null;
  try { leanReceipt = readJson("build/lean-verification.json"); } catch {}
  const leanOk = leanReceipt?.exitCode === 0 && leanReceipt?.verified === true &&
    leanReceipt?.uncheckedProofEscapes === 0;
  add(15, "Lean kernel verification receipt", leanOk,
    leanOk ? `${leanReceipt.checker} ${leanReceipt.version}; ${leanReceipt.declarations} declarations` : "missing or failed Lean verification receipt");

  const policyOk = manifest.proofPolicy.empiricalClaimsMayBeTheorems === false &&
    manifest.proofPolicy.interpretationsMayBeTheorems === false &&
    manifest.proofPolicy.normativeClaimsMayBeTheorems === false;
  add(16, "Closed proof/empiricism policy", policyOk,
    policyOk ? "empirical, interpretive, and normative layers cannot enter theorem status" : "proof policy permits category collapse");

  let negativeReceipt: any = null;
  try { negativeReceipt = readJson("build/negative-test-report.json"); } catch {}
  const negativeOk = negativeReceipt?.passed === true && negativeReceipt?.rejected === 3;
  add(17, "Negative overclaim fixtures rejected", negativeOk,
    negativeOk ? "three deliberate overclaims rejected" : "negative-test receipt missing or failed");

  let checksumsOk = true;
  let checksumDetails = "SHA256SUMS not generated";
  try {
    const rows = readFileSync(new URL("SHA256SUMS", root), "utf8").trim().split(/\n+/);
    const failures: string[] = [];
    for (const row of rows) {
      const match = row.match(/^([0-9a-f]{64})  (.+)$/);
      if (!match || sha256(match[2]) !== match[1]) failures.push(match?.[2] ?? row);
    }
    checksumsOk = rows.length >= 15 && failures.length === 0;
    checksumDetails = checksumsOk ? `${rows.length} package hashes verified` : `checksum failures: ${failures.join(", ")}`;
  } catch {
    checksumsOk = false;
  }
  add(18, "Package integrity manifest", checksumsOk, checksumDetails);

  return results;
}

export function basicOverclaimViolations(claims: Claim[]): string[] {
  const violations: string[] = [];
  for (const c of claims) {
    if (!compatibility[c.kind]?.has(c.status)) violations.push(`${c.id}: incompatible ${c.kind}/${c.status}`);
    if (["PROVED", "PROVED_CONDITIONAL", "REFUTED_IN_MODEL"].includes(c.status) && !c.formalReference)
      violations.push(`${c.id}: theorem-level status without formal reference`);
    if (["OPEN_EMPIRICAL", "UNSUPPORTED"].includes(c.status) && c.falsification.length === 0)
      violations.push(`${c.id}: open empirical status without falsification target`);
  }
  return violations;
}
