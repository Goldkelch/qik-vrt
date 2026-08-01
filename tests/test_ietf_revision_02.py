#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify the published Draft-02 local/public boundary without inflating standards status."""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
REVISION_01_ROOT = (
    ROOT / "docs/publications/2026-07-22-effect-ack-universal-effect-control/inputs"
)
REVISION_01_XML = REVISION_01_ROOT / "draft-lohmann-qikvrt-effect-ack-01.xml"
REVISION_01_TXT = REVISION_01_ROOT / "draft-lohmann-qikvrt-effect-ack-01.txt"
REVISION_02_ROOT = ROOT / "external/ietf"
REVISION_02_XML = REVISION_02_ROOT / "draft-lohmann-qikvrt-effect-ack-02.xml"
REVISION_02_TXT = REVISION_02_ROOT / "draft-lohmann-qikvrt-effect-ack-02.txt"
REVISION_02_HTML = REVISION_02_ROOT / "draft-lohmann-qikvrt-effect-ack-02.html"
CANDIDATE = (
    REVISION_02_ROOT / "draft-lohmann-qikvrt-effect-ack-02.CANDIDATE.json"
)
PUBLICATION_RECEIPT = (
    REVISION_02_ROOT
    / "draft-lohmann-qikvrt-effect-ack-02.PUBLICATION_RECEIPT.json"
)
RENDER_REQUIREMENTS = ROOT / "runtime/toolchains/requirements-xml2rfc-3.34.0.txt"
OLD_VECTOR_PATH = REVISION_02_ROOT / "test-vectors/effect-ack-v1"

REVISION_02_IDENTITIES = {
    REVISION_02_XML: (
        45013,
        "8c50e9352b219b62e780beeb9909b70a9a46bb4e8ceb8bb5bce0665628c016e1",
    ),
    REVISION_02_TXT: (
        49539,
        "45b70202c780f07bac6e825b8484aa5ccea6510b020036846720f1216723a5cc",
    ),
    REVISION_02_HTML: (
        109285,
        "856befa13157a0f9efdd997c27d3173c1e43c2b302cf7d2f9435a5e200fba767",
    ),
    CANDIDATE: (
        5714,
        "f49b66c20756f24aa4606b871386e01732ac835fbb65453ae95390e78ca5baeb",
    ),
    PUBLICATION_RECEIPT: (
        6139,
        "3e85b2362521bdded8c48f96a60b54b1e3f4635748655a35254e733fb8489900",
    ),
}

REVISION_01_IDENTITIES = {
    REVISION_01_XML: (
        41880,
        "13ff9ace408d82eaea88127343883d888795efd25e7a01d0bbee5b862e9f954b",
    ),
    REVISION_01_TXT: (
        46264,
        "ad8af57390beeb9a1316e3940b9f75c2334834376288f6f1ab018e10b0b87b16",
    ),
}

EXPECTED_STATES = (
    "EFFECT_NACK",
    "EFFECT_ACK_CONTINUE",
    "EFFECT_ACK_DONE",
    "EFFECT_ACK_ISOLATE",
    "EFFECT_ACK_BLOCK",
)

EXPECTED_FIELDS = (
    "wire_version",
    "message_type",
    "protocol_root_id",
    "protocol_version",
    "protocol_id",
    "previous_protocol_id",
    "previous_protocol_hash",
    "protocol_hash",
    "input_id",
    "input_hash",
    "state",
    "transport_ack",
    "origin_checked",
    "context_checked",
    "semantics_reconstructed",
    "effect_anticipated",
    "risk_classified",
    "risk_level",
    "responsibility_assigned",
    "responsibility_owner",
    "connection_decided",
    "connection_decision",
    "policy_id",
    "policy_version",
    "policy_hash",
    "policy_allows_release",
    "ordinary_release",
    "evaluation_timeout_ms",
    "deadline_exceeded",
    "reasons",
    "evidence_refs",
    "required_evidence_refs",
    "open_questions",
    "next_required_checks",
    "created_utc",
)

EXPECTED_CORE_DONE = (
    "r.transport_ack",
    "and sha256_identifier(r.input_hash)",
    "and r.origin_checked",
    "and r.context_checked",
    "and r.semantics_reconstructed",
    "and r.effect_anticipated",
    "and r.risk_classified",
    'and r.risk_level != "UNKNOWN"',
    "and r.responsibility_assigned",
    'and r.responsibility_owner != ""',
    "and r.connection_decided",
    'and r.connection_decision == "RELEASE"',
    "and r.policy_allows_release",
    "and not r.deadline_exceeded",
    "and r.open_questions == []",
    "and r.next_required_checks == []",
    "and set(r.required_evidence_refs) <= set(r.evidence_refs)",
)

