from __future__ import annotations
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs/publications/2026-08-04-pre-spacetime-ontology"
ROUTER = Path(__file__).resolve().parents[1] / "tools/qikvrt_publication_router.py"

class PublicationRouterTests(unittest.TestCase):
    def test_router_is_fail_closed_and_effect_free(self) -> None:
        cp = subprocess.run(
            [sys.executable, "-B", str(ROUTER), str(ROOT), "--json"],
            check=True,
            text=True,
            capture_output=True,
        )
        data = json.loads(cp.stdout)
        self.assertEqual(data["repository"], "CANDIDATE")
        self.assertEqual(data["zenodo"], "STAGED_REQUIRES_EXPLICIT_REQUEST")
        self.assertEqual(data["ietf"], "NO_SUBMISSION_SCOPE_NOTE_ONLY")
        self.assertIs(data["external_effect_performed"], False)

    def test_ietf_disposition_is_non_mutating(self) -> None:
        data = json.loads((ROOT / "IETF_DISPOSITION.json").read_text(encoding="utf-8"))
        self.assertIs(data["protocol_change_required"], False)
        self.assertIs(data["ietf_mutation_authorized"], False)

if __name__ == "__main__":
    unittest.main()
