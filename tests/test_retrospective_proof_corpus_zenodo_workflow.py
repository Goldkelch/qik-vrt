from __future__ import annotations

import pathlib
import re
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_PATH = (
    ROOT
    / ".github"
    / "workflows"
    / "qikvrt_retrospective_proof_corpus_zenodo_publish.yml"
)
WORKFLOW = WORKFLOW_PATH.read_text(encoding="utf-8")

CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
BASIS = "c556382c89d32faf7bdd193d8e58c4a190ebc3cc"
SOURCE_HEAD = "035642a660583113ec739d90577193ccb5a08889"
BRANCH = "publication/retrospective-proof-corpus-v3"
CONTROL_ROOT = "release/zenodo-corpus-proof-publication-2026-08-03"
RECOVERY_TOOL = "tools/qikvrt_retrospective_proof_corpus_zenodo_recovery.py"

EXECUTION_DELTA = (
    (
        "A",
        ".github/workflows/qikvrt_retrospective_proof_corpus_mirror_finalize.yml",
    ),
    (
        "A",
        ".github/workflows/"
        "qikvrt_retrospective_proof_corpus_zenodo_publish.yml",
    ),
    ("M", "REPOSITORY_FILE_MANIFEST.json"),
    ("M", "REPOSITORY_FILE_MANIFEST.json.sha256"),
    ("M", "SHA256SUMS.txt"),
    ("A", f"{CONTROL_ROOT}/OWNER_ZENODO_AUTHORIZATION.json"),
    ("A", f"{CONTROL_ROOT}/publish-request.json"),
    ("A", "tests/test_retrospective_proof_corpus_mirror_finalize.py"),
    ("A", "tests/test_retrospective_proof_corpus_zenodo_recovery.py"),
    ("A", "tests/test_retrospective_proof_corpus_zenodo_workflow.py"),
    ("A", "tools/qikvrt_retrospective_proof_corpus_mirror_finalize.py"),
    ("A", RECOVERY_TOOL),
)


def between(value: str, start: str, end: str) -> str:
    begin = value.index(start)
    finish = value.index(end, begin + len(start))
    return value[begin:finish]


def job(name: str, next_name: str | None) -> str:
    start = f"\n  {name}:\n"
    begin = WORKFLOW.index(start) + 1
    if next_name is None:
        return WORKFLOW[begin:]
    finish = WORKFLOW.index(f"\n  {next_name}:\n", begin)
    return WORKFLOW[begin:finish]


