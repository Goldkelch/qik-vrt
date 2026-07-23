#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Structural regression tests for the formalization-v2 release protocol."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_formalization_v2_zenodo.yml"
MARKER = ROOT / "release/formalization-v2-request.json"
MANIFEST = ROOT / "release/formalization-v2-zenodo.json"
CLIENT = ROOT / "tools/qikvrt_formalization_v2_zenodo.py"
SHARED_CLIENT = ROOT / "tools/qikvrt_zenodo_actions.py"
CLIENT_TEST = ROOT / "tests/test_formalization_v2_zenodo.py"
ARCHIVE = ROOT / "release/formalization-v2/QIKVRT_Formalization_v2.0-alpha.1.zip"
EFFECT = (
    ROOT
    / "formalization/QIKVRT_Formalization_v2.0/release_authorization/EFFECT_ACK_DONE.json"
)
MAKEFILE = ROOT / "Makefile"
INSPECTION_WORKFLOW = ROOT / ".github/workflows/qikvrt_formalization_v2_inspect.yml"
INSPECTION_MARKER = ROOT / "release/formalization-v2-inspection-request.json"
INVENTORY_WORKFLOW = ROOT / ".github/workflows/qikvrt_formalization_v2_inventory.yml"
INVENTORY_MARKER = ROOT / "release/formalization-v2-inventory-request.json"
RECOVERY_EVIDENCE = ROOT / "release/formalization-v2-draft-recovery.json"
DIRECT_INVENTORY = ROOT / "release/formalization-v2-direct-draft-inventory.json"
PUBLICATION_RESULT = ROOT / "release/formalization-v2-zenodo-publication.json"
INDEPENDENT_VERIFICATION = (
    ROOT / "release/formalization-v2-zenodo-independent-verification.json"
)
PUBLICATION_PROVENANCE = ROOT / "release/formalization-v2-publication-provenance.json"
PUBLICATION_WHATSAPP = ROOT / "release/FORMALIZATION_V2_PUBLICATION_WHATSAPP_DE.md"
AUTOMATION_BRANCH = "automation/formalization-v2-publish-20260723-v5"
FEATURE_BRANCH = "agent/manuscript-formalization-v2-alpha"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def embedded_python(workflow: str, step_name: str) -> str:
    start = workflow.index(f"      - name: {step_name}")
    next_step = workflow.find("\n      - name:", start + 1)
    block = workflow[start:] if next_step < 0 else workflow[start:next_step]
    match = re.search(
        r"python -I -S -B - <<'PY'\n(.*?)\n\s*PY(?:\n|$)", block, re.S
    )
    if match is None:
        raise AssertionError(f"workflow step has no isolated embedded Python: {step_name}")
    lines = match.group(1).splitlines()
    indentation = min(
        len(line) - len(line.lstrip()) for line in lines if line.strip()
    )
    return "\n".join(
        line[indentation:] if line.strip() else "" for line in lines
    )


