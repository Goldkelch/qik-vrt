#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest

from tools import qikvrt_ruleset_effect_recovery as recovery


MAIN = "a" * 40
HEAD = "b" * 40


def page(*runs):
    return {"workflow_runs": list(runs)}


def run(run_id: int, *, status: str, title: str):
    return {
        "id": run_id,
        "status": status,
        "head_branch": "main",
        "head_sha": MAIN,
        "display_title": title,
    }


def title(*, bridge: int | None = None, mode: str = "APPLY", recovery_of: int | None = None) -> str:
    base = f"QIKVRT ruleset effect mode=PR pr=7 head={HEAD} upstream=99"
    origin = "none" if recovery_of is None else str(recovery_of)
    return base if bridge is None else f"{base} bridge={bridge} carrier=unbound recovery={mode} recovery_of={origin} policy=none"


def receipt(state: str, **extra):
    value = {
        "schema": recovery.CONTINUATION_RECEIPT_SCHEMA,
        "repository": "Goldkelch/qik-vrt",
        "subject_mode": "PR",
        "pr_number": 7,
        "head_sha": HEAD,
        "trusted_main_sha": MAIN,
        "upstream_run_id": 99,
        "full_exact_subject_verified": True,
        "state": state,
        "mutation": "NONE",
        "effect_transport_attempted": False,
        "effect_observed": False,
    }
    if state == "HOLD":
        value.update(
            {
                "verification_state": "HOLD_UNVERIFIED",
                "continuation_required": True,
                "first_blocker": "TEST_HOLD",
                "next_action": "REOBSERVE",
                "hold_reason": {
                    "d0": 2,
                    "reason_code": "TEST_HOLD",
                    "reason": "test hold",
                    "next_action": "REOBSERVE",
                    "subject": {"repository": "Goldkelch/qik-vrt"},
                    "owner": {"role": "TEST"},
                    "retry_condition": {"event": "TEST"},
                    "evidence_refs": ["test:evidence"],
                },
                "d0": 2,
            }
        )
    value.update(extra)
    return value


def classify(value, *, mode="APPLY", conclusion="failure", bridge=None, recovery_of=None):
    value = dict(value)
    if bridge is not None:
        value.setdefault("bridge_run_id", bridge)
        value.setdefault("recovery_mode", mode)
        value.setdefault("recovery_of_effect_run_id", recovery_of)
    return recovery.classify_terminal_receipt(
        value,
        recovery_mode=mode,
        bridge_run_id=bridge,
        recovery_of_effect_run_id=recovery_of,
        conclusion=conclusion,
        repository="Goldkelch/qik-vrt",
        pr_number=7,
        head_sha=HEAD,
        main_sha=MAIN,
        upstream_run_id=99,
    )


class RulesetEffectRecoveryTests(unittest.TestCase):
    def test_active_exact_effect_beats_terminal_history(self):
        result = recovery.select_run(
            [page(run(2, status="completed", title=title(bridge=10)), run(3, status="queued", title=title(bridge=11)))],
            pr_number=7,
            head_sha=HEAD,
            main_sha=MAIN,
            upstream_run_id=99,
        )
        self.assertEqual(result["state"], "ACTIVE")
        self.assertEqual(result["effect_run_id"], 3)

    def test_terminal_current_is_a_noop(self):
        result = classify(
            receipt("CURRENT", effect_transport_attempted=False, effect_observed=False),
            conclusion="success",
        )
        self.assertEqual(result["state"], "NOOP")

    def test_uncertain_put_requires_get_only_reobserve_before_retry(self):
        result = classify(
            receipt(
                "HOLD",
                effect_transport_attempted=True,
                effect_observed=False,
            )
        )
        self.assertEqual(result["next_recovery_mode"], "REOBSERVE_UNCONFIRMED")

    def test_reobserve_drift_permits_a_later_apply(self):
        result = classify(
            receipt(
                "HOLD",
                observed_state="DRIFT",
                effect_transport_attempted=False,
                effect_observed=False,
            ),
            mode="REOBSERVE_UNCONFIRMED",
            bridge=10,
            recovery_of=11,
        )
        self.assertEqual(result["next_recovery_mode"], "APPLY")

    def test_reobserve_without_an_uncertain_origin_fails_closed(self):
        with self.assertRaisesRegex(recovery.EffectRecoveryError, "omitted its original uncertain effect"):
            classify(
                receipt(
                    "HOLD",
                    observed_state="DRIFT",
                    effect_transport_attempted=False,
                    effect_observed=False,
                ),
                mode="REOBSERVE_UNCONFIRMED",
                bridge=10,
            )

    def test_provenanced_normal_apply_accepts_no_recovery_origin(self):
        result = classify(
            receipt(
                "CURRENT",
                bridge_run_id=10,
                recovery_mode="APPLY",
                recovery_of_effect_run_id=None,
                effect_transport_attempted=False,
                effect_observed=False,
            ),
            conclusion="success",
            bridge=10,
        )
        self.assertEqual(result["state"], "NOOP")

    def test_current_receipt_with_failed_job_is_retried_for_completion(self):
        result = classify(
            receipt("CURRENT", effect_transport_attempted=False, effect_observed=False),
            conclusion="failure",
        )
        self.assertEqual(result["state"], "RETRY")
        self.assertEqual(result["next_recovery_mode"], "APPLY")

    def test_malformed_page_fails_closed(self):
        with self.assertRaisesRegex(recovery.EffectRecoveryError, "workflow_runs"):
            recovery.select_run(
                [{}], pr_number=7, head_sha=HEAD, main_sha=MAIN, upstream_run_id=99
            )

    def test_over_capacity_single_page_fails_closed(self):
        with self.assertRaisesRegex(recovery.EffectRecoveryError, "within 100"):
            recovery.select_run(
                {"total_count": 101, "workflow_runs": []},
                pr_number=7,
                head_sha=HEAD,
                main_sha=MAIN,
                upstream_run_id=99,
            )

    def test_schema_free_terminal_receipt_cannot_authorize_a_noop(self):
        value = receipt("CURRENT")
        value.pop("schema")
        with self.assertRaisesRegex(recovery.EffectRecoveryError, "schema"):
            classify(value, conclusion="success")

    def test_incomplete_hold_contract_cannot_authorize_a_retry(self):
        value = receipt("HOLD")
        value["hold_reason"] = {"d0": 2}
        with self.assertRaisesRegex(recovery.EffectRecoveryError, "hold_reason"):
            classify(value)


if __name__ == "__main__":
    unittest.main()
