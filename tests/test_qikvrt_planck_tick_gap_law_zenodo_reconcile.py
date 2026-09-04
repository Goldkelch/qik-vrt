# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_planck_tick_gap_law_zenodo_reconcile.yml"


class PlanckTickGapLawZenodoReconciliationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_main_binding_precedes_external_readback(self) -> None:
        self.assertIn("ref: ${{ github.sha }}", self.text)
        self.assertIn('remote_main="$(git ls-remote origin refs/heads/main', self.text)
        self.assertIn('test "$remote_main" = "$GITHUB_SHA"', self.text)
        self.assertLess(
            self.text.index("Bind exact current Main head and tree"),
            self.text.index("GET public Zenodo record and verify downloaded bytes"),
        )

    def test_reconciliation_is_get_only_and_creates_no_second_record(self) -> None:
        self.assertIn('method="GET"', self.text)
        self.assertNotIn("ZENODO_ACCESS_TOKEN", self.text)
        self.assertNotIn("deposit/depositions", self.text)
        self.assertNotIn('method="POST"', self.text)
        self.assertNotIn('method="PUT"', self.text)
        self.assertNotIn('method="PATCH"', self.text)
        self.assertNotIn('method="DELETE"', self.text)
        self.assertIn('"second_zenodo_record_created": False', self.text)

    def test_public_and_current_main_bytes_are_sha256_checked(self) -> None:
        self.assertIn("ZENODO_SHA256_MISMATCH", self.text)
        self.assertIn("CURRENT_MAIN_BUILD_SHA256_MISMATCH", self.text)
        self.assertIn("PUBLICATION_HEAD_NOT_ANCESTOR_OF_CURRENT_MAIN", self.text)
        for name in (
            "QIKVRT_Planck_Tick_Gap_Law_2026-09-03.pdf",
            "QIKVRT_Planck_Tick_Gap_Law_2026-09-03.tex",
            "README.md",
            "planck_tick_gap_law_v1.json",
            "ZENODO_METADATA.json",
            "SHA256SUMS.txt",
        ):
            self.assertIn(name, self.text)

    def test_receipt_preserves_claim_boundaries(self) -> None:
        self.assertIn('"EMPIRICAL_CORRESPONDENCE": False', self.text)
        self.assertIn('"INDEPENDENT_REPRODUCTION": False', self.text)
        self.assertIn('"PASS": False', self.text)
        self.assertIn('"FINAL_PASS": False', self.text)
        self.assertIn('"EFFECT_ACK_DONE": False', self.text)

    def test_workflow_is_read_only_and_retains_receipt_as_artifact(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.text)
        self.assertIn("persist-credentials: false", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("RECEIPT_BRANCH", self.text)
        self.assertNotIn("git push", self.text)
        self.assertNotIn("git commit", self.text)
        self.assertIn("actions/upload-artifact@", self.text)
        self.assertIn("input for a separate repository persistence PR", self.text)

    def test_main_push_and_manual_dispatch_are_supported(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("branches: [main]", self.text)
        self.assertIn(
            "planck-tick-gap-law-zenodo-current-main-${{ github.run_id }}",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
