"""Independent standard-library verifier for the QIK-VRT claim boundary."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    id: int
    name: str
    passed: bool
    details: str


COMPATIBILITY = {
    "MATHEMATICAL_THEOREM": {"PROVED", "FALSE_IN_GENERAL"},
    "MODEL_DEFINITION": {"DEFINED"},
    "MODEL_THEOREM": {"PROVED", "PROVED_CONDITIONAL", "REFUTED_IN_MODEL"},
    "CORRESPONDENCE_HYPOTHESIS": {"OPEN_EMPIRICAL", "UNSUPPORTED"},
    "EMPIRICAL_CLAIM": {"ESTABLISHED_BACKGROUND", "OPEN_EMPIRICAL", "UNSUPPORTED"},
    "INTERPRETATION": {"INTERPRETIVE"},
    "CAUSAL_CLAIM": {"PROVED_CONDITIONAL", "OPEN_EMPIRICAL", "UNSUPPORTED", "REFUTED_IN_MODEL"},
    "ONTOLOGICAL_INTERPRETATION": {"INTERPRETIVE"},
    "NORMATIVE_CONCLUSION": {"NORMATIVE"},
}


def read_json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def file_sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def overclaim_violations(claim: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if claim["status"] not in COMPATIBILITY.get(claim["kind"], set()):
        out.append("kind/status incompatibility")
    if claim["status"] in {"PROVED", "PROVED_CONDITIONAL", "REFUTED_IN_MODEL"} and not claim["formalReference"]:
        out.append("theorem-level status lacks formal reference")
    if claim["status"] in {"OPEN_EMPIRICAL", "UNSUPPORTED"} and not claim["falsification"]:
        out.append("open empirical status lacks falsification target")
    return out


def evaluate() -> list[Check]:
    manifest = read_json("manifest.json")
    claims = read_json(manifest["claimsFile"])
    checks: list[Check] = []
    add = lambda i, n, p, d: checks.append(Check(i, n, bool(p), d))

    required_manifest = {"schemaVersion", "package", "source", "proofPolicy", "claimsFile", "requiredChecks"}
    schema_ok = set(manifest) == required_manifest and isinstance(claims, list) and len(claims) >= 30
    add(1, "Schema", schema_ok, f"{len(claims)} claims and exact manifest keys")

    source = manifest["source"]
    pdf_path = "source/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf"
    tex_path = "source/Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex"
    hashes_ok = file_sha256(pdf_path) == source["pdfSha256"] and file_sha256(tex_path) == source["texSha256"]
    add(2, "Source provenance and hashes", hashes_ok, "published Zenodo source bytes checked")

    ids = [c["id"] for c in claims]
    add(3, "Unique claim identifiers", len(ids) == len(set(ids)), f"{len(ids)} IDs")

    incompatible = [c["id"] for c in claims if c["status"] not in COMPATIBILITY.get(c["kind"], set())]
    add(4, "Kind/status compatibility", not incompatible, ", ".join(incompatible) or "compatible")

    missing = [c["id"] for c in claims if c["status"] in {"PROVED", "PROVED_CONDITIONAL", "REFUTED_IN_MODEL"} and not c["formalReference"]]
    add(5, "Formal references", not missing, ", ".join(missing) or "complete")

    missing = [c["id"] for c in claims if c["status"] == "PROVED_CONDITIONAL" and not c["assumptions"]]
    add(6, "Conditional assumptions", not missing, ", ".join(missing) or "complete")

    missing = [c["id"] for c in claims if c["status"] in {"OPEN_EMPIRICAL", "UNSUPPORTED"} and not c["falsification"]]
    add(7, "Empirical falsification targets", not missing, ", ".join(missing) or "complete")

    bad = [c["id"] for c in claims if c["kind"] in {"INTERPRETATION", "ONTOLOGICAL_INTERPRETATION", "NORMATIVE_CONCLUSION"} and c["status"].startswith("PROVED")]
    add(8, "No interpretive theorem collapse", not bad, ", ".join(bad) or "separated")

    bad = [c["id"] for c in claims if c["kind"] == "CORRESPONDENCE_HYPOTHESIS" and c["status"] not in {"OPEN_EMPIRICAL", "UNSUPPORTED"}]
    add(9, "No model/reality shortcut", not bad, ", ".join(bad) or "separated")

    bad = [c["id"] for c in claims if c["kind"] in {"CORRESPONDENCE_HYPOTHESIS", "EMPIRICAL_CLAIM", "CAUSAL_CLAIM", "INTERPRETATION", "ONTOLOGICAL_INTERPRETATION"} and not c["guardedInferences"]]
    add(10, "Inference guards", not bad, ", ".join(bad) or "complete")

    required_retro = {"RET-001", "RET-003", "RET-004", "RET-005", "RET-007", "RET-008", "RET-009", "RET-010"}
    add(11, "Retrocausality taxonomy", required_retro.issubset(ids), "required temporal distinctions registered")

    dims = [c for c in claims if c["id"].startswith("DIM-")]
    add(12, "Dimensional bridge", len(dims) >= 5 and all(c["formalReference"] for c in dims), f"{len(dims)} dimension claims")

    lean_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ROOT.rglob("*.lean")))
    executable = re.sub(r"/-.*?-/", "", lean_text, flags=re.S)
    executable = re.sub(r"--.*$", "", executable, flags=re.M)
    forbidden = [t for t in manifest["proofPolicy"]["forbiddenTokens"] if re.search(rf"\b{re.escape(t)}\b", executable)]
    add(13, "No unchecked Lean proof escape", not forbidden, ", ".join(forbidden) or "clean")

    names = set(re.findall(r"\b(?:theorem|def|structure|inductive)\s+([A-Za-z0-9_]+)", lean_text))
    unresolved = []
    for c in claims:
        if c["formalReference"]:
            for ref in c["formalReference"].split(";"):
                name = ref.strip().split(".")[-1]
                if name not in names:
                    unresolved.append(f"{c['id']}:{name}")
    add(14, "Formal reference resolution", not unresolved, ", ".join(unresolved) or "resolved")

    try:
        receipt = read_json("build/lean-verification.json")
        lean_ok = receipt["verified"] is True and receipt["exitCode"] == 0 and receipt["uncheckedProofEscapes"] == 0
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        receipt, lean_ok = {}, False
    add(15, "Lean kernel receipt", lean_ok, receipt.get("checker", "missing"))

    policy = manifest["proofPolicy"]
    policy_ok = not policy["empiricalClaimsMayBeTheorems"] and not policy["interpretationsMayBeTheorems"] and not policy["normativeClaimsMayBeTheorems"]
    add(16, "Closed proof/empiricism policy", policy_ok, "policy closed" if policy_ok else "policy open")

    try:
        neg = read_json("build/negative-test-report.json")
        neg_ok = neg["passed"] is True and neg["rejected"] == 3
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        neg_ok = False
    add(17, "Negative overclaim fixtures", neg_ok, "three fixtures rejected" if neg_ok else "receipt missing or failed")

    try:
        rows = (ROOT / "SHA256SUMS").read_text(encoding="utf-8").strip().splitlines()
        failed = []
        for row in rows:
            expected, rel = row.split("  ", 1)
            if file_sha256(rel) != expected:
                failed.append(rel)
        sums_ok = len(rows) >= 15 and not failed
    except (FileNotFoundError, ValueError):
        rows, failed, sums_ok = [], ["SHA256SUMS"], False
    add(18, "Package integrity", sums_ok, f"{len(rows)} hashes; failures={failed}")

    return checks


def main() -> int:
    checks = evaluate()
    report = {
        "gate": "QUESTION_ROOT_VALIDATION_GATE_20_PYTHON",
        "matrix": "18_CHECK_MACHINE_VERIFICATION",
        "passed": sum(c.passed for c in checks),
        "failed": sum(not c.passed for c in checks),
        "status": "PASS" if all(c.passed for c in checks) else "BLOCK",
        "checks": [asdict(c) for c in checks],
    }
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "gate20-python-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
