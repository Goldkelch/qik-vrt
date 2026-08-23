#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Hardened V2 front-end for the exact Mesh Linux appliance builder."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import qikvrt_mesh_linux_release as base

OFFICIAL_UBUNTU_SHA256 = {
    "amd64": {
        "rootfs_sha": "915b4be62933475c3fb5f5031aa2e159294db95fb32aaa9e8b317aadcb6c065d",
        "cloud_sha": "0533b0655c32e68b31d792ecd6ccfca95abdbc536c4446874fe0513bd4140ffe",
    },
    "arm64": {
        "rootfs_sha": "379cc9a78497fe96449d2d498e455d40e3e0abd8baa22781b2d67aca06c5e2c8",
        "cloud_sha": "aa6da05756e85ea6dde4836b841fecb10cfd1ba3bcea320189d9af945db70476",
    },
}

for architecture, checksums in OFFICIAL_UBUNTU_SHA256.items():
    base.ARCH[architecture].update(checksums)

_original_build = base.build


def _run_container_acceptance(architecture: str, output: Path) -> None:
    image = f"qikvrt-mesh-linux:{base.VERSION}"
    container = f"qikvrt-mesh-linux-e2e-{architecture}"
    receipt_in_container = "/var/lib/qikvrt/firefox-effect-ack-receipt.json"
    receipt = output / (
        f"qikvrt-mesh-linux-{base.VERSION}-{architecture}.firefox-effect-ack.json"
    )
    log = output / f"qikvrt-mesh-linux-{base.VERSION}-{architecture}.container.log"

    subprocess.run(
        ["docker", "rm", "-f", container],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            container,
            "--shm-size",
            "1g",
            image,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    try:
        for _ in range(600):
            exists = subprocess.run(
                ["docker", "exec", container, "test", "-s", receipt_in_container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if exists.returncode == 0:
                break
            running = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if running.returncode != 0 or running.stdout.strip() != "true":
                raise RuntimeError("appliance container exited before producing a receipt")
            time.sleep(0.5)
        else:
            raise RuntimeError("appliance did not produce its bounded Effect-Ack receipt")

        subprocess.run(
            ["docker", "cp", f"{container}:{receipt_in_container}", str(receipt)],
            check=True,
        )
        document = json.loads(receipt.read_text())
        required = {
            "firefox_terminal_execution_observed": True,
            "bounded_loopback_effect_ack_done": True,
            "effect_ack_done_scope": "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
            "external_effect": "NONE",
            "physical_megast_execution": False,
            "general_internet_reachability_claimed": False,
        }
        for key, expected in required.items():
            if document.get(key) != expected:
                raise RuntimeError(
                    f"bounded appliance receipt mismatch: {key}={document.get(key)!r}"
                )
        events = document.get("backend_state", {}).get("events", [])
        if len(events) != 1 or events[0].get("effect") != "TERMINAL_INPUT_ACCEPTED":
            raise RuntimeError("bounded terminal-input backend event was not reobserved")
    finally:
        captured = subprocess.run(
            ["docker", "logs", container],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log.write_text(captured.stdout)
        subprocess.run(
            ["docker", "rm", "-f", container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    sums = output / f"SHA256SUMS-{architecture}"
    files = sorted(path for path in output.iterdir() if path.is_file() and path != sums)
    sums.write_text("".join(f"{base.sha256(path)}  {path.name}\n" for path in files))


def build(architecture: str, output: Path) -> None:
    _original_build(architecture, output)
    _run_container_acceptance(architecture, output)


base.build = build


if __name__ == "__main__":
    raise SystemExit(base.main())
