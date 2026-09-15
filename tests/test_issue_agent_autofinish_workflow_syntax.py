# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/issue-agent-autofinish.yml"
PROCESSOR = ROOT / ".github/workflows/issue-autonomous-processing.yml"


class IssueAgentAutofinishWorkflowSyntaxTests(unittest.TestCase):
    @staticmethod
    def shell_for_step(path: Path, step_name: str) -> str:
        lines = path.read_text(encoding="utf-8").splitlines()
        start = lines.index(step_name)
        run = next(index for index in range(start + 1, len(lines)) if lines[index] == "        run: |")
        body: list[str] = []
        for line in lines[run + 1 :]:
            if line.strip() and len(line) - len(line.lstrip(" ")) < 10:
                break
            body.append(line[10:] if len(line) >= 10 else line)
        return "\n".join(body) + "\n"

    def test_run_block_never_escapes_yaml_scalar(self):
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        for step_name in (
            "      - name: Bind one safe issue identifier for observer serialization",
            "      - name: Bind exact open issue-agent candidates and request merge authority",
        ):
            start = lines.index(step_name)
            run = next(index for index in range(start + 1, len(lines)) if lines[index] == "        run: |")
            body = lines[run + 1 :]
            self.assertTrue(body)
            for number, line in enumerate(body, start=run + 2):
                if line.strip() and len(line) - len(line.lstrip(" ")) < 10:
                    break
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip(" "))
                self.assertGreaterEqual(
                    indent,
                    10,
                    f"workflow shell line {number} escaped run block: {line!r}",
                )

    def test_deindented_run_block_is_valid_bash(self):
        for step_name in (
            "      - name: Bind one safe issue identifier for observer serialization",
            "      - name: Bind exact open issue-agent candidates and request merge authority",
        ):
            result = subprocess.run(
                ["bash", "-n"],
                input=self.shell_for_step(WORKFLOW, step_name),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_observer_receipt_and_concurrency_are_bound_per_exact_issue_run(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "group: issue-agent-completion-authority-observer-${{ needs.bind_issue.outputs.issue_number }}",
            workflow,
        )
        self.assertIn("Bind one safe issue identifier for observer serialization", workflow)
        self.assertIn("never directly from an unvalidated dispatch input", workflow)
        self.assertIn("[[ \"$REQUESTED_ISSUE\" =~ ^[1-9][0-9]*$ ]]", workflow)
        self.assertIn("- exact head: $head_sha", workflow)
        self.assertIn("- observer workflow run: $GITHUB_RUN_ID", workflow)

    def test_exact_handoff_is_bounded_and_valid_bash(self):
        workflow = PROCESSOR.read_text(encoding="utf-8")
        self.assertIn("actions: write", workflow)
        self.assertIn("gh workflow run issue-agent-autofinish.yml", workflow)
        self.assertIn("expected_head=$EXPECTED_HEAD", workflow)
        self.assertIn("expected_pr=$EXPECTED_PR", workflow)
        self.assertNotIn("actions/runs/$candidate", workflow)
        self.assertNotIn("sleep 5", workflow)
        self.assertIn("AWAIT_EXACT_OBSERVER_RECEIPT", workflow)
        self.assertIn('pr_after="$(gh api "repos/$REPOSITORY/pulls/$EXPECTED_PR")"', workflow)
        self.assertIn('jq -r .head.sha <<<"$pr_after"', workflow)
        self.assertIn(".head.repo.full_name // empty", workflow)
        shell = self.shell_for_step(
            PROCESSOR,
            next(line for line in workflow.splitlines() if line.startswith("      - name: Dispatch ")),
        )
        result = subprocess.run(
            ["bash", "-n"],
            input=shell,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def execute_workflow_step(self, path, step, **changes):
        """Run the real shell with an API fixture that never completes a queued run."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            api = root / "gh"
            api.write_text(f"#!{sys.executable}\n" + textwrap.dedent('''\
                import json, os, pathlib, sys
                args = sys.argv[1:]
                root = pathlib.Path(os.environ["FIXTURE_ROOT"])
                with (root / "calls.jsonl").open("a") as out:
                    out.write(json.dumps(args) + "\\n")
                head = "a" * 40
                repo = "Goldkelch/qik-vrt"
                pr = {"number": 91, "state": "open", "draft": False,
                      "base": {"ref": "main", "sha": "c" * 40},
                      "head": {"ref": "issue-agent/17", "sha": head,
                               "repo": {"full_name": repo}}}
                comment = root / "comment.json"
                if args[:2] == ["workflow", "run"]:
                    (root / "dispatched").touch()
                elif args[:2] == ["pr", "list"]:
                    print(json.dumps([{"number": 91, "url": "https://github.com/Goldkelch/qik-vrt/pull/91",
                        "baseRefName": "main", "baseRefOid": "c" * 40,
                        "headRefName": "issue-agent/17", "headRefOid": head,
                        "isDraft": False, "statusCheckRollup": []}]))
                elif args and args[0] == "api":
                    endpoint = next((arg for arg in args if arg.startswith("repos/")), "")
                    if "actions/workflows/" in endpoint:
                        print('{"workflow_runs": []}')
                    elif endpoint.endswith("git/ref/heads/issue-agent/17"):
                        print(head)
                    elif endpoint.endswith("pulls/91"):
                        if os.environ.get("DRIFT") == "yes" and ((root / "dispatched").exists() or comment.exists()):
                            pr["head"]["sha"] = "b" * 40
                        if "--jq" in args:
                            print(repo)
                        else:
                            print(json.dumps(pr))
                    elif "issues/17/comments" in endpoint:
                        if "POST" in args:
                            body = json.load(sys.stdin)["body"]
                            comment.write_text(json.dumps({"id": 123, "user": {"login": "github-actions[bot]"}, "body": body}))
                            print(123)
                        # An empty lookup means there is no existing receipt.
                    elif endpoint.endswith("issues/comments/123"):
                        value = json.loads(comment.read_text())
                        if os.environ.get("CORRUPT") == "yes":
                            value["body"] = value["body"].replace(head, "b" * 40)
                        print(json.dumps(value))
                    else:
                        sys.exit("unexpected API call: " + repr(args))
                else:
                    sys.exit("unexpected gh call: " + repr(args))
                '''), encoding="utf-8")
            api.chmod(0o755)
            sleeper = root / "sleep"
            sleeper.write_text("#!/bin/sh\necho 'status polling reached a sleep' >&2\nexit 82\n")
            sleeper.chmod(0o755)
            env = {
                **os.environ, "PATH": f"{root}:/usr/bin:/bin", "FIXTURE_ROOT": str(root),
                "REPOSITORY": "Goldkelch/qik-vrt", "AUTHORITY_REPOSITORY": "Goldkelch/qik-vrt",
                "ISSUE_NUMBER": "17", "REQUESTED_ISSUE": "17", "EXPECTED_PR": "91",
                "EXPECTED_HEAD": "a" * 40, "EVENT_NAME": "workflow_dispatch",
                "EVENT_PR": "", "EVENT_HEAD_REF": "", "EVENT_HEAD_REPOSITORY": "",
                "GITHUB_RUN_ID": "9876", "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_STEP_SUMMARY": str(root / "summary"), "GITHUB_OUTPUT": str(root / "output"),
                "RUNNER_TEMP": str(root), **changes,
            }
            result = subprocess.run(["bash", "-euo", "pipefail"],
                input=self.shell_for_step(path, step), env=env, text=True,
                capture_output=True, timeout=10, check=False)
            calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
            summary = (root / "summary").read_text() if (root / "summary").exists() else ""
            return result, calls, summary

    def test_queued_observer_preserves_one_exact_handoff_without_waiting(self):
        step = next(line for line in PROCESSOR.read_text().splitlines()
                    if line.startswith("      - name: Dispatch "))
        result, calls, summary = self.execute_workflow_step(PROCESSOR, step)
        self.assertEqual(result.returncode, 0, result.stderr)
        dispatches = [call for call in calls if call[:2] == ["workflow", "run"]]
        self.assertEqual(len(dispatches), 1)
        self.assertIn("expected_pr=91", dispatches[0])
        self.assertIn("expected_head=" + "a" * 40, dispatches[0])
        self.assertFalse(any("actions/" in arg for call in calls for arg in call))
        self.assertIn("AWAIT_EXACT_OBSERVER_RECEIPT", summary)
        self.assertIn("HOLD_UNVERIFIED", summary)

    def test_handoff_rejects_head_drift_after_dispatch(self):
        step = next(line for line in PROCESSOR.read_text().splitlines()
                    if line.startswith("      - name: Dispatch "))
        result, calls, _ = self.execute_workflow_step(PROCESSOR, step, DRIFT="yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(call[:2] == ["workflow", "run"] for call in calls), 1)

    def test_delayed_observer_accepts_only_its_exact_receipt(self):
        step = "      - name: Bind exact open issue-agent candidates and request merge authority"
        result, calls, _ = self.execute_workflow_step(WORKFLOW, step)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum("POST" in call for call in calls), 1)
        self.assertFalse(any("actions/" in arg for call in calls for arg in call))

    def test_observer_rejects_wrong_pr_before_publishing(self):
        step = "      - name: Bind exact open issue-agent candidates and request merge authority"
        result, calls, _ = self.execute_workflow_step(WORKFLOW, step, EXPECTED_PR="92")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("POST" in call for call in calls))

    def test_observer_rejects_wrong_head_before_publishing(self):
        step = "      - name: Bind exact open issue-agent candidates and request merge authority"
        result, calls, _ = self.execute_workflow_step(WORKFLOW, step, EXPECTED_HEAD="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("POST" in call for call in calls))

    def test_observer_rejects_corrupt_receipt_with_unchanged_marker(self):
        step = "      - name: Bind exact open issue-agent candidates and request merge authority"
        result, calls, _ = self.execute_workflow_step(WORKFLOW, step, CORRUPT="yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum("POST" in call for call in calls), 1)

    def test_observer_rejects_head_drift_after_receipt_publication(self):
        step = "      - name: Bind exact open issue-agent candidates and request merge authority"
        result, calls, _ = self.execute_workflow_step(WORKFLOW, step, DRIFT="yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum("POST" in call for call in calls), 1)


if __name__ == "__main__":
    unittest.main()
