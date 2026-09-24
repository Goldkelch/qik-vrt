#!/usr/bin/env python3
"""Verify structural/source equivalence across QIK-VRT Journal language editions."""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARTICLE=ROOT/"docs"/"journal"/"wahrheit-oder-spam"
I18N=ARTICLE/"i18n"

def load(p:Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def main()->int:
    manifest=load(I18N/"manifest.json")
    locales=manifest["required_locales"]
    url_locales=manifest["url_locales"]
    findings=[]
    def check(ok,msg):
        if not ok: findings.append(msg)

    contents={}
    claims={}
    for loc in locales:
        cpath=I18N/f"content.{loc}.json"
        qloc="zh" if loc=="zh-Hans" else loc
        qpath=I18N/f"claims.{qloc}.json"
        check(cpath.is_file(),f"missing content: {loc}")
        check(qpath.is_file(),f"missing claims: {loc}")
        if cpath.is_file(): contents[loc]=load(cpath)
        if qpath.is_file(): claims[loc]=load(qpath)

    if "de" in contents:
        base_sections=[s["id"] for s in contents["de"]["sections"]]
        for loc,c in contents.items():
            check(c.get("locale")==loc,f"content locale mismatch: {loc}")
            check([s.get("id") for s in c.get("sections",[])]==base_sections,f"segment ids diverge: {loc}")
            check(all(s.get("heading") and all(p.strip() for p in s.get("p",[])) for s in c.get("sections",[])),f"empty translated segment: {loc}")

    if "de" in claims:
        de=claims["de"]
        base_ids=[c["id"] for c in de["claims"]]
        base_sem={c["id"]:(c["kind"],c["status"],c.get("evidence",[])) for c in de["claims"]}
        for loc,q in claims.items():
            check(q.get("article_id")==de.get("article_id"),f"article id differs in claims: {loc}")
            check(q.get("version")==de.get("version"),f"version differs in claims: {loc}")
            check([c.get("id") for c in q.get("claims",[])]==base_ids,f"claim ids diverge: {loc}")
            for c in q.get("claims",[]):
                if c.get("id") in base_sem:
                    check((c.get("kind"),c.get("status"),c.get("evidence",[]))==base_sem[c["id"]],f"claim semantics/evidence diverge: {loc}:{c.get('id')}")
                check(bool(c.get("statement","").strip()),f"empty claim translation: {loc}:{c.get('id')}")

    expected_hreflangs={"de","en","fr","ru","fa","zh-Hans","x-default"}
    for loc in locales:
        urlpart=url_locales[loc]
        p=ARTICLE/"index.html" if not urlpart else ARTICLE/urlpart/"index.html"
        check(p.is_file(),f"missing rendered page: {loc}")
        if not p.is_file(): continue
        html=p.read_text(encoding="utf-8")
        check(f'name="qikvrt-locale" content="{loc}"' in html,f"page locale metadata mismatch: {loc}")
        check('content="wahrheit-oder-spam-2026-09-24"' in html,f"article id missing: {loc}")
        check('content="2026-09-24-v1"' in html,f"version missing: {loc}")
        found=set(re.findall(r'hreflang="([^"]+)"',html))
        check(expected_hreflangs.issubset(found),f"hreflang set incomplete: {loc}")
        if "de" in contents:
            ids=re.findall(r'data-segment-id="([^"]+)"',html)
            expected=[s["id"] for s in contents["de"]["sections"]]+["sources","claims"]
            check(ids==expected,f"rendered segment sequence differs: {loc}")
        if loc=="fa":
            check('dir="rtl"' in html,"Persian edition is not RTL")

    archive=ARTICLE/"versions"/manifest["version"]
    check((archive/"i18n-manifest.json").is_file(),"archive i18n manifest missing")
    for loc in locales:
        qloc="zh" if loc=="zh-Hans" else loc
        urlpart=url_locales[loc]
        page=archive/"index.html" if not urlpart else archive/urlpart/"index.html"
        check(page.is_file(),f"archive page missing: {loc}")
        check((archive/f"claims.{qloc}.json").is_file(),f"archive claims missing: {loc}")
        check((archive/f"content.{loc}.json").is_file(),f"archive content missing: {loc}")
        if page.is_file():
            html=page.read_text(encoding="utf-8")
            check(f'name="qikvrt-locale" content="{loc}"' in html,f"archive locale metadata mismatch: {loc}")
            check('content="2026-09-24-v1"' in html,f"archive version mismatch: {loc}")

    receipt={
      "schema":"qikvrt-journal-i18n-integrity/1.0",
      "article_id":manifest["article_id"],
      "version":manifest["version"],
      "locales":locales,
      "locale_count":len(locales),
      "status":"PASS" if not findings else "BLOCK",
      "finding_count":len(findings),
      "findings":findings,
      "semantic_equivalence_human_certified":False,
      "structural_source_claim_equivalence_machine_checked":not findings
    }
    print(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if not findings else 2

if __name__=="__main__":
    raise SystemExit(main())
