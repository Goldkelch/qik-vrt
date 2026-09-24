#!/usr/bin/env python3
"""QIK-VRT Journal technical self-audit.

This audit verifies the bounded publication architecture. It does not claim
legal certification, journalistic truth certification, or external JTI certification.
"""
from __future__ import annotations
import argparse, json, re, hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"
JOURNAL=DOCS/"journal"
ARTICLE=JOURNAL/"wahrheit-oder-spam"
REQUIRED_ARCHIVE=("index.html","style.css","evidence.js","claims.json")

def load(path:Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def article_block(text:str)->str:
    m=re.search(r'<article class="journal-article">.*?</article>',text,re.S)
    if not m:
        raise ValueError("journal article block missing")
    return m.group(0)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output")
    ns=ap.parse_args()
    findings=[]

    def check(ok:bool,msg:str):
        if not ok: findings.append(msg)

    idx=load(JOURNAL/"index.json")
    claims=load(ARTICLE/"claims.json")
    sources=load(ARTICLE/"sources.json")
    corrections=load(JOURNAL/"corrections.json")
    versions=load(ARTICLE/"versions"/"index.json")
    audit=load(ROOT/"audit"/"QIKVRT_MESH_AUDIT_SUMMARY.json")
    adapters=load(ROOT/"AI_ADAPTERS.json")
    legal=load(JOURNAL/"legal"/"publication-readiness.json")

    check(idx.get("schema")=="qikvrt-journal-index/1.0","journal index schema mismatch")
    check(len(idx.get("articles",[]))>=1,"journal index has no articles")
    check(claims.get("schema")=="qikvrt-journal-claims/1.0","claims schema mismatch")
    ids=[c.get("id") for c in claims.get("claims",[])]
    check(len(ids)==len(set(ids)) and all(ids),"claim ids must be unique and non-empty")
    for c in claims.get("claims",[]):
        check(bool(c.get("kind")) and bool(c.get("status")) and bool(c.get("statement")),
              f"claim {c.get('id')} missing classification")
        check(isinstance(c.get("evidence"),list),f"claim {c.get('id')} evidence must be a list")
    check(sources.get("schema")=="qikvrt-journal-sources/1.0","sources schema mismatch")
    check(corrections.get("schema")=="qikvrt-journal-corrections/1.0","corrections schema mismatch")
    check(versions.get("schema")=="qikvrt-journal-version-index/1.0","version index schema mismatch")

    current=idx["articles"][0]["current_version"]
    archive=ARTICLE/"versions"/current
    for name in REQUIRED_ARCHIVE:
        check((archive/name).is_file(),f"archive missing {name}")

    canonical=(ARTICLE/"index.html").read_text(encoding="utf-8")
    home=(DOCS/"index.html").read_text(encoding="utf-8")
    try:
        check(article_block(canonical)==article_block(home),
              "homepage article block differs from canonical journal article")
    except ValueError as e:
        findings.append(str(e))

    check("data-qikvrt-claim-explorer" in canonical,"canonical article lacks interactive claim explorer")
    check('"@type":"Article"' in canonical,"canonical article lacks structured Article metadata")
    check((DOCS/"assets"/"js"/"qikvrt-journal-evidence.js").is_file(),"claim explorer JS missing")

    check(str(audit.get("run_id"))=="29753095894","bound mesh audit run id mismatch")
    check(audit.get("status")=="PASS","bound mesh audit is not PASS")
    check(audit.get("report_path")=="audit/QIKVRT_MESH_AUDIT_REPORT.md","bound mesh audit report path mismatch")

    systems=[a.get("system") for a in adapters.get("adapters",[])]
    for expected in ("OpenAI Codex","Anthropic Claude Code","Google Gemini CLI"):
        check(expected in systems,f"required AI adapter missing: {expected}")

    priority=[c for c in claims.get("claims",[]) if c.get("kind")=="PRIORITY"]
    check(any(c.get("status")=="NOT_ESTABLISHED" for c in priority),
          "absolute world-first priority boundary not recorded")

    receipt={
      "schema":"qikvrt-journal-self-audit/1.0",
      "article_id":claims.get("article_id"),
      "status":"PASS" if not findings else "BLOCK",
      "finding_count":len(findings),
      "findings":findings,
      "bounded_mesh_audit_run":audit.get("run_id"),
      "bounded_mesh_audit_status":audit.get("status"),
      "claim_count":len(claims.get("claims",[])),
      "source_count":len(sources.get("sources",[])),
      "adapter_count":len(adapters.get("adapters",[])),
      "current_version":current,
      "canonical_article_sha256":sha256(ARTICLE/"index.html"),
      "immutable_version_sha256":sha256(archive/"index.html"),
      "legal_publication_status":legal.get("publication_status"),
      "legal_readiness_claimed":False,
      "jti_certified":False,
      "world_first_claim_established":False
    }
    out=json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if ns.output:
        Path(ns.output).write_text(out,encoding="utf-8")
    print(out,end="")
    return 0 if not findings else 2

if __name__=="__main__":
    raise SystemExit(main())
