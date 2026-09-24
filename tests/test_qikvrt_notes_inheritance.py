# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

TOOL = Path("tools/qikvrt_notes_inheritance.py")

def load_tool():
    spec = importlib.util.spec_from_file_location("qikvrt_notes_inheritance", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

class NotesInheritanceTests(unittest.TestCase):
    def test_note_path_classifier(self):
        module = load_tool()
        self.assertTrue(module.is_note_path("release/V45_20_RELEASE_NOTES.md"))
        self.assertTrue(module.is_note_path("docs/x/EDITORIAL_NOTE.md"))
        self.assertTrue(module.is_note_path("docs/x/NOTE_DE.md"))
        self.assertFalse(module.is_note_path("policy/QIKVRT_NOTES_INHERITANCE_V1.json"))
        self.assertFalse(module.is_note_path("tests/test_qikvrt_notes_inheritance.py"))

    def test_repository_contract(self):
        proc = subprocess.run(
            [sys.executable, "-B", str(TOOL), "check"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["result"], "PASS")
        self.assertTrue(payload["future_notes_auto_inherit"])
        self.assertFalse(payload["historical_note_bytes_rewritten"])
        self.assertFalse(payload["private_payload_publicly_materialized"])
        self.assertGreaterEqual(payload["current_note_count"], 11)

if __name__ == "__main__":
    unittest.main()
