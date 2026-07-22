"""Create a verification receipt only from an error-free Lean JSON stream."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checker", default="Lean 4 kernel")
    parser.add_argument("--version", default="4.28.0-pre (WebAssembly independent checker)")
    parser.add_argument("--commit", default="38f3c0c45b8df6da2652faff6dcaa15afb5a6981")
    args = parser.parse_args()

    stream = ROOT / "build" / "lean.stdout.jsonl"
    monolith = ROOT / "build" / "All.lean"
    events = []
    for line in stream.read_text(encoding="utf-8").splitlines():
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    errors = [e for e in events if e.get("severity") == "error"]
    escapes = [e for e in events if e.get("kind") == "hasSorry"]
    lean_source = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((ROOT / "QIKVRTFormalization").glob("*.lean"))
    )
    declarations = len(re.findall(r"\b(?:theorem|def|structure|inductive|abbrev)\s+[A-Za-z0-9_]+", lean_source))
    verified = not errors and not escapes and monolith.exists()
    receipt = {
        "schemaVersion": "1.0.0",
        "checker": args.checker,
        "version": args.version,
        "checkerCommit": args.commit,
        "targetToolchain": (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip(),
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "verified": verified,
        "exitCode": 0 if verified else 1,
        "errors": len(errors),
        "uncheckedProofEscapes": len(escapes),
        "declarations": declarations,
        "monolithSha256": sha256(monolith) if monolith.exists() else None,
    }
    out = ROOT / "build" / "lean-verification.json"
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())

