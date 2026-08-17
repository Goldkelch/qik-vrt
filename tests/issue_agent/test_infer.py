import os
import subprocess
import unittest
from unittest import mock

from scripts.issue_agent import infer


class InferRouterTests(unittest.TestCase):
    def test_build_prompt_binds_issue_and_context(self):
        prompt = infer.build_prompt(
            {"number": 661, "title": "Titel", "body": "Koerper"},
            "REPO-CONTEXT",
        )
        self.assertIn("ISSUE #661", prompt)
        self.assertIn("TITLE: Titel", prompt)
        self.assertIn("Koerper", prompt)
        self.assertIn("REPO-CONTEXT", prompt)
        self.assertIn("Never claim PASS", prompt)

    @mock.patch("scripts.issue_agent.infer.subprocess.run")
    def test_copilot_success_returns_answer_and_disables_tools(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["copilot"], returncode=0, stdout="# Repository answer\nOK\n", stderr=""
        )
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}, clear=True):
            answer = infer.run_copilot("prompt", "auto")
        self.assertEqual(answer, "# Repository answer\nOK\n")
        argv = run.call_args.args[0]
        self.assertIn("--model=auto", argv)
        self.assertTrue(any(a.startswith("--excluded-tools=") for a in argv))
        env = run.call_args.kwargs["env"]
        self.assertEqual(env["COPILOT_GITHUB_TOKEN"], "token")
        self.assertEqual(env["COPILOT_AUTO_UPDATE"], "false")

    def test_missing_authentication_fails_closed(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "authentication token"):
                infer.run_copilot("prompt", "auto")

    @mock.patch("scripts.issue_agent.infer.subprocess.run")
    def test_provider_failure_fails_closed(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["copilot"], returncode=7, stdout="", stderr="provider unavailable"
        )
        with mock.patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "token"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
                infer.run_copilot("prompt", "auto")

    @mock.patch("scripts.issue_agent.infer.subprocess.run")
    def test_empty_provider_output_fails_closed(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["copilot"], returncode=0, stdout="   ", stderr=""
        )
        with mock.patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "token"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "empty answer"):
                infer.run_copilot("prompt", "auto")


if __name__ == "__main__":
    unittest.main()
