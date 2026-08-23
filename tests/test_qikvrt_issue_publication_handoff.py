# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import qikvrt_issue_publication_handoff as handoff
from scripts.issue_agent.promote import promote
from scripts.issue_agent.validate import validate


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def init_repo(root: Path) -> None:
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


def commit_all(root: Path) -> None:
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "candidate"],
        cwd=root,
        check=True,
    )


class IssuePublicationHandoffTest(unittest.TestCase):
    def test_absent_route_is_not_a_false_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            init_repo(work)
            (work / "README.md").write_text("x\n", encoding="utf-8")
            commit_all(work)
            value = handoff.assess(work, 79)
            self.assertEqual(value["state"], "NOT_REQUESTED")
            self.assertFalse(value["ready"])
            self.assertFalse(value["effect_ack_done"])

    def make_ready_candidate(self, root: Path) -> None:
        issue_dir = root / "evidence/issues/79"
        manifest_path = root / "release/example/publish-request.json"
        manifest = {
            "schema": "qikvrt_zenodo_publication_manifest_v2",
            "state": "publish",
            "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
            "repository": "Goldkelch/qik-vrt",
            "machine_proof": {"path": "proof.json"},
            "owner_authorization": {"path": "authorization.json"},
            "evidence_path": "release/example/zenodo-publication.json",
        }
        write_json(manifest_path, manifest)
        write_json(
            issue_dir / "STATUS.json",
            {
                "status": "CONTINUE",
                "pre_effect_ready": True,
                "publication_required": True,
                "publication_state": "READY",
                "model_inference_completed": True,
                "no_false_pass": True,
            },
        )
        manifest_sha = hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest()
        write_json(
            issue_dir / "PUBLICATION_ROUTE.json",
            {
                "schema": "qikvrt_issue_publication_route_v1",
                "issue_number": 79,
                "required": True,
                "platform": "zenodo",
                "state": "READY",
                "manifest_path": (
                    "release/example/publish-request.json"
                ),
                "manifest_sha256": manifest_sha,
                "adapter": "tools/qikvrt_zenodo_publish.py",
                "receipt_path": (
                    "evidence/issues/79/"
                    "PUBLICATION_EFFECT_RECEIPT.json"
                ),
            },
        )

    def test_exact_committed_v2_route_reaches_m68000_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            init_repo(work)
            self.make_ready_candidate(work)
            commit_all(work)
            value = handoff.assess(work, 79)
            self.assertEqual(value["state"], "READY")
            self.assertTrue(value["ready"])
            self.assertEqual(
                value["m68000_decision"]["decision"],
                "NOOP_COMPLETE",
            )
            self.assertEqual(
                value["effect_adapter"],
                "tools/qikvrt_zenodo_publish.py",
            )
            self.assertFalse(value["effect_ack_done"])

    def test_manifest_drift_forces_reobservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            init_repo(work)
            self.make_ready_candidate(work)
            commit_all(work)
            manifest_path = work / "release/example/publish-request.json"
            manifest_path.write_text(
                manifest_path.read_text() + "\n",
                encoding="utf-8",
            )
            value = handoff.assess(work, 79)
            self.assertEqual(value["state"], "HOLD")
            self.assertFalse(value["ready"])
            self.assertIn(
                "differs from committed HEAD bytes",
                value["first_blocker"],
            )

    def test_unsupported_platform_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            init_repo(work)
            self.make_ready_candidate(work)
            route_path = (
                work
                / "evidence/issues/79/PUBLICATION_ROUTE.json"
            )
            route = json.loads(route_path.read_text())
            route["platform"] = "arxiv"
            write_json(route_path, route)
            commit_all(work)
            value = handoff.assess(work, 79)
            self.assertEqual(value["state"], "HOLD")
            self.assertFalse(value["ready"])
            self.assertEqual(
                value["m68000_decision"]["decision"],
                "HOLD",
            )
            self.assertIsNone(value["effect_adapter"])

    def make_issue_bundle(
        self,
        root: Path,
        *,
        publication_state: str,
    ) -> Path:
        directory = root / "evidence/issues/79"
        directory.mkdir(parents=True, exist_ok=True)
        request = (
            json.dumps({"issue_number": 79}, sort_keys=True) + "\n"
        ).encode()
        (directory / "REQUEST.json").write_bytes(request)
        (directory / "REQUEST.sha256").write_text(
            f"{hashlib.sha256(request).hexdigest()}  REQUEST.json\n",
            encoding="utf-8",
        )
        (directory / "CONTEXT.md").write_text(
            "context\n",
            encoding="utf-8",
        )
        (directory / "ANSWER.md").write_text(
            "## Issue disposition\n\nCLOSE_COMPLETED\n\n"
            "## Disposition reason\n\nInternal work complete.\n\n"
            "## Required next action\n\nNONE\n\n"
            "## Gate result\n\nCONTINUE\n",
            encoding="utf-8",
        )
        status = {
            "status": "CONTINUE",
            "model_inference_completed": True,
            "issue_disposition": "CLOSE_COMPLETED",
            "disposition_reason": "Internal work complete.",
            "next_action": "NONE",
            "closure_recommended": True,
            "automatic_issue_close": False,
            "automatic_merge": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "publication_required": True,
            "publication_state": publication_state,
            "effect_ack_done": publication_state == "PUBLIC_VERIFIED",
            "no_false_pass": True,
        }
        if publication_state == "PUBLIC_VERIFIED":
            receipt = directory / "PUBLICATION_EFFECT_RECEIPT.json"
            write_json(
                receipt,
                {
                    "schema": handoff.SCHEMA_RECEIPT,
                    "state": "PUBLIC_VERIFIED",
                },
            )
            status["publication_effect_receipt"] = (
                "evidence/issues/79/PUBLICATION_EFFECT_RECEIPT.json"
            )
        write_json(directory / "STATUS.json", status)
        return directory

    def test_ready_required_publication_cannot_promote_to_done(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = self.make_issue_bundle(
                Path(temp),
                publication_state="READY",
            )
            promote(directory)
            status = json.loads(
                (directory / "STATUS.json").read_text()
            )
            self.assertEqual(status["status"], "CONTINUE")
            self.assertEqual(
                status["issue_disposition"],
                "EXECUTE_NOW",
            )
            self.assertFalse(status["automatic_merge"])
            self.assertFalse(status["effect_ack_done"])
            validate(directory)

    def test_public_verified_receipt_allows_repository_autofinish(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = self.make_issue_bundle(
                Path(temp),
                publication_state="PUBLIC_VERIFIED",
            )
            promote(directory)
            status = json.loads(
                (directory / "STATUS.json").read_text()
            )
            self.assertEqual(status["status"], "DONE")
            self.assertTrue(status["automatic_merge"])
            self.assertTrue(status["automatic_issue_close"])
            self.assertTrue(status["effect_ack_done"])
            validate(directory)


if __name__ == "__main__":
    unittest.main()
