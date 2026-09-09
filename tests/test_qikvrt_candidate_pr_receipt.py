# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_candidate_pr_receipt as receipt


BASE = "a" * 40
HEAD = "b" * 40
TREE = "c" * 40
BRANCH = "automation/example"


def readback(**overrides):
    value = {
        "number": 42,
        "url": "https://github.com/Goldkelch/qik-vrt/pull/42",
        "isDraft": True,
        "baseRefName": "main",
        "baseRefOid": BASE,
        "headRefName": BRANCH,
        "headRefOid": HEAD,
    }
    value.update(overrides)
    return value


def provenance(**overrides):
    value = {
        "commit": HEAD,
        "tree": TREE,
        "parents": [BASE],
    }
    value.update(overrides)
    return value


class CandidatePullRequestReceiptTests(unittest.TestCase):
    def test_exact_draft_candidate_is_reobserved(self):
        value = receipt.validate(
            readback(),
            expected_base=BASE,
            expected_head=HEAD,
            expected_branch=BRANCH,
            expected_tree=TREE,
            provenance=provenance(),
        )
        self.assertEqual(value["state"], "DRAFT_CANDIDATE_REOBSERVED")
        self.assertEqual(value["pull_request"]["headRefOid"], HEAD)
        self.assertEqual(value["candidate_commit"]["tree"], TREE)

    def test_wrong_pr_metadata_tree_or_ancestry_is_rejected(self):
        for wrong_readback, wrong_provenance in (
            (readback(baseRefOid=HEAD), provenance()),
            (readback(isDraft=False), provenance()),
            (readback(), provenance(tree=HEAD)),
            (readback(), provenance(parents=[BASE, HEAD])),
            (readback(), provenance(parents=[HEAD])),
        ):
            with self.assertRaises(ValueError):
                receipt.validate(
                    wrong_readback,
                    expected_base=BASE,
                    expected_head=HEAD,
                    expected_branch=BRANCH,
                    expected_tree=TREE,
                    provenance=wrong_provenance,
                )

    def test_git_provenance_binds_one_commit_tree_and_direct_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            def git(*args: str) -> str:
                result = subprocess.run(
                    ["git", "-C", str(root), *args],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return result.stdout.strip()

            git("init", "--quiet")
            git("config", "user.name", "QIKVRT test")
            git("config", "user.email", "qikvrt-test@example.invalid")
            (root / "proof.txt").write_text("base\n", encoding="utf-8")
            git("add", "proof.txt")
            git("commit", "--quiet", "-m", "base")
            base = git("rev-parse", "HEAD")
            (root / "proof.txt").write_text("candidate\n", encoding="utf-8")
            git("add", "proof.txt")
            git("commit", "--quiet", "-m", "candidate")
            head = git("rev-parse", "HEAD")
            tree = git("rev-parse", "HEAD^{tree}")

            observed = receipt.candidate_provenance(root, head)

        self.assertEqual(observed, {"commit": head, "tree": tree, "parents": [base]})

    def test_cli_writes_a_hold_receipt_for_mismatching_readback(self):
        class Output:
            def __init__(self):
                self.buffer = io.BytesIO()

            def write(self, value):
                return len(value)

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "readback.json"
            source.write_text(json.dumps(readback(isDraft=False)), encoding="utf-8")
            result = root / "receipt.json"
            with mock.patch.object(receipt.sys, "stdout", Output()):
                code = receipt.main([
                    "--readback", str(source),
                    "--expected-base", BASE,
                    "--expected-head", HEAD,
                    "--expected-branch", BRANCH,
                    "--expected-tree", TREE,
                    "--receipt", str(result),
                ])
            value = json.loads(result.read_text(encoding="utf-8"))
        self.assertEqual(code, 2)
        self.assertEqual(value["state"], "HOLD_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
