from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import tempfile
import unittest

from tools import qikvrt_vrtcore_zenodo_publication_controls as controls
from tools import qikvrt_zenodo_publish as publish


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_vrtcore_zenodo_publish.yml"


class VRTCoreZenodoPublicationControlTests(unittest.TestCase):
    def test_three_exact_unique_owner_decisions(self) -> None:
        self.assertEqual(set(controls.PROFILES), {"h3", "h5", "h6"})
        ids = {str(value["authorization_id"]) for value in controls.PROFILES.values()}
        self.assertEqual(len(ids), 3)
        for profile in controls.PROFILES.values():
            statement = controls.exact_statement(profile)
            self.assertTrue(statement.startswith("AUTHORIZE_EXACT_UPLOAD "))
            self.assertIn("authorization_id=" + str(profile["authorization_id"]), statement)
            self.assertIn("publication_id=" + str(profile["publication_id"]), statement)

    def test_controls_pass_active_v2_manifest_gate(self) -> None:
        for profile in controls.PROFILES.values():
            control = ROOT / str(profile["control"])
            manifest = publish.load_manifest(control / "publish-request.json", ROOT)
            self.assertEqual(manifest["source_head"], controls.SOURCE_HEAD)
            self.assertEqual(len(manifest["files"]), profile["upload_count"])
            self.assertEqual(
                manifest["owner_authorization"]["authorization_id"],
                profile["authorization_id"],
            )
            self.assertFalse((control / "zenodo-publication.json").exists())

    def test_single_use_nonces_are_distinct_without_exposing_values(self) -> None:
        digests = set()
        for profile in controls.PROFILES.values():
            control = ROOT / str(profile["control"])
            value = json.loads(
                (control / "OWNER_ZENODO_AUTHORIZATION.json").read_text(encoding="utf-8")
            )
            nonce = value["nonce"]
            self.assertEqual(len(nonce), 64)
            self.assertNotEqual(nonce, "0" * 64)
            normalized = publish.load_manifest(control / "publish-request.json", ROOT)
            digests.add(normalized["owner_authorization"]["nonce_digest"]["value"])
        self.assertEqual(len(digests), 3)

    def test_missing_control_refuses_replacement_single_use_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = pathlib.Path(directory) / "OWNER_ZENODO_AUTHORIZATION.json"
            with self.assertRaisesRegex(
                SystemExit,
                "replacement nonce generation is forbidden",
            ):
                controls.read_preserved_event(missing)

    def test_workflow_has_only_the_three_static_push_triggers(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        trigger = raw[raw.index("on:\n") : raw.index("\npermissions:\n")]
        self.assertEqual(trigger.count("  push:\n"), 1)
        self.assertIn("    branches:\n", trigger)
        self.assertIn("    paths:\n", trigger)
        for branch in (
            "publication/vrtcore-relational-h3-v1",
            "publication/vrtcore-smg-h5-v1",
            "publication/vrtcore-virtual-sphere-h6-v1",
        ):
            self.assertIn("      - " + branch + "\n", trigger)
        self.assertIn(
            "      - .github/workflows/qikvrt_vrtcore_zenodo_publish.yml\n",
            trigger,
        )
        for forbidden in (
            "workflow_dispatch",
            "repository_dispatch",
            "pull_request",
            "pull_request_target",
            "schedule:",
            "create:",
        ):
            self.assertNotIn(forbidden, trigger)

    def test_workflow_is_fail_closed_and_causally_ordered(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("if: github.repository == 'Goldkelch/qik-vrt'", raw)
        self.assertIn("contents: write", raw)
        self.assertIn(
            "group: qikvrt-vrtcore-causal-zenodo-publication-v1",
            raw,
        )
        self.assertIn("cancel-in-progress: false", raw)
        parent_match = re.search(r"^      EXPECTED_PARENT: (\S+)$", raw, re.MULTILINE)
        self.assertIsNotNone(parent_match)
        assert parent_match is not None
        parent = parent_match.group(1)
        self.assertTrue(
            parent == "__EXPECTED_PARENT_COMMIT_SHA__"
            or re.fullmatch(r"[0-9a-f]{40}", parent) is not None
        )
        self.assertIn(
            'if ! [[ "$EXPECTED_PARENT" =~ ^[0-9a-f]{40}$ ]]',
            raw,
        )
        self.assertIn(
            'test "$(git show -s --format=%P HEAD)" = "$EXPECTED_PARENT"',
            raw,
        )
        self.assertGreaterEqual(
            raw.count('test "$main_head" = "$EXPECTED_PARENT"'),
            2,
        )
        self.assertIn('"h5": ("h3",)', raw)
        self.assertIn('"h6": ("h3", "h5")', raw)
        self.assertIn(
            "BLOCK: causally prior published receipt is absent from main parent",
            raw,
        )
        self.assertIn(
            "BLOCK: predecessor execution is not an ancestor of main parent",
            raw,
        )
        self.assertNotIn("PREDECESSOR_BRANCH", raw)

    def test_workflow_binds_exact_execution_deltas(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        for line in (
            "'A\t.github/workflows/qikvrt_vrtcore_zenodo_publish.yml'",
            "'M\t.github/workflows/qikvrt_vrtcore_zenodo_publish.yml'",
            "'M\tREPOSITORY_FILE_MANIFEST.json'",
            "'M\tREPOSITORY_FILE_MANIFEST.json.sha256'",
            "'M\tSHA256SUMS.txt'",
            "'M\ttests/test_vrtcore_zenodo_publication_controls.py'",
        ):
            self.assertIn(line, raw)
        self.assertIn("--name-status", raw)
        self.assertIn("--no-renames", raw)
        self.assertIn('test "$observed_delta" = "$expected_delta"', raw)
        self.assertIn(
            "python3 -B tools/qikvrt_vrtcore_zenodo_publication_controls.py --check",
            raw,
        )
        self.assertIn("make test", raw)

    def test_workflow_limits_secret_and_requires_published_receipt(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        github_token = "${{ github.token }}"
        zenodo_token = "${{ secrets.ZENODO_ACCESS_TOKEN }}"
        self.assertEqual(raw.count(github_token), 2)
        self.assertEqual(raw.count(zenodo_token), 1)
        publish_start = raw.index(
            "      - name: Consume authorization and publish exact files\n"
        )
        persist_start = raw.index(
            "      - name: Prepare exact published or recovery receipt tree\n"
        )
        receipt_effect_start = raw.index(
            "      - name: Persist exact receipt through GitHub Git Data REST\n"
        )
        artifact_start = raw.index(
            "      - name: Upload publication recovery evidence\n"
        )
        self.assertNotIn(github_token, raw[:publish_start])
        self.assertIn(github_token, raw[publish_start:persist_start])
        self.assertNotIn(github_token, raw[persist_start:receipt_effect_start])
        self.assertIn(github_token, raw[receipt_effect_start:artifact_start])
        self.assertNotIn(github_token, raw[artifact_start:])
        self.assertIn(zenodo_token, raw[publish_start:persist_start])
        self.assertNotIn(zenodo_token, raw[:publish_start])
        self.assertNotIn(zenodo_token, raw[persist_start:])
        self.assertIn("persist-credentials: false", raw)
        self.assertNotIn("persist-credentials: true", raw)
        self.assertIn('if key != "GITHUB_TOKEN"', raw)
        self.assertIn("continue-on-error: true", raw[publish_start:persist_start])
        effect = raw[publish_start:persist_start]
        self.assertIn("for attempt in 1 2 3; do", effect)
        self.assertEqual(effect.count("sleep 5"), 1)
        self.assertIn(
            "publisher failed before durable V2 recovery evidence; no retry",
            effect,
        )
        self.assertIn(
            "publisher recovery evidence failed validation; no retry",
            effect,
        )
        self.assertIn("retry refuses immutable legacy v1 evidence", effect)
        self.assertIn("retry requires V2 recovery evidence", effect)
        self.assertIn("publish._validate_recovery_evidence(", effect)
        self.assertIn(
            "printf 'attempts=%s\\n' \"$attempt\" >> \"$GITHUB_OUTPUT\"",
            effect,
        )
        self.assertIn("if: always()", raw[persist_start:])
        self.assertIn("publish.EVIDENCE_SCHEMA_V2", raw)
        self.assertIn("publish._validate_recovery_evidence(", raw)
        self.assertIn(
            "graceful recovery receipt must not use immutable v1 evidence",
            raw,
        )
        self.assertIn(
            'not in {"NEWLY_CREATED_REF", "EXISTING_EXACT_REF_NO_CREATE"}',
            raw,
        )
        self.assertIn('evidence["binding"]["consumption_key"]', raw)
        self.assertIn('evidence["governance_boundaries"]', raw)
        self.assertIn("list(publish.GOVERNANCE_BOUNDARIES)", raw)
        self.assertIn(
            'test "${{ steps.persist.outputs.phase }}" = "public_verified"',
            raw,
        )
        self.assertIn(
            'test "${{ steps.persist.outputs.state }}" = "published"',
            raw,
        )
        self.assertNotIn('test "$status" = "2"', raw)
        self.assertIn(
            'test "${{ steps.push.outputs.persisted }}" = "true"',
            raw,
        )
        self.assertIn(
            'test "${{ steps.publish.outputs.status }}" = "0"',
            raw,
        )

    def test_actions_are_pinned_and_receipt_effect_uses_git_data_rest(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        uses = re.findall(r"^        uses: ([^ #]+)", raw, re.MULTILINE)
        self.assertEqual(
            uses,
            [
                "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            ],
        )
        for endpoint in ("git/blobs", "git/trees", "git/commits", "git/refs"):
            self.assertIn(endpoint, raw)
        self.assertIn('method not in {"GET", "POST", "PATCH"}', raw)
        self.assertIn('payload={"sha": receipt_commit, "force": False}', raw)
        self.assertNotIn('"force": True', raw)
        self.assertNotIn('"DELETE"', raw)
        self.assertNotIn("git push", raw)
        self.assertNotIn("--force", raw)
        self.assertNotIn("--force-with-lease", raw)
        self.assertNotIn("+refs/", raw)

    def test_recovery_ref_preserves_execution_head_until_public_verified(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            '"qikvrt-recovery/vrtcore-zenodo/"',
            raw,
        )
        self.assertIn(
            "Restore validated recovery receipt without moving execution head",
            raw,
        )
        self.assertIn('git fetch --no-tags origin "$RECOVERY_REF"', raw)
        self.assertIn(
            'git show "$recovery_head:$EVIDENCE_PATH" > "$EVIDENCE_PATH"',
            raw,
        )
        self.assertIn("BLOCK: recovery commit delta differs", raw)
        self.assertIn("BLOCK: recovery phases regress", raw)
        self.assertIn("BLOCK: recovery branch contains public evidence", raw)
        self.assertIn(
            'test "$(git rev-parse --verify HEAD^{commit})" = "$GITHUB_SHA"',
            raw,
        )
        self.assertIn('"parents": [parent]', raw)
        self.assertIn('"base_tree": base_tree', raw)
        self.assertIn("receipt_storage=recovery", raw)
        self.assertIn("receipt_storage=publication", raw)

    def test_receipt_commit_is_exact_parent_bound_and_revalidated(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("BLOCK: GitHub receipt commit readback differs", raw)
        self.assertIn("BLOCK: receipt commit delta differs", raw)
        self.assertIn("BLOCK: credential-free receipt blob differs", raw)
        self.assertIn("BLOCK: receipt phase regresses from recovery parent", raw)
        self.assertGreaterEqual(raw.count("publish._validate_recovery_evidence("), 5)
        self.assertIn(
            'python3 -B -m unittest -v \\\n'
            "            tests.test_vrtcore_zenodo_publication_controls",
            raw,
        )
        snapshot_test = raw.index(
            "python3 -B -m unittest -v \\\n"
            "            tests.test_vrtcore_zenodo_publication_controls"
        )
        effect = raw.index("Consume authorization and publish exact files")
        self.assertLess(snapshot_test, effect)

    def test_git_data_ref_races_and_rewrites_are_fail_closed(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        effect_start = raw.index(
            "      - name: Persist exact receipt through GitHub Git Data REST\n"
        )
        effect_end = raw.index(
            "      - name: Verify persisted receipt without credentials\n"
        )
        effect = raw[effect_start:effect_end]
        self.assertIn("BLOCK: recovery ref already exists before create", raw)
        self.assertIn("BLOCK: receipt target disappeared before update", raw)
        self.assertIn("BLOCK: publication ref moved before receipt effect", raw)
        self.assertIn("BLOCK: recovery ref moved before receipt effect", raw)
        self.assertIn("BLOCK: recovery ref appeared before receipt effect", raw)
        self.assertIn("BLOCK: credential-free target ref differs", raw)
        self.assertIn('accept=(200, 404)', raw)
        self.assertIn('operation == "create"', raw)
        self.assertIn('operation not in {"create", "update"}', raw)
        self.assertIn('payload={"ref": target_ref, "sha": receipt_commit}', raw)
        self.assertIn('payload={"sha": receipt_commit, "force": False}', raw)
        self.assertIn("class AmbiguousRefMutation", effect)
        self.assertIn("500 <= status <= 599", effect)
        self.assertIn("The mutation request is never retried", effect)
        self.assertIn("REST_PATCH_FORCE_FALSE_IS_FF_NOT_EXPECTED_OLD_CAS", effect)
        self.assertEqual(
            effect.count('"/repos/Goldkelch/qik-vrt/git/refs",'),
            1,
        )
        self.assertEqual(effect.count('"PATCH",\n'), 1)

    def test_token_effect_is_embedded_deterministic_and_read_back_twice(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        start = raw.index(
            "      - name: Persist exact receipt through GitHub Git Data REST\n"
        )
        end = raw.index(
            "      - name: Verify persisted receipt without credentials\n"
        )
        effect = raw[start:end]
        self.assertNotIn("from tools import", effect)
        self.assertNotIn("import tools", effect)
        self.assertNotIn("subprocess", effect)
        self.assertIn('effect_date = os.environ["RECEIPT_DATE"]', effect)
        self.assertNotIn("datetime.now", effect)
        self.assertIn("BLOCK: deterministic receipt date differs", effect)
        self.assertIn("BLOCK: GitHub receipt parent binding differs", effect)
        self.assertIn("BLOCK: GitHub receipt parent tree differs", effect)
        self.assertIn("BLOCK: GitHub receipt tree readback differs", effect)
        self.assertIn("post_ref_commit", effect)
        self.assertIn("post_ref_tree", effect)
        self.assertIn("final_ref_readback", effect)
        self.assertIn("reconciliation_status", effect)

    def test_finalized_state_is_read_only_and_rejects_divergence(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        finalized = raw.index("Detect and verify an already finalized publication")
        publisher = raw.index("Consume authorization and publish exact files")
        receipt_effect = raw.index("Persist exact receipt through GitHub Git Data REST")
        self.assertLess(finalized, publisher)
        self.assertLess(finalized, receipt_effect)
        self.assertGreaterEqual(
            raw.count("if: env.ALREADY_FINALIZED != 'true'"),
            5,
        )
        for rejection in (
            "BLOCK: final receipt parent differs",
            "BLOCK: final receipt delta differs",
            "BLOCK: finalized receipt path mode differs",
            "BLOCK: finalized integrity manifest differs",
            "BLOCK: final receipt diverges from recovery tip",
            "BLOCK: final remote consumption ref differs",
            "BLOCK: final public record identity differs",
            "BLOCK: final public file set differs",
        ):
            self.assertIn(rejection, raw)
        self.assertIn("VRTCORE_ALREADY_FINALIZED=VALID", raw)
        self.assertIn('test -z "${{ steps.publish.outputs.status }}"', raw)
        self.assertIn('test -z "${{ steps.push.outputs.receipt_commit }}"', raw)

    def test_recovery_chain_rejects_modes_integrity_and_identity_changes(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        for rejection in (
            "BLOCK: recovery receipt path mode differs",
            "BLOCK: recovery integrity manifest differs",
            "BLOCK: recovery SHA256 index differs",
            "BLOCK: recovery detached digest differs",
            "BLOCK: recovery consumption identity changes",
            "BLOCK: recovery record identity changes",
            "BLOCK: recovery phases regress",
        ):
            self.assertIn(rejection, raw)
        self.assertIn('left >= right for left, right in zip', raw)
        self.assertIn('len(publish.RECOVERY_PHASES) - 1', raw)

    def test_every_bash_run_block_parses(self) -> None:
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        scripts: list[str] = []
        index = 0
        while index < len(lines):
            if lines[index] != "        run: |":
                index += 1
                continue
            index += 1
            body: list[str] = []
            while index < len(lines):
                line = lines[index]
                if line and not line.startswith("          "):
                    break
                body.append(line[10:] if line.startswith("          ") else "")
                index += 1
            scripts.append("\n".join(body) + "\n")
        self.assertEqual(len(scripts), 12)
        for number, script in enumerate(scripts, 1):
            normalized = re.sub(r"\$\{\{.*?\}\}", "GITHUB_EXPRESSION", script)
            result = subprocess.run(
                ["bash", "-n"],
                input=normalized,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=f"bash run block {number} failed syntax: {result.stderr}",
            )

    def test_every_embedded_python_block_parses(self) -> None:
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        blocks: list[str] = []
        index = 0
        while index < len(lines):
            if "<<'PY'" not in lines[index]:
                index += 1
                continue
            index += 1
            body: list[str] = []
            while index < len(lines) and lines[index] != "          PY":
                line = lines[index]
                if line:
                    self.assertTrue(line.startswith("          "))
                    body.append(line[10:])
                else:
                    body.append("")
                index += 1
            self.assertLess(index, len(lines), "unterminated embedded Python block")
            blocks.append("\n".join(body) + "\n")
            index += 1
        self.assertEqual(len(blocks), 11)
        for number, block in enumerate(blocks, 1):
            try:
                ast.parse(block)
            except SyntaxError as exc:
                self.fail(f"embedded Python block {number} failed syntax: {exc}")


if __name__ == "__main__":
    unittest.main()
