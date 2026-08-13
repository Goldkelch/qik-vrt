#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-ND-4.0
# Copyright 2026 Ingolf Lohmann.
"""Offline structural validator for the local EAP-LCTP -00 current candidate.

This checker is deliberately narrow.  It validates the declared candidate XML
and synthetic fixtures; it neither authenticates a real principal nor submits
or contacts an external service.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
XML_PATH = ROOT / "draft-lohmann-qikvrt-local-change-time-00.xml"
VECTORS_PATH = ROOT / "TEST_VECTORS.json"
MANIFEST_PATH = ROOT / "SUBMISSION_MANIFEST.json"
RENDER_STATUS_PATH = ROOT / "RENDER_STATUS.json"
CHECKSUMS_PATH = ROOT / "SHA256SUMS"

FIXITY_PATHS = (
    "draft-lohmann-qikvrt-local-change-time-00.xml",
    "TEST_VECTORS.json",
    "verify_candidate.py",
    "RENDER_STATUS.json",
    "SOURCE_PROVENANCE.json",
    "SUBMISSION_MANIFEST.json",
    "README.md",
    "STAGING_README.md",
    "EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md",
)

SUPPORTING_ARTIFACT_PATHS = {
    "TEST_VECTORS.json",
    "verify_candidate.py",
    "RENDER_STATUS.json",
    "SOURCE_PROVENANCE.json",
    "README.md",
    "STAGING_README.md",
    "EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md",
}

FORWARD = "FORWARD_INFORMATION_DIRECTION"
NEGATIVE = "NEGATIVE_INFORMATION_DIRECTION"
INDETERMINATE = "INDETERMINATE"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def digest(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def classify(baseline: dict[str, object], current: dict[str, object]) -> str:
    """Return the profile classification for one controlled test fixture."""

    comparable = (
        baseline["receiver_id"] == current["receiver_id"]
        and baseline["source_order_domain"] == current["source_order_domain"]
        and baseline["evidence_digest"] == current["baseline_evidence_digest"]
        and bool(baseline["source_authentication_valid"])
        and bool(baseline["receiver_authentication_valid"])
        and bool(current["source_authentication_valid"])
        and bool(current["receiver_authentication_valid"])
        and isinstance(baseline["local_change_index"], int)
        and isinstance(current["local_change_index"], int)
        and isinstance(baseline["source_order_marker"], int)
        and isinstance(current["source_order_marker"], int)
        and baseline["local_change_index"] < current["local_change_index"]
    )
    if not comparable:
        return INDETERMINATE
    if baseline["source_order_marker"] < current["source_order_marker"]:
        return FORWARD
    if baseline["source_order_marker"] > current["source_order_marker"]:
        return NEGATIVE
    return INDETERMINATE


def validate_xml() -> dict[str, object]:
    root = ElementTree.parse(XML_PATH).getroot()
    source = XML_PATH.read_text(encoding="utf-8")
    require(root.tag == "rfc", "root element must be rfc")
    require(root.attrib.get("version") == "3", "RFCXML version must be 3")
    require(root.attrib.get("ipr") == "trust200902", "IETF Trust IPR selector required")
    require(root.attrib.get("category") == "exp", "intended status must be Experimental")
    require(root.attrib.get("submissionType") == "IETF", "submission type must be IETF")
    require(
        root.attrib.get("docName") == "draft-lohmann-qikvrt-local-change-time-00",
        "unexpected I-D filename",
    )
    author = root.find("./front/author")
    require(author is not None, "author required")
    require(author.attrib.get("fullname") == "Ingolf Lohmann", "author name mismatch")
    require(author.findtext("./address/email") == "ingolf.lohmann@live.com", "author email missing")
    date = root.find("./front/date")
    require(date is not None, "document date required")
    require(date.attrib == {"year": "2026", "month": "August", "day": "12"}, "unexpected document date")
    series = root.find("./front/seriesInfo")
    require(series is not None, "Internet-Draft series identifier required")
    require(
        series.attrib == {
            "name": "Internet-Draft",
            "value": "draft-lohmann-qikvrt-local-change-time-00",
        },
        "Internet-Draft series identifier mismatch",
    )
    require(root.findtext("./front/area") == "Applications and Real-Time", "area mismatch")
    for required in (
        "eap-lctp-1",
        "local_change_index",
        "operational Eigenzeit",
        "NEGATIVE_INFORMATION_DIRECTION",
        "FORWARD_INFORMATION_DIRECTION",
        "not a claim that the value is a relativistic metric proper time",
        "not a statement that a signal travelled backward",
        "This document requests no IANA actions.",
    ):
        require(required in source, f"missing required source phrase: {required}")
    for forbidden in (
        "receipt_sequence",
        "RETROGRADE_REFERENCE",
        "FORWARD_REFERENCE",
        "draft-lohmann-qikvrt-temporal-provenance-00",
    ):
        require(forbidden not in source, f"legacy term unexpectedly present: {forbidden}")
    return {
        "xml_well_formed": True,
        "doc_name": root.attrib["docName"],
        "profile_version": "eap-lctp-1",
        "static_ietf_header_precheck": "PASS",
        "renderer_and_idnits": "CONTINUE_NO_RENDERED_ARTIFACTS",
    }


def validate_vectors() -> dict[str, object]:
    data = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    require(data["schema"] == "eap_lctp_classification_test_vectors_v1", "vector schema")
    require(data["profile_version"] == "eap-lctp-1", "vector profile version")
    vectors = data["vectors"]
    require(isinstance(vectors, list) and len(vectors) == 7, "expected seven fixtures")
    for vector in vectors:
        baseline = vector["baseline"]
        current = vector["current"]
        result = classify(baseline, current)
        require(
            result == vector["expected_classification"],
            f"{vector['id']}: {result} != {vector['expected_classification']}",
        )
    return {
        "reference_classification_vectors": len(vectors),
        "negative_information_direction_vectors": sum(
            vector["expected_classification"] == NEGATIVE for vector in vectors
        ),
        "result": "PASS",
    }


def validate_manifest_and_fixity() -> dict[str, object]:
    """Check the current local package without rendering or external access."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    require(
        manifest["schema"] == "qikvrt_ietf_current_candidate_manifest_v3",
        "unexpected submission-manifest schema",
    )
    require(
        manifest["state"] == "LOCAL_CURRENT_CANDIDATE_NOT_SUBMITTED",
        "candidate state must remain local and not submitted",
    )
    require(
        manifest["internet_draft"] == "draft-lohmann-qikvrt-local-change-time-00",
        "manifest Internet-Draft name mismatch",
    )
    require(
        all(value is False for value in manifest["external_effects"].values()),
        "manifest must not claim an external effect",
    )

    xml_record = manifest["submission_artifacts"]["xml"]
    xml_digest, xml_size = digest(XML_PATH)
    require(xml_record["path"] == XML_PATH.name, "manifest XML path mismatch")
    require(xml_record["sha256"] == xml_digest, "manifest XML digest mismatch")
    require(xml_record["size_bytes"] == xml_size, "manifest XML size mismatch")

    supporting = manifest["supporting_artifacts"]
    paths = {record["path"] for record in supporting.values()}
    require(paths == SUPPORTING_ARTIFACT_PATHS, "manifest supporting-artifact paths mismatch")
    for name, record in supporting.items():
        path = ROOT / record["path"]
        require(path.is_file(), f"{name}: declared supporting artifact is absent")
        actual_digest, actual_size = digest(path)
        require(record["sha256"] == actual_digest, f"{name}: digest mismatch")
        require(record["size_bytes"] == actual_size, f"{name}: size mismatch")

    fixity = manifest["fixity_index"]
    require(fixity["path"] == CHECKSUMS_PATH.name, "fixity-index path mismatch")
    require(
        tuple(fixity["indexed_paths"]) == FIXITY_PATHS,
        "fixity-index paths mismatch",
    )
    require(fixity["excludes"] == [CHECKSUMS_PATH.name], "fixity-index exclusion mismatch")

    recorded: dict[str, str] = {}
    for raw in CHECKSUMS_PATH.read_text(encoding="utf-8").splitlines():
        digest_value, separator, name = raw.partition("  ")
        require(separator == "  ", "invalid SHA256SUMS record")
        require(len(digest_value) == 64, "invalid SHA256SUMS digest length")
        require(name and name not in recorded, "duplicate or empty SHA256SUMS path")
        recorded[name] = digest_value
    require(tuple(recorded) == FIXITY_PATHS, "SHA256SUMS path order or scope mismatch")
    for name in FIXITY_PATHS:
        actual_digest, _ = digest(ROOT / name)
        require(recorded[name] == actual_digest, f"SHA256SUMS mismatch: {name}")

    render_status = json.loads(RENDER_STATUS_PATH.read_text(encoding="utf-8"))
    require(
        render_status["schema"] == "qikvrt_ietf_candidate_render_status_v3",
        "unexpected render-status schema",
    )
    require(
        render_status["state"] == "CONTINUE_XML2RFC_3_34_0_UNAVAILABLE",
        "unexpected renderer state",
    )
    require(render_status["source"]["path"] == XML_PATH.name, "render source path mismatch")
    require(render_status["source"]["sha256"] == xml_digest, "render source digest mismatch")
    require(render_status["source"]["size_bytes"] == xml_size, "render source size mismatch")
    require(
        render_status["required_renderer"] == {
            "name": "xml2rfc",
            "version": "3.34.0",
            "runtime_contract": "runtime/toolchains/TOOLCHAIN.lock.tsv",
            "availability_observed": False,
        },
        "renderer contract mismatch",
    )
    for output_name in ("txt", "html"):
        require(
            render_status["outputs"][output_name]["state"] == "NOT_RENDERED",
            f"{output_name} output state mismatch",
        )
    require(
        all(value is False for value in render_status["external_effects"].values()),
        "render status must not claim an external effect",
    )
    require(
        manifest["validation"] == {
            "xml_well_formed": True,
            "static_ietf_header_precheck": "PASS",
            "reference_classification_vectors": 7,
            "candidate_fixity": "PASS",
            "validation_command": "python3 -B verify_candidate.py",
            "result": "PASS_STATIC_CANDIDATE_VALIDATION",
            "renderer_validation": "CONTINUE_XML2RFC_3_34_0_UNAVAILABLE",
            "idnits_validation": "CONTINUE_NO_RENDERED_TEXT_AND_NO_DECLARED_IDNITS_RUNTIME",
        },
        "validation state mismatch",
    )
    return {
        "manifest": "PASS",
        "fixity_index": "PASS",
        "rendered_artifacts": "NOT_RENDERED",
        "renderer_validation": "CONTINUE_XML2RFC_3_34_0_UNAVAILABLE",
        "idnits_validation": "CONTINUE_NO_RENDERED_TEXT_AND_NO_DECLARED_IDNITS_RUNTIME",
    }


def main() -> int:
    report = {
        "manifest_and_fixity": validate_manifest_and_fixity(),
        "vectors": validate_vectors(),
        "xml": validate_xml(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