class FormalizationV2ReleaseWorkflowTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.marker = json.loads(MARKER.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_trigger_is_one_inert_marker_on_one_authority_branch(self) -> None:
        trigger = self.workflow.split("permissions:", 1)[0]
        self.assertIn(f"      - {AUTOMATION_BRANCH}\n", trigger)
        self.assertNotIn("formalization-v2-publish-20260723-v4", trigger)
        self.assertIn("      - release/formalization-v2-request.json\n", trigger)
        self.assertNotIn(FEATURE_BRANCH, trigger)
        self.assertNotIn("workflow_dispatch", self.workflow)
        self.assertNotIn("repository_dispatch", self.workflow)
        self.assertNotRegex(self.workflow, r"(?m)^\s*pull_request(?:_target)?:")
        self.assertIn("github.repository == 'Goldkelch/qik-vrt'", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_candidate_marker_is_closed_and_inert(self) -> None:
        self.assertEqual(
            set(self.marker),
            {"schema", "request_id", "state", "confirm", "candidate", "bindings"},
        )
        self.assertEqual(
            self.marker["schema"],
            "qikvrt_formalization_v2_publication_request_v1",
        )
        self.assertEqual(
            self.marker["request_id"], "2026-07-23-formalization-v2.0-alpha.1"
        )
        self.assertEqual(self.marker["state"], "inactive")
        self.assertEqual(self.marker["confirm"], "NOT_AUTHORIZED")
        candidate = self.marker["candidate"]
        self.assertEqual(candidate["authority_repository"], "Goldkelch/qik-vrt")
        self.assertEqual(candidate["mirror_repository"], "ingolf-lohmann/qik-vrt")
        self.assertEqual(candidate["feature_branch"], FEATURE_BRANCH)
        for key in ("candidate_commit", "candidate_tree", "mirror_commit", "mirror_tree"):
            self.assertEqual(candidate[key], "0" * 40)
        self.assertEqual(
            set(self.marker["bindings"]),
            {
                "effect_ack_sha256",
                "manifest_sha256",
                "client_sha256",
                "shared_client_sha256",
                "client_test_sha256",
                "workflow_sha256",
                "recovery_evidence_sha256",
                "direct_inventory_sha256",
                "archive_sha256",
            },
        )
        for value in self.marker["bindings"].values():
            self.assertEqual(value, "0" * 64)

    def test_inert_marker_executes_without_network_and_cannot_authorize(self) -> None:
        source = embedded_python(
            self.workflow, "Validate inert or marker-only publication request"
        )
        with tempfile.TemporaryDirectory(prefix="qikvrt-inert-marker-output-") as raw:
            output = pathlib.Path(raw) / "github-output"
            environment = {
                "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                "GITHUB_SHA": "a" * 40,
                "GITHUB_OUTPUT": os.fspath(output),
                "GH_API_TOKEN": "offline-unused-token",
                "EVENT_AFTER": "a" * 40,
                "EVENT_BEFORE": "0" * 40,
                "EVENT_FORCED": "false",
                "EVENT_REF": "refs/heads/" + AUTOMATION_BRANCH,
            }
            with mock.patch.dict(os.environ, environment, clear=False), mock.patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("inactive marker attempted network access"),
            ), mock.patch("pathlib.Path.cwd", return_value=ROOT), mock.patch(
                "os.getcwd", return_value=os.fspath(ROOT)
            ):
                previous = pathlib.Path.cwd()
                os.chdir(ROOT)
                try:
                    with self.assertRaises(SystemExit) as stopped:
                        exec(compile(source, "<formalization-v2-marker>", "exec"), {})
                finally:
                    os.chdir(previous)
            self.assertEqual(stopped.exception.code, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "authorized=false\n")

    def test_finalize_protocol_binds_parent_diff_bases_mirror_and_all_mutators(self) -> None:
        required = (
            'state != "finalize"',
            'PUBLISH_ZENODO_FORMALIZATION_V2_ALPHA_1',
            'changes != ["M\\t" + MARKER_PATH]',
            'git("show", "-s", "--format=%P", "HEAD^").split() != [AUTHORITY_CANDIDATE_PARENT]',
            'candidate["candidate_tree"] != candidate["mirror_tree"]',
            'd037a44d2893b9ea094d7cad55954223eb90a186',
            '7aaee4e1b182e18c9f0e927685f31d3c1190031a',
            '3aa271ab38c022232b744dbac2faa64c3bafd74d',
            '9b3f87ed1fdd642137387d0892de9ea533bc709f',
            '69b19b6e3b0da8cf2c279222f761e2c810089b41',
            'af6762da33e19f3a1525b3a726eabc70994542b0',
            '6d6d1866779f1d907b8a33d1515f951d7cbd2a81',
            '6d14ac019cde5be15ea12fd6993e015efd041d26',
            '9624466b84dc785d9bc6d18ff6b3c0966de89684',
            '661b9ecd66bd91d1359e3d47ab77a8991522b662',
            'f45b713bddbb6377e0f3ebb3cb2061235f41ceb4',
            '8d39c93b738ac53ea952f8d8dda78aea973961cd',
            '48a9f2c642ed6fb22daa4d841f606d33d5b65c37',
            '7d4f6238063eb18c56cef8d03f111b7ddc1530a1',
            'ed4f61fb4f09043eb8683932a1fed5222ad524f7',
            'c9a7bcabebd66768f2f728d8b35a9317c5ea7323',
            '00e71ed364b388727aafea133122eda02c046692',
            'AUTHORITY_ANCESTRY',
            'MIRROR_ANCESTRY',
            'fetch-depth: 8',
            'git checkout --detach "${{ steps.marker.outputs.candidate_commit }}"',
            'EVENT_BEFORE',
            'EVENT_FORCED',
        )
        for text in required:
            self.assertIn(text, self.workflow)
        paths = {
            "effect_ack_sha256": EFFECT,
            "manifest_sha256": MANIFEST,
            "client_sha256": CLIENT,
            "shared_client_sha256": SHARED_CLIENT,
            "client_test_sha256": CLIENT_TEST,
            "workflow_sha256": WORKFLOW,
            "recovery_evidence_sha256": RECOVERY_EVIDENCE,
            "direct_inventory_sha256": DIRECT_INVENTORY,
            "archive_sha256": ARCHIVE,
        }
        for key, path in paths.items():
            self.assertIn(f'"{key}": "{path.relative_to(ROOT).as_posix()}"', self.workflow)
        self.assertGreaterEqual(self.workflow.count("remote_head("), 3)
        self.assertIn("authority feature branch moved before effect", self.workflow)
        self.assertIn("mirror feature branch moved before effect", self.workflow)

    def test_effect_ack_and_truthful_partial_scope_are_hard_gates(self) -> None:
        for value in (
            "ICH AKZEPTIERE",
            "NATURAL_PERSON",
            "Ingolf Lohmann",
            "partial formalization with explicit boundaries",
            "publish a new version of formalization concept 10.5281/zenodo.21488115",
            "EFFECT_ACK_DONE",
        ):
            self.assertIn(value, self.workflow)
        self.assertIn('software.get("source_record_id") != 21498774', self.workflow)
        self.assertIn('software.get("concept_record_id") != 21488115', self.workflow)
        self.assertIn('software.get("metadata", {}).get("version") != "2.0.0-alpha.1"', self.workflow)

    def test_secret_boundary_is_isolated_and_followed_by_anonymous_verification(self) -> None:
        self.assertEqual(self.workflow.count("secrets.ZENODO_ACCESS_TOKEN"), 2)
        self.assertNotIn("access_token=", self.workflow.lower())
        publish = self.workflow.index(
            "Publish the exact new Zenodo version through the isolated client"
        )
        anonymous = self.workflow.index(
            "Independently verify anonymous public Zenodo metadata and bytes"
        )
        reject = self.workflow.index(
            "Reject secret-bearing or incomplete publication evidence"
        )
        recheck = self.workflow.index(
            "Revalidate candidate bytes and both remote branch heads before effect"
        )
        self.assertLess(recheck, publish)
        self.assertLess(publish, anonymous)
        self.assertLess(anonymous, reject)
        anonymous_block = self.workflow[anonymous:reject]
        self.assertNotIn("ZENODO_ACCESS_TOKEN", anonymous_block)
        self.assertNotIn("from tools", anonymous_block)
        self.assertIn('"anonymous": True', anonymous_block)
        self.assertIn("source_latest_verified", anonymous_block)
        self.assertIn("hashlib.sha256(raw).hexdigest()", anonymous_block)
        publish_block = self.workflow[publish:anonymous]
        self.assertIn("python -I -S -B -", publish_block)
        self.assertIn("runpy.run_path", publish_block)

    def test_actions_are_immutable_and_workflow_never_writes_repository_refs(self) -> None:
        uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", self.workflow)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"@(?:[0-9a-f]{40}|[0-9a-f]{64})$")
        for forbidden in ("git push", "gh pr", "gh release", "contents: write"):
            self.assertNotIn(forbidden, self.workflow)

    def test_draft_inspection_is_inert_read_only_and_hash_bound(self) -> None:
        inspection = INSPECTION_WORKFLOW.read_text(encoding="utf-8")
        marker = json.loads(INSPECTION_MARKER.read_text(encoding="utf-8"))
        self.assertEqual(marker["state"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertTrue(all(value == "0" * 64 for value in marker["bindings"].values()))
        self.assertIn("automation/formalization-v2-inspect-20260723", inspection)
        self.assertIn("release/formalization-v2-inspection-request.json", inspection)
        self.assertIn("INSPECT_ZENODO_FORMALIZATION_V2_DRAFT_READ_ONLY", inspection)
        self.assertIn('["M\\t" + MARKER]', inspection)
        self.assertIn('method="GET"', inspection)
        for method in ('method="POST"', 'method="PUT"', 'method="PATCH"', 'method="DELETE"'):
            self.assertNotIn(method, inspection)
        uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", inspection)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"@(?:[0-9a-f]{40}|[0-9a-f]{64})$")

    def test_recovery_evidence_and_inventory_are_exact_and_read_only(self) -> None:
        inventory = INVENTORY_WORKFLOW.read_text(encoding="utf-8")
        marker = json.loads(INVENTORY_MARKER.read_text(encoding="utf-8"))
        evidence = json.loads(RECOVERY_EVIDENCE.read_text(encoding="utf-8"))
        direct = json.loads(DIRECT_INVENTORY.read_text(encoding="utf-8"))
        client = CLIENT.read_text(encoding="utf-8")
        self.assertEqual(marker["state"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertTrue(all(value == "0" * 64 for value in marker["bindings"].values()))
        self.assertIn("automation/formalization-v2-inventory-20260723", inventory)
        self.assertIn("INSPECT_ZENODO_FORMALIZATION_V2_DEPOSITIONS_READ_ONLY", inventory)
        self.assertIn('method="GET"', inventory)
        for method in ('method="POST"', 'method="PUT"', 'method="PATCH"', 'method="DELETE"'):
            self.assertNotIn(method, inventory)
        self.assertEqual(
            evidence["schema"],
            "qikvrt_formalization_v2_draft_recovery_evidence_v1",
        )
        self.assertTrue(evidence["read_only"])
        recovery = evidence["recovery_draft"]
        self.assertEqual(recovery["record_id"], 21501365)
        self.assertEqual(recovery["concept_record_id"], 21488115)
        self.assertEqual(recovery["prereserved_doi"], "10.5281/zenodo.21501365")
        self.assertEqual(recovery["file_count"], 3)
        self.assertEqual(recovery["collection_view_file_count"], 0)
        self.assertEqual(
            [(item["name"], item["size"], item["md5"]) for item in recovery["files"]],
            list(release_file_fingerprint := (
                (
                    "qik-vrt-effect-ack-source-export-provenance.json",
                    1082,
                    "898967a157d5b54c4959037d4a4bb876",
                ),
                (
                    "qik-vrt-v2026.07.22-effect-ack-universality-1.0.0-source.tar.gz",
                    102094416,
                    "645eb72d099a303da91ce37ceb3e95bf",
                ),
                (
                    "qik-vrt-v2026.07.22-effect-ack-universality-1.0.0-source.tar.gz.sha256",
                    130,
                    "e786e1e10f859d1960519930438532e9",
                ),
            )),
        )
        self.assertEqual(
            [
                (item["name"], item["size"], item["checksum"])
                for item in direct["direct_recovery"]["files"]
            ],
            list(release_file_fingerprint),
        )
        self.assertEqual(sha256(DIRECT_INVENTORY), "84445c480c3bd54d2587a3210b5eb95de6774ad2c9a5dbb36c7299582cfa4355")
        self.assertEqual(
            evidence["direct_inventory"]["inventory_json_sha256"],
            sha256(DIRECT_INVENTORY),
        )
        self.assertIn(str(recovery["record_id"]), client)
        self.assertIn(recovery["created"], client)
        self.assertIn(recovery["metadata_sha256"], client)
        boundary = evidence["failed_publication"]["effect_boundary"]
        self.assertTrue(boundary["newversion_post_reached"])
        self.assertFalse(boundary["metadata_put_reached"])
        self.assertFalse(boundary["file_delete_or_upload_reached"])
        self.assertFalse(boundary["publish_post_reached"])

    def test_release_tests_are_part_of_root_test_and_candidate_workflow(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        for module in (
            "tests.test_formalization_v2_release_workflow",
            "tests.test_formalization_v2_zenodo",
        ):
            self.assertIn(module, makefile)
            self.assertIn(module, self.workflow)
        self.assertIn("tools/qikvrt_formalization_v2_zenodo.py", makefile)

    def test_persisted_publication_evidence_is_exact_and_truthful(self) -> None:
        publication = json.loads(PUBLICATION_RESULT.read_text(encoding="utf-8"))
        independent = json.loads(
            INDEPENDENT_VERIFICATION.read_text(encoding="utf-8")
        )
        provenance = json.loads(PUBLICATION_PROVENANCE.read_text(encoding="utf-8"))
        note = PUBLICATION_WHATSAPP.read_text(encoding="utf-8")
        self.assertEqual(
            publication["schema"], "qikvrt_formalization_v2_zenodo_result_v1"
        )
        self.assertEqual(
            independent["schema"],
            "qikvrt_formalization_v2_zenodo_independent_verification_v1",
        )
        self.assertEqual(publication["published_record_id"], 21501365)
        self.assertEqual(publication["doi"], "10.5281/zenodo.21501365")
        self.assertEqual(publication["files"], independent["files"])
        self.assertTrue(publication["published_by_this_run"])
        self.assertTrue(publication["public_record_verified"])
        self.assertTrue(independent["anonymous"])
        self.assertTrue(independent["source_latest_verified"])
        manifest_files = [
            {
                "name": item["name"],
                "size": item["size"],
                "md5": item["md5"],
                "sha256": item["sha256"],
            }
            for item in self.manifest["software"]["files"]
        ]
        self.assertEqual(publication["files"], manifest_files)
        self.assertEqual(
            provenance["artifact"]["publication_json_sha256"],
            sha256(PUBLICATION_RESULT),
        )
        self.assertEqual(
            provenance["artifact"]["independent_verification_json_sha256"],
            sha256(INDEPENDENT_VERIFICATION),
        )
        self.assertEqual(provenance["workflow"]["run_id"], 29971603518)
        self.assertEqual(provenance["publication"]["verified_file_count"], 14)
        self.assertIn("https://doi.org/10.5281/zenodo.21501365", note)
        self.assertIn("beweist nicht", note)
        self.assertIn("partielle, quellengebundene Lean‑4‑Formalisierung", note)

    def test_manifest_continues_only_live_latest_concept_version(self) -> None:
        software = self.manifest["software"]
        self.assertEqual(software["source_record_id"], 21498774)
        self.assertEqual(software["concept_record_id"], 21488115)
        self.assertEqual(software["metadata"]["version"], "2.0.0-alpha.1")
        archive = next(
            item
            for item in software["files"]
            if item["name"] == "QIKVRT_Formalization_v2.0-alpha.1.zip"
        )
        self.assertEqual(archive["sha256"], sha256(ARCHIVE))
        self.assertEqual(
            archive["sha256"],
            "7cfa6851256bc5bdd9f5cb18ed7760d732dac2544a9f3a5ca514abade3a7825b",
        )


if __name__ == "__main__":
    unittest.main()
