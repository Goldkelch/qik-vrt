#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def coarse_status(*, succeeded: bool, fallback_error: str | None = None) -> dict[str, Any]:
    status: dict[str, Any] = {
        "status": "CONTINUE" if succeeded else "BLOCK",
        "issue_materialized": True,
        "model_inference_completed": succeeded,
        "automatic_merge": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "no_false_pass": True,
    }
    if fallback_error:
        status["fallback_error"] = fallback_error
    return status


def run_deterministic_fallback(directory: Path) -> dict[str, Any]:
    resolved = directory.resolve()
    try:
        issue = int(resolved.name)
    except ValueError as exc:
        raise RuntimeError(f"issue directory name is not numeric: {resolved.name}") from exc

    root = resolved.parents[2]
    planner = root / "tools" / "issue_agent_work_units.py"
    if not planner.is_file():
        raise RuntimeError(f"deterministic fallback planner missing: {planner}")

    subprocess.run(
        [sys.executable, str(planner), "--root", str(root), "--issue", str(issue)],
        cwd=root,
        check=True,
    )

    aggregate_path = directory / "STATUS.work-units.json"
    if not aggregate_path.is_file():
        raise RuntimeError("fallback planner did not produce STATUS.work-units.json")
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))

    if aggregate.get("status") in {"DONE", "EFFECT_ACK_DONE"}:
        # The deterministic fallback is not permitted to elevate the issue to a
        # final state by itself. Scientific completion still requires the
        # dedicated completion gate and all repository receipts.
        aggregate["status"] = "EFFECT_ACK_CONTINUE"
        aggregate["automatic_merge"] = False
        aggregate["completion_gate_required"] = True

    aggregate["fallback_mode"] = "deterministic_work_units"
    aggregate["no_false_pass"] = True
    write_json(directory / "STATUS.json", aggregate)
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--inference-outcome", required=True)
    args = parser.parse_args()

    directory = Path(args.directory)
    answer = directory / "ANSWER.md"
    succeeded = args.inference_outcome == "success" and answer.exists() and answer.stat().st_size > 0

    if succeeded:
        write_json(directory / "STATUS.json", coarse_status(succeeded=True))
        return

    answer.write_text(
        "# Repository answer\n\n"
        "The autonomous semantic model step was not available or failed. No scientific claim is "
        "asserted from that step. Deterministic repository work units are executed and checkpointed "
        "below the semantic boundary.\n\n"
        "## Gate result\n\nEFFECT_ACK_CONTINUE\n",
        encoding="utf-8",
    )

    try:
        run_deterministic_fallback(directory)
    except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        write_json(directory / "STATUS.json", coarse_status(succeeded=False, fallback_error=str(exc)))
        raise


if __name__ == "__main__":
    main()
