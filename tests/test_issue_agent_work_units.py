import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "issue_agent_work_units.py"


def run(tmp_path: Path, *extra: str):
    (tmp_path / "evidence" / "issues" / "79").mkdir(parents=True)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--issue", "79", *extra],
        text=True,
        capture_output=True,
        check=False,
    )


def load_state(tmp_path: Path):
    return json.loads((tmp_path / "evidence" / "issues" / "79" / "work-units" / "STATE.json").read_text())


def test_model_unavailable_still_materializes_deterministic_units(tmp_path: Path):
    (tmp_path / "zenodo-metadata.json").write_text('{"doi":"10.0/example"}')
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    state = load_state(tmp_path)
    units = {u["name"]: u for u in state["units"]}
    assert units["ZENODO_RECORD_DISCOVERY"]["status"] == "DONE"
    assert units["ARTIFACT_FILE_INVENTORY"]["status"] == "DONE"
    assert units["SOURCE_HASH_BINDING"]["status"] == "DONE"
    assert units["CLAIM_EXTRACTION_QUEUE"]["status"] == "BLOCK"
    assert units["CLAIM_EXTRACTION_QUEUE"]["blocker"] == "MODEL_INFERENCE_UNAVAILABLE"
    assert state["aggregate_status"] == "EFFECT_ACK_CONTINUE"
    assert state["next_cursor"] == "CLAIM_EXTRACTION_QUEUE"


def test_resume_does_not_repeat_completed_units(tmp_path: Path):
    (tmp_path / "zenodo-metadata.json").write_text("{}")
    assert run(tmp_path).returncode == 0
    first = load_state(tmp_path)
    attempts = {u["name"]: u["attempts"] for u in first["units"]}
    assert run(tmp_path).returncode == 0
    second = load_state(tmp_path)
    for name in ("ZENODO_RECORD_DISCOVERY", "ARTIFACT_FILE_INVENTORY", "SOURCE_HASH_BINDING"):
        assert second["units"][[u["name"] for u in second["units"]].index(name)]["attempts"] == attempts[name]
    claim = next(u for u in second["units"] if u["name"] == "CLAIM_EXTRACTION_QUEUE")
    assert claim["attempts"] == 2


def test_no_false_done_without_all_units(tmp_path: Path):
    assert run(tmp_path).returncode == 0
    status = json.loads((tmp_path / "evidence" / "issues" / "79" / "STATUS.work-units.json").read_text())
    assert status["status"] == "EFFECT_ACK_CONTINUE"
    assert status["automatic_merge"] is False
    assert status["no_false_pass"] is True
