import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPILER = ROOT / "scripts/issue_agent/compile.py"


class DeterministicIssueCompilerTest(unittest.TestCase):
    def compile(self, issue):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "issue.json", root / "answer.md"
            source.write_text(json.dumps(issue), encoding="utf-8")
            subprocess.run(["python3", str(COMPILER), "--issue", str(source), "--context", str(source), "--output", str(output)], check=True)
            return output.read_text(encoding="utf-8")

    def test_ruleset_app_request_holds_for_explicit_authority_setup(self):
        answer = self.compile({"title": "ruleset", "body": "GitHub App authority"})
        self.assertIn("MISSING_GITHUB_APP_RULESET_AUTHORITY", answer)
        self.assertIn("BLOCKED_WITH_NEXT_ACTION", answer)

    def test_unknown_request_never_invents_a_patch(self):
        answer = self.compile({"title": "invent something", "body": ""})
        self.assertIn("UNSUPPORTED_DETERMINISTIC_WORK_UNIT", answer)

