#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify that Draft-03 adds research context without changing wire version 1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from test_ietf_revision_02 import (
    EXPECTED_CORE_DONE,
    EXPECTED_FIELDS,
    EXPECTED_STATES,
    canonical_element,
    done_conjuncts,
    field_names,
    normalized,
    section,
    state_names,
)


ROOT = Path(__file__).resolve().parents[1]
IETF_ROOT = ROOT / "external/ietf"
REVISION_02_XML = IETF_ROOT / "draft-lohmann-qikvrt-effect-ack-02.xml"
REVISION_03_XML = IETF_ROOT / "draft-lohmann-qikvrt-effect-ack-03.xml"
REVISION_03_TXT = IETF_ROOT / "draft-lohmann-qikvrt-effect-ack-03.txt"
REVISION_03_HTML = IETF_ROOT / "draft-lohmann-qikvrt-effect-ack-03.html"
REVISION_03_CANDIDATE = (
    IETF_ROOT / "draft-lohmann-qikvrt-effect-ack-03.CANDIDATE.json"
)
REVISION_03_SUBMISSION_RECEIPT = (
    IETF_ROOT / "draft-lohmann-qikvrt-effect-ack-03.SUBMISSION_RECEIPT.json"
)
REVISION_03_PUBLICATION_RECEIPT = (
    IETF_ROOT / "draft-lohmann-qikvrt-effect-ack-03.PUBLICATION_RECEIPT.json"
)
REVISION_03_DOCUMENT_DATE = "2026-08-02"
EXPECTED_ARCHIVAL_DATE_WARNING = re.compile(
    rf".*[/\\]{re.escape(REVISION_03_XML.name)}\(\d+\): "
    rf"Warning: The document date \({REVISION_03_DOCUMENT_DATE}\) "
    r"is more than \d+ days away from today's date$"
)


def is_expected_archival_date_warning(line: str) -> bool:
    """Accept only xml2rfc's clock-relative warning for the frozen -03 date."""
    return EXPECTED_ARCHIVAL_DATE_WARNING.fullmatch(line) is not None


UNCHANGED_NORMATIVE_ANCHORS = (
    "conventions",
    "architecture",
    "states",
    "done-predicate",
    "selection",
    "transitions",
    "wire",
    "record-fields",
    "canonical",
    "chain",
    "versioning",
    "timeouts",
    "policy-evidence",
    "conformance",
    "wire-conformance",
    "gate-conformance",
    "deployment-conformance",
    "test-vectors",
    "security",
    "privacy",
    "iana",
    "limitations",
)

TYPED_CLAIM_MARKERS = (
    "This subsection is non-normative.",
    "external evidence object",
    "evidence_refs",
    "required_evidence_refs",
    "policy_id",
    "policy_version",
    "policy_hash",
    "FORMAL_PROVED",
    "EMPIRICAL_SUPPORTED",
    "SOURCE_BOUND",
    "NORMATIVE",
    "INTERPRETIVE",
    "OPEN",
    "KERNEL_VERIFIED",
    "exact theorem statement",
    "exact source octets",
    "declared axioms or trust assumptions",
    "does not establish unencoded premises",
    "authorization for downstream effect",
    "does not bypass consumer rederivation",
    "DONE-only ordinary-release rule",
)

VRT_BOUNDARY_MARKERS = (
    "This subsection is non-normative.",
    "VRT := Rec(D,I,M,W,R,C,A,P)",
    "temporal sequence, co-occurrence, and correlation",
    "explicitly identified bridge",
    "neither defines nor proves a general physical theory of causality",
    "ontic retrocausality",
    "backward or superluminal signalling",
    "modification of past events",
    "emergence of Minkowski or general Lorentzian spacetime",
    "stable classical limit",
    "arbitrary semantic truth",
    "universal decoder",
    "authorship or person identity",
    "consciousness",
    "moral correctness",
    "social benefit",
    "absence of harm",
    "responsible human authorization",
    "Lean theorem",
    "empirical bridge",
    "Candidate formalization text without an exact receipt is not represented as kernel-verified.",
)

