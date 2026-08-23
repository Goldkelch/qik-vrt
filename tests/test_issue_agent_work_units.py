# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "issue_agent_work_units.py"
sys.path.insert(0, str(ROOT))

from tools import issue_agent_work_units as work_units


def init_repo(root: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=root,
        check=True,
    )
    (root / "README.md").write_text("repository\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "base"],
        cwd=root,
        check=True,
    )
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
    ).strip()


def write_request(root: Path, issue: int, body: str) -> None:
    directory = root / "evidence" / "issues" / str(issue)
    directory.mkdir(parents=True, exist_ok=True)
    value = {
        "issue_number": issue,
        "body": body,
    }
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    (directory / "REQUEST.json").write_bytes(raw)
    (directory / "REQUEST.sha256").write_text(
        f"{hashlib.sha256(raw).hexdigest()}  REQUEST.json\n",
        encoding="utf-8",
    )


class IssueWorkUnitsTest(unittest.TestCase):
    def run_planner(
        self,
        root: Path,
        issue: int = 79,
        *,
        model_available: bool = False,
        authority_head: str,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--issue",
            str(issue),
        ]
        if model_available:
            command.append("--model-available")
        env = os.environ.copy()
        env["QIKVRT_ISSUE_AUTHORITY_HEAD"] = authority_head
        return subprocess.run(
            command,
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_model_unavailable_preserves_deterministic_progress_and_exact_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            authority = init_repo(work)
            write_request(
                work,
                79,
                "Inventory and publish all QIK-VRT Zenodo artifacts.",
            )
            result = self.run_planner(
                work,
                authority_head=authority,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            state_path = (
                work
                / "evidence/issues/79/work-units/STATE.json"
            )
            state = json.loads(state_path.read_text())
            units = {item["name"]: item for item in state["units"]}
            for name in (
                "ZENODO_RECORD_DISCOVERY",
                "ARTIFACT_FILE_INVENTORY",
                "SOURCE_HASH_BINDING",
            ):
                self.assertEqual(units[name]["status"], "DONE")
            claim = units["CLAIM_EXTRACTION_QUEUE"]
            self.assertEqual(claim["status"], "BLOCK")
            self.assertEqual(
                claim["blocker"],
                "MODEL_INFERENCE_UNAVAILABLE",
            )
            self.assertEqual(
                state["next_cursor"],
                "CLAIM_EXTRACTION_QUEUE",
            )
            self.assertEqual(state["gate_status"], "BLOCK")
            self.assertEqual(
                state["repository_head"],
                authority,
            )

    def test_same_blocked_authority_input_creates_no_new_state_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            authority = init_repo(work)
            write_request(work, 79, "Zenodo publication")
            first = self.run_planner(
                work,
                authority_head=authority,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            state_path = (
                work
                / "evidence/issues/79/work-units/STATE.json"
            )
            before = state_path.read_bytes()
            second = self.run_planner(
                work,
                authority_head=authority,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(state_path.read_bytes(), before)
            output = json.loads(second.stdout)
            self.assertFalse(output["changed"])

    def test_available_model_without_claim_inventory_has_precise_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            authority = init_repo(work)
            write_request(work, 79, "Zenodo publication")
            result = self.run_planner(
                work,
                model_available=True,
                authority_head=authority,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(
                (
                    work
                    / "evidence/issues/79/work-units/STATE.json"
                ).read_text()
            )
            claim = next(
                item
                for item in state["units"]
                if item["name"] == "CLAIM_EXTRACTION_QUEUE"
            )
            self.assertEqual(
                claim["blocker"],
                "MACHINE_READABLE_CLAIM_INVENTORY_MISSING",
            )

    def test_publication_request_without_route_is_precise_not_generic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            authority = init_repo(work)
            write_request(work, 79, "Publish to Zenodo and obtain a DOI")
            config = work_units.Config(
                root=work,
                issue=79,
                model_available=True,
                execute=True,
            )
            with mock.patch.dict(
                os.environ,
                {"QIKVRT_ISSUE_AUTHORITY_HEAD": authority},
            ):
                status, produced, blocker, next_action = (
                    work_units._publication_assessment(config)
                )
            self.assertEqual(status, "BLOCK")
            self.assertTrue(produced)
            self.assertEqual(blocker, "PUBLICATION_ROUTE_MISSING")
            self.assertIn("qikvrt_issue_publication_route_v1", next_action)

    def test_authority_mirror_sync_is_explicit_post_effect_unit(self) -> None:
        definition = {
            name: kind
            for name, _prerequisites, kind in work_units.UNITS
        }
        self.assertEqual(
            definition["AUTHORITY_MIRROR_SYNC"],
            "post_effect",
        )


if __name__ == "__main__":
    unittest.main()
