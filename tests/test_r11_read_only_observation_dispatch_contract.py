# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Static tests for the paired one-shot R11 read-only observation contract."""

from __future__ import annotations

import hashlib
import json
import pathlib
import unittest
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "state/authorization/r11/R11_READ_ONLY_OBSERVATION_DISPATCH_V1.json"
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load() -> dict[str, Any]:
    return json.loads(
        CONTRACT_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )


class R11ReadOnlyObservationDispatchContractTests(unittest.TestCase):
    def test_top_level_shape_and_identity(self) -> None:
        value = _load()
        self.assertEqual(
            set(value),
            {
                "_license",
                "schema",
                "contract_id",
                "state",
                "authorization_payload",
                "authorization_payload_sha256",
                "effect_boundary",
                "completion_claims",
            },
        )
        self.assertEqual(
            value["schema"],
            "qikvrt_r11_read_only_observation_dispatch_contract_v1",
        )
        self.assertEqual(
            value["contract_id"],
            "qikvrt-r11-read-only-observation-dispatch-20260805-v1",
        )
        self.assertEqual(value["state"], "AUTHORIZED_FOR_ONE_TRUSTED_PROXY_RUN")

    def test_authorization_payload_digest_is_byte_current(self) -> None:
        value = _load()
        canonical = json.dumps(
            value["authorization_payload"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(),
            "0618150363cadb907a479f85da4e29e6f494d927126eb2abe6aba411b70ab89d",
        )
        self.assertEqual(
            value["authorization_payload_sha256"],
            hashlib.sha256(canonical).hexdigest(),
        )

    def test_exact_source_carrier_and_proxy_bindings(self) -> None:
        payload = _load()["authorization_payload"]
        self.assertEqual(
            payload["source_mains"],
            {
                "authority": "e8a0b521e6dbd7951b256fb0ed7f363ef465de41",
                "mirror": "ca43c6970774c5825a0cba9b640c749eaa9c16c6",
            },
        )
        self.assertEqual(
            payload["carrier"],
            {
                "repository": "Goldkelch/qik-vrt",
                "pull_request": 395,
                "branch": "recovery-execution/vrtcore-relational-h3-e1-v1",
                "head": "26a45a0af463dcd8bb1667897d1a999230375307",
                "tree": "693ae135b907ee50e9bc9d3ff70b0b1662ab8072",
                "parent": "507f4f30b694df3a415194b2c2cae41a0922b6d9",
                "must_remain_open": True,
                "must_never_merge": True,
            },
        )
        self.assertEqual(
            payload["proxy"],
            {
                "repository": "Goldkelch/qik-vrt",
                "branch": "trusted/r11-read-only-observation-proxy-v1",
                "head": "6b0fd669b880505d71c0d03cb60a85d08bf0c326",
                "workflow_path": (
                    ".github/workflows/"
                    "qikvrt_r11_read_only_observation_proxy_v1.yml"
                ),
                "workflow_git_blob_sha1": (
                    "5e42fbeecda02fc21dcdd4f7d8b3da87d907bcb9"
                ),
                "workflow_sha256": (
                    "3173972d70adea57483a419b0f000cfaf3253c49119337408171b0f785e060ad"
                ),
                "workflow_bytes": 22892,
            },
        )

    def test_one_shot_get_only_observation_and_artifact_scope(self) -> None:
        payload = _load()["authorization_payload"]
        self.assertEqual(
            payload["trigger"],
            {
                "event": "pull_request",
                "action": "opened",
                "run_attempt": 1,
                "rerun_authorized": False,
                "synchronize_authorized": False,
                "reopen_authorized": False,
                "exactly_one_run": True,
            },
        )
        self.assertEqual(
            payload["observation"],
            {
                "service": "zenodo.org",
                "api_origin": "https://zenodo.org/api",
                "authenticated_request_count": 2,
                "allowed_methods": ["GET"],
                "target_deposition_id": 16304099,
                "target_record_id": 17269164,
                "redirects_followed": False,
                "raw_response_bytes_persisted": False,
                "arbitrary_response_values_persisted": False,
            },
        )
        self.assertEqual(
            payload["artifact"],
            {
                "name_template": (
                    "vrtcore-h3-r11-draft-shape-observation-{run_id}-1"
                ),
                "artifact_count": 1,
                "entry_count": 2,
                "entries": [
                    (
                        "release/vrtcore-relational-h3-publication-2026-08-02/"
                        "zenodo-publication.json"
                    ),
                    ".qikvrt/vrtcore-h3-r11/draft-shape-observation.json",
                ],
                "retention_days": 90,
            },
        )

    def test_c2_and_historical_failures_are_exact(self) -> None:
        payload = _load()["authorization_payload"]
        self.assertEqual(
            payload["c2"],
            {
                "commit": "376e869dc3504929b8913146cb29264d3ac585f3",
                "git_blob_sha1": "d81135af4a14c5fa3d67966761f473569c7d2689",
                "bytes": 23415,
                "sha256": (
                    "3114f282d76e453ae0aa9106a0b7481c0be8566bd6b38674922eb3e5f0bc74f4"
                ),
                "must_remain_unchanged": True,
            },
        )
        self.assertEqual(
            payload["historical_failed_runs"],
            [
                {
                    "run_id": 30818549721,
                    "conclusion": "failure",
                    "artifact_count": 0,
                },
                {
                    "run_id": 30935794485,
                    "conclusion": "failure",
                    "artifact_count": 0,
                },
            ],
        )

    def test_paired_promotion_and_post_observation_boundary(self) -> None:
        payload = _load()["authorization_payload"]
        promotion = payload["promotion_contract"]
        self.assertEqual(promotion["promotion_order"], ["authority", "mirror"])
        self.assertTrue(promotion["exact_head_gates_required"])
        self.assertTrue(promotion["expected_head_promotion_required"])
        self.assertTrue(promotion["force_push_forbidden"])
        self.assertEqual(
            promotion["portable_paths"],
            [
                (
                    "state/authorization/r11/"
                    "R11_READ_ONLY_OBSERVATION_DISPATCH_V1.json"
                ),
                "tests/test_r11_read_only_observation_dispatch_contract.py",
            ],
        )
        post = payload["post_observation"]
        self.assertTrue(post["artifact_bytes_and_sha256_verification_required"])
        self.assertTrue(post["paired_receipt_only_successors_required"])
        self.assertTrue(post["reciprocal_r11_synchronization_required"])
        self.assertFalse(
            post["repository_wide_effect_ack_done_evaluation_before_receipt_pair"]
        )

    def test_effect_boundary_and_completion_claims_remain_fail_closed(self) -> None:
        value = _load()
        self.assertEqual(
            value["effect_boundary"],
            {
                "zenodo_mutation": False,
                "metadata_mutation": False,
                "upload": False,
                "publish": False,
                "new_doi": False,
                "repository_mutation_by_observer": False,
                "receipt_minting_by_observer": False,
                "ietf_mutation": False,
                "release": False,
                "deployment": False,
                "terminal_result": "OBSERVATION_RECEIPT_PERSISTED_BLOCKED",
            },
        )
        self.assertEqual(
            value["completion_claims"],
            {"pass": False, "final_pass": False, "effect_ack_done": False},
        )
        raw = CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("ZENODO_ACCESS_TOKEN", raw)
        self.assertNotIn("GITHUB_TOKEN", raw)


if __name__ == "__main__":
    unittest.main()
