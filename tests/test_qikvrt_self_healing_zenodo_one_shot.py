# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest
from unittest import mock

import yaml

from tools import qikvrt_self_healing_zenodo_one_shot as one_shot

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_self_healing_zenodo_publish_once.yml"


class SelfHealingZenodoOneShotTests(unittest.TestCase):
    def test_exact_identity_constants_are_frozen(self) -> None:
        self.assertEqual(
            one_shot.PUBLICATION_ID,
            "qikvrt-self-healing-repository-collective-intelligence-v1",
        )
        self.assertEqual(
            one_shot.AUTHORIZATION_ID,
            "qikvrt-self-healing-repository-collective-intelligence-v1-4fa477b9",
        )
        self.assertEqual(one_shot.CONFIRMATION, "PUBLISH_TO_PRODUCTION_ZENODO")
        self.assertEqual(one_shot.REPOSITORY, "Goldkelch/qik-vrt")

    def test_current_authorization_and_candidate_hashes_validate(self) -> None:
        authorization = one_shot.validate_authorization(ROOT)
        self.assertTrue(authorization["authorization"]["authorized"])
        self.assertFalse(
            authorization["completion_claims"]["zenodo_publication_complete"]
        )
        one_shot.validate_candidate_hashes(ROOT)

    def test_missing_v2_manifest_is_the_first_pre_effect_blocker(self) -> None:
        self.assertFalse((ROOT / one_shot.MANIFEST_PATH).exists())
        with self.assertRaisesRegex(
            one_shot.BoundaryError,
            "^PUBLICATION_MANIFEST_NOT_MATERIALIZED$",
        ):
            one_shot.preflight(ROOT)

    def test_wrong_dispatch_identity_blocks_before_generic_publish(self) -> None:
        args = type(
            "Args",
            (),
            {
                "publication_id": "other",
                "authorization_id": one_shot.AUTHORIZATION_ID,
                "confirm": one_shot.CONFIRMATION,
            },
        )()
        with mock.patch.dict(
            "os.environ",
            {
                "GITHUB_REPOSITORY": one_shot.REPOSITORY,
                "GITHUB_REF": "refs/heads/main",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                one_shot.BoundaryError,
                "^DISPATCH_PUBLICATION_ID_MISMATCH$",
            ):
                one_shot.require_execution_inputs(args)

    def test_workflow_is_manual_main_only_and_publication_bound(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        document = yaml.safe_load(text)
        event = document.get("on", document.get(True))
        self.assertEqual(set(event), {"workflow_dispatch"})
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        self.assertNotIn("schedule:", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn(one_shot.PUBLICATION_ID, text)
        self.assertIn(one_shot.AUTHORIZATION_ID, text)
        self.assertIn(one_shot.CONFIRMATION, text)
        self.assertIn("environment: production-zenodo", text)
        self.assertIn("ZENODO_ACCESS_TOKEN: ${{ secrets.ZENODO_ACCESS_TOKEN }}", text)
        self.assertNotIn("workflow_run:", text)
        self.assertNotIn("repository_dispatch:", text)

    def test_wrapper_delegates_transport_only_to_hardened_publisher(self) -> None:
        source = (ROOT / "tools/qikvrt_self_healing_zenodo_one_shot.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("publisher.load_manifest", source)
        self.assertIn("publisher.publish", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("zenodo.org/api/deposit", source)


if __name__ == "__main__":
    unittest.main()
