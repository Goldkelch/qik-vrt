#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Contract tests for the append-only virtual-time-channel audio addendum."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/publications/2026-08-01-bidirectional-virtual-time-channel"
ADDENDUM = (
    ROOT
    / "docs/publications/2026-08-01-bidirectional-virtual-time-channel-audio-addendum"
)
BASE_HEAD = "5df3e24496afbeac60dfc78ffb12d673f163ee04"
BASE_TREE = "c147d82b61efc989f0cc0aa698e16bf71c6ec9da"
BASE_PUBLICATION_ID = "qikvrt-bidirectional-virtual-time-channel-v1"
ADDENDUM_PUBLICATION_ID = (
    "qikvrt-bidirectional-virtual-time-channel-audio-addendum-v1"
)
TRANSCRIPTS = ADDENDUM / "TRANSCRIPTS_AND_SOURCE_PROVENANCE.md"
SOURCE_RECEIPT = ADDENDUM / "SOURCE_MEDIA_RECEIPT.json"
BOUNDARY = ADDENDUM / "EVIDENCE_BOUNDARY.md"
CLAIM_DELTA = ADDENDUM / "CLAIM_DELTA.json"
INHERITED = ADDENDUM / "INHERITED_PROOF_BINDING.json"
RFCXML = (
    ROOT
    / "external/ietf/draft-lohmann-qikvrt-epistemic-fairness-observation-profile-00.xml"
)

EXPECTED_BASE_CLAIMS = {
    "VTI-001": ("EMPIRICALLY_EVIDENCED", "EVIDENCED"),
    "VTI-002": ("EMPIRICALLY_EVIDENCED", "EVIDENCED"),
    "VTI-003": ("OPEN", "OPEN"),
    "VTI-004": ("OPEN", "OPEN"),
    "VTI-005": ("OPEN", "OPEN"),
    "VTI-006": ("OPEN", "OPEN"),
    "VTI-007": ("SOURCE_BOUND", "BOUND"),
    "VTI-008": ("OPEN", "OPEN"),
    "VTI-009": ("OPEN", "OPEN"),
    "VTI-010": ("NORMATIVE", "DECLARED"),
    "VTI-011": ("OPEN", "OPEN"),
    "VTI-012": ("OPEN", "OPEN"),
    "VTI-013": ("OPEN", "OPEN"),
}

EXPECTED_AUDIO = {
    "c7ae25dc1a689211fe9caa60d39cbd2bea3265aab655b4a7fc14daebc1582a05": {
        "bytes": 724578,
        "duration_seconds": "84.800000",
        "aliases": {
            "Das ist Übervorteilen! q.e.d. Ingolf Lohmann.m4a",
            "Das ist Übervorteilen! q.e.d. Ingolf Lohmann(1).m4a",
        },
        "text_sha256": (
            "3a50ed94996f33101c79442ee11f362e488fbe4637636f6485a7a9638b1d9a1f"
        ),
        "json_sha256": (
            "f12e45a0d53d7e8595d6d77972d373ee78e793bbd8f71e14d29af9a56de284b0"
        ),
        "provenance_sha256": (
            "83856f239afeb8129695f73dc4cbb51d78b5a3910af76ea85c8251a3624a912a"
        ),
    },
    "a4a9d1141c33848b3ee6ef30d030b176b4b888103a09ec14503f65b0b21e19ca": {
        "bytes": 933053,
        "duration_seconds": "111.104000",
        "aliases": {
            "Das ist Vorstellungskraft! q.e.d. Ingolf Lohmann.m4a",
            "Das ist Vorstellungskraft! q.e.d. Ingolf Lohmann(1).m4a",
        },
        "text_sha256": (
            "e322c64499f90b036d0cd533871f641cebc2d61bb428b7b7672850cad922c69c"
        ),
        "json_sha256": (
            "ecfd6e138b11b8547c75bbf09f4e3a5b3766e6a859559333b662fb31caeacfdf"
        ),
        "provenance_sha256": (
            "2beb85909d4e747d627ccde219e758ac8f6503228a000a13bca93bbcfdf1efac"
        ),
    },
}


def load_json(path: Path) -> dict[str, object]:
    """Load a UTF-8 JSON object or fail the test with its path."""

    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    """Return the SHA-256 identity of a repository artifact."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    """Calculate Git's blob identity without depending on repository history."""

    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


