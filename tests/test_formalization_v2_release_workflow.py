#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Structural regression tests for the Formalization v2 alpha.2 release."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import qikvrt_formalization_v2_zenodo as release  # noqa: E402


RESERVE_WORKFLOW = (
    ROOT / ".github/workflows/qikvrt_formalization_v2_zenodo.yml"
)
FINALIZE_WORKFLOW = (
    ROOT / ".github/workflows/qikvrt_formalization_v2_zenodo_finalize.yml"
)
SCHEMA = (
    ROOT
    / "policy/qikvrt-formalization-v2-alpha2-release-request.schema.json"
)
MARKER = ROOT / "release/formalization-v2-alpha2-request.json"
MANIFEST = ROOT / "release/formalization-v2-alpha2-zenodo.json"
SOURCE_EVIDENCE = (
    ROOT / "release/formalization-v2-zenodo-independent-verification.json"
)
PACKAGE_SCRIPT = (
    ROOT
    / "formalization/QIKVRT_Formalization_v2.0/scripts/package_release.py"
)
ARCHIVE = (
    ROOT
    / "release/formalization-v2/QIKVRT_Formalization_v2.0-alpha.2.zip"
)
ARCHIVE_SHA = pathlib.Path(str(ARCHIVE) + ".sha256")
ZENODO_SUMS = ROOT / "release/formalization-v2/ZENODO_SHA256SUMS-alpha.2"
FILESET = (
    ROOT
    / "docs/publications/2026-07-23-effect-ack-lean-status/ZENODO_FILESET.md"
)
ALPHA2_INPUT = (
    ROOT
    / "formalization/QIKVRT_Formalization_v2.0/release_authorization/"
    "ALPHA2_INPUT.json"
)
ALPHA2_DONE = (
    ROOT
    / "formalization/QIKVRT_Formalization_v2.0/release_authorization/"
    "ALPHA2_EFFECT_ACK_DONE.json"
)
ZERO40 = "0" * 40
ZERO64 = "0" * 64


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def embedded_python(workflow: str) -> list[str]:
    values: list[str] = []
    pattern = re.compile(r"python -B - <<'PY'\n(.*?)\n\s*PY(?:\n|$)", re.S)
    for match in pattern.finditer(workflow):
        lines = match.group(1).splitlines()
        indentation = min(
            len(line) - len(line.lstrip())
            for line in lines
            if line.strip()
        )
        values.append(
            "\n".join(
                line[indentation:] if line.strip() else ""
                for line in lines
            )
        )
    return values


