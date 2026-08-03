#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Tests for the deterministic retrospective proof-corpus v3 freeze."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools/qikvrt_retrospective_proof_corpus_zenodo_candidate.py"
PUBLICATION = ROOT / "release/zenodo-corpus-proof-2026-07-28"
INDEX = PUBLICATION / "canonical-union/retrospective-proof-corpus/RETROSPECTIVE_PROOF_CORPUS_INDEX.json"
MATRIX = PUBLICATION / "CORPUS_CLAIM_MATRIX.json"
RETURN = PUBLICATION / "PREPUBLICATION_RETURN_RECEIPT.json"
METADATA = PUBLICATION / "ZENODO_METADATA.json"
BUNDLE = PUBLICATION / "MACHINE_PROOF_BUNDLE.json"
RETURN_EVENT = PUBLICATION / "PREPUBLICATION_RETURN_EVENT.json"
CORPUS_RECEIPT = (
    PUBLICATION
    / "canonical-union/retrospective-proof-corpus/RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json"
)

EXPECTED_RETURN_SHA256 = "46c57378a6708df379768f943a99905cde3da4c4a11220f9a177e9bc968d3968"
EXPECTED_METADATA_SHA256 = "4bb6abea1f226f3950337ee3585abd1ba5d52f731a93f25fabfc2722f5b170de"
EXPECTED_MACHINE_SHA256 = "cfe9ae60e3da81a6427c96399bd70299c74f12999dc4371809b879f5a5630be1"
EXPECTED_MATRIX_SHA256 = "4750f37565df8abc78a28bdf85f2499ea4f35435ca29ef1e43979d9d2532cd67"
EXPECTED_UPLOAD_CONTRACT_SHA256 = (
    "3965b4167094ff47de60fc32023ac74ea1598148ab381885be8da3db4c427609"
)
EXPECTED_UPLOAD_BYTES = 221_808_115
EXPECTED_INDEX_SHA256 = "9ce73608a7aaa17bc825f163475adb820ed208b188fd3017eafdacf2b2dd253c"
EXPECTED_CORPUS_RECEIPT_SHA256 = (
    "b85546e5359bdcd1afb0f3b535a257be68ffee19a283790d14db2847fa186a68"
)


