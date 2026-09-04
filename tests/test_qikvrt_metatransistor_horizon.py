from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "qikvrt_metatransistor_horizon.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_metatransistor_horizon", MODULE)
assert SPEC and SPEC.loader
horizon = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = horizon
SPEC.loader.exec_module(horizon)


class MetatransistorHorizonTests(unittest.TestCase):
    def event(self, gate: str, *, conclusion: str = "failure", run_id: int = 1):
        return horizon.normalize_event(
            {
                "repository": "Goldkelch/qik-vrt",
                "gate": gate,
                "run_id": run_id,
                "head_sha": "a" * 40,
                "head_branch": "feature/example",
                "action": "completed",
                "status": "completed",
                "conclusion": conclusion,
                "pr_number": 42,
            }
        )

    def hold_vector(self, *, authoritative: bool = False):
        result = {}
        for index, gate in enumerate(horizon.EXPECTED_GATES, start=1):
            event = self.event(gate, run_id=index)
            if authoritative:
                event["cause_authority"] = "REPOSITORY_RECEIPT"
                event["causal_fingerprint"] = f"{index:064x}"
            result[gate] = event
        return result

    def test_success_is_ready_not_pass(self) -> None:
        event = self.event(horizon.EXPECTED_GATES[0], conclusion="success")
        self.assertEqual(event["state"], "READY")
        self.assertFalse(event["claims"]["pass"])
        self.assertFalse(event["claims"]["final_pass"])
        self.assertFalse(event["claims"]["effect_ack_done"])

    def test_all_eight_holds_bind_depth_nine_cut_candidate(self) -> None:
        projection = horizon.classify_projection(
            head_sha="a" * 40,
            gates=self.hold_vector(),
            carrier={
                "pull_request_open": True,
                "branch_exists": True,
                "exact_head_current": True,
                "protected": False,
                "default_branch": False,
            },
        )
        self.assertEqual(projection["computation_depth"], 9)
        self.assertTrue(projection["cut_candidate"])
        self.assertFalse(projection["cut_eligible"])
        self.assertEqual(
            projection["disposition"], "CUT_CANDIDATE_REQUIRES_EXACT_RECEIPT"
        )
        self.assertFalse(projection["prune_plan"]["automatic"])

    def test_cut_requires_authoritative_receipts_and_exact_safe_carrier(self) -> None:
        projection = horizon.classify_projection(
            head_sha="a" * 40,
            gates=self.hold_vector(authoritative=True),
            carrier={
                "pull_request_open": True,
                "branch_exists": True,
                "exact_head_current": True,
                "protected": False,
                "default_branch": False,
            },
        )
        self.assertTrue(projection["cut_candidate"])
        self.assertTrue(projection["cut_eligible"])
        self.assertEqual(projection["disposition"], "CUT_ELIGIBLE")
        self.assertTrue(projection["prune_plan"]["executable"])

    def test_partial_hold_vector_maps_carrier_plus_hold_count(self) -> None:
        gates = self.hold_vector()
        for name in horizon.EXPECTED_GATES[3:]:
            gates[name]["state"] = "READY"
        projection = horizon.classify_projection(head_sha="a" * 40, gates=gates)
        self.assertEqual(projection["computation_depth"], 4)
        self.assertFalse(projection["cut_candidate"])

    def test_active_writer_and_successor_reset_dead_end_depth(self) -> None:
        gates = self.hold_vector()
        active = horizon.classify_projection(
            head_sha="a" * 40, gates=gates, active_writer=True
        )
        self.assertEqual(active["computation_depth"], 0)
        self.assertFalse(active["cut_candidate"])
        successor = horizon.classify_projection(
            head_sha="a" * 40, gates=gates, successor_observed=True
        )
        self.assertEqual(successor["computation_depth"], 0)
        self.assertFalse(successor["cut_candidate"])

    def test_lossless_serial_frame_round_trip(self) -> None:
        frame = horizon.build_terminal_frame(
            node_id="mirror",
            sequence=7,
            payload={"text": "manifest and derealize", "head": "a" * 40},
        )
        self.assertTrue(horizon.verify_terminal_frame(frame))
        changed = json.loads(json.dumps(frame))
        changed["payload"]["text"] = "changed"
        self.assertFalse(horizon.verify_terminal_frame(changed))

    def test_repository_surface_is_event_driven_atomic_and_visualizes_nodes(self) -> None:
        html = (ROOT / "deploy/vercel-monitor/index.html").read_text(encoding="utf-8")
        stream = (
            ROOT / "deploy/vercel-monitor/api/gate-stream.js"
        ).read_text(encoding="utf-8")
        snapshot = (
            ROOT / "deploy/vercel-monitor/api/state.js"
        ).read_text(encoding="utf-8")
        ingress = (
            ROOT / "deploy/vercel-monitor/api/gate-event.js"
        ).read_text(encoding="utf-8")
        workflow = (
            ROOT / ".github/workflows/qikvrt_horizon_event_projection.yml"
        ).read_text(encoding="utf-8")
        registry = json.loads(
            (ROOT / "deploy/vercel-monitor/NODE_REGISTRY_V1.json").read_text(
                encoding="utf-8"
            )
        )
        gate_set = json.loads(
            (ROOT / "deploy/vercel-monitor/GATE_SET_V1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("setInterval", html)
        self.assertEqual(html.count("fetch('/api/state'"), 1)
        self.assertIn("new EventSource", html)
        self.assertIn("stream_cursor", snapshot)
        self.assertIn("last-event-id", stream.lower())
        self.assertIn("xRead", stream)
        self.assertIn("BLOCK: 25000", stream)
        self.assertIn("reader.destroy()", stream)
        self.assertIn("qikvrt_metatransistor_projection_v1", ingress)
        self.assertIn("holdCount + 1", ingress)
        self.assertIn("WatchError", ingress)
        self.assertIn("client.watch(dkey, gkey)", ingress)
        self.assertIn("const replies = await client.multi()", ingress)
        self.assertIn(".xAdd(", ingress)
        self.assertIn(".set(dkey, body.event_id", ingress)
        self.assertIn("client.destroy()", ingress)
        self.assertNotIn("redis.set(dedupeKey(body.event_id)", ingress)
        self.assertIn("ref: main", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("qikvrt_metatransistor_horizon.py event", workflow)
        self.assertEqual(gate_set["metatransistor"]["max_compute_depth"], 9)
        self.assertFalse(gate_set["transport"]["polling"])
        self.assertEqual(registry["framework"], "KubiKAva")
        self.assertTrue(
            any(node["role"] == "AUTHORITY" for node in registry["nodes"])
        )
        self.assertTrue(
            any("FULL_TERMINAL" in node["surface"] for node in registry["nodes"])
        )

    def test_loopback_terminal_wrapper_exposes_only_registered_origins(self) -> None:
        wrapper = (
            ROOT / "src/qikvrt_metatransistor_terminal.py"
        ).read_text(encoding="utf-8")
        entrypoint = (
            ROOT / "deploy/universal-terminal/entrypoint.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("https://horizon-by-qik-vrt.vercel.app", wrapper)
        self.assertIn("https://goldkelch.github.io", wrapper)
        self.assertIn("Access-Control-Allow-Private-Network", wrapper)
        self.assertIn("127.0.0.1", wrapper)
        self.assertIn("qikvrt_metatransistor_terminal.py", entrypoint)
        self.assertNotIn("--host 0.0.0.0", entrypoint)

    def test_unknown_gate_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.event("NOT A GATE")


if __name__ == "__main__":
    unittest.main()
