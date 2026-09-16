# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed structural self-test for repository handover preparation."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_FILES=["HANDOVER.md","LICENSE","COMMERCIAL_USE_POLICY.md","QIKVRT_LICENSE_AND_RIGHTS.md","state/HANDOVER_READINESS.json"]
REQUIRED_MODES={"STEWARDSHIP","PERSONAL_SUCCESSION","COMMERCIAL","ARCHIVAL"}
REQUIRED_EVIDENCE={"exact_head_tree","license_and_third_party_inventory","pr_disposition_ledger","branch_disposition_ledger","build_test_runtime_reproduction","authority_matrix","provider_and_deployment_inventory","credential_name_purpose_inventory_without_values","successor_credential_rotation_readback","backup_restore_test","known_defect_and_hold_ledger","fresh_successor_main_validation","fresh_successor_effect_readback","outgoing_incoming_same_receipt_ack"}

def check()->None:
    missing=[p for p in REQUIRED_FILES if not (ROOT/p).is_file()]
    if missing: raise SystemExit(f"BLOCK handover files missing: {missing}")
    state=json.loads((ROOT/"state/HANDOVER_READINESS.json").read_text(encoding="utf-8"))
    if state.get("status") != "HANDOVER_NOT_EFFECTIVE": raise SystemExit("BLOCK preparation must not claim an effective transfer")
    if set(state.get("supported_modes",[])) != REQUIRED_MODES: raise SystemExit("BLOCK transfer modes incomplete")
    if set(state.get("required_evidence",[])) != REQUIRED_EVIDENCE: raise SystemExit("BLOCK transfer evidence contract incomplete")
    if state.get("evidence_transfer") is not False or state.get("fail_closed") is not True: raise SystemExit("BLOCK evidence/fail-closed boundary weakened")
    secret=state.get("secret_policy",{})
    if secret.get("export_secret_values") is not False or secret.get("commit_secret_values") is not False or secret.get("rotate_or_reissue_on_transfer") is not True: raise SystemExit("BLOCK secret-transfer boundary weakened")
    handover=(ROOT/"HANDOVER.md").read_text(encoding="utf-8")
    for token in ("STEWARDSHIP","PERSONAL_SUCCESSION","COMMERCIAL","ARCHIVAL","HANDOVER_NOT_EFFECTIVE","TRANSPORT_ACK != EFFECT_ACK"):
        if token not in handover: raise SystemExit(f"BLOCK handover protocol missing {token}")
    print("PASS handover preparation structurally complete and fail-closed; no transfer claimed")

if __name__=="__main__": check()
