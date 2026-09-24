#!/usr/bin/env python3
"""Fail closed when QIK-VRT Journal publication-law readiness is incomplete."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"docs"/"journal"/"legal"/"publication-readiness.json"
d=json.loads(p.read_text(encoding="utf-8-sig"))

gaps=[]

director=d.get("publication_director") or {}
publisher=d.get("publisher") or {}
host=d.get("hosting_provider") or {}
reply=d.get("right_of_reply") or {}
editorial=d.get("editorial_contact") or {}
review=d.get("human_legal_review") or {}

if not director.get("name"):
    gaps.append("publication_director.name")

classification=publisher.get("professional_or_nonprofessional_classification")
if classification not in {"PROFESSIONAL","NONPROFESSIONAL"}:
    gaps.append("publisher.professional_or_nonprofessional_classification")

if classification=="PROFESSIONAL":
    for field in ("public_address","public_phone","public_electronic_contact"):
        if not publisher.get(field):
            gaps.append("publisher."+field)
elif classification=="NONPROFESSIONAL":
    if publisher.get("identity_delivered_to_host") is not True:
        gaps.append("publisher.identity_delivered_to_host")

entities=host.get("provider_entities") or []
if not entities or not all(e.get("name") and e.get("address") for e in entities):
    gaps.append("hosting_provider.provider_entities")

if not reply.get("public_contact"):
    gaps.append("right_of_reply.public_contact")
if not editorial.get("public_contact"):
    gaps.append("editorial_contact.public_contact")

if review.get("confirmed") is not True:
    gaps.append("human_legal_review.confirmed")

declared=d.get("publication_status")
ready=(not gaps) and declared=="READY_FOR_PUBLIC_PROMOTION"

print(json.dumps({
    "schema":"qikvrt-journal-legal-readiness-check/1.0",
    "declared_status":declared,
    "computed_ready":ready,
    "gap_count":len(gaps),
    "gaps":gaps,
    "legal_advice":False
},ensure_ascii=False,sort_keys=True,indent=2))

if not ready:
    raise SystemExit(2)
