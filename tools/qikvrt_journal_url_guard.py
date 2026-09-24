#!/usr/bin/env python3
"""Guard stable QIK-VRT Journal URLs and immutable historical versions."""
from __future__ import annotations
import argparse, subprocess, sys

JOURNAL="docs/journal/"
VERSIONS="/versions/"

def out(*args:str)->str:
    return subprocess.check_output(["git",*args],text=True,stderr=subprocess.DEVNULL)

def tree_paths(ref:str)->set[str]:
    raw=out("ls-tree","-r","--name-only",ref)
    return {p for p in raw.splitlines() if p.startswith(JOURNAL)}

def blob(ref:str,path:str)->str|None:
    try:
        return out("rev-parse",f"{ref}:{path}").strip()
    except subprocess.CalledProcessError:
        return None

def article_roots(paths:set[str])->set[str]:
    roots=set()
    for p in paths:
        if p.endswith("/claims.json") and "/versions/" not in p:
            roots.add(p[:-len("/claims.json")])
    return roots

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True)
    ap.add_argument("--head",default="HEAD")
    ns=ap.parse_args()
    base_paths,head_paths=tree_paths(ns.base),tree_paths(ns.head)
    errors=[]

    for path in sorted(base_paths):
        if path.endswith("/index.html") and path not in head_paths:
            errors.append(f"published URL removed: {path}")

    for path in sorted(base_paths):
        if VERSIONS in path:
            if path not in head_paths:
                errors.append(f"archived version removed: {path}")
            elif blob(ns.base,path)!=blob(ns.head,path):
                errors.append(f"archived version modified: {path}")

    base_roots,head_roots=article_roots(base_paths),article_roots(head_paths)

    for root in sorted(head_roots-base_roots):
        archives=[p for p in head_paths if p.startswith(root+"/versions/") and p.endswith("/index.html")]
        if not archives:
            errors.append(f"new article lacks immutable initial version: {root}")

    for root in sorted(base_roots & head_roots):
        canon=root+"/index.html"
        if blob(ns.base,canon)!=blob(ns.head,canon):
            old={p for p in base_paths if p.startswith(root+"/versions/") and p.endswith("/index.html")}
            new={p for p in head_paths if p.startswith(root+"/versions/") and p.endswith("/index.html")}
            if not (new-old):
                errors.append(f"canonical article changed without new immutable version: {root}")

    if errors:
        print("\n".join("BLOCK: "+e for e in errors),file=sys.stderr)
        return 2
    print("PASS: journal URLs preserved; archive history immutable; canonical changes versioned")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
