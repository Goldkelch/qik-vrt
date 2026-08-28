#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Shared decision-projection checks for the Python and C evaluators.

These tests compare representative, already-decoded decision snapshots.  They
do not assert wire-format, parser, memory-layout, ABI, timestamp, receipt, or
protocol-chain equivalence between the two implementations.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qikvrt_effect_ack import (  # noqa: E402
    ConnectionDecision,
    EffectAckEngine,
    EffectAckRequest,
    EffectState,
    RiskLevel,
    ordinary_release,
    sha256_identifier,
)


PAYLOAD = b"cross-language effect input"
EVIDENCE = sha256_identifier(b"cross-language evidence")

C_FIELDS = (
    "transport_ack",
    "input_identifier_available",
    "input_digest_valid",
    "origin_checked",
    "context_checked",
    "semantics_reconstructed",
    "effect_anticipated",
    "risk_classified",
    "risk_known",
    "responsibility_assigned",
    "responsibility_owner_present",
    "connection_decided",
    "connection_decision",
    "policy_allows_release",
    "deadline_exceeded",
    "no_open_questions",
    "no_next_required_checks",
    "required_evidence_present",
    "predecessor_invalid",
    "integrity_failure",
)

BASE_C = {
    "transport_ack": 1,
    "input_identifier_available": 1,
    "input_digest_valid": 1,
    "origin_checked": 1,
    "context_checked": 1,
    "semantics_reconstructed": 1,
    "effect_anticipated": 1,
    "risk_classified": 1,
    "risk_known": 1,
    "responsibility_assigned": 1,
    "responsibility_owner_present": 1,
    "connection_decided": 1,
    "connection_decision": 2,
    "policy_allows_release": 1,
    "deadline_exceeded": 0,
    "no_open_questions": 1,
    "no_next_required_checks": 1,
    "required_evidence_present": 1,
    "predecessor_invalid": 0,
    "integrity_failure": 0,
}

BASE_PYTHON: dict[str, Any] = {
    "protocol_root_id": "qikvrt:cross-language:root",
    "input_id": "cross-language-input",
    "payload": PAYLOAD,
    "declared_input_hash": sha256_identifier(PAYLOAD),
    "transport_ack": True,
    "origin_checked": True,
    "context_checked": True,
    "semantics_reconstructed": True,
    "effect_anticipated": True,
    "risk_classified": True,
    "risk_level": RiskLevel.LOW,
    "responsibility_assigned": True,
    "responsibility_owner": "cross-language-owner",
    "connection_decision": ConnectionDecision.RELEASE,
    "policy_allows_release": True,
    "reasons": (),
    "evidence_refs": (EVIDENCE,),
    "required_evidence_refs": (EVIDENCE,),
    "open_questions": (),
    "next_required_checks": (),
}

VECTORS: tuple[
    tuple[str, dict[str, int], dict[str, Any], EffectState], ...
] = (
    (
        "no_effect_checkable_reception",
        {"input_identifier_available": 0, "input_digest_valid": 0},
        {"payload": None, "declared_input_hash": None},
        EffectState.EFFECT_NACK,
    ),
    (
        "transport_ack_is_a_done_gate_not_checkability",
        {"transport_ack": 0},
        {"transport_ack": False},
        EffectState.EFFECT_ACK_CONTINUE,
    ),
    (
        "checking_continues",
        {"connection_decided": 1, "connection_decision": 1},
        {"connection_decision": ConnectionDecision.CONTINUE},
        EffectState.EFFECT_ACK_CONTINUE,
    ),
    (
        "all_done_conjuncts",
        {},
        {},
        EffectState.EFFECT_ACK_DONE,
    ),
    (
        "responsible_isolation",
        {"connection_decision": 3},
        {"connection_decision": ConnectionDecision.ISOLATE},
        EffectState.EFFECT_ACK_ISOLATE,
    ),
    (
        "responsible_block",
        {"connection_decision": 4},
        {"connection_decision": ConnectionDecision.BLOCK},
        EffectState.EFFECT_ACK_BLOCK,
    ),
    (
        "done_conjunct_origin_missing",
        {"origin_checked": 0},
        {"origin_checked": False},
        EffectState.EFFECT_ACK_CONTINUE,
    ),
    (
        "done_conjunct_required_evidence_missing",
        {"required_evidence_present": 0},
        {"evidence_refs": ()},
        EffectState.EFFECT_ACK_CONTINUE,
    ),
)

C_RUNNER = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "qikvrt/effect_ack.h"