BCP14_KEYWORD = re.compile(
    r"\b(?:MUST|MUST NOT|REQUIRED|SHALL|SHALL NOT|SHOULD|SHOULD NOT|"
    r"RECOMMENDED|NOT RECOMMENDED|MAY|OPTIONAL)\b"
)

XML2RFC: Path | None = None


def sourcecode_text(root: ET.Element, anchor: str, code_type: str) -> str:
    value = section(root, anchor).find(f".//sourcecode[@type='{code_type}']")
    if value is None or value.text is None:
        raise AssertionError(f"{anchor} lacks {code_type} sourcecode")
    return value.text


def section_text(root: ET.Element, anchor: str) -> str:
    return normalized(" ".join(section(root, anchor).itertext()))


def run_renderer(
    xml2rfc: Path,
    output: Path,
    cache: Path,
    mode: str,
) -> None:
    environment = os.environ.copy()
    environment["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        [
            str(xml2rfc),
            str(REVISION_03_XML),
            "--v3",
            f"--{mode}",
            "--no-network",
            "--skip-config-files",
            "--warn-bare-unicode",
            "--cache",
            str(cache),
            "--verbose",
            "--out",
            str(output),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=180,
    )
    diagnostics = "\n".join((completed.stdout, completed.stderr))
    if completed.returncode != 0:
        raise AssertionError(
            f"xml2rfc {mode} render exited {completed.returncode}\n"
            f"{diagnostics[-4000:]}"
        )
    warnings = tuple(
        line
        for line in diagnostics.splitlines()
        if re.search(r"\b(?:warning|error)\b", line, flags=re.IGNORECASE)
    )
    unexpected_warnings = tuple(
        line for line in warnings if not is_expected_archival_date_warning(line)
    )
    if unexpected_warnings:
        raise AssertionError(
            f"xml2rfc emitted unexpected warning/error diagnostics for {mode}:\n"
            + "\n".join(unexpected_warnings[-40:])
        )
    if not output.is_file() or output.stat().st_size == 0:
        raise AssertionError(f"xml2rfc did not create a non-empty {mode} output")


