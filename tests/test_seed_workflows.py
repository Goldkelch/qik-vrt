#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import qikvrt_workflow_executor as workflow_executor
from tools.qikvrt_seed_common import (
    FetchedJson,
    MAX_INPUT_BYTES,
    SeedError,
    canonical_json_bytes,
    load_nodes,
    parse_json_bytes,
    read_json,
    run_acceptance,
    run_audit_export,
    run_dashboard,
    run_maintenance,
    run_revalidation,
    validate_raw_request_url,
)


GUID = "a84f157a-cef2-4c47-bca9-8f407085bdbe"
SOURCE = "example/node"
SEED = "Goldkelch/qik-vrt"
REQUEST_URL = (
    "https://raw.githubusercontent.com/example/node/refs/tags/v1/"
    "qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json"
)
NOW = dt.datetime(2026, 7, 20, 12, 0, 0, tzinfo=dt.timezone.utc)


def continuity_declaration() -> dict[str, object]:
    return {
        "schema": "qikvrt_workflow_executor_mesh_continuity_declaration_v1",
        "receipt_path": "state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json",
        "receipt_url": workflow_executor.expected_node_receipt_url(SOURCE, "main"),
        "acceptance_required": True,
    }


class FakeFetcher:
    def __init__(self, documents: dict[str, dict[str, object]]) -> None:
        self.documents = documents
        self.calls: list[str] = []

    def __call__(self, url: str) -> FetchedJson:
        self.calls.append(url)
        if url not in self.documents:
            raise SeedError(f"fixture has no response for {url}")
        raw = canonical_json_bytes(self.documents[url])
        return FetchedJson(self.documents[url], hashlib.sha256(raw).hexdigest())


def request_document() -> dict[str, object]:
    return {
        "version": "2.13.4",
        "event": "QIKVRT_NODE_ONBOARDING_REQUEST",
        "role": "node",
        "repository_guid": GUID,
        "source_repository": SOURCE,
        "seed_repository": SEED,
        "seed_url": f"https://github.com/{SEED}",
        "automatic_after_setup": True,
        "no_further_human_machine_interaction_after_setup": True,
        "authorized_manifest_graph_only": True,
        "no_global_scanning": True,
        "no_self_propagation": True,
        "no_remote_mutation_without_authorization": True,
        "workflow_executor_continuity": continuity_declaration(),
    }


def remote_documents(node_state_ref: str = "main") -> dict[str, dict[str, object]]:
    prefix = (
        f"https://raw.githubusercontent.com/{SOURCE}/{node_state_ref}/"
        "qikvrt/runtime/onboarding/"
    )
    boundaries = {
        "no_global_scanning": True,
        "no_self_propagation": True,
        "no_remote_mutation_without_authorization": True,
    }
    return {
        REQUEST_URL: request_document(),
        prefix + "NODE_HEALTH.json": {
            "qikvrt_event": "NODE_HEALTH_HEARTBEAT",
            "guid": GUID,
            "repository": SOURCE,
            "seed_repository": SEED,
            "node_branch": "main",
            "node_state_ref": node_state_ref,
            "status": "ACTIVE",
            "heartbeat_utc": "2026-07-20T11:50:00Z",
            "expires_utc": "2026-07-21T12:00:00Z",
            "boundaries": boundaries,
        },
        prefix + "SEED_ACCEPTANCE_STATUS.json": {
            "qikvrt_event": "NODE_ACK_OF_SEED_ACCEPTANCE",
            "guid": GUID,
            "repository": SOURCE,
            "seed_repository": SEED,
            "node_branch": "main",
            "node_state_ref": node_state_ref,
            "status": "ACCEPTED_BY_SEED",
        },
        prefix + "NODE_REGISTRATION_RENEWAL.json": {
            "qikvrt_event": "NODE_REGISTRATION_RENEWAL",
            "guid": GUID,
            "repository": SOURCE,
            "seed_repository": SEED,
            "node_branch": "main",
            "node_state_ref": node_state_ref,
        },
        workflow_executor.expected_node_receipt_url(SOURCE, "main"): workflow_executor.build_node_receipt(
            SOURCE,
            "main",
        ),
    }


class SeedWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "registry/node_request_queue").mkdir(parents=True)
        (self.root / "registry/KNOWN_NODE_REQUESTS.tsv").write_text(
            "# guid\tsource_repo\tseed_repo\trequest_url\tnode_branch\tnode_state_ref\theartbeat_ttl_minutes\tlifecycle_policy\n"
            f"{GUID}\t{SOURCE}\t{SEED}\t{REQUEST_URL}\tmain\tmain\t1500\tACTIVE\n",
            encoding="utf-8",
        )
        (self.root / "registry/NODE_POLICY.tsv").write_text(
            f"# guid\tpolicy_status\treason\n{GUID}\tACTIVE\ttest authorization\n",
            encoding="utf-8",
        )
        (self.root / "registry/node_request_queue/OPEN_NODE_REQUESTS.tsv").write_text(
            "# empty queue\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def accept(self) -> None:
        result = run_acceptance(
            self.root,
            "accept-1",
            FakeFetcher(remote_documents()),
            now=NOW,
        )
        self.assertEqual("PASS", result["status"])

    def move_node_to_future_queue(self) -> None:
        known = self.root / "registry/KNOWN_NODE_REQUESTS.tsv"
        queue = self.root / "registry/node_request_queue/OPEN_NODE_REQUESTS.tsv"
        row = next(line for line in known.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))
        known.write_text("# guid\tsource_repo\tseed_repo\trequest_url\tnode_branch\tnode_state_ref\theartbeat_ttl_minutes\tlifecycle_policy\n", encoding="utf-8")
        queue.write_text(
            "# guid\tsource_repo\tseed_repo\trequest_url\tnode_branch\tnode_state_ref\theartbeat_ttl_minutes\tlifecycle_policy\n"
            + row
            + "\n",
            encoding="utf-8",
        )

    def test_duplicate_json_keys_and_non_object_documents_are_rejected(self) -> None:
        with self.assertRaises(SeedError):
            parse_json_bytes(b'{"a":1,"a":2}', "duplicate")
        with self.assertRaises(SeedError):
            parse_json_bytes(b"[]", "array")

    def test_local_registry_symlink_is_rejected(self) -> None:
        policy = self.root / "registry/NODE_POLICY.tsv"
        external = self.root / "external-policy.tsv"
        external.write_text(policy.read_text(encoding="utf-8"), encoding="utf-8")
        policy.unlink()
        try:
            os.symlink(external, policy)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are unavailable")
        with self.assertRaisesRegex(SeedError, "symlink"):
            load_nodes(self.root, SEED)

    def test_tsv_requires_exact_columns_explicit_policy_and_unique_guid(self) -> None:
        queue = self.root / "registry/node_request_queue/OPEN_NODE_REQUESTS.tsv"
        queue.write_text(
            f"{GUID}\t{SOURCE}\t{SEED}\t{REQUEST_URL}\tmain\tmain\t1500\tACTIVE\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SeedError, "duplicate node GUID"):
            load_nodes(self.root, SEED)

        queue.write_text("not\tenough\tfields\n", encoding="utf-8")
        with self.assertRaisesRegex(SeedError, "expected exactly 8"):
            load_nodes(self.root, SEED)

    def test_request_url_is_bound_to_declared_repository(self) -> None:
        with self.assertRaises(SeedError):
            validate_raw_request_url(
                "https://raw.githubusercontent.com/attacker/repo/main/qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json",
                SOURCE,
            )
        with self.assertRaises(SeedError):
            validate_raw_request_url(REQUEST_URL + "?download=1", SOURCE)
        with self.assertRaises(SeedError):
            validate_raw_request_url(
                "https://raw.githubusercontent.com:not-a-port/example/node/main/qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json",
                SOURCE,
            )

    def test_committed_mirror_liveness_uses_a_role_local_state_ref(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        state_branch = "state/mirror-node-a84f157a-v1"
        known = (repository / "registry/KNOWN_NODE_REQUESTS.tsv").read_text(encoding="utf-8")
        self.assertIn(f"\tmain\t{state_branch}\t1500\tACTIVE\n", known)

        entry = read_json(repository / f"registry/nodes/{GUID}.json")
        self.assertEqual("main", entry["node_branch"])
        self.assertEqual(state_branch, entry["node_state_ref"])

        index = read_json(repository / "registry/NODEMESH_INDEX.json")
        node = next(item for item in index["nodes"] if item["guid"] == GUID)
        self.assertEqual("main", node["node_branch"])
        self.assertEqual(state_branch, node["node_state_ref"])
        url_prefix = f"https://raw.githubusercontent.com/ingolf-lohmann/qik-vrt/{state_branch}/"
        self.assertEqual(
            {url_prefix + "qikvrt/runtime/onboarding/" + filename for filename in (
                "NODE_HEALTH.json",
                "SEED_ACCEPTANCE_STATUS.json",
                "NODE_REGISTRATION_RENEWAL.json",
            )},
            {node["node_health_url"], node["node_ack_url"], node["node_renewal_url"]},
        )
        self.assertNotIn("/main/qikvrt/runtime/onboarding/", json.dumps(node, sort_keys=True))

    def test_state_ref_separation_preserves_main_bound_continuity(self) -> None:
        state_ref = "state/example-node-liveness-v1"
        known = self.root / "registry/KNOWN_NODE_REQUESTS.tsv"
        known.write_text(
            known.read_text(encoding="utf-8").replace(
                "\tmain\tmain\t1500\tACTIVE\n",
                f"\tmain\t{state_ref}\t1500\tACTIVE\n",
            ),
            encoding="utf-8",
        )
        self.move_node_to_future_queue()
        documents = remote_documents(state_ref)
        continuity_url = workflow_executor.expected_node_receipt_url(SOURCE, "main")
        self.assertIn(continuity_url, documents)

        acceptance = run_acceptance(
            self.root,
            "state-ref-acceptance",
            FakeFetcher(documents),
            now=NOW,
        )
        self.assertEqual("PASS", acceptance["status"])
        entry = read_json(self.root / f"registry/nodes/{GUID}.json")
        self.assertEqual("main", entry["node_branch"])
        self.assertEqual(state_ref, entry["node_state_ref"])
        self.assertEqual(
            continuity_url,
            entry["workflow_executor_continuity"]["receipt_url"],
        )

        maintenance = run_maintenance(
            self.root,
            "state-ref-maintenance",
            FakeFetcher(documents),
            now=NOW,
        )
        self.assertEqual("PASS", maintenance["status"])
        node = maintenance["nodes"][0]
        self.assertEqual("main", node["node_branch"])
        self.assertEqual(state_ref, node["node_state_ref"])
        index = read_json(self.root / "registry/NODEMESH_INDEX.json")
        index_node = index["nodes"][0]
        for key in ("node_health_url", "node_ack_url", "node_renewal_url"):
            self.assertIn(f"/{state_ref}/qikvrt/runtime/onboarding/", index_node[key])

    def test_each_liveness_record_rejects_state_ref_drift(self) -> None:
        self.accept()
        for index, (filename, source) in enumerate((
            ("NODE_HEALTH.json", "health"),
            ("SEED_ACCEPTANCE_STATUS.json", "ack"),
            ("NODE_REGISTRATION_RENEWAL.json", "renewal"),
        )):
            with self.subTest(filename=filename):
                documents = remote_documents()
                url = next(url for url in documents if url.endswith(filename))
                documents[url]["node_state_ref"] = "state/unbound-other-node"
                result = run_maintenance(
                    self.root,
                    f"state-ref-drift-{index}",
                    FakeFetcher(documents),
                    now=NOW,
                )
                self.assertEqual("CONTINUE", result["status"])
                self.assertIn(source, {error["source"] for error in result["nodes"][0]["errors"]})

    def test_acceptance_is_transactional_and_counts_validation_failure(self) -> None:
        documents = remote_documents()
        documents[REQUEST_URL] = {**request_document(), "no_global_scanning": "true"}
        result = run_acceptance(
            self.root,
            "blocked-1",
            FakeFetcher(documents),
            now=NOW,
        )
        self.assertEqual("BLOCK", result["status"])
        self.assertEqual(1, result["fail_count"])
        self.assertFalse((self.root / f"registry/nodes/{GUID}.json").exists())
        evidence = read_json(self.root / "evidence/seed_acceptance/runs/blocked-1.json")
        self.assertEqual("BLOCK", evidence["status"])

    def test_acceptance_writes_valid_bound_evidence_and_ledger(self) -> None:
        self.accept()
        entry = read_json(self.root / f"registry/nodes/{GUID}.json")
        self.assertEqual("qikvrt_seed_registry_entry_v2", entry["schema"])
        self.assertEqual("main", entry["node_state_ref"])
        self.assertEqual(1500, entry["heartbeat_ttl_minutes"])
        self.assertRegex(entry["node_request_sha256"], r"^[0-9a-f]{64}$")
        lines = (self.root / "ledger/NODE_REGISTRATION_LEDGER.jsonl").read_bytes().splitlines()
        self.assertEqual(1, len(lines))
        self.assertEqual(GUID, parse_json_bytes(lines[0], "ledger")["guid"])

    def test_future_queue_node_requires_exact_workflow_executor_continuity_receipt(self) -> None:
        self.move_node_to_future_queue()
        result = run_acceptance(
            self.root,
            "continuity-1",
            FakeFetcher(remote_documents()),
            now=NOW,
        )
        self.assertEqual("PASS", result["status"])
        entry = read_json(self.root / f"registry/nodes/{GUID}.json")
        continuity = entry["workflow_executor_continuity"]
        self.assertEqual(
            continuity["receipt_url"],
            workflow_executor.expected_node_receipt_url(SOURCE, "main"),
        )
        self.assertRegex(continuity["receipt_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(continuity["validation"], "STRUCTURAL_ACCEPTANCE_ONLY")

    def test_future_queue_node_without_continuity_declaration_is_blocked(self) -> None:
        self.move_node_to_future_queue()
        documents = remote_documents()
        request = dict(documents[REQUEST_URL])
        del request["workflow_executor_continuity"]
        documents[REQUEST_URL] = request
        result = run_acceptance(self.root, "continuity-blocked", FakeFetcher(documents), now=NOW)
        self.assertEqual("BLOCK", result["status"])
        self.assertEqual(result["fail_count"], 1)
        self.assertIn("workflow executor continuity", result["errors"][0]["error"])

    def test_corrupt_ledger_blocks_before_registry_mutation(self) -> None:
        ledger = self.root / "ledger/NODE_REGISTRATION_LEDGER.jsonl"
        ledger.parent.mkdir(parents=True)
        ledger.write_text("not-json\n", encoding="utf-8")
        with self.assertRaises(SeedError):
            run_acceptance(
                self.root,
                "corrupt-ledger",
                FakeFetcher(remote_documents()),
                now=NOW,
            )
        self.assertFalse((self.root / f"registry/nodes/{GUID}.json").exists())

        ledger.write_bytes(b"x" * (16 * MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(SeedError, "exceeds"):
            run_acceptance(
                self.root,
                "oversized-ledger",
                FakeFetcher(remote_documents()),
                now=NOW,
            )
        self.assertFalse((self.root / f"registry/nodes/{GUID}.json").exists())

    def test_maintenance_uses_ttl_and_revalidates_remote_identity(self) -> None:
        self.accept()
        result = run_maintenance(
            self.root,
            "maint-1",
            FakeFetcher(remote_documents()),
            now=NOW,
        )
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, result["active_count"])
        node = result["nodes"][0]
        self.assertEqual("FRESH", node["heartbeat_status"])
        # Claimed expiry is capped by the allowlisted 1500-minute TTL.
        self.assertEqual("2026-07-21T12:00:00Z", node["effective_expires_utc"])
        run_revalidation(self.root, "revalidate-1", now=NOW)
        revalidation = read_json(self.root / "registry/NODEMESH_REVALIDATION.json")
        self.assertEqual("PASS", revalidation["status"])

    def test_missing_ack_is_visible_and_never_reported_as_pass(self) -> None:
        self.accept()
        documents = remote_documents()
        ack_url = next(url for url in documents if url.endswith("SEED_ACCEPTANCE_STATUS.json"))
        del documents[ack_url]
        result = run_maintenance(
            self.root,
            "maint-blocked",
            FakeFetcher(documents),
            now=NOW,
        )
        self.assertEqual("CONTINUE", result["status"])
        self.assertEqual(0, result["active_count"])
        self.assertEqual(1, result["error_count"])
        revalidation = run_revalidation(self.root, "revalidate-blocked", now=NOW)
        self.assertEqual("CONTINUE", revalidation["status"])

    def test_revalidation_detects_counter_tampering(self) -> None:
        self.accept()
        run_maintenance(self.root, "maint-2", FakeFetcher(remote_documents()), now=NOW)
        status_path = self.root / "registry/NODEMESH_STATUS.json"
        status = read_json(status_path)
        status["active_count"] = 999
        status_path.write_bytes(canonical_json_bytes(status))
        with self.assertRaisesRegex(SeedError, "active_count"):
            run_revalidation(self.root, "revalidate-tampered", now=NOW)

    def test_dashboard_and_audit_require_current_pass_revalidation(self) -> None:
        self.accept()
        run_maintenance(self.root, "maint-3", FakeFetcher(remote_documents()), now=NOW)
        run_revalidation(self.root, "revalidate-3", now=NOW)
        dashboard = run_dashboard(self.root, "dashboard-3", now=NOW)
        audit = run_audit_export(self.root, "audit-3", now=NOW)
        self.assertEqual("PASS", dashboard["status"])
        self.assertEqual("PASS", audit["status"])
        self.assertIn("source_status_run_id", (self.root / "docs/QIKVRT_MESH_DASHBOARD.md").read_text())
        self.assertEqual(
            "qikvrt_seed_mesh_audit_export_v2",
            read_json(self.root / "audit/QIKVRT_MESH_AUDIT_SUMMARY.json")["schema"],
        )

    def test_dashboard_build_binds_every_main_push_to_exact_head_artifact(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        workflow = (
            repository / ".github/workflows/qikvrt_seed_dashboard_publish.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("push:\n    branches: [main]", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)
        self.assertIn('actual_head="$(git rev-parse --verify HEAD^{commit})"', workflow)
        self.assertIn('test "$actual_head" = "$EXPECTED_HEAD"', workflow)
        self.assertIn('actual_tree="$(git show -s --format=%T HEAD)"', workflow)
        self.assertIn("dashboard-exact-head-binding.json", workflow)
        self.assertIn('"source_head": os.environ["EXPECTED_HEAD"]', workflow)
        self.assertIn('"source_tree": os.environ["ACTUAL_TREE"]', workflow)
        self.assertIn("qikvrt_seed_dashboard_exact_head_binding_v1", workflow)

    def test_seed_workflows_are_pinned_read_only_and_do_not_push(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        for workflow in sorted((repository / ".github/workflows").glob("qikvrt_seed_*.yml")):
            text = workflow.read_text(encoding="utf-8")
            self.assertIn("contents: read", text, workflow.name)
            self.assertNotIn("contents: write", text, workflow.name)
            self.assertIn("persist-credentials: false", text, workflow.name)
            self.assertNotRegex(text, r"actions/(?:checkout|upload-artifact)@v\d")
            self.assertNotRegex(text, r"\bgit (?:push|pull|commit)\b")


if __name__ == "__main__":
    unittest.main()
