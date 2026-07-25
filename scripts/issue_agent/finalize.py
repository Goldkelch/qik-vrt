#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--directory", required=True)
    p.add_argument("--inference-outcome", required=True)
    args = p.parse_args()

    directory = Path(args.directory)
    answer = directory / "ANSWER.md"
    succeeded = args.inference_outcome == "success" and answer.exists() and answer.stat().st_size > 0
    if not succeeded:
        answer.write_text(
            "# Repository answer\n\n"
            "The autonomous model step was not available or failed. No scientific or technical "
            "answer is asserted. The request and repository context were materialized for review.\n\n"
            "## Gate result\n\nBLOCK\n",
            encoding="utf-8",
        )

    status = {
        "status": "CONTINUE" if succeeded else "BLOCK",
        "issue_materialized": True,
        "model_inference_completed": succeeded,
        "automatic_merge": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "no_false_pass": True,
    }
    (directory / "STATUS.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
