#!/usr/bin/env python3
import json
import pathlib
import sys

BASE = pathlib.Path("patent/meta-transistor/application-candidate-v1")
GATE = BASE / "UPLOAD_READINESS.json"
MANIFEST = BASE / "SUBMISSION_PACKAGE_MANIFEST.json"
PLAN = BASE / "SUBMISSION_PLAN.json"

def load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def fail(msg):
    print(f"QIKVRT_FILING_GATE_INVALID: {msg}", file=sys.stderr)
    raise SystemExit(1)

gate = load(GATE)
manifest = load(MANIFEST)
plan = load(PLAN)

if gate.get("schema") != "qikvrt_upload_readiness_v1":
    fail("unexpected gate schema")
if manifest.get("schema") != "qikvrt_submission_package_manifest_v1":
    fail("unexpected package manifest schema")
if plan.get("schema") != "qikvrt_submission_plan_v1":
    fail("unexpected submission plan schema")

required = gate.get("required_conditions")
if not isinstance(required, dict) or not required:
    fail("required_conditions missing")

all_required_true = all(value is True for value in required.values())
derived = gate.get("derived_state", {})
declared_ready = derived.get("upload_ready")

if declared_ready is True and not all_required_true:
    fail("UPLOAD_READY declared true while one or more required conditions are not explicitly true")
if manifest.get("upload_ready") is True and not all_required_true:
    fail("manifest declares upload_ready without satisfying gate")
if plan.get("upload_ready") is True and not all_required_true:
    fail("submission plan declares upload_ready without satisfying gate")
if plan.get("filed") is True and plan.get("verified_filing") is not True:
    fail("FILED must not be promoted without verified filing evidence in this carrier")
if derived.get("filing_effect_ack_done") is True and derived.get("verified_filing") is not True:
    fail("FILING_EFFECT_ACK_DONE requires verified filing")

sources = manifest.get("application_sources", [])
for entry in sources:
    path = entry.get("path")
    blob = entry.get("blob_sha")
    if not path or not blob or len(blob) != 40:
        fail("source entry missing repository path or 40-character blob SHA")

state = "UPLOAD_READY" if all_required_true else "NOT_UPLOAD_READY"
receipt = {
    "schema": "qikvrt_submission_readiness_receipt_v1",
    "state": state,
    "all_required_conditions_explicitly_true": all_required_true,
    "unresolved_required_conditions": sorted(k for k, v in required.items() if v is not True),
    "filed": bool(derived.get("filed", False)),
    "verified_filing": bool(derived.get("verified_filing", False)),
    "filing_effect_ack_done": bool(derived.get("filing_effect_ack_done", False)),
}
print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
