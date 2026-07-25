# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "tools/verify_wirkungsquadrat_release.py"
SPEC = importlib.util.spec_from_file_location("verify_wirkungsquadrat_release", VERIFIER_PATH)
assert SPEC and SPEC.loader
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class WirkungsquadratVerificationTests(unittest.TestCase):
    def test_canonical_release_passes_static_verifier(self) -> None:
        result = VERIFIER.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["proof_escape_count"], 0)
        self.assertEqual(result["doi_state"], "DOI_PENDING_PUBLICATION")
        self.assertFalse(result["repository_canonicalization_byte_identical_claim"])
        self.assertEqual(result["dimensional_matrix_determinant"], -2)

    def test_dimensional_solution_is_unique(self) -> None:
        a, b, d, determinant = VERIFIER.dimensional_solution()
        self.assertEqual((str(a), str(b), str(d)), ("-3/2", "1/2", "1/2"))
        self.assertEqual(determinant, -2)

    def test_forbidden_lean_escape_is_blocked(self) -> None:
        canonical = VERIFIER.LEAN.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp_dir:
            mutated = pathlib.Path(temp_dir) / "WirkungsquadratKernel.lean"
            mutated.write_text(canonical + "\nexample : True := by sorry\n", encoding="utf-8")
            with mock.patch.object(VERIFIER, "LEAN", mutated):
                with self.assertRaisesRegex(SystemExit, "forbidden Lean escape"):
                    VERIFIER.verify()

    def test_premature_doi_promotion_is_blocked(self) -> None:
        metadata = json.loads(VERIFIER.METADATA.read_text(encoding="utf-8"))
        metadata["doi"] = "10.5281/zenodo.NOT_PUBLIC"
        with tempfile.TemporaryDirectory() as temp_dir:
            mutated = pathlib.Path(temp_dir) / "zenodo-metadata.json"
            mutated.write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(VERIFIER, "METADATA", mutated):
                with self.assertRaisesRegex(SystemExit, "DOI sentinel"):
                    VERIFIER.verify()

    def test_silent_byte_identity_claim_is_blocked(self) -> None:
        canonical = VERIFIER.README.read_text(encoding="utf-8")
        mutated_text = canonical.replace("nicht als byteidentisch", "als byteidentisch")
        with tempfile.TemporaryDirectory() as temp_dir:
            mutated = pathlib.Path(temp_dir) / "README.md"
            mutated.write_text(mutated_text, encoding="utf-8")
            with mock.patch.object(VERIFIER, "README", mutated):
                with self.assertRaisesRegex(SystemExit, "canonicalization boundary"):
                    VERIFIER.verify()


if __name__ == "__main__":
    unittest.main()
