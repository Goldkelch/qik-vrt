#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import copy
import unittest
from unittest import mock

from tools import qikvrt_ruleset_outbox as outbox


class MemoryBackend:
    repository = "Goldkelch/qik-vrt"

    def __init__(self, *, preinitialized=True):
        self.heads = {}
        self.last_lane = "ruleset-dispatch"
        self.main_head = "a" * 40
        self.commits = {}
        self.counter = 1
        self.read_paths = []
        self.update_calls = 0
        self.protection_ok = {lane: True for lane in outbox.LANES}
        self.authority_environment_ok = {lane: True for lane in outbox.LANES}
        self.authority_environment_reads = []
        self.last_authority_readback = None
        self.writer_scope_ok = {lane: True for lane in outbox.LANES}
        if preinitialized:
            for lane in outbox.LANES:
                commit = self.build_root(outbox._root_files(lane), "external genesis")
                self.heads[lane] = commit

    @property
    def head(self):
        return self.heads.get(self.last_lane)

    def _sha(self):
        value = f"{self.counter:040x}"
        self.counter += 1
        return value

    def get_ledger_head(self, lane):
        self.last_lane = lane
        return self.heads.get(lane)

    def verify_ledger_protection(self, lane):
        if not self.protection_ok.get(lane, False):
            raise outbox.OutboxBlock("OUTBOX_LEDGER_PROTECTION_NOT_VERIFIED")

    def verify_authority_environment(self, lane):
        self.authority_environment_reads.append(lane)
        if not self.authority_environment_ok.get(lane, False):
            raise outbox.OutboxBlock(
                "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED"
            )
        self.last_authority_readback = {
            "schema": outbox.AUTHORITY_READBACK_SCHEMA,
            "state": "VERIFIED_FOR_THIS_EFFECT_ONLY",
            "repository": self.repository,
            "lane": lane,
            "repository_owner": {
                "login": "Goldkelch",
                "type": "User",
                "id": 293941403,
            },
            "environment": outbox.AUTHORITY_ENVIRONMENT,
            "deployment_branch": "main",
            "protection_rules_present": True,
            "environment_secret_names_present": [
                outbox.AUDITOR_SECRET_NAME,
                outbox.WRITER_SECRET_NAME,
            ],
            "repository_scope_fallback_names_absent": True,
            "organization_scope_fallback_names_absent": True,
            "organization_scope_readback": "NOT_APPLICABLE_USER_OWNER",
            "writer_actor_id": 42,
            "secret_values_observed": False,
            "external_configuration_claimed_by_repository": False,
        }
        return self.last_authority_readback

    def verify_writer_scope(self, lane):
        if not self.writer_scope_ok.get(lane, False):
            raise outbox.OutboxBlock("OUTBOX_LEDGER_WRITER_SCOPE_NOT_VERIFIED")

    def get_main_head(self):
        return self.main_head

    def read_file(self, commit, path):
        self.read_paths.append(path)
        return self.commits[commit].get(path)

    def build_root(self, files, _message):
        commit = self._sha()
        self.commits[commit] = dict(files)
        return commit

    def build_commit(self, parent, files, _message):
        commit = self._sha()
        self.commits[commit] = {**self.commits[parent], **dict(files)}
        return commit

    def update_ledger_ref(self, lane, commit):
        self.update_calls += 1
        self.last_lane = lane
        self.heads[lane] = commit


class OneRaceBackend(MemoryBackend):
    def __init__(self):
        super().__init__()
        self.race_enabled = False
        self.raced = False

    def update_ledger_ref(self, lane, commit):
        self.update_calls += 1
        self.last_lane = lane
        if self.race_enabled and not self.raced:
            self.raced = True
            rival = self._sha()
            self.commits[rival] = {
                **self.commits[self.heads[lane]],
                "unrelated/rival.json": outbox.canonical_bytes({"rival": True}),
            }
            self.heads[lane] = rival
            raise RuntimeError("non-fast-forward")
        self.heads[lane] = commit


class ManyRaceBackend(MemoryBackend):
    def __init__(self, races):
        super().__init__()
        self.races_remaining = races

    def update_ledger_ref(self, lane, commit):
        self.update_calls += 1
        self.last_lane = lane
        if self.races_remaining:
            self.races_remaining -= 1
            rival = self._sha()
            self.commits[rival] = {
                **self.commits[self.heads[lane]],
                f"unrelated/rival-{self.races_remaining}.json": outbox.canonical_bytes(
                    {"rival": self.races_remaining}
                ),
            }
            self.heads[lane] = rival
            raise RuntimeError("non-fast-forward")
        self.heads[lane] = commit


class CallbackRaceBackend(MemoryBackend):
    def __init__(self):
        super().__init__()
        self.race_callback = None
        self.raced = False

    def update_ledger_ref(self, lane, commit):
        self.update_calls += 1
        self.last_lane = lane
        if self.race_callback is not None and not self.raced:
            self.raced = True
            changes = self.race_callback(self, lane)
            if changes is not None:
                rival = self.build_commit(self.heads[lane], changes, "semantic race")
                self.heads[lane] = rival
            raise RuntimeError("non-fast-forward")
        self.heads[lane] = commit


class ProtectionProbe(outbox.GitHubLedgerBackend):
    def __init__(self, rules, ruleset):
        super().__init__("Goldkelch/qik-vrt", "test-token")
        self.rules = rules
        self.ruleset = ruleset

    def _request_list(self, _endpoint):
        return copy.deepcopy(self.rules)

    def _request(self, method, endpoint, payload=None, **_kwargs):
        if method == "GET" and endpoint.startswith("rulesets/"):
            return copy.deepcopy(self.ruleset)
        raise AssertionError((method, endpoint, payload))


class AuthorityProbe(outbox.GitHubLedgerBackend):
    def __init__(
        self,
        *,
        environment_secret_names=(
            outbox.AUDITOR_SECRET_NAME,
            outbox.WRITER_SECRET_NAME,
        ),
        repository_secret_names=(),
        organization_secret_names=(),
        branch_policies=({"name": "main", "type": "branch"},),
        protection_rules=({"type": "required_reviewers"},),
        owner_login="Goldkelch",
        owner_type="User",
        owner_id=293941403,
        org_error=None,
    ):
        super().__init__("Goldkelch/qik-vrt", "auditor-token")
        self.environment_secret_names = tuple(environment_secret_names)
        self.repository_secret_names = tuple(repository_secret_names)
        self.organization_secret_names = tuple(organization_secret_names)
        self.branch_policies = tuple(branch_policies)
        self.protection_rules = tuple(protection_rules)
        self.owner_login = owner_login
        self.owner_type = owner_type
        self.owner_id = owner_id
        self.org_error = org_error

    @staticmethod
    def _inventory(key, values):
        return {
            "total_count": len(values),
            key: [{"name": value} for value in values],
        }

    def _request(self, method, endpoint, payload=None, **_kwargs):
        if method != "GET" or payload is not None:
            raise AssertionError((method, endpoint, payload))
        base = "environments/qikvrt-outbox-ledger-authority"
        if endpoint == base:
            return {
                "name": outbox.AUTHORITY_ENVIRONMENT,
                "deployment_branch_policy": {
                    "protected_branches": False,
                    "custom_branch_policies": True,
                },
                "protection_rules": list(self.protection_rules),
            }
        if endpoint.startswith(base + "/deployment-branch-policies?"):
            return {
                "total_count": len(self.branch_policies),
                "branch_policies": [dict(item) for item in self.branch_policies],
            }
        if endpoint.startswith(base + "/secrets?"):
            return self._inventory("secrets", self.environment_secret_names)
        if endpoint.startswith("actions/secrets?"):
            return self._inventory("secrets", self.repository_secret_names)
        raise AssertionError((method, endpoint, payload))

    def _request_absolute(self, url):
        if url == "https://api.github.com/repos/Goldkelch/qik-vrt":
            return {
                "owner": {
                    "login": self.owner_login,
                    "type": self.owner_type,
                    "id": self.owner_id,
                }
            }
        if url.startswith("https://api.github.com/orgs/Goldkelch/actions/secrets?"):
            if self.org_error is not None:
                raise self.org_error
            return self._inventory("secrets", self.organization_secret_names)
        raise AssertionError(url)


def payload(lane="ruleset-dispatch", *, run_id=101, subject="one"):
    producer = {
        "workflow_path": ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
        "workflow_sha": "a" * 40,
        "workflow_id": 17,
        "run_id": run_id,
        "run_attempt": 1,
        "event": "workflow_run",
    }
    exact_subject = {
        "pull_request": 935,
        "head_repository": "Goldkelch/qik-vrt",
        "head_ref": "authority-pr931",
        "head_sha": "b" * 40,
        "head_tree_sha": "c" * 40,
        "base_ref": "main",
        "base_sha": "d" * 40,
    }
    targets = {
        "ruleset-dispatch": (88, ".github/workflows/qikvrt_ruleset_reconcile.yml", "repository_dispatch"),
        "reconciler-rerun": (88, ".github/workflows/qikvrt_ruleset_reconcile.yml", "repository_dispatch"),
        "requested-review-dispatch": (77, ".github/workflows/qikvrt_requested_review_executor.yml", "workflow_dispatch"),
        "exact-head-dispatch": (66, ".github/workflows/qikvrt_autonomous_exact_head_verify.yml", "repository_dispatch"),
        "exact-review-dispatch": (77, ".github/workflows/qikvrt_requested_review_executor.yml", "workflow_dispatch"),
        "mesh-review-successor-dispatch": (77, ".github/workflows/qikvrt_requested_review_executor.yml", "workflow_dispatch"),
    }
    original_reconciler_child = {
        "run_id": 91,
        "run_attempt": 1,
        "workflow_id": 88,
        "workflow_path": ".github/workflows/qikvrt_ruleset_reconcile.yml",
        "event": "repository_dispatch",
        "repository": "Goldkelch/qik-vrt",
        "head_sha": "a" * 40,
        "status": "completed",
        "conclusion": "failure",
        "display_title": (
            "QIKVRT ruleset intent=" + "e" * 64
            + " seq=7 transport-attempt=1"
        ),
    }
    requests = {
        "ruleset-dispatch": {
            "event_type": "qikvrt_ruleset_reconcile",
            "client_payload": {
                "schema": "qikvrt_ruleset_reconcile_dispatch_v1",
                "repository": "Goldkelch/qik-vrt",
                "source": {"run_id": run_id},
                "binding": {"main_head_sha": "a" * 40},
                "review": {"pull_request": 935},
                "causal": {"d0": 2},
            },
        },
        "reconciler-rerun": {
            "schema": "qikvrt_ruleset_reconciler_rerun_request_v1",
            "repository": "Goldkelch/qik-vrt",
            "reconciler_run_id": 91,
            "reconciler_run_attempt": 1,
            "method": "POST",
            "endpoint": "repos/Goldkelch/qik-vrt/actions/runs/91/rerun",
            "target_attempt": 2,
            "original_child": original_reconciler_child,
            "original_child_sha256": outbox.digest(original_reconciler_child),
            "productive_effect": False,
        },
        "requested-review-dispatch": {
            "ref": "main",
            "return_run_details": True,
            "inputs": {
                "pr": "935",
                "head": "b" * 40,
                "fingerprint": "c" * 64,
                "evaluator_sha": "a" * 40,
            },
        },
        "exact-head-dispatch": {
            "event_type": "qikvrt_autonomous_exact_head_verify",
            "client_payload": {
                "schema": "qikvrt_autonomous_exact_head_verify_dispatch_v1",
                "repository": "Goldkelch/qik-vrt",
                "subject": exact_subject,
                "producer": {
                    key: producer[key]
                    for key in (
                        "run_id",
                        "run_attempt",
                        "workflow_id",
                        "workflow_path",
                        "workflow_sha",
                    )
                },
                "causal": {
                    "attempt": 1,
                    "d0": 2,
                    "state": "REOBSERVE",
                    "productive_effect": False,
                },
            },
        },
        "exact-review-dispatch": {
            "ref": "main",
            "return_run_details": True,
            "inputs": {
                "pr": "935",
                "head": "b" * 40,
                "fingerprint": "c" * 64,
                "evaluator_sha": "a" * 40,
            },
        },
        "mesh-review-successor-dispatch": {
            "ref": "main",
            "return_run_details": True,
            "inputs": {
                "pr": "935",
                "head": "b" * 40,
                "fingerprint": "c" * 64,
                "evaluator_sha": "a" * 40,
            },
        },
    }
    value = {
        "schema": outbox.PAYLOAD_SCHEMA,
        "repository": "Goldkelch/qik-vrt",
        "lane": lane,
        "main_head_sha": "a" * 40,
        "producer": producer,
        "subject": exact_subject if lane == "exact-head-dispatch" else {"key": subject},
        "target": {
            "workflow_id": targets[lane][0],
            "workflow_path": targets[lane][1],
            "event": targets[lane][2],
        },
        "request": requests[lane],
        "causal": {"d0": 2, "state": "REOBSERVE", "productive_effect": False},
    }
    if lane in outbox.REVIEW_TRANSPORT_LANES:
        return outbox.seal_review_transport_payload(value)
    return value


def artifact(value):
    normalized = outbox.validate_payload(value)
    return {
        "id": normalized["producer"]["run_id"] + 1000,
        "name": f"intent-{normalized['producer']['run_id']}",
        "archive_sha256": "d" * 64,
        "payload_sha256": outbox.sha256_bytes(outbox.canonical_bytes(normalized)),
        "producer_run_id": normalized["producer"]["run_id"],
        "producer_run_attempt": normalized["producer"]["run_attempt"],
        "producer_workflow_id": normalized["producer"]["workflow_id"],
    }


def completion_evidence(child, business_artifact, *, job_name="terminal"):
    return {
        "schema": outbox.COMPLETION_EVIDENCE_SCHEMA,
        "run_id": child["run_id"],
        "run_attempt": child["run_attempt"],
        "jobs_total_count": 1,
        "terminal_job": {
            "id": child["run_id"] + 5000,
            "name": job_name,
            "run_attempt": child["run_attempt"],
            "status": "completed",
            "conclusion": child["conclusion"],
        },
        "artifact": business_artifact,
        "verified": True,
        "productive_effect": False,
    }


def child_retry_evidence(intent, acceptance, *, observed_child=None):
    locator = dict(acceptance["child"])
    observed = dict(
        observed_child
        or {**locator, "status": "completed", "conclusion": "cancelled"}
    )
    return {
        "schema": outbox.CHILD_RETRY_EVIDENCE_SCHEMA,
        "lane": intent["lane"],
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "transport_attempt": 1,
        "classification": "ZERO_JOB_CONCURRENCY_CANCELLED",
        "first_blocker": "ATTEMPT_1_ZERO_JOB_CONCURRENCY_CANCELLED",
        "accepted_child_sha256": acceptance["child_sha256"],
        "observed_terminal_child": observed,
        "observed_terminal_child_sha256": outbox.digest(observed),
        "jobs_total_count": 0,
        "verified": True,
        "productive_effect": False,
    }


def terminal_evidence(value):
    return {
        "schema": outbox.TERMINAL_EVIDENCE_SCHEMA,
        "completion_claims": outbox.empty_completion_claims(),
        **value,
    }


def authority_observer(
    *, run_id=8801, run_attempt=1, workflow_sha=None, lane=None
):
    if lane == "mesh-review-successor-dispatch":
        return {
            "workflow_path": (
                ".github/workflows/qikvrt_mesh_review_successor_completion.yml"
            ),
            "workflow_sha": workflow_sha or "a" * 40,
            "workflow_id": 902,
            "run_id": run_id,
            "run_attempt": run_attempt,
            "event": "schedule",
        }
    return {
        "workflow_path": (
            ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ),
        "workflow_sha": workflow_sha or "a" * 40,
        "workflow_id": 901,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "event": "schedule",
    }


def persist_authority_observation(
    backend, intent, observation, *, run_id=8801, run_attempt=1
):
    if observation.get("blocker") == "OUTBOX_EVALUATOR_SUPERSEDED":
        backend.main_head = observation["observed_main_head_sha"]
    blocker = observation["blocker"]
    if blocker == "SOURCE_ATTEMPT_1_ACTION_REQUIRED":
        producer = {
            "workflow_path": (
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            "workflow_sha": "a" * 40,
            "workflow_id": 903,
            "run_id": run_id,
            "run_attempt": run_attempt,
            "event": "schedule",
        }
    else:
        producer = authority_observer(
            run_id=run_id,
            run_attempt=run_attempt,
            lane=intent["lane"],
            workflow_sha=(
                observation.get("observed_main_head_sha")
                if blocker == "OUTBOX_EVALUATOR_SUPERSEDED"
                else None
            ),
        )
    receipt = outbox.record_authority_observation(
        backend,
        lane=intent["lane"],
        sequence=intent["sequence"],
        observation=observation,
        producer=producer,
        artifact={
            "id": run_id + 1000,
            "name": (
                f"qikvrt-outbox-authority-observation-{intent['lane']}-"
                f"{intent['sequence']}-{blocker}-run-{run_id}-"
                f"attempt-{run_attempt}"
            ),
            "archive_sha256": "e" * 64,
            "payload_sha256": outbox.sha256_bytes(
                outbox.canonical_bytes(observation)
            ),
            "producer_run_id": run_id,
            "producer_run_attempt": run_attempt,
            "producer_workflow_id": producer["workflow_id"],
        },
    )
    return receipt["record"]


def ambiguity_exhaustion(intent, blocker, record, *, attempts=(1,)):
    observation = record["observation"]
    return {
        "schema": outbox.EXHAUSTION_SCHEMA,
        "lane": intent["lane"],
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "mode": "AMBIGUOUS_OR_DRIFT",
        "attempts": list(attempts),
        "first_blocker": blocker,
        "authority_observation_sha256": outbox.digest(record),
        "observation_sha256": outbox.digest(observation),
        "verified": True,
        "productive_effect": False,
    }


def orphan_retry_evidence(
    intent,
    attempt_one_transport,
    *,
    backend=None,
    blocker=None,
    actor_conclusion="success",
    actor_workflow_path=None,
    actor_event=None,
    actor_workflow_id=None,
):
    lane = intent["lane"]
    mesh_lane = lane == "mesh-review-successor-dispatch"
    actor_workflow_path = actor_workflow_path or (
        ".github/workflows/qikvrt_requested_review_executor.yml"
        if mesh_lane
        else ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
    )
    actor_event = actor_event or ("workflow_dispatch" if mesh_lane else "schedule")
    actor_workflow_id = actor_workflow_id or (
        intent["payload"]["target"]["workflow_id"] if mesh_lane else 901
    )
    blocker = blocker or (
        "NO_BOUND_RULESET_RECONCILER_AFTER_ATTEMPT_1"
        if lane == "ruleset-dispatch"
        else "ATTEMPT_1_HAS_NO_BOUND_SUCCESSOR"
    )
    actor = {
        "workflow_path": actor_workflow_path,
        "workflow_sha": "a" * 40,
        "workflow_id": actor_workflow_id,
        "run_id": attempt_one_transport["actor_run_id"],
        "run_attempt": attempt_one_transport["actor_run_attempt"],
        "event": actor_event,
        "status": "completed",
        "conclusion": actor_conclusion,
        "created_at": "2026-09-01T08:00:00Z",
        "updated_at": "2026-09-01T08:30:00Z",
    }
    producer = authority_observer(
        run_id=actor["run_id"] + 100, lane=lane
    )
    cursor = {
        "schema": outbox.RETRY_SCAN_CURSOR_SCHEMA,
        "lane": lane,
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "transport_attempt": 1,
        "transport_request_sha256": attempt_one_transport["request_sha256"],
        "ordinal": 1,
        "previous_cursor_sha256": None,
        "transport_actor": actor,
        "transport_actor_sha256": outbox.digest(actor),
        "observation_producer": producer,
        "observation_producer_sha256": outbox.digest(producer),
        "target_workflow_id": intent["payload"]["target"]["workflow_id"],
        "query_window_start": "2026-09-01T08:00:00Z",
        "query_window_end": "2026-09-01T08:31:00Z",
        "observation_started_at": "2026-09-01T08:31:00Z",
        "observation_completed_at": "2026-09-01T09:00:00Z",
        "upper_bound_run_id": 9999,
        "last_scanned_run_id": 1,
        "next_page": None,
        "page_cap": 100,
        "pages_scanned": 1,
        "declared_total_count": 0,
        "queried_page": 1,
        "page_run_ids": [],
        "page_run_ids_sha256": outbox.digest([]),
        "cumulative_run_ids": [],
        "cumulative_run_ids_sha256": outbox.digest([]),
        "page_candidate_run_ids": [],
        "page_candidate_run_ids_sha256": outbox.digest([]),
        "cumulative_candidate_run_ids": [],
        "cumulative_candidate_run_ids_sha256": outbox.digest([]),
        "observed_unique_run_count": 0,
        "inventory_consistent": True,
        "inventory_blocker": None,
        "candidates_seen": 0,
        "candidate_locators": [],
        "candidate_set_sha256": outbox.digest([]),
        "bound_successor_count": 0,
        "same_second_boundary_complete": True,
        "scan_complete": True,
        "verified": True,
        "productive_effect": False,
    }
    artifact_binding = {
        "id": producer["run_id"] + 20000,
        "name": (
            f"qikvrt-outbox-retry-scan-cursor-{lane}-{intent['sequence']}-"
            f"attempt-1-ordinal-1-run-{producer['run_id']}-"
            f"attempt-{producer['run_attempt']}"
        ),
        "archive_sha256": "9" * 64,
        "payload_sha256": outbox.sha256_bytes(
            outbox.canonical_bytes(cursor)
        ),
        "producer_run_id": producer["run_id"],
        "producer_run_attempt": producer["run_attempt"],
        "producer_workflow_id": producer["workflow_id"],
    }
    if backend is None:
        scan_cursor = outbox.validate_retry_scan_cursor_record(
            {
                "schema": outbox.RETRY_SCAN_CURSOR_RECORD_SCHEMA,
                "lane": lane,
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "transport_attempt": 1,
                "cursor": cursor,
                "cursor_sha256": outbox.digest(cursor),
                "artifact": artifact_binding,
                "state": "COMPLETE_ZERO_SUCCESSOR",
                "productive_effect": False,
            },
            intent=intent,
            transport=attempt_one_transport,
        )
    else:
        scan_cursor = outbox.record_retry_scan_cursor(
            backend,
            lane=lane,
            sequence=intent["sequence"],
            cursor=cursor,
            artifact=artifact_binding,
        )["record"]
    return {
        "schema": outbox.RETRY_EVIDENCE_SCHEMA,
        "lane": lane,
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "attempt": 1,
        "classification": "ORPHAN_NO_BOUND_SUCCESSOR",
        "first_blocker": blocker,
        "successor": None,
        "retry_scan_cursor": scan_cursor,
        "retry_scan_cursor_sha256": outbox.digest(scan_cursor),
        "d0": 2,
        "verified": True,
        "productive_effect": False,
    }


def persist_capped_retry_cursor(backend, intent, transport, *, page_cap=2):
    template = orphan_retry_evidence(intent, transport)["retry_scan_cursor"]
    current = None
    cumulative = []
    declared_total = page_cap * 100 + 1
    upper_bound = 100000
    for page in range(1, page_cap + 1):
        high = upper_bound - (page - 1) * 100
        page_ids = list(range(high, high - 100, -1))
        cumulative = sorted(set(cumulative) | set(page_ids), reverse=True)
        cursor = copy.deepcopy(template["cursor"])
        cursor.update(
            {
                "ordinal": page,
                "previous_cursor_sha256": (
                    None if current is None else outbox.digest(current["record"])
                ),
                "observation_started_at": (
                    f"2026-09-01T{9 + (page - 1) // 60:02d}:"
                    f"{(page - 1) % 60:02d}:00Z"
                ),
                "observation_completed_at": (
                    f"2026-09-01T{9 + page // 60:02d}:"
                    f"{page % 60:02d}:00Z"
                ),
                "upper_bound_run_id": upper_bound,
                "last_scanned_run_id": page_ids[-1],
                "scan_complete": False,
                "next_page": None if page == page_cap else page + 1,
                "page_cap": page_cap,
                "pages_scanned": page,
                "declared_total_count": declared_total,
                "queried_page": page,
                "page_run_ids": page_ids,
                "page_run_ids_sha256": outbox.digest(page_ids),
                "cumulative_run_ids": cumulative,
                "cumulative_run_ids_sha256": outbox.digest(cumulative),
                "observed_unique_run_count": len(cumulative),
                "inventory_consistent": True,
                "inventory_blocker": None,
                "candidates_seen": 0,
            }
        )
        artifact_binding = copy.deepcopy(template["artifact"])
        producer = cursor["observation_producer"]
        artifact_binding["name"] = (
            f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
            f"{intent['sequence']}-attempt-1-ordinal-{page}-run-"
            f"{producer['run_id']}-attempt-{producer['run_attempt']}"
        )
        artifact_binding["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(cursor)
        )
        current = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=cursor,
            artifact=artifact_binding,
        )
    return current


