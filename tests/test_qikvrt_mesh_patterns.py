# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import qikvrt_mesh_patterns as patterns


class MeshPatternsTest(unittest.TestCase):
    def test_existing_m68000_kernel_is_reused_for_all_four_states(self) -> None:
        complete = patterns.machine_decision(
            implemented=True,
            verified=True,
            persisted=True,
            reobserved=True,
            witness=0xA5,
        )
        stale = patterns.machine_decision(
            implemented=True,
            verified=True,
            persisted=True,
            reobserved=True,
            stale=True,
            witness=0xA5,
        )
        authority = patterns.machine_decision(
            implemented=True,
            verified=True,
            persisted=True,
            reobserved=True,
            authority_required=True,
            authority_present=False,
            witness=0xA5,
        )
        invalid = patterns.machine_decision(
            implemented=True,
            verified=True,
            persisted=True,
            reobserved=True,
            unclassified_remainder=True,
            witness=0xA5,
        )
        self.assertEqual(complete["decision"], "NOOP_COMPLETE")
        self.assertEqual(stale["decision"], "REOBSERVE")
        self.assertEqual(authority["decision"], "REQUEST_AUTHORITY")
        self.assertEqual(invalid["decision"], "HOLD")
        for value in (complete, stale, authority, invalid):
            self.assertEqual(value["d3_before"], 0xA5)
            self.assertEqual(value["d3_after"], 0xA5)
            self.assertTrue(value["virtual_m68000_execution_observed"])
            self.assertFalse(value["physical_m68000_execution_observed"])
            self.assertFalse(value["sun_sparc_execution_observed"])
            self.assertFalse(value["git_or_platform_effect_applied"])

    def test_terminal_watchdog_is_lossless_and_views_share_one_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            status_path = work / "evidence/issues/79/STATUS.json"
            detail_path = work / "evidence/issues/79/work-units/STATE.json"
            status_path.parent.mkdir(parents=True)
            detail_path.parent.mkdir(parents=True)
            status_raw = (
                '{"status":"BLOCK","no_false_pass":true,'
                '"disposition_reason":"EXACT_BLOCKER",'
                '"next_action":"continue exact cursor",'
                '"publication_required":false}\n'
            ).encode()
            status_path.write_bytes(status_raw)
            detail_raw = b'{"units":[{"name":"A","status":"DONE"}]}\n'
            detail_path.write_bytes(detail_raw)

            receipt, views = patterns.build_terminal_receipt(
                root=work,
                status_path=status_path,
                detail_paths=[detail_path],
                repository="Goldkelch/qik-vrt",
                ref="refs/heads/issue-agent/79",
                head="1" * 40,
                tree="2" * 40,
            )
            patterns.verify_terminal_receipt(receipt)
            payload = receipt["canonical_state"]["status_payload"]
            self.assertEqual(patterns.decode_payload(payload), status_raw)
            self.assertEqual(
                patterns.decode_payload(
                    receipt["canonical_state"]["detail_payloads"][0]
                ),
                detail_raw,
            )
            for audience in patterns.AUDIENCES:
                self.assertEqual(
                    views[audience]["receipt_sha256"],
                    receipt["receipt_sha256"],
                )
            self.assertTrue(views["WATCHDOG_FULL"]["lossless"])
            self.assertEqual(
                views["WATCHDOG_FULL"]["canonical_receipt"],
                receipt,
            )
            self.assertNotIn(
                "canonical_receipt",
                views["OWNER"],
            )

    def test_pattern_capsule_is_content_addressed_and_does_not_clone_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            status_path = work / "STATUS.json"
            status_path.write_text(
                json.dumps(
                    {
                        "status": "CONTINUE",
                        "no_false_pass": True,
                        "next_action": "continue",
                        "publication_required": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            receipt, _views = patterns.build_terminal_receipt(
                root=work,
                status_path=status_path,
                repository="Goldkelch/qik-vrt",
                ref="refs/heads/test",
                head="3" * 40,
                tree="4" * 40,
            )
            capsule = patterns.build_pattern_capsule(receipt)
            patterns.verify_pattern_capsule(capsule)
            self.assertTrue(
                capsule["clone_contract"]["clone_requirements"]
            )
            self.assertIn(
                "repository ownership",
                capsule["nonportable_authority"],
            )
            serialized = patterns.canonical_bytes(capsule)
            self.assertNotIn(b"ZENODO_ACCESS_TOKEN=", serialized)
            self.assertNotIn(b"GITHUB_TOKEN=", serialized)

    def test_policy_distinguishes_qikvrt_spark_from_sun_sparc(self) -> None:
        policy = patterns.load_policy()
        boundaries = policy["m68000_compilation"]["truth_boundaries"]
        self.assertIn(
            "QIKVRT_CIRCULAR_SPARK_ARCHITECTURE_NOT_EQUAL_SUN_SPARC_ISA",
            boundaries,
        )
        self.assertEqual(
            policy["m68000_compilation"]["scope"],
            "ALL_ELIGIBLE_FINITE_CONTROL_PATTERNS",
        )


if __name__ == "__main__":
    unittest.main()
