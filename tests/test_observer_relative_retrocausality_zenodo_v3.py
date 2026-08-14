# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed tests for the observer-relative retrocausality v3 package."""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import qikvrt_zenodo_machine_proof as machine_proof
from tools import qikvrt_zenodo_publish as publish


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release/observer-relative-retrocausality-current-synthesis-zenodo-v3"
ASSEMBLER_PATH = RELEASE / "assemble_successor_package.py"
FINALIZER_PATH = RELEASE / "finalize_authorized_controls.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assembler = load_module("qikvrt_orr_v3_assembler", ASSEMBLER_PATH)
finalizer = load_module("qikvrt_orr_v3_finalizer", FINALIZER_PATH)


class ObserverRelativeRetrocausalityZenodoV3Tests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def raw_sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def load_json(path: Path) -> dict:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise AssertionError("expected JSON object: " + str(path))
        return value

    def test_exact_owner_text_audio_and_git_attribute_boundaries(self) -> None:
        text_path = ROOT / assembler.TEXT_PATH
        audio_path = ROOT / assembler.AUDIO_PATH
        text = text_path.read_bytes()
        audio = audio_path.read_bytes()
        self.assertEqual(len(text), 364)
        self.assertEqual(hashlib.sha256(text).hexdigest(), assembler.TEXT_SHA256)
        self.assertEqual(assembler._git_blob(text), assembler.TEXT_BLOB)
        self.assertEqual(len(audio), 344328)
        self.assertEqual(hashlib.sha256(audio).hexdigest(), assembler.AUDIO_SHA256)
        self.assertEqual(assembler._git_blob(audio), assembler.AUDIO_BLOB)
        decoded = text.decode("utf-8")
        self.assertEqual(decoded.count("\n"), 29)
        self.assertTrue(decoded.endswith("\n"))
        self.assertEqual(
            {
                index
                for index, line in enumerate(decoded.splitlines(), start=1)
                if line.endswith(" ")
            },
            {3, 4, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 21, 22, 23, 24, 26},
        )
        for relative in (assembler.TEXT_PATH, assembler.AUDIO_PATH):
            observed = subprocess.check_output(
                ["git", "check-attr", "text", "--", relative],
                cwd=ROOT,
                text=True,
            ).strip()
            self.assertTrue(observed.endswith(": unset"), observed)

    def test_generated_v3_proof_partition_and_boundaries(self) -> None:
        completed = subprocess.run(
            ["python3", "-B", str(ASSEMBLER_PATH), "--check"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("candidate_files=17 upload_files=23", completed.stdout)
        freeze = self.load_json(RELEASE / "FROZEN_UPLOAD_CANDIDATE.json")
        draft = self.load_json(RELEASE / "PUBLISH_REQUEST_DRAFT.json")
        bundle = self.load_json(RELEASE / "MACHINE_PROOF_BUNDLE.json")
        matrix = self.load_json(RELEASE / "CLAIM_MATRIX_V2.json")
        bindings = self.load_json(RELEASE / "SOURCE_EVIDENCE_BINDINGS.json")
        boundary = self.load_json(RELEASE / "BOUNDARY_TEST_REPORT.json")
        self.assertEqual(freeze["file_count"], 17)
        self.assertEqual(len(bundle["candidate"]["files"]), 17)
        self.assertEqual(len(draft["exact_upload_files"]), 23)
        self.assertEqual(len(draft["exact_upload_paths"]), 23)
        self.assertEqual(len(set(draft["exact_upload_paths"])), 23)
        self.assertEqual(
            len({item["name"] for item in draft["exact_upload_files"]}), 23
        )
        self.assertEqual(matrix["claim_count"], 12)
        self.assertEqual(bindings["binding_count"], 12)
        pair = boundary["owner_pair"]
        for field in (
            "text_is_audio_transcript",
            "asr_performed",
            "human_acoustic_verbatim_review",
            "verbatim_verified",
            "semantic_equivalence_asserted",
            "filename_semantics_inferred",
        ):
            self.assertIs(pair[field], False)
        receipt = machine_proof.validate_bundle(
            ROOT,
            RELEASE / "MACHINE_PROOF_BUNDLE.json",
            upload_paths=draft["exact_upload_paths"],
        )
        self.assertEqual(receipt["claim_count"], 12)

    def test_embedded_freigabe_is_never_action_time_authorization(self) -> None:
        state = finalizer.release_state()
        source_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        action = {
            "schema": finalizer.INPUT_SCHEMA,
            "authorization_id": "qikvrt-orr-v3-test-authorization",
            "nonce": "a" * 64,
            "source_head": source_head,
            "principal": finalizer.PRINCIPAL,
            "authorized_at": dt.datetime.now(dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "exact_statement": "Freigabe!",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authorization.json"
            path.write_text(json.dumps(action), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "exact statement differs"):
                finalizer.load_action(path, state)

    def test_finalizer_builds_v2_schema_controls_for_exact_23_files(self) -> None:
        state = finalizer.release_state()
        source_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        draft = self.load_json(RELEASE / "OWNER_ZENODO_AUTHORIZATION_DRAFT.json")
        action = {
            "authorization_id": draft["authorization_id"],
            "nonce": "b" * 64,
            "source_head": source_head,
            "authorized_at": dt.datetime.now(dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "exact_statement": draft["canonical_statement"],
        }
        authorization_raw, manifest_raw = finalizer.build_controls(action, state)
        authorization = json.loads(authorization_raw)
        manifest = json.loads(manifest_raw)
        self.assertEqual(authorization["schema"], publish.OWNER_AUTHORIZATION_SCHEMA)
        self.assertEqual(manifest["schema"], publish.SCHEMA_V2)
        self.assertEqual(len(authorization["uploads"]), 23)
        self.assertEqual(len(manifest["files"]), 23)
        self.assertEqual(manifest["source_head"], source_head)

    def test_v2_publication_controls_remain_byte_unchanged(self) -> None:
        expected = {
            ".github/workflows/qikvrt_observer_relative_retrocausality_zenodo_publish.yml": "31cb058fa0ea298b950cbee7ee5b30f7972b9b7389f6e5bef48f15ac44c9031a",
            "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/OWNER_ZENODO_AUTHORIZATION.json": "62c3faa1b4c0877e29c813357969d7fd1d9bfc49f3c98f6e9c6e761435fcd0ba",
            "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/publish-request.json": "beb740b7dd4475114b6c4a8a34fa071ba623dc1c4391ebc01e59aacb6ad887bd",
            "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/MACHINE_PROOF_BUNDLE.json": "e18a535c51b5dd09bd0618962401e10645f7c3c00f5ffef25c7435c7ce1f3210",
        }
        for relative, digest in expected.items():
            self.assertEqual(self.raw_sha256(ROOT / relative), digest, relative)
        manifest = self.load_json(
            ROOT
            / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/publish-request.json"
        )
        self.assertEqual(len(manifest["files"]), 21)

    def test_final_control_pair_is_absent_or_complete(self) -> None:
        authorization = RELEASE / "OWNER_ZENODO_AUTHORIZATION.json"
        manifest = RELEASE / "publish-request.json"
        self.assertEqual(authorization.exists(), manifest.exists())
        if manifest.exists():
            normalized = publish.load_manifest(manifest, ROOT)
            self.assertEqual(normalized["owner_authorization"]["publication_id"], assembler.PUBLICATION_ID)
            self.assertEqual(len(normalized["files"]), 23)


if __name__ == "__main__":
    unittest.main()
