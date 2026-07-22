import { mkdirSync, writeFileSync } from "node:fs";
import { ClaimSchema } from "./schema.ts";
import { basicOverclaimViolations, loadPackage } from "./rules.ts";
import { root } from "./common.ts";

const { claims } = loadPackage();
const fixtures = [
  {
    ...claims.find((c) => c.id === "PHY-002")!,
    id: "BAD-001",
    status: "PROVED",
    formalReference: null,
    falsification: []
  },
  {
    ...claims.find((c) => c.id === "RET-007")!,
    id: "BAD-002",
    status: "PROVED",
    formalReference: null,
    falsification: []
  },
  {
    ...claims.find((c) => c.id === "ONT-002")!,
    id: "BAD-003",
    status: "PROVED",
    formalReference: null,
    falsification: []
  }
].map((x) => ClaimSchema.parse(x));

const cases = fixtures.map((fixture) => {
  const violations = basicOverclaimViolations([fixture]);
  return { id: fixture.id, rejected: violations.length > 0, violations };
});
const report = {
  generatedAt: new Date().toISOString(),
  passed: cases.every((c) => c.rejected),
  rejected: cases.filter((c) => c.rejected).length,
  cases
};

mkdirSync(new URL("build", root), { recursive: true });
writeFileSync(new URL("build/negative-test-report.json", root), JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
if (!report.passed) process.exit(1);
