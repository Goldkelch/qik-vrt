# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "QIKVRT_NOTES_INHERITANCE_V1.json"
REGISTRY = ROOT / "state" / "QIKVRT_NOTES_REGISTRY_V1.json"
NOTE_RE = re.compile("note", re.IGNORECASE)
EXTENSIONS = {".md", ".txt", ".tex", ".json", ".yaml", ".yml"}
CONTROL_PATHS = {
    "docs/QIKVRT_NOTES_INHERITANCE_V1.md",
    "policy/QIKVRT_NOTES_INHERITANCE_V1.json",
    "state/QIKVRT_NOTES_REGISTRY_V1.json",
    "tests/test_qikvrt_notes_inheritance.py",
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def discover_notes():
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = [p.decode("utf-8") for p in raw.split(b"\0") if p]
    return sorted(
        p for p in paths
        if p not in CONTROL_PATHS
        and Path(p).suffix.lower() in EXTENSIONS
        and NOTE_RE.search(Path(p).name)
    )


class NotesInheritanceTests(unittest.TestCase):
    def test_historical_notes_remain_byte_bound(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["carrier_count"], 11)
        discovered = set(discover_notes())
        for item in registry["carriers"]:
            self.assertIn(item["path"], discovered)
            self.assertEqual(
                git("hash-object", "--", item["path"]),
                item["git_blob_sha1"],
            )

    def test_future_notes_inherit_by_scope(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(
            policy["scope"]["applies_to"],
            "ALL_EXISTING_AND_FUTURE_QIKVRT_NOTE_CARRIERS",
        )
        self.assertTrue(policy["future_rule"]["inheritance_is_automatic_by_scope_match"])
        self.assertTrue(
            policy["future_rule"]["historical_or_frozen_note_bytes_are_not_rewritten_for_inheritance"]
        )

    def test_effect_semantics_remain_separate(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        inv = set(policy["canonical_note_invariants"])
        self.assertIn("TRANSPORT_ACK_IS_NOT_EFFECT_ACK", inv)
        self.assertIn("PREDECESSOR_EVIDENCE_TRANSFER_IS_FALSE", inv)
        self.assertIn("FRESH_READBACK_PRECEDES_ACCEPTANCE", inv)
        self.assertIn("ACCEPTED_SUCCESSOR_MAY_BECOME_NEXT_BOUND_INPUT", inv)
        self.assertFalse(policy["completion_boundary"]["effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