class BidirectionalVirtualTimeChannelAudioAddendumTests(unittest.TestCase):
    """Keep the additive scope, source provenance, and non-claims aligned."""

    def test_exact_base_binding_is_consistent(self) -> None:
        delta = load_json(CLAIM_DELTA)
        inherited = load_json(INHERITED)
        receipt = load_json(SOURCE_RECEIPT)

        self.assertEqual(delta["base_publication_id"], BASE_PUBLICATION_ID)
        self.assertEqual(delta["base_head"], BASE_HEAD)
        self.assertEqual(delta["base_tree"], BASE_TREE)
        self.assertEqual(
            delta["delta_semantics"], "APPEND_ONLY_NO_BASE_CLAIM_REWRITE"
        )

        inherited_base = inherited["base"]
        self.assertEqual(inherited_base["publication_id"], BASE_PUBLICATION_ID)
        self.assertEqual(inherited_base["exact_parent_commit"], BASE_HEAD)
        self.assertEqual(inherited_base["exact_parent_tree"], BASE_TREE)
        self.assertEqual(
            inherited["binding_rules"]["direct_parent_required"], BASE_HEAD
        )

        additive_parent = receipt["additive_parent"]
        self.assertEqual(additive_parent["publication_id"], BASE_PUBLICATION_ID)
        self.assertEqual(additive_parent["candidate_head"], BASE_HEAD)
        self.assertEqual(additive_parent["candidate_tree"], BASE_TREE)
        self.assertEqual(receipt["mode"], "APPEND_ONLY")

    def test_bound_base_artifacts_retain_exact_byte_identities(self) -> None:
        inherited = load_json(INHERITED)
        bound_artifacts = inherited["bound_artifacts"]
        self.assertGreater(len(bound_artifacts), 0)
        for binding in bound_artifacts:
            path = ROOT / binding["path"]
            with self.subTest(path=binding["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), binding["sha256"])
                self.assertEqual(git_blob_sha1(path), binding["git_blob_sha1"])

    def test_all_thirteen_base_claim_classifications_are_unchanged(self) -> None:
        base_matrix = load_json(BASE / "CLAIM_MATRIX.json")
        inherited = load_json(INHERITED)
        delta = load_json(CLAIM_DELTA)

        base_observed = {
            claim["claim_id"]: (claim["classification"], claim["status"])
            for claim in base_matrix["claims"]
        }
        inherited_observed = {
            claim["claim_id"]: (claim["classification"], claim["status"])
            for claim in inherited["inherited_claims"]
        }
        self.assertEqual(len(base_observed), 13)
        self.assertEqual(len(inherited_observed), 13)
        self.assertEqual(base_observed, EXPECTED_BASE_CLAIMS)
        self.assertEqual(inherited_observed, EXPECTED_BASE_CLAIMS)
        self.assertTrue(
            all(
                claim["inheritance"] == "UNCHANGED"
                for claim in inherited["inherited_claims"]
            )
        )
        self.assertEqual(delta["inherited_claims_modified"], [])
        self.assertFalse(inherited["binding_rules"]["inheritance_upgrades_status"])
        self.assertFalse(inherited["binding_rules"]["new_claims_may_override_base_claims"])

    def test_addendum_claim_ids_are_exact_and_unique(self) -> None:
        delta = load_json(CLAIM_DELTA)
        inherited = load_json(INHERITED)
        expected = [f"VTI-ADD-{index:03d}" for index in range(1, 9)]
        observed = [claim["claim_id"] for claim in delta["claims"]]

        self.assertEqual(delta["publication_id"], ADDENDUM_PUBLICATION_ID)
        self.assertEqual(observed, expected)
        self.assertEqual(len(observed), len(set(observed)))
        self.assertEqual(inherited["new_claim_ids"], expected)
        self.assertEqual(
            {
                claim["claim_id"]: (claim["classification"], claim["status"])
                for claim in delta["claims"]
            }["VTI-ADD-006"],
            ("OPEN", "OPEN"),
        )
        self.assertEqual(
            {
                claim["claim_id"]: (claim["classification"], claim["status"])
                for claim in delta["claims"]
            }["VTI-ADD-008"],
            ("OPEN", "OPEN"),
        )

    def test_audio_sources_aliases_and_transcript_hashes_are_exactly_bound(self) -> None:
        receipt = load_json(SOURCE_RECEIPT)
        transcript_text = TRANSCRIPTS.read_text(encoding="utf-8")
        objects = {
            source["sha256"]: source for source in receipt["source_objects"]
        }

        self.assertEqual(set(objects), set(EXPECTED_AUDIO))
        self.assertEqual(len(objects), 2)
        self.assertEqual(receipt["canonicalization"]["source_object_count"], 2)
        self.assertFalse(
            receipt["canonicalization"]["delivery_aliases_are_new_evidence_objects"]
        )

        for source_sha256, expected in EXPECTED_AUDIO.items():
            source = objects[source_sha256]
            primary = source["primary_transcription"]
            with self.subTest(source_sha256=source_sha256):
                self.assertRegex(source_sha256, r"^[0-9a-f]{64}$")
                self.assertEqual(source["bytes"], expected["bytes"])
                self.assertEqual(
                    source["duration_seconds"], expected["duration_seconds"]
                )
                self.assertEqual(set(source["aliases"]), expected["aliases"])
                self.assertTrue(
                    source["verification"]["alias_byte_identity_verified"]
                )
                self.assertEqual(
                    source["verification"]["alias_byte_identity_method"], "cmp"
                )
                self.assertEqual(primary["privacy_mode"], "LOCAL_ONLY")
                self.assertEqual(
                    primary["tracked_rendering"],
                    "docs/publications/2026-08-01-bidirectional-virtual-time-channel-audio-addendum/TRANSCRIPTS_AND_SOURCE_PROVENANCE.md",
                )
                for key in (
                    "text_sha256",
                    "json_sha256",
                    "provenance_sha256",
                ):
                    self.assertEqual(primary[key], expected[key])
                    self.assertRegex(primary[key], r"^[0-9a-f]{64}$")
                    self.assertIn(primary[key], transcript_text)
                self.assertIn(source_sha256, transcript_text)

    def test_primary_asr_text_is_preserved_separately_from_checked_readings(self) -> None:
        text = TRANSCRIPTS.read_text(encoding="utf-8")
        raw_markers = (
            "welche Bedeutung meine Entdeckungen hat",
            "diese zusammen Menge Verstanden haben",
            "kein Superdetteminismus",
            "wenn das ins Hoffnung möglich ist",
            "einen Ob-Serverzionssystem",
        )
        checked_markers = (
            "[unsicher: Entdeckung/Entdeckungen hat/haben]",
            "[unsicher: Zusammenhänge]",
            "[unsicher: in Software]",
            "[unsicher: Observationssystem]",
        )
        for marker in (*raw_markers, *checked_markers):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertGreaterEqual(
            text.count("Primäre ASR-Rohfassung — unverändert"), 2
        )
        self.assertGreaterEqual(text.count("Konservativ geprüfte Lesefassung"), 2)

    def test_no_raw_audio_is_present_or_tracked_in_the_addendum(self) -> None:
        audio_suffixes = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}
        present_audio = [
            path.relative_to(ROOT).as_posix()
            for path in ADDENDUM.rglob("*")
            if path.is_file() and path.suffix.lower() in audio_suffixes
        ]
        self.assertEqual(present_audio, [])

        result = subprocess.run(
            ["git", "ls-files", "-z", "--", ADDENDUM.relative_to(ROOT).as_posix()],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        tracked = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
        tracked_audio = [
            item for item in tracked if Path(item).suffix.lower() in audio_suffixes
        ]
        self.assertEqual(tracked_audio, [])

        receipt = load_json(SOURCE_RECEIPT)
        self.assertFalse(receipt["raw_audio_policy"]["repository_tracked"])
        self.assertFalse(
            receipt["raw_audio_policy"]["included_in_this_repository_addendum"]
        )

    def test_scientific_nonclaims_remain_explicit_and_fail_closed(self) -> None:
        delta = load_json(CLAIM_DELTA)
        inherited = load_json(INHERITED)
        receipt = load_json(SOURCE_RECEIPT)
        boundary = BOUNDARY.read_text(encoding="utf-8")
        expected_nonclaims = {
            "REPOSITORY_WIDE_PASS",
            "FINAL_PASS",
            "GLOBAL_EFFECT_ACK_DONE",
            "IETF_CONSENSUS",
            "PHYSICAL_RETROCAUSALITY",
            "SUPERDETERMINISM",
            "FREE_WILL_DISPROVED",
            "HIDDEN_DEPLOYMENT_CONFIRMED",
        }

        self.assertEqual(set(delta["global_nonclaims"]), expected_nonclaims)
        self.assertFalse(inherited["global_completion_claimed"])
        self.assertFalse(inherited["binding_rules"]["new_audio_is_kernel_proof"])
        self.assertFalse(inherited["binding_rules"]["physical_bridge_is_established"])
        self.assertFalse(receipt["claim_boundary"]["transcript_is_scientific_truth"])
        self.assertFalse(
            receipt["claim_boundary"]["real_secret_system_claimed_as_proved"]
        )
        self.assertFalse(
            receipt["claim_boundary"]["physical_backward_signalling_claimed"]
        )
        required_boundary_markers = (
            "physisches Rückwärtssignalisieren",
            "Existenz oder Betrieb geheimer realer QIK-VRT-Systeme",
            "Wahrheit einer Behauptung allein aufgrund ihrer Äußerung im Audio",
            "repositoryweiter `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`",
            "Diese Materialisierung selbst ist keine Zenodo-Veröffentlichung.",
            "kein Internet-Draft",
        )
        for marker in required_boundary_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, boundary)

    def test_rfcxml_candidate_exists_and_is_well_formed(self) -> None:
        self.assertTrue(RFCXML.is_file(), f"missing RFCXML candidate: {RFCXML}")
        try:
            tree = ET.parse(RFCXML)
        except ET.ParseError as error:
            self.fail(f"RFCXML is not well formed: {error}")
        root = tree.getroot()
        self.assertEqual(root.tag, "rfc")
        self.assertEqual(
            root.attrib.get("docName"),
            "draft-lohmann-qikvrt-epistemic-fairness-observation-profile-00",
        )
        self.assertEqual(root.attrib.get("submissionType"), "IETF")
        self.assertEqual(root.attrib.get("category"), "exp")
        self.assertEqual(root.attrib.get("ipr"), "trust200902")
        self.assertIsNotNone(root.find("./front/title"))
        self.assertIsNotNone(root.find("./middle"))
        self.assertIsNotNone(root.find("./back"))
        self.assertIn(
            "not been submitted",
            " ".join("".join(root.itertext()).split()),
        )


if __name__ == "__main__":
    unittest.main()