def transport_child(intent, *, attempt, run_id):
    lane = intent["lane"]
    target = intent["payload"]["target"]
    request = intent["payload"]["request"]
    if lane == "exact-head-dispatch":
        title = (
            f"qikvrt exact intent={intent['fingerprint']} "
            f"seq={intent['sequence']} transport-attempt={attempt}"
        )
        event = "repository_dispatch"
        head_sha = intent["payload"]["main_head_sha"]
    else:
        inputs = request["inputs"]
        title = (
            f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
            f"h={inputs['head']} f={inputs['fingerprint']} "
            f"i={intent['fingerprint']} a={attempt}"
        )
        event = "workflow_dispatch"
        head_sha = inputs["evaluator_sha"]
    return {
        "run_id": run_id,
        "run_attempt": 1,
        "workflow_id": target["workflow_id"],
        "workflow_path": target["workflow_path"],
        "event": event,
        "repository": intent["repository"],
        "head_sha": head_sha,
        "status": "queued",
        "conclusion": None,
        "display_title": title,
    }


def persist_retry_cursor_result(
    backend,
    intent,
    transport,
    *,
    attempt,
    successor_count,
    page_cap=100,
):
    mesh_lane = intent["lane"] == "mesh-review-successor-dispatch"
    actor = {
        "workflow_path": (
            ".github/workflows/qikvrt_requested_review_executor.yml"
            if mesh_lane
            else ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ),
        "workflow_sha": intent["payload"]["main_head_sha"],
        "workflow_id": (
            intent["payload"]["target"]["workflow_id"] if mesh_lane else 901
        ),
        "run_id": transport["actor_run_id"],
        "run_attempt": transport["actor_run_attempt"],
        "event": "workflow_dispatch" if mesh_lane else "schedule",
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-09-01T08:00:00Z",
        "updated_at": "2026-09-01T08:30:00Z",
    }
    producer = authority_observer(
        run_id=actor["run_id"] + 100, lane=intent["lane"]
    )
    all_candidates = [
        transport_child(
            intent,
            attempt=attempt,
            run_id=actor["run_id"] + 1000 + offset,
        )
        for offset in range(successor_count)
    ]
    stored_candidates = sorted(
        all_candidates, key=lambda item: item["run_id"], reverse=True
    )[:8]
    cursor = {
        "schema": outbox.RETRY_SCAN_CURSOR_SCHEMA,
        "lane": intent["lane"],
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "transport_attempt": attempt,
        "transport_request_sha256": transport["request_sha256"],
        "ordinal": 1,
        "previous_cursor_sha256": None,
        "transport_actor": actor,
        "transport_actor_sha256": outbox.digest(actor),
        "observation_producer": producer,
        "observation_producer_sha256": outbox.digest(producer),
        "target_workflow_id": intent["payload"]["target"]["workflow_id"],
        "query_window_start": "2026-09-01T08:00:00Z",
        "query_window_end": "2026-09-01T08:31:00Z",
        "observation_started_at": "2026-09-01T08:31:00Z",
        "observation_completed_at": "2026-09-01T09:00:00Z",
        "upper_bound_run_id": actor["run_id"] + 2000,
        "last_scanned_run_id": 1,
        "next_page": None,
        "page_cap": page_cap,
        "pages_scanned": 1,
        "declared_total_count": successor_count,
        "queried_page": 1,
        "page_run_ids": sorted(
            [item["run_id"] for item in all_candidates], reverse=True
        ),
        "page_run_ids_sha256": outbox.digest(
            sorted([item["run_id"] for item in all_candidates], reverse=True)
        ),
        "cumulative_run_ids": sorted(
            [item["run_id"] for item in all_candidates], reverse=True
        ),
        "cumulative_run_ids_sha256": outbox.digest(
            sorted([item["run_id"] for item in all_candidates], reverse=True)
        ),
        "page_candidate_run_ids": sorted(
            [item["run_id"] for item in all_candidates], reverse=True
        ),
        "page_candidate_run_ids_sha256": outbox.digest(
            sorted([item["run_id"] for item in all_candidates], reverse=True)
        ),
        "cumulative_candidate_run_ids": sorted(
            [item["run_id"] for item in all_candidates], reverse=True
        ),
        "cumulative_candidate_run_ids_sha256": outbox.digest(
            sorted([item["run_id"] for item in all_candidates], reverse=True)
        ),
        "observed_unique_run_count": successor_count,
        "inventory_consistent": True,
        "inventory_blocker": None,
        "candidates_seen": successor_count,
        "candidate_locators": stored_candidates,
        "candidate_set_sha256": outbox.digest(
            stored_candidates
            if successor_count <= 8
            else sorted(
                [item["run_id"] for item in all_candidates], reverse=True
            )
        ),
        "bound_successor_count": successor_count,
        "same_second_boundary_complete": True,
        "scan_complete": True,
        "verified": True,
        "productive_effect": False,
    }
    artifact_binding = {
        "id": producer["run_id"] + 20000,
        "name": (
            f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
            f"{intent['sequence']}-attempt-{attempt}-ordinal-1-run-"
            f"{producer['run_id']}-attempt-{producer['run_attempt']}"
        ),
        "archive_sha256": "9" * 64,
        "payload_sha256": outbox.sha256_bytes(outbox.canonical_bytes(cursor)),
        "producer_run_id": producer["run_id"],
        "producer_run_attempt": producer["run_attempt"],
        "producer_workflow_id": producer["workflow_id"],
    }
    return outbox.record_retry_scan_cursor(
        backend,
        lane=intent["lane"],
        sequence=intent["sequence"],
        cursor=cursor,
        artifact=artifact_binding,
    )


def exact_cursor_observation_fields(intent, cursor_receipt):
    record = cursor_receipt["record"]
    cursor = record["cursor"]
    return {
        "transport_attempt": record["transport_attempt"],
        "retry_scan_cursor_record_sha256": outbox.digest(record),
        "retry_scan_cursor_sha256": record["cursor_sha256"],
        "retry_scan_cursor_state": record["state"],
        "retry_scan_cursor_ledger_ref": cursor_receipt["ledger_ref"],
        "retry_scan_cursor_ledger_head": cursor_receipt["ledger_head"],
        "query_window_start": cursor["query_window_start"],
        "query_window_end": cursor["query_window_end"],
        "upper_bound_run_id": cursor["upper_bound_run_id"],
        "last_scanned_run_id": cursor["last_scanned_run_id"],
        "page_cap": cursor["page_cap"],
        "pages_scanned": cursor["pages_scanned"],
        "declared_total_count": cursor["declared_total_count"],
        "queried_page": cursor["queried_page"],
        "page_run_ids_sha256": cursor["page_run_ids_sha256"],
        "cumulative_run_ids_sha256": cursor[
            "cumulative_run_ids_sha256"
        ],
        "observed_unique_run_count": cursor["observed_unique_run_count"],
        "inventory_consistent": cursor["inventory_consistent"],
        "inventory_blocker": cursor["inventory_blocker"],
        "candidate_set_sha256": cursor["candidate_set_sha256"],
        "bound_successor_count": cursor["bound_successor_count"],
        "scan_complete": cursor["scan_complete"],
        "sealed_main_head_sha": intent["payload"]["main_head_sha"],
        "observed_main_head_sha": intent["payload"]["main_head_sha"],
    }


def recovery_bound_observation(intent, cursor_receipt):
    record = cursor_receipt["record"]
    cursor = record["cursor"]
    blocker = (
        "MESH_REVIEW_RECOVERY_QUERY_BOUND_EXCEEDED"
        if intent["lane"] == "mesh-review-successor-dispatch"
        else "RECOVERY_QUERY_BOUND_EXCEEDED"
    )
    return {
        "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
        "blocker": blocker,
        "lane": intent["lane"],
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        **exact_cursor_observation_fields(intent, cursor_receipt),
        "verified": True,
        "productive_effect": False,
    }