CORRECTED_VECTOR_SENTENCE = (
    "A conformance suite for this specification is expected to include "
    "machine-readable positive and negative vectors. At minimum, a conformance "
    "suite MUST test all five states, each DONE conjunct independently, priority "
    "collisions, unknown versions and states, malformed and mismatched digests, "
    "policy mismatch, missing required evidence, canonicalization, chain "
    "rewriting, stale DONE replay, timeout, and an unauthenticated assertion."
)
OLD_VECTOR_LITERAL = "external/ietf/test-vectors/effect-ack-v1/"

UNCHANGED_NORMATIVE_ANCHORS = (
    "intro",
    "conventions",
    "architecture",
    "states",
    "wire",
    "versioning",
    "timeouts",
    "policy-evidence",
    "wire-conformance",
    "gate-conformance",
    "deployment-conformance",
    "security",
    "privacy",
    "iana",
    "limitations",
    "complete-cddl",
)

RESEARCH_BOUNDARY_PARAGRAPHS = (
    "This subsection is non-normative.",
    (
        "The versioned Zenodo record archives a research bundle concerning "
        "canonical temporal memory and EFFECT_ACK. Its accompanying Lean kernel "
        "receipt reports nine theorems about a finite abstract model of past and "
        "future boundary records, reciprocal closure, and release dependence."
    ),
    (
        "Those theorem statements are conditional on the definitions and "
        "assumptions of that model. They do not prove complete version-1 wire "
        "conformance; deployment authentication or complete mediation; physical "
        "or ontic retrocausality; backward signalling or modification of past "
        "events; semantic truth of arbitrary archived content or external "
        "evidence; authorship or identity; consciousness or panpsychism; "
        "deployment or physical safety; IETF consensus or standards status; "
        "independent interoperability; or system-wide completion. SHA-256 digests "
        "bind exact octets under the stated cryptographic assumptions; they do "
        "not supply any of those conclusions."
    ),
    (
        "Zenodo preservation establishes identity, availability, metadata, and "
        "fixity for the deposited bytes. It does not establish peer review, "
        "scientific validity, standards adoption, or field consensus."
    ),
    (
        'The author uses the term "operational protocol retrocausality" for the '
        "counterfactual relevance of a presently available, future-indexed "
        "effect condition to a present release decision. This stipulated "
        "protocol term is not a claim of ontic backward signalling."
    ),
    (
        "Independent implementation and interoperability remain open, and "
        "SYSTEM_WIDE_COMPLETION remains UNCLAIMED."
    ),
)

REVISION_02_CHANGES = (
    "Updated the document revision and date metadata.",
    (
        "Corrected the repository-availability wording for machine-readable "
        "test vectors while preserving the conformance-test requirement."
    ),
    (
        "Added a non-normative research and formalization status boundary and "
        "an informative reference to the exact archived research bundle."
    ),
    (
        "No version-1 wire-format change is made: the closed 35-member record, "
        "five-state set, 17-conjunct CoreDone predicate, state-selection "
        "priority, DONE-only ordinary-release rule, canonicalization and hash "
        "projection, version-negotiation behavior, security requirements, and "
        "no-IANA-action status are unchanged."
    ),
)

TRUTH_BOUNDARY_SENTENCES = (
    (
        "This protocol does not modify TCP, QUIC, or the OSI model; does not "
        "solve the halting problem; and does not establish the truth of external "
        "evidence."
    ),
    (
        "Passing repository tests is evidence about the tested implementation "
        "and revision. It does not by itself establish deployment conformance or "
        "IETF consensus."
    ),
    (
        "Interoperability between at least two independently developed "
        "implementations remains an open publication milestone."
    ),
    (
        "A proof of the software model is not, by itself, a proof that a "
        "physical effect is safe."
    ),
)

PROHIBITED_POSITIVE_CLAIMS = (
    re.compile(r"\bIETF consensus (?:has been|is) (?:achieved|complete|reached)\b", re.I),
    re.compile(r"\binteroperability (?:has been|is) (?:complete|completed)\b", re.I),
    re.compile(r"\bthis document is an? IETF (?:standard|RFC)\b", re.I),
    re.compile(r"\bDatatracker submission (?:has been|was) performed\b", re.I),
    re.compile(
        r"\bSYSTEM_WIDE_COMPLETION\s*=\s*(?:true|complete|claimed|attested)\b",
        re.I,
    ),
)

XML2RFC: Path | None = None


