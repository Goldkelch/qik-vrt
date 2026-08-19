from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_effect_ack_live", ROOT / "tools/qikvrt_effect_ack_live.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

AUTHORITY_HEAD = "836a068d42b30f4df496caf4d712dbe8da45c043"
AUTHORITY_TREE = "f2f97a535842eb9558e29c3e60db3260941d8c56"
CANDIDATE_HEAD = "97bab72e69173ed3f4ff6cc01e75e264fad96b2e"
CANDIDATE_TREE = "3864ef3ea0fc1d414e89223926c663143b497c47"


def node(repository: str, head: str, tree: str):
    return {"repository": repository, "head": head, "tree": tree}


def snapshot(
    observation_id: str,
    predecessor_id: str | None,
    *,
    effect_state: str = "EFFECT_ACK_CONTINUE",
    closed_verified: list[str] | None = None,
    reasons: list[str] | None = None,
):
    requirements = ["REQ-STACKED-REVIEW", "REQ-HISTORICAL-INVENTORY", "REQ-OPEN-BACKLOG"]
    return {
        "authority": node("Goldkelch/qik-vrt", AUTHORITY_HEAD, AUTHORITY_TREE),
        "mirror": None,
        "candidate": node("Goldkelch/qik-vrt", CANDIDATE_HEAD, CANDIDATE_TREE),
        "effect_state": effect_state,
        "causal": {
            "transaction_id": "PR698-LIVE",
            "observation_id": observation_id,
            "predecessor_id": predecessor_id,
        },
        "mandatory_gates": {
            "QIKVRT CI": "success",
            "QIKVRT repository evidence materialization": "success",
        },
        "evidence_refs": [f"observation:{observation_id}"],
        "reason_codes": reasons or [],
        "next_possible_step": "obtain independent review disposition",
        "observed_at": "2026-08-19T00:00:00Z",
        "closure": {
            "requirements": requirements,
            "closed_verified": closed_verified or [],
        },
    }


class EffectAckLiveTests(unittest.TestCase):
    def test_encode_decode_round_trip_preserves_complementary_remainder(self):
        source = snapshot("OBS-1", None, closed_verified=["REQ-STACKED-REVIEW"])
        frame = MODULE.encode_frame(source, 7)
        self.assertEqual(
            frame["closure"]["active_remainder"],
            ["REQ-HISTORICAL-INVENTORY", "REQ-OPEN-BACKLOG"],
        )
        self.assertEqual(MODULE.decode_frame(frame), source)

    def test_tampered_remainder_is_rejected(self):
        frame = MODULE.encode_frame(snapshot("OBS-1", None), 1)
        frame["closure"]["active_remainder"] = []
        with self.assertRaises(MODULE.ProtocolError):
            MODULE.decode_frame(frame)

    def test_sequence_is_not_causal_or_snapshot_authority(self):
        source = snapshot("OBS-1", None)
        first = MODULE.encode_frame(source, 1)
        second = MODULE.encode_frame(source, 999)
        self.assertEqual(first["causal"], second["causal"])
        self.assertEqual(MODULE.decode_frame(first), MODULE.decode_frame(second))
        self.assertNotEqual(MODULE.canonical_bytes(first), MODULE.canonical_bytes(second))

    def test_completion_candidate_with_remainder_is_rejected(self):
        with self.assertRaises(MODULE.ProtocolError):
            MODULE.encode_frame(
                snapshot("OBS-1", None, effect_state="COMPLETION_CANDIDATE"),
                1,
            )

    def test_stale_predecessor_is_rejected(self):
        store = MODULE.LiveStore()
        store.accept(MODULE.encode_frame(snapshot("OBS-1", None), 1))
        with self.assertRaises(MODULE.CausalConflict):
            store.accept(MODULE.encode_frame(snapshot("OBS-2", "STALE"), 2))

    def test_loopback_rest_round_trip_carries_the_rest_back(self):
        server = MODULE.make_server(port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = MODULE.EffectAckClient(
            f"http://127.0.0.1:{server.server_address[1]}"
        )
        try:
            first = MODULE.encode_frame(
                snapshot("OBS-1", None, closed_verified=["REQ-STACKED-REVIEW"]),
                100,
            )
            first_receipt = client.post_observation(first)
            self.assertTrue(first_receipt["transport_ack"])
            self.assertFalse(first_receipt["completion_inferred"])
            self.assertEqual(first_receipt["effect_state"], "EFFECT_ACK_CONTINUE")
            self.assertEqual(
                first_receipt["active_remainder"],
                ["REQ-HISTORICAL-INVENTORY", "REQ-OPEN-BACKLOG"],
            )
            self.assertEqual(client.get_snapshot("PR698-LIVE"), first)

            second = MODULE.encode_frame(
                snapshot(
                    "OBS-2",
                    "OBS-1",
                    closed_verified=[
                        "REQ-STACKED-REVIEW",
                        "REQ-HISTORICAL-INVENTORY",
                    ],
                ),
                3,
            )
            client.post_observation(second)
            delta = client.get_delta("PR698-LIVE", "OBS-1")
            self.assertTrue(delta["causal_predecessor_valid"])
            self.assertIn("closure", delta["changed_fields"])
            self.assertNotIn("sequence", delta["changed_fields"])
            self.assertEqual(delta["active_remainder"], ["REQ-OPEN-BACKLOG"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_transport_acceptance_of_block_does_not_imply_completion(self):
        store = MODULE.LiveStore()
        frame = MODULE.encode_frame(
            snapshot(
                "OBS-BLOCK",
                None,
                effect_state="BLOCK",
                reasons=["PR698_EXACT_HEAD_REVIEW_REQUIRED"],
            ),
            1,
        )
        receipt = store.accept(frame)
        self.assertTrue(receipt["transport_ack"])
        self.assertFalse(receipt["completion_inferred"])
        self.assertEqual(receipt["effect_state"], "BLOCK")

    def test_manifest_schema_and_openapi_are_bound(self):
        manifest = json.loads(
            (ROOT / "state/autonomy/EFFECT_ACK_LIVE_REST_ROUNDTRIP_V1.json").read_text(
                encoding="utf-8"
            )
        )
        schema = json.loads(
            (ROOT / "schemas/qikvrt_effect_ack_live_v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        openapi = (ROOT / "api/qikvrt_effect_ack_live.openapi.yaml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(manifest["source_binding"]["head"], CANDIDATE_HEAD)
        self.assertEqual(manifest["source_binding"]["tree"], CANDIDATE_TREE)
        self.assertEqual(schema["properties"]["protocol_version"]["const"], MODULE.PROTOCOL_VERSION)
        self.assertEqual(
            set(schema["properties"]["effect_state"]["enum"]), MODULE.EFFECT_STATES
        )
        self.assertIn("openapi: 3.0.3", openapi)
        self.assertIn("/effect-ack/v1/observations:", openapi)
        self.assertIn("/effect-ack/v1/snapshots/{transaction_id}/delta:", openapi)
        self.assertIn("../schemas/qikvrt_effect_ack_live_v1.schema.json", openapi)


if __name__ == "__main__":
    unittest.main()
