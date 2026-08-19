import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_pr_head_continuation.yml"
ABI = ROOT / "state" / "autonomy" / "CAUSAL_D0_ABI_V1.json"


class AutonomousPrHeadContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.abi = json.loads(ABI.read_text(encoding="utf-8"))

    def test_is_event_driven_with_five_minute_lost_event_watchdog(self):
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("pull_request_target:", self.text)
        self.assertIn("workflow_run:", self.text)
        self.assertIn('cron: "*/5 * * * *"', self.text)
        self.assertNotIn('cron: "7,22,37,52 * * * *"', self.text)
        self.assertIn("Productive reobservation is normally interrupt/event driven", self.text)

    def test_relevant_repository_edges_are_interrupt_sources(self):
        for workflow_name in (
            "QIKVRT repository evidence materialization",
            "QIKVRT adaptive stacked successor integrity materialization",
            "QIKVRT CI",
            "QIKVRT Collective Proposal Review",
            "QIK-VRT global claim completion",
            "QIKVRT requested review executor",
            "QIKVRT code-owner review observer",
            "QIKVRT workflow executor watchdog",
        ):
            self.assertIn(workflow_name, self.text)
        self.assertIn("types: [completed]", self.text)

    def test_m68000_four_state_abi_is_exact(self):
        self.assertEqual(self.abi["architecture_reference"], "M68000")
        self.assertEqual(self.abi["endianness"], "big")
        self.assertEqual(self.abi["register"], "D0")
        expected = {
            "NOOP": (0, "70004E75", ["MOVEQ #0,D0", "RTS"]),
            "HOLD": (1, "70014E75", ["MOVEQ #1,D0", "RTS"]),
            "REOBSERVE": (2, "70024E75", ["MOVEQ #2,D0", "RTS"]),
            "REQUEST_AUTHORITY": (3, "70034E75", ["MOVEQ #3,D0", "RTS"]),
        }
        for state, (d0, bytes_hex, instructions) in expected.items():
            entry = self.abi["states"][state]
            self.assertEqual(entry["d0"], d0)
            self.assertEqual(entry["bytes_hex"], bytes_hex)
            self.assertEqual(entry["instructions"], instructions)

    def test_effect_gate_preserves_transport_effect_separation(self):
        gate = self.abi["productive_effect_gate"]
        self.assertEqual(gate["required_d0"], 0)
        self.assertEqual(gate["required_effect_ack"], "DONE")
        self.assertEqual(gate["expression"], "D0 == 0 && EFFECT_ACK == DONE")
        self.assertIn("TRANSPORT_ACK != EFFECT_ACK", self.abi["invariants"])
        self.assertIn("productive_effect:false", self.text)
        self.assertIn('effect_ack:"NOT_REQUIRED"', self.text)

    def test_authority_is_minimal_and_does_not_merge_or_review(self):
        self.assertIn("actions: write", self.text)
        self.assertIn("contents: read", self.text)
        self.assertIn("pull-requests: read", self.text)
        self.assertNotIn("pull-requests: write", self.text)
        self.assertNotIn("/merges", self.text)
        self.assertNotIn("/reviews", self.text)

    def test_discovery_and_productive_edge_are_bounded(self):
        self.assertIn("per_page=30", self.text)
        self.assertIn("break", self.text)
        self.assertIn("zero_job_action_required", self.text)
        self.assertIn("useful_terminal", self.text)
        self.assertIn("active=0", self.text)
        self.assertIn('test "$live_ref" = "$selected_head"', self.text)
        self.assertIn('test "$live_ref" = "$HEAD_SHA"', self.text)

    def test_classifier_emits_noop_hold_and_reobserve_without_fabricating_authority(self):
        self.assertIn("d0=0", self.text)
        self.assertIn("state=NOOP", self.text)
        self.assertIn("d0=1", self.text)
        self.assertIn("state=HOLD", self.text)
        self.assertIn("d0=2", self.text)
        self.assertIn("state=REOBSERVE", self.text)
        self.assertIn("REQUEST_AUTHORITY/D0=3", self.text)
        self.assertIn("is not fabricated by this stall classifier", self.text)

    def test_only_characteristic_zero_job_action_required_state_is_resumed(self):
        self.assertIn('"$conclusion" = action_required', self.text)
        self.assertIn(".total_count", self.text)
        self.assertIn('"$zero_job_action_required" -gt 0', self.text)
        self.assertIn('"$useful_terminal" -eq 0', self.text)
        self.assertIn('if [ "$d0" -eq 2 ]', self.text)

    def test_named_exact_head_gate_surface_is_restored(self):
        self.assertIn("qikvrt_ci.yml", self.text)
        self.assertIn("qikvrt_collective_review.yml", self.text)
        self.assertIn("qikvrt_global_completion.yml", self.text)
        self.assertIn('-f ref="$HEAD_REF"', self.text)

    def test_continuation_is_exact_head_bound_and_review_authority_stays_separate(self):
        self.assertIn('event_type:"qikvrt_autonomous_exact_head_verify"', self.text)
        self.assertIn("head_sha:$head", self.text)
        self.assertIn("base_sha:$base", self.text)
        self.assertIn("causal_state:\"REOBSERVE\"", self.text)
        self.assertIn("qikvrt_requested_review_executor.yml/dispatches", self.text)
        self.assertIn("REQUEST_AUTHORITY/D0=3", self.text)


if __name__ == "__main__":
    unittest.main()
