"""Run pytest and persist a small machine-readable receipt."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / '.pydeps'}:{ROOT}"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    receipt = {
        "schemaVersion": "1.0.0",
        "runner": "pytest",
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "exitCode": result.returncode,
        "passed": result.returncode == 0,
        "summary": output.strip(),
    }
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "python-test-report.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(output, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

