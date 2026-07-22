import { ClaimSchema, ManifestSchema } from "./schema.ts";
import { readJson } from "./common.ts";

const manifest = ManifestSchema.parse(readJson("manifest.json"));
const rawClaims = readJson(manifest.claimsFile);
const claims = Array.isArray(rawClaims)
  ? rawClaims.map((claim) => ClaimSchema.parse(claim))
  : (() => { throw new Error("claim matrix must be a JSON array"); })();

console.log(JSON.stringify({
  valid: true,
  schemaVersion: manifest.schemaVersion,
  claims: claims.length,
  sourceDoi: manifest.source.versionDoi
}, null, 2));
