#!/usr/bin/env python3
import pathlib
import re
import subprocess
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_mesh_review_successor_completion.yml"


class MeshReviewSuccessorCompletionWorkflowTests(unittest.TestCase):
    def test_trusted_recovery_only_triggers_and_fifo_serialization(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('workflows: ["QIKVRT requested review executor"]', text)
        self.assertIn("  schedule:\n", text)
        self.assertIn("  workflow_dispatch:\n", text)
        self.assertNotIn("pull_request_target:", text)
        self.assertNotIn("pull_request_review:", text)
        self.assertIn("permissions: {}", text)
        self.assertIn(
            "group: qikvrt-mesh-review-successor-completion-${{ github.repository }}",
            text,
        )
        self.assertGreaterEqual(text.count("queue: max"), 3)
        self.assertNotIn("actions/checkout@v", text)
        self.assertNotIn("          ref: main", text)
        self.assertEqual(text.count("ref: ${{ github.workflow_sha }}"), 5)

    def test_reader_observer_and_writer_credentials_are_separated(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        starts = {
            name: text.index(f"  {name}:\n")
            for name in (
                "read-mesh-frontier",
                "observe-mesh-child",
                "persist-cursor-or-accept-orphan",
                "terminalize-mesh-orphan",
                "persist-mesh-completion",
            )
        }
        ordered = sorted(starts, key=starts.get)
        blocks = {}
        for index, name in enumerate(ordered):
            end = starts[ordered[index + 1]] if index + 1 < len(ordered) else len(text)
            blocks[name] = text[starts[name] : end]
        self.assertIn(
            "secrets.QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN",
            blocks["read-mesh-frontier"],
        )
        self.assertNotIn(
            "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN",
            blocks["read-mesh-frontier"],
        )
        self.assertNotIn("secrets.", blocks["observe-mesh-child"])
        reader = blocks["read-mesh-frontier"]
        self.assertLess(
            reader.index("unset LEDGER_AUDITOR_TOKEN LEDGER_WRITER_ACTOR_ID"),
            reader.index('mkdir -p "$root"'),
        )
        for name in (
            "persist-cursor-or-accept-orphan",
            "terminalize-mesh-orphan",
            "persist-mesh-completion",
        ):
            with self.subTest(job=name):
                self.assertIn(
                    "environment: qikvrt-outbox-ledger-authority", blocks[name]
                )
                self.assertIn(
                    "secrets.QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", blocks[name]
                )
                self.assertNotIn(
                    "secrets.QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", blocks[name]
                )
                self.assertIn(
                    "group: qikvrt-outbox-ledger-v2-mesh-review-successor-dispatch",
                    blocks[name],
                )
                self.assertLess(
                    blocks[name].index(
                        "unset LEDGER_WRITER_TOKEN LEDGER_WRITER_ACTOR_ID"
                    ),
                    blocks[name].index('test "$(git rev-parse HEAD)"'),
                )
        self.assertNotIn(": write", blocks["read-mesh-frontier"])
        self.assertNotIn(": write", blocks["observe-mesh-child"])
        self.assertNotIn(": write", blocks["persist-cursor-or-accept-orphan"])
        self.assertNotIn(": write", blocks["terminalize-mesh-orphan"])
        self.assertNotIn(": write", blocks["persist-mesh-completion"])

    def test_completion_consumer_does_not_compete_for_zero_job_rerun_authority(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("ADMISSION_ZERO_JOB_RECOVERY", text)
        self.assertNotIn("prepare-child-rerun", text)
        self.assertNotIn("accept-child-rerun", text)
        self.assertNotIn("/rerun", text)
        self.assertIn("materialize_mesh_retry_scan_cursor", text)
        self.assertIn("record-retry-scan-cursor", text)
        self.assertIn("materialize_mesh_orphan_authority_observation", text)
        self.assertIn("materialize_mesh_target_workflow_supersession", text)
        self.assertIn("materialize_mesh_subject_supersession", text)
        self.assertNotIn("action='TARGET_WORKFLOW_SUPERSEDED'", text)
        self.assertIn('"OUTBOX_TARGET_WORKFLOW_SUPERSEDED"', (
            ROOT / "tools/qikvrt_mesh_review_outbox.py"
        ).read_text(encoding="utf-8"))
        terminal = text[text.index("  terminalize-mesh-orphan:\n") :]
        self.assertIn(
            'if test "$EFFECTIVE_BLOCKER" = OUTBOX_SUBJECT_SUPERSEDED;',
            terminal,
        )
        self.assertIn(
            ".observed_subject != $item[0].intent.payload.subject", terminal
        )
        self.assertIn(
            '"repos/$REPOSITORY/git/commits/$observed_head"', terminal
        )
        self.assertIn("record-observation --lane mesh-review-successor-dispatch", text)
        self.assertIn("TERMINALIZE_ORPHAN", text)
        self.assertIn("prepared['cas'].get('appended') is not True", (
            ROOT / ".github/workflows/qikvrt_requested_review_executor.yml"
        ).read_text(encoding="utf-8"))
        self.assertIn("materialize_mesh_completion", text)
        self.assertIn("materialize_mesh_completion_query_bound_observation", text)
        self.assertIn("materialize_mesh_missing_evidence_observation", text)
        self.assertIn("MESH_REVIEW_COMPLETION_BOUNDED_PAGE_INVALID", text)
        self.assertNotIn("COMPLETION_ARTIFACT_NOT_EXACT", text)
        self.assertIn("complete --lane mesh-review-successor-dispatch", text)
        self.assertIn("terminalize --lane mesh-review-successor-dispatch", text)
        self.assertIn("MESH_COMPLETION_CURSOR_PAGE_INVALID", text)
        self.assertIn("declared_total_count=page_value.get('total_count')", text)
        self.assertIn(
            "declared_total_count=declared_total_count,", text
        )
        self.assertIn(
            '"MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT"',
            (ROOT / "tools/qikvrt_mesh_review_outbox.py").read_text(
                encoding="utf-8"
            ),
        )
        self.assertIn("MESH_COMPLETION_CHILD_LOCATOR_DRIFT", text)
        self.assertNotIn("DISPATCH_ATTEMPT_2", text)
        self.assertNotIn("prepare-transport --lane mesh-review-successor-dispatch --attempt 2", text)
        self.assertLess(
            text.index("started=datetime.datetime.now"),
            text.index("window_end=("),
        )
        self.assertIn("started if boundary_complete", text)
        self.assertIn("queried_window_start=window_start", text)
        self.assertIn("queried_window_end=window_end", text)

    def test_every_embedded_python_block_compiles(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        blocks = re.findall(
            r"python3 -B - <<'PY'[^\n]*\n(.*?)\n\s+PY(?:\n|$)",
            text,
            flags=re.DOTALL,
        )
        self.assertGreaterEqual(len(blocks), 2)
        for index, raw in enumerate(blocks):
            lines = raw.splitlines()
            indentation = min(
                len(line) - len(line.lstrip()) for line in lines if line.strip()
            )
            source = "\n".join(line[indentation:] for line in lines) + "\n"
            with self.subTest(block=index):
                compile(source, f"mesh-completion-embedded-{index}.py", "exec")

    def test_yaml_and_every_bash_block_parse(self):
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        scripts = [
            step["run"]
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if isinstance(step.get("run"), str)
        ]
        self.assertGreaterEqual(len(scripts), 7)
        for index, script in enumerate(scripts):
            with self.subTest(block=index):
                subprocess.run(
                    ["bash", "-n"],
                    input=script,
                    text=True,
                    check=True,
                    capture_output=True,
                )

    def test_cursor_and_adoption_effect_env_is_set_u_complete(self):
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        job = workflow["jobs"]["persist-cursor-or-accept-orphan"]
        script = next(
            step["run"]
            for step in job["steps"]
            if step.get("name")
            == "Persist one cursor ordinal or the unique adopted child"
        )
        referenced = set(re.findall(r"\$\{?(EFFECTIVE_[A-Z_]+)", script))
        self.assertEqual(referenced, {"EFFECTIVE_ACTION", "EFFECTIVE_BLOCKER"})
        self.assertTrue(referenced.issubset(job["env"]))
        for action in ("CURSOR", "ADOPT"):
            with self.subTest(action=action):
                subprocess.run(
                    [
                        "bash",
                        "-ceu",
                        ': "$EFFECTIVE_ACTION" "$EFFECTIVE_BLOCKER"',
                    ],
                    env={
                        "EFFECTIVE_ACTION": action,
                        "EFFECTIVE_BLOCKER": "",
                    },
                    check=True,
                    capture_output=True,
                    text=True,
                )


if __name__ == "__main__":
    unittest.main()