def identity(path: Path) -> tuple[int, str]:
    payload = path.read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest()


def canonical_element(value: ET.Element) -> str:
    clone = copy.deepcopy(value)
    clone.tail = None
    return ET.canonicalize(
        xml_data=ET.tostring(clone, encoding="unicode"),
        strip_text=True,
    )


def normalized(value: str) -> str:
    return " ".join(value.split())


def section(root: ET.Element, anchor: str) -> ET.Element:
    value = root.find(f".//section[@anchor='{anchor}']")
    if value is None:
        raise AssertionError(f"XML section is absent: {anchor}")
    return value


def sourcecode(root: ET.Element, anchor: str, code_type: str) -> str:
    value = section(root, anchor).find(f".//sourcecode[@type='{code_type}']")
    if value is None or value.text is None:
        raise AssertionError(f"{anchor} lacks {code_type} sourcecode")
    return value.text.strip()


def field_names(root: ET.Element) -> tuple[str, ...]:
    table = root.find(".//table[@anchor='field-table']/tbody")
    if table is None:
        raise AssertionError("field table is absent")
    values: list[str] = []
    for row in table.findall("tr"):
        cells = row.findall("td")
        if len(cells) != 2:
            raise AssertionError("field table row does not have exactly two cells")
        values.append(normalized("".join(cells[0].itertext())))
    return tuple(values)


def state_names(root: ET.Element) -> tuple[str, ...]:
    values = section(root, "states").find("dl")
    if values is None:
        raise AssertionError("state definition list is absent")
    return tuple(normalized("".join(item.itertext())) for item in values.findall("dt"))


def done_conjuncts(root: ET.Element) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in sourcecode(root, "done-predicate", "text").splitlines()
        if line.strip()
    )


