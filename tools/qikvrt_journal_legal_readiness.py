#!/usr/bin/env python3
"""Fail closed when QIK-VRT Journal publication-law readiness is incomplete."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"docs"/"journal"/"legal"/"publication-readiness.json"
d=json.loads(p.read_text(encoding="utf-8"))
gaps=d.get("blocking_gaps",[])
if d.get("publication_status")!="READY_FOR_PUBLIC_PROMOTION" or gaps:
    print("BLOCK: journal legal publication readiness is incomplete")
    for gap in gaps:
        print(" - "+gap)
    raise SystemExit(2)
print("PASS: journal legal publication readiness explicitly complete")