int main(int argc, char **argv)
{
    qikvrt_effect_ack_input input;
    qikvrt_effect_ack_state state;

    if (argc != 21) {
        (void)fprintf(stderr, "expected 20 integer fields\n");
        return 2;
    }

    (void)memset(&input, 0, sizeof(input));
    input.transport_ack = atoi(argv[1]);
    input.input_identifier_available = atoi(argv[2]);
    input.input_digest_valid = atoi(argv[3]);
    input.origin_checked = atoi(argv[4]);
    input.context_checked = atoi(argv[5]);
    input.semantics_reconstructed = atoi(argv[6]);
    input.effect_anticipated = atoi(argv[7]);
    input.risk_classified = atoi(argv[8]);
    input.risk_known = atoi(argv[9]);
    input.responsibility_assigned = atoi(argv[10]);
    input.responsibility_owner_present = atoi(argv[11]);
    input.connection_decided = atoi(argv[12]);
    input.connection_decision = (qikvrt_effect_ack_decision)atoi(argv[13]);
    input.policy_allows_release = atoi(argv[14]);
    input.deadline_exceeded = atoi(argv[15]);
    input.no_open_questions = atoi(argv[16]);
    input.no_next_required_checks = atoi(argv[17]);
    input.required_evidence_present = atoi(argv[18]);
    input.predecessor_invalid = atoi(argv[19]);
    input.integrity_failure = atoi(argv[20]);

    state = qikvrt_effect_ack_evaluate(&input);
    (void)printf(
        "%s %d\n",
        qikvrt_effect_ack_state_name(state),
        qikvrt_effect_ack_ordinary_release(state));
    return 0;
}
"""


class EffectAckCrossLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary_directory = tempfile.TemporaryDirectory(
            prefix="qikvrt-effect-ack-cross-language-"
        )
        build = Path(cls._temporary_directory.name)
        runner_source = build / "effect_ack_runner.c"
        runner_source.write_text(C_RUNNER, encoding="utf-8")
        cls.runners: dict[str, Path] = {}
        compiler = shlex.split(os.environ.get("CC", "cc"))
        for dialect in ("c89", "c90"):
            runner = build / f"effect_ack_runner_{dialect}"
            subprocess.run(
                [
                    *compiler,
                    f"-std={dialect}",
                    "-pedantic",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    f"-I{ROOT / 'include'}",
                    str(ROOT / "src" / "effect_ack_core.c"),
                    str(runner_source),
                    "-o",
                    str(runner),
                ],
                check=True,
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            cls.runners[dialect] = runner

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary_directory.cleanup()

    @staticmethod
    def _python_result(updates: dict[str, Any]) -> tuple[str, bool]:
        values = dict(BASE_PYTHON)
        values.update(updates)
        request = EffectAckRequest(**values)
        result = EffectAckEngine(clock_ns=lambda: 0).evaluate(
            request,
            created_utc="2026-08-28T00:00:00Z",
        )
        return result.state.value, ordinary_release(result)

    def _c_result(
        self,
        dialect: str,
        updates: dict[str, int],
    ) -> tuple[str, bool]:
        values = dict(BASE_C)
        values.update(updates)
        completed = subprocess.run(
            [
                str(self.runners[dialect]),
                *(str(values[field]) for field in C_FIELDS),
            ],
            check=True,
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        state, release = completed.stdout.strip().split()
        return state, release == "1"

    def test_representative_shared_decision_projection(self) -> None:
        for dialect in ("c89", "c90"):
            for name, c_updates, python_updates, expected in VECTORS:
                with self.subTest(dialect=dialect, vector=name):
                    python_result = self._python_result(python_updates)
                    c_result = self._c_result(dialect, c_updates)
                    self.assertEqual(python_result, c_result)
                    self.assertEqual(
                        python_result,
                        (
                            expected.value,
                            expected is EffectState.EFFECT_ACK_DONE,
                        ),
                    )

    def test_vectors_cover_closed_state_set_and_done_conjuncts(self) -> None:
        expected_states = {state.value for state in EffectState}
        vector_states = {expected.value for _, _, _, expected in VECTORS}
        self.assertEqual(vector_states, expected_states)
        names = {name for name, _, _, _ in VECTORS}
        self.assertIn("transport_ack_is_a_done_gate_not_checkability", names)
        self.assertIn("all_done_conjuncts", names)
        self.assertTrue(
            any(name.startswith("done_conjunct_") for name in names)
        )


if __name__ == "__main__":
    unittest.main()
