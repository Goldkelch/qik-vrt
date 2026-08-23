# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AtariBrowserC89ContractTests(unittest.TestCase):
    def test_policy_preserves_exact_boundaries(self):
        policy = json.loads(
            (ROOT / "policy" / "ATARI_BROWSER_C89_V1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(policy["state"], "SOURCE_PRESENT_ON_PR")
        self.assertFalse(policy["provenance"]["mozilla_source_copied"])
        self.assertFalse(policy["provenance"]["gecko_equivalence_claimed"])
        self.assertFalse(policy["evidence_boundaries"]["m68000_binary_executed"])
        self.assertFalse(
            policy["evidence_boundaries"]["physical_megast_execution_observed"]
        )
        self.assertFalse(policy["evidence_boundaries"]["effect_ack_done"])
        self.assertIn("JAVASCRIPT", policy["not_implemented"])
        self.assertIn("TLS", policy["not_implemented"])

    def test_reusable_core_is_c89_bounded(self):
        source = (ROOT / "src" / "atari_browser_c89.c").read_text(
            encoding="utf-8"
        )
        header = (ROOT / "include" / "qikvrt" / "atari_browser_c89.h").read_text(
            encoding="utf-8"
        )
        combined = source + "\n" + header
        self.assertNotRegex(combined, r"(?m)^\s*//")
        for forbidden in (
            "malloc(",
            "calloc(",
            "realloc(",
            "strdup(",
            "snprintf(",
            "<stdint.h>",
            "<stdbool.h>",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertIn("QIKVRT_ATARI_BROWSER_TEXT_CAPACITY", header)
        self.assertIn("HTTP/1.0", source)

    def test_workflow_is_read_only_and_exactly_compiles_c90(self):
        workflow = (
            ROOT / ".github" / "workflows" / "qikvrt_atari_browser_c89.yml"
        ).read_text(encoding="utf-8")
        shell_test = (ROOT / "tests" / "test_atari_browser_c89.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertIn("-std=c90", shell_test)
        self.assertIn("tests/test_atari_browser_c89.sh", workflow)
        self.assertIn("tests/test_qikvrt_atari_browser_c89_contract.py", workflow)

    def test_document_does_not_claim_a_firefox_binary_port(self):
        document = (ROOT / "browser" / "atari-c89" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("not Firefox", document)
        self.assertIn("HTML_TEXT_PROJECTED != FIREFOX_EQUIVALENT", document)
        self.assertIn("PHYSICAL_MEGAST_EXECUTION", document)


if __name__ == "__main__":
    unittest.main()
