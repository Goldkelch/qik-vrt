#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys

BASE = pathlib.Path("patent/meta-transistor/application-candidate-v1")
GATE = BASE / "UPLOAD_READINESS.json"
MANIFEST = BASE / "SUBMISSION_PACKAGE_MANIFEST.json"
PLAN = BASE / "SUBMISSION_PLAN.json"
FACTS = BASE / "SUBMISSION_FACTS.json"

def load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def git_blob_sha(data):
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()

def fail(msg):
    print(f"QIKVRT_FILING_GATE_INVALID: {msg}", file=sys.stderr)
    raise SystemExit(1)

gate = load(GATE)
manifest = load(MANIFEST)
plan = load(PLAN)
facts = load(FACTS)

if gate.get("schema") != "qikvrt_upload_readiness_v1":
    fail("unexpected gate schema")
if manifest.get("schema") != "qikvrt_submission_package_manifest_v1":
    fail("unexpected package manifest schema")
if plan.get("schema") != "qikvrt_submission_plan_v1":
    fail("unexpected submission plan schema")
if facts.get("schema") != "qikvrt_submission_facts_v1":
    fail("unexpected submission facts schema")

subjects = {gate.get("subject"), manifest.get("subject"), plan.get("subject"), facts.get("subject")}
if len(subjects) != 1 or None in subjects:
    fail("subject identity differs across control files")

sources = manifest.get("application_sources", [])
if not sources:
    fail("application_sources missing")

source_receipts = []
for entry in sources:
    path_value = entry.get("path")
    declared = entry.get("blob_sha")
    if not path_value or not declared or len(declared) != 40:
        fail("source entry missing repository path or 40-character blob SHA")
    path = pathlib.Path(path_value)
    if not path.is_file():
        fail(f"bound source file missing: {path_value}")
    data = path.read_bytes()
    actual = git_blob_sha(data)
    if actual != declared:
        fail(f"bound source blob mismatch: {path_value}: declared={declared} actual={actual}")
    source_receipts.append({"path": path_value, "git_blob_sha": actual, "sha256": hashlib.sha256(data).hexdigest()})

inventors_confirmed = facts.get("inventors", {}).get("status") == "CONFIRMED" and bool(facts.get("inventors", {}).get("entries"))
applicants_confirmed = facts.get("applicants", {}).get("status") == "CONFIRMED" and bool(facts.get("applicants", {}).get("entries"))
disclosures_complete = facts.get("public_disclosures", {}).get("status") == "COMPLETE"
priority_confirmed = facts.get("priority", {}).get("status") == "CONFIRMED"
existing_applications_confirmed = facts.get("existing_applications", {}).get("status") == "CONFIRMED"
target_selected = facts.get("target", {}).get("status") == "SELECTED" and all(
    facts.get("target", {}).get(k) for k in ("office", "route", "schema_version")
)
authorization = facts.get("owner_submission_authorization", {})
authorization_present = (
    authorization.get("status") == "AUTHORIZED"
    and bool(authorization.get("authorization_id"))
    and authorization.get("authorized_subject") == manifest.get("subject")
    and isinstance(authorization.get("authorized_package_sha256"), str)
    and len(authorization.get("authorized_package_sha256")) == 64
)

required = gate.get("required_conditions")
if not isinstance(required, dict) or not required:
    fail("required_conditions missing")

if required.get("all_required_fields_resolved") is True and not (
    inventors_confirmed and applicants_confirmed and disclosures_complete and priority_confirmed and existing_applications_confirmed
):
    fail("all_required_fields_resolved contradicts SUBMISSION_FACTS")
if required.get("target_endpoint_bound") is True and not target_selected:
    fail("target_endpoint_bound contradicts SUBMISSION_FACTS")
if required.get("target_schema_bound") is True and not target_selected:
    fail("target_schema_bound contradicts SUBMISSION_FACTS")
if required.get("owner_submission_authorization") is True and not authorization_present:
    fail("owner_submission_authorization contradicts exact authorization binding")

all_required_true = all(value is True for value in required.values())
derived = gate.get("derived_state", {})

if derived.get("upload_ready") is True and not all_required_true:
    fail("UPLOAD_READY declared true while one or more required conditions are not explicitly true")
if manifest.get("upload_ready") is True and not all_required_true:
    fail("manifest declares upload_ready without satisfying gate")
if plan.get("upload_ready") is True and not all_required_true:
    fail("submission plan declares upload_ready without satisfying gate")
if plan.get("filed") is True and plan.get("verified_filing") is not True:
    fail("FILED must not be promoted without verified filing evidence in this carrier")
if derived.get("filing_effect_ack_done") is True and derived.get("verified_filing") is not True:
    fail("FILING_EFFECT_ACK_DONE requires verified filing")
if all_required_true and not authorization_present:
    fail("all readiness conditions true without exact owner authorization binding")

state = "UPLOAD_READY" if all_required_true else "NOT_UPLOAD_READY"
receipt = {
    "schema": "qikvrt_submission_readiness_receipt_v2",
    "subject": manifest.get("subject"),
    "state": state,
    "source_blob_bindings_verified": True,
    "source_count": len(source_receipts),
    "unresolved_required_conditions": sorted(k for k, v in required.items() if v is not True),
    "facts": {
        "inventors_confirmed": inventors_confirmed,
        "applicants_confirmed": applicants_confirmed,
        "public_disclosures_complete": disclosures_complete,
        "priority_confirmed": priority_confirmed,
        "existing_applications_confirmed": existing_applications_confirmed,
        "target_selected": target_selected,
        "owner_submission_authorization_bound": authorization_present
    },
    "filed": bool(derived.get("filed", False)),
    "verified_filing": bool(derived.get("verified_filing", False)),
    "filing_effect_ack_done": bool(derived.get("filing_effect_ack_done", False))
}
print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
