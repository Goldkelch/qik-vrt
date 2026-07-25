import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.issue_agent.validate import validate


class ValidateIssueAgentBundleTest(unittest.TestCase):
    def make_bundle(self, directory: Path) -> None:
        request = json.dumps({"issue_number": 76}, sort_keys=True) + "\n"
        (directory / "REQUEST.json").write_text(request, encoding="utf-8")
        digest = hashlib.sha256(request.encode()).hexdigest()
        (directory / "REQUEST.sha256").write_text(f"{digest}  REQUEST.json\n", encoding="utf-8")
        (directory / "CONTEXT.md").write_text("context\n", encoding="utf-8")
        (directory / "ANSWER.md").write_text("answer\n", encoding="utf-8")
        (directory / "STATUS.json").write_text(json.dumps({
            "status": "CONTINUE",
            "automatic_merge": False,
            "no_false_pass": True,
        }), encoding="utf-8")

    def test_valid_bundle_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            validate(directory)

    def test_automatic_merge_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["automatic_merge"] = True
            status_path.write_text(json.dumps(status), encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate(directory)


if __name__ == "__main__":
    unittest.main()
