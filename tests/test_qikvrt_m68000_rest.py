# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Real authenticated HTTP round trips and adversarial MC68000 binding checks."""
from __future__ import annotations

from copy import deepcopy
import http.client
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qikvrt_m68000_runtime import API_PATH, KERNEL_ID, M68000Runtime, RuntimeConflict, digest
from scripts.qikvrt_api_client import execute_m68000
from tests.test_handler_security import API_TOKEN, live_shim
from tools import qikvrt_spark_branch_m68000_compiler as compiler
from tools import qikvrt_spark_branch_work_unit as consumer


def request_for(runtime, flags=252):
    return {
        "schema": "qikvrt_m68000_execution_request_v1", "runtime": deepcopy(runtime.binding),
        "kernel_id": KERNEL_ID, "kernel_sha256": runtime.kernel_sha256,
        "registers": {"d0": flags},
    }


def exchange(address, method, path, body=None, token=API_TOKEN):
    connection = http.client.HTTPConnection(*address, timeout=10)
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    encoded = json.dumps(body).encode() if isinstance(body, dict) else body
    connection.request(method, path, body=encoded, headers=headers)
    response = connection.getresponse()
    result = response.status, json.loads(response.read())
    connection.close()
    return result


class M68000RestTests(unittest.TestCase):
    def setUp(self):
        self.runtime = M68000Runtime(ROOT, "security/qik-vrt")

    def live(self):
        # Reuse the authenticated adapter and its existing ephemeral test server.
        return live_shim(ROOT, m68000_runtime=self.runtime)

    def test_all_256_observations_cross_real_http_and_readback(self):
        runtime = self.runtime
        with self.live() as address:
            status, inventory = exchange(address, "GET", API_PATH + "/kernels")
            self.assertEqual(status, 200)
            self.assertEqual(inventory["kernels"][0]["machine_bytes"], 134)
            expected = [compiler.reference_plan(flags) for flags in range(256)]
            # A server-side Python rule evaluation is forbidden on the warm path.
            with mock.patch.object(compiler, "reference_plan", side_effect=AssertionError("host rule used")):
                for flags in range(256):
                    receipt = execute_m68000(f"http://{address[0]}:{address[1]}",
                                             request_for(runtime, flags), API_TOKEN)
                    self.assertEqual(receipt["registers"]["d0"], expected[flags])
                    self.assertFalse(receipt["effect_ack_done_claimed"])
            observation = {key: bool(252 & (1 << i))
                           for i, key in enumerate(consumer.OBSERVATION_KEYS)}
            with mock.patch.object(consumer, "_load_compiler", side_effect=AssertionError("local fallback")):
                plan = consumer.select_complete_plan(
                    observation, api_url=f"http://{address[0]}:{address[1]}")
            self.assertEqual(plan["plan"]["id"], "MERGE_TO_CLOSE")
            self.assertEqual(plan["execution_transport"], "authenticated_rest")
            self.assertTrue(plan["machine_readback_verified"])
            self.assertFalse(plan["host_effects_executed"])

    def test_http_authorization_scope_and_unknown_routes(self):
        runtime = self.runtime
        with self.live() as address:
            for method, path in [("GET", "/kernels"), ("POST", "/executions"),
                                 ("GET", "/executions/" + "a" * 64)]:
                self.assertEqual(exchange(address, method, API_PATH + path,
                                          request_for(runtime) if method == "POST" else None,
                                          token=None)[0], 401)
            self.assertEqual(exchange(address, "GET", API_PATH + "/kernels?other=1")[0], 404)
            self.assertEqual(exchange(address, "GET", API_PATH + "/executions/" + "a" * 64)[0], 404)
            self.assertEqual(exchange(address, "POST", API_PATH + "/executions",
                                      b'{"schema":"a","schema":"b"}')[0], 400)
            for field in ("repository", "head_sha", "tree_sha", "runtime_sha256"):
                request = request_for(runtime)
                request["runtime"][field] = "predecessor"
                self.assertEqual(exchange(address, "POST", API_PATH + "/executions", request)[0], 409)
            with mock.patch.dict(os.environ, {"QIKVRT_ALLOWED_REPOSITORY": "other/qik-vrt"}):
                self.assertEqual(exchange(address, "GET", API_PATH + "/kernels")[0], 409)

    def test_no_unknown_registers_kernel_or_coercion(self):
        for registers in ({"d0": True}, {"d0": -1}, {"d0": 256}, {"d0": 1.0},
                          {"d0": 0, "d4": 4}, {}, [0]):
            request = request_for(self.runtime)
            request["registers"] = registers
            with self.assertRaises(ValueError):
                self.runtime.execute(request)
        for field, value in (("kernel_id", "unknown"), ("kernel_sha256", "a" * 64),
                             ("program", "4e75")):
            request = request_for(self.runtime)
            request[field] = value
            with self.assertRaises(ValueError):
                self.runtime.execute(request)

    def test_head_or_source_change_invalidates_execution_and_old_readback(self):
        request = request_for(self.runtime)
        self.runtime.execute(request)
        for field in ("head_sha", "tree_sha", "runtime_sha256", "checkout_clean"):
            changed = deepcopy(self.runtime.binding)
            changed[field] = "changed"
            with mock.patch("qikvrt_m68000_runtime.source_binding", return_value=changed):
                with self.assertRaises(RuntimeConflict):
                    self.runtime.execute(request)
                with self.assertRaises(RuntimeConflict):
                    self.runtime.readback(digest(request))

    def test_receipts_are_immutable_bounded_and_replay_does_not_reexecute(self):
        self.runtime.capacity = 1
        request = request_for(self.runtime)
        receipt = self.runtime.execute(request)
        receipt["registers"]["d0"] = 100
        with mock.patch.object(compiler, "execute_kernel", side_effect=AssertionError("reexecuted")):
            replay = self.runtime.execute(request)
        self.assertEqual(replay["registers"]["d0"], 10)
        self.runtime.execute(request_for(self.runtime, 0))
        self.assertIsNone(self.runtime.readback(digest(request)))

    def test_instruction_loop_is_bounded(self):
        with self.assertRaisesRegex(RuntimeError, "budget"):
            compiler.execute_kernel(bytes.fromhex("66fe"), 0)

    def test_client_rejects_network_downgrade_and_missing_token(self):
        for url, token in (("http://example.com", API_TOKEN),
                           ("http://user@localhost", API_TOKEN),
                           ("http://127.0.0.1", "")):
            with self.assertRaises(ValueError):
                execute_m68000(url, request_for(self.runtime), token)

    def test_client_rejects_tampered_receipt_and_readback(self):
        request = request_for(self.runtime)
        receipt = self.runtime.execute(request)

        def response(value):
            item = mock.MagicMock()
            item.__enter__.return_value = item
            item.status = 200
            item.read.return_value = json.dumps(value).encode()
            return item

        bad = deepcopy(receipt)
        bad["registers"]["d0"] = 9
        for results in ([response(bad)], [response(receipt), response(bad)]):
            opener = mock.Mock()
            opener.open.side_effect = results
            with mock.patch("urllib.request.build_opener", return_value=opener):
                with self.assertRaises(ValueError):
                    execute_m68000("http://127.0.0.1", request, API_TOKEN)
        inflated = deepcopy(receipt)
        inflated["approved"] = True
        inflated.pop("receipt_sha256")
        inflated["receipt_sha256"] = digest(inflated)
        opener = mock.Mock()
        opener.open.return_value = response(inflated)
        with mock.patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaisesRegex(ValueError, "unknown fields"):
                execute_m68000("http://127.0.0.1", request, API_TOKEN)

    def test_consumer_rejects_local_head_change_after_readback(self):
        request = request_for(self.runtime)
        receipt = self.runtime.execute(request)
        changed = deepcopy(self.runtime.binding)
        changed["head_sha"] = "a" * 40
        observation = {key: bool(252 & (1 << i))
                       for i, key in enumerate(consumer.OBSERVATION_KEYS)}
        with mock.patch.dict(os.environ, {"QIKVRT_ALLOWED_REPOSITORY": "security/qik-vrt"}), \
                mock.patch("scripts.qikvrt_api_client.execute_m68000", return_value=receipt), \
                mock.patch("qikvrt_m68000_runtime.source_binding", side_effect=[self.runtime.binding, changed]):
            with self.assertRaisesRegex(RuntimeConflict, "consumer source changed"):
                consumer.select_complete_plan(observation, api_url="http://127.0.0.1")

    def test_repository_cli_consumes_enabled_service_and_persists_readback(self):
        repository = os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt")
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        environment = dict(os.environ, QIKVRT_API_TOKEN=API_TOKEN,
                           QIKVRT_API_TOKEN_EXPIRES_UTC="2099-01-01T00:00:00Z",
                           QIKVRT_ALLOWED_REPOSITORY=repository,
                           QIKVRT_API_PRINCIPAL="security-test-owner",
                           QIKVRT_REPO_ROOT=str(ROOT), QIKVRT_API_HOST="127.0.0.1",
                           QIKVRT_API_PORT=str(port), QIKVRT_M68000_ENABLED="1",
                           QIKVRT_REMOTE_ATTESTATION_SECRET="",
                           QIKVRT_TRUSTED_ATTESTATION_SIGNER="")
        # The test server startup event is read once, with a bound; no readiness polling.
        with tempfile.TemporaryDirectory() as directory:
            observation = {key: bool(252 & (1 << i))
                           for i, key in enumerate(consumer.OBSERVATION_KEYS)}
            source = Path(directory) / "observation.json"
            source.write_text(json.dumps(observation))
            with subprocess.Popen([sys.executable, "-B", "src/qikvrt_github_api_shim.py"],
                                  cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True) as service:
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(service.stdout, selectors.EVENT_READ)
                        self.assertTrue(selector.select(timeout=10), "service startup timed out")
                    ready = json.loads(service.stdout.readline())
                    self.assertEqual(ready["listening"], f"127.0.0.1:{port}")
                    start = time.perf_counter_ns()
                    result = subprocess.run(
                        [sys.executable, "-B", "tools/qikvrt_spark_branch_work_unit.py",
                         "--observation", str(source), "--m68000-api-url", f"http://127.0.0.1:{port}",
                         "--json"], cwd=ROOT, env=environment, capture_output=True,
                        text=True, timeout=20, check=True)
                    elapsed_ns = time.perf_counter_ns() - start
                    plan = json.loads(result.stdout)
                    self.assertTrue(plan["machine_readback_verified"])
                    self.assertEqual(plan["plan"]["id"], "MERGE_TO_CLOSE")
                    self.assertFalse(plan["host_effects_executed"])
                    output = os.environ.get("QIKVRT_M68000_RECEIPT_PATH")
                    if output:
                        target = Path(output).resolve()
                        self.assertFalse(target.is_relative_to(ROOT), "receipt belongs outside checkout")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(json.dumps({
                            "schema": "qikvrt_m68000_self_consumption_v1",
                            "measurement": {"cli_post_and_readback_wall_ns": elapsed_ns,
                                            "speedup_established": False},
                            "consumer_plan": plan,
                        }, indent=2, sort_keys=True) + "\n")
                finally:
                    service.terminate()
                    service.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