class FormalizationAlpha2ReleaseTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.reserve = RESERVE_WORKFLOW.read_text(encoding="utf-8")
        cls.finalize = FINALIZE_WORKFLOW.read_text(encoding="utf-8")
        cls.marker = json.loads(MARKER.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_inactive_marker_and_schema_are_closed(self) -> None:
        self.assertEqual(
            set(self.marker),
            {
                "_license",
                "$schema_ref",
                "schema",
                "schema_sha256",
                "request_id",
                "action",
                "confirm",
                "authorization_payload_sha256",
                "repository_policy",
                "candidate",
                "bindings",
                "reservation",
            },
        )
        self.assertEqual(self.marker["action"], "inactive")
        self.assertEqual(self.marker["confirm"], "NOT_AUTHORIZED")
        self.assertEqual(self.marker["authorization_payload_sha256"], ZERO64)
        self.assertEqual(self.marker["schema_sha256"], sha256(SCHEMA))
        self.assertEqual(
            self.marker["repository_policy"],
            {
                "authority_repository": "Goldkelch/qik-vrt",
                "mirror_repository": "ingolf-lohmann/qik-vrt",
                "feature_branch": "agent/effect-ack-lean-v1",
                "reserve_ref": (
                    "refs/heads/automation/"
                    "formalization-v2-alpha2-reserve-20260723"
                ),
                "finalize_ref": (
                    "refs/heads/automation/"
                    "formalization-v2-alpha2-finalize-20260723"
                ),
                "state_branch": "qikvrt/formalization-v2-state",
            },
        )
        self.assertTrue(
            all(value == ZERO40 for value in self.marker["candidate"].values())
        )
        self.assertTrue(
            all(value == ZERO64 for value in self.marker["bindings"].values())
        )
        self.assertEqual(
            self.marker["reservation"],
            {
                "state_path": (
                    "release-state/formalization-v2-alpha2/"
                    "zenodo-reservation.json"
                ),
                "evidence_sha256": ZERO64,
                "deposition_id": None,
                "doi": None,
            },
        )
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]),
            set(self.marker),
        )

    def test_manifest_is_exact_truth_bounded_alpha2_fileset(self) -> None:
        root = ROOT.resolve()
        normalized = release.validate_manifest(self.manifest, root)
        verified = release.verify_manifest_files(
            normalized, root, "offline-test-token"
        )
        self.assertEqual(len(verified), 19)
        software = normalized["software"]
        self.assertEqual(software["source_record_id"], 21501365)
        self.assertEqual(software["concept_record_id"], 21488115)
        self.assertEqual(software["metadata"]["version"], "2.0.0-alpha.2")
        title = software["metadata"]["title"].lower()
        self.assertIn("partielle", title)
        self.assertIn("quellengebundene", title)
        names = [item["name"] for item in software["files"]]
        self.assertEqual(
            names,
            [
                "QIKVRT_Formalization_v2.0-alpha.2.zip",
                "QIKVRT_Formalization_v2.0-alpha.2.zip.sha256",
                "README.md",
                "FORMALIZATION_SCOPE.md",
                "VERIFICATION_REPORT.md",
                "STATUSERKLAERUNG_WHATSAPP_DE.md",
                "EVIDENCE_BOUNDARY.md",
                "MANUSCRIPT_PROOF_MAP.md",
                "CLAIM_GRAPH.json",
                "DRAFT01_SOURCE_PROVENANCE.json",
                "DRAFT01_CLAIM_MATRIX.json",
                "CITATION.cff",
                "ZENODO_FILESET.md",
                "ZENODO_SHA256SUMS",
                "LICENSE_NOTICE.md",
                "LICENSE-CODE",
                "CC-BY-NC-ND-4.0.txt",
                "ALPHA2_INPUT.json",
                "ALPHA2_EFFECT_ACK_DONE.json",
            ],
        )
        self.assertNotIn("LEAN_CI_EVIDENCE.json", names)
        self.assertNotIn("ZENODO_PUBLICATION_EVIDENCE.json", names)
        self.assertNotIn("release-authorization-INPUT.json", names)
        for entry in software["files"]:
            path = ROOT / entry["path"]
            raw = path.read_bytes()
            self.assertEqual(len(raw), entry["size"], entry["name"])
            self.assertEqual(
                hashlib.md5(raw).hexdigest(),  # noqa: S324
                entry["md5"],
                entry["name"],
            )
            self.assertEqual(
                hashlib.sha256(raw).hexdigest(),
                entry["sha256"],
                entry["name"],
            )

    def test_zenodo_checksum_file_binds_other_eighteen_uploads(self) -> None:
        entries = self.manifest["software"]["files"]
        expected = {
            item["name"]: item["sha256"]
            for item in entries
            if item["name"] != "ZENODO_SHA256SUMS"
        }
        actual: dict[str, str] = {}
        for row in ZENODO_SUMS.read_text(encoding="ascii").splitlines():
            digest, name = row.split("  ", 1)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotIn(name, actual)
            actual[name] = digest
        self.assertEqual(actual, expected)
        self.assertNotIn("ZENODO_SHA256SUMS", actual)

    def test_package_is_reproducible_and_has_exact_provenance(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="qikvrt-alpha2-package-test-"
        ) as raw:
            temporary = pathlib.Path(raw)
            outputs = []
            sums = []
            for index in range(2):
                output = temporary / f"build-{index}.zip"
                zenodo_sums = temporary / f"build-{index}.sums"
                subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(PACKAGE_SCRIPT),
                        "--repository-root",
                        str(ROOT),
                        "--output",
                        str(output),
                        "--zenodo-checksums",
                        str(zenodo_sums),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                outputs.append(output.read_bytes())
                sums.append(zenodo_sums.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], ARCHIVE.read_bytes())
            self.assertEqual(sums[0], sums[1])
            self.assertEqual(sums[0], ZENODO_SUMS.read_bytes())
        prefix = "QIKVRT_Formalization_v2.0-alpha.2/"
        with zipfile.ZipFile(ARCHIVE) as archive:
            names = archive.namelist()
            provenance_name = prefix + "ARCHIVE_PROVENANCE.json"
            self.assertEqual(names, sorted(names))
            self.assertIn(provenance_name, names)
            provenance = json.loads(archive.read(provenance_name))
            self.assertEqual(
                provenance["schema"],
                "qikvrt_formalization_v2_alpha2_archive_provenance_v1",
            )
            self.assertEqual(provenance["version"], "2.0.0-alpha.2")
            self.assertEqual(provenance["archive_prefix"], prefix)
            entries = provenance["entries"]
            self.assertEqual(
                [item["path"] for item in entries],
                sorted(
                    name.removeprefix(prefix)
                    for name in names
                    if name != provenance_name
                ),
            )
            self.assertNotIn(
                "ARCHIVE_PROVENANCE.json",
                {item["path"] for item in entries},
            )
            for item in entries:
                raw = archive.read(prefix + item["path"])
                self.assertEqual(len(raw), item["bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
            forbidden = (
                "/release_authorization/",
                "/.lake/",
                "/__pycache__/",
                ".pyc",
                "LEAN_CI_EVIDENCE.json",
                "ZENODO_PUBLICATION_EVIDENCE.json",
                "QIKVRT_Formalization_v2.0-alpha.1.zip",
            )
            for name in names:
                self.assertFalse(
                    any(value in name for value in forbidden),
                    name,
                )

    def test_alpha2_authorization_is_self_reference_free_and_truth_bounded(
        self,
    ) -> None:
        value = json.loads(ALPHA2_INPUT.read_text(encoding="utf-8"))
        done = json.loads(ALPHA2_DONE.read_text(encoding="utf-8"))
        self.assertEqual(done["input_sha256"], sha256(ALPHA2_INPUT))
        canonical = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            done["input_canonical_sha256"],
            hashlib.sha256(canonical).hexdigest(),
        )
        self.assertFalse(
            value["natural_person"]["external_identity_verified"]
        )
        self.assertFalse(value["natural_person"]["digital_signature_present"])
        self.assertEqual(value["risk"]["classification"], "MEDIUM")
        self.assertFalse(
            done["non_effect"]["network_effect_performed_by_this_file"]
        )
        combined = ALPHA2_INPUT.read_text() + ALPHA2_DONE.read_text()
        self.assertNotRegex(combined, r"\b[0-9a-f]{40}\b")
        self.assertNotRegex(combined, r"10\.5281/zenodo\.(?!21488115\b)\d+")

    def test_source_evidence_is_published_alpha1_and_stays_historical(
        self,
    ) -> None:
        evidence = json.loads(SOURCE_EVIDENCE.read_text(encoding="utf-8"))
        normalized = release.validate_source_evidence(evidence)
        self.assertEqual(normalized["published_record_id"], 21501365)
        self.assertEqual(normalized["doi"], "10.5281/zenodo.21501365")
        self.assertEqual(normalized["concept_record_id"], 21488115)
        self.assertEqual(normalized["version"], "2.0.0-alpha.1")
        self.assertEqual(len(normalized["files"]), 14)

    def test_workflows_are_two_phase_inert_and_fail_closed(self) -> None:
        for workflow, branch in (
            (
                self.reserve,
                "automation/formalization-v2-alpha2-reserve-20260723",
            ),
            (
                self.finalize,
                "automation/formalization-v2-alpha2-finalize-20260723",
            ),
        ):
            trigger = workflow.split("permissions:", 1)[0]
            self.assertIn("      - " + branch, trigger)
            self.assertIn(
                "      - release/formalization-v2-alpha2-request.json",
                trigger,
            )
            self.assertNotIn("workflow_dispatch", workflow)
            self.assertNotIn("repository_dispatch", workflow)
            self.assertIn(
                "github.repository == 'Goldkelch/qik-vrt'", workflow
            )
            self.assertIn("cancel-in-progress: false", workflow)
            self.assertNotIn("access_token=", workflow.lower())
            self.assertIn('"force": False', workflow)
            for action in re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", workflow):
                self.assertRegex(action, r"@[0-9a-f]{40}$")
        intent = self.reserve.index(
            "Persist one-shot reservation intent before any Zenodo POST"
        )
        reserve_effect = self.reserve.index(
            "Reserve exactly one pristine new version without publishing"
        )
        self.assertLess(intent, reserve_effect)
        self.assertNotIn("/actions/publish", self.reserve)
        self.assertEqual(
            self.reserve.count("secrets.ZENODO_ACCESS_TOKEN"), 1
        )
        ci = self.finalize.index(
            "Persist prepublication Lean CI evidence"
        )
        effect = self.finalize.index(
            "Finalize only the MAC-bound reserved alpha.2 draft"
        )
        anonymous = self.finalize.index(
            "Independently verify anonymous public Zenodo metadata and bytes"
        )
        publication = self.finalize.index(
            "Persist finalization and Zenodo publication evidence"
        )
        self.assertLess(ci, effect)
        self.assertLess(effect, anonymous)
        self.assertLess(anonymous, publication)
        self.assertEqual(
            self.finalize.count("secrets.ZENODO_ACCESS_TOKEN"), 1
        )
        self.assertNotIn(
            "ZENODO_ACCESS_TOKEN",
            self.finalize[anonymous:publication],
        )
        self.assertIn("LEAN_CI_EVIDENCE.json", self.finalize[ci:effect])
        self.assertIn(
            "ZENODO_PUBLICATION_EVIDENCE.json",
            self.finalize[anonymous:],
        )

    def test_workflow_embedded_python_is_syntactically_valid(self) -> None:
        for label, workflow in (
            ("reserve", self.reserve),
            ("finalize", self.finalize),
        ):
            blocks = embedded_python(workflow)
            self.assertGreaterEqual(len(blocks), 4)
            for index, source in enumerate(blocks):
                with self.subTest(workflow=label, block=index):
                    compile(source, f"<{label}-{index}>", "exec")

    def test_fileset_text_matches_manifest_and_two_phase_evidence(self) -> None:
        text = FILESET.read_text(encoding="utf-8")
        names = [
            item["name"] for item in self.manifest["software"]["files"]
        ]
        for index, name in enumerate(names, 1):
            self.assertIn(f"{index}. `{name}`", text)
        self.assertIn("achtzehn Uploads", text)
        self.assertIn("exakt die neunzehn", text)
        self.assertIn(
            "Nicht zum vorab hashgebundenen Zenodo-Dateisatz", text
        )
        self.assertIn("LEAN_CI_EVIDENCE.json", text)
        self.assertIn("ZENODO_PUBLICATION_EVIDENCE.json", text)


if __name__ == "__main__":
    unittest.main()
