# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import stat
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/authorization/r11/R11_READ_ONLY_OBSERVATION_DISPATCH_V2.json"
PREDECESSOR = ROOT / "state/authorization/r11/R11_READ_ONLY_OBSERVATION_DISPATCH_V1.json"
HELPER = ROOT / "tools/qikvrt_r11_read_only_observation_dispatch_v2.py"
PAYLOAD_SHA256 = "eae62e7091292174950fc51fc11118871b9c7e2509bb5a40abc27c29c6531f35"
WORKFLOW_BLOB = "5f6a48b993c224f5a1359a3394b7907bb32a54a4"
WORKFLOW_SHA256 = "56aa47f22a8f9048dc1093c486c442ddcdff8e67e8a1801404ad41ba14c78b14"
HELPER_BLOB = "5e78b9ad9ceb1d2846d692933c883565d27a0645"
HELPER_SHA256 = "cbb8a89ad9075e20068d3f9000837c2ccc819eff895661160bd8a9f1564e23aa"


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def load_helper():
    spec = importlib.util.spec_from_file_location("qikvrt_r11_v2_test_helper", HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R11V2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CONTRACT.read_bytes()
        cls.value = json.loads(cls.raw.decode("utf-8"))
        cls.payload = cls.value["authorization_payload"]
        cls.helper = load_helper()

    def test_top_level_digest_and_inert_state(self) -> None:
        self.assertEqual(
            set(self.value),
            {
                "_license", "schema", "contract_id", "state",
                "authorization_payload", "authorization_payload_sha256",
                "effect_boundary", "completion_claims",
            },
        )
        self.assertEqual(self.value["schema"], "qikvrt_r11_read_only_observation_dispatch_contract_v2")
        self.assertEqual(self.value["contract_id"], "qikvrt-r11-read-only-observation-dispatch-20260805-v2")
        self.assertEqual(self.value["state"], "AUTHORIZED_FOR_ONE_NEW_TRUSTED_PROXY_RUN")
        canonical = json.dumps(
            self.payload, ensure_ascii=False, allow_nan=False,
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), PAYLOAD_SHA256)
        self.assertEqual(self.value["authorization_payload_sha256"], PAYLOAD_SHA256)

    def test_predecessor_is_consumed_and_byte_frozen(self) -> None:
        predecessor = self.payload["predecessor"]
        self.assertEqual(predecessor["contract_id"], "qikvrt-r11-read-only-observation-dispatch-20260805-v1")
        self.assertEqual(predecessor["git_blob_sha1"], "f19ea9df13afd465f3c9a32e5e6e3ee43d04a3b0")
        if PREDECESSOR.exists():
            self.assertEqual(git_blob(PREDECESSOR.read_bytes()), predecessor["git_blob_sha1"])
        failed = predecessor["consumed_failed_run"]
        self.assertEqual((failed["run_id"], failed["job_id"], failed["run_attempt"]), (31021322563, 92358456632, 1))
        self.assertEqual(failed["failure_class"], "GITHUB_API_INSTALLATION_RATE_LIMIT_BEFORE_OBSERVATION")
        self.assertEqual((failed["artifact_count"], failed["zenodo_get_count"], failed["external_effect"]), (0, 0, "NONE"))
        self.assertEqual(predecessor["locks"], {
            "rerun": False, "reopen": False, "synchronize": False,
            "head_change": False, "historical_bytes_mutable": False,
        })

    def test_v2_corrects_every_reachable_contract_mismatch(self) -> None:
        observed = {item["field"]: (item["v1"], item["v2"]) for item in self.payload["corrections"]}
        self.assertEqual(observed["observation.target_deposition_id"], (16304099, 21763614))
        self.assertEqual(observed["observation.target_record_id"], (17269164, 21763614))
        self.assertEqual(observed["execution.EXPECTED_CONTROLLER_PARENT"], ("ABSENT", "AUTHORITY_PULL_REQUEST_EVENT_BASE_SHA"))
        self.assertEqual(observed["terminal_report.request_shape"][1], ["api_origin", "method", "path", "count", "redirects_followed"])
        self.assertEqual(observed["controller_github_jobs_query"][1], "EXACT_ACTIONS_RUN_JOBS_PER_PAGE_100_ALLOWLIST")

    def test_exact_proxy_helper_and_c2_bindings(self) -> None:
        proxy = self.payload["proxy"]
        self.assertEqual(proxy["head"], "0c8b3a19b9934ba7f1dd9df68d42c64c53b744e6")
        self.assertEqual(proxy["parent"], "121f2f611eb1a7cf903ca80325d5900aad4f7876")
        self.assertEqual(proxy["workflow_git_blob_sha1"], WORKFLOW_BLOB)
        self.assertEqual(proxy["workflow_sha256"], WORKFLOW_SHA256)
        helper = self.payload["helper"]
        raw = HELPER.read_bytes()
        self.assertEqual((git_blob(raw), hashlib.sha256(raw).hexdigest()), (HELPER_BLOB, HELPER_SHA256))
        self.assertEqual((helper["git_blob_sha1"], helper["sha256"], helper["bytes"]), (HELPER_BLOB, HELPER_SHA256, len(raw)))
        self.assertEqual(helper["mode"], "100755")
        self.assertTrue(stat.S_IMODE(HELPER.stat().st_mode) & stat.S_IXUSR)
        self.assertEqual(self.payload["c2"], {
            "commit": "376e869dc3504929b8913146cb29264d3ac585f3",
            "git_blob_sha1": "d81135af4a14c5fa3d67966761f473569c7d2689",
            "bytes": 23415,
            "sha256": "3114f282d76e453ae0aa9106a0b7481c0be8566bd6b38674922eb3e5f0bc74f4",
            "phase": "record_created", "record_id": 21763614,
            "doi": "10.5281/zenodo.21763614", "must_remain_unchanged": True,
        })

    def test_retry_is_exactly_bounded_and_get_only(self) -> None:
        retry = self.payload["github_get_retry"]
        self.assertEqual(retry["maximum_retries_per_get"], 2)
        self.assertEqual(retry["backoff_seconds"], [15, 45])
        self.assertFalse(retry["non_rate_limit_403_retryable"])
        self.assertFalse(retry["github_mutation_allowed"])
        self.assertFalse(retry["zenodo_retry_allowed"])
        calls: list[str] = []
        sleeps: list[float] = []
        sequence = [
            (403, {"x-ratelimit-remaining": "0"}, json.dumps({"message": "API rate limit exceeded for installation. request id"}).encode()),
            (200, {}, b"{}"),
        ]
        api = self.helper.RetryingGitHubAPI(
            "x" * 20,
            transport=lambda path: (calls.append(path), sequence.pop(0))[1],
            sleeper=sleeps.append,
        )
        status, value = api.request("GET", "/repos/Goldkelch/qik-vrt/git/ref/heads/main")
        self.assertEqual((status, value, len(calls), sleeps), (200, {}, 2, [15.0]))
        with self.assertRaises(SystemExit):
            api.request("POST", "/repos/Goldkelch/qik-vrt/git/refs")

    def test_non_rate_limit_403_and_retry_exhaustion_fail_closed(self) -> None:
        calls: list[str] = []
        api = self.helper.RetryingGitHubAPI(
            "x" * 20,
            transport=lambda path: (calls.append(path), (403, {"x-ratelimit-remaining": "1"}, b'{"message":"forbidden"}'))[1],
            sleeper=lambda _delay: None,
        )
        with self.assertRaises(SystemExit):
            api.request("GET", "/repos/Goldkelch/qik-vrt/git/ref/heads/main")
        self.assertEqual(len(calls), 1)
        calls.clear()
        sleeps: list[float] = []
        limited = (403, {"x-ratelimit-remaining": "0"}, b'{"message":"API rate limit exceeded for installation. retry"}')
        api = self.helper.RetryingGitHubAPI(
            "x" * 20,
            transport=lambda path: (calls.append(path), limited)[1],
            sleeper=sleeps.append,
        )
        with self.assertRaises(SystemExit):
            api.request("GET", "/repos/Goldkelch/qik-vrt/git/ref/heads/main")
        self.assertEqual((len(calls), sleeps), (3, [15.0, 45.0]))

    def test_jobs_query_allowance_is_exact(self) -> None:
        self.helper.RetryingGitHubAPI._validate_path(
            "/repos/Goldkelch/qik-vrt/actions/runs/30779321919/jobs?per_page=100"
        )
        for path in (
            "/repos/Goldkelch/qik-vrt/actions/runs/1/jobs?per_page=50",
            "/repos/Goldkelch/qik-vrt/pulls?state=open",
            "/repos/other/repo/actions/runs/1/jobs?per_page=100",
        ):
            with self.assertRaises(SystemExit):
                self.helper.RetryingGitHubAPI._validate_path(path)

    def test_observation_and_artifact_are_exactly_read_only(self) -> None:
        observation = self.payload["observation"]
        self.assertEqual(observation["path"], "/api/deposit/depositions/21763614")
        self.assertEqual(observation["allowed_methods"], ["GET"])
        self.assertEqual(observation["authenticated_request_count"], 2)
        self.assertFalse(observation["redirects_followed"])
        self.assertEqual(self.payload["artifact"]["artifact_count"], 1)
        self.assertEqual(self.payload["artifact"]["entry_count"], 2)
        self.assertEqual(self.value["effect_boundary"]["terminal_result"], "OBSERVATION_RECEIPT_PERSISTED_BLOCKED")
        self.assertTrue(all(value is False for key, value in self.value["effect_boundary"].items() if key != "terminal_result"))
        self.assertEqual(self.value["completion_claims"], {"pass": False, "final_pass": False, "effect_ack_done": False})

    def test_promotion_is_paired_and_not_automatic(self) -> None:
        promotion = self.payload["promotion_contract"]
        self.assertEqual(promotion["portable_paths"], [
            "state/authorization/r11/R11_READ_ONLY_OBSERVATION_DISPATCH_V2.json",
            "tools/qikvrt_r11_read_only_observation_dispatch_v2.py",
            "tests/test_r11_read_only_observation_dispatch_contract_v2.py",
        ])
        self.assertTrue(promotion["authority_before_mirror"])
        self.assertTrue(promotion["expected_head_bound_promotion_only"])
        self.assertFalse(promotion["unconditional_automatic_merge"])


if __name__ == "__main__":
    unittest.main()
