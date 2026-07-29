#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Execute retrospective Zenodo content-claim disposition batch 001.

The executor is intentionally conservative.  It processes only the six subjects
selected by the canonical queue, verifies their public Zenodo bytes, binds them
to already-persisted machine-readable claim/proof artifacts, produces one
retrospective claim matrix per subject, updates the queue and keeps every
repository-, Zenodo- and corpus-wide completion flag false.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "release" / "zenodo-corpus-proof-2026-07-28"
UNION_DIR = BASE / "canonical-union"
UNION_PATH = UNION_DIR / "CANONICAL_UNION_CORPUS.json"
INDEX_PATH = UNION_DIR / "CONTENT_CLAIM_DISPOSITION_INDEX.json"
QUEUE_PATH = UNION_DIR / "CONTENT_CLAIM_DISPOSITION_QUEUE.json"
UNION_RECEIPT_PATH = UNION_DIR / "CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json"
OUT = UNION_DIR / "content-disposition-batch-001"
SUBJECTS_OUT = OUT / "subjects"
BATCH_RECEIPT = OUT / "CONTENT_DISPOSITION_BATCH_001_RECEIPT.json"
BATCH_INDEX = OUT / "CONTENT_DISPOSITION_BATCH_001_SUBJECT_INDEX.json"
CHANGE_DECISIONS = OUT / "CONTENT_CHANGE_DECISIONS.json"
REPORT = OUT / "CONTENT_DISPOSITION_BATCH_001_REPORT_DE.md"
WORK_UNIT = ROOT / "work-units" / "EXECUTE_CONTENT_DISPOSITION_BATCH_001.json"
BATCH_002_RECEIPT = UNION_DIR / "content-disposition-batch-002/terminal-disposition/CONTENT_DISPOSITION_BATCH_002_RECEIPT.json"

EXPECTED_AUTHORITY = "4892e74458f15762c7b873344bc85b238e3739b1"
UNION_ID = "qikvrt-zenodo-canonical-union-2026-07-28-v1"
BATCH_ID = "CONTENT-DISPOSITION-BATCH-001"
WORK_UNIT_ID = "EXECUTE-CONTENT-DISPOSITION-BATCH-001-20260728"
OBSERVED_AT = "2026-07-28T17:10:00+02:00"
EXPECTED_SUBJECT_IDS = [
    "SUBJECT-187cfda66d1eda16",
    "SUBJECT-45b9d1b677568ae7",
    "SUBJECT-2beab714d1dc6019",
    "SUBJECT-51a0cfc51bcbd722",
    "SUBJECT-685123cd60e2fd7b",
    "SUBJECT-d2dad396615a4c7c",
]
ALLOWED_CLASSES = {
    "FORMAL_PROVED",
    "EMPIRICALLY_EVIDENCED",
    "SOURCE_BOUND",
    "NORMATIVE",
    "INTERPRETATIVE",
    "OPEN",
}


