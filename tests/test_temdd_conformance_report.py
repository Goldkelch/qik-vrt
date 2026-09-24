import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.qikvrt_temdd_conformance_report import (
    ConformanceReportHold,
    build_report,
)


ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def receipt(head, tree):
    return {
        "source_sha": head,
        "source_tree": tree,
        "backends": {
            "c90": "EXECUTED_SUCCESS",
            "smalltalk": "EXECUTED_SUCCESS",
            "m68000": "EXECUTED_SUCCESS_QEMU_USER",
            "lean": "COMPILED_SUCCESS_LEAN_4_19_LAKE",
        },
        "predecessor_evidence_transfer": False,
    }


class TEMDDConformanceReportTests(unittest.TestCase):
    def test_exact_subject_report_is_crypto_bound_and_scoped(self):
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        report = build_report("Goldkelch/qik-vrt", head, tree, receipt(head, tree))
        self.assertEqual(report["overall"], "PASS")
        self.assertTrue(report["implementation"]["digest"].startswith("sha256:"))
        self.assertTrue(report["suite"]["digest"].startswith("sha256:"))
        self.assertFalse(report["stable_language_claim"])
        self.assertFalse(report["main_adoption"])
        self.assertFalse(report["production_effect"])
        self.assertFalse(report["effect_ack_done"])
        self.assertFalse(report["predecessor_evidence_transfer"])

    def test_wrong_subject_cannot_receive_report(self):
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        with self.assertRaises(ConformanceReportHold):
            build_report("Goldkelch/qik-vrt", "0" * 40, tree, receipt(head, tree))


if __name__ == "__main__":
    unittest.main()
