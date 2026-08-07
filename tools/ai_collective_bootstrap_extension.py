#!/usr/bin/env python3
"""Fail-closed bootstrap extension for collective cognition and bound audio work."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")

FILES = {
    "collective": ROOT / "policy/HUMAN_MACHINE_COLLECTIVE_COGNITION_V1.json",
    "interop": ROOT / "policy/THIRD_PARTY_HMI_INTEROP_REGISTRY_V1.json",
    "directive": ROOT / "state/authorization/delegations/OWNER_AUDIO_REALITY_AND_COLLECTIVE_COGNITION_BOOTSTRAP_DIRECTIVE_V1.json",
    "audio": ROOT / "state/audio/USER_SUPPLIED_AUDIO_TRANSCRIPTION_REQUEST_V1.json",
}

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    report = {"schema":"qikvrt-ai-collective-bootstrap/1.0","state":"PASS","gates":{}}
    try:
        docs = {k: load(v) for k,v in FILES.items()}
        report["gates"]["files"] = "PASS"
        c = docs["collective"]
        assert c["reality_model_contract"]["suitable_model_can_describe_reality"] is True
        assert c["reality_model_contract"]["product_owner_qik_vrt_claim"] == "OWNER_ASSERTED_REALITY_CORRESPONDENCE"
        assert c["external_effects"]["default"] == "DISABLED"
        report["gates"]["collective_cognition"] = "PASS"
        d = docs["directive"]
        assert d["instructions"]["transcribe_audio"] is True
        assert d["instructions"]["third_party_license_compliance_required"] is True
        assert d["claim_boundary"]["owner_assertion_is_not_by_itself_independent_empirical_confirmation"] is True
        report["gates"]["owner_directive"] = "PASS"
        r = docs["audio"]["recordings"]
        assert len(r) == 6
        assert all(SHA256.fullmatch(x["sha256"]) for x in r)
        pending = [x["id"] for x in r if x["state"] != "VERBATIM_VERIFIED"]
        report["audio_recordings"] = len(r)
        report["audio_pending"] = pending
        report["gates"]["audio_binding"] = "PASS"
        registry = docs["interop"]
        assert registry["default_vendored"] is False
        assert all(x["vendored"] is False for x in registry["components"])
        report["gates"]["third_party_license_boundary"] = "PASS"
        if pending:
            report["state"] = "CONTINUE"
            report["next_action"] = "Run repository-native ASR on the exact bound audio bytes, persist ASR_DRAFT receipts, then perform human acoustic review before VERBATIM_VERIFIED."
    except Exception as exc:
        report["state"] = "BLOCK"
        report["blocker"] = f"{type(exc).__name__}: {exc}"
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("AI_COLLECTIVE_BOOTSTRAP_STATE=" + report["state"])
        for k,v in report.get("gates",{}).items(): print(f"GATE_{k.upper()}={v}")
        print("AUDIO_PENDING=" + ",".join(report.get("audio_pending",[])))
        if "blocker" in report: print("BLOCKER=" + report["blocker"])
        if "next_action" in report: print("NEXT_ACTION=" + report["next_action"])
    return 0 if report["state"] in {"PASS","CONTINUE"} else 2

if __name__ == "__main__":
    raise SystemExit(main())
