#!/usr/bin/env python3
"""Verify the exact dossier bytes, total line coverage and epistemic boundaries."""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib
from typing import Any


D = pathlib.Path(__file__).resolve().parent
ALLOWED = {"SOURCE_BOUND", "INTERPRETATIVE", "NORMATIVE", "OPEN"}


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((D / name).read_text(encoding="utf-8"))


def _document_bytes(matrix: dict[str, Any]) -> dict[str, bytes]:
    return {
        document["path"]: (D.parents[2] / document["path"]).read_bytes()
        for document in matrix["documents"]
    }


def check(
    raw_by_path: dict[str, bytes],
    matrix: dict[str, Any],
    sources: dict[str, Any],
) -> int:
    documents = matrix["documents"]
    document_paths = [document["path"] for document in documents]
    assert len(document_paths) == len(set(document_paths)) == 4, "DOCUMENT_SET"
    assert set(raw_by_path) == set(document_paths), "DOCUMENT_INPUT_SET"

    lines_by_path: dict[str, list[str]] = {}
    for document in documents:
        path = document["path"]
        raw = raw_by_path[path]
        assert len(raw) == document["bytes"], "DOCUMENT_BYTES"
        assert hashlib.sha256(raw).hexdigest() == document["sha256"], "DOCUMENT_SHA256"
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        assert blob == document["git_blob_sha1"], "DOCUMENT_BLOB"
        lines = raw.decode("utf-8").splitlines()
        assert len(lines) == document["line_count"], "DOCUMENT_LINE_COUNT"
        lines_by_path[path] = lines

    claims = matrix["claims"]
    structural = matrix["structural_lines"]
    assert matrix["claim_count"] == len(claims), "CLAIM_COUNT"
    assert len({claim["claim_id"] for claim in claims}) == len(claims), "CLAIM_IDS"

    source_ids = {source["source_id"] for source in sources["sources"]}
    assert len(source_ids) == len(sources["sources"]), "SOURCE_IDS"
    assert sources["PREDECESSOR_EVIDENCE_TRANSFER"] is False, "NO_PREDECESSOR_TRANSFER"

    by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        path = claim["document_path"]
        line_number = claim["line"]
        statement = lines_by_path[path][line_number - 1]
        assert claim["statement"] == statement, "EXACT_STATEMENT"
        assert hashlib.sha256(statement.encode()).hexdigest() == claim["line_sha256"], "LINE_DIGEST"
        assert claim["classification"] in ALLOWED, "NO_UNBACKED_FORMAL_OR_EMPIRICAL"
        assert claim["boundary"] and not claim["proof_refs"], "SCOPE_NOT_THEOREM"
        assert set(claim["sources"]) <= source_ids, "REFERENCES"
        if claim["classification"] == "SOURCE_BOUND":
            assert claim["sources"], "SOURCE_REQUIRED"
        if claim["classification"] == "OPEN":
            assert claim["status"] == "OPEN", "OPEN_STATUS"
        by_id[claim["claim_id"]] = claim

    for path, lines in lines_by_path.items():
        wanted = {number for number, line in enumerate(lines, 1) if line.strip()}
        assigned = [
            item["line"]
            for item in [*claims, *structural]
            if item["document_path"] == path
        ]
        assert len(assigned) == len(set(assigned)), "DUPLICATE_LINE_ASSIGNMENT"
        assert set(assigned) == wanted, "FULL_LINE_COVERAGE"

    owner = by_id["OWNER-L010"]
    assert owner["classification"] == "INTERPRETATIVE", "OWNER_ASSESSMENT_NOT_FACT"
    assert "kein berechneter Posterior" in owner["boundary"], "OWNER_PROBABILITY_BOUNDARY"
    for claim_id in ("OWNER-L016", "OWNER-L017", "OWNER-L018", "OWNER-L019", "OWNER-L020"):
        assert by_id[claim_id]["classification"] == "OPEN", "OWNER_OPEN_RESULTS"
    for claim_id in ("EXPECT-L274", "EXPECT-L276", "EXPECT-L278", "EXPECT-L280"):
        assert by_id[claim_id]["classification"] == "OPEN", "HYPOTHESES_REMAIN_OPEN"
    assert by_id["EXPECT-L102"]["classification"] == "OPEN", "SPECIFIC_WAGER_OPEN"

    legal_sources = {
        "LAW-L046": "DE_GG_ART_1",
        "LAW-L052": "DE_GG_ART_1",
        "LAW-L054": "DE_GG_ART_79",
        "LAW-L068": "DE_STGB_240",
        "LAW-L070": "DE_STGB_238",
        "LAW-L072": "DE_STGB_241",
        "LAW-L074": "DE_STGB_202A",
        "LAW-L076": "DE_STGB_202D",
        "LAW-L078": "DE_STGB_126A",
        "LAW-L080": "DE_STGB_253",
        "LAW-L108": "DE_STGB_PARTICIPATION",
        "LAW-L160": "DE_BVERFG_COMPLAINT",
        "LAW-L234": "US_AMENDMENTS_5_14",
        "LAW-L242": "CN_CONSTITUTION_RIGHTS",
        "LAW-L250": "RU_CONSTITUTION_RIGHTS",
        "LAW-L256": "UA_CONSTITUTION_RIGHTS",
    }
    for claim_id, source_id in legal_sources.items():
        claim = by_id[claim_id]
        assert claim["classification"] == "SOURCE_BOUND", "LEGAL_SOURCE_CLASS"
        assert source_id in claim["sources"], "LEGAL_SOURCE_BINDING"
    return len(claims)


