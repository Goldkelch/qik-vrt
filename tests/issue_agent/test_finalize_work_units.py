import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


finalize = load_module(ROOT / "scripts" / "issue_agent" / "finalize.py", "issue_agent_finalize")


class FinalizeWorkUnitsTest(unittest.TestCase):
    def test_failed_inference_runs_deterministic_units_and_promotes_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tools").mkdir(parents=True)
            shutil.copy2(ROOT / "tools" / "issue_agent_work_units.py", root / "tools" / "issue_agent_work_units.py")
            issue_dir = root / "evidence" / "issues" / "79"
            issue_dir.mkdir(parents=True)
            (root / "zenodo-metadata.json").write_text('{"doi":"10.0000/example"}\n', encoding="utf-8")
            (root / "source.txt").write_text("source\n", encoding="utf-8")

            aggregate = finalize.run_deterministic_fallback(issue_dir)

            self.assertEqual(aggregate["status"], "EFFECT_ACK_CONTINUE")
            self.assertFalse(aggregate["automatic_merge"])
            self.assertEqual(aggregate["next_cursor"], "CLAIM_EXTRACTION_QUEUE")
            self.assertEqual(aggregate["fallback_mode"], "deterministic_work_units")

            canonical = json.loads((issue_dir / "STATUS.json").read_text(encoding="utf-8"))
            state = json.loads((issue_dir / "work-units" / "STATE.json").read_text(encoding="utf-8"))
            by_name = {unit["name"]: unit for unit in state["units"]}
            self.assertEqual(by_name["ZENODO_RECORD_DISCOVERY"]["status"], "DONE")
            self.assertEqual(by_name["ARTIFACT_FILE_INVENTORY"]["status"], "DONE")
            self.assertEqual(by_name["SOURCE_HASH_BINDING"]["status"], "DONE")
            self.assertEqual(by_name["CLAIM_EXTRACTION_QUEUE"]["status"], "BLOCK")
            self.assertEqual(canonical["status"], "EFFECT_ACK_CONTINUE")

    def test_coarse_success_never_enables_automatic_merge(self):
        status = finalize.coarse_status(succeeded=True)
        self.assertEqual(status["status"], "CONTINUE")
        self.assertTrue(status["model_inference_completed"])
        self.assertFalse(status["automatic_merge"])
        self.assertTrue(status["no_false_pass"])


if __name__ == "__main__":
    unittest.main()
