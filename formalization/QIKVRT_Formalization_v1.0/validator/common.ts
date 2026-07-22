import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

export const root = new URL("../", import.meta.url);

export function readJson(path: string): unknown {
  return JSON.parse(readFileSync(new URL(path, root), "utf8"));
}

export function sha256(path: string): string {
  return createHash("sha256")
    .update(readFileSync(new URL(path, root)))
    .digest("hex");
}

export function walkFiles(start: string): string[] {
  const base = new URL(start, root);
  const basePath = base.pathname;
  const out: string[] = [];
  const visit = (path: string) => {
    for (const name of readdirSync(path).sort()) {
      const full = join(path, name);
      if (statSync(full).isDirectory()) visit(full);
      else out.push(relative(root.pathname, full));
    }
  };
  visit(basePath);
  return out;
}