def step(job_text: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    begin = job_text.index(marker)
    next_step = job_text.find("\n      - name: ", begin + len(marker))
    return job_text[begin:] if next_step < 0 else job_text[begin:next_step]


VERIFY = job("verify", "publish")
PUBLISH = job("publish", "post_public_verify")
POST = job("post_public_verify", None)


class RetrospectiveProofCorpusZenodoWorkflowTests(unittest.TestCase):
    maxDiff = None

    def test_trigger_is_only_the_exact_publication_branch(self) -> None:
        observed = between(WORKFLOW, "on:\n", "\npermissions: {}")
        expected = """on:
  push:
    branches:
      - publication/retrospective-proof-corpus-v3
    paths:
      - .github/workflows/qikvrt_retrospective_proof_corpus_zenodo_publish.yml
      - release/zenodo-corpus-proof-publication-2026-08-03/OWNER_ZENODO_AUTHORIZATION.json
      - release/zenodo-corpus-proof-publication-2026-08-03/publish-request.json
  workflow_dispatch:
"""
        self.assertEqual(observed, expected)
        for forbidden in (
            "pull_request:",
            "pull_request_target:",
            "schedule:",
            "workflow_run:",
            "repository_dispatch:",
            "branches-ignore:",
            "tags:",
        ):
            self.assertNotIn(forbidden, observed)
        self.assertNotIn("- main", observed)

    def test_permissions_jobs_runner_and_dependency_chain_are_exact(self) -> None:
        self.assertEqual(WORKFLOW.count("permissions: {}"), 1)
        self.assertEqual(WORKFLOW.count("\n    permissions:\n"), 3)
        self.assertEqual(
            WORKFLOW.count("    permissions:\n      contents: read\n"), 2
        )
        self.assertEqual(
            WORKFLOW.count("    permissions:\n      contents: write\n"), 1
        )
        jobs_text = WORKFLOW[WORKFLOW.index("jobs:\n") :]
        self.assertEqual(
            re.findall(r"(?m)^  ([a-z][a-z0-9_]*):$", jobs_text),
            ["verify", "publish", "post_public_verify"],
        )
        self.assertIn("    permissions:\n      contents: read\n", VERIFY)
        self.assertIn("    permissions:\n      contents: write\n", PUBLISH)
        self.assertIn("    permissions:\n      contents: read\n", POST)
        self.assertNotIn("needs:", VERIFY)
        self.assertIn("    needs: verify\n", PUBLISH)
        self.assertIn("    needs: publish\n", POST)
        self.assertEqual(WORKFLOW.count("    runs-on: ubuntu-24.04\n"), 3)
        self.assertNotIn("ubuntu-latest", WORKFLOW)

    def test_concurrency_is_non_cancelling_and_all_actions_are_full_sha(self) -> None:
        self.assertIn(
            "concurrency:\n"
            "  group: qikvrt-retrospective-proof-corpus-zenodo-v3\n"
            "  cancel-in-progress: false\n",
            WORKFLOW,
        )
        self.assertNotIn("cancel-in-progress: true", WORKFLOW)
        actions = re.findall(
            r"(?m)^\s+uses: ([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s#]+)",
            WORKFLOW,
        )
        self.assertEqual(actions, [("actions/checkout", CHECKOUT_SHA)] * 3)
        for _action, revision in actions:
            self.assertRegex(revision, r"\A[0-9a-f]{40}\Z")

    def test_every_job_starts_from_a_fresh_credential_free_checkout(self) -> None:
        self.assertEqual(WORKFLOW.count("Fresh checkout"), 3)
        self.assertEqual(WORKFLOW.count("          fetch-depth: 0\n"), 3)
        self.assertEqual(WORKFLOW.count("          persist-credentials: false\n"), 3)
        self.assertNotIn("persist-credentials: true", WORKFLOW)
        self.assertIn("          ref: ${{ github.sha }}\n", VERIFY)
        self.assertIn("          ref: ${{ github.sha }}\n", PUBLISH)
        self.assertIn(f"          ref: refs/heads/{BRANCH}\n", POST)

    def test_frozen_candidate_authorization_and_contract_pins_are_literal(self) -> None:
        pins = {
            "EXPECTED_REPOSITORY": "Goldkelch/qik-vrt",
            "EXPECTED_BRANCH": BRANCH,
            "EXPECTED_BASIS": BASIS,
            "SOURCE_HEAD": SOURCE_HEAD,
            "PUBLICATION_ID": "qikvrt-retrospective-proof-corpus-2026-07-28-v3",
            "AUTHORIZATION_ID": (
                "qikvrt-retrospective-proof-corpus-v3-rebuild-20260803t094446z"
            ),
            "RETURN_SHA256": (
                "46c57378a6708df379768f943a99905cde3da4c4a11220f9a177e9bc968d3968"
            ),
            "METADATA_SHA256": (
                "4bb6abea1f226f3950337ee3585abd1ba5d52f731a93f25fabfc2722f5b170de"
            ),
            "MACHINE_PROOF_SHA256": (
                "cfe9ae60e3da81a6427c96399bd70299c74f12999dc4371809b879f5a5630be1"
            ),
            "UPLOAD_CONTRACT_SHA256": (
                "3965b4167094ff47de60fc32023ac74ea1598148ab381885be8da3db4c427609"
            ),
            "RECOVERY_TOOL": RECOVERY_TOOL,
        }
        for key, value in pins.items():
            self.assertEqual(WORKFLOW.count(f"  {key}: {value}\n"), 1, key)

    def test_execution_envelope_accepts_only_initial_or_valid_final_head(self) -> None:
        for job_text in (VERIFY, PUBLISH):
            self.assertIn('event_head="$(git rev-parse --verify HEAD^{commit})"', job_text)
            self.assertIn('test "$event_head" = "$GITHUB_SHA"', job_text)
            self.assertIn('execution_head="${branch_commits[0]}"', job_text)
            self.assertIn(
                'test "$(git show -s --format=%P "$execution_head")" = '
                '"$EXPECTED_BASIS"',
                job_text,
            )
            self.assertIn(
                'test "$(git rev-list --count '
                '"$EXPECTED_BASIS..$execution_head")" = "1"',
                job_text,
            )
            self.assertIn('git checkout --detach "$execution_head"', job_text)
        self.assertIn('if test "$remote_head" = "$execution_head"; then', VERIFY)
        self.assertIn('test "$GITHUB_EVENT_NAME" = "workflow_dispatch"', VERIFY)
        self.assertIn('finalized_rerun=true', VERIFY)
        self.assertIn('FINALIZED_RERUN_RECOVERY_CHAIN=PASS', VERIFY)
        self.assertIn('GITHUB_SHA="$EXECUTION_HEAD"', VERIFY)
        self.assertIn('GITHUB_SHA="$execution_head"', PUBLISH)
        self.assertIn(
            'GITHUB_SHA="$EXECUTION_HEAD" python3 -B "$RECOVERY_TOOL"',
            PUBLISH,
        )
        initial_delta = between(
            VERIFY,
            '          expected_delta="$(\n',
            '          observed_delta="$(\n',
        )
        observed = tuple(
            re.findall(r"(?m)^\s+'([AM])\t([^']+)'", initial_delta)
        )
        self.assertEqual(observed, EXECUTION_DELTA)
        self.assertIn(
            '"$EXPECTED_BASIS" "$execution_head" --',
            VERIFY,
        )
        self.assertNotIn('test "$GITHUB_RUN_ATTEMPT" = "1"', WORKFLOW)
        self.assertGreaterEqual(WORKFLOW.count('test ! -e "$EVIDENCE_PATH"'), 3)
        self.assertEqual(
            WORKFLOW.count(
                'git ls-remote --heads origin "refs/heads/$EXPECTED_BRANCH"'
            ),
            3,
        )
        self.assertIn('event.get("forced") is not False', VERIFY)
        self.assertIn('event.get("deleted") is True', VERIFY)
        self.assertIn('event.get("after") != os.environ["GITHUB_SHA"]', VERIFY)
        self.assertIn(
            'repository.get("full_name") != os.environ["EXPECTED_REPOSITORY"]',
            VERIFY,
        )

    def test_failed_push_rerun_and_final_dispatch_are_both_fail_closed(self) -> None:
        for job_text in (VERIFY, PUBLISH):
            for required in (
                'if test "$event_head" != "$execution_head"; then',
                'test "$event_head" = "$remote_head"',
                'if test "$remote_head" != "$event_head"; then',
                'test "$event_head" = "$execution_head"',
                'receipt_head="$remote_head"',
                'test "${#recovery_commits[@]}" -le 135',
                "recovery.validate_recovery_chain",
                'values[-1]["phase"] != "publish_requested"',
                "exact_remote_ref(context.recovery_ref)",
                "recovery_head != receipt_parent",
                "recovery.validate_ref_state",
            ):
                self.assertIn(required, job_text)
            self.assertIn(
                "git fetch \\\n"
                "              --no-tags \\\n"
                "              --no-write-fetch-head",
                job_text,
            )
        self.assertIn('if test "$remote_head" = "$execution_head"; then', VERIFY)
        self.assertIn('test "$GITHUB_EVENT_NAME" = "workflow_dispatch"', VERIFY)
        self.assertIn("FINALIZED_RERUN_RECOVERY_CHAIN=PASS", VERIFY)
        self.assertIn('if test "$remote_head" != "$execution_head"; then', PUBLISH)
        self.assertIn("PRE_EFFECT_FINALIZED_RECOVERY_CHAIN=PASS", PUBLISH)

    def test_read_only_contract_gates_precede_the_dedicated_controller(self) -> None:
        for required in (
            "controls.SOURCE_HEAD",
            "controls.PUBLICATION_ID",
            "controls.AUTHORIZATION_ID",
            "controls.RETURN_SHA256",
            "controls.METADATA_SHA256",
            "controls.MACHINE_PROOF_SHA256",
            "controls.UPLOAD_CONTRACT_SHA256",
            'contract.get("entry_count") != 65',
            "candidate.canonical_json_sha256(entries)",
            "raw_pairs != contract_pairs",
            "publish.load_manifest",
            "publish._validate_repository_source_head",
            "publish._validate_origin_repository",
            'normalized.get("owner_authorization", {}).get("upload_count") != 65',
        ):
            self.assertIn(required, VERIFY)
        for path_variable in (
            'os.environ["MANIFEST_PATH"]',
            'os.environ["AUTHORIZATION_PATH"]',
            'os.environ["EVIDENCE_PATH"]',
        ):
            self.assertIn(path_variable, VERIFY)
        self.assertEqual(WORKFLOW.count('python3 -B "$RECOVERY_TOOL" --check'), 2)
        self.assertEqual(
            WORKFLOW.count(
                'python3 -B "$RECOVERY_TOOL" \\\n            --execute \\\n            --github-output "$GITHUB_OUTPUT"'
            ),
            1,
        )
        self.assertNotIn("tools/qikvrt_zenodo_publish.py", WORKFLOW)
        self.assertNotIn("publish.publish(", WORKFLOW)
        self.assertNotIn("_resume_publication", WORKFLOW)
        self.assertNotIn("_recover_create_requested_record", WORKFLOW)
        self.assertIn(
            "tests.test_retrospective_proof_corpus_zenodo_recovery", VERIFY
        )
        self.assertIn(
            "tests.test_retrospective_proof_corpus_mirror_finalize", VERIFY
        )
        self.assertLess(
            PUBLISH.index('python3 -B "$RECOVERY_TOOL" --check'),
            PUBLISH.index("--execute"),
        )

    def test_tokens_are_confined_to_execute_and_public_ref_bootstrap(self) -> None:
        execute = step(
            PUBLISH,
            "Execute the dedicated checkpointed publication controller once",
        )
        bootstrap = step(
            POST,
            "Bootstrap the create-only Authority public ref after the complete byte gate",
        )
        self.assertEqual(WORKFLOW.count("${{ secrets.ZENODO_ACCESS_TOKEN }}"), 1)
        self.assertEqual(WORKFLOW.count("${{ github.token }}"), 1)
        self.assertEqual(WORKFLOW.count("${{ secrets.QIKVRT_MESH_TOKEN }}"), 1)
        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}\n", execute)
        self.assertIn(
            "          ZENODO_ACCESS_TOKEN: ${{ secrets.ZENODO_ACCESS_TOKEN }}\n",
            execute,
        )
        self.assertIn(
            "          QIKVRT_MESH_TOKEN: ${{ secrets.QIKVRT_MESH_TOKEN }}\n",
            bootstrap,
        )
        self.assertIn("          ZENODO_API_BASE: https://zenodo.org/api\n", execute)
        self.assertIn("        continue-on-error: true\n", execute)
        without_execute = PUBLISH.replace(execute, "")
        self.assertNotIn("${{ github.token }}", without_execute)
        self.assertNotIn("${{ secrets.", without_execute)
        self.assertNotIn("${{ github.token }}", VERIFY + POST)
        self.assertNotIn("${{ secrets.", VERIFY + POST.replace(bootstrap, ""))
        self.assertNotIn("ZENODO_ACCESS_TOKEN: ${{", bootstrap)
        self.assertNotIn("GITHUB_TOKEN: ${{", bootstrap)
        self.assertNotIn("GH_TOKEN: ${{", bootstrap)
        self.assertEqual(
            re.findall(r"(?m)^          ([A-Z][A-Z0-9_]*): ", between(
                bootstrap, "        env:\n", "        run: |\n"
            )),
            ["QIKVRT_MESH_TOKEN"],
        )
        self.assertGreaterEqual(WORKFLOW.count('test -z "${ZENODO_ACCESS_TOKEN:-}"'), 5)
        self.assertIn('test "${{ steps.recovery.outcome }}" = "success"', PUBLISH)
        self.assertIn(
            'test "${{ steps.recovery.outputs.phase }}" = "public_verified"',
            PUBLISH,
        )
        self.assertIn(
            'test "${{ steps.recovery.outputs.finalized }}" = "true"',
            PUBLISH,
        )

    def test_no_pr_schedule_artifact_handoff_or_direct_git_effect_exists(self) -> None:
        for forbidden in (
            "actions/upload-artifact@",
            "actions/download-artifact@",
            "actions/cache@",
            "runner.temp",
            "\n    outputs:",
            "git push ",
            "--force",
            "force-with-lease",
        ):
            self.assertNotIn(forbidden, WORKFLOW)

    def test_post_public_job_validates_the_exact_checkpoint_chain_and_integrity(self) -> None:
        self.assertIn(
            f"  RECOVERY_PATH: {CONTROL_ROOT}/zenodo-recovery.json\n", WORKFLOW
        )
        for required in (
            'git merge-base --is-ancestor "$EXECUTION_HEAD" "$receipt_head"',
            'git rev-list --merges "$EXECUTION_HEAD..$receipt_head"',
            '"$EXECUTION_HEAD..$receipt_parent"',
            "zenodo: persist retrospective proof corpus recovery",
            "zenodo: persist retrospective proof corpus publication",
            'test "$chain_parent" = "$receipt_parent"',
            'test "${#recovery_commits[@]}" -le 135',
            'test "$recovery_delta" = "A\t$RECOVERY_PATH"',
            'test "$recovery_delta" = "M\t$RECOVERY_PATH"',
            'git diff --name-status --no-renames "$receipt_parent" "$receipt_head" --',
            'git diff --name-status --no-renames "$EXECUTION_HEAD" "$receipt_head" --',
            "python3 -B tools/qikvrt_integrity.py verify",
            'test "$remote_head" = "$receipt_head"',
            "recovery.validate_recovery_chain",
            'values[-1]["phase"] != "publish_requested"',
            'values[-1]["sequence"] != len(values) - 1',
            "recovery.validate_ref_state",
            "exact_remote_ref(context.recovery_ref)",
            "recovery_head != receipt_parent",
            "POST_PUBLIC_RECOVERY_CHAIN=PASS",
        ):
            self.assertIn(required, POST)
        final_delta = between(
            POST,
            '          expected_final_delta="$(\n',
            '          observed_final_delta="$(\n',
        )
        self.assertEqual(
            tuple(re.findall(r"(?m)^\s+'([AM])\t([^']+)'", final_delta)),
            (
                ("M", "REPOSITORY_FILE_MANIFEST.json"),
                ("M", "REPOSITORY_FILE_MANIFEST.json.sha256"),
                ("M", "SHA256SUMS.txt"),
                ("A", f"{CONTROL_ROOT}/zenodo-publication.json"),
            ),
        )
        cumulative = between(
            POST,
            '          expected_cumulative_delta="$(\n',
            '          observed_cumulative_delta="$(\n',
        )
        self.assertEqual(
            tuple(re.findall(r"(?m)^\s+'([AM])\t([^']+)'", cumulative)),
            (
                ("M", "REPOSITORY_FILE_MANIFEST.json"),
                ("M", "REPOSITORY_FILE_MANIFEST.json.sha256"),
                ("M", "SHA256SUMS.txt"),
                ("A", f"{CONTROL_ROOT}/zenodo-publication.json"),
                ("A", f"{CONTROL_ROOT}/zenodo-recovery.json"),
            ),
        )

    def test_post_public_verification_is_anonymous_bounded_and_byte_exact(self) -> None:
        for required in (
            "urllib.request.ProxyHandler({})",
            "RejectRedirects",
            "return None",
            'parts.scheme != "https"',
            'parts.hostname != "zenodo.org"',
            "parts.username is not None",
            "parts.query",
            "maximum + 1 - total",
            'f"https://zenodo.org/api/records/{record_id}"',
            "zenodo._published_metadata_matches",
            "zenodo.ZenodoClient._server_files",
            'set(by_name) != {item["name"] for item in manifest["files"]}',
            'raw_size != expected["size"]',
            "aggregate > 512 * 1024 * 1024",
            "hashlib.md5(raw, usedforsecurity=False).hexdigest()",
            "hashlib.sha256(raw).hexdigest()",
            "PUBLIC_FILE_COUNT=65",
            "ANONYMOUS_PUBLIC_BYTE_EXACT_VERIFY=PASS",
        ):
            self.assertIn(required, POST)
        self.assertNotIn("SameZenodoRedirect", POST)
        self.assertNotIn("host.endswith", POST)
        self.assertNotIn("ZENODO_ACCESS_TOKEN: ${{", POST)
        self.assertNotIn("GITHUB_TOKEN: ${{", POST)

    def test_public_ref_bootstrap_is_last_and_remains_continue_only(self) -> None:
        byte_gate = step(
            POST,
            "Independently verify anonymous public metadata and all 65 file bytes",
        )
        bootstrap = step(
            POST,
            "Bootstrap the create-only Authority public ref after the complete byte gate",
        )
        self.assertLess(POST.index(byte_gate), POST.index(bootstrap))
        self.assertEqual(POST.rstrip().endswith(bootstrap.rstrip()), True)
        self.assertIn("ANONYMOUS_PUBLIC_BYTE_EXACT_VERIFY=PASS", byte_gate)
        self.assertIn("PUBLIC_FILE_COUNT=65", byte_gate)
        self.assertIn(
            "python3 -B tools/qikvrt_retrospective_proof_corpus_mirror_finalize.py \\\n"
            "            --bootstrap-authority-public-ref | tee \"$bootstrap_report\"",
            bootstrap,
        )
        self.assertIn('test -z "${ZENODO_ACCESS_TOKEN:-}"', bootstrap)
        self.assertIn('test -z "${GITHUB_TOKEN:-}"', bootstrap)
        self.assertIn('test -z "${GH_TOKEN:-}"', bootstrap)
        self.assertIn('test "$receipt_head" = "$RECEIPT_HEAD"', bootstrap)
        self.assertIn('done_state = "EFFECT_ACK_" + "DONE"', bootstrap)
        self.assertIn('done_state.encode("ascii") in raw', bootstrap)
        self.assertIn(
            'report.get("effect_state") != "EFFECT_ACK_CONTINUE"', bootstrap
        )
        self.assertIn("AUTHORITY_PUBLIC_REF_BOOTSTRAP=PASS", bootstrap)
        self.assertIn("EFFECT_STATE=EFFECT_ACK_CONTINUE", bootstrap)
        self.assertNotIn("EFFECT_ACK_DONE", bootstrap)

    def test_effect_state_never_claims_done(self) -> None:
        self.assertNotIn("EFFECT_ACK_DONE", WORKFLOW)
        self.assertGreaterEqual(WORKFLOW.count("EFFECT_ACK_CONTINUE"), 2)
        self.assertIn(
            "Authority/Mirror reciprocal persistence remains a separate required effect.",
            POST,
        )

    def test_embedded_python_and_bash_are_statically_well_formed(self) -> None:
        lines = WORKFLOW.splitlines()
        python_blocks: list[str] = []
        index = 0
        while index < len(lines):
            if "python3 -B - <<'PY'" not in lines[index]:
                index += 1
                continue
            finish = index + 1
            while finish < len(lines) and lines[finish].strip() != "PY":
                finish += 1
            self.assertLess(finish, len(lines), "unterminated Python heredoc")
            body_lines = lines[index + 1 : finish]
            normalized = [
                line[10:] if line else ""
                for line in body_lines
            ]
            for line in body_lines:
                if line:
                    self.assertTrue(line.startswith(" " * 10))
            source = "\n".join(normalized) + "\n"
            compile(source, f"{WORKFLOW_PATH.name}:heredoc-{len(python_blocks) + 1}", "exec")
            python_blocks.append(source)
            index = finish + 1
        self.assertEqual(len(python_blocks), 8)

        bash_blocks: list[str] = []
        index = 0
        while index < len(lines):
            if lines[index] != "        run: |":
                index += 1
                continue
            finish = index + 1
            while finish < len(lines):
                line = lines[finish]
                indentation = len(line) - len(line.lstrip(" "))
                if line and indentation <= 8:
                    break
                finish += 1
            body = "\n".join(
                line[10:] if line else "" for line in lines[index + 1 : finish]
            )
            body = re.sub(r"\$\{\{[^\n}]+\}\}", "STATIC_EXPRESSION", body)
            checked = subprocess.run(
                ["bash", "-n"],
                input=body + "\n",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            bash_blocks.append(body)
            index = finish
        self.assertGreaterEqual(len(bash_blocks), 8)


if __name__ == "__main__":
    unittest.main()
