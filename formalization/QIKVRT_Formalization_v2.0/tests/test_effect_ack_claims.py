from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EffectAckClaimBindingTests(unittest.TestCase):
    def test_draft01_source_and_claim_binding(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_effect_ack_claims.py"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            "PASS EFFECT_ACK Draft-01 source/structure/proof-reference validation",
            completed.stdout,
        )

    def test_effect_ack_library_is_a_default_target(self) -> None:
        lakefile = (ROOT / "lakefile.toml").read_text(encoding="utf-8")
        top_level = (ROOT / "QIKVRTEffectAck.lean").read_text(encoding="utf-8")
        self.assertIn('"QIKVRTEffectAck"', lakefile)
        for module in (
            "QIKVRTEffectAck.Model",
            "QIKVRTEffectAck.Safety",
            "QIKVRTEffectAck.Mediation",
            "QIKVRTEffectAck.InformationBoundary",
            "QIKVRTEffectAck.Claims",
        ):
            self.assertIn(f"import {module}", top_level)

    def test_effect_ack_axiom_and_escape_audits_are_bound(self) -> None:
        axiom_audit = (
            ROOT / "scripts/audit_lean_axioms.py"
        ).read_text(encoding="utf-8")
        escape_audit = (
            ROOT / "scripts/audit_proof_escapes.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'ROOT / "QIKVRTEffectAck" / "AxiomAudit.lean"',
            axiom_audit,
        )
        self.assertIn('ROOT / "QIKVRTEffectAck"', escape_audit)

    def test_effect_ack_axiom_audit_matches_claim_matrix(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from scripts.audit_lean_axioms import effect_ack_policy; "
                    "policy = effect_ack_policy(); "
                    "assert len(policy) == 34; "
                    "assert sum(bool(value) for value in policy.values()) == 23"
                ),
            ],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