def load_json(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tool():
    spec = importlib.util.spec_from_file_location("corpus_candidate", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load corpus candidate tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RetrospectiveProofCorpusCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tool = load_tool()
        cls.check = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                str(TOOL_PATH),
                "--check",
                "--return-event",
                str(RETURN_EVENT),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if cls.check.returncode != 0:
            raise AssertionError(cls.check.stdout + cls.check.stderr)
        cls.matrix = load_json(MATRIX)
        cls.receipt = load_json(RETURN)
        cls.metadata = load_json(METADATA)
        cls.bundle = load_json(BUNDLE)
        cls.return_event = load_json(RETURN_EVENT)

    def test_check_mode_reproduces_frozen_bytes(self) -> None:
        self.assertIn("PASS verified retrospective proof corpus v3", self.check.stdout)
        self.assertIn("OLD_AUTHORIZATION_ORACLE=MISMATCH_NEW_AUTHORIZATION_REQUIRED", self.check.stdout)
        self.assertIn(
            "NEW_AUTHORIZATION_TEMPLATE=AUTHORIZE_EXACT_UPLOAD ",
            self.check.stdout,
        )
        self.assertEqual(sha256(MATRIX), EXPECTED_MATRIX_SHA256)
        self.assertEqual(sha256(RETURN), EXPECTED_RETURN_SHA256)
        self.assertEqual(sha256(BUNDLE), EXPECTED_MACHINE_SHA256)
        self.assertEqual(
            self.tool.canonical_json_sha256(self.metadata),
            EXPECTED_METADATA_SHA256,
        )
        self.assertIn(
            "UPLOAD_CONTRACT_SHA256=" + EXPECTED_UPLOAD_CONTRACT_SHA256,
            self.check.stdout,
        )

    def test_upload_set_has_one_natural_primary_and_exact_disjoint_roles(self) -> None:
        candidates = self.bundle["candidate"]["files"]
        artifacts = self.bundle["artifacts"]
        self.assertEqual(len(candidates), 26)
        self.assertEqual(len(artifacts), 38)
        self.assertEqual(self.bundle["candidate"]["primary_document_path"], INDEX.relative_to(ROOT).as_posix())
        primary = [item for item in candidates if item["role"] == "PRIMARY"]
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary[0]["path"], INDEX.relative_to(ROOT).as_posix())
        candidate_paths = {item["path"] for item in candidates}
        artifact_paths = {item["path"] for item in artifacts}
        self.assertTrue(candidate_paths.isdisjoint(artifact_paths))
        upload_paths = self.tool.upload_paths(self.bundle)
        self.assertEqual(len(upload_paths), 65)
        self.assertEqual(len(upload_paths), len(set(upload_paths)))
        self.assertEqual(len(self.tool.upload_names(self.bundle, self.matrix)), 65)

    def test_strict_json_rejects_duplicates_nonfinite_and_lone_surrogates(self) -> None:
        invalid = (
            (b'{"outer":{"key":1,"key":2}}', "duplicate JSON key"),
            (b'{"value":NaN}', "non-finite JSON number"),
            (b'{"value":Infinity}', "non-finite JSON number"),
            (b'{"value":-Infinity}', "non-finite JSON number"),
            (b'{"value":"\\ud800"}', "lone Unicode surrogate"),
            (b'{"\\udfff":"value"}', "lone Unicode surrogate"),
            (b'\xff', "invalid strict fixture"),
        )
        for raw, message in invalid:
            with self.subTest(raw=raw), self.assertRaisesRegex(
                self.tool.CorpusCandidateError,
                message,
            ):
                self.tool.parse_json_bytes(raw, "invalid strict fixture")

        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "non-finite JSON number",
        ):
            self.tool.json_bytes({"value": float("nan")})
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "lone Unicode surrogate",
        ):
            self.tool.canonical_json_sha256({"value": "\ud800"})
        valid = self.tool.parse_json_bytes(
            '{"value":"𝄞"}'.encode("utf-8"),
            "valid astral fixture",
        )
        self.assertEqual(valid, {"value": "𝄞"})

    def test_paths_subject_ids_and_upload_names_are_canonical(self) -> None:
        for raw in (
            "/absolute",
            "../outside",
            "a/../outside",
            "a/./file",
            "a//file",
            "a\\file",
            "a\x1bfile",
        ):
            with self.subTest(raw=raw), self.assertRaises(
                self.tool.CorpusCandidateError
            ):
                self.tool.normalize_repo_relative(raw, "negative path")
        self.assertEqual(
            self.tool.normalize_repo_relative("safe/path.json"),
            "safe/path.json",
        )
        for value in ("SUBJECT-../escape", "SUBJECT-ABC", "SUBJECT-1234/5678"):
            with self.subTest(value=value), self.assertRaisesRegex(
                self.tool.CorpusCandidateError,
                "must match SUBJECT",
            ):
                self.tool.validate_subject_id(value, "negative subject")
        self.assertEqual(
            self.tool.validate_subject_id(
                "SUBJECT-2581811b342e505d",
                "positive subject",
            ),
            "SUBJECT-2581811b342e505d",
        )
        for name in ("../file.json", "folder/file.json", "file\\name", "line\nname"):
            with self.subTest(name=name), self.assertRaises(
                self.tool.CorpusCandidateError
            ):
                self.tool.safe_upload_name(name)

    def test_stable_reader_blocks_parent_symlink_hardlink_and_read_race(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "root"
            outside = pathlib.Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "data.bin").write_bytes(b"outside")
            (root / "alias").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(
                self.tool.CorpusCandidateError,
                "symlink or unsafe|open repository file safely",
            ):
                self.tool.read_stable_regular(root, "alias/data.bin")

            os.link(outside / "data.bin", root / "hardlink.bin")
            with self.assertRaisesRegex(
                self.tool.CorpusCandidateError,
                "single-link",
            ):
                self.tool.read_stable_regular(root, "hardlink.bin")

            victim = root / "racing.bin"
            victim.write_bytes(b"a")
            original_read = self.tool.os.read
            changed = False

            def racing_read(descriptor: int, count: int) -> bytes:
                nonlocal changed
                chunk = original_read(descriptor, count)
                if not changed:
                    changed = True
                    victim.write_bytes(b"changed during read")
                return chunk

            with mock.patch.object(self.tool.os, "read", side_effect=racing_read):
                with self.assertRaisesRegex(
                    self.tool.CorpusCandidateError,
                    "changed while being read",
                ):
                    self.tool.read_stable_regular(root, "racing.bin")

    def test_atomic_output_blocks_aliases_is_failure_safe_and_commits_bundle_last(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "root"
            output = root / "output"
            outside = pathlib.Path(directory) / "outside"
            output.mkdir(parents=True)
            outside.mkdir()
            (root / "alias").symlink_to(output, target_is_directory=True)
            with self.assertRaises(self.tool.CorpusCandidateError):
                with self.tool.output_directory_lock(root, "alias"):
                    pass

            external = outside / "external.json"
            external.write_bytes(b"external")
            os.link(external, output / "hardlink.json")
            with self.tool.output_directory_lock(root, "output") as descriptor:
                with self.assertRaisesRegex(
                    self.tool.CorpusCandidateError,
                    "single-link regular",
                ):
                    self.tool.atomic_write_set(
                        descriptor,
                        {
                            "hardlink.json": b"replacement",
                            "bundle.json": b"bundle",
                        },
                        commit_marker="bundle.json",
                    )
            self.assertEqual(external.read_bytes(), b"external")

            (output / "first.json").write_bytes(b"old-first")
            (output / "bundle.json").write_bytes(b"old-bundle")
            original_write = self.tool.os.write

            def interrupted_write(descriptor: int, raw: bytes) -> int:
                original_write(descriptor, bytes(raw[:1]))
                raise OSError("injected interruption")

            with self.tool.output_directory_lock(root, "output") as descriptor:
                with mock.patch.object(
                    self.tool.os,
                    "write",
                    side_effect=interrupted_write,
                ):
                    with self.assertRaisesRegex(
                        self.tool.CorpusCandidateError,
                        "atomic candidate output failed",
                    ):
                        self.tool.atomic_write_set(
                            descriptor,
                            {
                                "first.json": b"new-first",
                                "bundle.json": b"new-bundle",
                            },
                            commit_marker="bundle.json",
                        )
            self.assertEqual((output / "first.json").read_bytes(), b"old-first")
            self.assertEqual((output / "bundle.json").read_bytes(), b"old-bundle")
            self.assertFalse(
                any(path.name.endswith(".qikvrt.tmp") for path in output.iterdir())
            )

            (output / "first.json").write_bytes(b"old-first")
            (output / "bundle.json").write_bytes(b"old-bundle")
            original_write_all = self.tool._write_all
            changed_target = False

            def mutate_target_after_staging(descriptor: int, raw: bytes) -> None:
                nonlocal changed_target
                original_write_all(descriptor, raw)
                if not changed_target:
                    changed_target = True
                    (output / "first.json").write_bytes(
                        b"concurrent in-place target change"
                    )

            with self.tool.output_directory_lock(root, "output") as descriptor:
                with mock.patch.object(
                    self.tool,
                    "_write_all",
                    side_effect=mutate_target_after_staging,
                ):
                    with self.assertRaisesRegex(
                        self.tool.CorpusCandidateError,
                        "changed during atomic materialization",
                    ):
                        self.tool.atomic_write_set(
                            descriptor,
                            {
                                "first.json": b"new-first",
                                "bundle.json": b"new-bundle",
                            },
                            commit_marker="bundle.json",
                        )
            self.assertEqual(
                (output / "first.json").read_bytes(),
                b"concurrent in-place target change",
            )
            self.assertEqual((output / "bundle.json").read_bytes(), b"old-bundle")

            (output / "first.json").write_bytes(b"old-first")
            replacements: list[str] = []
            original_replace = self.tool.os.replace

            def recording_replace(source: str, target: str, **kwargs: object) -> None:
                replacements.append(target)
                original_replace(source, target, **kwargs)

            with self.tool.output_directory_lock(root, "output") as descriptor:
                with mock.patch.object(
                    self.tool.os,
                    "replace",
                    side_effect=recording_replace,
                ):
                    self.tool.atomic_write_set(
                        descriptor,
                        {
                            "first.json": b"new-first",
                            "bundle.json": b"new-bundle",
                        },
                        commit_marker="bundle.json",
                    )
            self.assertEqual(replacements[-1], "bundle.json")
            self.assertEqual((output / "first.json").read_bytes(), b"new-first")
            self.assertEqual((output / "bundle.json").read_bytes(), b"new-bundle")

    def test_upload_byte_total_is_computed_from_exact_paths(self) -> None:
        paths = self.tool.upload_paths(self.bundle)
        observed = sum(
            (ROOT / pathlib.PurePosixPath(path)).stat().st_size for path in paths
        )
        self.assertEqual(observed, EXPECTED_UPLOAD_BYTES)

    def test_source_inventory_and_corpus_claim_boundaries_remain_separate(self) -> None:
        index = load_json(INDEX)
        self.assertEqual(index["subject_count"], 19)
        self.assertEqual(index["claim_count"], 70_439)
        self.assertEqual(index["explicit_open_claim_count"], 1_262)
        self.assertEqual(self.matrix["source_inventory_counts"]["claims"], 70_439)
        inventory = self.matrix["source_inventory_recomputation"]
        self.assertEqual(inventory["matrix_claim_count_recomputed"], 70_439)
        self.assertEqual(
            inventory["matrix_epistemic_counts_recomputed"],
            {
                "EMPIRICALLY_EVIDENCED": 1_251,
                "FORMAL_PROVED": 160,
                "INTERPRETATIVE": 254,
                "NORMATIVE": 2_554,
                "OPEN": 1_262,
                "SOURCE_BOUND": 64_958,
            },
        )
        self.assertEqual(
            inventory["matrix_subjects_with_formal_proved_labels_recomputed"],
            7,
        )
        self.assertFalse(
            inventory["historical_corpus_receipt_verification_claims_adopted"]
        )
        self.assertEqual(self.matrix["claim_count"], len(self.matrix["claims"]))
        self.assertEqual(self.matrix["claim_count"], 17)
        self.assertNotIn(
            "FORMAL_PROVED",
            {claim["classification"] for claim in self.matrix["claims"]},
        )
        open_claims = [
            claim for claim in self.matrix["claims"]
            if claim["classification"] == "OPEN"
        ]
        self.assertEqual(len(open_claims), 2)
        self.assertTrue(all(claim["status"] == "OPEN" for claim in open_claims))

    def test_exact_historical_index_discrepancy_is_visible_and_only_one(self) -> None:
        discrepancies = self.matrix["source_inventory_recomputation"][
            "historical_index_discrepancies"
        ]
        self.assertEqual(len(discrepancies), 1)
        discrepancy = discrepancies[0]
        self.assertEqual(discrepancy["subject_id"], "SUBJECT-2581811b342e505d")
        self.assertEqual(discrepancy["historical_index_claim_count"], 39)
        self.assertEqual(
            discrepancy["historical_index_classification_summary"],
            {
                "EMPIRICALLY_EVIDENCED": 0,
                "FORMAL_PROVED": 0,
                "INTERPRETATIVE": 0,
                "NORMATIVE": 0,
                "OPEN": 0,
                "SOURCE_BOUND": 8,
            },
        )
        self.assertEqual(
            discrepancy["matrix_epistemic_counts_recomputed"],
            {
                "EMPIRICALLY_EVIDENCED": 20,
                "FORMAL_PROVED": 0,
                "INTERPRETATIVE": 0,
                "NORMATIVE": 0,
                "OPEN": 0,
                "SOURCE_BOUND": 19,
            },
        )
        self.assertEqual(discrepancy["claims_absent_from_historical_index_summary"], 31)
        self.assertEqual(discrepancy["disposition"], "DISCLOSED_NOT_REWRITTEN")

    def test_nested_formal_labels_are_explicitly_outside_bundle_validation(self) -> None:
        scope = self.matrix["nested_claim_validation_scope"]
        self.assertEqual(scope["nested_formal_proved_labels_observed"], 160)
        self.assertEqual(scope["nested_subjects_with_formal_proved_labels_observed"], 7)
        self.assertFalse(scope["nested_claims_recursively_revalidated_by_this_bundle"])
        self.assertFalse(
            scope["nested_formal_proved_proof_refs_kernel_verified_by_this_bundle"]
        )
        self.assertEqual(scope["corpus_level_formal_proved_claims"], 0)
        claim = next(
            item
            for item in self.matrix["claims"]
            if item["claim_id"] == "CORPUS-NESTED-VALIDATION-SCOPE-001"
        )
        self.assertIn("160 observed FORMAL_PROVED labels across 7 subjects", claim["statement"])
        self.assertIn("zero corpus-level FORMAL_PROVED claims", claim["boundary"])
        self.assertIn("160 FORMAL_PROVED labels across 7 subjects", self.metadata["description"])

    def test_exact_correction_archives_are_returned_candidates(self) -> None:
        return_package = load_json(
            PUBLICATION / "canonical-union/versioned-corrected-candidates/OWNER_RETURN_PACKAGE.json"
        )
        acceptance = load_json(
            PUBLICATION / "canonical-union/versioned-corrected-candidates/OWNER_ACCEPTANCE_RECEIPT.json"
        )
        candidate_by_path = {
            item["path"]: item for item in self.bundle["candidate"]["files"]
        }
        accepted = {
            item["candidate_archive_path"]: item["candidate_sha256"]
            for item in acceptance["decisions"]
        }
        self.assertEqual(len(return_package["candidates"]), 6)
        for item in return_package["candidates"]:
            archive = item["candidate_archive"]
            self.assertIn(archive["path"], candidate_by_path)
            self.assertEqual(candidate_by_path[archive["path"]]["sha256"], archive["sha256"])
            self.assertEqual(accepted[archive["path"]], archive["sha256"])

    def test_historical_index_and_receipt_bytes_remain_unchanged(self) -> None:
        self.assertEqual(sha256(INDEX), EXPECTED_INDEX_SHA256)
        self.assertEqual(sha256(CORPUS_RECEIPT), EXPECTED_CORPUS_RECEIPT_SHA256)

    def test_matrix_inventory_rejects_duplicate_ids_invalid_class_and_subject(self) -> None:
        index = load_json(INDEX)
        subject = index["subjects"][0]
        matrix = load_json(ROOT / subject["claim_matrix"]["path"])

        duplicate = copy.deepcopy(matrix)
        duplicate["claims"][1]["claim_id"] = duplicate["claims"][0]["claim_id"]
        with self.assertRaisesRegex(self.tool.CorpusCandidateError, "not unique"):
            self.tool.inventory_matrix_claims(
                subject["subject_id"], duplicate, "negative duplicate matrix"
            )

        invalid_class = copy.deepcopy(matrix)
        invalid_class["claims"][0]["epistemic_class"] = "UNREVIEWED"
        with self.assertRaisesRegex(self.tool.CorpusCandidateError, "unsupported"):
            self.tool.inventory_matrix_claims(
                subject["subject_id"], invalid_class, "negative class matrix"
            )

        wrong_subject = copy.deepcopy(matrix)
        wrong_subject["subject_id"] = "SUBJECT-not-the-bound-subject"
        with self.assertRaisesRegex(self.tool.CorpusCandidateError, "subject binding"):
            self.tool.inventory_matrix_claims(
                subject["subject_id"], wrong_subject, "negative subject matrix"
            )

    def test_any_unrecognized_or_changed_index_discrepancy_blocks(self) -> None:
        actual = {classification: 0 for classification in self.tool.STATUS}
        actual["SOURCE_BOUND"] = 1
        historical = dict(actual)
        historical["SOURCE_BOUND"] = 0
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "unrecognized index/matrix classification discrepancy",
        ):
            self.tool.classify_index_matrix_discrepancy(
                "SUBJECT-not-the-pinned-exception",
                1,
                historical,
                1,
                actual,
            )

        changed_pin = dict(self.tool.KNOWN_INDEX_DISCREPANCY_SUMMARY)
        changed_pin["SOURCE_BOUND"] = 9
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "no longer matches its exact pin",
        ):
            self.tool.classify_index_matrix_discrepancy(
                self.tool.KNOWN_INDEX_DISCREPANCY_SUBJECT,
                39,
                changed_pin,
                39,
                self.tool.KNOWN_MATRIX_RECOMPUTED_SUMMARY,
            )

    def test_upload_contract_binds_all_65_ordered_path_name_role_mappings(self) -> None:
        entries = self.tool.validate_upload_contract(self.matrix, self.bundle)
        self.assertEqual(len(entries), 65)
        self.assertEqual(
            self.matrix["upload_contract"]["ordered_entries_canonical_sha256"],
            EXPECTED_UPLOAD_CONTRACT_SHA256,
        )
        self.assertEqual(
            [item["path"] for item in entries],
            self.tool.upload_paths(self.bundle),
        )
        self.assertEqual(len({item["name"] for item in entries}), 65)
        matrix_artifact = next(
            item
            for item in self.bundle["artifacts"]
            if item["path"] == MATRIX.relative_to(ROOT).as_posix()
        )
        self.assertEqual(matrix_artifact["sha256"], EXPECTED_MATRIX_SHA256)

        tampered_name = copy.deepcopy(self.matrix)
        tampered_name["upload_contract"]["ordered_entries"][30]["name"] += ".tampered"
        with self.assertRaisesRegex(self.tool.CorpusCandidateError, "digest differs"):
            self.tool.validate_upload_contract(tampered_name, self.bundle)

        tampered_path = copy.deepcopy(self.matrix)
        tampered_path["upload_contract"]["ordered_entries"][30]["path"] += ".tampered"
        tampered_path["upload_contract"]["ordered_entries_canonical_sha256"] = (
            self.tool.canonical_json_sha256(
                tampered_path["upload_contract"]["ordered_entries"]
            )
        )
        with self.assertRaisesRegex(self.tool.CorpusCandidateError, "ordered paths differ"):
            self.tool.validate_upload_contract(tampered_path, self.bundle)

    def test_prepublication_receipt_is_candidate_exact_without_rewriting_history(self) -> None:
        candidates = self.bundle["candidate"]["files"]
        returned = self.receipt["candidate_files"]
        self.assertFalse(self.receipt["content_changed"])
        self.assertEqual(self.receipt["original_files"], [])
        self.assertEqual(self.receipt["changed_claim_ids"], [])
        self.assertEqual(self.receipt["change_reasons"], [])
        self.assertIsNone(self.receipt["change_notice_path"])
        self.assertEqual(
            returned,
            [
                {key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")}
                for item in candidates
            ],
        )
        self.assertTrue(self.receipt["return"]["candidate_returned_to_owner"])
        self.assertFalse(self.receipt["return"]["visible_change_notice_returned"])
        self.assertIn(
            "not independent external evidence",
            self.receipt["return"]["return_channel"],
        )
        self.assertEqual(
            self.receipt["return"]["returned_at"],
            self.return_event["returned_at"],
        )
        self.assertFalse(self.return_event["independent_external_proof"])

    def test_missing_or_wrong_return_event_blocks_before_final_hashes(self) -> None:
        blocked = subprocess.run(
            [sys.executable, "-B", str(TOOL_PATH), "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("final hashes are not authorizable", blocked.stderr)

        index, _owner_return, candidates, _inventory = self.tool.index_and_candidates()
        self.assertEqual(index["subject_count"], 19)
        tampered = dict(self.return_event)
        tampered["candidate_set_canonical_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "does not exactly bind",
        ):
            self.tool.validate_return_event(tampered, candidates)

        invalid_time = dict(self.return_event)
        invalid_time["returned_at"] = "2026-02-30T25:61:61Z"
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "real UTC calendar timestamp",
        ):
            self.tool.validate_return_event(invalid_time, candidates)

        offset_time = dict(self.return_event)
        offset_time["returned_at"] = "2026-08-03T09:44:46+00:00"
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "exact UTC",
        ):
            self.tool.validate_return_event(offset_time, candidates)

    def test_owner_acceptance_claims_require_exact_principal_scope_and_binding(self) -> None:
        acceptance = load_json(
            PUBLICATION
            / "canonical-union/versioned-corrected-candidates/OWNER_ACCEPTANCE_RECEIPT.json"
        )
        self.tool.validate_owner_acceptance_boundary(acceptance)
        mutations = []
        wrong_principal = copy.deepcopy(acceptance)
        wrong_principal["accepted_by"]["github_login"] = "someone-else"
        mutations.append(wrong_principal)
        wrong_receipt = copy.deepcopy(acceptance)
        wrong_receipt["receipt_id"] += "-tampered"
        mutations.append(wrong_receipt)
        wrong_scope = copy.deepcopy(acceptance)
        wrong_scope["scope_separation_verified"] = False
        mutations.append(wrong_scope)
        missing_non_authorization = copy.deepcopy(acceptance)
        missing_non_authorization["non_authorizations"].remove(
            "Zenodo upload, publication or record mutation"
        )
        mutations.append(missing_non_authorization)
        wrong_completion = copy.deepcopy(acceptance)
        wrong_completion["completion_claims"]["zenodo_mutation_authorized"] = True
        mutations.append(wrong_completion)
        wrong_binding = copy.deepcopy(acceptance)
        wrong_binding["candidate_binding"]["owner_return_package_sha256"] = "0" * 64
        mutations.append(wrong_binding)
        for index, mutated in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(
                self.tool.CorpusCandidateError
            ):
                self.tool.validate_owner_acceptance_boundary(mutated)

    def test_v2_machine_proof_validator_accepts_exact_set(self) -> None:
        result = self.tool.verify_machine_bundle(self.bundle)
        self.assertEqual(result["publication_id"], self.tool.PUBLICATION_ID)
        self.assertEqual(result["sha256"], EXPECTED_MACHINE_SHA256)
        self.assertEqual(result["claim_count"], 17)
        self.assertEqual(result["candidate_file_count"], 26)
        self.assertEqual(result["artifact_count"], 38)
        self.assertTrue(result["machine_proof_complete"])
        self.assertTrue(result["zenodo_upload_authorized"])

        first_path = self.bundle["candidate"]["files"][0]["path"]
        observed = self.tool.identity(ROOT / first_path)
        drifted = dict(observed)
        drifted["sha256"] = "0" * 64
        with mock.patch.object(self.tool, "identity", return_value=drifted):
            with self.assertRaisesRegex(
                self.tool.CorpusCandidateError,
                "identity changed after pinned validation",
            ):
                self.tool.verify_upload_identity_snapshot(self.bundle, result)

        with mock.patch.object(self.tool, "VALIDATOR_SHA256", "0" * 64):
            with self.assertRaisesRegex(
                self.tool.CorpusCandidateError,
                "validator source binding differs",
            ):
                self.tool.verify_machine_bundle(self.bundle)

        tampered_result = copy.deepcopy(result)
        tampered_result["machine_proof_complete"] = False
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "result differs",
        ):
            self.tool.validate_validator_result(
                self.bundle,
                BUNDLE.read_bytes(),
                tampered_result,
            )
        with self.assertRaisesRegex(
            self.tool.CorpusCandidateError,
            "inexact result shape",
        ):
            self.tool.validate_validator_result(
                self.bundle,
                BUNDLE.read_bytes(),
                {},
            )

    def test_old_owner_statement_fails_closed_for_rebuilt_bytes(self) -> None:
        blocked = subprocess.run(
            [
                sys.executable,
                "-B",
                str(TOOL_PATH),
                "--check",
                "--return-event",
                str(RETURN_EVENT),
                "--require-old-authorization-match",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn(
            "BLOCK rebuilt candidate differs from the exact old owner authorization",
            blocked.stderr,
        )
        self.assertNotEqual(sha256(RETURN), self.tool.OLD_AUTHORIZED_RETURN_SHA256)
        self.assertNotEqual(
            self.tool.canonical_json_sha256(self.metadata),
            self.tool.OLD_AUTHORIZED_METADATA_SHA256,
        )
        self.assertNotEqual(sha256(BUNDLE), self.tool.OLD_AUTHORIZED_MACHINE_PROOF_SHA256)


if __name__ == "__main__":
    unittest.main()
