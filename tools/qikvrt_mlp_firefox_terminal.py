#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

MLP_SHA256 = "5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e"
FRAME_SHA256 = "8f3b74fd6d2868ac24fb22ae160b1e2806650f9a8e84978a7a04c0af30a94734"
DEFAULT_URL = "https://github.com/Goldkelch/qik-vrt/blob/main/AI"
EXTENSION = Path("browser/firefox/qikvrt-terminal")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(mlp_tos: Path, drive_c: Path) -> dict:
    if sha256(mlp_tos) != MLP_SHA256:
        raise SystemExit("HOLD: MLP.TOS digest mismatch")
    drive_c.mkdir(parents=True, exist_ok=True)
    target = drive_c / "MLP.PRG"
    shutil.copyfile(mlp_tos, target)
    return {
        "desktop_program": str(target),
        "desktop_program_sha256": sha256(target),
        "manifested_on_guest_drive": True,
        "executed": False,
        "observed": False,
        "acknowledged": False,
    }


def validate_frame(frame: Path) -> dict:
    if not frame.exists():
        raise SystemExit("HOLD: MLP.OPEN absent")
    digest = sha256(frame)
    if digest != FRAME_SHA256:
        raise SystemExit("HOLD: MLP.OPEN digest mismatch")
    return {"frame": str(frame), "frame_sha256": digest, "requested": True}


def firefox_binary(explicit: str | None) -> str:
    candidates = [explicit] if explicit else []
    candidates += ["firefox", "firefox-esr"]
    for name in candidates:
        if name and (os.path.isabs(name) and Path(name).exists() or shutil.which(name)):
            return name
    raise SystemExit("HOLD: Firefox executable unavailable")


def launch(frame: Path, url: str, executable: str | None, dry_run: bool) -> dict:
    binding = validate_frame(frame)
    if not EXTENSION.is_dir() or not (EXTENSION / "manifest.json").exists():
        raise SystemExit("HOLD: QIK-VRT Firefox terminal extension unavailable")
    binary = firefox_binary(executable)
    profile = Path(tempfile.mkdtemp(prefix="qikvrt-firefox-terminal-"))
    cmd = [binary, "--no-remote", "--new-instance", "--profile", str(profile), url]
    result = {
        **binding,
        "firefox": binary,
        "profile": str(profile),
        "terminal_extension": str(EXTENSION),
        "terminal_mode": "INTERACTIVE_TERMINAL",
        "monitor_only": False,
        "launch_command": cmd,
        "executed": False,
        "browser_execution_observed": False,
        "effect_ack_done": False,
    }
    if dry_run:
        return result
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result["executed"] = True
    result["pid"] = proc.pid
    # Process creation is execution evidence only. Browser readiness and any
    # protected effect require separate observation / Effect-Ack evidence.
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage")
    s.add_argument("--mlp-tos", type=Path, default=Path("MLP.TOS/MLP.TOS"))
    s.add_argument("--drive-c", type=Path, required=True)
    l = sub.add_parser("launch")
    l.add_argument("--frame", type=Path, required=True)
    l.add_argument("--url", default=DEFAULT_URL)
    l.add_argument("--firefox")
    l.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.cmd == "stage":
        out = stage(args.mlp_tos, args.drive_c)
    else:
        out = launch(args.frame, args.url, args.firefox, args.dry_run)
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
