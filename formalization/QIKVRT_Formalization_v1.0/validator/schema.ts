import { z } from "zod";

export const claimKinds = [
  "MATHEMATICAL_THEOREM",
  "MODEL_DEFINITION",
  "MODEL_THEOREM",
  "CORRESPONDENCE_HYPOTHESIS",
  "EMPIRICAL_CLAIM",
  "INTERPRETATION",
  "CAUSAL_CLAIM",
  "ONTOLOGICAL_INTERPRETATION",
  "NORMATIVE_CONCLUSION"
] as const;

export const claimStatuses = [
  "PROVED",
  "PROVED_CONDITIONAL",
  "DEFINED",
  "REFUTED_IN_MODEL",
  "ESTABLISHED_BACKGROUND",
  "OPEN_EMPIRICAL",
  "UNSUPPORTED",
  "INTERPRETIVE",
  "NORMATIVE",
  "FALSE_IN_GENERAL"
] as const;

export const ClaimSchema = z.object({
  id: z.string().regex(/^[A-Z]+-[0-9]{3}$/),
  statement: z.string().min(12),
  kind: z.enum(claimKinds),
  status: z.enum(claimStatuses),
  scope: z.string().min(8),
  formalReference: z.string().min(3).nullable(),
  assumptions: z.array(z.string().min(3)),
  evidence: z.array(z.string().min(3)),
  falsification: z.array(z.string().min(3)),
  sourcePages: z.array(z.number().int().min(1).max(62)).min(1),
  guardedInferences: z.array(z.string().min(3))
}).strict();

export const ManifestSchema = z.object({
  schemaVersion: z.literal("1.0.0"),
  package: z.object({
    title: z.string().min(10),
    version: z.literal("1.0.0"),
    author: z.literal("Ingolf Lohmann"),
    formalizationRole: z.string().min(5),
    generatedAt: z.string().datetime(),
    license: z.string().min(3)
  }).strict(),
  source: z.object({
    title: z.string().min(10),
    version: z.literal("3.0"),
    pages: z.literal(62),
    zenodoRecord: z.literal("https://zenodo.org/records/21482023"),
    versionDoi: z.literal("10.5281/zenodo.21482023"),
    conceptDoi: z.literal("10.5281/zenodo.21482022"),
    pdfSha256: z.literal("b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f"),
    texSha256: z.literal("c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf"),
    goldkelchCommit: z.literal("16c69b4632b2d4698ff441b2a194c2da90923197"),
    ingolfLohmannCommit: z.literal("aab6c43e855a2c09424440bd075777aa20539dc1"),
    sharedTree: z.literal("f6ffe2b0c02a1b30c9c1f28a0a48e66538f229c1")
  }).strict(),
  proofPolicy: z.object({
    proofAssistant: z.literal("Lean 4"),
    toolchain: z.literal("v4.19.0"),
    forbiddenTokens: z.tuple([
      z.literal("sorry"), z.literal("admit"), z.literal("axiom")
    ]),
    empiricalClaimsMayBeTheorems: z.literal(false),
    interpretationsMayBeTheorems: z.literal(false),
    normativeClaimsMayBeTheorems: z.literal(false)
  }).strict(),
  claimsFile: z.literal("claims/claim-matrix.json"),
  requiredChecks: z.literal(18)
}).strict();

export type Claim = z.infer<typeof ClaimSchema>;
export type Manifest = z.infer<typeof ManifestSchema>;
