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
import select
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "runtime/toolchains/pharo-13.lock.json"
SOURCES = ("src/smalltalk/QikvrtEffectAck.st", "src/smalltalk/QikvrtEventReactor.st")


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
    run([vm, "--headless", str(image), "st", *[str(ROOT / p) for p in SOURCES], str(ROOT / "src/smalltalk/save-image.st")], output)
    run([vm, "--headless", str(image), "st", str(ROOT / "src/smalltalk/smoke.st")], output)
    receipt = {"schema": "qikvrt_smalltalk_image_v1", "lock_sha256": digest(LOCK_PATH),
               "source_sha256": digest(ROOT / "src/smalltalk/QikvrtEffectAck.st"),
               "sources_sha256": {p: digest(ROOT / p) for p in (*SOURCES, "src/smalltalk/events.st")},
               "image_sha256": digest(image), "image_restored": True, "effect_ack_done": False}
    (output / "smalltalk-image-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return image


class EventWorker:
    """A persistent Smalltalk reactor over inherited local pipes.

    The timeout bounds a requested operation, never schedules status polling.
    There are no credentials, user-provided selectors, or shell commands here.
    """
    def __init__(self, directory: Path, lock: dict, image: Path, binding: dict):
        receipt = json.loads((image.parent / "smalltalk-image-receipt.json").read_text())
        sources = {p: digest(ROOT / p) for p in (*SOURCES, "src/smalltalk/events.st")}
        if (receipt.get("sources_sha256") != sources
                or receipt.get("lock_sha256") != digest(LOCK_PATH)
                or receipt.get("image_sha256") != digest(image)):
            raise ValueError("Smalltalk image/source/lock binding drift")
        self.runtime_binding = {"lock": digest(LOCK_PATH), "sources": sources,
                                "adapter": digest(Path(__file__)),
                                "ledger": digest(ROOT / "tools/qikvrt_real_mesh.py")}
        self.process = subprocess.Popen(
            [str(directory / "vm" / lock["vm"]["file"]), "--headless", str(image),
             "st", str(ROOT / "src/smalltalk/events.st")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1)
        try:
            if self.exchange(binding).get("status") != "READY":
                raise ValueError("Smalltalk rejected the exact subject binding")
        except BaseException:
            self.close()
            raise

    def exchange(self, event):
        from tools.qikvrt_real_mesh import canonical_json_bytes
        encoded = canonical_json_bytes(event)
        if len(encoded) > 65535:
            raise ValueError("event exceeds pipe bound")
        self.process.stdin.write(encoded.decode("utf-8") + "\n")
        self.process.stdin.flush()
        ready, _, _ = select.select([self.process.stdout], [], [], 15)
        if not ready:
            raise TimeoutError("Smalltalk event processing deadline exceeded")
        line = self.process.stdout.readline(16 * 1024 * 1024)
        if not line.endswith("\n"):
            raise ValueError("Smalltalk terminated or exceeded response bound")
        response = json.loads(line)
        if not isinstance(response, dict):
            raise ValueError("Smalltalk response is not an object")
        return response

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdout.close()


class EventContinuation:
    """Reuse the existing hash-linked, fsynced Mesh ledger as a durable outbox.

    Only the pure Smalltalk handler is replayed. COMPLETED means local handler
    output was persisted, never that an external action or a P0-P7 gate passed.
    Stdout is a projection; consumers must use event IDs and the durable outbox
    to recover a crash between persistence and receipt of that projection.
    """
    def __init__(self, worker, binding, ledger_path):
        from tools.qikvrt_real_mesh import AppendOnlyNodeLedger, canonical_sha256
        self.worker = worker
        self.ledger = AppendOnlyNodeLedger(ledger_path, "smalltalk:" + canonical_sha256(
            {"binding": binding, "runtime": worker.runtime_binding}))
        self.failed = False
        if len(self.ledger.accepted) > 10000:
            raise ValueError("event history capacity exceeded")
        self.recovered = []
        for accepted in list(self.ledger.accepted.values()):
            event = accepted["event"]
            response = self.worker.exchange(event)
            if response.get("status") != "ACCEPTED":
                raise ValueError("Smalltalk cannot reconstruct the accepted event history")
            self.recovered.extend(self._complete(response))

    def _complete(self, response):
        outputs = []
        for result in response.get("completions", []):
            event_id = result["event_id"]
            old = self.ledger.completed.get(event_id)
            if old is not None:
                if old != result:
                    raise ValueError("Smalltalk replay changed a persisted continuation")
                continue
            if event_id not in self.ledger.accepted:
                raise ValueError("Smalltalk completed an event absent from the inbox")
            self.ledger.append("COMPLETED", event_id, response=result)
            outputs.append(result)
        return outputs

    def accept(self, event):
        from tools.qikvrt_live_sse import valid_event
        from tools.qikvrt_real_mesh import canonical_json_bytes
        if self.failed:
            raise ValueError("event consumer requires restart after persistence failure")
        canonical_json_bytes(event)  # Reject non-canonical JSON, including floats.
        if not valid_event(event):
            raise ValueError("invalid live event envelope")
        event_id = event["event_id"]
        old = self.ledger.accepted.get(event_id)
        if old is not None:
            if old["event"] != event:
                raise ValueError("event ID rebound to different content")
            return []
        response = self.worker.exchange(event)
        if response.get("status") != "ACCEPTED":
            raise ValueError("Smalltalk HOLD: " + str(response.get("reason", response)))
        try:
            self.ledger.append("ACCEPTED", event_id, accepted={"event": event})
            return self._complete(response)
        except BaseException:
            self.failed = True
            raise


def events(directory, lock, binding_path, events_path, ledger_path, once=False):
    from tools.qikvrt_live_sse import EventFile, unique_object
    binding = json.loads(binding_path.read_text(), object_pairs_hook=unique_object)
    # Acquire the single-writer lease before starting or replaying Smalltalk.
    import fcntl
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with (ledger_path.parent / (ledger_path.name + ".lock")).open("a") as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix="qikvrt-event-image-") as temp:
            image = build(directory, lock, Path(temp))
            worker = EventWorker(directory, lock, image, binding)
            try:
                consumer = EventContinuation(worker, binding, ledger_path)
                for result in consumer.recovered:
                    print(json.dumps(result, sort_keys=True), flush=True)
                reader = EventFile(events_path)
                try:
                    print('QIKVRT_SMALLTALK_EVENT_READY', flush=True)
                    for event in reader.read_new() if once else reader.follow():
                        for result in consumer.accept(event):
                            print(json.dumps(result, sort_keys=True), flush=True)
                finally:
                    reader.close()
            finally:
                worker.close()


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
    parser.add_argument("command", choices=("verify", "install", "build", "test", "events"))
    parser.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("QIKVRT_TOOLCHAIN_CACHE", ROOT / ".qikvrt/toolchains")))
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--binding", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--once", action="store_true", help="Process available events once and exit")
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
            os.environ["QIKVRT_TOOLCHAIN_CACHE"] = str(args.cache_dir.resolve())
            run([sys.executable, "-B", "-m", "unittest", "-v",
                 "tests.test_qikvrt_smalltalk_events"], ROOT)
        if args.command == "events":
            if not all((args.binding, args.events, args.ledger)):
                parser.error("events requires --binding, --events and --ledger")
            events(directory, lock, args.binding, args.events, args.ledger, args.once)
        print(f"PHARO_{args.command.upper()}_OK version={lock['version']}")
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(f"BLOCK: {error}")
        return 1


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
