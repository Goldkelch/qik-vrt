#!/usr/bin/env python3
"""Audit QIK-VRT Journal translation-quality evidence and claim boundary."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
J=ROOT/"docs"/"journal"/"wahrheit-oder-spam"
I18N=J/"i18n"
POLICY=ROOT/"policy"/"QIKVRT_JOURNAL_TRANSLATION_QUALITY_V1.json"
REVIEWS=ROOT/"docs"/"journal"/"translation-quality"/"reviews.json"

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def main():
    policy=load(POLICY); reviews=load(REVIEWS); manifest=load(I18N/"manifest.json")
    findings=[]
    def check(ok,msg):
        if not ok: findings.append(msg)

    locales=policy["required_locales"]
    check(manifest.get("required_locales")==locales,"i18n locale set differs from translation-quality policy")
    base_claims=load(I18N/"claims.de.json")
    base_ids=[c["id"] for c in base_claims["claims"]]
    base_sem={c["id"]:(c["kind"],c["status"],c.get("evidence",[])) for c in base_claims["claims"]}
    base_content=load(I18N/"content.de.json")
    base_segments=[s["id"] for s in base_content["sections"]]

    for loc in locales:
        qloc="zh" if loc=="zh-Hans" else loc
        claims=load(I18N/f"claims.{qloc}.json")
        content=load(I18N/f"content.{loc}.json")
        check([c["id"] for c in claims["claims"]]==base_ids,f"claim id drift: {loc}")
        for c in claims["claims"]:
            check((c["kind"],c["status"],c.get("evidence",[]))==base_sem[c["id"]],f"claim evidence/status drift: {loc}:{c['id']}")
            check(bool(c.get("statement","").strip()),f"empty translated claim: {loc}:{c['id']}")
        check([s["id"] for s in content["sections"]]==base_segments,f"segment drift: {loc}")
        check(all(s.get("heading") and s.get("p") and all(str(p).strip() for p in s["p"]) for s in content["sections"]),f"empty translated segment: {loc}")

    req=policy["superiority_claim_requirements"]
    targets=[x for x in locales if x!="de"]
    superior=True
    for loc in targets:
        r=reviews["locales"].get(loc,{})
        if int(r.get("native_reviewers",0)) < int(req["independent_native_reviewers_per_target_locale"]):
            superior=False
        if r.get("blind_comparison")!="PASS":
            superior=False
        scores=r.get("scores") or {}
        if scores:
            if float(scores.get("mean",0)) < float(req["minimum_mean_score_0_to_1"]): superior=False
            if float(scores.get("terminology",0)) < float(req["minimum_terminology_score_0_to_1"]): superior=False
            if int(scores.get("critical_factual_errors",999)) != 0: superior=False
            if int(scores.get("material_omissions",999)) != 0: superior=False
            if int(scores.get("legal_meaning_changes",999)) != 0: superior=False
        else:
            superior=False

    check(reviews.get("best_translation_claim_established") is superior,
          "review registry superiority flag does not match evidence")

    receipt={
      "schema":"qikvrt-journal-translation-quality-audit/1.0",
      "article_id":reviews["article_id"],
      "version":reviews["version"],
      "locales":locales,
      "locale_count":len(locales),
      "machine_equivalence_status":"PASS" if not findings else "BLOCK",
      "best_translation_claim_established":superior and not findings,
      "benchmark_status":reviews.get("benchmark_status"),
      "finding_count":len(findings),
      "findings":findings,
      "allowed_public_wording":policy["allowed_before_superiority_established"] if not superior else "independently benchmarked top-tier translations",
      "human_translation_superiority_is_machine_proved":False
    }
    print(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if not findings else 2

if __name__=="__main__":
    raise SystemExit(main())
