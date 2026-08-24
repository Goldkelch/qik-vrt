#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Hardened V2 front-end for the exact Mesh Linux appliance builder."""
from __future__ import annotations

import json
import stat
import subprocess
import sys
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

MAX_RELEASE_ASSET_BYTES = 2 * 1024**3
RELEASE_MANIFEST_NAME = "QIKVRT_MESH_LINUX_RELEASE_MANIFEST.json"
RELEASE_SUMS_NAME = "SHA256SUMS"


def expected_release_asset_names(final: bool = False) -> set[str]:
    names = {f"qikvrt-terminal-{base.VERSION}.xpi"}
    for architecture in base.ARCH:
        prefix = f"qikvrt-mesh-linux-{base.VERSION}-{architecture}"
        names.update(
            {
                f"{prefix}.oci.tar.zst",
                f"{prefix}.qcow2.zst",
                f"{prefix}.vhdx.zst",
                f"{prefix}.build.json",
                f"{prefix}.firefox-effect-ack.json",
                f"{prefix}.container.log",
                f"SHA256SUMS-{architecture}",
            }
        )
    names.add(f"qikvrt-mesh-linux-{base.VERSION}-amd64.ova")
    if final:
        names.update({RELEASE_MANIFEST_NAME, RELEASE_SUMS_NAME})
    return names


def _regular_entries(assets: Path) -> dict[str, Path]:
    entries = list(assets.iterdir())
    irregular = sorted(
        path.name
        for path in entries
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode)
    )
    if irregular:
        raise RuntimeError(f"release asset entries are not regular files: {irregular}")
    return {path.name: path for path in entries}


def _validate_global_sums(assets: Path, expected: set[str]) -> None:
    sums = assets / RELEASE_SUMS_NAME
    records: dict[str, str] = {}
    for line in sums.read_text().splitlines():
        digest, separator, name = line.partition("  ")
        if (
            separator != "  "
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not name
            or name in records
        ):
            raise RuntimeError(f"invalid global SHA256SUMS record: {line!r}")
        records[name] = digest
    checksum_targets = expected - {RELEASE_SUMS_NAME}
    if set(records) != checksum_targets:
        raise RuntimeError(
            "global SHA256SUMS name set mismatch: "
            f"expected={sorted(checksum_targets)}, actual={sorted(records)}"
        )
    mismatches = sorted(
        name for name, digest in records.items() if base.sha256(assets / name) != digest
    )
    if mismatches:
        raise RuntimeError(f"global SHA256SUMS digest mismatch: {mismatches}")


def validate_release_assets(assets: Path, final: bool = False) -> None:
    if not assets.is_dir():
        raise RuntimeError(f"release asset directory is missing: {assets}")
    expected = expected_release_asset_names(final)
    files = _regular_entries(assets)
    missing = sorted(expected - set(files))
    unexpected = sorted(set(files) - expected)
    if missing or unexpected:
        raise RuntimeError(
            f"release asset set mismatch: missing={missing}, unexpected={unexpected}"
        )
    empty = sorted(name for name, path in files.items() if path.stat().st_size == 0)
    oversized = sorted(
        name
        for name, path in files.items()
        if path.stat().st_size >= MAX_RELEASE_ASSET_BYTES
    )
    if empty or oversized:
        raise RuntimeError(
            f"release asset size violation: empty={empty}, oversized={oversized}"
        )
    if final:
        _validate_global_sums(assets, expected)


def validate_release_readback(assets: Path, document: Path) -> None:
    validate_release_assets(assets, final=True)
    payload = json.loads(document.read_text())
    remote_assets = payload.get("assets")
    if not isinstance(remote_assets, list):
        raise RuntimeError("release readback has no asset list")
    expected = {
        path.name: path.stat().st_size for path in _regular_entries(assets).values()
    }
    actual: dict[str, int] = {}
    for item in remote_assets:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not isinstance(item.get("size"), int)
            or item["name"] in actual
        ):
            raise RuntimeError(f"invalid release asset readback entry: {item!r}")
        actual[item["name"]] = item["size"]
    if actual != expected:
        raise RuntimeError(
            f"release asset readback mismatch: expected={expected}, actual={actual}"
        )

_original_build = base.build


def validate_bounded_appliance_receipt(document: object) -> None:
    if not isinstance(document, dict):
        raise RuntimeError("bounded appliance receipt is not an object")
    required = {
        "firefox_terminal_execution_observed": True,
        "bounded_loopback_effect_ack_done": True,
        "effect_ack_done_scope": "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
        "external_effect": "NONE",
        "physical_megast_execution": False,
        "general_internet_reachability_claimed": False,
    }
    for key, expected in required.items():
        actual = document.get(key)
        if type(actual) is not type(expected) or actual != expected:
            raise RuntimeError(
                f"bounded appliance receipt mismatch: {key}={actual!r}"
            )
    backend_state = document.get("backend_state")
    if not isinstance(backend_state, dict):
        raise RuntimeError("bounded appliance backend_state is not an object")
    event_count = backend_state.get("events")
    if type(event_count) is not int or event_count != 1:
        raise RuntimeError("bounded terminal-input backend event count is not one")
    last_event = backend_state.get("last_event")
    if not isinstance(last_event, dict):
        raise RuntimeError("bounded terminal-input backend last_event is not an object")
    if last_event.get("kind") != "TERMINAL_INPUT_ACCEPTED":
        raise RuntimeError("bounded terminal-input backend event was not reobserved")


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
        validate_bounded_appliance_receipt(document)
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


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "validate-build-assets":
        validate_release_assets(Path(sys.argv[2]), final=False)
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "validate-release-assets":
        validate_release_assets(Path(sys.argv[2]), final=True)
        return 0
    if len(sys.argv) == 4 and sys.argv[1] == "validate-release-readback":
        validate_release_readback(Path(sys.argv[2]), Path(sys.argv[3]))
        return 0
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
