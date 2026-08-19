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
    maxDiff = None

    def test_declared_theorems_match_exact_allowed_kernel_dependencies(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        formal_model = manifest["formal_model"]
        policy = formal_model["axiom_policy"]
        expected = formal_model["expected_axioms_by_theorem"]
        allowed = set(policy["allowed_kernel_axioms"])

        self.assertTrue(policy["exact_dependency_map_required"])
        self.assertTrue(policy["project_axioms_forbidden"])
        self.assertTrue(expected)
        for theorem, axioms in expected.items():
            self.assertEqual(len(axioms), len(set(axioms)), theorem)
            self.assertTrue(set(axioms).issubset(allowed), theorem)
            if policy["classical_choice_forbidden_for_this_module"]:
                self.assertNotIn("Classical.choice", axioms, theorem)
            if policy["sorry_admit_unsafe_forbidden"]:
                self.assertNotIn("sorryAx", axioms, theorem)

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

        print("QIKVRT_SERIALIZED_REMAINDER_AXIOMS=" + json.dumps(observed, sort_keys=True))
        self.assertEqual(observed, expected)
        self.assertTrue(
            all(set(axioms).issubset(allowed) for axioms in observed.values()),
            observed,
        )


if __name__ == "__main__":
    unittest.main()