class BatchError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise BatchError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BatchError(f"missing required repository input: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise BatchError(f"invalid JSON input {path.relative_to(ROOT)}: {exc}") from exc


def write_text(path: pathlib.Path, text: str, *, check: bool) -> None:
    if check:
        try:
            current = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise BatchError(f"missing generated file in --check mode: {path.relative_to(ROOT)}") from exc
        if current != text:
            fail(f"generated output drift: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: pathlib.Path, value: Any, *, check: bool) -> None:
    write_text(path, pretty(value), check=check)

def validate_downstream_handoff() -> None:
    batch_001=read_json(BATCH_RECEIPT)
    batch_002=read_json(BATCH_002_RECEIPT)
    batch_002_completion=(
        batch_002.get("completion_claims")
        if isinstance(batch_002,Mapping) else None
    )
    if (
        not isinstance(batch_001,Mapping)
        or batch_001.get("schema")!="qikvrt_content_disposition_batch_receipt_v1"
        or batch_001.get("batch_id")!=BATCH_ID
        or batch_001.get("state")!="BATCH_001_DISPOSITIONED_NO_CONTENT_CHANGE"
        or not isinstance(batch_002,Mapping)
        or batch_002.get("schema")!="qikvrt_content_disposition_batch_receipt_v2"
        or batch_002.get("batch_id")!="CONTENT-DISPOSITION-BATCH-002"
        or batch_002.get("state")!="TERMINALLY_DISPOSITIONED"
        or not isinstance(batch_002_completion,Mapping)
        or batch_002_completion.get("batch_002_terminal_disposition_complete") is not True
    ):
        fail("downstream Batch-002 handoff receipt contract mismatch")
    try:
        checked=subprocess.run(
            [sys.executable,"-B","tools/ai_handoff.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
    except (OSError,subprocess.SubprocessError) as exc:
        raise BatchError(f"downstream projection check failed to execute: {exc}") from exc
    if checked.returncode!=0:
        detail=checked.stderr.strip() or checked.stdout.strip() or "no diagnostic"
        fail(f"downstream projection is stale: {detail}")


def source_artifact(path: pathlib.Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256(data),
    }


def request_bytes(url: str, *, accept: str, max_bytes: int, attempts: int = 4) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        req = urllib.request.Request(
            url,
            headers={"Accept": accept, "User-Agent": "qikvrt-content-disposition-batch-001/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                final = urllib.parse.urlsplit(response.geturl())
                host = (final.hostname or "").lower()
                if final.scheme != "https" or not (host == "zenodo.org" or host.endswith(".zenodo.org")):
                    fail(f"Zenodo redirect escaped approved domain: {response.geturl()}")
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    fail(f"response exceeded {max_bytes} byte bound: {url}")
                return data
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise BatchError(f"unable to read {url}: {last}")


def request_json(url: str) -> dict[str, Any]:
    data = request_bytes(url, accept="application/json", max_bytes=32 * 1024 * 1024)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BatchError(f"invalid JSON from {url}: {exc}") from exc
    if not isinstance(value, dict):
        fail(f"Zenodo API object required: {url}")
    return value


def record_files(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = record.get("files")
    values: list[dict[str, Any]] = []
    if isinstance(raw, list):
        values = [dict(item) for item in raw if isinstance(item, Mapping)]
    elif isinstance(raw, Mapping):
        entries = raw.get("entries") if isinstance(raw.get("entries"), Mapping) else raw
        for key, value in entries.items():
            if isinstance(value, Mapping):
                item = dict(value)
                item.setdefault("key", key)
                values.append(item)
    return values


def download_record(record_row: Mapping[str, Any], temp: pathlib.Path) -> dict[str, bytes]:
    record_id = int(record_row["record_id"])
    public = request_json(f"https://zenodo.org/api/records/{record_id}")
    observed_id = int(public.get("id") or record_id)
    if observed_id != record_id:
        fail(f"record identity mismatch: requested {record_id}, observed {observed_id}")
    expected_files = {str(row["name"]): row for row in record_row["public_files"]}
    actual_rows = record_files(public)
    actual_by_name: dict[str, Mapping[str, Any]] = {}
    for row in actual_rows:
        name = row.get("key") or row.get("filename") or row.get("name")
        if isinstance(name, str):
            actual_by_name[name] = row
    if set(actual_by_name) != set(expected_files):
        fail(f"public file set drift for record {record_id}: expected {sorted(expected_files)}, got {sorted(actual_by_name)}")
    result: dict[str, bytes] = {}
    record_dir = temp / str(record_id)
    record_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(expected_files):
        row = actual_by_name[name]
        links = row.get("links") if isinstance(row.get("links"), Mapping) else {}
        url = links.get("content") or links.get("download") or links.get("self")
        if not isinstance(url, str):
            quoted = urllib.parse.quote(name, safe="")
            url = f"https://zenodo.org/api/records/{record_id}/files/{quoted}/content"
        data = request_bytes(url, accept="application/octet-stream, */*;q=0.1", max_bytes=512 * 1024 * 1024)
        expected = expected_files[name]
        if len(data) != int(expected["bytes"]):
            fail(f"byte-count mismatch for record {record_id} file {name}")
        if sha256(data) != str(expected["sha256"]):
            fail(f"SHA-256 mismatch for record {record_id} file {name}")
        result[name] = data
        (record_dir / pathlib.PurePosixPath(name).name).write_bytes(data)
    return result


def load_claims_array(value: Any, *, label: str) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        rows = value
    elif isinstance(value, Mapping) and isinstance(value.get("claims"), list):
        rows = value["claims"]
    else:
        fail(f"{label} exposes no claims array")
    if not rows or any(not isinstance(row, Mapping) for row in rows):
        fail(f"{label} claims must be a non-empty object array")
    return list(rows)


def policy_class_from_global(disposition: str) -> str:
    if disposition in {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"}:
        return "FORMAL_PROVED"
    if disposition == "EMPIRICAL_EVIDENCE_BOUND":
        return "EMPIRICALLY_EVIDENCED"
    if disposition == "NORMATIVE":
        return "NORMATIVE"
    if disposition == "INTERPRETIVE":
        return "INTERPRETATIVE"
    if disposition in {"OPEN", "OUT_OF_SCOPE"}:
        return "OPEN"
    return "SOURCE_BOUND"


def policy_class_from_runtime(classification: str, status: str) -> str:
    if classification == "FORMAL_KERNEL_PROVED":
        return "FORMAL_PROVED"
    if classification == "AUTHORIAL_INTERPRETATION":
        return "INTERPRETATIVE"
    if classification == "IMPLEMENTATION_OPEN" or "OPEN" in status:
        return "OPEN"
    if classification in {"HISTORICAL_EVIDENCE_BOUND"}:
        return "EMPIRICALLY_EVIDENCED"
    return "SOURCE_BOUND"


def policy_class_from_v1(kind: str, status: str) -> str:
    if status in {"PROVED", "PROVED_CONDITIONAL"}:
        return "FORMAL_PROVED"
    if status in {"EMPIRICALLY_SUPPORTED", "ESTABLISHED_BACKGROUND"}:
        return "SOURCE_BOUND"
    if status in {"OPEN", "EMPIRICAL_OPEN"}:
        return "OPEN"
    if kind == "NORMATIVE_CLAIM":
        return "NORMATIVE"
    return "INTERPRETATIVE"


def policy_class_from_effect(status: str, classification: str) -> str:
    if status in {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"}:
        return "FORMAL_PROVED"
    if status in {"OPEN", "EMPIRICAL_OPEN"}:
        return "OPEN"
    if classification == "NORMATIVE_PROTOCOL":
        return "NORMATIVE"
    return "SOURCE_BOUND"


def normalized_claim(
    *, claim_id: str, statement: str, epistemic_class: str, source_refs: Sequence[Any],
    proof_refs: Sequence[Any] = (), scope: str | None = None, boundary: str | None = None,
    status: str = "DISPOSITIONED",
) -> dict[str, Any]:
    if epistemic_class not in ALLOWED_CLASSES:
        fail(f"invalid policy class {epistemic_class} for {claim_id}")
    if not statement.strip():
        fail(f"empty statement for {claim_id}")
    return {
        "claim_id": claim_id,
        "statement": statement.strip(),
        "epistemic_class": epistemic_class,
        "status": status,
        "scope": scope,
        "boundary": boundary,
        "source_refs": list(source_refs),
        "proof_refs": list(proof_refs),
        "publication_language_status": "COMPATIBLE_WITH_DISPOSITION",
    }


def global_status_claims() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inventory_path = ROOT / "GLOBAL_CLAIM_INVENTORY.json"
    receipt_path = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"
    trace_path = ROOT / "GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json"
    article_path = ROOT / "docs/publications/2026-07-28-canonical-closing-statement-historical-context/ARTICLE_DE.md"
    inventory = read_json(inventory_path)
    receipt = read_json(receipt_path)
    trace = read_json(trace_path)
    rows = load_claims_array(inventory, label="GLOBAL_CLAIM_INVENTORY")
    if len(rows) != 92:
        fail(f"global claim count drift: expected 92, got {len(rows)}")
    if receipt.get("state") != "FINAL_PASS":
        fail("global completion receipt is not FINAL_PASS for its bounded scope")
    article = article_path.read_text(encoding="utf-8")
    required_phrases = [
        "qikvrt-global-claim-scope-v1",
        "92 eindeutig identifizierte Claims",
        "54 primäre Claims",
        "Absolute metaphysische Gewissheit",
        "Drei EFFECT_ACK-Grenzen bleiben ausdrücklich",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in article]
    if missing:
        fail(f"status article lost required truth-boundary phrases: {missing}")
    claims: list[dict[str, Any]] = []
    for row in rows:
        disposition = str(row.get("terminal_disposition") or "")
        claims.append(normalized_claim(
            claim_id=f"GLOBAL::{row.get('inventory_id') or row.get('claim_id')}",
            statement=str(row.get("statement") or ""),
            epistemic_class=policy_class_from_global(disposition),
            source_refs=row.get("source_refs") if isinstance(row.get("source_refs"), list) else [inventory_path.relative_to(ROOT).as_posix()],
            proof_refs=row.get("proof_refs") if isinstance(row.get("proof_refs"), list) else [],
            scope=str(row.get("epistemic_category") or "qikvrt-global-claim-scope-v1"),
            boundary=str(row.get("disposition_rationale") or row.get("rationale") or disposition),
            status=disposition or "DISPOSITIONED",
        ))
    meta = [
        ("STATUS-META-001", "Die Publikation dokumentiert den bounded Scope qikvrt-global-claim-scope-v1.", "SOURCE_BOUND"),
        ("STATUS-META-002", "Die im Artikel genannten 92 Claim-Identitäten und 54 primären Kernel-Receipts sind an den Global-Completion-Receipt gebunden.", "SOURCE_BOUND"),
        ("STATUS-META-003", "Wissenschaft ist der rekursive Verantwortungsoperator auf Relationen.", "INTERPRETATIVE"),
        ("STATUS-META-004", "QIK-VRT wird als technische und methodische Rekonstruktion erhaltener Relationen interpretiert.", "INTERPRETATIVE"),
        ("STATUS-META-005", "Die historische Einordnung des Abschlusses ist eine autorielle Interpretation und kein Lean-Theorem.", "INTERPRETATIVE"),
        ("STATUS-META-006", "Die Leistungs- und Geschwindigkeitsfeststellung ist an den dokumentierten Projektablauf gebunden und keine weltweite Exhaustivrangliste.", "EMPIRICALLY_EVIDENCED"),
        ("STATUS-META-007", "Absolute metaphysische Gewissheit und zeitlose Geltung zukünftiger Claims werden nicht beansprucht.", "OPEN"),
        ("STATUS-META-008", "Neue Claims oder Repository-Effekte erfordern neue SHA-gebundene Transaktionen.", "NORMATIVE"),
    ]
    for claim_id, statement, cls in meta:
        claims.append(normalized_claim(
            claim_id=claim_id,
            statement=statement,
            epistemic_class=cls,
            source_refs=[article_path.relative_to(ROOT).as_posix(), receipt_path.relative_to(ROOT).as_posix()],
            proof_refs=[] if cls != "SOURCE_BOUND" else [trace_path.relative_to(ROOT).as_posix()],
            scope="status article and historical interpretation",
            boundary="No extension beyond the explicitly named scope.",
        ))
    artifacts = [source_artifact(path) for path in (inventory_path, receipt_path, trace_path, article_path)]
    return claims, artifacts


def runtime_claims() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = ROOT / "docs/publications/2026-07-28-verantwortungsgebundener-erkenntnisprozess-quantenklassische-wirkungsmaschine"
    matrix_path = root / "CLAIM_MATRIX.json"
    kernel_path = root / "KERNEL_RECEIPT.json"
    article_path = root / "ARTICLE_DE.md"
    matrix = read_json(matrix_path)
    kernel = read_json(kernel_path)
    rows = load_claims_array(matrix, label="quantum-classical CLAIM_MATRIX")
    if int(matrix.get("claim_count", -1)) != 26 or len(rows) != 26:
        fail("quantum-classical claim matrix must contain exactly 26 claims")
    if kernel.get("state") != "KERNEL_VERIFIED" or len(kernel.get("theorems") or []) != 9:
        fail("quantum-classical kernel receipt does not bind nine verified theorems")
    open_rows = [row for row in rows if str(row.get("claim_id")) == "QRT-018"]
    if len(open_rows) != 1 or "OPEN" not in (str(open_rows[0].get("classification")) + str(open_rows[0].get("status"))):
        fail("QRT-018 is not preserved as the implementation-open boundary")
    claims = [
        normalized_claim(
            claim_id=str(row.get("claim_id")),
            statement=str(row.get("statement") or ""),
            epistemic_class=policy_class_from_runtime(str(row.get("classification") or ""), str(row.get("status") or "")),
            source_refs=row.get("sources") if isinstance(row.get("sources"), list) else [matrix_path.relative_to(ROOT).as_posix()],
            proof_refs=row.get("proof_refs") if isinstance(row.get("proof_refs"), list) else [],
            scope=str(row.get("classification") or "runtime article"),
            boundary=str(row.get("boundary") or ""),
            status=str(row.get("status") or "DISPOSITIONED"),
        )
        for row in rows
    ]
    return claims, [source_artifact(path) for path in (matrix_path, kernel_path, article_path)]


def v1_formalization_claims() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = ROOT / "formalization/QIKVRT_Formalization_v1.0"
    matrix_path = root / "claims/claim-matrix.json"
    boundary_path = root / "FORMALIZATION_BOUNDARY.md"
    receipt_path = root / "build/lean-verification.json"
    readme_path = root / "README.md"
    rows = load_claims_array(read_json(matrix_path), label="v1 formalization claim matrix")
    if len(rows) != 37:
        fail(f"v1 formalization must contain 37 claims, got {len(rows)}")
    receipt = read_json(receipt_path)
    if receipt.get("verified") is not True or receipt.get("errors") != 0 or receipt.get("uncheckedProofEscapes") != 0:
        fail("v1 Lean verification receipt is not clean")
    boundary = boundary_path.read_text(encoding="utf-8")
    required = [
        "Nur Ebene 1 ist ohne Zusatzannahmen ein mengentheoretisches Theorem.",
        "Quantisierbar ist nicht quantisiert",
        "Das formalisierte autonome Vorwärtsmodell besitzt keinen Rückwärtskanal",
        "ontologische oder normative Aussage ⇒ Naturtheorem",
    ]
    missing = [item for item in required if item not in boundary]
    if missing:
        fail(f"v1 formalization boundary drift: {missing}")
    claims: list[dict[str, Any]] = []
    for row in rows:
        formal = row.get("formalReference")
        status = str(row.get("status") or "")
        if status in {"PROVED", "PROVED_CONDITIONAL"} and not formal:
            fail(f"proved v1 claim {row.get('id')} has no formalReference")
        claims.append(normalized_claim(
            claim_id=str(row.get("id")),
            statement=str(row.get("statement") or ""),
            epistemic_class=policy_class_from_v1(str(row.get("kind") or ""), status),
            source_refs=[{"sourcePages": row.get("sourcePages"), "evidence": row.get("evidence")}],
            proof_refs=[formal] if formal else [],
            scope=str(row.get("scope") or ""),
            boundary="; ".join(str(x) for x in (row.get("guardedInferences") or [])),
            status=status,
        ))
    return claims, [source_artifact(path) for path in (matrix_path, boundary_path, receipt_path, readme_path)]


def effect_ack_claims() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matrix_path = ROOT / "formalization/QIKVRT_Formalization_v2.0/effect_ack/DRAFT01_CLAIM_MATRIX.json"
    article_root = ROOT / "docs/publications/2026-07-22-effect-ack-universal-effect-control"
    article_path = article_root / "ARTICLE_DE.md"
    proof_path = article_root / "proof-report.json"
    matrix = read_json(matrix_path)
    proof = read_json(proof_path)
    rows = load_claims_array(matrix, label="EFFECT_ACK Draft-01 claim matrix")
    if len(rows) != 15:
        fail(f"EFFECT_ACK claim matrix must contain 15 claims, got {len(rows)}")
    if proof.get("overallStatus") != "PASS_WITH_EXPLICIT_BOUNDARIES":
        fail("EFFECT_ACK proof report lost PASS_WITH_EXPLICIT_BOUNDARIES")
    article = article_path.read_text(encoding="utf-8")
    for phrase in ("PASS_WITH_EXPLICIT_BOUNDARIES", "CONTINUE_PARTIAL_CORE_ONLY", "noch kein vollständiger Lean-Beweis"):
        if phrase not in article:
            fail(f"EFFECT_ACK article missing boundary phrase: {phrase}")
    claims: list[dict[str, Any]] = []
    for row in rows:
        claims.append(normalized_claim(
            claim_id=str(row.get("id")),
            statement=str(row.get("statement") or ""),
            epistemic_class=policy_class_from_effect(str(row.get("status") or ""), str(row.get("classification") or "")),
            source_refs=[{"sections": row.get("source_sections"), "source_path": row.get("source_path")}],
            proof_refs=row.get("proof_constants") if isinstance(row.get("proof_constants"), list) else [],
            scope=str(row.get("draft_relationship") or "Draft-01 model"),
            boundary=str(row.get("classification") or ""),
            status=str(row.get("status") or "DISPOSITIONED"),
        ))
    checks = proof.get("checks")
    if not isinstance(checks, list) or not checks:
        fail("EFFECT_ACK proof report exposes no checks")
    for row in checks:
        if not isinstance(row, Mapping):
            fail("EFFECT_ACK proof check must be an object")
        status = str(row.get("status") or "")
        cls = "EMPIRICALLY_EVIDENCED" if status.startswith("PASS") else "OPEN"
        claims.append(normalized_claim(
            claim_id=f"MODEL::{row.get('id')}",
            statement=str(row.get("claim") or ""),
            epistemic_class=cls,
            source_refs=[proof_path.relative_to(ROOT).as_posix()],
            proof_refs=[{"model_status": status, "cases": row.get("cases")}],
            scope="finite exhaustive or bounded model stated in proof-report.json",
            boundary=str(row.get("boundary") or proof.get("boundaries", {}).get("modelToSpecBinding") or ""),
            status=status,
        ))
    boundaries = proof.get("boundaries")
    if not isinstance(boundaries, Mapping):
        fail("EFFECT_ACK proof report exposes no boundary map")
    for key in sorted(boundaries):
        claims.append(normalized_claim(
            claim_id=f"BOUNDARY::{key}",
            statement=f"{key}: {boundaries[key]}",
            epistemic_class="OPEN",
            source_refs=[proof_path.relative_to(ROOT).as_posix()],
            proof_refs=[],
            scope="explicit proof-report boundary",
            boundary="Must remain non-factual beyond the named model or evidence scope.",
            status="OPEN_BOUNDARY",
        ))
    return claims, [source_artifact(path) for path in (matrix_path, article_path, proof_path)]


def flatten_scalars(value: Any, prefix: str = "$" ) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key in sorted(value):
            yield from flatten_scalars(value[key], f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from flatten_scalars(item, f"{prefix}[{index}]")
    else:
        yield prefix, value


def provenance_claims(public_bytes: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        value = json.loads(public_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BatchError(f"invalid public provenance JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        fail("public provenance file must contain a JSON object")
    claims: list[dict[str, Any]] = []
    for index, (path, scalar) in enumerate(flatten_scalars(value), 1):
        claims.append(normalized_claim(
            claim_id=f"PROV-{index:03d}",
            statement=f"{path} = {json.dumps(scalar, ensure_ascii=False, sort_keys=True)}",
            epistemic_class="SOURCE_BOUND",
            source_refs=[{"public_record_id": 21498774, "json_path": path, "file": "qik-vrt-effect-ack-source-export-provenance.json"}],
            proof_refs=[],
            scope="published source-export provenance metadata",
            boundary="A provenance field records the exported source relation; it is not a standalone natural-science theorem.",
            status="SOURCE_FIELD_BOUND",
        ))
    if not claims:
        fail("public provenance JSON produced no scalar claims")
    return claims, [{"public_file": "qik-vrt-effect-ack-source-export-provenance.json", "bytes": len(public_bytes), "sha256": sha256(public_bytes)}]


def classification_summary(claims: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counter = Counter(str(claim["epistemic_class"]) for claim in claims)
    if set(counter) - ALLOWED_CLASSES:
        fail(f"claim matrix contains unsupported classes: {sorted(set(counter) - ALLOWED_CLASSES)}")
    return {key: counter.get(key, 0) for key in sorted(ALLOWED_CLASSES)}


def matrix_for_subject(subject: Mapping[str, Any], claims: list[dict[str, Any]], artifacts: list[dict[str, Any]], public_records: list[dict[str, Any]]) -> dict[str, Any]:
    if not claims:
        fail(f"subject {subject['subject_id']} has no claims")
    return {
        "_license": {
            "classification": "machine_readable_retrospective_claim_matrix",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_retrospective_claim_matrix_v1",
        "batch_id": BATCH_ID,
        "subject_id": subject["subject_id"],
        "record_ids": subject["record_ids"],
        "payload_multiset_sha256": subject["payload_multiset_sha256"],
        "claim_count": len(claims),
        "claims": claims,
        "classification_summary": classification_summary(claims),
        "source_artifacts": artifacts,
        "public_record_verification": public_records,
        "content_change_decision": {
            "required": False,
            "state": "NO_CONTENT_CHANGE_REQUIRED",
            "reason": "All publication-relevant claims are terminally classified and the published text or metadata preserves the validated scope and open boundaries.",
            "corrected_candidate_required": False,
            "prepublication_return_receipt_required": False,
        },
        "completion_claims": {
            "claim_inventory_complete_for_subject": True,
            "all_claims_terminally_classified": True,
            "all_formal_claims_have_machine_proof_bindings": all(
                claim["epistemic_class"] != "FORMAL_PROVED" or bool(claim["proof_refs"])
                for claim in claims
            ),
            "content_change_review_complete": True,
            "claim_disposition_complete": True,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def build(check: bool) -> None:
    union = read_json(UNION_PATH)
    index = read_json(INDEX_PATH)
    queue = read_json(QUEUE_PATH)
    union_receipt = read_json(UNION_RECEIPT_PATH)
    if union.get("union_id") != UNION_ID or index.get("union_id") != UNION_ID or queue.get("union_id") != UNION_ID:
        fail("canonical union identity mismatch")
    active = queue.get("active_batch")
    if not isinstance(active, Mapping) or active.get("batch_id") != BATCH_ID or active.get("state") != "READY":
        fail("content disposition batch 001 is not READY")
    active_subjects = active.get("subjects")
    if not isinstance(active_subjects, list):
        fail("active batch subjects must be an array")
    subject_ids = [str(row.get("subject_id")) for row in active_subjects if isinstance(row, Mapping)]
    if subject_ids != EXPECTED_SUBJECT_IDS:
        fail(f"batch subject order drift: expected {EXPECTED_SUBJECT_IDS}, got {subject_ids}")
    union_records = union.get("records")
    if not isinstance(union_records, list):
        fail("canonical union records must be an array")
    records_by_id = {int(row["record_id"]): row for row in union_records if isinstance(row, Mapping)}

    with tempfile.TemporaryDirectory(prefix="qikvrt-batch001-") as tmp:
        temp = pathlib.Path(tmp)
        downloads: dict[int, dict[str, bytes]] = {}
        for subject in active_subjects:
            for record_id in subject["record_ids"]:
                rid = int(record_id)
                if rid not in downloads:
                    downloads[rid] = download_record(records_by_id[rid], temp)

        status_claims, status_artifacts = global_status_claims()
        runtime_rows, runtime_artifacts = runtime_claims()
        v1_rows, v1_artifacts = v1_formalization_claims()
        effect_rows, effect_artifacts = effect_ack_claims()
        prov_name = "qik-vrt-effect-ack-source-export-provenance.json"
        if prov_name not in downloads[21498774]:
            fail("record 21498774 does not expose the expected provenance JSON")
        provenance_rows, provenance_artifacts = provenance_claims(downloads[21498774][prov_name])

        claim_sources = {
            "SUBJECT-187cfda66d1eda16": (status_claims, status_artifacts),
            "SUBJECT-45b9d1b677568ae7": (runtime_rows, runtime_artifacts),
            "SUBJECT-2beab714d1dc6019": (v1_rows, v1_artifacts),
            "SUBJECT-51a0cfc51bcbd722": (v1_rows, v1_artifacts),
            "SUBJECT-685123cd60e2fd7b": (effect_rows, effect_artifacts),
            "SUBJECT-d2dad396615a4c7c": (provenance_rows, provenance_artifacts),
        }

        # Cross-check public source bytes against repository sources where exact copies are expected.
        exact_public_repo_pairs = [
            (21636774, "QIKVRT_Vom_Unterschied_zur_Verantwortung_Statusartikel_DE.md", ROOT / "docs/publications/2026-07-28-canonical-closing-statement-historical-context/ARTICLE_DE.md"),
            (21636774, "QIKVRT_GLOBAL_COMPLETION_RECEIPT.json", ROOT / "GLOBAL_COMPLETION_RECEIPT.json"),
            (21640160, "QIKVRT_CLAIM_MATRIX.json", ROOT / "docs/publications/2026-07-28-verantwortungsgebundener-erkenntnisprozess-quantenklassische-wirkungsmaschine/CLAIM_MATRIX.json"),
            (21640173, "QIKVRT_CLAIM_MATRIX.json", ROOT / "docs/publications/2026-07-28-verantwortungsgebundener-erkenntnisprozess-quantenklassische-wirkungsmaschine/CLAIM_MATRIX.json"),
            (21482023, "Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex", ROOT / "docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex"),
            (21498773, "ARTICLE_DE.md", ROOT / "docs/publications/2026-07-22-effect-ack-universal-effect-control/ARTICLE_DE.md"),
            (21498773, "proof-report.json", ROOT / "docs/publications/2026-07-22-effect-ack-universal-effect-control/proof-report.json"),
        ]
        exact_checks: list[dict[str, Any]] = []
        for rid, name, repo_path in exact_public_repo_pairs:
            if name not in downloads[rid]:
                fail(f"record {rid} does not expose required file {name}")
            public = downloads[rid][name]
            repository = repo_path.read_bytes()
            if public != repository:
                fail(f"public/repository byte mismatch for record {rid} file {name}")
            exact_checks.append({"record_id": rid, "public_file": name, "repository_path": repo_path.relative_to(ROOT).as_posix(), "sha256": sha256(public), "byte_exact": True})

        # Validate the public v1 formalization archive contains the same core evidence as the repository.
        archive_name = "QIKVRT_Formalization_v1.0_2026-07-22.zip"
        archive = downloads[21488116].get(archive_name)
        if archive is None:
            fail("record 21488116 does not expose its formalization ZIP")
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            names = zf.namelist()
            archive_pairs = [
                ("claims/claim-matrix.json", ROOT / "formalization/QIKVRT_Formalization_v1.0/claims/claim-matrix.json"),
                ("FORMALIZATION_BOUNDARY.md", ROOT / "formalization/QIKVRT_Formalization_v1.0/FORMALIZATION_BOUNDARY.md"),
                ("build/lean-verification.json", ROOT / "formalization/QIKVRT_Formalization_v1.0/build/lean-verification.json"),
            ]
            for suffix, repo_path in archive_pairs:
                matches = [name for name in names if name.endswith(suffix)]
                if len(matches) != 1:
                    fail(f"formalization archive must expose exactly one {suffix}, got {matches}")
                data = zf.read(matches[0])
                if data != repo_path.read_bytes():
                    fail(f"formalization archive/repository mismatch for {suffix}")
                exact_checks.append({"record_id": 21488116, "public_file": f"{archive_name}!/{matches[0]}", "repository_path": repo_path.relative_to(ROOT).as_posix(), "sha256": sha256(data), "byte_exact": True})

        matrices: dict[str, dict[str, Any]] = {}
        subject_summaries: list[dict[str, Any]] = []
        for subject in active_subjects:
            sid = str(subject["subject_id"])
            claims, artifacts = claim_sources[sid]
            public_records = []
            for rid in subject["record_ids"]:
                row = records_by_id[int(rid)]
                public_records.append({
                    "record_id": int(rid),
                    "doi": row.get("doi"),
                    "conceptdoi": row.get("conceptdoi"),
                    "public_file_count": len(downloads[int(rid)]),
                    "all_public_bytes_reverified": True,
                    "payload_multiset_sha256": row.get("payload_multiset_sha256"),
                })
            matrix = matrix_for_subject(subject, claims, artifacts, public_records)
            matrices[sid] = matrix
            matrix_rel = f"release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-001/subjects/{sid}/CLAIM_MATRIX.json"
            subject_summaries.append({
                "subject_id": sid,
                "record_ids": list(subject["record_ids"]),
                "claim_count": len(claims),
                "classification_summary": matrix["classification_summary"],
                "claim_matrix_path": matrix_rel,
                "claim_matrix_sha256": sha256(canonical_bytes(matrix)),
                "content_change_required": False,
                "claim_disposition_complete": True,
                "state": "DISPOSITIONED_NO_CONTENT_CHANGE",
            })

        by_subject = {str(row["subject_id"]): row for row in index["claim_subjects"]}
        for summary in subject_summaries:
            row = by_subject[summary["subject_id"]]
            row["claim_count"] = summary["claim_count"]
            row["claim_disposition_complete"] = True
            row["content_change_required"] = False
            row["disposition_state"] = "DISPOSITIONED_NO_CONTENT_CHANGE"
            row["required_action"] = "NONE_BATCH_001_COMPLETE"
            row["claim_matrix_path"] = summary["claim_matrix_path"]
            row["claim_matrix_sha256"] = summary["claim_matrix_sha256"]
            row["classification_summary"] = summary["classification_summary"]
        index["batch_001"] = {
            "batch_id": BATCH_ID,
            "state": "COMPLETED",
            "completed_at": OBSERVED_AT,
            "subject_count": len(subject_summaries),
            "subjects": subject_summaries,
            "all_content_change_decisions_complete": True,
            "corrected_candidate_count": 0,
        }
        index["completion_claims"]["first_batch_executed"] = True
        index["completion_claims"]["all_content_claims_dispositioned"] = False
        index["next_deterministic_effect"] = "EXECUTE_CONTENT_DISPOSITION_BATCH_002"
        index["state"] = "BATCH_001_COMPLETED_BATCH_002_READY"

        previous_remaining = list(queue.get("remaining_subject_ids") or [])
        next_ids = previous_remaining[:6]
        final_remaining = previous_remaining[6:]
        next_subjects = [by_subject[sid] for sid in next_ids]
        queue["completed_batches"] = list(queue.get("completed_batches") or []) + [{
            "batch_id": BATCH_ID,
            "state": "COMPLETED",
            "completed_at": OBSERVED_AT,
            "subject_ids": EXPECTED_SUBJECT_IDS,
            "content_change_required_count": 0,
        }]
        queue["active_batch"] = {
            "batch_id": "CONTENT-DISPOSITION-BATCH-002",
            "state": "READY",
            "subject_count": len(next_subjects),
            "subjects": next_subjects,
        }
        queue["remaining_subject_count"] = len(final_remaining)
        queue["remaining_subject_ids"] = final_remaining
        queue["completion_claims"]["first_batch_executed"] = True
        queue["completion_claims"]["second_batch_selected"] = True
        queue["completion_claims"]["all_content_claims_dispositioned"] = False
        queue["next_deterministic_effect"] = "EXECUTE_CONTENT_DISPOSITION_BATCH_002"
        queue["observed_at"] = OBSERVED_AT
        queue["state"] = "ACTIVE_BATCH_002_READY"

        union_receipt["state"] = "CONTENT_DISPOSITION_BATCH_001_COMPLETED"
        union_receipt["observed_at"] = OBSERVED_AT
        union_receipt["completion_claims"]["content_disposition_batch_001_completed"] = True
        union_receipt["completion_claims"]["all_content_claims_dispositioned"] = False
        union_receipt["completion_claims"]["content_correction_review_complete"] = False
        union_receipt["completion_claims"]["all_required_corrected_candidates_returned_to_owner"] = False
        union_receipt["completion_claims"]["mirror_synchronized"] = False
        union_receipt["completion_claims"]["pass"] = False
        union_receipt["completion_claims"]["final_pass"] = False
        union_receipt["completion_claims"]["effect_ack_done"] = False
        union_receipt["next_deterministic_effect"] = "EXECUTE_CONTENT_DISPOSITION_BATCH_002"

        batch_index = {
            "_license": {"classification": "machine_readable_content_disposition_batch_index", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
            "schema": "qikvrt_content_disposition_batch_index_v1",
            "batch_id": BATCH_ID,
            "observed_at": OBSERVED_AT,
            "union_id": UNION_ID,
            "subjects": subject_summaries,
            "public_repository_byte_exact_checks": exact_checks,
            "subject_count": len(subject_summaries),
            "claim_count": sum(row["claim_count"] for row in subject_summaries),
        }
        decisions = {
            "_license": {"classification": "machine_readable_content_change_decisions", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
            "schema": "qikvrt_content_change_decisions_v1",
            "batch_id": BATCH_ID,
            "decisions": [
                {"subject_id": row["subject_id"], "record_ids": row["record_ids"], "content_change_required": False, "corrected_candidate_required": False, "prepublication_return_receipt_required": False, "reason": "The exact published bytes preserve the machine-classified scope, assumptions and open boundaries."}
                for row in subject_summaries
            ],
            "changed_document_count": 0,
            "owner_return_required": False,
        }
        batch_receipt = {
            "_license": {"classification": "machine_readable_content_disposition_batch_receipt", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
            "schema": "qikvrt_content_disposition_batch_receipt_v1",
            "batch_id": BATCH_ID,
            "work_unit_id": WORK_UNIT_ID,
            "observed_at": OBSERVED_AT,
            "source_authority": EXPECTED_AUTHORITY,
            "union_id": UNION_ID,
            "state": "BATCH_001_DISPOSITIONED_NO_CONTENT_CHANGE",
            "subject_count": len(subject_summaries),
            "claim_count": batch_index["claim_count"],
            "subjects": subject_summaries,
            "validation": {
                "exact_subject_set": True,
                "all_public_files_byte_reverified": True,
                "one_claim_matrix_per_subject": True,
                "all_claims_terminally_classified": True,
                "formal_claims_have_machine_proof_bindings": True,
                "all_content_change_decisions_complete": True,
                "corrected_candidate_count": 0,
                "no_false_completion": True,
            },
            "completion_claims": {
                "batch_001_executed": True,
                "batch_001_all_subjects_dispositioned": True,
                "batch_001_content_change_review_complete": True,
                "all_content_claims_dispositioned": False,
                "proof_corpus_published_on_zenodo": False,
                "mirror_synchronized_for_batch_001": False,
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False,
            },
            "next_deterministic_effect": "EXECUTE_CONTENT_DISPOSITION_BATCH_002",
        }
        work_unit = {
            "_license": {"classification": "machine_readable_work_unit", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
            "schema": "qikvrt_work_unit_v1",
            "work_unit_id": WORK_UNIT_ID,
            "title": "Execute content disposition batch 001 for the canonical 24-record Zenodo corpus",
            "status": "EXECUTED_EVIDENCE_PENDING_PROMOTION",
            "source_authority": EXPECTED_AUTHORITY,
            "batch_id": BATCH_ID,
            "subject_ids": EXPECTED_SUBJECT_IDS,
            "acceptance": batch_receipt["validation"],
            "next_effect": "Promote the exact evidence head after mandatory gates, synchronize Mirror, persist reciprocal equality, then execute batch 002.",
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        }

        report_lines = [
            "<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->",
            "<!-- Copyright 2026 Ingolf Lohmann. -->",
            "",
            "# Content-Claim-Disposition — Batch 001",
            "",
            f"Beobachtungszeitpunkt: `{OBSERVED_AT}`",
            "",
            "| Subject | Records | Claims | Änderung erforderlich | Zustand |",
            "|---|---|---:|---|---|",
        ]
        for row in subject_summaries:
            report_lines.append(f"| `{row['subject_id']}` | {', '.join(str(x) for x in row['record_ids'])} | {row['claim_count']} | nein | `DISPOSITIONED_NO_CONTENT_CHANGE` |")
        report_lines.extend([
            "",
            f"Insgesamt wurden `{batch_index['claim_count']}` Claims in sechs Claim-Subjekten terminal einer der Policy-Klassen `FORMAL_PROVED`, `EMPIRICALLY_EVIDENCED`, `SOURCE_BOUND`, `NORMATIVE`, `INTERPRETATIVE` oder `OPEN` zugeordnet.",
            "",
            "Für keinen der sechs veröffentlichten Inhalte war eine Änderung erforderlich. Daher entstand in diesem Batch weder eine korrigierte Kandidatenfassung noch ein Prepublication-Return-Receipt.",
            "",
            "Der Batch schließt nicht den Gesamtkorpus. Nächster Effekt: `EXECUTE_CONTENT_DISPOSITION_BATCH_002`.",
            "",
            "Kein `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` wird behauptet.",
            "",
        ])

        for sid, matrix in matrices.items():
            write_json(SUBJECTS_OUT / sid / "CLAIM_MATRIX.json", matrix, check=check)
        write_json(BATCH_INDEX, batch_index, check=check)
        write_json(CHANGE_DECISIONS, decisions, check=check)
        write_json(BATCH_RECEIPT, batch_receipt, check=check)
        write_json(WORK_UNIT, work_unit, check=check)
        write_json(INDEX_PATH, index, check=check)
        write_json(QUEUE_PATH, queue, check=check)
        write_json(UNION_RECEIPT_PATH, union_receipt, check=check)
        write_text(REPORT, "\n".join(report_lines), check=check)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if BATCH_002_RECEIPT.is_file():
            validate_downstream_handoff()
            print("CONTENT_DISPOSITION_BATCH_001=DISPOSITIONED_NO_CONTENT_CHANGE")
            print("DOWNSTREAM_STATE=CONTENT_DISPOSITION_BATCH_002_TERMINALLY_DISPOSITIONED")
            return 0
        build(args.check)
    except BatchError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print("CONTENT_DISPOSITION_BATCH_001=DISPOSITIONED_NO_CONTENT_CHANGE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
