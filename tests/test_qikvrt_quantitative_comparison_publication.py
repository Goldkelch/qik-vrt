# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/publications/2026-08-29-qikvrt-quantitative-comparison"
ARTICLE = BUNDLE / "QIKVRT_QUANTITATIVER_VERGLEICHSARTIKEL_DE_2026-08-29.md"
MATRIX = BUNDLE / "CLAIM_MATRIX.json"
OVERVIEW = ROOT / "docs/publications/index.json"
AUDIO_SHA256 = "9cfcea675874a12035dee982ffea487c6666ea2569a86080a3ba9afc1c346532"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class QuantitativeComparisonPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.article_bytes = ARTICLE.read_bytes()
        cls.article = cls.article_bytes.decode("utf-8")
        cls.matrix = read_json(MATRIX)
        cls.overview = read_json(OVERVIEW)

    def test_article_digest_and_claim_ids_are_exact(self):
        digest = hashlib.sha256(self.article_bytes).hexdigest()
        self.assertEqual(self.matrix["article"]["sha256"], digest)
        claim_ids = [claim["id"] for claim in self.matrix["claims"]]
        self.assertEqual(
            claim_ids,
            [f"QCOMP-{index:03d}" for index in range(1, len(claim_ids) + 1)],
        )

    def test_audio_revision_is_bound_without_verbatim_claim(self):
        readme = (BUNDLE / "README.md").read_text(encoding="utf-8")
        self.assertIn(AUDIO_SHA256, readme)
        self.assertIn("not a\n`VERBATIM_VERIFIED` artifact", readme)
        self.assertIn("Veröffentlichungskandidat 1.1", self.article)

    def test_quantitative_boundaries_are_explicit(self):
        for required in (
            "F(N,W) = N² × W + 72 Bit",
            "S_Filter = 1 / (1 − r)",
            "S_Gesamt = 1 / ((1 − p) + p / s)",
            "BASELINE_NOT_YET_MEASURED",
            "nicht Milliarden vollständige Receipts/s",
            "OWNER_ASSERTED_REALITY_CORRESPONDENCE",
            "INDEPENDENT_EMPIRICAL_CONFIRMATION",
        ):
            self.assertIn(required, self.article)

    def test_release_claims_remain_false(self):
        release = self.matrix["release_claims"]
        self.assertTrue(release)
        self.assertTrue(all(value is False for value in release.values()))

    def test_overview_selects_same_revision_and_audio(self):
        entries = {
            entry["id"]: entry for entry in self.overview["publication_bundles"]
        }
        entry = entries["2026-08-29-qikvrt-quantitative-comparison"]
        self.assertEqual(entry["version"], "1.1")
        self.assertEqual(entry["audio_instruction_sha256"], AUDIO_SHA256)
        self.assertEqual(entry["state"], "repository_candidate_quantitative_baseline_open")


if __name__ == "__main__":
    unittest.main()
