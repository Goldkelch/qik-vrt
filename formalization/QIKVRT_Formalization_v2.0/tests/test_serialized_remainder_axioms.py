from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

FORMAL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = FORMAL_ROOT.parents[1]
MANIFEST = REPOSITORY_ROOT / "state/autonomy/EFFECT_ACK_LIVE_REST_ROUNDTRIP_V1.json"
AUDIT = FORMAL_ROOT / "QIKVRTEffectAck/SerializedRemainderAxiomAudit.lean"


class SerializedRemainderAxiomTests(unittest.TestCase):
    def test_declared_theorems_are_kernel_checked_and_axiom_free(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        expected = manifest["formal_model"]["expected_axioms_by_theorem"]
        self.assertTrue(expected)
        self.assertTrue(all(axioms == [] for axioms in expected.values()))

        result = subprocess.run(
            ["lake", "env", "lean", str(AUDIT.relative_to(FORMAL_ROOT))],
            cwd=FORMAL_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)

        pattern = re.compile(
            r"^'([^']+)' (?:does not depend on any axioms|depends on axioms: \[([^]]*)\])$"
        )
        observed: dict[str, list[str]] = {}
        for line in output.splitlines():
            match = pattern.fullmatch(line.strip())
            if match is None:
                continue
            axioms = [item.strip() for item in (match.group(2) or "").split(",") if item.strip()]
            observed[match.group(1)] = axioms

        self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
