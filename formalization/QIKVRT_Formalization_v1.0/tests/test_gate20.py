import copy
import json
from pathlib import Path

from python.gate20 import ROOT, overclaim_violations


def claims():
    return json.loads((ROOT / "claims" / "claim-matrix.json").read_text(encoding="utf-8"))


def test_all_ids_are_unique():
    ids = [c["id"] for c in claims()]
    assert len(ids) == len(set(ids))


def test_ontic_quantization_overclaim_is_rejected():
    c = copy.deepcopy(next(c for c in claims() if c["id"] == "PHY-002"))
    c.update(status="PROVED", formalReference=None, falsification=[])
    assert overclaim_violations(c)


def test_physical_retrocausality_overclaim_is_rejected():
    c = copy.deepcopy(next(c for c in claims() if c["id"] == "RET-007"))
    c.update(status="PROVED", formalReference=None, falsification=[])
    assert overclaim_violations(c)


def test_ontology_as_theorem_is_rejected():
    c = copy.deepcopy(next(c for c in claims() if c["id"] == "ONT-002"))
    c.update(status="PROVED", formalReference=None)
    assert overclaim_violations(c)


def test_source_hashes_are_fixed():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["versionDoi"] == "10.5281/zenodo.21482023"
    assert manifest["source"]["pages"] == 62
