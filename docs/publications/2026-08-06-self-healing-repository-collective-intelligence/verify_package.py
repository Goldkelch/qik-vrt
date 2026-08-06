#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PUB=ROOT/"docs/publications/2026-08-06-self-healing-repository-collective-intelligence"
REL=ROOT/"release/self-healing-repository-collective-intelligence-zenodo-v1"
cm=json.loads((PUB/"CLAIM_MATRIX.json").read_text(encoding="utf-8"))
bt=json.loads((PUB/"BOUNDARY_TEST_REPORT.json").read_text(encoding="utf-8"))
proof=json.loads((REL/"MACHINE_PROOF_BUNDLE.json").read_text(encoding="utf-8"))
receipt=json.loads((REL/"PREPUBLICATION_RETURN_RECEIPT.json").read_text(encoding="utf-8"))
assert cm["claim_count"]==len(cm["claims"])==10
assert len({c["claim_id"] for c in cm["claims"]})==10
assert all(c["classification"] in {"SOURCE_BOUND","NORMATIVE","INTERPRETATIVE","OPEN"} for c in cm["claims"])
assert bt["summary"]=={"failed":0,"passed":12,"result":"BOUNDARIES_PRESERVED","total":12}
cp={x["path"] for x in proof["candidate"]["files"]}
ap={x["path"] for x in proof["artifacts"]}
assert not cp & ap
assert cp=={x["path"] for x in receipt["candidate_files"]}
assert receipt["content_changed"] is False
assert receipt["return"]["visible_change_notice_returned"] is False
assert proof["gates"] and all(proof["gates"].values())
print("OK qikvrt-self-healing-repository-collective-intelligence claims=10 boundary_tests=12")
