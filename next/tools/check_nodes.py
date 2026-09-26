#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Fresh TLS identities, all directed node pairs, live terminals and durable re-entry."""
import argparse
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from check_bus import Process, canonical, sha
from node import tls_context

ROOT = Path(__file__).resolve().parents[1]


class LoggedProcess(Process):
    """Drain daemon output to disk; large deliveries must not block on test pipes."""
    def __init__(self, args, directory, number):
        log = directory / f"process-{number}.log"
        self.writer = log.open("wb")
        self.reader = log.open("rb")
        self.errors = (directory / f"process-{number}.err").open("w+b")
        self.p = subprocess.Popen(list(map(str, args)), stdin=subprocess.PIPE,
                                  stdout=self.writer, stderr=self.errors)
        self.events = []
        self.store = Path(args[args.index("--store") + 1])

    def wait(self, predicate, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for index, item in enumerate(self.events):
                if predicate(item):
                    return self.events.pop(index)
            position = self.reader.tell()
            line = self.reader.readline()
            if line.endswith(b"\n"):
                self.events.append(json.loads(line))
                continue
            self.reader.seek(position)
            if self.p.poll() is not None:
                self.errors.seek(0)
                raise AssertionError((self.p.returncode, self.events, self.errors.read().decode()))
            time.sleep(.02)
        raise AssertionError(("event timeout", self.events))

    def stop(self):
        super().stop()
        self.writer.close()
        self.reader.close()
        self.errors.close()
        deadline = time.monotonic() + 5
        while True:
            with (self.store / "writer.lock").open("rb") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise AssertionError("orphan store owner after supervisor death")
            time.sleep(.02)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/release/qikvrt-next")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--subjects", type=Path, help="Explicit previously resolved repository subjects; no deployment claim")
    args = parser.parse_args()
    binary = args.binary.resolve()
    binary_hash = sha(binary.read_bytes())
    processes = []

    def cli(*args, data=None):
        result = subprocess.run([str(binary), *map(str, args)], input=data,
                                capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr.decode()
        return json.loads(result.stdout)

    def request(url, path, value=None):
        data = None if value is None else canonical(value)
        with urllib.request.urlopen(urllib.request.Request(url + path, data=data,
                headers={"Content-Type": "application/json"}), timeout=8) as response:
            return json.load(response)

    def await_message(url, predicate, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for message in request(url, "/api/bus/messages")["messages"]:
                if predicate(message):
                    return message
            time.sleep(.05)
        raise AssertionError("durable receipt timeout")

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT.parent, text=True).strip()

    source_head, source_tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    subject = {"repository": "Goldkelch/qik-vrt", "subject_id": "repository-node-test",
               "head": source_head, "tree": source_tree}
    # Distinct repository subjects are fixtures. This is a process-level test,
    # never evidence that a remote GitHub repository has deployed this runtime.
    subjects = [subject, {**subject, "repository": "ingolf-lohmann/qik-vrt", "head": "2" * 40},
                {**subject, "repository": "validation/third-node", "head": "3" * 40}]
    if args.subjects:
        subjects = json.loads(args.subjects.read_text())
        assert 2 <= len(subjects) <= 16
    with tempfile.TemporaryDirectory(prefix="qikvrt-node-") as temporary:
        temp = Path(temporary)

        def openssl(*args):
            result = subprocess.run(["openssl", *map(str, args)], cwd=temp,
                                    capture_output=True, timeout=30)
            assert result.returncode == 0, result.stderr.decode()
            return result.stdout

        assert openssl("version").startswith(b"OpenSSL 3.")
        openssl("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                "-nodes", "-keyout", "ca.key", "-out", "ca.pem", "-days", "1",
                "-subj", "/CN=Disposable QIKVRT test CA")

        def certificate(name, server=False):
            openssl("req", "-new", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                    "-nodes", "-keyout", name + ".key", "-out", name + ".csr", "-subj", "/CN=" + name)
            (temp / (name + ".ext")).write_text("basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage="
                + ("serverAuth\nsubjectAltName=DNS:localhost\n" if server else "clientAuth\n"))
            openssl("x509", "-req", "-in", name + ".csr", "-CA", "ca.pem", "-CAkey", "ca.key",
                    "-CAcreateserial", "-days", "1", "-out", name + ".pem", "-extfile", name + ".ext")
            (temp / (name + ".key")).chmod(0o600)
            return sha(ssl.PEM_cert_to_DER_cert((temp / (name + ".pem")).read_text()))

        server_hash = certificate("router", True)
        router_subject = temp / "router-subject.json"
        router_subject.write_bytes(canonical(subject))
        nodes = temp / "nodes.json"
        nodes.write_bytes(canonical(subjects))
        credentials = temp / "credentials"
        cli("bus-repository-config", credentials, "router", router_subject, nodes)
        config = json.loads((credentials / "bus.json").read_text())
        ids = list(config["repositories"])
        pins = {name: certificate(name) for name in ids}
        certificate("unadmitted")
        (temp / "pins.json").write_bytes(canonical(pins))
        cli("init", temp / "router", "router")
        for name in ids:
            cli("init", temp / name, name)
            (temp / (name + ".subject")).write_bytes(canonical(config["repositories"][name]))
            obj = temp / (name + ".object")
            obj.write_bytes(name.encode())
            artifact = cli("put", temp / name, obj)["sha256"]
            cli("run", temp / name, data=canonical({"event_id": "initial", "node_id": "calculator",
                "subject": config["repositories"][name], "cause_event_ids": [],
                "operation": {"op": "register", "artifact": artifact, "entrypoint": "next/AI"}}) + b"\n")

        def start(mode, name, address, **options):
            command = [sys.executable, ROOT / "tools/node.py", mode, "--binary", binary,
                "--binary-sha256", binary_hash, "--store", temp / name,
                "--config", credentials / ("bus.json" if mode == "router" else name + ".json"),
                "--ca", temp / "ca.pem", "--certificate", temp / (name + ".pem"),
                "--key", temp / (name + ".key"), "--address", address]
            if mode == "router":
                command += ["--peer-certificates", temp / "pins.json"]
            else:
                command += ["--subject", temp / (name + ".subject"), "--server-name", "localhost",
                    "--server-certificate-sha256", options.get("pin", server_hash), "--terminal", "127.0.0.1:0"]
            proc = LoggedProcess(command, temp, len(processes))
            processes.append(proc)
            if options.get("bad"):
                return proc
            if mode == "router":
                address = proc.wait(lambda v: v.get("state") == "TLS_ROUTER_LISTENING")["address"]
                return proc, f"{address[0]}:{address[1]}"
            terminal = proc.wait(lambda v: v.get("state") == "TERMINAL_LISTENING")["address"]
            joined = proc.wait(lambda v: v.get("state") == "JOINED")
            assert joined["repositories"] == config["repositories"]
            return proc, "http://" + terminal

        def send(url, destination, body, codec=2, bound=None):
            directory = request(url, "/api/bus")
            return request(url, "/api/bus/send", {"op": "send", "destination": destination,
                "subject": bound or directory["subject_digests"][destination],
                "codec": codec, "payload_hex": body.hex()})

        def delivered(url, correlation, attempt=None):
            result = await_message(url, lambda v: v["kind"] == 3 and v["correlation"] == correlation
                and (attempt is None or all(v[k] == attempt[k] for k in ("session", "nonce", "message_id"))))
            return json.loads(result["payload_utf8"])

        try:
            router, addr = start("router", "router", "127.0.0.1:0")
            peers = {name: start("peer", name, addr) for name in ids}
            bodies = {}
            for source in ids:
                for destination in ids:
                    if source == destination:
                        continue
                    body = (f"{source} → {destination}\n".encode() * 80) + bytes(range(256))
                    queued = send(peers[source][1], destination, body)
                    assert queued["state"] == "QUEUED_DURABLE"
                    receipt = delivered(peers[source][1], queued["correlation"])
                    assert receipt["result"]["sha256"] == sha(body)
                    assert receipt["store"] == destination and receipt["effect_ack_done"] is False
                    bodies[destination, sha(body)] = body
            a, b = ids[:2]
            command = {"event_id": "same-command", "node_id": "calculator", "subject": config["repositories"][b],
                "cause_event_ids": [], "operation": {"op": "evaluate", "a": 13, "b": 9, "lut": 6,
                    "requested": 2, "binding": 1, "authority": 1, "distinction": 1, "drift": 0}}
            first = delivered(peers[a][1], send(peers[a][1], b, canonical(command), 1)["correlation"])
            retry = send(peers[a][1], b, canonical(command), 1)
            second = delivered(peers[a][1], retry["correlation"], retry)
            assert first["result"]["record"]["result"]["value"] == 4
            assert second["result"]["replayed"] is True
            assert second["result"]["record"] == first["result"]["record"]
            # Check durable uniqueness as well as the exact second reply binding.
            rows = request(peers[b][1], "/api/events")
            assert len([r for r in rows if r["record"]["command"]["event_id"] == "same-command"]) == 1
            try:
                send(peers[a][1], b, b"wrong binding", bound="0" * 64)
                raise AssertionError("wrong destination subject accepted")
            except urllib.error.HTTPError as error:
                assert error.code == 400
                assert json.load(error)["reason"] == "DESTINATION_REPOSITORY_SUBJECT_MISMATCH"
            host, port = addr.rsplit(":", 1)
            rogue = tls_context(temp / "ca.pem", temp / "unadmitted.pem", temp / "unadmitted.key")
            with rogue.wrap_socket(socket.create_connection((host, int(port)), timeout=5), server_hostname="localhost") as stream:
                assert stream.recv(1) == b""
            context = tls_context(temp / "ca.pem", temp / (a + ".pem"), temp / (a + ".key"))
            try:
                with context.wrap_socket(socket.create_connection((host, int(port)), timeout=5), server_hostname="wrong.invalid"):
                    raise AssertionError("wrong hostname accepted")
            except ssl.SSLCertVerificationError:
                pass
            peers[a][0].stop()
            time.sleep(.1)
            with context.wrap_socket(socket.create_connection((host, int(port)), timeout=5), server_hostname="localhost") as stream:
                f = stream.makefile("rwb", buffering=0)
                assert json.loads(f.readline())["protocol"] == "qikvrt-bus-auth-v1"
                f.write(canonical({"id": b, "proof": "0" * 64}) + b"\n")
                assert f.read(1) == b""
                f.close()
            bad = start("peer", a, addr, pin="0" * 64, bad=True)
            assert bad.p.wait(timeout=15) != 0
            bad.stop()
            peers[a] = start("peer", a, addr)
            # Receiver partition, followed by SIGKILL of every process. All bytes
            # accepted into the source outbox must still be deliverable afterwards.
            peers[b][0].stop()
            payload = b"retained across TLS disconnect and process SIGKILL\x00" * 160
            queued = send(peers[a][1], b, payload)
            assert queued["state"] == "QUEUED_DURABLE"
            for name, (proc, _) in peers.items():
                if name != b:
                    proc.stop()
            router.stop()
            original = {name: {f.name: f.read_bytes() for f in (temp / name / "events").glob("*.json")}
                        for name in ["router", *ids]}
            router, addr = start("router", "router", "127.0.0.1:0")
            peers = {name: start("peer", name, addr) for name in ids}
            recovered = delivered(peers[a][1], queued["correlation"])
            assert recovered["result"]["sha256"] == sha(payload)
            bodies[b, sha(payload)] = payload
            # The receiving terminal also reconstructs incoming messages.
            await_message(peers[b][1], lambda m: m["payload_sha256"] == sha(payload))
            for proc, _ in peers.values():
                proc.stop()
            router.stop()
            for name, records in original.items():
                for filename, data in records.items():
                    assert (temp / name / "events" / filename).read_bytes() == data
                cli("verify", temp / name)
            for (name, digest), body in bodies.items():
                actual = subprocess.check_output([str(binary), "get", str(temp / name), digest])
                assert actual == body
        finally:
            for process in processes:
                if process.p.poll() is None:
                    process.stop()
        report = {"state": "PASS", "head": source_head, "tree": source_tree,
            "source_dirty": bool(git("status", "--porcelain")), "binary_sha256": binary_hash,
            "scope": "single_host_independent_repository_node_processes",
            "repository_deployments_claimed": False, "subjects": subjects,
            "fixture_subjects": args.subjects is None, "node_count": len(ids),
            "directed_pairs_tested": len(ids) * (len(ids) - 1), "tls": "TLSv1.3 mutual authentication and certificate pins",
            "terminal_and_bus_share_one_store_owner": True, "wrong_subject_rejected": True,
            "unadmitted_certificate_rejected": True, "wrong_hostname_rejected": True,
            "certificate_identity_substitution_rejected": True, "wrong_router_pin_rejected": True,
            "partition_and_sigkill_replay": True, "byte_exact_receiver_readback": True,
            "original_event_bytes_unchanged": True, "effect_ack_done": False}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
