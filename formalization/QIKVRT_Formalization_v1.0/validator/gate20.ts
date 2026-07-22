import { mkdirSync, writeFileSync } from "node:fs";
import { evaluateChecks, loadPackage } from "./rules.ts";
import { root } from "./common.ts";

const { manifest, claims } = loadPackage();
const checks = evaluateChecks(manifest, claims);
const passed = checks.filter((c) => c.pass).length;
const report = {
  gate: "QUESTION_ROOT_VALIDATION_GATE_20",
  matrix: "18_CHECK_MACHINE_VERIFICATION",
  generatedAt: new Date().toISOString(),
  passed,
  failed: checks.length - passed,
  status: passed === 18 ? "PASS" : "BLOCK",
  checks
};

mkdirSync(new URL("build", root), { recursive: true });
writeFileSync(new URL("build/gate20-report.json", root), JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
if (report.status !== "PASS") process.exit(1);
