# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest

from tools.qikvrt_terminal_realtime import (
    DEFAULT_HEARTBEAT_INTERVAL_MS,
    MAX_HEARTBEAT_INTERVAL_MS,
    MAX_STATE_AGE_MS,
    MIN_HEARTBEAT_INTERVAL_MS,
    RealtimeTerminalBlock,
    choose_interval_ms,
    make_envelope,
    render_modalities,
    validate_envelope,
)


class RealtimeTerminalTests(unittest.TestCase):
    def state(self):
        return {
            "aggregate": {
                "classification": "NONTERMINAL_APPLICABLE_GATE",
                "first_blocker": "CI_RUNNING",
                "next_actions": ["REOBSERVE"],
            }
        }

    def test_timing_contract_keeps_margin_under_five_seconds(self):
        self.assertLess(MIN_HEARTBEAT_INTERVAL_MS, DEFAULT_HEARTBEAT_INTERVAL_MS)
        self.assertLess(DEFAULT_HEARTBEAT_INTERVAL_MS, MAX_HEARTBEAT_INTERVAL_MS + 1)
        self.assertLess(MAX_HEARTBEAT_INTERVAL_MS, MAX_STATE_AGE_MS)
        self.assertEqual(MIN_HEARTBEAT_INTERVAL_MS, 100)
        self.assertEqual(MAX_STATE_AGE_MS, 5000)

    def test_fast_resources_scale_well_below_five_seconds(self):
        self.assertEqual(
            choose_interval_ms(
                transport_rtt_ms=2,
                local_load_fraction=0.10,
                send_queue_depth=0,
            ),
            100,
        )
        self.assertEqual(
            choose_interval_ms(
                transport_rtt_ms=15,
                local_load_fraction=0.20,
                send_queue_depth=0,
            ),
            200,
        )

    def test_backpressure_slows_but_never_crosses_freshness_ceiling(self):
        interval = choose_interval_ms(
            transport_rtt_ms=2,
            local_load_fraction=0.95,
            send_queue_depth=20,
        )
        self.assertEqual(interval, 3500)
        self.assertLess(interval, MAX_STATE_AGE_MS)

    def test_peer_requested_interval_is_bounded(self):
        self.assertEqual(
            choose_interval_ms(
                transport_rtt_ms=1,
                local_load_fraction=0.10,
                send_queue_depth=0,
                peer_requested_interval_ms=250,
            ),
            250,
        )
        self.assertEqual(
            choose_interval_ms(
                transport_rtt_ms=1,
                local_load_fraction=0.10,
                send_queue_depth=0,
                peer_requested_interval_ms=99999,
            ),
            MAX_HEARTBEAT_INTERVAL_MS,
        )

    def test_fresh_envelope_is_admitted_and_all_modalities_share_event(self):
        envelope = make_envelope(peer_id="mesh/node-a", sequence=7, state=self.state(), capabilities=["text", "visual", "auditory"], now_ms=1000, heartbeat_interval_ms=200)
        validation = validate_envelope(envelope, now_ms=5999)
        self.assertTrue(validation["fresh"])
        self.assertTrue(validation["admit_productive_writer"])
        rendered = render_modalities(envelope, now_ms=5999)
        self.assertEqual(rendered["event_id"], envelope["event_id"])
        self.assertIn("NONTERMINAL_APPLICABLE_GATE", rendered["text"])
        self.assertIn("QIKVRT TERMINAL PEER", rendered["visual"])
        self.assertIn("cadence", rendered["visual"])
        self.assertIn("speech_text", rendered["auditory"])

    def test_state_older_than_five_seconds_is_visible_stale_and_fail_closed(self):
        envelope = make_envelope(peer_id="mesh/node-a", sequence=8, state=self.state(), capabilities=[], now_ms=1000)
        validation = validate_envelope(envelope, now_ms=6001)
        self.assertFalse(validation["fresh"])
        self.assertFalse(validation["admit_productive_writer"])
        rendered = render_modalities(envelope, now_ms=6001)
        self.assertIn("PEER_STATE_STALE", rendered["text"])
        self.assertIn("PEER_HEARTBEAT_OLDER_THAN_5_SECONDS", rendered["visual"])

    def test_sequence_must_be_monotonic(self):
        envelope = make_envelope(peer_id="mesh/node-a", sequence=3, state=self.state(), capabilities=[], now_ms=1000)
        with self.assertRaises(RealtimeTerminalBlock):
            validate_envelope(envelope, now_ms=1100, previous_sequence=3)

    def test_invalid_adaptive_input_blocks(self):
        with self.assertRaises(RealtimeTerminalBlock):
            choose_interval_ms(transport_rtt_ms=-1)
        with self.assertRaises(RealtimeTerminalBlock):
            choose_interval_ms(send_queue_depth=-1)

    def test_credential_shaped_state_is_rejected(self):
        with self.assertRaises(RealtimeTerminalBlock):
            make_envelope(peer_id="mesh/node-a", sequence=0, state={"token": "never"}, capabilities=[], now_ms=1000)

    def test_modalities_do_not_promote_completion_claims(self):
        envelope = make_envelope(peer_id="mesh/node-a", sequence=1, state=self.state(), capabilities=[], now_ms=1000)
        self.assertEqual(envelope["completion_claims"], {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False})


if __name__ == "__main__":
    unittest.main()