def run_tests() -> dict[str, Any]:
    matrix = _load_json("CLAIM_MATRIX.json")
    sources = _load_json("SOURCE_BINDINGS.json")
    raw_by_path = _document_bytes(matrix)
    count = check(raw_by_path, matrix, sources)
    results: list[dict[str, str]] = []

    def rejected(
        name: str,
        raws: dict[str, bytes],
        changed_matrix: dict[str, Any],
        changed_sources: dict[str, Any],
    ) -> None:
        try:
            check(raws, changed_matrix, changed_sources)
        except (AssertionError, KeyError, IndexError, UnicodeDecodeError):
            results.append({"name": name, "result": "EXPECTED_REJECTION"})
            return
        raise AssertionError("negative fixture admitted: " + name)

    changed_raws = dict(raw_by_path)
    first_path = matrix["documents"][0]["path"]
    changed_raws[first_path] += b" "
    rejected("changed_candidate_bytes", changed_raws, matrix, sources)

    changed = copy.deepcopy(matrix)
    changed["claims"].pop()
    rejected("omitted_claim", raw_by_path, changed, sources)

    changed = copy.deepcopy(matrix)
    changed["claims"].append(copy.deepcopy(changed["claims"][0]))
    rejected("duplicate_claim", raw_by_path, changed, sources)

    changed = copy.deepcopy(matrix)
    next(item for item in changed["claims"] if item["claim_id"] == "OWNER-L010")["classification"] = "EMPIRICALLY_EVIDENCED"
    rejected("owner_assessment_laundered_as_evidence", raw_by_path, changed, sources)

    changed = copy.deepcopy(matrix)
    next(item for item in changed["claims"] if item["claim_id"] == "EXPECT-L102")["classification"] = "INTERPRETATIVE"
    rejected("specific_wager_worded_as_settled", raw_by_path, changed, sources)

    changed = copy.deepcopy(matrix)
    next(item for item in changed["claims"] if item["claim_id"] == "LAW-L068")["sources"] = []
    rejected("legal_source_removed", raw_by_path, changed, sources)

    changed = copy.deepcopy(matrix)
    next(item for item in changed["claims"] if item["claim_id"] == "LAW-L070")["sources"] = ["MISSING"]
    rejected("unresolved_source", raw_by_path, changed, sources)

    changed_sources = copy.deepcopy(sources)
    changed_sources["PREDECESSOR_EVIDENCE_TRANSFER"] = True
    rejected("predecessor_evidence_transfer", raw_by_path, matrix, changed_sources)

    return {
        "schema": "qikvrt_pr1128_scope_tests_v2",
        "publication_id": matrix["publication_id"],
        "document_count": len(matrix["documents"]),
        "claim_count": count,
        "positive_fixture": "VERIFIED",
        "negative_tests": results,
        "all_nonblank_lines_accounted": True,
        "candidate_sha256": {
            document["path"]: document["sha256"] for document in matrix["documents"]
        },
        "native_P3": False,
        "owner_exact_upload_authorization": False,
        "ZENODO_PUBLICATION": False,
        "DONE": False,
        "scope": "exact identity and claim disposition, not natural-language truth, calibrated probability, legal judgment or empirical superiority",
    }


if __name__ == "__main__":
    report = run_tests()
    stored = _load_json("BOUNDARY_TEST_REPORT.json")
    assert stored == report, "BOUNDARY_REPORT_DRIFT"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
