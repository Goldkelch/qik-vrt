from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs/publications/2026-08-04-pre-spacetime-ontology"
ROUTER = Path(__file__).resolve().parents[1] / "tools/qikvrt_publication_router.py"

def test_router_is_fail_closed_and_effect_free() -> None:
    cp = subprocess.run([sys.executable, "-B", str(ROUTER), str(ROOT), "--json"],
                        check=True, text=True, capture_output=True)
    data = json.loads(cp.stdout)
    assert data["repository"] == "CANDIDATE"
    assert data["zenodo"] == "STAGED_REQUIRES_EXPLICIT_REQUEST"
    assert data["ietf"] == "NO_SUBMISSION_SCOPE_NOTE_ONLY"
    assert data["external_effect_performed"] is False

def test_ietf_disposition_is_non_mutating() -> None:
    data = json.loads((ROOT / "IETF_DISPOSITION.json").read_text(encoding="utf-8"))
    assert data["protocol_change_required"] is False
    assert data["ietf_mutation_authorized"] is False
