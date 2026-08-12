#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-ND-4.0
# Copyright 2026 Ingolf Lohmann.
"""Offline structural validator for the local EAP-LCTP -00 current candidate.

This checker is deliberately narrow.  It validates the declared candidate XML
and synthetic fixtures; it neither authenticates a real principal nor submits
or contacts an external service.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
XML_PATH = ROOT / "draft-lohmann-qikvrt-local-change-time-00.xml"
VECTORS_PATH = ROOT / "TEST_VECTORS.json"

FORWARD = "FORWARD_INFORMATION_DIRECTION"
NEGATIVE = "NEGATIVE_INFORMATION_DIRECTION"
INDETERMINATE = "INDETERMINATE"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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
        "renderer_and_idnits": "PENDING_XML2RFC_3_34_0_AND_IDNITS",
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


def main() -> int:
    report = {"xml": validate_xml(), "vectors": validate_vectors()}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