class RulesetOutboxTests(unittest.TestCase):
    def test_missing_or_unprotected_lane_ref_never_reinitializes(self):
        missing = MemoryBackend(preinitialized=False)
        value = payload()
        with self.assertRaisesRegex(outbox.OutboxBlock, "GENESIS_MISSING"):
            outbox.append_intent(missing, payload=value, artifact=artifact(value))
        self.assertEqual(missing.commits, {})
        self.assertIsNone(missing.get_ledger_head("ruleset-dispatch"))

        unprotected = MemoryBackend()
        unprotected.protection_ok["ruleset-dispatch"] = False
        with self.assertRaisesRegex(outbox.OutboxBlock, "PROTECTION_NOT_VERIFIED"):
            outbox.append_intent(
                unprotected, payload=value, artifact=artifact(value)
            )
        self.assertEqual(unprotected.update_calls, 0)

        wrong_scope = MemoryBackend()
        wrong_scope.writer_scope_ok["ruleset-dispatch"] = False
        with self.assertRaisesRegex(outbox.OutboxBlock, "WRITER_SCOPE_NOT_VERIFIED"):
            outbox.append_intent(
                wrong_scope, payload=value, artifact=artifact(value)
            )
        self.assertEqual(wrong_scope.update_calls, 0)

    def test_lane_refs_and_writer_groups_are_isolated(self):
        backend = MemoryBackend()
        first = payload("ruleset-dispatch")
        second = payload("exact-head-dispatch", run_id=202)
        first_intent = outbox.append_intent(
            backend, payload=first, artifact=artifact(first)
        )
        second_intent = outbox.append_intent(
            backend, payload=second, artifact=artifact(second)
        )
        self.assertNotEqual(
            backend.heads["ruleset-dispatch"],
            backend.heads["exact-head-dispatch"],
        )
        self.assertEqual(
            first_intent["ledger_ref"], outbox.ledger_ref("ruleset-dispatch")
        )
        self.assertEqual(
            second_intent["ledger_ref"], outbox.ledger_ref("exact-head-dispatch")
        )
        self.assertNotEqual(
            outbox.writer_concurrency_group("ruleset-dispatch"),
            outbox.writer_concurrency_group("exact-head-dispatch"),
        )

    def test_lane_local_ff_cas_survives_more_than_legacy_eight_collisions(self):
        backend = ManyRaceBackend(12)
        value = payload()
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        self.assertEqual(intent["cas"]["attempts"], 13)
        self.assertEqual(intent["sequence"], 1)
        self.assertEqual(backend.races_remaining, 0)

    def test_ruleset_protection_requires_restricted_update_and_sole_app_bypass(self):
        lane = "ruleset-dispatch"
        ruleset_id = 901
        rules = [
            {"type": kind, "ruleset_id": ruleset_id}
            for kind in ("deletion", "non_fast_forward", "update")
        ]
        ruleset = {
            "id": ruleset_id,
            "target": "branch",
            "source_type": "Repository",
            "source": "Goldkelch/qik-vrt",
            "enforcement": "active",
            "bypass_actors": [
                {
                    "actor_id": 42,
                    "actor_type": "Integration",
                    "bypass_mode": "always",
                }
            ],
            "conditions": {
                "ref_name": {"include": [outbox.ledger_ref(lane)], "exclude": []}
            },
            "rules": [{"type": item} for item in ("deletion", "non_fast_forward", "update")],
        }
        with mock.patch.dict(
            "os.environ",
            {"QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID": "42"},
            clear=False,
        ):
            ProtectionProbe(rules, ruleset).verify_ledger_protection(lane)
            with self.assertRaisesRegex(
                outbox.OutboxBlock, "PROTECTION_NOT_VERIFIED"
            ):
                ProtectionProbe(rules[:-1], ruleset).verify_ledger_protection(lane)
            forged = copy.deepcopy(ruleset)
            forged["bypass_actors"].append(
                {"actor_id": 7, "actor_type": "User", "bypass_mode": "always"}
            )
            with self.assertRaisesRegex(
                outbox.OutboxBlock, "WRITER_IDENTITY_NOT_VERIFIED"
            ):
                ProtectionProbe(rules, forged).verify_ledger_protection(lane)
            with self.assertRaisesRegex(
                outbox.OutboxBlock, "PROTECTION_NOT_VERIFIED"
            ):
                ProtectionProbe(
                    rules + [{"type": "required_status_checks"}] * 97,
                    ruleset,
                ).verify_ledger_protection(lane)

    def test_authority_environment_readback_is_main_only_and_fail_closed(self):
        with mock.patch.dict(
            "os.environ",
            {"QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID": "42"},
            clear=False,
        ):
            proof = AuthorityProbe().verify_authority_environment(
                "ruleset-dispatch"
            )
            self.assertEqual(proof["schema"], outbox.AUTHORITY_READBACK_SCHEMA)
            self.assertEqual(proof["state"], "VERIFIED_FOR_THIS_EFFECT_ONLY")
            self.assertEqual(proof["deployment_branch"], "main")
            self.assertEqual(
                proof["environment_secret_names_present"],
                [outbox.AUDITOR_SECRET_NAME, outbox.WRITER_SECRET_NAME],
            )
            self.assertTrue(proof["repository_scope_fallback_names_absent"])
            self.assertTrue(proof["organization_scope_fallback_names_absent"])
            self.assertEqual(
                proof["repository_owner"],
                {"login": "Goldkelch", "type": "User", "id": 293941403},
            )
            self.assertEqual(
                proof["organization_scope_readback"],
                "NOT_APPLICABLE_USER_OWNER",
            )
            self.assertFalse(proof["secret_values_observed"])
            self.assertFalse(proof["external_configuration_claimed_by_repository"])

            organization_proof = AuthorityProbe(
                owner_type="Organization"
            ).verify_authority_environment("ruleset-dispatch")
            self.assertEqual(
                organization_proof["organization_scope_readback"],
                "VERIFIED_ORGANIZATION_SECRET_INVENTORY",
            )

            invalid_probes = (
                AuthorityProbe(
                    environment_secret_names=(outbox.AUDITOR_SECRET_NAME,)
                ),
                AuthorityProbe(
                    repository_secret_names=(outbox.WRITER_SECRET_NAME,)
                ),
                AuthorityProbe(
                    organization_secret_names=(
                        "QIKVRT_OUTBOX_LEDGER_AUDITOR_TOKEN",
                    ),
                    owner_type="Organization",
                ),
                AuthorityProbe(branch_policies=()),
                AuthorityProbe(protection_rules=()),
                AuthorityProbe(
                    owner_type="Organization",
                    org_error=outbox.GitHubApiError(403, "forbidden"),
                ),
                AuthorityProbe(owner_login="forged"),
                AuthorityProbe(owner_type="Bot"),
                AuthorityProbe(owner_id=None),
            )
            for probe in invalid_probes:
                with self.subTest(probe=probe.__dict__):
                    with self.assertRaisesRegex(
                        outbox.OutboxBlock,
                        "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED",
                    ):
                        probe.verify_authority_environment("ruleset-dispatch")

            with self.assertRaisesRegex(
                outbox.OutboxBlock,
                "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED",
            ):
                AuthorityProbe(
                    repository_secret_names=tuple(
                        f"SAFE_REPOSITORY_SECRET_{index}" for index in range(101)
                    )
                ).verify_authority_environment("ruleset-dispatch")

            class NetZeroMovingInventoryProbe(AuthorityProbe):
                def __init__(self):
                    super().__init__(repository_secret_names=("SAFE_SECRET",))
                    self.repository_inventory_reads = 0

                def _request(self, method, endpoint, payload=None, **kwargs):
                    if endpoint.startswith("actions/secrets?"):
                        self.repository_inventory_reads += 1
                        names = (
                            ("SAFE_SECRET",)
                            if self.repository_inventory_reads == 1
                            else (outbox.WRITER_SECRET_NAME,)
                        )
                        return self._inventory("secrets", names)
                    return super()._request(
                        method, endpoint, payload=payload, **kwargs
                    )

            with self.assertRaisesRegex(
                outbox.OutboxBlock,
                "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED:.*changed",
            ):
                NetZeroMovingInventoryProbe().verify_authority_environment(
                    "ruleset-dispatch"
                )

        with mock.patch.dict(
            "os.environ",
            {"QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID": "not-an-integer"},
            clear=False,
        ):
            with self.assertRaisesRegex(
                outbox.OutboxBlock,
                "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED",
            ):
                AuthorityProbe().verify_authority_environment("ruleset-dispatch")

    def test_every_ledger_read_and_mutation_requires_effect_local_authority(self):
        blocked = MemoryBackend()
        blocked.authority_environment_ok["ruleset-dispatch"] = False
        value = payload("ruleset-dispatch")
        with self.assertRaisesRegex(
            outbox.OutboxBlock,
            "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED",
        ):
            outbox.append_intent(blocked, payload=value, artifact=artifact(value))
        self.assertEqual(blocked.update_calls, 0)

        readable = MemoryBackend()
        outbox.read_next(readable, "ruleset-dispatch")
        self.assertEqual(readable.authority_environment_reads, ["ruleset-dispatch"])

    def test_verify_authority_cli_uses_auditor_scope_and_emits_readback(self):
        backend = MemoryBackend()
        with (
            mock.patch.dict(
                "os.environ",
                {
                    "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN": "auditor-token",
                    "QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID": "42",
                    "GITHUB_TOKEN": "ordinary-token",
                },
                clear=True,
            ),
            mock.patch.object(
                outbox, "GitHubLedgerBackend", return_value=backend
            ) as backend_factory,
            mock.patch.object(outbox, "_write_result") as write_result,
        ):
            status = outbox.main(
                [
                    "--repository",
                    "Goldkelch/qik-vrt",
                    "verify-authority",
                    "--lane",
                    "ruleset-dispatch",
                ]
            )
        self.assertEqual(status, 0)
        backend_factory.assert_called_once_with(
            "Goldkelch/qik-vrt", "auditor-token"
        )
        receipt = write_result.call_args.args[0]
        self.assertEqual(receipt["state"], "VERIFIED_FOR_THIS_EFFECT_ONLY")
        self.assertEqual(receipt["ledger_ref"], outbox.ledger_ref("ruleset-dispatch"))
        self.assertTrue(receipt["ledger_protection_verified"])
        self.assertFalse(receipt["secret_values_observed"])

    def test_read_cli_requires_public_actor_id_but_never_writer_secret(self):
        command_backends = []
        next_backend = MemoryBackend()
        command_backends.append((next_backend, ["next", "--lane", "ruleset-dispatch"]))

        lookup_backend = MemoryBackend()
        value = payload("ruleset-dispatch")
        intent = outbox.append_intent(
            lookup_backend, payload=value, artifact=artifact(value)
        )
        command_backends.append(
            (
                lookup_backend,
                [
                    "lookup",
                    "--lane",
                    "ruleset-dispatch",
                    "--sequence",
                    str(intent["sequence"]),
                    "--fingerprint",
                    intent["fingerprint"],
                ],
            )
        )
        command_backends.append(
            (
                lookup_backend,
                [
                    "lookup-fingerprint",
                    "--lane",
                    "ruleset-dispatch",
                    "--fingerprint",
                    intent["fingerprint"],
                ],
            )
        )

        for backend, command in command_backends:
            with self.subTest(command=command[0]), mock.patch.dict(
                "os.environ",
                {
                    "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN": "auditor-token",
                    "QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID": "42",
                },
                clear=True,
            ), mock.patch.object(
                outbox, "GitHubLedgerBackend", return_value=backend
            ) as backend_factory, mock.patch.object(outbox, "_write_result"):
                status = outbox.main(
                    ["--repository", "Goldkelch/qik-vrt", *command]
                )
            self.assertEqual(status, 0)
            backend_factory.assert_called_once_with(
                "Goldkelch/qik-vrt", "auditor-token"
            )

        with mock.patch.dict(
            "os.environ",
            {"QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN": "auditor-token"},
            clear=True,
        ), mock.patch.object(outbox, "GitHubLedgerBackend") as backend_factory, mock.patch.object(
            outbox, "_write_result"
        ) as write_result:
            status = outbox.main(
                [
                    "--repository",
                    "Goldkelch/qik-vrt",
                    "next",
                    "--lane",
                    "ruleset-dispatch",
                ]
            )
        self.assertEqual(status, 3)
        backend_factory.assert_not_called()
        self.assertIn(
            "OUTBOX_LEDGER_WRITER_ACTOR_ID_UNAVAILABLE",
            write_result.call_args.args[0]["first_blocker"],
        )

    def test_writer_token_has_no_ordinary_workflow_token_fallback(self):
        with self.assertRaisesRegex(outbox.OutboxBlock, "TOKEN_UNAVAILABLE"):
            outbox.writer_token_from_environment({})
        with self.assertRaisesRegex(outbox.OutboxBlock, "SCOPE_INVALID"):
            outbox.writer_token_from_environment(
                {
                    "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN": "same",
                    "GITHUB_TOKEN": "same",
                }
            )
        self.assertEqual(
            outbox.writer_token_from_environment(
                {
                    "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN": "app-token",
                    "GITHUB_TOKEN": "ordinary-token",
                }
            ),
            "app-token",
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "AUDITOR_TOKEN_UNAVAILABLE"):
            outbox.auditor_token_from_environment({})
        with self.assertRaisesRegex(outbox.OutboxBlock, "AUDITOR_TOKEN_SCOPE_INVALID"):
            outbox.auditor_token_from_environment(
                {
                    "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN": "same",
                    "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN": "same",
                }
            )
        self.assertEqual(
            outbox.auditor_token_from_environment(
                {
                    "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN": "auditor-token",
                    "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN": "writer-token",
                }
            ),
            "auditor-token",
        )

    def test_terminal_claim_boundary_rejects_nested_and_alias_claims(self):
        backend = MemoryBackend()
        value = payload("ruleset-dispatch")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6001,
            actor_run_attempt=1,
        )
        item = outbox.read_next(backend, intent["lane"])
        ambiguity_observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "BOUND_EVIDENCE_AMBIGUOUS",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "candidate_sha256s": ["1" * 64, "2" * 64],
            "scan_complete": True,
            "verified": True,
            "productive_effect": False,
        }
        ambiguity_record = persist_authority_observation(
            backend, intent, ambiguity_observation
        )
        item = outbox.read_next(backend, intent["lane"])
        item = {**item, "authority_observation": ambiguity_record}
        safe = terminal_evidence(
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "exhaustion": ambiguity_exhaustion(
                    intent,
                    "BOUND_EVIDENCE_AMBIGUOUS",
                    ambiguity_record,
                ),
                "continuation": {
                    "schema": "qikvrt.causal-continuation.v1",
                    "mode": "REQUEST_AUTHORITY",
                    "owner": "AUTHORITY_ADMIN",
                    "next_action": "INSPECT_EXACT_BOUND_EVIDENCE",
                    "resume_events": ["workflow_dispatch"],
                    "persistence_run_terminal": False,
                    "client_return_allowed": False,
                },
                "productive_effect": False,
            }
        )
        self.assertEqual(
            outbox.validate_terminal_evidence(safe, next_item=item)["d0"], 3
        )
        superseded_backend = MemoryBackend()
        superseded_value = payload("ruleset-dispatch", run_id=102)
        superseded_intent = outbox.append_intent(
            superseded_backend,
            payload=superseded_value,
            artifact=artifact(superseded_value),
        )
        outbox.prepare_transport(
            superseded_backend,
            lane=superseded_intent["lane"],
            sequence=superseded_intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(superseded_intent, 1),
            actor_run_id=6002,
            actor_run_attempt=1,
        )
        superseded_observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_EVALUATOR_SUPERSEDED",
            "lane": superseded_intent["lane"],
            "sequence": superseded_intent["sequence"],
            "fingerprint": superseded_intent["fingerprint"],
            "sealed_main_head_sha": "a" * 40,
            "observed_main_head_sha": "f" * 40,
            "verified": True,
            "productive_effect": False,
        }
        superseded_record = persist_authority_observation(
            superseded_backend,
            superseded_intent,
            superseded_observation,
            run_id=8802,
        )
        superseded = terminal_evidence(
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "reason": "OUTBOX_EVALUATOR_SUPERSEDED",
                "exhaustion": ambiguity_exhaustion(
                    superseded_intent,
                    "OUTBOX_EVALUATOR_SUPERSEDED",
                    superseded_record,
                ),
                "productive_effect": False,
            }
        )
        self.assertEqual(
            outbox.validate_terminal_evidence(
                superseded,
                next_item={
                    **outbox.read_next(
                        superseded_backend, superseded_intent["lane"]
                    ),
                    "authority_observation": superseded_record,
                },
            )["d0"],
            3,
        )
        variants = (
            {
                **terminal_evidence(
                    {
                        "d0": 3,
                        "state": "REQUEST_AUTHORITY",
                        "exhaustion": {
                            "schema": outbox.EXHAUSTION_SCHEMA,
                            "lane": intent["lane"],
                            "sequence": intent["sequence"],
                            "fingerprint": intent["fingerprint"],
                            "mode": "AMBIGUOUS_OR_DRIFT",
                            "attempts": [1],
                            "first_blocker": "BOUND_EVIDENCE_AMBIGUOUS",
                            "verified": True,
                            "productive_effect": False,
                        },
                        "productive_effect": False,
                    }
                ),
                "claims": {"FINAL_PASS": True},
            },
            terminal_evidence(
                {
                    "d0": 3,
                    "state": "PASS",
                    "exhaustion": {},
                    "productive_effect": False,
                }
            ),
            {
                **terminal_evidence(
                    {
                        "d0": 3,
                        "state": "REQUEST_AUTHORITY",
                        "exhaustion": {},
                        "productive_effect": False,
                    }
                ),
                "approval": True,
            },
            terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "exhaustion": {
                        "schema": outbox.EXHAUSTION_SCHEMA,
                        "lane": intent["lane"],
                        "sequence": intent["sequence"],
                        "fingerprint": intent["fingerprint"],
                        "mode": "AMBIGUOUS_OR_DRIFT",
                        "attempts": [1],
                        "first_blocker": "BOUND_EVIDENCE_AMBIGUOUS",
                        "verified": True,
                        "productive_effect": False,
                    },
                    "continuation": {
                        "schema": "qikvrt.causal-continuation.v1",
                        "mode": "REQUEST_AUTHORITY",
                        "owner": "AUTHORITY_ADMIN",
                        "next_action": "REQUEST_GENERAL_EFFECT_ACK_DONE",
                        "resume_events": ["workflow_dispatch"],
                        "persistence_run_terminal": False,
                        "client_return_allowed": False,
                    },
                    "productive_effect": False,
                }
            ),
            terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "exhaustion": {
                        "schema": outbox.EXHAUSTION_SCHEMA,
                        "lane": intent["lane"],
                        "sequence": intent["sequence"],
                        "fingerprint": intent["fingerprint"],
                        "mode": "AMBIGUOUS_OR_DRIFT",
                        "attempts": [1],
                        "first_blocker": "BOUND_EVIDENCE_AMBIGUOUS",
                        "verified": True,
                        "productive_effect": False,
                    },
                    "continuation": {
                        "schema": "qikvrt.causal-continuation.v1",
                        "mode": "REQUEST_AUTHORITY",
                        "owner": "AUTHORITY_ADMIN",
                        "next_action": "REPOSITORY_RELEASE_PUBLISHED",
                        "resume_events": ["workflow_dispatch"],
                        "persistence_run_terminal": False,
                        "client_return_allowed": False,
                    },
                    "productive_effect": False,
                }
            ),
            {
                **copy.deepcopy(safe),
                "reason": "REPOSITORY_FINAL_PASS",
            },
            {
                **copy.deepcopy(safe),
                "exhaustion": {
                    **copy.deepcopy(safe["exhaustion"]),
                    "first_blocker": "GENERAL_EFFECT_ACK_DONE",
                },
            },
            {
                **copy.deepcopy(safe),
                "pull_request": 999,
                "head_sha": "0" * 40,
            },
        )
        for forged in variants:
            with self.subTest(forged=forged):
                with self.assertRaises(outbox.OutboxBlock):
                    outbox.validate_terminal_evidence(forged, next_item=item)
        for alias in (
            "GENERAL_EFFECT_ACK_DONE",
            "REPOSITORY_PASS",
            "RELEASE_PUBLISHED",
            "AUTHORITY_MIRROR_SYNCHRONIZED",
            "APPROVAL_GRANTED",
            "PHYSICAL_ATARI_EXECUTION",
        ):
            with self.subTest(alias=alias):
                forged = copy.deepcopy(safe)
                forged["continuation"]["next_action"] = alias
                with self.assertRaisesRegex(outbox.OutboxBlock, "forbidden semantics"):
                    outbox.validate_terminal_evidence(forged, next_item=item)

    def test_success_precedence_rejects_evidence_free_generic_ambiguity(self):
        backend = MemoryBackend()
        value = payload("exact-head-dispatch")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6101,
            actor_run_attempt=1,
        )
        child = {
            "run_id": 6102,
            "run_attempt": 1,
            "workflow_id": 66,
            "workflow_path": ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
            "event": "repository_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "success",
            "display_title": (
                f"qikvrt-exact intent={intent['fingerprint']} "
                f"seq={intent['sequence']} transport-attempt=1"
            ),
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=child,
        )
        result_artifact = {
            "id": 6103,
            "name": "qikvrt-exact-head-business-6102-1",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 6102,
            "producer_run_attempt": 1,
            "verified": True,
        }
        outbox.record_completion(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=child,
            evidence=completion_evidence(child, result_artifact),
        )
        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_EVALUATOR_SUPERSEDED",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "sealed_main_head_sha": "a" * 40,
            "observed_main_head_sha": "f" * 40,
            "verified": True,
            "productive_effect": False,
        }
        observation_record = persist_authority_observation(
            backend, intent, observation, run_id=8810
        )
        forged_hold = terminal_evidence(
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "reason": "OUTBOX_EVALUATOR_SUPERSEDED",
                "exhaustion": ambiguity_exhaustion(
                    intent,
                    "OUTBOX_EVALUATOR_SUPERSEDED",
                    observation_record,
                ),
                "productive_effect": False,
            }
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "success.*precedence"):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=forged_hold,
            )
        self.assertEqual(
            outbox.read_next(backend, intent["lane"])["state"], "PENDING"
        )

    def test_authority_ambiguity_requires_exact_immutable_observation(self):
        backend = MemoryBackend()
        value = payload("ruleset-dispatch", run_id=6110)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6111,
            actor_run_attempt=1,
        )
        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "BOUND_EVIDENCE_AMBIGUOUS",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "candidate_sha256s": ["1" * 64, "2" * 64],
            "scan_complete": True,
            "verified": True,
            "productive_effect": False,
        }
        forged = terminal_evidence(
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "reason": "BOUND_EVIDENCE_AMBIGUOUS",
                "exhaustion": {
                    "schema": outbox.EXHAUSTION_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "mode": "AMBIGUOUS_OR_DRIFT",
                    "attempts": [1],
                    "first_blocker": "BOUND_EVIDENCE_AMBIGUOUS",
                    "authority_observation_sha256": "9" * 64,
                    "observation_sha256": outbox.digest(observation),
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "authority-observation"):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=forged,
            )

        producer = authority_observer(run_id=6112)
        with self.assertRaisesRegex(outbox.OutboxBlock, "sealed bytes"):
            outbox.record_authority_observation(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                observation=observation,
                producer=producer,
                artifact={
                    "id": 6113,
                    "name": (
                        "qikvrt-outbox-authority-observation-ruleset-dispatch-1-"
                        "BOUND_EVIDENCE_AMBIGUOUS-run-6112-attempt-1"
                    ),
                    "archive_sha256": "e" * 64,
                    "payload_sha256": "0" * 64,
                    "producer_run_id": 6112,
                    "producer_run_attempt": 1,
                    "producer_workflow_id": producer["workflow_id"],
                },
            )
        record = persist_authority_observation(
            backend, intent, observation, run_id=6112
        )
        exact = copy.deepcopy(forged)
        exact["exhaustion"]["authority_observation_sha256"] = outbox.digest(
            record
        )
        self.assertEqual(
            outbox.validate_terminal_evidence(
                exact,
                next_item={
                    **outbox.read_next(backend, intent["lane"]),
                    "authority_observation": record,
                },
            )["d0"],
            3,
        )
        mismatched = copy.deepcopy(exact)
        mismatched["exhaustion"]["authority_observation_sha256"] = "8" * 64
        with self.assertRaisesRegex(outbox.OutboxBlock, "does not bind stored"):
            outbox.validate_terminal_evidence(
                mismatched,
                next_item={
                    **outbox.read_next(backend, intent["lane"]),
                    "authority_observation": record,
                },
            )

        subject_backend = MemoryBackend()
        subject_value = payload("ruleset-dispatch", run_id=6114)
        subject_intent = outbox.append_intent(
            subject_backend,
            payload=subject_value,
            artifact=artifact(subject_value),
        )
        outbox.prepare_transport(
            subject_backend,
            lane=subject_intent["lane"],
            sequence=subject_intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(subject_intent, 1),
            actor_run_id=6115,
            actor_run_attempt=1,
        )
        null_subject = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_SUBJECT_SUPERSEDED",
            "lane": subject_intent["lane"],
            "sequence": subject_intent["sequence"],
            "fingerprint": subject_intent["fingerprint"],
            "sealed_subject_sha256": outbox.digest({"key": "one"}),
            "observed_subject": {"key": None},
            "observed_subject_sha256": outbox.digest({"key": None}),
            "verified": True,
            "productive_effect": False,
        }
        with self.assertRaisesRegex(outbox.OutboxBlock, "subject string locator"):
            persist_authority_observation(
                subject_backend,
                subject_intent,
                null_subject,
                run_id=6116,
            )

        by_fingerprint = outbox.lookup_fingerprint(
            backend,
            lane=intent["lane"],
            fingerprint=intent["fingerprint"],
        )
        self.assertEqual(by_fingerprint["sequence"], intent["sequence"])
        with self.assertRaisesRegex(outbox.OutboxBlock, "NOT_FOUND"):
            outbox.lookup_fingerprint(
                backend,
                lane=intent["lane"],
                fingerprint="f" * 64,
            )

    def test_exact_review_recovery_bound_and_missing_evidence_are_closed(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6120)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6121,
            actor_run_attempt=1,
        )
        transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        capped_cursor = persist_capped_retry_cursor(
            backend, intent, transport, page_cap=5
        )
        bounded = recovery_bound_observation(intent, capped_cursor)
        bounded_record = persist_authority_observation(
            backend, intent, bounded, run_id=6122
        )
        bounded_terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": "RECOVERY_QUERY_BOUND_EXCEEDED",
                    "exhaustion": ambiguity_exhaustion(
                        intent,
                        "RECOVERY_QUERY_BOUND_EXCEEDED",
                        bounded_record,
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(bounded_terminal["d0"], 3)

        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6123)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6124,
            actor_run_attempt=1,
        )
        child = {
            "run_id": 6125,
            "run_attempt": 1,
            "workflow_id": 77,
            "workflow_path": (
                ".github/workflows/qikvrt_requested_review_executor.yml"
            ),
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": (
                "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h=" + "b" * 40
                + " f=" + "c" * 64 + " i=" + intent["fingerprint"]
                + " a=1"
            ),
        }
        accepted = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=child,
        )
        observed_child = {
            **child,
            "status": "completed",
            "conclusion": "success",
        }
        missing = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "EXACT_REVIEW_COMPLETION_EVIDENCE_MISSING",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "transport_attempt": 1,
            "accepted_child_sha256": accepted["child_sha256"],
            "observed_child": observed_child,
            "observed_child_sha256": outbox.digest(observed_child),
            "jobs_total_count": 4,
            "expected_artifact_name": (
                "qikvrt-requested-review-completion-6125-attempt-1"
            ),
            "evidence_classification": "MISSING_ARTIFACT",
            "artifact_count": 0,
            "artifact_set_sha256": outbox.digest([]),
            "scan_complete": True,
            "verified": True,
            "productive_effect": False,
        }
        invalid_missing = {**missing, "artifact_count": 1}
        with self.assertRaisesRegex(outbox.OutboxBlock, "missing evidence"):
            persist_authority_observation(
                backend, intent, invalid_missing, run_id=6126
            )
        missing_record = persist_authority_observation(
            backend, intent, missing, run_id=6126
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": "EXACT_REVIEW_COMPLETION_EVIDENCE_MISSING",
                    "exhaustion": ambiguity_exhaustion(
                        intent,
                        "EXACT_REVIEW_COMPLETION_EVIDENCE_MISSING",
                        missing_record,
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(terminal["d0"], 3)

    def test_capped_retry_cursor_terminal_is_exact_for_both_exact_lanes(self):
        for offset, lane in enumerate(
            ("exact-head-dispatch", "exact-review-dispatch")
        ):
            with self.subTest(lane=lane):
                backend = MemoryBackend()
                value = payload(lane, run_id=6260 + offset * 10)
                intent = outbox.append_intent(
                    backend, payload=value, artifact=artifact(value)
                )
                outbox.prepare_transport(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    actor_run_id=6261 + offset * 10,
                    actor_run_attempt=1,
                )
                transport = outbox.read_next(backend, lane)["transport"]["1"]
                cursor_receipt = persist_capped_retry_cursor(
                    backend, intent, transport, page_cap=3
                )
                observation = recovery_bound_observation(
                    intent, cursor_receipt
                )
                record = persist_authority_observation(
                    backend, intent, observation, run_id=6262 + offset * 10
                )
                terminal = outbox.terminalize(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    evidence=terminal_evidence(
                        {
                            "d0": 3,
                            "state": "REQUEST_AUTHORITY",
                            "reason": "RECOVERY_QUERY_BOUND_EXCEEDED",
                            "exhaustion": ambiguity_exhaustion(
                                intent,
                                "RECOVERY_QUERY_BOUND_EXCEEDED",
                                record,
                            ),
                            "productive_effect": False,
                        }
                    ),
                )
                self.assertEqual(terminal["d0"], 3)

    def test_mesh_retry_provenance_is_real_lane_scoped_and_event_scoped(self):
        backend = MemoryBackend()
        value = payload("mesh-review-successor-dispatch", run_id=6278)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6279,
            actor_run_attempt=1,
        )
        transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        evidence = orphan_retry_evidence(
            intent,
            transport,
            actor_workflow_path=(
                ".github/workflows/qikvrt_requested_review_executor.yml"
            ),
            actor_event="workflow_dispatch",
            actor_workflow_id=intent["payload"]["target"]["workflow_id"],
        )
        self.assertEqual(
            evidence["retry_scan_cursor"]["cursor"]["transport_actor"][
                "workflow_path"
            ],
            ".github/workflows/qikvrt_requested_review_executor.yml",
        )

        bad_event = copy.deepcopy(
            evidence["retry_scan_cursor"]["cursor"]["transport_actor"]
        )
        bad_event["event"] = "repository_dispatch"
        bad_cursor = copy.deepcopy(evidence["retry_scan_cursor"])
        bad_cursor["cursor"]["transport_actor"] = bad_event
        bad_cursor["cursor"]["transport_actor_sha256"] = outbox.digest(bad_event)
        bad_cursor["cursor_sha256"] = outbox.digest(bad_cursor["cursor"])
        bad_cursor["artifact"]["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(bad_cursor["cursor"])
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "actor"):
            outbox.validate_retry_scan_cursor_record(
                bad_cursor, intent=intent, transport=transport
            )

        other_backend = MemoryBackend()
        other_value = payload("exact-review-dispatch", run_id=6280)
        other_intent = outbox.append_intent(
            other_backend, payload=other_value, artifact=artifact(other_value)
        )
        outbox.prepare_transport(
            other_backend,
            lane=other_intent["lane"],
            sequence=other_intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(other_intent, 1),
            actor_run_id=6281,
            actor_run_attempt=1,
        )
        other_transport = outbox.read_next(
            other_backend, other_intent["lane"]
        )["transport"]["1"]
        with self.assertRaisesRegex(outbox.OutboxBlock, "actor"):
            orphan_retry_evidence(
                other_intent,
                other_transport,
                actor_workflow_path=(
                    ".github/workflows/qikvrt_requested_review_executor.yml"
                ),
                actor_event="workflow_dispatch",
                actor_workflow_id=other_intent["payload"]["target"]["workflow_id"],
            )

        foreign_lane_observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_SUBJECT_SUPERSEDED",
            "lane": other_intent["lane"],
            "sequence": other_intent["sequence"],
            "fingerprint": other_intent["fingerprint"],
            "sealed_subject_sha256": outbox.digest({"key": "one"}),
            "observed_subject": {"key": "two"},
            "observed_subject_sha256": outbox.digest({"key": "two"}),
            "verified": True,
            "productive_effect": False,
        }
        foreign_lane_producer = {
            "workflow_path": (
                ".github/workflows/qikvrt_mesh_review_successor_completion.yml"
            ),
            "workflow_sha": "a" * 40,
            "workflow_id": 902,
            "run_id": 6285,
            "run_attempt": 1,
            "event": "schedule",
        }
        with self.assertRaisesRegex(outbox.OutboxBlock, "provenance"):
            outbox.record_authority_observation(
                other_backend,
                lane=other_intent["lane"],
                sequence=other_intent["sequence"],
                observation=foreign_lane_observation,
                producer=foreign_lane_producer,
                artifact={
                    "id": 7285,
                    "name": (
                        "qikvrt-outbox-authority-observation-"
                        f"{other_intent['lane']}-{other_intent['sequence']}-"
                        "OUTBOX_SUBJECT_SUPERSEDED-run-6285-attempt-1"
                    ),
                    "archive_sha256": "e" * 64,
                    "payload_sha256": outbox.sha256_bytes(
                        outbox.canonical_bytes(foreign_lane_observation)
                    ),
                    "producer_run_id": 6285,
                    "producer_run_attempt": 1,
                    "producer_workflow_id": 902,
                },
            )

        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_SUBJECT_SUPERSEDED",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "sealed_subject_sha256": outbox.digest({"key": "one"}),
            "observed_subject": {"key": "two"},
            "observed_subject_sha256": outbox.digest({"key": "two"}),
            "verified": True,
            "productive_effect": False,
        }
        producer = {
            "workflow_path": (
                ".github/workflows/qikvrt_mesh_review_successor_completion.yml"
            ),
            "workflow_sha": "a" * 40,
            "workflow_id": 902,
            "run_id": 6282,
            "run_attempt": 1,
            "event": "schedule",
        }
        receipt = outbox.record_authority_observation(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            observation=observation,
            producer=producer,
            artifact={
                "id": 7282,
                "name": (
                    "qikvrt-outbox-authority-observation-"
                    f"{intent['lane']}-{intent['sequence']}-"
                    "OUTBOX_SUBJECT_SUPERSEDED-run-6282-attempt-1"
                ),
                "archive_sha256": "e" * 64,
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(observation)
                ),
                "producer_run_id": 6282,
                "producer_run_attempt": 1,
                "producer_workflow_id": 902,
            },
        )
        self.assertEqual(
            receipt["record"]["producer"]["workflow_path"],
            producer["workflow_path"],
        )

        for changed in (
            {**producer, "event": "pull_request_target", "run_id": 6283},
            {
                **producer,
                "workflow_path": ".github/workflows/qikvrt_required_review_gate.yml",
                "run_id": 6284,
            },
        ):
            with self.subTest(producer=changed):
                with self.assertRaisesRegex(outbox.OutboxBlock, "provenance"):
                    outbox.record_authority_observation(
                        backend,
                        lane=intent["lane"],
                        sequence=intent["sequence"],
                        observation=observation,
                        producer=changed,
                        artifact={
                            "id": changed["run_id"] + 1000,
                            "name": (
                                "qikvrt-outbox-authority-observation-"
                                f"{intent['lane']}-{intent['sequence']}-"
                                "OUTBOX_SUBJECT_SUPERSEDED-run-"
                                f"{changed['run_id']}-attempt-1"
                            ),
                            "archive_sha256": "e" * 64,
                            "payload_sha256": outbox.sha256_bytes(
                                outbox.canonical_bytes(observation)
                            ),
                            "producer_run_id": changed["run_id"],
                            "producer_run_attempt": 1,
                            "producer_workflow_id": changed["workflow_id"],
                        },
                    )

    def test_admission_authority_observer_is_lane_and_blocker_scoped(self):
        producer = {
            "workflow_path": (
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            "workflow_sha": "a" * 40,
            "workflow_id": 903,
            "run_id": 6299,
            "run_attempt": 1,
            "event": "schedule",
        }
        blocker = "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED"
        for lane in (
            "exact-review-dispatch",
            "mesh-review-successor-dispatch",
        ):
            with self.subTest(accepted_lane=lane):
                intent = {
                    "lane": lane,
                    "payload": {"main_head_sha": "a" * 40},
                }
                self.assertEqual(
                    outbox._normalize_authority_observer(
                        producer, intent=intent, blocker=blocker
                    ),
                    producer,
                )
        for lane in (
            "ruleset-dispatch",
            "requested-review-dispatch",
            "exact-head-dispatch",
        ):
            with self.subTest(rejected_lane=lane):
                with self.assertRaisesRegex(outbox.OutboxBlock, "provenance"):
                    outbox._normalize_authority_observer(
                        producer,
                        intent={
                            "lane": lane,
                            "payload": {"main_head_sha": "a" * 40},
                        },
                        blocker=blocker,
                    )
        with self.assertRaisesRegex(outbox.OutboxBlock, "provenance"):
            outbox._normalize_authority_observer(
                producer,
                intent={
                    "lane": "mesh-review-successor-dispatch",
                    "payload": {"main_head_sha": "a" * 40},
                },
                blocker="OUTBOX_SUBJECT_SUPERSEDED",
            )

    def test_admission_action_required_zero_job_terminalizes_shared_core(self):
        def prepared_item(lane, run_id):
            backend = MemoryBackend()
            value = payload(lane, run_id=run_id)
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            outbox.prepare_transport(
                backend,
                lane=lane,
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=run_id + 1,
                actor_run_attempt=1,
            )
            title = (
                "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h=" + "b" * 40
                + " f=" + "c" * 64 + " i=" + intent["fingerprint"]
                + " a=1"
            )
            locator = {
                "run_id": run_id + 2,
                "run_attempt": 1,
                "workflow_id": 77,
                "workflow_path": (
                    ".github/workflows/qikvrt_requested_review_executor.yml"
                ),
                "event": "workflow_dispatch",
                "repository": "Goldkelch/qik-vrt",
                "head_sha": "a" * 40,
                "status": "queued",
                "conclusion": None,
                "display_title": title,
            }
            acceptance = outbox.record_acceptance(
                backend,
                lane=lane,
                sequence=intent["sequence"],
                attempt=1,
                child=locator,
            )
            observed = {
                **locator,
                "status": "completed",
                "conclusion": "action_required",
            }
            source = {
                **observed,
                "repository_id": 293941403,
                "head_branch": "main",
                "created_at": "2026-09-01T08:30:00Z",
                "jobs_total": 0,
                "artifacts_total": 0,
                "pull_requests": [],
            }
            from tools import qikvrt_review_admission_recovery as admission

            receipt = admission.build_terminal_receipt(
                {
                    "state": "ACTION_REQUIRED_D0_3",
                    "rerun_required": False,
                    "d0": 3,
                    "first_blocker": "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
                    "selected": source,
                }
            )
            subject = copy.deepcopy(intent["payload"]["subject"])
            observation = {
                "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
                "blocker": "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
                "lane": lane,
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "transport_attempt": 1,
                "intent_sha256": outbox.digest(
                    outbox._validate_intent_record(intent, lane=lane)
                ),
                "acceptance_sha256": outbox.digest(
                    {
                        key: value
                        for key, value in acceptance.items()
                        if key not in {"ledger_ref", "ledger_head", "cas"}
                    }
                ),
                "accepted_child_sha256": acceptance["child_sha256"],
                "observed_child": observed,
                "observed_child_sha256": outbox.digest(observed),
                "jobs_total_count": 0,
                "jobs_set_sha256": outbox.digest([]),
                "jobs_pages_scanned": 1,
                "jobs_page_cap": 100,
                "jobs_scan_complete": True,
                "admission_receipt": receipt,
                "admission_receipt_sha256": outbox.digest(receipt),
                "sealed_main_head_sha": "a" * 40,
                "observed_main_head_sha": "a" * 40,
                "sealed_subject_sha256": outbox.digest(subject),
                "observed_subject": subject,
                "observed_subject_sha256": outbox.digest(subject),
                "observation_started_at": "2026-09-01T08:31:00Z",
                "observation_completed_at": "2026-09-01T08:32:00Z",
                "verified": True,
                "productive_effect": False,
            }
            return backend, intent, acceptance, observed, observation

        for ordinal, lane in enumerate(
            ("exact-review-dispatch", "mesh-review-successor-dispatch"), 1
        ):
            with self.subTest(lane=lane):
                backend, intent, _acceptance, _observed, observation = (
                    prepared_item(lane, 6300 + ordinal * 10)
                )
                record = persist_authority_observation(
                    backend, intent, observation, run_id=6400 + ordinal
                )
                terminal = outbox.terminalize(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    evidence=terminal_evidence(
                        {
                            "d0": 3,
                            "state": "REQUEST_AUTHORITY",
                            "reason": observation["blocker"],
                            "exhaustion": ambiguity_exhaustion(
                                intent, observation["blocker"], record
                            ),
                            "productive_effect": False,
                        }
                    ),
                )
                self.assertEqual(terminal["d0"], 3)
                historical = outbox.lookup_fingerprint(
                    backend,
                    lane=lane,
                    fingerprint=intent["fingerprint"],
                )
                self.assertEqual(historical["authority_observation"], record)
                self.assertEqual(
                    historical["authority_observation"]["observation"][
                        "admission_receipt"
                    ],
                    observation["admission_receipt"],
                )
                self.assertEqual(outbox.read_next(backend, lane)["state"], "EMPTY")

        for label, mutate in (
            (
                "success",
                lambda value: value["observed_child"].update(
                    conclusion="success"
                ),
            ),
            (
                "cancelled",
                lambda value: value["observed_child"].update(
                    conclusion="cancelled"
                ),
            ),
            (
                "nonzero-jobs",
                lambda value: value.update(jobs_total_count=1),
            ),
        ):
            with self.subTest(rejected=label):
                backend, intent, _acceptance, _observed, observation = (
                    prepared_item("exact-review-dispatch", 6500)
                )
                mutate(observation)
                observation["observed_child_sha256"] = outbox.digest(
                    observation["observed_child"]
                )
                with self.assertRaises(outbox.OutboxBlock):
                    persist_authority_observation(
                        backend, intent, observation, run_id=6503
                    )

        backend, intent, _acceptance, observed, observation = prepared_item(
            "mesh-review-successor-dispatch", 6600
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "provenance"):
            outbox.record_authority_observation(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                observation=observation,
                producer=authority_observer(
                    run_id=6603, lane="mesh-review-successor-dispatch"
                ),
                artifact={
                    "id": 7603,
                    "name": (
                        "qikvrt-outbox-authority-observation-"
                        "mesh-review-successor-dispatch-1-"
                        "SOURCE_ATTEMPT_1_ACTION_REQUIRED-run-6603-attempt-1"
                    ),
                    "archive_sha256": "e" * 64,
                    "payload_sha256": outbox.sha256_bytes(
                        outbox.canonical_bytes(observation)
                    ),
                    "producer_run_id": 6603,
                    "producer_run_attempt": 1,
                    "producer_workflow_id": 902,
                },
            )

        record = persist_authority_observation(
            backend, intent, observation, run_id=6604
        )
        business_artifact = {
            "id": 7700,
            "name": "qikvrt-requested-review-admission-action-required-6602-1",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": observed["run_id"],
            "producer_run_attempt": 1,
            "verified": True,
        }
        outbox.record_completion(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=observed,
            evidence=completion_evidence(observed, business_artifact),
        )
        with self.assertRaises(outbox.OutboxBlock):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=terminal_evidence(
                    {
                        "d0": 3,
                        "state": "REQUEST_AUTHORITY",
                        "reason": observation["blocker"],
                        "exhaustion": ambiguity_exhaustion(
                            intent, observation["blocker"], record
                        ),
                        "productive_effect": False,
                    }
                ),
            )

    def test_mesh_one_shot_cursor_closures_are_exact_and_snapshot_bound(self):
        cases = (
            (0, "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED"),
            (2, "MESH_REVIEW_TRANSPORT_CHILD_AMBIGUOUS"),
            (9, "MESH_REVIEW_TRANSPORT_CHILD_SET_EXCEEDED"),
            (None, "MESH_REVIEW_RECOVERY_QUERY_BOUND_EXCEEDED"),
        )
        for offset, (successor_count, blocker) in enumerate(cases):
            with self.subTest(blocker=blocker):
                backend = MemoryBackend()
                value = payload(
                    "mesh-review-successor-dispatch", run_id=6320 + offset * 20
                )
                intent = outbox.append_intent(
                    backend, payload=value, artifact=artifact(value)
                )
                outbox.prepare_transport(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    actor_run_id=6321 + offset * 20,
                    actor_run_attempt=1,
                )
                transport = outbox.read_next(backend, intent["lane"])[
                    "transport"
                ]["1"]
                with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
                    outbox.prepare_transport(
                        backend,
                        lane=intent["lane"],
                        sequence=intent["sequence"],
                        attempt=2,
                        request=outbox.request_for_transport_attempt(intent, 2),
                        actor_run_id=6322 + offset * 20,
                        actor_run_attempt=1,
                        retry_evidence={},
                    )
                receipt = (
                    persist_capped_retry_cursor(
                        backend, intent, transport, page_cap=2
                    )
                    if successor_count is None
                    else persist_retry_cursor_result(
                        backend,
                        intent,
                        transport,
                        attempt=1,
                        successor_count=successor_count,
                    )
                )
                observation = {
                    "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
                    "blocker": blocker,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    **exact_cursor_observation_fields(intent, receipt),
                    "verified": True,
                    "productive_effect": False,
                }
                if successor_count == 0:
                    observation["transport_request_sha256"] = transport[
                        "request_sha256"
                    ]
                elif successor_count == 2:
                    observation["candidate_sha256s"] = sorted(
                        outbox.digest(item)
                        for item in receipt["record"]["cursor"][
                            "candidate_locators"
                        ]
                    )
                elif successor_count == 9:
                    observation["candidate_count"] = 9

                forged = copy.deepcopy(observation)
                forged["retry_scan_cursor_record_sha256"] = "f" * 64
                with self.assertRaisesRegex(
                    outbox.OutboxBlock, "cursor observation binding mismatch"
                ):
                    persist_authority_observation(
                        backend,
                        intent,
                        forged,
                        run_id=6323 + offset * 20,
                    )

                record = persist_authority_observation(
                    backend,
                    intent,
                    observation,
                    run_id=6324 + offset * 20,
                )
                replay = persist_authority_observation(
                    backend,
                    intent,
                    observation,
                    run_id=6324 + offset * 20,
                )
                self.assertEqual(record, replay)
                terminal = outbox.terminalize(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    evidence=terminal_evidence(
                        {
                            "d0": 3,
                            "state": "REQUEST_AUTHORITY",
                            "reason": blocker,
                            "exhaustion": ambiguity_exhaustion(
                                intent, blocker, record
                            ),
                            "productive_effect": False,
                        }
                    ),
                )
                self.assertEqual(terminal["d0"], 3)
                self.assertEqual(
                    outbox.lookup(
                        backend,
                        lane=intent["lane"],
                        sequence=intent["sequence"],
                        fingerprint=intent["fingerprint"],
                    )["effective_d0"],
                    3,
                )

    def test_mesh_missing_completion_evidence_is_inventory_bound_and_terminal(self):
        def seeded(run_id):
            backend = MemoryBackend()
            value = payload("mesh-review-successor-dispatch", run_id=run_id)
            value["subject"] = {
                "schema": "qikvrt_mesh_review_successor_subject_v1",
                "queue_intent": {
                    "pr_number": 935,
                    "head_sha": "b" * 40,
                },
            }
            value = outbox.seal_review_transport_payload(value)
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=run_id + 1,
                actor_run_attempt=1,
            )
            locator = transport_child(intent, attempt=1, run_id=run_id + 2)
            acceptance = outbox.record_acceptance(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                child=locator,
            )
            observed = {
                **locator,
                "status": "completed",
                "conclusion": "failure",
            }
            observation = {
                "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
                "blocker": "MESH_REVIEW_COMPLETION_EVIDENCE_MISSING",
                "lane": intent["lane"],
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "transport_attempt": 1,
                "child_recovery": False,
                "accepted_child_sha256": acceptance["child_sha256"],
                "observed_child": observed,
                "observed_child_sha256": outbox.digest(observed),
                "jobs_total_count": 1,
                "jobs_set_sha256": outbox.digest([{"id": run_id + 20}]),
                "jobs_pages_scanned": 1,
                "jobs_page_cap": 10,
                "jobs_scan_complete": True,
                "artifacts_total_count": 0,
                "artifact_inventory_sha256": outbox.digest([]),
                "artifacts_pages_scanned": 1,
                "artifacts_page_cap": 10,
                "artifacts_scan_complete": True,
                "observation_started_at": "2026-09-01T10:00:00Z",
                "observation_completed_at": "2026-09-01T10:01:00Z",
                "expected_artifact_name": (
                    f"qikvrt-requested-review-completion-{observed['run_id']}-"
                    f"attempt-{observed['run_attempt']}"
                ),
                "completion_artifact_count": 0,
                "completion_artifact_set_sha256": outbox.digest([]),
                "evidence_classification": "MISSING_ARTIFACT",
                "verified": True,
                "productive_effect": False,
            }
            return backend, intent, observed, observation

        backend, intent, _observed, observation = seeded(6450)
        for label, malformed in (
            (
                "zero jobs",
                {**observation, "jobs_total_count": 0},
            ),
            (
                "incomplete pages",
                {**observation, "jobs_scan_complete": False},
            ),
            (
                "wrong acceptance",
                {**observation, "accepted_child_sha256": "f" * 64},
            ),
            (
                "wrong recovery selector",
                {**observation, "child_recovery": True},
            ),
        ):
            with self.subTest(label=label):
                with self.assertRaises(outbox.OutboxBlock):
                    persist_authority_observation(
                        backend, intent, malformed, run_id=6460
                    )

        record = persist_authority_observation(
            backend, intent, observation, run_id=6461
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": observation["blocker"],
                    "exhaustion": ambiguity_exhaustion(
                        intent, observation["blocker"], record
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(terminal["d0"], 3)

        race_backend, race_intent, observed, race_observation = seeded(6470)
        race_record = persist_authority_observation(
            race_backend, race_intent, race_observation, run_id=6474
        )
        result_artifact = {
            "id": 7475,
            "name": (
                f"qikvrt-requested-review-completion-{observed['run_id']}-"
                f"attempt-{observed['run_attempt']}"
            ),
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": observed["run_id"],
            "producer_run_attempt": observed["run_attempt"],
            "verified": True,
        }
        outbox.record_completion(
            race_backend,
            lane=race_intent["lane"],
            sequence=race_intent["sequence"],
            attempt=1,
            child=observed,
            evidence=completion_evidence(observed, result_artifact),
        )
        with self.assertRaises(outbox.OutboxBlock):
            outbox.terminalize(
                race_backend,
                lane=race_intent["lane"],
                sequence=race_intent["sequence"],
                evidence=terminal_evidence(
                    {
                        "d0": 3,
                        "state": "REQUEST_AUTHORITY",
                        "reason": race_observation["blocker"],
                        "exhaustion": ambiguity_exhaustion(
                            race_intent,
                            race_observation["blocker"],
                            race_record,
                        ),
                        "productive_effect": False,
                    }
                ),
            )

    def test_target_workflow_supersession_is_exact_and_main_bound(self):
        backend = MemoryBackend()
        value = payload("mesh-review-successor-dispatch", run_id=6410)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6411,
            actor_run_attempt=1,
        )
        sealed_target = intent["payload"]["target"]
        observed_target = {**sealed_target, "workflow_id": 999}
        blocker = "OUTBOX_TARGET_WORKFLOW_SUPERSEDED"
        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": blocker,
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "sealed_target": sealed_target,
            "sealed_target_sha256": outbox.digest(sealed_target),
            "observed_target": observed_target,
            "observed_target_sha256": outbox.digest(observed_target),
            "sealed_main_head_sha": intent["payload"]["main_head_sha"],
            "observed_main_head_sha": intent["payload"]["main_head_sha"],
            "verified": True,
            "productive_effect": False,
        }
        unchanged = copy.deepcopy(observation)
        unchanged["observed_target"] = sealed_target
        unchanged["observed_target_sha256"] = outbox.digest(sealed_target)
        tampered = copy.deepcopy(observation)
        tampered["observed_target_sha256"] = "f" * 64
        wrong_sequence = copy.deepcopy(observation)
        wrong_sequence["sequence"] = 2
        for offset, malformed in enumerate((unchanged, tampered, wrong_sequence)):
            with self.subTest(malformed=offset):
                with self.assertRaises(outbox.OutboxBlock):
                    persist_authority_observation(
                        backend, intent, malformed, run_id=6412 + offset
                    )
        foreign = authority_observer(run_id=6415)
        with self.assertRaisesRegex(outbox.OutboxBlock, "provenance"):
            outbox.record_authority_observation(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                observation=observation,
                producer=foreign,
                artifact={
                    "id": 7415,
                    "name": (
                        "qikvrt-outbox-authority-observation-"
                        f"{intent['lane']}-{intent['sequence']}-{blocker}-"
                        "run-6415-attempt-1"
                    ),
                    "archive_sha256": "e" * 64,
                    "payload_sha256": outbox.sha256_bytes(
                        outbox.canonical_bytes(observation)
                    ),
                    "producer_run_id": 6415,
                    "producer_run_attempt": 1,
                    "producer_workflow_id": foreign["workflow_id"],
                },
            )
        record = persist_authority_observation(
            backend, intent, observation, run_id=6416
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": blocker,
                    "exhaustion": ambiguity_exhaustion(
                        intent, blocker, record
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(terminal["d0"], 3)

    def test_capped_retry_cursor_rejects_missing_foreign_tampered_and_drifted_proof(self):
        def seeded(run_id=6290):
            backend = MemoryBackend()
            value = payload("exact-review-dispatch", run_id=run_id)
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=run_id + 1,
                actor_run_attempt=1,
            )
            transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
            receipt = persist_capped_retry_cursor(
                backend, intent, transport, page_cap=2
            )
            return backend, intent, recovery_bound_observation(intent, receipt)

        backend, intent, observation = seeded()
        tampered = copy.deepcopy(observation)
        tampered["retry_scan_cursor_record_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            outbox.OutboxBlock, "observation.*mismatch"
        ):
            persist_authority_observation(
                backend, intent, tampered, run_id=6292
            )

        backend, intent, observation = seeded(6300)
        foreign = copy.deepcopy(observation)
        foreign["retry_scan_cursor_ledger_head"] = backend.heads[
            "exact-head-dispatch"
        ]
        with self.assertRaises(outbox.OutboxBlock):
            persist_authority_observation(
                backend, intent, foreign, run_id=6302
            )

        foreign_backend, foreign_intent, observation = seeded(6310)
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6320)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6321,
            actor_run_attempt=1,
        )
        missing = copy.deepcopy(observation)
        missing.update(
            {
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "sealed_main_head_sha": intent["payload"]["main_head_sha"],
                "observed_main_head_sha": intent["payload"]["main_head_sha"],
            }
        )
        with self.assertRaises(outbox.OutboxBlock):
            persist_authority_observation(
                backend, intent, missing, run_id=6322
            )

        backend, intent, observation = seeded(6330)
        backend.main_head = "b" * 40
        with self.assertRaisesRegex(outbox.OutboxBlock, "snapshot mismatch"):
            persist_authority_observation(
                backend, intent, observation, run_id=6332
            )

    def test_complete_null_scan_never_authorizes_a_second_new_run(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6130)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6131,
            actor_run_attempt=1,
        )
        attempt_one = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        cursor_receipt = persist_retry_cursor_result(
            backend,
            intent,
            attempt_one,
            attempt=1,
            successor_count=0,
        )
        self.assertEqual(cursor_receipt["state"], "COMPLETE_ZERO_SUCCESSOR")
        with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
            outbox.request_for_transport_attempt(intent, 2)
        with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=2,
                request={},
                actor_run_id=6132,
                actor_run_attempt=1,
                retry_evidence={},
            )
        self.assertEqual(
            set(outbox.read_next(backend, intent["lane"])["transport"]), {"1"}
        )

    def test_retry_cursor_replay_progress_boundary_and_cap_are_bounded(self):
        def seeded(run_id):
            backend = MemoryBackend()
            value = payload("exact-review-dispatch", run_id=run_id)
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=run_id + 1,
                actor_run_attempt=1,
            )
            transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
            evidence = orphan_retry_evidence(intent, transport)
            return backend, intent, transport, evidence["retry_scan_cursor"]

        backend, intent, _transport, complete_record = seeded(6150)
        complete_cursor = complete_record["cursor"]
        complete_artifact = complete_record["artifact"]
        first = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=complete_cursor,
            artifact=complete_artifact,
        )
        replay = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=complete_cursor,
            artifact=complete_artifact,
        )
        self.assertEqual(first["record_sha256"], replay["record_sha256"])
        self.assertFalse(replay["cas"]["appended"])

        backend, intent, _transport, template = seeded(6160)
        incomplete = copy.deepcopy(template["cursor"])
        first_page_run_ids = list(range(6000, 5900, -1))
        incomplete.update(
            {
                "scan_complete": False,
                "same_second_boundary_complete": True,
                "next_page": 2,
                "page_cap": 3,
                "pages_scanned": 1,
                "declared_total_count": 300,
                "queried_page": 1,
                "page_run_ids": first_page_run_ids,
                "page_run_ids_sha256": outbox.digest(first_page_run_ids),
                "cumulative_run_ids": first_page_run_ids,
                "cumulative_run_ids_sha256": outbox.digest(first_page_run_ids),
                "observed_unique_run_count": 100,
                "last_scanned_run_id": first_page_run_ids[-1],
            }
        )
        incomplete_artifact = copy.deepcopy(template["artifact"])
        incomplete_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(incomplete)
        )
        incomplete_first = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=incomplete,
            artifact=incomplete_artifact,
        )
        incomplete_replay = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=incomplete,
            artifact=incomplete_artifact,
        )
        self.assertEqual(
            incomplete_replay["record_sha256"], incomplete_first["record_sha256"]
        )
        self.assertFalse(incomplete_replay["cas"]["appended"])

        ordinal_two = copy.deepcopy(incomplete)
        second_page_run_ids = list(range(5900, 5800, -1))
        first_two_pages = sorted(
            set(first_page_run_ids) | set(second_page_run_ids), reverse=True
        )
        ordinal_two.update(
            {
                "ordinal": 2,
                "previous_cursor_sha256": outbox.digest(
                    incomplete_first["record"]
                ),
                "next_page": 3,
                "pages_scanned": 2,
                "queried_page": 2,
                "page_run_ids": second_page_run_ids,
                "page_run_ids_sha256": outbox.digest(second_page_run_ids),
                "cumulative_run_ids": first_two_pages,
                "cumulative_run_ids_sha256": outbox.digest(first_two_pages),
                "observed_unique_run_count": 200,
                "last_scanned_run_id": second_page_run_ids[-1],
                "observation_started_at": "2026-09-01T09:01:00Z",
                "observation_completed_at": "2026-09-01T09:02:00Z",
            }
        )
        ordinal_two["observation_producer"]["run_id"] += 1
        ordinal_two["observation_producer_sha256"] = outbox.digest(
            ordinal_two["observation_producer"]
        )
        ordinal_two_artifact = copy.deepcopy(incomplete_artifact)
        ordinal_two_artifact.update(
            {
                "id": ordinal_two_artifact["id"] + 1,
                "name": (
                    f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
                    f"{intent['sequence']}-attempt-1-ordinal-2-run-"
                    f"{ordinal_two['observation_producer']['run_id']}-attempt-1"
                ),
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(ordinal_two)
                ),
                "producer_run_id": ordinal_two["observation_producer"]["run_id"],
            }
        )
        second = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=ordinal_two,
            artifact=ordinal_two_artifact,
        )
        self.assertEqual(second["record"]["cursor"]["ordinal"], 2)
        later_end_drift = copy.deepcopy(ordinal_two)
        third_page_run_ids = list(range(5800, 5700, -1))
        first_three_pages = sorted(
            set(first_two_pages) | set(third_page_run_ids), reverse=True
        )
        later_end_drift.update(
            {
                "ordinal": 3,
                "previous_cursor_sha256": outbox.digest(second["record"]),
                "next_page": None,
                "pages_scanned": 3,
                "queried_page": 3,
                "page_run_ids": third_page_run_ids,
                "page_run_ids_sha256": outbox.digest(third_page_run_ids),
                "cumulative_run_ids": first_three_pages,
                "cumulative_run_ids_sha256": outbox.digest(first_three_pages),
                "observed_unique_run_count": 300,
                "last_scanned_run_id": third_page_run_ids[-1],
                "scan_complete": True,
                "query_window_end": "2026-09-01T09:03:00Z",
                "observation_started_at": "2026-09-01T09:03:00Z",
                "observation_completed_at": "2026-09-01T09:04:00Z",
            }
        )
        later_end_drift["observation_producer"]["run_id"] += 2
        later_end_drift["observation_producer_sha256"] = outbox.digest(
            later_end_drift["observation_producer"]
        )
        later_end_artifact = copy.deepcopy(ordinal_two_artifact)
        later_end_artifact.update(
            {
                "id": later_end_artifact["id"] + 2,
                "name": (
                    f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
                    f"{intent['sequence']}-attempt-1-ordinal-3-run-"
                    f"{later_end_drift['observation_producer']['run_id']}-attempt-1"
                ),
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(later_end_drift)
                ),
                "producer_run_id": later_end_drift["observation_producer"][
                    "run_id"
                ],
            }
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "monotone continuation"):
            outbox.record_retry_scan_cursor(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                cursor=later_end_drift,
                artifact=later_end_artifact,
            )

        collision = copy.deepcopy(ordinal_two)
        collision_artifact = copy.deepcopy(ordinal_two_artifact)
        collision_artifact["id"] += 99
        collision_artifact["archive_sha256"] = "8" * 64
        with self.assertRaisesRegex(outbox.OutboxBlock, "ordinal collision"):
            outbox.record_retry_scan_cursor(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                cursor=collision,
                artifact=collision_artifact,
            )

        # The same updated_at second is first persisted as a D2 boundary
        # stabilization cursor.  A later higher run id can then expand the
        # upper bound before it is frozen and is durably retained for adoption.
        backend, intent, _transport, template = seeded(6170)
        boundary = copy.deepcopy(template["cursor"])
        boundary.update(
            {
                "same_second_boundary_complete": False,
                "scan_complete": False,
                "upper_bound_run_id": 7000,
                "last_scanned_run_id": 7000,
                "next_page": 1,
                "pages_scanned": 0,
                "declared_total_count": None,
                "queried_page": None,
            }
        )
        boundary_artifact = copy.deepcopy(template["artifact"])
        boundary_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(boundary)
        )
        boundary_first = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=boundary,
            artifact=boundary_artifact,
        )
        self.assertEqual(
            boundary_first["state"], "BOUNDARY_STABILIZATION_REOBSERVE"
        )
        null_page_boundary = copy.deepcopy(boundary)
        null_page_boundary["next_page"] = None
        null_page_artifact = copy.deepcopy(boundary_artifact)
        null_page_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(null_page_boundary)
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "cursor binding"):
            outbox.record_retry_scan_cursor(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                cursor=null_page_boundary,
                artifact=null_page_artifact,
            )
        boundary_replay = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=boundary,
            artifact=boundary_artifact,
        )
        self.assertFalse(boundary_replay["cas"]["appended"])
        for ordinal in range(2, 12):
            repeated_boundary = copy.deepcopy(boundary)
            repeated_boundary.update(
                {
                    "ordinal": ordinal,
                    "previous_cursor_sha256": outbox.digest(
                        boundary_first["record"]
                    ),
                    "upper_bound_run_id": 7000 + ordinal,
                    "last_scanned_run_id": 7000 + ordinal,
                }
            )
            repeated_boundary["observation_producer"]["run_id"] += ordinal
            repeated_boundary["observation_producer_sha256"] = outbox.digest(
                repeated_boundary["observation_producer"]
            )
            repeated_artifact = copy.deepcopy(boundary_artifact)
            repeated_artifact.update(
                {
                    "id": repeated_artifact["id"] + ordinal,
                    "name": (
                        f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
                        f"{intent['sequence']}-attempt-1-ordinal-{ordinal}-run-"
                        f"{repeated_boundary['observation_producer']['run_id']}-"
                        "attempt-1"
                    ),
                    "payload_sha256": outbox.sha256_bytes(
                        outbox.canonical_bytes(repeated_boundary)
                    ),
                    "producer_run_id": repeated_boundary[
                        "observation_producer"
                    ]["run_id"],
                }
            )
            with self.assertRaises(outbox.OutboxBlock):
                outbox.record_retry_scan_cursor(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    cursor=repeated_boundary,
                    artifact=repeated_artifact,
                )

        inputs = intent["payload"]["request"]["inputs"]
        late_child = {
            "run_id": 7001,
            "run_attempt": 1,
            "workflow_id": intent["payload"]["target"]["workflow_id"],
            "workflow_path": intent["payload"]["target"]["workflow_path"],
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": inputs["evaluator_sha"],
            "status": "queued",
            "conclusion": None,
            "display_title": (
                f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
                f"h={inputs['head']} f={inputs['fingerprint']} "
                f"i={intent['fingerprint']} a=1"
            ),
        }
        boundary_final = copy.deepcopy(boundary)
        boundary_page_run_ids = [7001]
        boundary_final.update(
            {
                "ordinal": 2,
                "previous_cursor_sha256": outbox.digest(boundary_first["record"]),
                "same_second_boundary_complete": True,
                "scan_complete": True,
                "upper_bound_run_id": 7001,
                "last_scanned_run_id": 7001,
                "next_page": None,
                "pages_scanned": 1,
                "declared_total_count": 1,
                "queried_page": 1,
                "page_run_ids": boundary_page_run_ids,
                "page_run_ids_sha256": outbox.digest(boundary_page_run_ids),
                "cumulative_run_ids": boundary_page_run_ids,
                "cumulative_run_ids_sha256": outbox.digest(
                    boundary_page_run_ids
                ),
                "page_candidate_run_ids": boundary_page_run_ids,
                "page_candidate_run_ids_sha256": outbox.digest(
                    boundary_page_run_ids
                ),
                "cumulative_candidate_run_ids": boundary_page_run_ids,
                "cumulative_candidate_run_ids_sha256": outbox.digest(
                    boundary_page_run_ids
                ),
                "observed_unique_run_count": 1,
                "candidates_seen": 1,
                "candidate_locators": [late_child],
                "candidate_set_sha256": outbox.digest([late_child]),
                "bound_successor_count": 1,
                "query_window_end": "2026-09-01T09:01:00Z",
                "observation_started_at": "2026-09-01T09:01:00Z",
                "observation_completed_at": "2026-09-01T09:02:00Z",
            }
        )
        boundary_final["observation_producer"]["run_id"] += 1
        boundary_final["observation_producer_sha256"] = outbox.digest(
            boundary_final["observation_producer"]
        )
        boundary_final_artifact = copy.deepcopy(boundary_artifact)
        boundary_final_artifact.update(
            {
                "id": boundary_final_artifact["id"] + 1,
                "name": (
                    f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
                    f"{intent['sequence']}-attempt-1-ordinal-2-run-"
                    f"{boundary_final['observation_producer']['run_id']}-attempt-1"
                ),
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(boundary_final)
                ),
                "producer_run_id": boundary_final["observation_producer"]["run_id"],
            }
        )
        observed = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=boundary_final,
            artifact=boundary_final_artifact,
        )
        self.assertEqual(observed["state"], "COMPLETE_SUCCESSOR_OBSERVED")
        self.assertEqual(
            observed["record"]["cursor"]["candidate_locators"], [late_child]
        )

        backend, intent, transport, _template = seeded(6180)
        cap_receipt = persist_capped_retry_cursor(
            backend, intent, transport, page_cap=2
        )
        self.assertEqual(cap_receipt["state"], "SCAN_BOUND_EXCEEDED_AUTHORITY")
        with self.assertRaisesRegex(
            outbox.OutboxBlock, "not an authorized|retry evidence binding"
        ):
            outbox.validate_retry_evidence(
                {
                    "schema": outbox.RETRY_EVIDENCE_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "attempt": 1,
                    "classification": "ORPHAN_NO_BOUND_SUCCESSOR",
                    "first_blocker": "ATTEMPT_1_HAS_NO_BOUND_SUCCESSOR",
                    "successor": None,
                    "retry_scan_cursor": cap_receipt["record"],
                    "retry_scan_cursor_sha256": outbox.digest(cap_receipt["record"]),
                    "d0": 2,
                    "verified": True,
                    "productive_effect": False,
                },
                lane=intent["lane"],
                sequence=intent["sequence"],
                fingerprint=intent["fingerprint"],
                attempt_one_accepted=False,
                attempt_one_transport=outbox.read_next(backend, intent["lane"])[
                    "transport"
                ]["1"],
                intent=intent,
                retry_scan_cursor=cap_receipt["record"],
            )
        malformed = copy.deepcopy(cap_receipt["record"]["cursor"])
        malformed["bound_successor_count"] = "zero"
        malformed_artifact = copy.deepcopy(cap_receipt["record"]["artifact"])
        malformed_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(malformed)
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "bound successor count"):
            outbox.record_retry_scan_cursor(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                cursor=malformed,
                artifact=malformed_artifact,
            )

    def test_retry_cursor_candidate_set_is_monotone_and_cannot_erase_a_child(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6440)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6441,
            actor_run_attempt=1,
        )
        transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        template = orphan_retry_evidence(intent, transport)["retry_scan_cursor"]
        first_child = transport_child(intent, attempt=1, run_id=8002)
        first_page_run_ids = list(range(8101, 8001, -1))
        first_cursor = copy.deepcopy(template["cursor"])
        first_cursor.update(
            page_cap=3,
            pages_scanned=1,
            next_page=2,
            declared_total_count=200,
            queried_page=1,
            page_run_ids=first_page_run_ids,
            page_run_ids_sha256=outbox.digest(first_page_run_ids),
            cumulative_run_ids=first_page_run_ids,
            cumulative_run_ids_sha256=outbox.digest(first_page_run_ids),
            page_candidate_run_ids=[8002],
            page_candidate_run_ids_sha256=outbox.digest([8002]),
            cumulative_candidate_run_ids=[8002],
            cumulative_candidate_run_ids_sha256=outbox.digest([8002]),
            observed_unique_run_count=100,
            last_scanned_run_id=8002,
            candidates_seen=1,
            candidate_locators=[first_child],
            candidate_set_sha256=outbox.digest([first_child]),
            bound_successor_count=1,
            scan_complete=False,
        )
        first_artifact = copy.deepcopy(template["artifact"])
        first_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(first_cursor)
        )
        first = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=first_cursor,
            artifact=first_artifact,
        )

        second_child = transport_child(intent, attempt=1, run_id=8001)
        second_page_run_ids = list(range(8001, 7901, -1))
        both_page_run_ids = sorted(
            set(first_page_run_ids) | set(second_page_run_ids), reverse=True
        )
        replaced = copy.deepcopy(first_cursor)
        replaced.update(
            ordinal=2,
            previous_cursor_sha256=outbox.digest(first["record"]),
            pages_scanned=2,
            queried_page=2,
            next_page=None,
            page_run_ids=second_page_run_ids,
            page_run_ids_sha256=outbox.digest(second_page_run_ids),
            cumulative_run_ids=both_page_run_ids,
            cumulative_run_ids_sha256=outbox.digest(both_page_run_ids),
            page_candidate_run_ids=[8001],
            page_candidate_run_ids_sha256=outbox.digest([8001]),
            cumulative_candidate_run_ids=[8001],
            cumulative_candidate_run_ids_sha256=outbox.digest([8001]),
            observed_unique_run_count=200,
            last_scanned_run_id=7902,
            candidates_seen=1,
            candidate_locators=[second_child],
            candidate_set_sha256=outbox.digest([second_child]),
            bound_successor_count=1,
            scan_complete=True,
            observation_started_at="2026-09-01T09:01:00Z",
            observation_completed_at="2026-09-01T09:02:00Z",
        )
        replaced_producer = {
            **replaced["observation_producer"],
            "run_id": replaced["observation_producer"]["run_id"] + 1,
        }
        replaced["observation_producer"] = replaced_producer
        replaced["observation_producer_sha256"] = outbox.digest(
            replaced_producer
        )
        replaced_artifact = {
            **first_artifact,
            "id": first_artifact["id"] + 1,
            "name": (
                f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
                f"{intent['sequence']}-attempt-1-ordinal-2-run-"
                f"{replaced_producer['run_id']}-attempt-"
                f"{replaced_producer['run_attempt']}"
            ),
            "payload_sha256": outbox.sha256_bytes(
                outbox.canonical_bytes(replaced)
            ),
            "producer_run_id": replaced_producer["run_id"],
        }
        with self.assertRaisesRegex(outbox.OutboxBlock, "monotone continuation"):
            outbox.record_retry_scan_cursor(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                cursor=replaced,
                artifact=replaced_artifact,
            )

        foreign = copy.deepcopy(replaced)
        foreign_child = transport_child(intent, attempt=1, run_id=7777)
        foreign["candidate_locators"] = [foreign_child]
        foreign["candidate_set_sha256"] = outbox.digest([foreign_child])
        foreign_artifact = {
            **replaced_artifact,
            "payload_sha256": outbox.sha256_bytes(
                outbox.canonical_bytes(foreign)
            ),
        }
        with self.assertRaisesRegex(outbox.OutboxBlock, "cursor binding"):
            outbox.record_retry_scan_cursor(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                cursor=foreign,
                artifact=foreign_artifact,
            )

        union = copy.deepcopy(replaced)
        union_candidates = sorted(
            [first_child, second_child],
            key=lambda item: item["run_id"],
            reverse=True,
        )
        union.update(
            cumulative_candidate_run_ids=[8002, 8001],
            cumulative_candidate_run_ids_sha256=outbox.digest([8002, 8001]),
            candidates_seen=2,
            candidate_locators=union_candidates,
            candidate_set_sha256=outbox.digest(union_candidates),
            bound_successor_count=2,
        )
        union_artifact = {
            **replaced_artifact,
            "payload_sha256": outbox.sha256_bytes(
                outbox.canonical_bytes(union)
            ),
        }
        persisted = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=union,
            artifact=union_artifact,
        )
        self.assertEqual(
            [
                item["run_id"]
                for item in persisted["record"]["cursor"]["candidate_locators"]
            ],
            [8002, 8001],
        )

    def test_retry_cursor_inventory_never_false_closes_and_drift_is_durable(self):
        def seeded(run_id):
            backend = MemoryBackend()
            value = payload("exact-review-dispatch", run_id=run_id)
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=run_id + 1,
                actor_run_attempt=1,
            )
            transport = outbox.read_next(backend, intent["lane"])["transport"][
                "1"
            ]
            template = orphan_retry_evidence(intent, transport)[
                "retry_scan_cursor"
            ]
            return backend, intent, template

        backend, intent, template = seeded(6450)
        false_zero = copy.deepcopy(template["cursor"])
        false_zero["declared_total_count"] = 1
        false_zero_artifact = copy.deepcopy(template["artifact"])
        false_zero_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(false_zero)
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "cursor binding"):
            outbox.record_retry_scan_cursor(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                cursor=false_zero,
                artifact=false_zero_artifact,
            )

        short_page = copy.deepcopy(template["cursor"])
        short_page_run_ids = [7000]
        short_page.update(
            {
                "scan_complete": False,
                "next_page": None,
                "declared_total_count": 2,
                "page_run_ids": short_page_run_ids,
                "page_run_ids_sha256": outbox.digest(short_page_run_ids),
                "cumulative_run_ids": short_page_run_ids,
                "cumulative_run_ids_sha256": outbox.digest(short_page_run_ids),
                "observed_unique_run_count": 1,
                "last_scanned_run_id": 7000,
                "inventory_consistent": False,
                "inventory_blocker": "SHORT_PAGE_BEFORE_DECLARED_TOTAL",
            }
        )
        short_page_artifact = copy.deepcopy(template["artifact"])
        short_page_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(short_page)
        )
        short_receipt = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=short_page,
            artifact=short_page_artifact,
        )
        self.assertEqual(
            short_receipt["state"], "SCAN_INVENTORY_INCONSISTENT_AUTHORITY"
        )

        for offset, raw_ids, cumulative_ids, blocker in (
            (1, [7000, 7000], [7000], "PAGE_RUN_ID_DUPLICATE"),
            (
                2,
                [6999, 7000],
                [7000, 6999],
                "PAGE_RUN_ID_PAGE_ORDER_DRIFT",
            ),
        ):
            with self.subTest(raw_page_blocker=blocker):
                raw_backend, raw_intent, raw_template = seeded(6450 + offset)
                raw_page = copy.deepcopy(raw_template["cursor"])
                raw_page.update(
                    {
                        "scan_complete": False,
                        "next_page": None,
                        "declared_total_count": len(raw_ids),
                        "page_run_ids": raw_ids,
                        "page_run_ids_sha256": outbox.digest(raw_ids),
                        "cumulative_run_ids": cumulative_ids,
                        "cumulative_run_ids_sha256": outbox.digest(
                            cumulative_ids
                        ),
                        "observed_unique_run_count": len(cumulative_ids),
                        "last_scanned_run_id": min(raw_ids),
                        "inventory_consistent": False,
                        "inventory_blocker": blocker,
                    }
                )
                raw_artifact = copy.deepcopy(raw_template["artifact"])
                raw_artifact["payload_sha256"] = outbox.sha256_bytes(
                    outbox.canonical_bytes(raw_page)
                )
                raw_receipt = outbox.record_retry_scan_cursor(
                    raw_backend,
                    lane=raw_intent["lane"],
                    sequence=raw_intent["sequence"],
                    cursor=raw_page,
                    artifact=raw_artifact,
                )
                self.assertEqual(
                    raw_receipt["record"]["cursor"]["inventory_blocker"],
                    blocker,
                )
                self.assertEqual(
                    raw_receipt["state"],
                    "SCAN_INVENTORY_INCONSISTENT_AUTHORITY",
                )

        backend, intent, template = seeded(6460)
        first_page = copy.deepcopy(template["cursor"])
        first_page_ids = list(range(9000, 8900, -1))
        first_page.update(
            {
                "scan_complete": False,
                "next_page": 2,
                "page_cap": 2,
                "declared_total_count": 200,
                "page_run_ids": first_page_ids,
                "page_run_ids_sha256": outbox.digest(first_page_ids),
                "cumulative_run_ids": first_page_ids,
                "cumulative_run_ids_sha256": outbox.digest(first_page_ids),
                "observed_unique_run_count": 100,
                "last_scanned_run_id": first_page_ids[-1],
            }
        )
        first_artifact = copy.deepcopy(template["artifact"])
        first_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(first_page)
        )
        first = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=first_page,
            artifact=first_artifact,
        )

        shifted_page_ids = list(range(10099, 9999, -1))
        shifted_cumulative = sorted(
            set(first_page_ids) | set(shifted_page_ids), reverse=True
        )
        shifted = copy.deepcopy(first_page)
        shifted.update(
            {
                "ordinal": 2,
                "previous_cursor_sha256": outbox.digest(first["record"]),
                "pages_scanned": 2,
                "queried_page": 2,
                "next_page": None,
                "page_run_ids": shifted_page_ids,
                "page_run_ids_sha256": outbox.digest(shifted_page_ids),
                "cumulative_run_ids": shifted_cumulative,
                "cumulative_run_ids_sha256": outbox.digest(shifted_cumulative),
                "observed_unique_run_count": 200,
                "last_scanned_run_id": shifted_page_ids[-1],
                "inventory_consistent": False,
                "inventory_blocker": "PAGE_RUN_ID_ORDER_DRIFT",
                "observation_started_at": "2026-09-01T09:01:00Z",
                "observation_completed_at": "2026-09-01T09:02:00Z",
            }
        )
        shifted["observation_producer"]["run_id"] += 1
        shifted["observation_producer_sha256"] = outbox.digest(
            shifted["observation_producer"]
        )
        shifted_artifact = copy.deepcopy(first_artifact)
        shifted_artifact.update(
            {
                "id": shifted_artifact["id"] + 1,
                "name": (
                    f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
                    f"{intent['sequence']}-attempt-1-ordinal-2-run-"
                    f"{shifted['observation_producer']['run_id']}-attempt-1"
                ),
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(shifted)
                ),
                "producer_run_id": shifted["observation_producer"]["run_id"],
            }
        )
        shifted_receipt = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=shifted,
            artifact=shifted_artifact,
        )
        self.assertEqual(
            shifted_receipt["state"], "SCAN_INVENTORY_INCONSISTENT_AUTHORITY"
        )
        self.assertEqual(
            shifted_receipt["record"]["cursor"]["inventory_blocker"],
            "PAGE_RUN_ID_ORDER_DRIFT",
        )

    def test_retry_cursor_overflow_retains_monotone_witness_subset(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6470)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6471,
            actor_run_attempt=1,
        )
        transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        template = orphan_retry_evidence(intent, transport)["retry_scan_cursor"]
        first_page_ids = list(range(9100, 9000, -1))
        first_candidate_ids = first_page_ids[:8]
        first_candidates = [
            transport_child(intent, attempt=1, run_id=run_id)
            for run_id in first_candidate_ids
        ]
        first_cursor = copy.deepcopy(template["cursor"])
        first_cursor.update(
            {
                "page_cap": 2,
                "pages_scanned": 1,
                "declared_total_count": 200,
                "next_page": 2,
                "scan_complete": False,
                "page_run_ids": first_page_ids,
                "page_run_ids_sha256": outbox.digest(first_page_ids),
                "cumulative_run_ids": first_page_ids,
                "cumulative_run_ids_sha256": outbox.digest(first_page_ids),
                "page_candidate_run_ids": first_candidate_ids,
                "page_candidate_run_ids_sha256": outbox.digest(
                    first_candidate_ids
                ),
                "cumulative_candidate_run_ids": first_candidate_ids,
                "cumulative_candidate_run_ids_sha256": outbox.digest(
                    first_candidate_ids
                ),
                "observed_unique_run_count": 100,
                "last_scanned_run_id": first_page_ids[-1],
                "candidates_seen": 8,
                "candidate_locators": first_candidates,
                "candidate_set_sha256": outbox.digest(first_candidates),
                "bound_successor_count": 8,
            }
        )
        first_artifact = copy.deepcopy(template["artifact"])
        first_artifact["payload_sha256"] = outbox.sha256_bytes(
            outbox.canonical_bytes(first_cursor)
        )
        first = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=first_cursor,
            artifact=first_artifact,
        )

        second_page_ids = list(range(9000, 8900, -1))
        all_page_ids = sorted(
            set(first_page_ids) | set(second_page_ids), reverse=True
        )
        all_candidate_ids = first_candidate_ids + [9000]
        overflow = copy.deepcopy(first_cursor)
        overflow.update(
            {
                "ordinal": 2,
                "previous_cursor_sha256": outbox.digest(first["record"]),
                "pages_scanned": 2,
                "queried_page": 2,
                "next_page": None,
                "scan_complete": True,
                "page_run_ids": second_page_ids,
                "page_run_ids_sha256": outbox.digest(second_page_ids),
                "cumulative_run_ids": all_page_ids,
                "cumulative_run_ids_sha256": outbox.digest(all_page_ids),
                "page_candidate_run_ids": [9000],
                "page_candidate_run_ids_sha256": outbox.digest([9000]),
                "cumulative_candidate_run_ids": all_candidate_ids,
                "cumulative_candidate_run_ids_sha256": outbox.digest(
                    all_candidate_ids
                ),
                "observed_unique_run_count": 200,
                "last_scanned_run_id": second_page_ids[-1],
                "candidates_seen": 9,
                # The first eight immutable locators remain the witness subset;
                # the complete nine-ID inventory proves the overflow.
                "candidate_locators": first_candidates,
                "candidate_set_sha256": outbox.digest(all_candidate_ids),
                "bound_successor_count": 9,
                "observation_started_at": "2026-09-01T09:01:00Z",
                "observation_completed_at": "2026-09-01T09:02:00Z",
            }
        )
        overflow["observation_producer"]["run_id"] += 1
        overflow["observation_producer_sha256"] = outbox.digest(
            overflow["observation_producer"]
        )
        overflow_artifact = copy.deepcopy(first_artifact)
        overflow_artifact.update(
            {
                "id": overflow_artifact["id"] + 1,
                "name": (
                    f"qikvrt-outbox-retry-scan-cursor-{intent['lane']}-"
                    f"{intent['sequence']}-attempt-1-ordinal-2-run-"
                    f"{overflow['observation_producer']['run_id']}-attempt-1"
                ),
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(overflow)
                ),
                "producer_run_id": overflow["observation_producer"]["run_id"],
            }
        )
        receipt = outbox.record_retry_scan_cursor(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            cursor=overflow,
            artifact=overflow_artifact,
        )
        self.assertEqual(receipt["state"], "AMBIGUITY_SET_EXCEEDED_AUTHORITY")
        self.assertEqual(
            [
                child["run_id"]
                for child in receipt["record"]["cursor"]["candidate_locators"]
            ],
            first_candidate_ids,
        )
        self.assertEqual(
            receipt["record"]["cursor"]["candidate_set_sha256"],
            outbox.digest(all_candidate_ids),
        )

    def test_exact_review_complete_ambiguity_and_missing_business_are_terminal(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6140)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6141,
            actor_run_attempt=1,
        )
        transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        cursor_receipt = persist_retry_cursor_result(
            backend,
            intent,
            transport,
            attempt=1,
            successor_count=9,
        )
        ambiguity = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "BOUND_EVIDENCE_AMBIGUITY_SET_EXCEEDED",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            **exact_cursor_observation_fields(intent, cursor_receipt),
            "candidate_count": 9,
            "verified": True,
            "productive_effect": False,
        }
        ambiguity_record = persist_authority_observation(
            backend, intent, ambiguity, run_id=6142
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": ambiguity["blocker"],
                    "exhaustion": ambiguity_exhaustion(
                        intent, ambiguity["blocker"], ambiguity_record
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(terminal["d0"], 3)

        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=6143)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6144,
            actor_run_attempt=1,
        )
        locator = {
            "run_id": 6145,
            "run_attempt": 1,
            "workflow_id": 77,
            "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": (
                "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h=" + "b" * 40
                + " f=" + "c" * 64 + " i=" + intent["fingerprint"]
                + " a=1"
            ),
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=locator,
        )
        observed = {**locator, "status": "completed", "conclusion": "success"}
        missing_business = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "EXACT_REVIEW_BUSINESS_EVIDENCE_MISSING",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "transport_attempt": 1,
            "accepted_child_sha256": acceptance["child_sha256"],
            "observed_child": observed,
            "observed_child_sha256": outbox.digest(observed),
            "jobs_total_count": 4,
            "completion_envelope_artifact_name": (
                "qikvrt-requested-review-completion-6145-attempt-1"
            ),
            "completion_envelope_artifact_count": 1,
            "expected_business_artifact_prefix": (
                "qikvrt-mesh-review-pr-935-" + "b" * 40 + "-"
            ),
            "expected_business_artifact_suffix": "-run-6145-attempt-1",
            "business_evidence_classification": "MISSING_ARTIFACT",
            "business_artifact_count": 0,
            "business_artifact_set_sha256": outbox.digest([]),
            "scan_complete": True,
            "verified": True,
            "productive_effect": False,
        }
        record = persist_authority_observation(
            backend, intent, missing_business, run_id=6146
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": missing_business["blocker"],
                    "exhaustion": ambiguity_exhaustion(
                        intent, missing_business["blocker"], record
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(terminal["d0"], 3)

    def test_exact_head_async_missing_result_evidence_is_explicit_hold(self):
        backend = MemoryBackend()
        value = payload("exact-head-dispatch", run_id=6150)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6151,
            actor_run_attempt=1,
        )
        locator = {
            "run_id": 6152,
            "run_attempt": 1,
            "workflow_id": 66,
            "workflow_path": ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
            "event": "repository_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": (
                f"qikvrt-exact intent={intent['fingerprint']} "
                f"seq={intent['sequence']} transport-attempt=1"
            ),
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=locator,
        )
        observed = {**locator, "status": "completed", "conclusion": "failure"}
        missing = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "EXACT_HEAD_COMPLETION_EVIDENCE_MISSING",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "transport_attempt": 1,
            "accepted_child_sha256": acceptance["child_sha256"],
            "observed_child": observed,
            "observed_child_sha256": outbox.digest(observed),
            "same_run_result": False,
            "jobs_total_count": 2,
            "expected_artifact_name": "qikvrt-exact-head-business-result-6152-1",
            "evidence_classification": "MISSING_ARTIFACT",
            "artifact_count": 0,
            "artifact_set_sha256": outbox.digest([]),
            "scan_complete": True,
            "verified": True,
            "productive_effect": False,
        }
        record = persist_authority_observation(
            backend, intent, missing, run_id=6153
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": missing["blocker"],
                    "exhaustion": ambiguity_exhaustion(
                        intent, missing["blocker"], record
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(terminal["d0"], 3)

    def test_lookup_distinguishes_current_pending_from_future_queued(self):
        backend = MemoryBackend()
        first_value = payload(run_id=301, subject="first")
        second_value = payload(run_id=302, subject="second")
        first = outbox.append_intent(
            backend, payload=first_value, artifact=artifact(first_value)
        )
        second = outbox.append_intent(
            backend, payload=second_value, artifact=artifact(second_value)
        )
        current = outbox.lookup(
            backend,
            lane=first["lane"],
            sequence=first["sequence"],
            fingerprint=first["fingerprint"],
        )
        queued = outbox.lookup(
            backend,
            lane=second["lane"],
            sequence=second["sequence"],
            fingerprint=second["fingerprint"],
        )
        self.assertEqual(current["lookup_state"], "PENDING")
        self.assertEqual(queued["lookup_state"], "QUEUED")
        self.assertEqual(queued["state"], "QUEUED")
        self.assertLess(queued["meta"]["drain_seq"], queued["sequence"])

    def test_read_results_bind_one_exact_ledger_ref_and_head_snapshot(self):
        backend = MemoryBackend()
        first_value = payload(run_id=303, subject="snapshot-first")
        second_value = payload(run_id=304, subject="snapshot-second")
        first = outbox.append_intent(
            backend, payload=first_value, artifact=artifact(first_value)
        )
        second = outbox.append_intent(
            backend, payload=second_value, artifact=artifact(second_value)
        )
        sealed_head = backend.heads[first["lane"]]
        exact_ref = outbox.ledger_ref(first["lane"])

        for result in (
            outbox.read_next(backend, first["lane"]),
            outbox.lookup(
                backend,
                lane=first["lane"],
                sequence=first["sequence"],
                fingerprint=first["fingerprint"],
            ),
            outbox.lookup(
                backend,
                lane=second["lane"],
                sequence=second["sequence"],
                fingerprint=second["fingerprint"],
            ),
        ):
            self.assertEqual(result["ledger_ref"], exact_ref)
            self.assertEqual(result["ledger_head"], sealed_head)

        calls = []

        def drifting_get_head(lane):
            calls.append(lane)
            if len(calls) == 1:
                return sealed_head
            rival = backend.build_commit(
                sealed_head,
                {"unrelated/post-snapshot.json": outbox.canonical_bytes({"n": 2})},
                "post-snapshot ref advance",
            )
            backend.heads[lane] = rival
            return rival

        with mock.patch.object(backend, "get_ledger_head", side_effect=drifting_get_head):
            by_fingerprint = outbox.lookup_fingerprint(
                backend,
                lane=first["lane"],
                fingerprint=first["fingerprint"],
            )
        self.assertEqual(calls, [first["lane"]])
        self.assertEqual(by_fingerprint["ledger_ref"], exact_ref)
        self.assertEqual(by_fingerprint["ledger_head"], sealed_head)
        self.assertEqual(by_fingerprint["sequence"], first["sequence"])
        self.assertEqual(by_fingerprint["fingerprint"], first["fingerprint"])

        empty_backend = MemoryBackend()
        empty = outbox.read_next(empty_backend, first["lane"])
        self.assertEqual(empty["ledger_ref"], exact_ref)
        self.assertEqual(empty["ledger_head"], empty_backend.heads[first["lane"]])

    def test_authority_observations_are_content_addressed_and_replayable(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=305)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=306,
            actor_run_attempt=1,
        )
        pending = outbox.read_next(backend, intent["lane"])
        attempt_one = pending["transport"]["1"]
        cursor_receipt = persist_retry_cursor_result(
            backend,
            intent,
            attempt_one,
            attempt=1,
            successor_count=2,
        )
        cursor_candidates = cursor_receipt["record"]["cursor"][
            "candidate_locators"
        ]
        observation_a = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "BOUND_EVIDENCE_AMBIGUOUS",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            **exact_cursor_observation_fields(intent, cursor_receipt),
            "candidate_sha256s": sorted(
                outbox.digest(item) for item in cursor_candidates
            ),
            "verified": True,
            "productive_effect": False,
        }
        record_a = persist_authority_observation(
            backend, intent, observation_a, run_id=307
        )
        # A crash after the immutable observation CAS can replay exactly the
        # same record without colliding or creating a different FIFO slot.
        replay_a = persist_authority_observation(
            backend, intent, observation_a, run_id=307
        )
        self.assertEqual(record_a, replay_a)
        path_a = outbox.authority_observation_path(
            intent["lane"], intent["sequence"], outbox.digest(record_a)
        )
        self.assertIsNotNone(backend.read_file(backend.head, path_a))

        request = intent["payload"]["request"]
        inputs = request["inputs"]
        accepted = {
            "run_id": 308,
            "run_attempt": 1,
            "workflow_id": intent["payload"]["target"]["workflow_id"],
            "workflow_path": intent["payload"]["target"]["workflow_path"],
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": inputs["evaluator_sha"],
            "status": "queued",
            "conclusion": None,
            "display_title": (
                f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
                f"h={inputs['head']} f={inputs['fingerprint']} "
                f"i={intent['fingerprint']} a=1"
            ),
        }
        outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=accepted,
        )
        observed_subject = {"key": "advanced"}
        observation_b = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_SUBJECT_SUPERSEDED",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "sealed_subject_sha256": outbox.digest(value["subject"]),
            "observed_subject": observed_subject,
            "observed_subject_sha256": outbox.digest(observed_subject),
            "verified": True,
            "productive_effect": False,
        }
        record_b = persist_authority_observation(
            backend, intent, observation_b, run_id=309
        )
        path_b = outbox.authority_observation_path(
            intent["lane"], intent["sequence"], outbox.digest(record_b)
        )
        self.assertNotEqual(path_a, path_b)
        self.assertIsNotNone(backend.read_file(backend.head, path_a))
        self.assertIsNotNone(backend.read_file(backend.head, path_b))

        # Content addressing preserves the prior observation while the
        # terminal decision explicitly selects the later subject fact.
        self.assertIsNotNone(backend.read_file(backend.head, path_a))
        current_terminal = terminal_evidence(
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "reason": observation_b["blocker"],
                "exhaustion": ambiguity_exhaustion(
                    intent, observation_b["blocker"], record_b
                ),
                "productive_effect": False,
            }
        )
        self.assertEqual(
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=current_terminal,
            )["d0"],
            3,
        )

    def test_selected_nonprimary_witness_survives_later_retry_noise(self):
        backend = MemoryBackend()
        first_value = payload(run_id=1000)
        first = outbox.append_intent(
            backend, payload=first_value, artifact=artifact(first_value)
        )
        retry_value = payload(run_id=1001)
        retry = outbox.append_intent(
            backend, payload=retry_value, artifact=artifact(retry_value)
        )
        selected = next(
            item
            for item in retry["witnesses"]
            if item["producer"]["run_id"] == 1001
        )
        outbox.prepare_transport(
            backend,
            lane=retry["lane"],
            sequence=retry["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(
                retry, 1, witness=selected
            ),
            actor_run_id=5001,
            actor_run_attempt=1,
            witness_run_id=1001,
            witness_run_attempt=1,
        )
        updates_after_transport = backend.update_calls
        for number in range(100):
            value = payload(run_id=2000 + number)
            replay = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            self.assertFalse(replay["cas"]["appended"])
        self.assertEqual(backend.update_calls, updates_after_transport)
        current = outbox.read_next(backend, "ruleset-dispatch")
        self.assertEqual(
            current["transport"]["1"]["witness_producer_run_id"], 1001
        )
        self.assertEqual(
            current["transport"]["1"]["witness_path"],
            outbox.witness_path(
                "ruleset-dispatch", first["fingerprint"], 1001, 1
            ),
        )
        index = outbox._read_json(
            backend,
            backend.heads["ruleset-dispatch"],
            outbox.witness_index_path("ruleset-dispatch", first["fingerprint"]),
        )
        self.assertEqual(index["page"], 1)
        self.assertEqual(index["next_ordinal"], 3)
        self.assertEqual(len(index["entries"]), 2)
        meta = outbox.validate_meta(
            outbox._read_json(
                backend,
                backend.heads["ruleset-dispatch"],
                outbox.meta_path("ruleset-dispatch"),
            ),
            "ruleset-dispatch",
        )
        self.assertEqual(meta["next_seq"], 2)

    def test_pretransport_witness_growth_has_explicit_authority_bound(self):
        backend = MemoryBackend()
        for number in range(outbox.MAX_ACTIVE_WITNESSES):
            value = payload(run_id=3000 + number)
            outbox.append_intent(backend, payload=value, artifact=artifact(value))
        overflow = payload(run_id=4000)
        with self.assertRaisesRegex(outbox.OutboxBlock, "WITNESS_BOUND_EXHAUSTED"):
            outbox.append_intent(
                backend, payload=overflow, artifact=artifact(overflow)
            )

    def test_exact_lane_request_abis_are_narrow_and_required(self):
        self.assertEqual(
            outbox.validate_payload(payload("exact-head-dispatch"))["request"][
                "event_type"
            ],
            "qikvrt_autonomous_exact_head_verify",
        )
        exact_review = payload("exact-review-dispatch")
        self.assertEqual(
            outbox.validate_payload(exact_review)["request"]["inputs"][
                "evaluator_sha"
            ],
            "a" * 40,
        )
        del exact_review["request"]["inputs"]["evaluator_sha"]
        with self.assertRaisesRegex(outbox.OutboxBlock, "exact-review"):
            outbox.validate_payload(exact_review)
        self.assertEqual(
            outbox.validate_payload(payload("mesh-review-successor-dispatch"))[
                "request"
            ]["inputs"]["fingerprint"],
            "c" * 64,
        )
        ten_digit = payload("mesh-review-successor-dispatch")
        ten_digit["request"]["inputs"]["pr"] = "9999999999"
        ten_digit = outbox.seal_review_transport_payload(ten_digit)
        self.assertEqual(
            outbox.validate_payload(ten_digit)["request"]["inputs"]["pr"],
            "9999999999",
        )
        eleven_digit = copy.deepcopy(ten_digit)
        eleven_digit["request"]["inputs"]["pr"] = "10000000000"
        with self.assertRaisesRegex(outbox.OutboxBlock, "mesh-review"):
            outbox.validate_payload(eleven_digit)

    def test_reads_preexisting_protected_lane_ref_and_only_exact_fifo_paths(self):
        backend = MemoryBackend()
        first_payload = payload(subject="oldest")
        first = outbox.append_intent(
            backend, payload=first_payload, artifact=artifact(first_payload)
        )
        second_payload = payload(run_id=102, subject="second")
        outbox.append_intent(
            backend, payload=second_payload, artifact=artifact(second_payload)
        )
        for number in range(1300):
            backend.commits[backend.head][f"unrelated/artifact-{number}.json"] = b"{}\n"
        backend.read_paths.clear()
        observed = outbox.read_next(backend, "ruleset-dispatch")
        self.assertEqual(observed["sequence"], first["sequence"])
        self.assertEqual(observed["intent"]["payload"]["subject"]["key"], "oldest")
        self.assertLessEqual(len(backend.read_paths), 28)
        self.assertFalse(any(path.startswith("unrelated/") for path in backend.read_paths))
        manifest = outbox._read_json(backend, backend.head, "ledger.json")
        self.assertFalse(manifest["candidate_or_main_bytes"])
        self.assertFalse(manifest["force_updates"])

    def test_content_addressed_duplicate_is_idempotent(self):
        backend = MemoryBackend()
        value = payload()
        first = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        second = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        self.assertEqual(first["sequence"], second["sequence"])
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertFalse(second["cas"]["appended"])
        self.assertEqual(len(second["witnesses"]), 1)
        meta = outbox.validate_meta(
            outbox._read_json(backend, backend.head, outbox.meta_path("ruleset-dispatch")),
            "ruleset-dispatch",
        )
        self.assertEqual(meta["next_seq"], 2)

    def test_same_work_unit_rerun_and_new_artifact_do_not_enqueue_twice(self):
        backend = MemoryBackend()
        first_payload = payload(run_id=111)
        first = outbox.append_intent(
            backend, payload=first_payload, artifact=artifact(first_payload)
        )
        rerun_payload = copy.deepcopy(first_payload)
        rerun_payload["producer"]["run_id"] = 222
        rerun_payload["producer"]["run_attempt"] = 2
        second = outbox.append_intent(
            backend, payload=rerun_payload, artifact=artifact(rerun_payload)
        )
        self.assertEqual(second["sequence"], first["sequence"])
        self.assertEqual(second["fingerprint"], first["fingerprint"])
        self.assertTrue(second["cas"]["appended"])
        self.assertEqual(len(second["witnesses"]), 2)
        self.assertEqual(second["artifact"], first["artifact"])
        meta = outbox.validate_meta(
            outbox._read_json(backend, backend.head, outbox.meta_path("ruleset-dispatch")),
            "ruleset-dispatch",
        )
        self.assertEqual(meta["next_seq"], 2)

    def test_attempt_two_and_acceptance_require_prior_exact_state(self):
        backend = MemoryBackend()
        value = payload("requested-review-dispatch")
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
            outbox.prepare_transport(
                backend,
                lane="requested-review-dispatch",
                sequence=intent["sequence"],
                attempt=2,
                request={},
                actor_run_id=701,
                actor_run_attempt=1,
                retry_evidence={},
            )
        with self.assertRaisesRegex(outbox.OutboxBlock, "matching pre-effect"):
            outbox.record_acceptance(
                backend,
                lane="requested-review-dispatch",
                sequence=intent["sequence"],
                attempt=1,
                child={
                    "run_id": 702,
                    "run_attempt": 1,
                    "workflow_id": 77,
                    "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
                    "event": "workflow_dispatch",
                    "repository": "Goldkelch/qik-vrt",
                    "head_sha": "a" * 40,
                    "status": "queued",
                    "conclusion": None,
                    "display_title": "exact child",
                },
            )

    def test_direct_transport_acceptance_rejects_rerun_attempts_in_new_run_lanes(self):
        new_run_lanes = (
            "ruleset-dispatch",
            "requested-review-dispatch",
            "exact-head-dispatch",
            "exact-review-dispatch",
            "mesh-review-successor-dispatch",
        )
        for ordinal, lane in enumerate(new_run_lanes, start=1):
            with self.subTest(lane=lane):
                backend = MemoryBackend()
                value = payload(lane, run_id=6800 + ordinal)
                intent = outbox.append_intent(
                    backend, payload=value, artifact=artifact(value)
                )
                outbox.prepare_transport(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    actor_run_id=6810 + ordinal,
                    actor_run_attempt=1,
                )
                if lane in outbox.REVIEW_TRANSPORT_LANES:
                    title = (
                        "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h="
                        + "b" * 40 + " f=" + "c" * 64 + " i="
                        + intent["fingerprint"] + " a=1"
                    )
                    workflow_id = 77
                    workflow_path = (
                        ".github/workflows/qikvrt_requested_review_executor.yml"
                    )
                    event = "workflow_dispatch"
                elif lane == "exact-head-dispatch":
                    title = (
                        "qikvrt-exact intent=" + intent["fingerprint"]
                        + f" seq={intent['sequence']} transport-attempt=1"
                    )
                    workflow_id = 66
                    workflow_path = (
                        ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"
                    )
                    event = "repository_dispatch"
                else:
                    title = (
                        "qikvrt-ruleset intent=" + intent["fingerprint"]
                        + f" seq={intent['sequence']} transport-attempt=1"
                    )
                    workflow_id = 88
                    workflow_path = (
                        ".github/workflows/qikvrt_ruleset_reconcile.yml"
                    )
                    event = "repository_dispatch"
                child = {
                    "run_id": 6820 + ordinal,
                    "run_attempt": 2,
                    "workflow_id": workflow_id,
                    "workflow_path": workflow_path,
                    "event": event,
                    "repository": "Goldkelch/qik-vrt",
                    "head_sha": "a" * 40,
                    "status": "queued",
                    "conclusion": None,
                    "display_title": title,
                }
                with self.assertRaisesRegex(
                    outbox.OutboxBlock, "direct transport child.*attempt one"
                ):
                    outbox.record_acceptance(
                        backend,
                        lane=lane,
                        sequence=intent["sequence"],
                        attempt=1,
                        child=child,
                    )
                self.assertEqual(
                    outbox.read_next(backend, lane)["acceptance"], {}
                )

    def test_terminal_acceptance_conclusion_is_immutable_but_queued_can_complete(self):
        for ordinal, (accepted_status, accepted_conclusion, observed_conclusion, allowed) in enumerate(
            (
                ("completed", "failure", "success", False),
                ("completed", "success", "failure", False),
                ("queued", None, "success", True),
            ),
            start=1,
        ):
            with self.subTest(
                accepted=accepted_conclusion,
                observed=observed_conclusion,
            ):
                backend = MemoryBackend()
                value = payload(
                    "requested-review-dispatch", run_id=6830 + ordinal
                )
                intent = outbox.append_intent(
                    backend, payload=value, artifact=artifact(value)
                )
                outbox.prepare_transport(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    actor_run_id=6840 + ordinal,
                    actor_run_attempt=1,
                )
                child = {
                    "run_id": 6850 + ordinal,
                    "run_attempt": 1,
                    "workflow_id": 77,
                    "workflow_path": (
                        ".github/workflows/qikvrt_requested_review_executor.yml"
                    ),
                    "event": "workflow_dispatch",
                    "repository": "Goldkelch/qik-vrt",
                    "head_sha": "a" * 40,
                    "status": accepted_status,
                    "conclusion": accepted_conclusion,
                    "display_title": (
                        "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h="
                        + "b" * 40 + " f=" + "c" * 64 + " i="
                        + intent["fingerprint"] + " a=1"
                    ),
                }
                outbox.record_acceptance(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    attempt=1,
                    child=child,
                )
                observed = {
                    **child,
                    "status": "completed",
                    "conclusion": observed_conclusion,
                }
                result_artifact = {
                    "id": 6860 + ordinal,
                    "name": f"completion-{ordinal}",
                    "archive_sha256": "f" * 64,
                    "payload_sha256": "d" * 64,
                    "producer_run_id": observed["run_id"],
                    "producer_run_attempt": 1,
                    "verified": True,
                }
                invoke = lambda: outbox.record_completion(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    attempt=1,
                    child=observed,
                    evidence=completion_evidence(observed, result_artifact),
                )
                if allowed:
                    self.assertEqual(invoke()["child"]["conclusion"], "success")
                else:
                    with self.assertRaisesRegex(
                        outbox.OutboxBlock, "exact accepted child result"
                    ):
                        invoke()
                    self.assertEqual(
                        outbox.read_next(backend, intent["lane"])["completion"],
                        {},
                    )
    def test_delayed_attempt_one_child_blocks_stale_zero_scan_and_never_reposts(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=6901,
            actor_run_attempt=1,
        )
        transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        cursor_receipt = persist_retry_cursor_result(
            backend, intent, transport, attempt=1, successor_count=0
        )
        blocker = "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED"
        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": blocker,
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            **exact_cursor_observation_fields(intent, cursor_receipt),
            "transport_request_sha256": transport["request_sha256"],
            "verified": True,
            "productive_effect": False,
        }
        record = persist_authority_observation(
            backend, intent, observation, run_id=6902
        )
        request = intent["payload"]["request"]
        inputs = request["inputs"]
        delayed_child = {
            "run_id": 6903,
            "run_attempt": 1,
            "workflow_id": intent["payload"]["target"]["workflow_id"],
            "workflow_path": intent["payload"]["target"]["workflow_path"],
            "event": "workflow_dispatch",
            "repository": intent["repository"],
            "head_sha": inputs["evaluator_sha"],
            "status": "queued",
            "conclusion": None,
            "display_title": (
                f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
                f"h={inputs['head']} f={inputs['fingerprint']} "
                f"i={intent['fingerprint']} a=1"
            ),
        }
        outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=delayed_child,
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "unacknowledged"):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=terminal_evidence(
                    {
                        "d0": 3,
                        "state": "REQUEST_AUTHORITY",
                        "reason": blocker,
                        "exhaustion": ambiguity_exhaustion(
                            intent, blocker, record
                        ),
                        "productive_effect": False,
                    }
                ),
            )
        with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=2,
                request={},
                actor_run_id=6904,
                actor_run_attempt=1,
                retry_evidence={},
            )
        pending = outbox.read_next(backend, intent["lane"])
        self.assertEqual(set(pending["transport"]), {"1"})
        self.assertEqual(set(pending["acceptance"]), {"1"})

    def test_terminal_cannot_advance_without_business_or_exhaustion_proof(self):
        backend = MemoryBackend()
        value = payload("ruleset-dispatch")
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        with self.assertRaisesRegex(outbox.OutboxBlock, "exact transport"):
            outbox.terminalize(
                backend,
                lane="ruleset-dispatch",
                sequence=intent["sequence"],
                evidence=terminal_evidence(
                    {"d0": 2, "state": "CONTINUE", "productive_effect": False}
                ),
            )
        outbox.prepare_transport(
            backend,
            lane="ruleset-dispatch",
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=703,
            actor_run_attempt=1,
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "business receipt binding"):
            outbox.terminalize(
                backend,
                lane="ruleset-dispatch",
                sequence=intent["sequence"],
                evidence=terminal_evidence({
                    "d0": 2,
                    "state": "CONTINUE",
                    "business_receipt": {
                        "schema": outbox.BUSINESS_RECEIPT_SCHEMA,
                        "lane": "ruleset-dispatch",
                        "sequence": intent["sequence"],
                        "fingerprint": intent["fingerprint"],
                        "outcome": "RULESET_CURRENT_RECEIPT",
                        "attempt": 1,
                        "run_id": 999,
                        "run_attempt": 1,
                        "workflow_id": 88,
                        "workflow_path": ".github/workflows/qikvrt_ruleset_reconcile.yml",
                        "head_sha": "a" * 40,
                        "child_sha256": "f" * 64,
                        "child_recovery": False,
                        "same_run_result": False,
                        "artifact": {},
                        "evidence_sha256": "e" * 64,
                        "verified": True,
                        "productive_effect": False,
                    },
                    "productive_effect": False,
                }),
            )
        with self.assertRaisesRegex(
            outbox.OutboxBlock,
            "authorized technical code|exhausted-attempt list|adverse exhaustion",
        ):
            outbox.terminalize(
                backend,
                lane="ruleset-dispatch",
                sequence=intent["sequence"],
                evidence=terminal_evidence({
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "exhaustion": {
                        "schema": outbox.EXHAUSTION_SCHEMA,
                        "lane": "ruleset-dispatch",
                        "sequence": intent["sequence"],
                        "fingerprint": intent["fingerprint"],
                        "mode": "CHILD_RESULT_ADVERSE",
                        "attempts": [1, 2],
                        "transport_attempt": 2,
                        "successor": {},
                        "successor_sha256": "f" * 64,
                        "completion_evidence_sha256": "e" * 64,
                        "first_blocker": "attempt two absent",
                        "verified": True,
                        "productive_effect": False,
                    },
                    "productive_effect": False,
                }),
            )
    def test_queued_child_and_unobserved_one_shot_rerun_cannot_claim_success(self):
        backend = MemoryBackend()
        value = payload("reconciler-rerun")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=704,
            actor_run_attempt=1,
        )
        queued = {
            **value["request"]["original_child"],
            "run_attempt": 2,
            "status": "queued",
            "conclusion": None,
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=queued,
        )
        business_artifact = {
            "id": 905,
            "name": "qikvrt-main-ruleset-receipt-91-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 91,
            "producer_run_attempt": 2,
            "verified": True,
        }
        with self.assertRaisesRegex(
            outbox.OutboxBlock, "authorized technical code|adverse exhaustion"
        ):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=terminal_evidence({
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "exhaustion": {
                        "schema": outbox.EXHAUSTION_SCHEMA,
                        "lane": intent["lane"],
                        "sequence": intent["sequence"],
                        "fingerprint": intent["fingerprint"],
                        "mode": "CHILD_RESULT_ADVERSE",
                        "attempts": [1],
                        "transport_attempt": 1,
                        "successor": queued,
                        "successor_sha256": acceptance["child_sha256"],
                        "completion_evidence_sha256": "e" * 64,
                        "first_blocker": "QUEUED_IS_NOT_AN_ADVERSE_RESULT",
                        "verified": True,
                        "productive_effect": False,
                    },
                    "productive_effect": False,
                }),
            )
        with self.assertRaisesRegex(outbox.OutboxBlock, "business receipt"):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=terminal_evidence({
                    "d0": 2,
                    "state": "CONTINUE",
                    "business_receipt": {
                        "schema": outbox.BUSINESS_RECEIPT_SCHEMA,
                        "lane": intent["lane"],
                        "sequence": intent["sequence"],
                        "fingerprint": intent["fingerprint"],
                        "outcome": "RECONCILER_CURRENT_RECEIPT",
                        "attempt": 1,
                        "run_id": 91,
                        "run_attempt": 2,
                        "workflow_id": 88,
                        "workflow_path": ".github/workflows/qikvrt_ruleset_reconcile.yml",
                        "head_sha": "a" * 40,
                        "child_sha256": acceptance["child_sha256"],
                        "child_recovery": False,
                        "same_run_result": False,
                        "artifact": business_artifact,
                        "evidence_sha256": outbox.digest(business_artifact),
                        "verified": True,
                        "productive_effect": False,
                    },
                    "productive_effect": False,
                }),
            )

    def test_one_shot_reconciler_adverse_requires_exact_completed_result(self):
        backend = MemoryBackend()
        value = payload("reconciler-rerun")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=710,
            actor_run_attempt=1,
        )
        adverse = {
            **value["request"]["original_child"],
            "run_attempt": 2,
            "status": "queued",
            "conclusion": None,
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=adverse,
        )
        missing_completion = terminal_evidence(
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "exhaustion": {
                    "schema": outbox.EXHAUSTION_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "mode": "CHILD_RESULT_ADVERSE",
                    "attempts": [1],
                    "transport_attempt": 1,
                    "successor": adverse,
                    "successor_sha256": outbox.digest(adverse),
                    "completion_evidence_sha256": "e" * 64,
                    "first_blocker": "RECONCILER_ATTEMPT_2_CANCELLED",
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "adverse exhaustion"):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=missing_completion,
            )
        result_artifact = {
            "id": 1710,
            "name": "qikvrt-main-ruleset-receipt-91-2",
            "archive_sha256": "c" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 91,
            "producer_run_attempt": 2,
            "verified": True,
        }
        completed_adverse = {
            **adverse,
            "status": "completed",
            "conclusion": "cancelled",
        }
        completion = outbox.record_completion(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=completed_adverse,
            evidence=completion_evidence(completed_adverse, result_artifact),
        )
        exact = copy.deepcopy(missing_completion)
        exact["exhaustion"]["successor"] = completed_adverse
        exact["exhaustion"]["successor_sha256"] = completion["child_sha256"]
        exact["exhaustion"]["completion_evidence_sha256"] = completion[
            "evidence_sha256"
        ]
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=exact,
        )
        self.assertEqual(terminal["d0"], 3)
        self.assertEqual(outbox.read_next(backend, intent["lane"])["state"], "EMPTY")

    def test_queued_locator_can_complete_then_terminalize_each_lane_class(self):
        cases = (
            (
                "ruleset-dispatch",
                88,
                ".github/workflows/qikvrt_ruleset_reconcile.yml",
                "repository_dispatch",
                "RULESET_CURRENT_RECEIPT",
            ),
            (
                "exact-head-dispatch",
                66,
                ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
                "repository_dispatch",
                "EXACT_HEAD_TERMINAL_CONTINUATION",
            ),
            (
                "requested-review-dispatch",
                77,
                ".github/workflows/qikvrt_requested_review_executor.yml",
                "workflow_dispatch",
                "REQUESTED_REVIEW_LEDGER_CONTINUATION",
            ),
        )
        for lane, workflow_id, workflow_path, event, outcome in cases:
            with self.subTest(lane=lane):
                backend = (
                    CallbackRaceBackend()
                    if lane == "ruleset-dispatch"
                    else MemoryBackend()
                )
                value = payload(lane)
                intent = outbox.append_intent(
                    backend, payload=value, artifact=artifact(value)
                )
                outbox.prepare_transport(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    actor_run_id=720,
                    actor_run_attempt=1,
                )
                if lane in outbox.REVIEW_TRANSPORT_LANES:
                    title = (
                        "qikvrt-rr-v3 e=" + "a" * 40
                        + " p=935 h=" + "b" * 40 + " f=" + "c" * 64
                        + " i=" + intent["fingerprint"] + " a=1"
                    )
                else:
                    title = (
                        f"qikvrt-child intent={intent['fingerprint']} "
                        f"seq={intent['sequence']} transport-attempt=1"
                    )
                queued = {
                    "run_id": 721,
                    "run_attempt": 1,
                    "workflow_id": workflow_id,
                    "workflow_path": workflow_path,
                    "event": event,
                    "repository": "Goldkelch/qik-vrt",
                    "head_sha": "a" * 40,
                    "status": "queued",
                    "conclusion": None,
                    "display_title": title,
                }
                acceptance = outbox.record_acceptance(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    child=queued,
                )
                completed = {
                    **queued,
                    "status": "completed",
                    "conclusion": "success",
                }
                artifact_name = (
                    "qikvrt-main-ruleset-receipt-721-1"
                    if lane == "ruleset-dispatch"
                    else f"qikvrt-{lane}-business-721-1"
                )
                result_artifact = {
                    "id": 722,
                    "name": artifact_name,
                    "archive_sha256": "f" * 64,
                    "payload_sha256": "d" * 64,
                    "producer_run_id": 721,
                    "producer_run_attempt": 1,
                    "verified": True,
                }
                completion = outbox.record_completion(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    child=completed,
                    evidence=completion_evidence(completed, result_artifact),
                )
                terminal_value = terminal_evidence({
                        "d0": 2,
                        "state": "CONTINUE",
                        "business_receipt": {
                            "schema": outbox.BUSINESS_RECEIPT_SCHEMA,
                            "lane": lane,
                            "sequence": intent["sequence"],
                            "fingerprint": intent["fingerprint"],
                            "outcome": outcome,
                            "attempt": 1,
                            "run_id": 721,
                            "run_attempt": 1,
                            "workflow_id": workflow_id,
                            "workflow_path": workflow_path,
                            "head_sha": "a" * 40,
                            "locator_child_sha256": acceptance["child_sha256"],
                            "child_sha256": completion["child_sha256"],
                            "child_recovery": False,
                            "same_run_result": False,
                            "artifact": result_artifact,
                            "completion_evidence_sha256": completion[
                                "evidence_sha256"
                            ],
                            "evidence_sha256": outbox.digest(result_artifact),
                            "verified": True,
                            "productive_effect": False,
                        },
                        "productive_effect": False,
                    })
                if lane == "ruleset-dispatch":
                    backend.main_head = "e" * 40
                    with self.assertRaisesRegex(
                        outbox.OutboxBlock, "EVALUATOR_SUPERSEDED"
                    ):
                        outbox.terminalize(
                            backend,
                            lane=lane,
                            sequence=intent["sequence"],
                            evidence=terminal_value,
                        )
                    backend.main_head = "a" * 40
                    def drift_main_during_terminal(_backend, _lane):
                        _backend.main_head = "e" * 40
                        return {
                            "unrelated/terminal-race.json": outbox.canonical_bytes(
                                {"race": True}
                            )
                        }

                    backend.race_callback = drift_main_during_terminal
                    backend.raced = False
                    with self.assertRaisesRegex(
                        outbox.OutboxBlock, "EVALUATOR_SUPERSEDED"
                    ):
                        outbox.terminalize(
                            backend,
                            lane=lane,
                            sequence=intent["sequence"],
                            evidence=terminal_value,
                        )
                    backend.race_callback = None
                    backend.main_head = "a" * 40
                terminal = outbox.terminalize(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    evidence=terminal_value,
                )
                self.assertEqual(terminal["d0"], 2)
    def test_ff_cas_replans_without_losing_parallel_ref_append(self):
        backend = OneRaceBackend()
        outbox.ensure_initialized(backend, "ruleset-dispatch")
        backend.race_enabled = True
        value = payload()
        result = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        self.assertTrue(backend.raced)
        self.assertEqual(result["cas"]["attempts"], 2)
        self.assertIn("unrelated/rival.json", backend.commits[backend.head])
        self.assertFalse(result["cas"]["force"])

    def test_state_dependent_mutations_revalidate_every_cas_parent(self):
        def seeded():
            backend = CallbackRaceBackend()
            value = payload("requested-review-dispatch")
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=9001,
                actor_run_attempt=1,
            )

            def child(run_id, attempt):
                return {
                    "run_id": run_id,
                    "run_attempt": 1,
                    "workflow_id": 77,
                    "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
                    "event": "workflow_dispatch",
                    "repository": "Goldkelch/qik-vrt",
                    "head_sha": "a" * 40,
                    "status": "queued",
                    "conclusion": None,
                    "display_title": (
                        "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h=" + "b" * 40
                        + " f=" + "c" * 64 + " i=" + intent["fingerprint"]
                        + f" a={attempt}"
                    ),
                }

            return backend, intent, child, None

        # New-run transports are one-shot before any state-dependent CAS work.
        backend, intent, child, _retry = seeded()
        with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=2,
                request={},
                actor_run_id=9002,
                actor_run_attempt=1,
                retry_evidence={},
            )
        self.assertEqual(
            set(outbox.read_next(backend, intent["lane"])["transport"]), {"1"}
        )

        # A child-rerun pre-effect record is equally state dependent.  If an
        # exact original completion wins the first ref update, the CAS retry
        # must not authorize a redundant same-run attempt two.
        backend, intent, child, _retry = seeded()
        original = child(9010, 1)
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=original,
        )
        completed = {
            **original,
            "status": "completed",
            "conclusion": "cancelled",
        }
        child_retry = child_retry_evidence(
            intent, acceptance, observed_child=completed
        )
        completed_artifact = {
            "id": 9011,
            "name": "qikvrt-requested-review-dispatch-business-9010-1",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 9010,
            "producer_run_attempt": 1,
            "verified": True,
        }

        def complete_original(racing_backend, _lane):
            outbox.record_completion(
                racing_backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                child=completed,
                evidence=completion_evidence(completed, completed_artifact),
            )
            return None

        backend.race_callback = complete_original
        backend.raced = False
        with self.assertRaisesRegex(
            outbox.OutboxBlock, "exact result already exists during CAS"
        ):
            outbox.prepare_child_rerun(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                transport_attempt=1,
                retry_evidence=child_retry,
                actor_run_id=9012,
                actor_run_attempt=1,
            )
        current = outbox.read_next(backend, intent["lane"])
        self.assertEqual(
            current["acceptance"]["1"]["child_sha256"],
            acceptance["child_sha256"],
        )
        self.assertIn("1", current["completion"])
        self.assertEqual(current["child_recovery"], {})

        # A stored absence/ambiguity observation is also chosen against every
        # CAS parent.  A bound child that appears during the write invalidates
        # the observation instead of leaving an authoritative stale absence.
        backend, intent, child, _retry = seeded()
        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "REPEATED_REQUESTED_REVIEW_TRANSPORT_UNACKNOWLEDGED",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "transport_attempt": 1,
            "transport_request_sha256": outbox.read_next(
                backend, intent["lane"]
            )["transport"]["1"]["request_sha256"],
            "scan_complete": True,
            "bound_successor_count": 0,
            "verified": True,
            "productive_effect": False,
        }

        def accept_during_observation(racing_backend, _lane):
            outbox.record_acceptance(
                racing_backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                child=child(9020, 1),
            )
            return None

        backend.race_callback = accept_during_observation
        backend.raced = False
        with self.assertRaisesRegex(
            outbox.OutboxBlock, "unacknowledged transport observation"
        ):
            persist_authority_observation(
                backend, intent, observation, run_id=9021
            )
        current = outbox.read_next(backend, intent["lane"])
        self.assertIn("1", current["acceptance"])
        self.assertIsNone(current["authority_observation"])

    def test_crash_windows_are_durable_and_one_shot_orphan_holds(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )

        # Cancel before POST leaves the exact FIFO intent and sealed request.
        pending = outbox.read_next(backend, intent["lane"])
        self.assertEqual(pending["transport"], {})
        self.assertEqual(pending["intent"]["payload"]["request"], value["request"])

        prepared = outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=201,
            actor_run_attempt=1,
        )
        self.assertTrue(prepared["cas"]["appended"])
        replay = outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=201,
            actor_run_attempt=1,
        )
        self.assertFalse(replay["cas"]["appended"])

        transport = outbox.read_next(backend, intent["lane"])["transport"]["1"]
        cursor_receipt = persist_retry_cursor_result(
            backend, intent, transport, attempt=1, successor_count=0
        )
        blocker = "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED"
        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": blocker,
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            **exact_cursor_observation_fields(intent, cursor_receipt),
            "transport_request_sha256": transport["request_sha256"],
            "verified": True,
            "productive_effect": False,
        }
        record = persist_authority_observation(
            backend, intent, observation, run_id=202
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=2,
                request={},
                actor_run_id=203,
                actor_run_attempt=1,
                retry_evidence={},
            )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": blocker,
                    "exhaustion": ambiguity_exhaustion(
                        intent, blocker, record
                    ),
                    "productive_effect": False,
                }
            ),
        )
        self.assertEqual(terminal["d0"], 3)
        self.assertEqual(outbox.read_next(backend, intent["lane"])["state"], "EMPTY")

    def test_accepted_attempt_one_is_business_result_not_new_child_permission(self):
        cases = {
            "ruleset-dispatch": (88, ".github/workflows/qikvrt_ruleset_reconcile.yml", "repository_dispatch"),
            "requested-review-dispatch": (77, ".github/workflows/qikvrt_requested_review_executor.yml", "workflow_dispatch"),
            "exact-head-dispatch": (66, ".github/workflows/qikvrt_autonomous_exact_head_verify.yml", "repository_dispatch"),
            "exact-review-dispatch": (77, ".github/workflows/qikvrt_requested_review_executor.yml", "workflow_dispatch"),
            "mesh-review-successor-dispatch": (77, ".github/workflows/qikvrt_requested_review_executor.yml", "workflow_dispatch"),
        }
        for lane, (workflow_id, workflow_path, event) in cases.items():
            with self.subTest(lane=lane):
                backend = MemoryBackend()
                value = payload(lane)
                intent = outbox.append_intent(
                    backend, payload=value, artifact=artifact(value)
                )
                outbox.prepare_transport(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    actor_run_id=1801,
                    actor_run_attempt=1,
                )
                if lane in outbox.REVIEW_TRANSPORT_LANES:
                    title = (
                        "qikvrt-rr-v3 e=" + "a" * 40
                        + " p=935 h=" + "b" * 40 + " f=" + "c" * 64
                        + " i=" + intent["fingerprint"] + " a=1"
                    )
                else:
                    title = (
                        f"qikvrt-child intent={intent['fingerprint']} "
                        f"seq={intent['sequence']} transport-attempt=1"
                    )
                child = {
                    "run_id": 1802,
                    "run_attempt": 1,
                    "workflow_id": workflow_id,
                    "workflow_path": workflow_path,
                    "event": event,
                    "repository": "Goldkelch/qik-vrt",
                    "head_sha": "a" * 40,
                    "status": "completed",
                    "conclusion": "failure",
                    "display_title": title,
                }
                outbox.record_acceptance(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    child=child,
                )
                result_artifact = {
                    "id": 2802,
                    "name": f"qikvrt-{lane}-adverse-1802-1",
                    "archive_sha256": "a" * 64,
                    "payload_sha256": "b" * 64,
                    "producer_run_id": 1802,
                    "producer_run_attempt": 1,
                    "verified": True,
                }
                completion = outbox.record_completion(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    child=child,
                    evidence=completion_evidence(child, result_artifact),
                )
                with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
                    outbox.prepare_transport(
                        backend,
                        lane=lane,
                        sequence=intent["sequence"],
                        attempt=2,
                        request={},
                        actor_run_id=1803,
                        actor_run_attempt=1,
                        retry_evidence={},
                    )
                terminal = outbox.terminalize(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    evidence=terminal_evidence({
                        "d0": 3,
                        "state": "REQUEST_AUTHORITY",
                        "exhaustion": {
                            "schema": outbox.EXHAUSTION_SCHEMA,
                            "lane": lane,
                            "sequence": intent["sequence"],
                            "fingerprint": intent["fingerprint"],
                            "mode": "CHILD_RESULT_ADVERSE",
                            "attempts": [1],
                            "transport_attempt": 1,
                            "successor": child,
                            "successor_sha256": completion["child_sha256"],
                            "completion_evidence_sha256": completion[
                                "evidence_sha256"
                            ],
                            "first_blocker": "ATTEMPT_1_ACCEPTED_ADVERSE",
                            "verified": True,
                            "productive_effect": False,
                        },
                        "productive_effect": False,
                    }),
                )
                self.assertEqual(terminal["d0"], 3)

    def test_terminal_cursor_advances_fifo_one_item_at_a_time(self):
        backend = MemoryBackend()
        first_value = payload("reconciler-rerun", run_id=401, subject="first")
        second_value = payload("reconciler-rerun", run_id=402, subject="second")
        first = outbox.append_intent(
            backend, payload=first_value, artifact=artifact(first_value)
        )
        second = outbox.append_intent(
            backend, payload=second_value, artifact=artifact(second_value)
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "current FIFO"):
            outbox.terminalize(
                backend,
                lane="reconciler-rerun",
                sequence=second["sequence"],
                evidence=terminal_evidence(
                    {
                        "d0": 3,
                        "state": "REQUEST_AUTHORITY",
                        "productive_effect": False,
                    }
                ),
            )
        outbox.prepare_transport(
            backend,
            lane="reconciler-rerun",
            sequence=first["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(first, 1),
            actor_run_id=410,
            actor_run_attempt=1,
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "one-shot"):
            outbox.prepare_transport(
                backend,
                lane="reconciler-rerun",
                sequence=first["sequence"],
                attempt=2,
                request=first["payload"]["request"],
                actor_run_id=411,
                actor_run_attempt=1,
                retry_evidence={},
            )
        accepted_child = {
            "run_id": 91,
            "run_attempt": 2,
            "workflow_id": 88,
            "workflow_path": ".github/workflows/qikvrt_ruleset_reconcile.yml",
            "event": "repository_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "success",
            "display_title": first_value["request"]["original_child"][
                "display_title"
            ],
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane="reconciler-rerun",
            sequence=first["sequence"],
            attempt=1,
            child=accepted_child,
        )
        business_artifact = {
            "id": 901,
            "name": "qikvrt-main-ruleset-receipt-91-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 91,
            "producer_run_attempt": 2,
            "verified": True,
        }
        completion = outbox.record_completion(
            backend,
            lane="reconciler-rerun",
            sequence=first["sequence"],
            attempt=1,
            child=accepted_child,
            evidence=completion_evidence(
                accepted_child, business_artifact, job_name="reconcile"
            ),
        )
        outbox.terminalize(
            backend,
            lane="reconciler-rerun",
            sequence=first["sequence"],
            evidence=terminal_evidence({
                "d0": 2,
                "state": "CURRENT",
                "business_receipt": {
                    "schema": outbox.BUSINESS_RECEIPT_SCHEMA,
                    "lane": "reconciler-rerun",
                    "sequence": first["sequence"],
                    "fingerprint": first["fingerprint"],
                    "outcome": "RECONCILER_CURRENT_RECEIPT",
                    "attempt": 1,
                    "run_id": 91,
                    "run_attempt": 2,
                    "workflow_id": 88,
                    "workflow_path": ".github/workflows/qikvrt_ruleset_reconcile.yml",
                    "head_sha": "a" * 40,
                    "locator_child_sha256": acceptance["child_sha256"],
                    "child_sha256": completion["child_sha256"],
                    "child_recovery": False,
                    "same_run_result": False,
                    "artifact": business_artifact,
                    "completion_evidence_sha256": completion["evidence_sha256"],
                    "evidence_sha256": outbox.digest(business_artifact),
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }),
        )
        historical = outbox.lookup(
            backend,
            lane="reconciler-rerun",
            sequence=first["sequence"],
            fingerprint=first["fingerprint"],
        )
        self.assertEqual(historical["lookup_state"], "TERMINAL")
        self.assertEqual(historical["terminal"]["d0"], 2)
        with self.assertRaisesRegex(outbox.OutboxBlock, "fingerprint mismatch"):
            outbox.lookup(
                backend,
                lane="reconciler-rerun",
                sequence=first["sequence"],
                fingerprint="0" * 64,
            )
        self.assertEqual(
            outbox.read_next(backend, "reconciler-rerun")["sequence"],
            second["sequence"],
        )
        updates_before_duplicate = backend.update_calls
        terminal_retry = copy.deepcopy(first_value)
        terminal_retry["producer"]["run_id"] = 999
        replay = outbox.append_intent(
            backend,
            payload=terminal_retry,
            artifact=artifact(terminal_retry),
        )
        self.assertEqual(replay["sequence"], first["sequence"])
        self.assertFalse(replay["cas"]["appended"])
        self.assertEqual(backend.update_calls, updates_before_duplicate)

    def test_same_run_child_rerun_is_pre_effect_and_terminally_bound(self):
        backend = MemoryBackend()
        value = payload("mesh-review-successor-dispatch")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=801,
            actor_run_attempt=1,
        )
        title = (
            "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h=" + "b" * 40
            + " f=" + "c" * 64 + " i=" + intent["fingerprint"] + " a=1"
        )
        original = {
            "run_id": 802,
            "run_attempt": 1,
            "workflow_id": 77,
            "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": title,
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=original,
        )
        observed_original = {
            **original,
            "status": "completed",
            "conclusion": "cancelled",
        }
        child_retry = child_retry_evidence(
            intent, acceptance, observed_child=observed_original
        )
        rerun = outbox.prepare_child_rerun(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            transport_attempt=1,
            retry_evidence=child_retry,
            actor_run_id=803,
            actor_run_attempt=1,
        )
        self.assertEqual(
            rerun["endpoint"],
            "repos/Goldkelch/qik-vrt/actions/runs/802/rerun",
        )
        recovered = {
            **original,
            "run_attempt": 2,
            "status": "completed",
            "conclusion": "success",
        }
        recovery_acceptance = outbox.record_child_rerun_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            transport_attempt=1,
            child=recovered,
        )
        business_artifact = {
            "id": 902,
            "name": "qikvrt-requested-review-ledger-802-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 802,
            "producer_run_attempt": 2,
            "verified": True,
        }
        recovery_completion = outbox.record_completion(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=recovered,
            evidence=completion_evidence(
                recovered, business_artifact, job_name="ledger-write"
            ),
            child_recovery=True,
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence({
                "d0": 2,
                "state": "CONTINUE",
                "business_receipt": {
                    "schema": outbox.BUSINESS_RECEIPT_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "outcome": "MESH_REVIEW_LEDGER_CONTINUATION",
                    "attempt": 1,
                    "run_id": 802,
                    "run_attempt": 2,
                    "workflow_id": 77,
                    "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
                    "head_sha": "a" * 40,
                    "locator_child_sha256": recovery_acceptance["child_sha256"],
                    "child_sha256": recovery_completion["child_sha256"],
                    "child_recovery": True,
                    "same_run_result": False,
                    "artifact": business_artifact,
                    "completion_evidence_sha256": recovery_completion[
                        "evidence_sha256"
                    ],
                    "evidence_sha256": outbox.digest(business_artifact),
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }),
        )
        self.assertEqual(terminal["d0"], 2)

    def test_exact_same_run_result_handles_pending_and_dominates_drained_terminal(self):
        def seeded(*, queued: bool):
            backend = MemoryBackend()
            value = payload("exact-head-dispatch")
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            outbox.prepare_transport(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=821,
                actor_run_attempt=1,
            )
            locator = {
                "run_id": 822,
                "run_attempt": 1,
                "workflow_id": 66,
                "workflow_path": ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
                "event": "repository_dispatch",
                "repository": "Goldkelch/qik-vrt",
                "head_sha": "a" * 40,
                "status": "queued" if queued else "completed",
                "conclusion": None if queued else "success",
                "display_title": (
                    f"qikvrt-exact intent={intent['fingerprint']} "
                    f"seq={intent['sequence']} transport-attempt=1"
                ),
            }
            acceptance = outbox.record_acceptance(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                attempt=1,
                child=locator,
            )
            return backend, intent, locator, acceptance

        # A cancel before the normal attempt-one result can still be bound to
        # the same run's exact attempt two and terminalized without reopening.
        backend, intent, locator, acceptance = seeded(queued=True)
        attempt_two = {
            **locator,
            "run_attempt": 2,
            "status": "completed",
            "conclusion": "success",
        }
        artifact_two = {
            "id": 823,
            "name": "qikvrt-exact-head-business-822-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 822,
            "producer_run_attempt": 2,
            "verified": True,
        }
        same_run = outbox.record_same_run_result(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            fingerprint=intent["fingerprint"],
            transport_attempt=1,
            child=attempt_two,
            evidence=completion_evidence(attempt_two, artifact_two),
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence({
                "d0": 2,
                "state": "REOBSERVE",
                "business_receipt": {
                    "schema": outbox.BUSINESS_RECEIPT_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "outcome": "EXACT_HEAD_TERMINAL_CONTINUATION",
                    "attempt": 1,
                    "run_id": 822,
                    "run_attempt": 2,
                    "workflow_id": 66,
                    "workflow_path": ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
                    "head_sha": "a" * 40,
                    "locator_child_sha256": acceptance["child_sha256"],
                    "child_sha256": same_run["child_sha256"],
                    "child_recovery": False,
                    "same_run_result": True,
                    "artifact": artifact_two,
                    "completion_evidence_sha256": same_run["evidence_sha256"],
                    "evidence_sha256": outbox.digest(artifact_two),
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }),
        )
        self.assertEqual(terminal["d0"], 2)

        # A later exact attempt-two adverse result does not rewrite/reopen the
        # earlier terminal, but atomically appends an effective D0=3
        # supersession so the stale D0=2 can never mask the latest attempt.
        backend, intent, locator, acceptance = seeded(queued=False)
        artifact_one = {
            "id": 824,
            "name": "qikvrt-exact-head-business-822-1",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 822,
            "producer_run_attempt": 1,
            "verified": True,
        }
        completion = outbox.record_completion(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=locator,
            evidence=completion_evidence(locator, artifact_one),
        )
        outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence({
                "d0": 2,
                "state": "REOBSERVE",
                "business_receipt": {
                    "schema": outbox.BUSINESS_RECEIPT_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "outcome": "EXACT_HEAD_TERMINAL_CONTINUATION",
                    "attempt": 1,
                    "run_id": 822,
                    "run_attempt": 1,
                    "workflow_id": 66,
                    "workflow_path": ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
                    "head_sha": "a" * 40,
                    "locator_child_sha256": acceptance["child_sha256"],
                    "child_sha256": completion["child_sha256"],
                    "child_recovery": False,
                    "same_run_result": False,
                    "artifact": artifact_one,
                    "completion_evidence_sha256": completion["evidence_sha256"],
                    "evidence_sha256": outbox.digest(artifact_one),
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }),
        )
        adverse = {**locator, "run_attempt": 2, "conclusion": "failure"}
        artifact_adverse = {
            "id": 825,
            "name": "qikvrt-exact-head-adverse-822-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 822,
            "producer_run_attempt": 2,
            "verified": True,
        }
        observed = outbox.record_same_run_result(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            fingerprint=intent["fingerprint"],
            transport_attempt=1,
            child=adverse,
            evidence=completion_evidence(adverse, artifact_adverse),
        )
        historical = outbox.lookup(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            fingerprint=intent["fingerprint"],
        )
        self.assertEqual(historical["terminal"]["d0"], 2)
        self.assertEqual(historical["same_run_result"]["1"]["d0"], 3)
        self.assertEqual(historical["terminal_supersession"]["d0"], 3)
        self.assertEqual(historical["effective_d0"], 3)
        self.assertEqual(observed["terminal_supersession"]["d0"], 3)
        self.assertTrue(observed["dominates_prior_attempt"])

        # Dominance is bidirectional: an exact attempt-two success also
        # supersedes a previously drained adverse attempt-one result without
        # rewriting either immutable observation.
        backend = MemoryBackend()
        value = payload("exact-head-dispatch", run_id=826)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=827,
            actor_run_attempt=1,
        )
        locator = {
            "run_id": 828,
            "run_attempt": 1,
            "workflow_id": 66,
            "workflow_path": (
                ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"
            ),
            "event": "repository_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "failure",
            "display_title": (
                f"qikvrt-exact intent={intent['fingerprint']} "
                f"seq={intent['sequence']} transport-attempt=1"
            ),
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=locator,
        )
        adverse_artifact = {
            "id": 829,
            "name": "qikvrt-exact-head-adverse-828-1",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 828,
            "producer_run_attempt": 1,
            "verified": True,
        }
        completion = outbox.record_completion(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=locator,
            evidence=completion_evidence(locator, adverse_artifact),
        )
        outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": "ATTEMPT_1_ACCEPTED_ADVERSE",
                    "exhaustion": {
                        "schema": outbox.EXHAUSTION_SCHEMA,
                        "lane": intent["lane"],
                        "sequence": intent["sequence"],
                        "fingerprint": intent["fingerprint"],
                        "mode": "CHILD_RESULT_ADVERSE",
                        "attempts": [1],
                        "first_blocker": "ATTEMPT_1_ACCEPTED_ADVERSE",
                        "transport_attempt": 1,
                        "successor": locator,
                        "successor_sha256": completion["child_sha256"],
                        "completion_evidence_sha256": completion[
                            "evidence_sha256"
                        ],
                        "verified": True,
                        "productive_effect": False,
                    },
                    "productive_effect": False,
                }
            ),
        )
        success = {**locator, "run_attempt": 2, "conclusion": "success"}
        success_artifact = {
            "id": 830,
            "name": "qikvrt-exact-head-business-828-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 828,
            "producer_run_attempt": 2,
            "verified": True,
        }
        observed = outbox.record_same_run_result(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            fingerprint=intent["fingerprint"],
            transport_attempt=1,
            child=success,
            evidence=completion_evidence(success, success_artifact),
        )
        historical = outbox.lookup(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            fingerprint=intent["fingerprint"],
        )
        self.assertEqual(historical["terminal"]["d0"], 3)
        self.assertEqual(historical["terminal_supersession"]["d0"], 2)
        self.assertEqual(historical["effective_d0"], 2)
        self.assertEqual(observed["terminal_supersession"]["d0"], 2)

        # A favorable later attempt can repair only the exact adverse result
        # of the same accepted run.  It must never erase an evaluator/main
        # supersession Authority terminal.
        backend, intent, locator, _acceptance = seeded(queued=True)
        superseded_observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_EVALUATOR_SUPERSEDED",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "sealed_main_head_sha": "a" * 40,
            "observed_main_head_sha": "f" * 40,
            "verified": True,
            "productive_effect": False,
        }
        superseded_record = persist_authority_observation(
            backend, intent, superseded_observation, run_id=831
        )
        outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence(
                {
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": "OUTBOX_EVALUATOR_SUPERSEDED",
                    "exhaustion": ambiguity_exhaustion(
                        intent,
                        "OUTBOX_EVALUATOR_SUPERSEDED",
                        superseded_record,
                    ),
                    "productive_effect": False,
                }
            ),
        )
        late_success = {
            **locator,
            "run_attempt": 2,
            "status": "completed",
            "conclusion": "success",
        }
        late_artifact = {
            "id": 832,
            "name": "qikvrt-exact-head-business-822-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 822,
            "producer_run_attempt": 2,
            "verified": True,
        }
        with self.assertRaisesRegex(outbox.OutboxBlock, "EVALUATOR_SUPERSEDED"):
            outbox.record_same_run_result(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                fingerprint=intent["fingerprint"],
                transport_attempt=1,
                child=late_success,
                evidence=completion_evidence(late_success, late_artifact),
            )
        self.assertEqual(
            outbox.lookup(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                fingerprint=intent["fingerprint"],
            )["effective_d0"],
            3,
        )

    def test_child_rerun_rejects_wrong_run_and_exhausts_exact_attempt_two(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch")
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=811,
            actor_run_attempt=1,
        )
        title = (
            "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h=" + "b" * 40
            + " f=" + "c" * 64 + " i=" + intent["fingerprint"] + " a=1"
        )
        original = {
            "run_id": 812,
            "run_attempt": 1,
            "workflow_id": 77,
            "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "cancelled",
            "display_title": title,
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=original,
        )
        evidence = child_retry_evidence(intent, acceptance)
        outbox.prepare_child_rerun(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            transport_attempt=1,
            retry_evidence=evidence,
            actor_run_id=813,
            actor_run_attempt=1,
        )
        recovered = {
            **original,
            "run_id": 999,
            "run_attempt": 2,
            "conclusion": "failure",
        }
        with self.assertRaisesRegex(outbox.OutboxBlock, "exact same-run"):
            outbox.record_child_rerun_acceptance(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                transport_attempt=1,
                child=recovered,
            )
        recovered["run_id"] = 812
        recovery_acceptance = outbox.record_child_rerun_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            transport_attempt=1,
            child=recovered,
        )
        adverse_artifact = {
            "id": 903,
            "name": "qikvrt-requested-review-adverse-812-2",
            "archive_sha256": "f" * 64,
            "payload_sha256": "d" * 64,
            "producer_run_id": 812,
            "producer_run_attempt": 2,
            "verified": True,
        }
        recovery_completion = outbox.record_completion(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=recovered,
            evidence=completion_evidence(
                recovered, adverse_artifact, job_name="plan-review"
            ),
            child_recovery=True,
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=terminal_evidence({
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "exhaustion": {
                    "schema": outbox.EXHAUSTION_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "mode": "CHILD_RERUN_EXHAUSTED",
                    "attempts": [1],
                    "transport_attempt": 1,
                    "target_run_id": 812,
                    "target_run_attempt": 2,
                    "successor": recovered,
                    "successor_sha256": recovery_completion["child_sha256"],
                    "completion_evidence_sha256": recovery_completion[
                        "evidence_sha256"
                    ],
                    "first_blocker": "ATTEMPT_2_TERMINAL_ADVERSE",
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }),
        )
        self.assertEqual(terminal["d0"], 3)

    def test_child_rerun_absence_requires_stored_api_observation(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=814)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=815,
            actor_run_attempt=1,
        )
        original = {
            "run_id": 816,
            "run_attempt": 1,
            "workflow_id": 77,
            "workflow_path": (
                ".github/workflows/qikvrt_requested_review_executor.yml"
            ),
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "cancelled",
            "display_title": (
                "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h=" + "b" * 40
                + " f=" + "c" * 64 + " i=" + intent["fingerprint"]
                + " a=1"
            ),
        }
        acceptance = outbox.record_acceptance(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            attempt=1,
            child=original,
        )
        outbox.prepare_child_rerun(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            transport_attempt=1,
            retry_evidence=child_retry_evidence(intent, acceptance),
            actor_run_id=817,
            actor_run_attempt=1,
        )
        observation = {
            "schema": outbox.CHILD_RERUN_OBSERVATION_SCHEMA,
            "blocker": "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
            "lane": intent["lane"],
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "transport_attempt": 1,
            "target_run_id": original["run_id"],
            "target_run_attempt": 2,
            "target_attempt_one_child": original,
            "target_attempt_one_child_sha256": outbox.digest(original),
            "preparation_actor": {
                "run_id": 817,
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-09-01T08:00:00Z",
                "updated_at": "2026-09-01T08:30:00Z",
            },
            "preparation_actor_sha256": outbox.digest(
                {
                    "run_id": 817,
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-09-01T08:00:00Z",
                    "updated_at": "2026-09-01T08:30:00Z",
                }
            ),
            "query_window_start": "2026-09-01T08:00:00Z",
            "query_window_end": "2026-09-01T08:31:00Z",
            "observation_started_at": "2026-09-01T08:31:00Z",
            "observation_completed_at": "2026-09-01T09:00:00Z",
            "observed_run_attempt": 1,
            "scan_complete": True,
            "successor_present": False,
            "verified": True,
            "productive_effect": False,
        }
        malformed_observations = []
        preterminal = copy.deepcopy(observation)
        preterminal["query_window_end"] = "2026-09-01T08:30:00Z"
        preterminal["observation_started_at"] = "2026-09-01T08:30:00Z"
        malformed_observations.append(preterminal)
        wrong_actor = copy.deepcopy(observation)
        wrong_actor["preparation_actor"]["run_id"] = 999
        wrong_actor["preparation_actor_sha256"] = outbox.digest(
            wrong_actor["preparation_actor"]
        )
        malformed_observations.append(wrong_actor)
        nonterminal_actor = copy.deepcopy(observation)
        nonterminal_actor["preparation_actor"].update(
            status="in_progress", conclusion=None
        )
        nonterminal_actor["preparation_actor_sha256"] = outbox.digest(
            nonterminal_actor["preparation_actor"]
        )
        malformed_observations.append(nonterminal_actor)
        wrong_target = copy.deepcopy(observation)
        wrong_target["target_attempt_one_child"]["conclusion"] = "failure"
        wrong_target["target_attempt_one_child_sha256"] = outbox.digest(
            wrong_target["target_attempt_one_child"]
        )
        malformed_observations.append(wrong_target)
        for offset, malformed in enumerate(malformed_observations):
            with self.subTest(malformed_observation=offset):
                with self.assertRaisesRegex(
                    outbox.OutboxBlock, "child-rerun absence observation mismatch"
                ):
                    persist_authority_observation(
                        backend, intent, malformed, run_id=819 + offset
                    )
        raw_hold = terminal_evidence(
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "reason": "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
                "exhaustion": {
                    "schema": outbox.EXHAUSTION_SCHEMA,
                    "lane": intent["lane"],
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "mode": "CHILD_RERUN_EXHAUSTED",
                    "attempts": [1],
                    "first_blocker": "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
                    "transport_attempt": 1,
                    "target_run_id": original["run_id"],
                    "target_run_attempt": 2,
                    "successor": None,
                    "successor_sha256": None,
                    "authority_observation_sha256": "9" * 64,
                    "observation_sha256": outbox.digest(observation),
                    "verified": True,
                    "productive_effect": False,
                },
                "productive_effect": False,
            }
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "authority-observation"):
            outbox.terminalize(
                backend,
                lane=intent["lane"],
                sequence=intent["sequence"],
                evidence=raw_hold,
            )
        record = persist_authority_observation(
            backend, intent, observation, run_id=818
        )
        exact_hold = copy.deepcopy(raw_hold)
        exact_hold["exhaustion"]["authority_observation_sha256"] = outbox.digest(
            record
        )
        terminal = outbox.terminalize(
            backend,
            lane=intent["lane"],
            sequence=intent["sequence"],
            evidence=exact_hold,
        )
        self.assertEqual(terminal["d0"], 3)

    def test_child_rerun_never_retries_non_cancelled_business_result(self):
        for ordinal, conclusion in enumerate(("success", "failure", "skipped"), 1):
            with self.subTest(conclusion=conclusion):
                backend = MemoryBackend()
                value = payload(
                    "exact-review-dispatch", run_id=820 + ordinal
                )
                intent = outbox.append_intent(
                    backend, payload=value, artifact=artifact(value)
                )
                outbox.prepare_transport(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    actor_run_id=830 + ordinal,
                    actor_run_attempt=1,
                )
                child = {
                    "run_id": 840 + ordinal,
                    "run_attempt": 1,
                    "workflow_id": 77,
                    "workflow_path": (
                        ".github/workflows/qikvrt_requested_review_executor.yml"
                    ),
                    "event": "workflow_dispatch",
                    "repository": "Goldkelch/qik-vrt",
                    "head_sha": "a" * 40,
                    "status": "completed",
                    "conclusion": conclusion,
                    "display_title": (
                        "qikvrt-rr-v3 e=" + "a" * 40 + " p=935 h="
                        + "b" * 40 + " f=" + "c" * 64 + " i="
                        + intent["fingerprint"] + " a=1"
                    ),
                }
                acceptance = outbox.record_acceptance(
                    backend,
                    lane=intent["lane"],
                    sequence=intent["sequence"],
                    attempt=1,
                    child=child,
                )
                retry = child_retry_evidence(intent, acceptance)
                with self.assertRaisesRegex(
                    outbox.OutboxBlock,
                    "retry evidence binding|completed/cancelled|observed child differs",
                ):
                    outbox.prepare_child_rerun(
                        backend,
                        lane=intent["lane"],
                        sequence=intent["sequence"],
                        transport_attempt=1,
                        retry_evidence=retry,
                        actor_run_id=850 + ordinal,
                        actor_run_attempt=1,
                    )
                self.assertEqual(
                    outbox.read_next(backend, intent["lane"])["child_recovery"],
                    {},
                )

    def test_artifact_payload_digest_must_equal_exact_sealed_bytes(self):
        backend = MemoryBackend()
        value = payload()
        bad = artifact(value)
        bad["payload_sha256"] = "e" * 64
        with self.assertRaisesRegex(outbox.OutboxBlock, "differs from sealed bytes"):
            outbox.append_intent(backend, payload=value, artifact=bad)
        self.assertEqual(backend.update_calls, 0)

    def test_main_drift_blocks_pre_transport_marker_and_post(self):
        backend = MemoryBackend()
        value = payload()
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        backend.main_head = "f" * 40
        with self.assertRaisesRegex(outbox.OutboxBlock, "main head drifted"):
            outbox.prepare_transport(
                backend,
                lane="ruleset-dispatch",
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=501,
                actor_run_attempt=1,
            )
        self.assertNotIn(
            outbox.transport_path("ruleset-dispatch", intent["sequence"], 1),
            backend.commits[backend.head],
        )

    def test_immutable_transport_collision_is_fail_closed(self):
        backend = MemoryBackend()
        value = payload()
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        outbox.prepare_transport(
            backend,
            lane="ruleset-dispatch",
            sequence=intent["sequence"],
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=601,
            actor_run_attempt=1,
        )
        with self.assertRaisesRegex(outbox.OutboxBlock, "immutable outbox record collision"):
            outbox.prepare_transport(
                backend,
                lane="ruleset-dispatch",
                sequence=intent["sequence"],
                attempt=1,
                request=outbox.request_for_transport_attempt(intent, 1),
                actor_run_id=602,
                actor_run_attempt=1,
            )


if __name__ == "__main__":
    unittest.main()
