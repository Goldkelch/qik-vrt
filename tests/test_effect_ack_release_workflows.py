#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline structural regression tests for EFFECT_ACK release workflows."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESERVE = ROOT / ".github/workflows/qikvrt_zenodo_reserve.yml"
FINALIZE = ROOT / ".github/workflows/qikvrt_effect_ack_finalize.yml"
GENERAL_CI = ROOT / ".github/workflows/qikvrt_ci.yml"
ADAPTIVE_RUNTIME = ROOT / ".github/workflows/qikvrt_adaptive_runtime.yml"
MARKER = ROOT / "release/effect-ack-universality-request.json"
SCHEMA = ROOT / "policy/qikvrt-effect-ack-release-request.schema.json"
MARKER_PATH = "release/effect-ack-universality-request.json"
RESERVE_BRANCH = "automation/effect-ack-universality-reserve-20260722"
FINALIZE_BRANCH = "automation/effect-ack-universality-finalize-20260722"


def run_git(root: pathlib.Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", os.fspath(root), *arguments],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


class EffectAckReleaseWorkflowTests(unittest.TestCase):
    maxDiff = None

    def test_inert_marker_binds_schema_and_canonical_payload(self) -> None:
        marker = json.loads(MARKER.read_text(encoding="utf-8"))
        json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(marker["state"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertEqual(marker["release"]["expected_source_commit"], "0" * 40)
        self.assertEqual(marker["release"]["expected_source_tree"], "0" * 40)
        self.assertEqual(
            marker["schema_sha256"], hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
        )
        supplied = marker.pop("authorization_payload_sha256")
        canonical = json.dumps(
            marker, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(supplied, hashlib.sha256(canonical).hexdigest())

    def test_exact_branch_filters_and_no_interactive_or_main_trigger(self) -> None:
        reserve = RESERVE.read_text(encoding="utf-8")
        finalize = FINALIZE.read_text(encoding="utf-8")
        self.assertIn(f"      - {RESERVE_BRANCH}\n", reserve)
        self.assertNotIn(FINALIZE_BRANCH, reserve.split("permissions:", 1)[0])
        self.assertIn(f"      - {FINALIZE_BRANCH}\n", finalize)
        self.assertNotIn(RESERVE_BRANCH, finalize.split("permissions:", 1)[0])
        for text in (reserve, finalize):
            trigger = text.split("permissions:", 1)[0]
            self.assertNotRegex(trigger, r"(?m)^\s*- main\s*$")
            self.assertNotIn("workflow_dispatch", text)
            self.assertNotIn("repository_dispatch", text)
            self.assertNotRegex(text, r"(?m)^\s*environment\s*:")

        general_ci = GENERAL_CI.read_text(encoding="utf-8")
        self.assertIn(f"      - {RESERVE_BRANCH}\n", general_ci)
        self.assertIn(f"      - {FINALIZE_BRANCH}\n", general_ci)

    def test_effect_boundaries_and_secret_wiring(self) -> None:
        for path in (RESERVE, FINALIZE):
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            self.assertNotIn("datatracker.ietf.org", lowered)
            self.assertNotIn("gh release", lowered)
            self.assertNotIn("--token", lowered)
            secret_expressions = re.findall(
                r"\$\{\{\s*secrets\.[A-Za-z0-9_]+\s*\}\}", text
            )
            self.assertTrue(secret_expressions)
            self.assertEqual(
                set(secret_expressions), {"${{ secrets.ZENODO_ACCESS_TOKEN }}"}
            )
        reserve = RESERVE.read_text(encoding="utf-8")
        finalize = FINALIZE.read_text(encoding="utf-8")
        self.assertIn('release_path = "/releases/tags/"', finalize)
        self.assertIn('api("GET", release_path, missing_ok=True)', finalize)
        self.assertIn('"github_release_object_absence_verified": True', finalize)
        self.assertNotRegex(
            finalize,
            r'api\("(?:POST|PATCH|PUT|DELETE)",\s*(?:release_path|"/releases)',
        )
        self.assertIn(
            ".qikvrt/release/effect-ack-universality/zenodo-reservation.json",
            reserve,
        )
        self.assertIn(
            ".qikvrt/release/effect-ack-universality/zenodo-finalization.json",
            finalize,
        )
        self.assertIn("tools/qikvrt_build_zenodo_manifest.py", finalize)
        self.assertIn(
            "--manifest .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json",
            finalize,
        )
        self.assertIn("--source-commit \"$SOURCE_COMMIT\"", finalize)
        self.assertIn("--source-tree \"$SOURCE_TREE\"", finalize)
        self.assertNotRegex(reserve, r"runner\.temp[^\n]*zenodo-reservation")
        self.assertNotRegex(finalize, r"runner\.temp[^\n]*zenodo-finalization")

    def test_workflows_pin_external_actions_by_full_sha(self) -> None:
        for path in (RESERVE, FINALIZE, ADAPTIVE_RUNTIME):
            text = path.read_text(encoding="utf-8")
            uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text)
            self.assertTrue(uses)
            for reference in uses:
                self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")

    def test_adaptive_runtime_exact_renderer_capability_is_fail_closed(self) -> None:
        text = ADAPTIVE_RUNTIME.read_text(encoding="utf-8")
        self.assertEqual(text.count("exact_renderer_optional: false"), 2)
        self.assertEqual(text.count("exact_renderer_optional: true"), 4)
        self.assertEqual(text.count("id: renderer-python"), 2)
        self.assertEqual(
            text.count("continue-on-error: ${{ matrix.exact_renderer_optional }}"),
            2,
        )
        self.assertGreaterEqual(
            text.count("steps.renderer-python.outcome == 'success'"), 12
        )
        self.assertGreaterEqual(
            text.count("steps.renderer-python.outcome == 'failure'"), 8
        )
        self.assertIn(
            "Revalidate exact POSIX renderer before cache publication", text
        )
        self.assertIn(
            "Revalidate exact Windows renderer before cache publication", text
        )
        self.assertIn("qikvrt-runtime-v4-py-3.12.13-success-", text)
        self.assertIn("qikvrt-runtime-v4-py-3.12.13-unavailable-", text)
        self.assertIn("path: .qikvrt/toolchains/gh", text)
        self.assertNotIn("restore-keys:", text)
        self.assertNotIn("enableCrossOsArchive: true", text)
        exact_restore = text[
            text.index("Restore exact renderer and GH cache") :
            text.index("Restore GH-only cache without exact renderer")
        ]
        exact_save = text[
            text.index("Save verified exact renderer and GH cache") :
            text.index("Save verified GH-only cache without exact renderer")
        ]
        for cache_step in (exact_restore, exact_save):
            self.assertIn(
                ".qikvrt/toolchains/xml2rfc/3.34.0/"
                "python-3.12.13/*/wheelhouse",
                cache_step,
            )
            self.assertNotIn("/venv", cache_step)
            self.assertNotIn("\\venv", cache_step)
        self.assertIn(
            'renderer=".qikvrt/toolchains/xml2rfc/3.34.0/'
            'python-3.12.13/$renderer_platform/venv/bin/xml2rfc"',
            text,
        )
        self.assertIn(
            "'.qikvrt\\toolchains\\xml2rfc\\3.34.0\\python-3.12.13\\"
            "windows-amd64\\venv\\Scripts\\xml2rfc.exe'",
            text,
        )
        exact_save = text.index("Save verified exact renderer and GH cache")
        posix_recheck = text.index(
            "Revalidate exact POSIX renderer before cache publication"
        )
        windows_recheck = text.index(
            "Revalidate exact Windows renderer before cache publication"
        )
        self.assertLess(posix_recheck, exact_save)
        self.assertLess(windows_recheck, exact_save)
        posix_bootstrap = (ROOT / "tools/bootstrap-gh.sh").read_text(
            encoding="utf-8"
        )
        windows_bootstrap = (ROOT / "tools/bootstrap-gh.ps1").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("gh version $VERSION (2026-07-02)", posix_bootstrap)
        self.assertNotIn("gh version $Version (2026-07-02)", windows_bootstrap)
        self.assertIn("^gh version 2\\.96\\.0", posix_bootstrap)
        self.assertIn("[regex]::Escape($Version)", windows_bootstrap)
        self.assertNotIn(
            '"gh_${Version}_windows_${Arch}\\bin\\gh.exe"',
            windows_bootstrap,
        )
        self.assertIn("Join-Path $verifyDir 'bin\\gh.exe'", windows_bootstrap)
        self.assertIn("Join-Path $ExtractDir 'bin\\gh.exe'", windows_bootstrap)

    def test_embedded_python_is_syntactically_valid(self) -> None:
        pattern = re.compile(r"python -B - <<'PY'\n(.*?)\n\s*PY(?:\n|$)", re.S)
        for path in (RESERVE, FINALIZE):
            blocks = pattern.findall(path.read_text(encoding="utf-8"))
            self.assertTrue(blocks)
            for index, block in enumerate(blocks, 1):
                lines = block.splitlines()
                indentation = min(
                    len(line) - len(line.lstrip()) for line in lines if line.strip()
                )
                source = "\n".join(
                    line[indentation:] if line.strip() else "" for line in lines
                )
                compile(source, f"{path}:embedded-python-{index}", "exec")

    def test_two_commit_parent_tree_fixture(self) -> None:
        """Prove the selector is parent A, not authorization marker HEAD B."""
        with tempfile.TemporaryDirectory(prefix="qikvrt-release-workflow-") as raw:
            repository = pathlib.Path(raw)
            run_git(repository, "init", "-q")
            run_git(repository, "config", "user.name", "QIK-VRT fixture")
            run_git(repository, "config", "user.email", "fixture@example.invalid")
            marker_path = repository / MARKER_PATH
            marker_path.parent.mkdir(parents=True)
            inert = json.loads(MARKER.read_text(encoding="utf-8"))
            marker_path.write_text(
                json.dumps(inert, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            run_git(repository, "add", MARKER_PATH)
            run_git(repository, "commit", "-q", "-m", "candidate A with inert marker")
            source_commit = run_git(repository, "rev-parse", "HEAD")
            source_tree = run_git(repository, "show", "-s", "--format=%T", "HEAD")

            active = copy.deepcopy(inert)
            active["state"] = "reserve"
            active["confirm"] = "RESERVE_ZENODO_DRAFT_ONLY_NO_PUBLISH"
            active["release"]["expected_source_commit"] = source_commit
            active["release"]["expected_source_tree"] = source_tree
            active["authorization_payload_sha256"] = "0" * 64
            projection = copy.deepcopy(active)
            projection.pop("authorization_payload_sha256")
            active["authorization_payload_sha256"] = hashlib.sha256(
                json.dumps(
                    projection,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            marker_path.write_text(
                json.dumps(active, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            run_git(repository, "add", MARKER_PATH)
            run_git(repository, "commit", "-q", "-m", "marker-only authorization B")

            self.assertEqual(run_git(repository, "rev-parse", "HEAD^"), source_commit)
            self.assertEqual(
                run_git(repository, "show", "-s", "--format=%T", "HEAD^"),
                source_tree,
            )
            self.assertNotEqual(
                run_git(repository, "show", "-s", "--format=%T", "HEAD"),
                source_tree,
            )
            self.assertEqual(
                run_git(
                    repository,
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    "HEAD^",
                    "HEAD",
                ).splitlines(),
                [MARKER_PATH],
            )
            for path in (RESERVE, FINALIZE):
                text = path.read_text(encoding="utf-8")
                self.assertIn('["git", "show", "-s", "--format=%T", "HEAD^"]', text)
                self.assertNotIn('["git", "rev-parse", "HEAD^{tree}"]', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
