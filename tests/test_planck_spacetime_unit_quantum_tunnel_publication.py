# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/publications/2026-08-29-planck-spacetime-unit-quantum-tunnel"
ARTICLE = BUNDLE / "QIKVRT_RAUMZEIT_PLANCK_EINHEIT_QUANTENTUNNEL_DE_2026-08-29.md"
MATRIX = BUNDLE / "CLAIM_MATRIX.json"
OVERVIEW = ROOT / "docs/publications/index.json"
AUDIO_SHA256 = "2c9512a1ce79c9ea75f669b4e68e748076dcabfad8164d639a424578786b61dd"


class PlanckSpacetimeUnitPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.article_bytes = ARTICLE.read_bytes()
        cls.article = cls.article_bytes.decode("utf-8")
        cls.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        cls.overview = json.loads(OVERVIEW.read_text(encoding="utf-8"))

    def test_article_digest_and_claim_ids_are_exact(self):
        self.assertEqual(
            self.matrix["article"]["sha256"],
            hashlib.sha256(self.article_bytes).hexdigest(),
        )
        claim_ids = [claim["id"] for claim in self.matrix["claims"]]
        self.assertEqual(
            claim_ids,
            [f"PSU-{index:03d}" for index in range(1, len(claim_ids) + 1)],
        )

    def test_audio_is_bound_without_a_verbatim_claim(self):
        readme = (BUNDLE / "README.md").read_text(encoding="utf-8")
        self.assertIn(AUDIO_SHA256, readme)
        self.assertIn("not a `VERBATIM_VERIFIED` artifact", readme)
        self.assertIn("repository-gebundener Veröffentlichungskandidat 0.2", self.article)

    def test_required_physics_boundaries_are_explicit(self):
        for required in (
            "Determinante ihrer Dimensionsmatrix beträgt `−2`",
            "X⁰ = cΔt/ℓ_P",
            "SI → PLANCK → SI = IDENTITÄT",
            "QIK-VRT PLANCK-BRÜCKE",
            "PHYSICALLY_CONNECTABLE = true",
            "NEW_PHYSICAL_PREDICTION = NOT_YET_DEFINED",
            "nicht dieselbe globale `U(1)`-Dualität",
            "physische Tunnelverbindung",
        ):
            self.assertIn(required, self.article)

    def test_release_claims_remain_false(self):
        release = self.matrix["release_claims"]
        self.assertTrue(release)
        self.assertTrue(all(value is False for value in release.values()))

    def test_overview_selects_same_candidate(self):
        entries = {
            entry["id"]: entry for entry in self.overview["publication_bundles"]
        }
        entry = entries["2026-08-29-planck-spacetime-unit-quantum-tunnel"]
        self.assertEqual(
            entry["state"],
            "repository_candidate_open_dynamics_prepublication_hold",
        )
        self.assertEqual(entry["audio_instruction_sha256"], AUDIO_SHA256)


if __name__ == "__main__":
    unittest.main()
