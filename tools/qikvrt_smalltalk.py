#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pinned Pharo bootstrap, reproducible source loading and exhaustive C90 comparison.

Extends bootstrap-runtime's language profiles. Base image/cache bytes never acquire
authority through a mutable live image; every build starts from the hash-locked ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "runtime/toolchains/pharo-13.lock.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, timeout=600)


def cache_path(cache: Path, lock: dict) -> Path:
    return cache / "pharo" / lock["version"]


def verify(cache: Path, lock: dict) -> Path:
    directory = cache_path(cache, lock)
    for kind in ("image", "vm"):
        archive = directory / (kind + ".zip")
        if digest(archive) != lock[kind]["sha256"]:
            raise ValueError(f"{kind}: archive digest mismatch")
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                if member.is_dir():
                    continue
                path = directory / kind / member.filename
                if path.is_symlink() or not path.resolve().is_relative_to((directory / kind).resolve()):
                    raise ValueError("unsafe cache member")
                if digest(path) != hashlib.sha256(source.read(member)).hexdigest():
                    raise ValueError(f"{kind}: extracted bytes changed: {member.filename}")
    return directory


def install(cache: Path, lock: dict, archive_dir: Path | None = None) -> Path:
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        raise ValueError("Pharo lock is for Linux x86_64")
    target = cache_path(cache, lock)
    if target.exists():
        return verify(cache, lock)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".install-", dir=target.parent))
    try:
        for kind in ("image", "vm"):
            archive = temporary / (kind + ".zip")
            print(f"PHARO_FETCH {kind}", flush=True)
            if archive_dir:
                shutil.copyfile(archive_dir / (kind + ".zip"), archive)
            else:
                with urllib.request.urlopen(lock[kind]["url"], timeout=120) as response, archive.open("wb") as output:
                    shutil.copyfileobj(response, output)
            if digest(archive) != lock[kind]["sha256"]:
                raise ValueError(f"{kind}: downloaded archive digest mismatch")
            with zipfile.ZipFile(archive) as source:
                for member in source.infolist():
                    path = temporary / kind / member.filename
                    if not path.resolve().is_relative_to((temporary / kind).resolve()):
                        raise ValueError("unsafe archive path")
                source.extractall(temporary / kind)
                for member in source.infolist():
                    path = temporary / kind / member.filename
                    if path.is_file() and member.external_attr >> 16 & 0o111:
                        path.chmod(0o755)
        temporary.rename(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    print("PHARO_INSTALL_COMPLETE", flush=True)
    return verify(cache, lock)


def build(directory: Path, lock: dict, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    image = output / "QIKVRT.image"
    if image.exists():
        raise ValueError("Refusing to overwrite an existing mutable image")
    shutil.copyfile(directory / "image" / lock["image"]["file"], image)
    original_changes = (directory / "image" / lock["image"]["file"]).with_suffix(".changes")
    shutil.copyfile(original_changes, image.with_suffix(".changes"))
    for source in (directory / "image").glob("*.sources"):
        shutil.copyfile(source, output / source.name)
    vm = str(directory / "vm" / lock["vm"]["file"])
    run([vm, "--headless", str(image), "st", str(ROOT / "src/smalltalk/QikvrtEffectAck.st"), str(ROOT / "src/smalltalk/save-image.st")], output)
    run([vm, "--headless", str(image), "st", str(ROOT / "src/smalltalk/smoke.st")], output)
    receipt = {"schema": "qikvrt_smalltalk_image_v1", "lock_sha256": digest(LOCK_PATH),
               "source_sha256": digest(ROOT / "src/smalltalk/QikvrtEffectAck.st"),
               "image_sha256": digest(image), "image_restored": True, "effect_ack_done": False}
    (output / "smalltalk-image-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return image


def test(directory: Path, lock: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="qikvrt-smalltalk-") as temp:
        work = Path(temp)
        image = build(directory, lock, work)
        run([str(directory / "vm" / lock["vm"]["file"]), "--headless", str(image), "st", str(ROOT / "tests/smalltalk/core-vectors.st")], work)
        executable = work / "c90-vectors"
        run([os.environ.get("CC", "cc"), "-std=c90", "-pedantic", "-Wall", "-Wextra", "-Werror", "-O2", "-I" + str(ROOT / "include"), str(ROOT / "src/effect_ack_core.c"), str(ROOT / "tests/smalltalk/core-vectors.c"), "-o", str(executable)], work)
        with (work / "c90-vectors.bin").open("wb") as output:
            subprocess.run([str(executable)], stdout=output, check=True, timeout=60)
        a, b = work / "c90-vectors.bin", work / "smalltalk-vectors.bin"
        if a.stat().st_size != 2621440 or b.stat().st_size != 2621440 or digest(a) != digest(b):
            raise ValueError("Smalltalk/C90 exhaustive result mismatch")
        # Also use the existing rich Python engine on representable boundary
        # cases. Its evidence parser is intentionally not replaced by the C ABI.
        sys.path.insert(0, str(ROOT / "src"))
        from qikvrt_effect_ack import EffectAckEngine, ConnectionDecision, RiskLevel
        sys.path.insert(0, str(ROOT))
        from tests.test_effect_ack_conformance import request
        vectors = a.read_bytes()
        cases = [(122879, 2, {}, 100)]
        fields = {0: "transport_ack", 1: "input_id", 3: "origin_checked", 4: "context_checked",
                  5: "semantics_reconstructed", 6: "effect_anticipated", 7: "risk_classified",
                  8: "risk_level", 9: "responsibility_assigned", 10: "responsibility_owner",
                  12: "policy_allows_release", 14: "open_questions", 15: "next_required_checks", 16: "evidence_refs"}
        for bit, field in fields.items():
            value = False
            if field in ("input_id", "responsibility_owner"): value = ""
            if field == "risk_level": value = RiskLevel.UNKNOWN
            if field in ("open_questions", "next_required_checks"): value = ("pending",)
            if field == "evidence_refs": value = ()
            mask = 122879 & ~(1 << bit)
            if field == "transport_ack":
                # A rich Python request without acknowledged reception has no
                # effect-checkable input identity. The core consumes verified
                # facts, not the raw request's non-empty identifier string.
                mask &= ~(1 << 1)
            cases.append((mask, 2, {field: value}, 100))
        for code, decision in enumerate(ConnectionDecision):
            mask = 122879 if code != 0 else 122879 & ~(1 << 11)
            cases.append((mask, code, {"connection_decision": decision}, 100))
        cases += [(122879 | (1 << 13), 2, {}, 0),
                  (122879 | (1 << 18), 2, {"declared_input_hash": "0" * 64}, 100),
                  (122879 & ~(1 << 2), 2, {"payload": None, "declared_input_hash": None}, 100)]
        names = ["EFFECT_NACK", "EFFECT_ACK_CONTINUE", "EFFECT_ACK_DONE", "EFFECT_ACK_ISOLATE", "EFFECT_ACK_BLOCK"]
        for mask, decision, changes, timeout in cases:
            result = EffectAckEngine(clock_ns=lambda: 0).evaluate(request(**changes), timeout_ms=timeout)
            if result.state.value != names[vectors[mask * 5 + decision]]:
                raise ValueError(f"Python/C90/Smalltalk boundary mismatch: {mask}/{decision}")
        print(f"QIKVRT_PYTHON_C90_SMALLTALK_BOUNDARIES={len(cases)}")
        print(f"QIKVRT_SMALLTALK_C90_EXHAUSTIVE_MATCH vectors=2621440 sha256={digest(a)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "install", "build", "test"))
    parser.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("QIKVRT_TOOLCHAIN_CACHE", ROOT / ".qikvrt/toolchains")))
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    lock = json.loads(LOCK_PATH.read_text())
    try:
        directory = install(args.cache_dir.resolve(), lock, args.archive_dir) if args.command == "install" else verify(args.cache_dir.resolve(), lock)
        if args.command == "build":
            if not args.output:
                parser.error("build requires --output")
            build(directory, lock, args.output.resolve())
        if args.command == "test":
            test(directory, lock)
        print(f"PHARO_{args.command.upper()}_OK version={lock['version']}")
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(f"BLOCK: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