class IETFRevision03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (
            REVISION_02_XML,
            REVISION_03_XML,
            REVISION_03_TXT,
            REVISION_03_HTML,
            REVISION_03_CANDIDATE,
            REVISION_03_SUBMISSION_RECEIPT,
            REVISION_03_PUBLICATION_RECEIPT,
        ):
            if not path.is_file():
                raise AssertionError(f"required revision source is absent: {path}")
        cls.revision_02 = ET.parse(REVISION_02_XML).getroot()
        cls.revision_03 = ET.parse(REVISION_03_XML).getroot()
        cls.candidate = json.loads(
            REVISION_03_CANDIDATE.read_text(encoding="utf-8")
        )
        cls.submission_receipt = json.loads(
            REVISION_03_SUBMISSION_RECEIPT.read_text(encoding="utf-8")
        )
        cls.publication_receipt = json.loads(
            REVISION_03_PUBLICATION_RECEIPT.read_text(encoding="utf-8")
        )

    def test_candidate_receipt_binds_exact_local_artifacts(self) -> None:
        self.assertEqual(
            self.candidate["schema"], "qikvrt_ietf_draft_candidate_v1"
        )
        self.assertEqual(
            self.candidate["state"],
            "AWAITING_PREVIOUS_VERSION_AUTHOR_APPROVAL",
        )
        self.assertIs(self.candidate["datatracker_submission_performed"], True)
        self.assertIs(self.candidate["submitted"], True)
        self.assertEqual(self.candidate["submission_checks"], "PASS")
        self.assertIs(self.candidate["published"], False)
        self.assertIs(self.candidate["consensus"], False)
        self.assertEqual(
            self.candidate["internet_draft"],
            "draft-lohmann-qikvrt-effect-ack-03",
        )
        for kind, path in (
            ("xml", REVISION_03_XML),
            ("txt", REVISION_03_TXT),
            ("html", REVISION_03_HTML),
        ):
            raw = path.read_bytes()
            binding = self.candidate["artifacts"][kind]
            self.assertEqual(binding["filename"], path.name)
            self.assertEqual(binding["size_bytes"], len(raw))
            self.assertEqual(
                binding["sha256"], hashlib.sha256(raw).hexdigest()
            )

    def test_submission_receipt_records_pending_effect_without_overclaim(self) -> None:
        receipt = self.submission_receipt
        self.assertEqual(
            receipt["schema"],
            "qikvrt_ietf_datatracker_submission_receipt_v1",
        )
        self.assertEqual(receipt["submission_id"], 167201)
        self.assertEqual(
            receipt["internet_draft"],
            "draft-lohmann-qikvrt-effect-ack-03",
        )
        self.assertEqual(receipt["submission_checks"], "PASS")
        self.assertIs(receipt["submitted"], True)
        self.assertEqual(
            receipt["state"],
            "AWAITING_PREVIOUS_VERSION_AUTHOR_APPROVAL",
        )
        self.assertIs(receipt["author_email_notification_sent"], True)
        self.assertIs(receipt["published"], False)
        self.assertIs(receipt["consensus"], False)
        self.assertIs(
            receipt["security_boundary"]["secret_status_token_recorded"],
            False,
        )
        self.assertIs(
            receipt["security_boundary"][
                "token_bearing_status_url_recorded"
            ],
            False,
        )
        serialized = REVISION_03_SUBMISSION_RECEIPT.read_text(encoding="utf-8")
        self.assertNotIn("/submit/status/167201/", serialized)
        for kind, path in (
            ("xml", REVISION_03_XML),
            ("txt", REVISION_03_TXT),
            ("html", REVISION_03_HTML),
        ):
            raw = path.read_bytes()
            binding = receipt["artifacts"][kind]
            self.assertEqual(binding["path"], path.relative_to(ROOT).as_posix())
            self.assertEqual(binding["size_bytes"], len(raw))
            self.assertEqual(binding["sha256"], hashlib.sha256(raw).hexdigest())

    def test_publication_receipt_adds_current_state_without_rewriting_history(
        self,
    ) -> None:
        receipt = self.publication_receipt
        self.assertEqual(
            set(receipt),
            {
                "_license",
                "schema",
                "receipt_id",
                "observed_utc",
                "internet_draft",
                "revision",
                "public_state",
                "observation",
                "datatracker",
                "artifacts",
                "comparison",
                "candidate_before_transition",
                "repository_binding",
                "truth_boundaries",
            },
        )
        self.assertEqual(
            receipt["schema"],
            "qikvrt_ietf_datatracker_publication_receipt_v1",
        )
        self.assertEqual(
            receipt["public_state"], "ACTIVE_INDIVIDUAL_INTERNET_DRAFT"
        )
        self.assertIs(receipt["observation"]["read_only"], True)
        self.assertIs(
            receipt["observation"]["remote_mutation_performed"],
            False,
        )
        predecessor = receipt["candidate_before_transition"]
        self.assertEqual(
            predecessor["path"],
            REVISION_03_SUBMISSION_RECEIPT.relative_to(ROOT).as_posix(),
        )
        self.assertEqual(
            predecessor["state"],
            "AWAITING_PREVIOUS_VERSION_AUTHOR_APPROVAL",
        )
        self.assertEqual(
            predecessor["sha256"],
            hashlib.sha256(REVISION_03_SUBMISSION_RECEIPT.read_bytes()).hexdigest(),
        )
        for kind, path in (("xml", REVISION_03_XML), ("txt", REVISION_03_TXT)):
            binding = receipt["artifacts"][kind]
            self.assertIs(binding["byte_identical_to_local"], True)
            self.assertEqual(binding["local"]["size_bytes"], path.stat().st_size)
            self.assertEqual(
                binding["local"]["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            self.assertEqual(binding["local"]["sha256"], binding["public"]["sha256"])
        html = receipt["artifacts"]["html"]
        self.assertIs(html["byte_identical_to_local"], False)
        self.assertNotEqual(html["local"]["sha256"], html["public"]["sha256"])
        self.assertEqual(receipt["comparison"]["exact_kinds"], ["txt", "xml"])
        self.assertEqual(receipt["comparison"]["divergent_kinds"], ["html"])
        boundaries = receipt["truth_boundaries"]
        self.assertIs(boundaries["internet_draft_publication_verified"], True)
        self.assertIs(boundaries["ietf_standard_claimed"], False)
        self.assertIs(boundaries["ietf_consensus_claimed"], False)
        self.assertIs(
            boundaries["physical_or_ontic_retrocausality_proved"],
            False,
        )

    def test_revision_metadata_is_exact(self) -> None:
        self.assertEqual(
            self.revision_02.attrib["docName"],
            "draft-lohmann-qikvrt-effect-ack-02",
        )
        self.assertEqual(
            self.revision_03.attrib["docName"],
            "draft-lohmann-qikvrt-effect-ack-03",
        )
        for attribute in ("version", "ipr", "category", "submissionType"):
            self.assertEqual(
                self.revision_03.attrib[attribute],
                self.revision_02.attrib[attribute],
                attribute,
            )
        self.assertEqual(self.revision_03.attrib["version"], "3")
        self.assertEqual(self.revision_03.attrib["ipr"], "trust200902")
        self.assertEqual(self.revision_03.attrib["category"], "exp")
        self.assertEqual(self.revision_03.attrib["submissionType"], "IETF")

        front = self.revision_03.find("front")
        self.assertIsNotNone(front)
        assert front is not None
        series = front.find("seriesInfo")
        date = front.find("date")
        self.assertIsNotNone(series)
        self.assertIsNotNone(date)
        assert series is not None and date is not None
        self.assertEqual(
            series.attrib,
            {
                "name": "Internet-Draft",
                "value": "draft-lohmann-qikvrt-effect-ack-03",
            },
        )
        self.assertEqual(
            date.attrib,
            {"year": "2026", "month": "August", "day": "2"},
        )

    def test_wire_v1_counts_and_values_are_unchanged(self) -> None:
        fields_02 = field_names(self.revision_02)
        fields_03 = field_names(self.revision_03)
        states_02 = state_names(self.revision_02)
        states_03 = state_names(self.revision_03)
        conjuncts_02 = done_conjuncts(self.revision_02)
        conjuncts_03 = done_conjuncts(self.revision_03)

        self.assertEqual(fields_03, fields_02)
        self.assertEqual(fields_03, EXPECTED_FIELDS)
        self.assertEqual(len(fields_03), 35)
        self.assertEqual(states_03, states_02)
        self.assertEqual(states_03, EXPECTED_STATES)
        self.assertEqual(len(states_03), 5)
        self.assertEqual(conjuncts_03, conjuncts_02)
        self.assertEqual(conjuncts_03, EXPECTED_CORE_DONE)
        self.assertEqual(len(conjuncts_03), 17)

    def test_complete_v1_cddl_text_is_byte_equal(self) -> None:
        self.assertEqual(
            sourcecode_text(self.revision_03, "complete-cddl", "cddl"),
            sourcecode_text(self.revision_02, "complete-cddl", "cddl"),
        )

    def test_normative_algorithm_wire_security_and_iana_sections_are_unchanged(
        self,
    ) -> None:
        for anchor in UNCHANGED_NORMATIVE_ANCHORS:
            self.assertEqual(
                canonical_element(section(self.revision_03, anchor)),
                canonical_element(section(self.revision_02, anchor)),
                anchor,
            )
        self.assertIn(
            "This document requests no IANA actions.",
            section_text(self.revision_03, "iana"),
        )

    def test_new_sections_are_explicitly_non_normative_and_evidence_bound(
        self,
    ) -> None:
        implementation = section(self.revision_03, "implementation-status")
        self.assertEqual(implementation.attrib.get("removeInRFC"), "true")

        typed = section(self.revision_03, "typed-claim-receipt-status")
        vrt = section(self.revision_03, "vrt-research-mapping")
        self.assertIn(typed, list(implementation))
        self.assertIn(vrt, list(implementation))

        typed_text = section_text(self.revision_03, "typed-claim-receipt-status")
        vrt_text = section_text(self.revision_03, "vrt-research-mapping")
        for marker in TYPED_CLAIM_MARKERS:
            self.assertIn(normalized(marker), typed_text, marker)
        for marker in VRT_BOUNDARY_MARKERS:
            self.assertIn(normalized(marker), vrt_text, marker)
        self.assertIsNone(BCP14_KEYWORD.search(typed_text))
        self.assertIsNone(BCP14_KEYWORD.search(vrt_text))

    def test_revision_03_is_additive_after_metadata_normalization(self) -> None:
        normalized_03 = copy.deepcopy(self.revision_03)
        implementation = section(normalized_03, "implementation-status")
        for anchor in ("typed-claim-receipt-status", "vrt-research-mapping"):
            implementation.remove(section(normalized_03, anchor))
        back = normalized_03.find("back")
        self.assertIsNotNone(back)
        assert back is not None
        back.remove(section(normalized_03, "change-log-03"))

        normalized_03.set("docName", "draft-lohmann-qikvrt-effect-ack-02")
        series = normalized_03.find("./front/seriesInfo")
        date = normalized_03.find("./front/date")
        self.assertIsNotNone(series)
        self.assertIsNotNone(date)
        assert series is not None and date is not None
        series.set("value", "draft-lohmann-qikvrt-effect-ack-02")
        date.attrib.clear()
        date.attrib.update({"year": "2026", "month": "July", "day": "31"})

        self.assertEqual(
            canonical_element(normalized_03),
            canonical_element(self.revision_02),
        )

    def test_archival_date_warning_filter_is_exact(self) -> None:
        expected = (
            f"/tmp/{REVISION_03_XML.name}(27): Warning: The document date "
            f"({REVISION_03_DOCUMENT_DATE}) is more than 3 days away from today's date"
        )
        self.assertTrue(is_expected_archival_date_warning(expected))
        self.assertFalse(
            is_expected_archival_date_warning(expected.replace("2026-08-02", "2026-08-03"))
        )
        self.assertFalse(
            is_expected_archival_date_warning(expected.replace("Warning:", "Error:"))
        )
        self.assertFalse(
            is_expected_archival_date_warning(expected.replace(REVISION_03_XML.name, "other.xml"))
        )

    def test_optional_offline_renders_are_warning_free(self) -> None:
        if XML2RFC is None:
            self.skipTest("--xml2rfc PATH was not supplied")
        xml2rfc = XML2RFC.resolve(strict=True)
        self.assertTrue(xml2rfc.is_file())
        version = subprocess.run(
            [str(xml2rfc), "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("xml2rfc 3.34.0", "\n".join((version.stdout, version.stderr)))

        with tempfile.TemporaryDirectory(
            prefix="qikvrt-ietf-revision-03-render-"
        ) as temporary:
            scratch = Path(temporary)
            cache = scratch / "cache"
            cache.mkdir()
            rendered_txt = scratch / "draft-03.txt"
            rendered_html = scratch / "draft-03.html"
            run_renderer(xml2rfc, rendered_txt, cache, "text")
            run_renderer(xml2rfc, rendered_html, cache, "html")
            self.assertEqual(rendered_txt.read_bytes(), REVISION_03_TXT.read_bytes())
            self.assertEqual(
                rendered_html.read_bytes(), REVISION_03_HTML.read_bytes()
            )


def main() -> None:
    global XML2RFC

    parser = argparse.ArgumentParser(
        description=(
            "Validate the additive Draft-03 XML revision and optionally render "
            "it with the exact offline xml2rfc toolchain."
        ),
    )
    parser.add_argument("--xml2rfc", type=Path)
    args, unittest_args = parser.parse_known_args()
    XML2RFC = args.xml2rfc
    unittest.main(argv=[sys.argv[0], *unittest_args], verbosity=2)


if __name__ == "__main__":
    main()