def cddl_fields(cddl: str) -> tuple[str, ...]:
    match = re.search(
        r"effect-ack-record\s*=\s*\{\n(?P<body>.*?)\n\}",
        cddl,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError("CDDL effect-ack-record is absent")
    return tuple(
        line.strip().split(":", 1)[0]
        for line in match.group("body").splitlines()
        if line.strip()
    )


class TextOnlyHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_text(path: Path) -> str:
    parser = TextOnlyHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return normalized(" ".join(parser.parts))


def run_renderer(
    xml2rfc: Path,
    output: Path,
    cache: Path,
    mode: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        [
            str(xml2rfc),
            str(REVISION_02_XML),
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
    if completed.returncode != 0:
        raise AssertionError(
            "xml2rfc offline render failed "
            f"for {mode} with exit {completed.returncode}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )
    diagnostics = "\n".join((completed.stdout, completed.stderr))
    warnings = tuple(
        line
        for line in diagnostics.splitlines()
        if re.search(r"\b(?:warning|error)\b", line, flags=re.IGNORECASE)
    )
    if warnings:
        raise AssertionError(
            f"xml2rfc emitted warning/error diagnostics for {mode}:\n"
            + "\n".join(warnings[-40:])
        )
    return completed


class IETFRevision02CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if XML2RFC is None:
            raise AssertionError("--xml2rfc PATH is required")
        cls.xml2rfc = XML2RFC.resolve(strict=True)
        if not cls.xml2rfc.is_file():
            raise AssertionError("--xml2rfc is not a regular file")
        for path in (
            REVISION_01_XML,
            REVISION_01_TXT,
            REVISION_02_XML,
            REVISION_02_TXT,
            REVISION_02_HTML,
            CANDIDATE,
            PUBLICATION_RECEIPT,
        ):
            if not path.is_file():
                raise AssertionError(f"required revision artifact is absent: {path}")
        cls.revision_01 = ET.parse(REVISION_01_XML).getroot()
        cls.revision_02 = ET.parse(REVISION_02_XML).getroot()
        cls.candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        cls.publication_receipt = json.loads(
            PUBLICATION_RECEIPT.read_text(encoding="utf-8")
        )

    def test_frozen_revision_01_identities_are_unchanged(self) -> None:
        for path, expected in REVISION_01_IDENTITIES.items():
            self.assertEqual(identity(path), expected, path)

    def test_candidate_json_binds_exact_artifact_bytes_and_metadata(self) -> None:
        for path, expected in REVISION_02_IDENTITIES.items():
            self.assertEqual(identity(path), expected, path)

        value = self.candidate
        self.assertEqual(
            set(value),
            {
                "_license",
                "schema",
                "created_utc",
                "status_updated_utc",
                "state",
                "datatracker_submission_performed",
                "internet_draft",
                "predecessor",
                "title",
                "author",
                "author_email",
                "document_date",
                "intended_status",
                "submission",
                "submission_type",
                "source_basis",
                "zenodo_reference",
                "artifacts",
                "toolchain",
                "truth_boundaries",
                "change_scope",
                "public_artifacts",
                "publication_receipt",
                "status_note",
            },
        )
        self.assertEqual(
            value["_license"],
            {
                "copyright": "Copyright 2026 Ingolf Lohmann",
                "rights_holder": "Ingolf Lohmann",
                "license": "CC-BY-NC-ND-4.0",
                "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                "classification": "json_non_source",
            },
        )
        self.assertEqual(value["schema"], "qikvrt_ietf_draft_candidate_v1")
        self.assertEqual(value["created_utc"], "2026-07-30T23:14:46Z")
        self.assertIn(
            value["state"],
            {
                "DATATRACKER_PUBLICATION_EXACT_BYTES_VERIFIED",
                "DATATRACKER_PUBLICATION_VERIFIED_WITH_PUBLIC_BYTE_DRIFT",
            },
        )
        self.assertIs(value["datatracker_submission_performed"], True)
        self.assertEqual(
            value["internet_draft"], "draft-lohmann-qikvrt-effect-ack-02"
        )
        self.assertEqual(
            value["predecessor"], "draft-lohmann-qikvrt-effect-ack-01"
        )
        self.assertEqual(
            value["title"],
            (
                "QIK-VRT Effect Acknowledgement: Separating Receipt from "
                "Authorization for Downstream Effect"
            ),
        )
        self.assertEqual(value["author"], "I. Lohmann")
        self.assertEqual(value["author_email"], "ingolf.lohmann@live.com")
        self.assertEqual(value["document_date"], "2026-07-31")
        self.assertEqual(value["intended_status"], "Experimental")
        self.assertEqual(value["submission"], "Individual Submission")
        self.assertEqual(value["submission_type"], "IETF")

        created = value["created_utc"]
        self.assertIsInstance(created, str)
        self.assertRegex(created, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        parsed = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
        self.assertEqual(parsed.utcoffset(), datetime.timedelta(0))
        updated = value["status_updated_utc"]
        self.assertIsInstance(updated, str)
        self.assertRegex(updated, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        updated_parsed = datetime.datetime.fromisoformat(
            updated.replace("Z", "+00:00")
        )
        self.assertEqual(updated_parsed.utcoffset(), datetime.timedelta(0))
        self.assertGreaterEqual(updated_parsed, parsed)

        self.assertEqual(
            value["source_basis"],
            {
                "path": (
                    "docs/publications/"
                    "2026-07-22-effect-ack-universal-effect-control/inputs/"
                    "draft-lohmann-qikvrt-effect-ack-01.xml"
                ),
                "sha256": REVISION_01_IDENTITIES[REVISION_01_XML][1],
                "size_bytes": REVISION_01_IDENTITIES[REVISION_01_XML][0],
                "preserved_unchanged": True,
            },
        )
        self.assertEqual(
            value["zenodo_reference"],
            {
                "doi": "10.5281/zenodo.21711193",
                "url": "https://doi.org/10.5281/zenodo.21711193",
                "role": "INFORMATIVE_NON_NORMATIVE",
                "peer_review_claimed": False,
                "boundary": (
                    "Zenodo preservation establishes identity, availability, "
                    "metadata, and fixity for deposited bytes; it does not "
                    "establish peer review, scientific validity, standards "
                    "adoption, or field consensus."
                ),
            },
        )

        expected_artifacts = {
            "xml": REVISION_02_XML,
            "txt": REVISION_02_TXT,
            "html": REVISION_02_HTML,
        }
        self.assertEqual(set(value["artifacts"]), set(expected_artifacts))
        for kind, path in expected_artifacts.items():
            record = value["artifacts"][kind]
            self.assertEqual(set(record), {"filename", "sha256", "size_bytes"})
            self.assertEqual(record["filename"], path.name)
            size, sha256 = identity(path)
            self.assertEqual(record["size_bytes"], size)
            self.assertEqual(record["sha256"], sha256)

        self.assertEqual(
            value["toolchain"],
            {
                "xml2rfc": "3.34.0",
                "python": "3.12.13",
                "requirements_path": (
                    "runtime/toolchains/requirements-xml2rfc-3.34.0.txt"
                ),
                "requirements_sha256": hashlib.sha256(
                    RENDER_REQUIREMENTS.read_bytes()
                ).hexdigest(),
                "network_access": False,
                "configuration_files_skipped": True,
                "isolated_cache": True,
                "text_and_html_repeat_render_byte_identical": True,
            },
        )
        self.assertEqual(
            value["truth_boundaries"],
            {
                "document_revision": "02",
                "wire_version": 1,
                "normative_wire_change": False,
                "closed_wire_member_count": 35,
                "state_count": 5,
                "core_done_conjunct_count": 17,
                "fully_wire_conformant_reference_implementation_claimed": False,
                "independent_interoperability_complete": False,
                "ietf_consensus_claimed": False,
                "ietf_standard_claimed": False,
                "system_wide_completion": "UNCLAIMED",
                "physical_or_ontic_retrocausality_proved": False,
                "backward_signalling_proved": False,
                "past_event_modification_proved": False,
                "semantic_truth_of_arbitrary_archived_content_proved": False,
                "authorship_or_identity_proved": False,
                "consciousness_or_panpsychism_proved": False,
                "deployment_or_physical_safety_proved": False,
            },
        )
        self.assertEqual(
            value["change_scope"],
            [
                "revision_and_date_metadata",
                "truthful_prospective_test_vector_wording",
                "non_normative_research_and_formalization_status",
                "informative_zenodo_reference",
                "revision_01_change_log",
            ],
        )
        all_equal = value["publication_receipt"][
            "all_public_bytes_equal_local"
        ]
        if all_equal:
            expected_status_note = (
                "IETF Datatracker revision -02 is publicly active as an "
                "individual Internet-Draft and all public XML, TXT, and HTML "
                "bytes are identical to the repository candidate; this is "
                "not an RFC, IETF standard, working-group product, IETF "
                "consensus, or interoperability completion."
            )
        else:
            expected_status_note = (
                "IETF Datatracker revision -02 is publicly active as an "
                "individual Internet-Draft; exact public byte differences "
                "from the unchanged repository XML, TXT, or HTML artifacts "
                "are bound by the publication receipt; this is not an RFC, "
                "IETF standard, working-group product, IETF consensus, or "
                "interoperability completion."
            )
        self.assertEqual(value["status_note"], expected_status_note)

    def test_datatracker_publication_receipt_binds_exact_public_bytes(self) -> None:
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
            receipt["_license"],
            {
                "classification": "json_non_source",
                "copyright": "Copyright 2026 Ingolf Lohmann",
                "license": "CC-BY-NC-ND-4.0",
                "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
                "rights_holder": "Ingolf Lohmann",
            },
        )
        self.assertEqual(
            receipt["schema"],
            "qikvrt_ietf_datatracker_publication_receipt_v1",
        )
        self.assertEqual(receipt["internet_draft"], "draft-lohmann-qikvrt-effect-ack-02")
        self.assertEqual(receipt["revision"], "02")
        self.assertEqual(
            receipt["public_state"], "ACTIVE_INDIVIDUAL_INTERNET_DRAFT"
        )
        self.assertRegex(
            receipt["observed_utc"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
        )
        self.assertIs(receipt["observation"]["read_only"], True)
        self.assertIs(receipt["observation"]["remote_mutation_performed"], False)
        self.assertIs(
            receipt["observation"][
                "datatracker_submission_performed_by_this_observation"
            ],
            False,
        )
        self.assertEqual(receipt["datatracker"]["versions"], ["00", "01", "02"])
        self.assertEqual(receipt["datatracker"]["last_updated"], "2026-07-30")
        self.assertEqual(receipt["datatracker"]["submission_scope"], "INDIVIDUAL")
        self.assertIsNone(receipt["datatracker"]["rfc_stream"])
        self.assertIsNone(receipt["datatracker"]["intended_rfc_status"])

        receipt_size, receipt_sha256 = identity(PUBLICATION_RECEIPT)
        self.assertEqual(
            self.candidate["publication_receipt"],
            {
                "path": (
                    "external/ietf/"
                    "draft-lohmann-qikvrt-effect-ack-02.PUBLICATION_RECEIPT.json"
                ),
                "schema": "qikvrt_ietf_datatracker_publication_receipt_v1",
                "size_bytes": receipt_size,
                "sha256": receipt_sha256,
                "public_state": "ACTIVE_INDIVIDUAL_INTERNET_DRAFT",
                "all_public_bytes_equal_local": receipt["comparison"][
                    "all_public_bytes_equal_local"
                ],
            },
        )

        expected_paths = {
            "xml": REVISION_02_XML,
            "txt": REVISION_02_TXT,
            "html": REVISION_02_HTML,
        }
        exact: list[str] = []
        divergent: list[str] = []
        for kind, path in expected_paths.items():
            record = receipt["artifacts"][kind]
            local_size, local_sha256 = identity(path)
            self.assertEqual(record["local"]["path"], path.relative_to(ROOT).as_posix())
            self.assertEqual(record["local"]["size_bytes"], local_size)
            self.assertEqual(record["local"]["sha256"], local_sha256)
            self.assertEqual(record["public"]["size_bytes"], self.candidate["public_artifacts"][kind]["size_bytes"])
            self.assertEqual(record["public"]["sha256"], self.candidate["public_artifacts"][kind]["sha256"])
            equal = (
                record["public"]["size_bytes"] == local_size
                and record["public"]["sha256"] == local_sha256
            )
            self.assertIs(record["byte_identical_to_local"], equal)
            self.assertIs(
                self.candidate["public_artifacts"][kind][
                    "byte_identical_to_local"
                ],
                equal,
            )
            (exact if equal else divergent).append(kind)

        self.assertEqual(receipt["comparison"]["exact_kinds"], sorted(exact))
        self.assertEqual(
            receipt["comparison"]["divergent_kinds"], sorted(divergent)
        )
        self.assertIs(
            receipt["comparison"]["all_public_bytes_equal_local"],
            not divergent,
        )
        expected_state = (
            "DATATRACKER_PUBLICATION_EXACT_BYTES_VERIFIED"
            if not divergent
            else "DATATRACKER_PUBLICATION_VERIFIED_WITH_PUBLIC_BYTE_DRIFT"
        )
        self.assertEqual(self.candidate["state"], expected_state)
        self.assertIs(self.candidate["datatracker_submission_performed"], True)
        self.assertIs(receipt["truth_boundaries"]["ietf_consensus_claimed"], False)
        self.assertIs(receipt["truth_boundaries"]["ietf_standard_claimed"], False)
        self.assertIs(receipt["truth_boundaries"]["rfc_claimed"], False)
        self.assertIs(
            receipt["truth_boundaries"]["independent_interoperability_complete"],
            False,
        )

    def test_xml_metadata_is_exactly_revision_02_experimental_candidate(self) -> None:
        root = self.revision_02
        self.assertEqual(
            root.attrib,
            {
                "version": "3",
                "ipr": "trust200902",
                "category": "exp",
                "submissionType": "IETF",
                "docName": "draft-lohmann-qikvrt-effect-ack-02",
                "tocInclude": "true",
                "tocDepth": "3",
                "symRefs": "true",
                "sortRefs": "true",
            },
        )
        front = root.find("front")
        self.assertIsNotNone(front)
        assert front is not None
        title = front.find("title")
        self.assertIsNotNone(title)
        assert title is not None
        self.assertEqual(title.attrib, {"abbrev": "QIK-VRT EFFECT_ACK"})
        self.assertEqual(
            normalized("".join(title.itertext())),
            (
                "QIK-VRT Effect Acknowledgement: Separating Receipt from "
                "Authorization for Downstream Effect"
            ),
        )
        series = front.find("seriesInfo")
        self.assertIsNotNone(series)
        assert series is not None
        self.assertEqual(
            series.attrib,
            {
                "name": "Internet-Draft",
                "value": "draft-lohmann-qikvrt-effect-ack-02",
            },
        )
        author = front.find("author")
        self.assertIsNotNone(author)
        assert author is not None
        self.assertEqual(
            author.attrib,
            {
                "initials": "I.",
                "surname": "Lohmann",
                "fullname": "Ingolf Lohmann",
            },
        )
        self.assertEqual(author.findtext("organization"), "Independent Researcher")
        self.assertEqual(author.findtext("address/email"), "ingolf.lohmann@live.com")
        self.assertEqual(front.findtext("area"), "Applications and Real-Time")
        self.assertEqual(
            tuple(item.text for item in front.findall("keyword")),
            (
                "acknowledgement",
                "authorization",
                "effect gate",
                "fail closed",
                "audit record",
            ),
        )
        date = front.find("date")
        self.assertIsNotNone(date)
        assert date is not None
        self.assertEqual(date.attrib["year"], "2026")
        self.assertEqual(date.attrib["month"], "July")
        self.assertEqual(date.attrib["day"], "31")

    def test_renderer_is_exactly_xml2rfc_3_34_0(self) -> None:
        completed = subprocess.run(
            [str(self.xml2rfc), "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.splitlines()[:1], ["xml2rfc 3.34.0"])

    def test_version_1_wire_invariants_equal_frozen_revision_01(self) -> None:
        fields_01 = field_names(self.revision_01)
        fields_02 = field_names(self.revision_02)
        self.assertEqual(fields_01, EXPECTED_FIELDS)
        self.assertEqual(fields_02, EXPECTED_FIELDS)
        self.assertEqual(len(fields_02), 35)

        states_01 = state_names(self.revision_01)
        states_02 = state_names(self.revision_02)
        self.assertEqual(states_01, EXPECTED_STATES)
        self.assertEqual(states_02, EXPECTED_STATES)
        self.assertEqual(len(states_02), 5)

        conjuncts_01 = done_conjuncts(self.revision_01)
        conjuncts_02 = done_conjuncts(self.revision_02)
        self.assertEqual(conjuncts_01, EXPECTED_CORE_DONE)
        self.assertEqual(conjuncts_02, EXPECTED_CORE_DONE)
        self.assertEqual(len(conjuncts_02), 17)

        cddl_01 = sourcecode(self.revision_01, "complete-cddl", "cddl")
        cddl_02 = sourcecode(self.revision_02, "complete-cddl", "cddl")
        self.assertEqual(cddl_02, cddl_01)
        self.assertEqual(cddl_fields(cddl_01), EXPECTED_FIELDS)
        self.assertEqual(cddl_fields(cddl_02), EXPECTED_FIELDS)
        self.assertIn("wire_version: 1,", cddl_02)
        self.assertNotIn("wire_version: 2", cddl_02)
        self.assertIn(
            '{"message_type":"effect-ack-capabilities","supported_versions":[1]}',
            "".join(self.revision_02.itertext()),
        )

    def test_unchanged_normative_subtrees_equal_frozen_revision_01(self) -> None:
        for anchor in UNCHANGED_NORMATIVE_ANCHORS:
            self.assertEqual(
                canonical_element(section(self.revision_02, anchor)),
                canonical_element(section(self.revision_01, anchor)),
                anchor,
            )

    def test_only_permitted_middle_and_back_deltas_exist(self) -> None:
        middle_01 = copy.deepcopy(self.revision_01.find("middle"))
        middle_02 = copy.deepcopy(self.revision_02.find("middle"))
        self.assertIsNotNone(middle_01)
        self.assertIsNotNone(middle_02)
        assert middle_01 is not None and middle_02 is not None

        vector_section_01 = section(middle_01, "test-vectors")
        vector_section_02 = section(middle_02, "test-vectors")
        vectors_01 = vector_section_01.findall("t")
        vectors_02 = vector_section_02.findall("t")
        self.assertEqual(len(vectors_01), 2)
        self.assertEqual(len(vectors_02), 2)
        corrected_index = list(vector_section_02).index(vectors_02[0])
        vector_section_02.remove(vectors_02[0])
        vector_section_02.insert(corrected_index, copy.deepcopy(vectors_01[0]))

        implementation_02 = section(middle_02, "implementation-status")
        research_02 = implementation_02.find(
            "section[@anchor='research-formalization-status']"
        )
        self.assertIsNotNone(research_02)
        assert research_02 is not None
        implementation_02.remove(research_02)
        self.assertEqual(
            canonical_element(middle_02),
            canonical_element(middle_01),
            (
                "revision -02 middle differs outside the corrected vector "
                "paragraph and non-normative research subsection"
            ),
        )

        back_01 = copy.deepcopy(self.revision_01.find("back"))
        back_02 = copy.deepcopy(self.revision_02.find("back"))
        self.assertIsNotNone(back_01)
        self.assertIsNotNone(back_02)
        assert back_01 is not None and back_02 is not None
        informative_groups = [
            group
            for group in back_02.findall("references")
            if group.find("reference[@anchor='QIKVRT-CTM-2026']") is not None
        ]
        self.assertEqual(len(informative_groups), 1)
        back_02.remove(informative_groups[0])
        revision_02_log = back_02.find("section[@anchor='change-log-02']")
        self.assertIsNotNone(revision_02_log)
        assert revision_02_log is not None
        back_02.remove(revision_02_log)
        self.assertEqual(
            canonical_element(back_02),
            canonical_element(back_01),
            (
                "revision -02 back matter differs outside the exact informative "
                "DOI reference and revision -02 change log"
            ),
        )

    def test_research_boundary_doi_and_change_log_are_exact(self) -> None:
        research = section(self.revision_02, "research-formalization-status")
        self.assertEqual(research.attrib, {"anchor": "research-formalization-status"})
        self.assertEqual(research.findtext("name"), "Research and Formalization Status")
        self.assertEqual(
            tuple(normalized("".join(item.itertext())) for item in research.findall("t")),
            tuple(normalized(item) for item in RESEARCH_BOUNDARY_PARAGRAPHS),
        )

        reference = self.revision_02.find(
            ".//reference[@anchor='QIKVRT-CTM-2026']"
        )
        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual(
            reference.attrib,
            {
                "anchor": "QIKVRT-CTM-2026",
                "target": "https://doi.org/10.5281/zenodo.21711193",
            },
        )
        front = reference.find("front")
        self.assertIsNotNone(front)
        assert front is not None
        self.assertEqual(
            front.findtext("title"),
            (
                "QIK-VRT und das Effect-Acknowledgement-Protokoll: Kanonischer "
                "Speicher zwischen Vergangenheit und Zukunft"
            ),
        )
        author = front.find("author")
        self.assertIsNotNone(author)
        assert author is not None
        self.assertEqual(
            author.attrib,
            {
                "initials": "I.",
                "surname": "Lohmann",
                "fullname": "Ingolf Lohmann",
            },
        )
        date = front.find("date")
        self.assertIsNotNone(date)
        assert date is not None
        self.assertEqual(
            date.attrib,
            {"year": "2026", "month": "July", "day": "31"},
        )
        series = reference.find("seriesInfo")
        self.assertIsNotNone(series)
        assert series is not None
        self.assertEqual(
            series.attrib,
            {"name": "DOI", "value": "10.5281/zenodo.21711193"},
        )

        changes = section(self.revision_02, "change-log-02")
        self.assertEqual(changes.attrib, {"anchor": "change-log-02"})
        self.assertEqual(changes.findtext("name"), "Changes from Revision -01")
        self.assertEqual(
            tuple(
                normalized("".join(item.itertext()))
                for item in changes.findall("./ul/li")
            ),
            tuple(normalized(item) for item in REVISION_02_CHANGES),
        )

    def test_fresh_offline_renders_are_warning_free_and_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="qikvrt-ietf-revision-02-render-"
        ) as temporary:
            scratch = Path(temporary)
            cache = scratch / "cache"
            cache.mkdir()
            rendered_txt = scratch / REVISION_02_TXT.name
            rendered_html = scratch / REVISION_02_HTML.name
            run_renderer(self.xml2rfc, rendered_txt, cache, "text")
            run_renderer(self.xml2rfc, rendered_html, cache, "html")
            self.assertEqual(
                rendered_txt.read_bytes(),
                REVISION_02_TXT.read_bytes(),
                "fresh offline TXT render differs from the committed artifact",
            )
            self.assertEqual(
                rendered_html.read_bytes(),
                REVISION_02_HTML.read_bytes(),
                "fresh offline HTML render differs from the committed artifact",
            )
            self.assertEqual(identity(rendered_txt), identity(REVISION_02_TXT))
            self.assertEqual(identity(rendered_html), identity(REVISION_02_HTML))

    def test_truth_boundaries_remain_explicit_without_completion_claims(self) -> None:
        representations = {
            "xml": normalized(" ".join(self.revision_02.itertext())),
            "txt": normalized(REVISION_02_TXT.read_text(encoding="utf-8")),
            "html": html_text(REVISION_02_HTML),
        }
        for name, text in representations.items():
            for required in TRUTH_BOUNDARY_SENTENCES:
                self.assertIn(normalized(required), text, f"{name}: {required}")
            for prohibited in PROHIBITED_POSITIVE_CLAIMS:
                self.assertIsNone(prohibited.search(text), f"{name}: {prohibited.pattern}")

    def test_nonexistent_vector_claim_is_corrected_in_every_representation(self) -> None:
        self.assertFalse(
            OLD_VECTOR_PATH.exists(),
            "the old path is no longer a nonexistence boundary",
        )
        representations = {
            "xml": normalized(" ".join(self.revision_02.itertext())),
            "txt": normalized(REVISION_02_TXT.read_text(encoding="utf-8")),
            "html": html_text(REVISION_02_HTML),
        }
        expected = normalized(CORRECTED_VECTOR_SENTENCE)
        for name, text in representations.items():
            self.assertNotIn(OLD_VECTOR_LITERAL, text, name)
            self.assertIn(expected, text, name)


def main() -> None:
    global XML2RFC

    parser = argparse.ArgumentParser(
        description=(
            "Validate the published Draft-02 local/public boundary with the "
            "exact offline xml2rfc renderer."
        ),
    )
    parser.add_argument("--xml2rfc", type=Path, required=True)
    args, unittest_args = parser.parse_known_args()
    XML2RFC = args.xml2rfc
    unittest.main(argv=[sys.argv[0], *unittest_args], verbosity=2)


if __name__ == "__main__":
    main()
