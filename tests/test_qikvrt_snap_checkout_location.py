# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression: a dependency Git checkout must not enter the inventory gate."""
from pathlib import Path
import unittest


class SnapCheckoutLocationTests(unittest.TestCase):
    def test_source_relocated_before_native_build_and_integrity_gate(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/qikvrt_real_mesh.yml").read_text()
        self.assertIn('mktemp -d "$RUNNER_TEMP/qikvrt-snap-source.XXXXXX"', workflow)
        relocation = 'mv .qikvrt/snap-source "$snap_workdir/source"'
        native_build = 'tools/qikvrt_build_snap.py --source "$snap_workdir/source"'
        self.assertIn(relocation, workflow)
        self.assertIn(native_build, workflow)
        self.assertLess(workflow.index(relocation), workflow.index(native_build))
        self.assertLess(workflow.index(native_build),
                        workflow.index("tools/qikvrt_integrity.py verify"))
        self.assertIn("-p 'test_qikvrt_snap_*.py' -v", workflow)
        self.assertNotIn("continue-on-error", workflow)


if __name__ == "__main__":
    unittest.main()
