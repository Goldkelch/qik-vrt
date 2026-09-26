#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bound read-only review work using the existing evaluator and chunk transport.

The source owns live observation and all effects. A counterpart computes over
exact retained bytes. Its output is accepted only when it matches the source
receipt byte for byte. Node identity never substitutes for review authority.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import qikvrt_requested_review_executor as review
from tools.qikvrt_github_observation import ObservationClient, ObservationError

PAIR = {"Goldkelch/qik-vrt": "ingolf-lohmann/qik-vrt",
        "ingolf-lohmann/qik-vrt": "Goldkelch/qik-vrt"}
CODE = ("tools/qikvrt_requested_review_executor.py", "tools/qikvrt_review_mesh_work.py",
        "tools/qikvrt_github_observation.py", "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json")
WORKFLOW = "qikvrt_requested_review_executor.yml"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(review._pretty_json_bytes(value))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def pack(root, output):
    root, output = Path(root), Path(output)
    snapshot_bytes, diff = (root / "snapshot.json").read_bytes(), (root / "review.diff").read_bytes()
    snapshot = json.loads(snapshot_bytes)
    receipt_bytes = (root / "review.json").read_bytes()
    receipt = review.evaluate(snapshot, diff)
    require(receipt_bytes == review._pretty_json_bytes(receipt), "SOURCE_RECEIPT_NOT_EXACT")
    source = snapshot["repository"]
    require(source in PAIR, "SOURCE_REPOSITORY_NOT_CONFIGURED")
    transport = receipt["repository_feedback"]["diff_transport"]
    # Reuse the existing exact packet contract, including its total digest.
    manifest_bytes, packets = review.prepare_diff_transport_ledger_entries(
        transport, diff, receipt["ledger_diff_path"])
    output.mkdir(parents=True, exist_ok=False)
    (output / "snapshot.json").write_bytes(snapshot_bytes)
    (output / "source-review.json").write_bytes(receipt_bytes)
    (output / "diff-manifest.json").write_bytes(manifest_bytes)
    for index, packet in enumerate(packets):
        (output / f"packet-{index:06d}.bin").write_bytes(packet)
    code = {path: git("rev-parse", f"HEAD:{path}") for path in CODE}
    require(code[CODE[0]] == snapshot["trusted_evaluator_blob_sha"], "SOURCE_EVALUATOR_DRIFT")
    require(code[CODE[2]] == snapshot.get("trusted_read_transport_blob_sha"), "SOURCE_TRANSPORT_DRIFT")
    value = {"schema": "qikvrt_review_mesh_work_v1", "source_repository": source,
             "worker_repository": PAIR[source], "pr_number": snapshot["pr_number"],
             "source_main_sha": snapshot["current_main_sha"],
             "base_sha": snapshot["base_sha"], "head_sha": snapshot["head_sha"],
             "tree_sha": snapshot["tree_sha"], "evaluator_blobs": code,
             "snapshot_sha256": digest(snapshot_bytes), "source_receipt_sha256": digest(receipt_bytes),
             "diff_manifest_sha256": digest(manifest_bytes), "packet_count": len(packets),
             "diff_sha256": digest(diff), "external_effect": "NONE",
             "source_run_id": os.environ.get("GITHUB_RUN_ID"),
             "source_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}
    write(output / "work.json", value)
    return digest((output / "work.json").read_bytes())


def worker(bundle, expected_digest, repository, output):
    bundle = Path(bundle)
    raw = (bundle / "work.json").read_bytes()
    require(digest(raw) == expected_digest, "WORK_DIGEST_MISMATCH")
    work = json.loads(raw)
    require(work.get("schema") == "qikvrt_review_mesh_work_v1", "WORK_SCHEMA_INVALID")
    source = work["source_repository"]
    require(source in PAIR and PAIR[source] == repository == work["worker_repository"],
            "WORKER_ROLE_MISMATCH")
    require(set(work["evaluator_blobs"]) == set(CODE), "WORKER_CODE_SET_MISMATCH")
    for path in CODE:
        require(git("rev-parse", f"HEAD:{path}") == work["evaluator_blobs"][path],
                "WORKER_CODE_IDENTITY_MISMATCH " + path)
    snapshot_bytes = (bundle / "snapshot.json").read_bytes()
    receipt_bytes = (bundle / "source-review.json").read_bytes()
    manifest_bytes = (bundle / "diff-manifest.json").read_bytes()
    for raw_bytes, name in ((snapshot_bytes, "snapshot"), (receipt_bytes, "source_receipt"),
                            (manifest_bytes, "diff_manifest")):
        require(digest(raw_bytes) == work[name + "_sha256"], "WORK_INPUT_DIGEST_MISMATCH " + name)
    count = work["packet_count"]
    require(type(count) is int and 0 < count <= 4096, "WORK_PACKET_COUNT_INVALID")
    require(sorted(p.name for p in bundle.glob('packet-*.bin'))
            == [f"packet-{index:06d}.bin" for index in range(count)], "WORK_PACKET_SET_MISMATCH")
    packets = [(bundle / f"packet-{index:06d}.bin").read_bytes() for index in range(count)]
    diff = review.reassemble_diff_transport(json.loads(manifest_bytes), packets)
    require(digest(diff) == work["diff_sha256"], "WORK_DIFF_DIGEST_MISMATCH")
    snapshot = json.loads(snapshot_bytes)
    require(snapshot["current_main_sha"] == work["source_main_sha"]
            and git("rev-parse", "HEAD") == work["source_main_sha"], "WORK_EVALUATOR_SOURCE_MISMATCH")
    for field in ("pr_number", "base_sha", "head_sha", "tree_sha"):
        require(snapshot[field] == work[field], "WORK_SUBJECT_MISMATCH " + field)
    require(snapshot["repository"] == source, "WORK_SOURCE_MISMATCH")
    observed = review._pretty_json_bytes(review.evaluate(snapshot, diff))
    require(observed == receipt_bytes, "WORKER_DISAGREES_WITH_SOURCE")
    result = {"schema": "qikvrt_review_mesh_result_v1", "work_sha256": expected_digest,
              "source_repository": source, "worker_repository": repository,
              "worker_head_sha": os.environ.get("QIKVRT_WORKER_HEAD") or git("rev-parse", "HEAD"),
              "worker_tree_sha": os.environ.get("QIKVRT_WORKER_TREE") or git("rev-parse", "HEAD^{tree}"),
              "evaluator_source_repository": source,
              "evaluator_source_head": work["source_main_sha"],
              "worker_run_id": os.environ.get("GITHUB_RUN_ID"),
              "worker_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
              "evaluator_blobs": work["evaluator_blobs"],
              "head_sha": work["head_sha"], "tree_sha": work["tree_sha"],
              "result_sha256": digest(observed), "byte_identical": True,
              "external_effect": "NONE", "native_approval": False, "merge": False}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "review.json").write_bytes(observed)
    write(output / "worker.json", result)
    return result


def consolidate(bundle, returned):
    bundle, returned = Path(bundle), Path(returned)
    work_bytes = (bundle / "work.json").read_bytes()
    work = json.loads(work_bytes)
    value = json.loads((returned / "worker.json").read_bytes())
    require(value.get("schema") == "qikvrt_review_mesh_result_v1", "WORKER_RESULT_SCHEMA_INVALID")
    expected = {"work_sha256": digest(work_bytes), "source_repository": work["source_repository"],
                "evaluator_source_repository": work["source_repository"],
                "evaluator_source_head": work["source_main_sha"],
                "worker_repository": work["worker_repository"], "evaluator_blobs": work["evaluator_blobs"],
                "head_sha": work["head_sha"], "tree_sha": work["tree_sha"],
                "result_sha256": work["source_receipt_sha256"], "byte_identical": True,
                "external_effect": "NONE", "native_approval": False, "merge": False}
    require(set(value) == set(expected) | {"schema", "worker_head_sha", "worker_tree_sha",
                                            "worker_run_id", "worker_run_attempt"}, "WORKER_RESULT_FIELDS_MISMATCH")
    require(review._pretty_json_bytes({k: value.get(k) for k in expected})
            == review._pretty_json_bytes(expected), "WORKER_RESULT_BINDING_MISMATCH")
    require(all(re.fullmatch(r"[0-9a-f]{40}", value.get(k, ""))
                for k in ("worker_head_sha", "worker_tree_sha")), "WORKER_IDENTITY_MISSING")
    result = (returned / "review.json").read_bytes()
    require(digest(result) == work["source_receipt_sha256"]
            and result == (bundle / "source-review.json").read_bytes(), "WORKER_RESULT_BYTES_MISMATCH")
    return {"schema": "qikvrt_review_mesh_consolidation_v1", "state": "EXACT_BYTES_CONSOLIDATED",
            **expected, "worker_head_sha": value["worker_head_sha"],
            "worker_tree_sha": value["worker_tree_sha"], "fresh_authority_reobservation_required": True}


def execute(bundle, output, *, timeout=300):
    """Dispatch once, synchronously collect once; retain local capacity if absent.

    Missing capability is recorded explicitly. An admitted remote task must
    complete exactly; failure or ambiguous delivery cannot silently fall back.
    """
    bundle, output = Path(bundle), Path(output)
    work_bytes = (bundle / "work.json").read_bytes()
    work = json.loads(work_bytes)
    key = digest(work_bytes)
    source, target = work["source_repository"], work["worker_repository"]
    require(PAIR.get(source) == target, "WORKER_ROUTE_INVALID")
    token = os.environ.get("QIKVRT_MESH_TOKEN", "")
    report = {"schema": "qikvrt_review_mesh_execution_v1", "work_sha256": key,
              "source_repository": source, "worker_repository": target,
              "dispatch_performed": False, "remote_execution_verified": False,
              "native_approval": False, "merge": False}
    output.mkdir(parents=True, exist_ok=True)
    def save(state, **values):
        report.update(state=state, **values)
        write(output / "execution.json", report)
        return report
    if not token:
        return save("LOCAL_RETAINED_MESH_CREDENTIAL_MISSING")
    api = ObservationClient(target, token, output / "observations", lane="MESH_READ_ONLY")
    prefix = f"repos/{target}"
    try:
        # The existing Mirror review core can be older and remains available.
        # Only the worker adapter and read transport must be locally identical;
        # evaluation runs from a separately verified source-Main checkout.
        for path in (CODE[1], CODE[2]):
            expected = work["evaluator_blobs"][path]
            content = api.get(f"{prefix}/contents/{path}?ref=main")[0]
            if content.get("sha") != expected:
                return save("LOCAL_RETAINED_WORKER_CODE_NOT_ADMITTED", path=path)
        workflow = api.get(f"{prefix}/contents/.github/workflows/{WORKFLOW}?ref=main")[0]
    except ObservationError as exc:
        if exc.status == 404:
            return save("LOCAL_RETAINED_WORKER_CAPABILITY_ABSENT")
        raise
    workflow_bytes = base64.b64decode(workflow["content"], validate=False)
    require(b"# qikvrt-mesh-review-worker:v1" in workflow_bytes, "WORKER_PROTOCOL_NOT_ADMITTED")
    source_run = os.environ.get("GITHUB_RUN_ID", "")
    require(source_run.isdecimal() and int(source_run) > 0, "SOURCE_RUN_ID_MISSING")
    require(work.get("source_run_id") == source_run, "SOURCE_RUN_BINDING_MISMATCH")
    payload = {"ref": "main", "inputs": {"mode": "mesh-worker", "pr": str(work["pr_number"]),
               "head": work["head_sha"], "source_repository": source,
               "source_run_id": source_run, "work_sha256": key}}
    environment = {**os.environ, "GH_TOKEN": token}
    # A worker cannot outlive the source's 12-minute job lease. Bound discovery
    # to a full hour, paginate completely, and reuse an already dispatched task.
    since = datetime.fromtimestamp(time.time() - 3600, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    runs_path = (f"{prefix}/actions/workflows/{WORKFLOW}/runs?event=workflow_dispatch"
                 f"&per_page=100&created=%3E%3D{since}")
    def existing():
        pages = api.pages(runs_path)
        runs = [run for page in pages for run in page.get("workflow_runs", [])
                if run.get("display_title") == f"QIKVRT mesh review {source_run} {key}"
                and run.get("head_branch") == "main"]
        require(len(runs) <= 1, "MESH_DELIVERY_AMBIGUOUS")
        return runs[0] if runs else None
    selected = existing()
    # The dedicated Mesh credential is used only for the declared dispatch and
    # the exact artifact read. It is never substituted after a rate-limit error.
    if selected is None:
        request = subprocess.run(["gh", "api", "--method", "POST",
                                 f"{prefix}/actions/workflows/{WORKFLOW}/dispatches", "--input", "-"],
                                input=json.dumps(payload), text=True, capture_output=True, env=environment)
        if request.returncode:
            save("HOLD_DISPATCH_NOT_CONFIRMED", detail=request.stderr[:500])
            raise ValueError("MESH_DISPATCH_NOT_CONFIRMED")
        save("DISPATCH_ACCEPTED", dispatch_performed=True)
    else:
        save("EXISTING_EXACT_DISPATCH_REUSED", run_id=selected["id"])
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if selected is None:
            selected = existing()
        else:
            selected = api.get(f"{prefix}/actions/runs/{selected['id']}")[0]
        if selected and selected.get("status") == "completed":
            save("REMOTE_TERMINAL", run_id=selected["id"], conclusion=selected.get("conclusion"))
            require(selected.get("conclusion") == "success", "MESH_WORKER_FAILED")
            returned = output / "returned"
            subprocess.run(["gh", "run", "download", str(selected["id"]), "--repo", target,
                            "--name", f"qikvrt-mesh-result-{key}", "--dir", str(returned)],
                           check=True, env=environment)
            result = consolidate(bundle, returned)
            require(result["worker_head_sha"] == selected["head_sha"], "WORKER_RUN_HEAD_MISMATCH")
            worker_receipt = json.loads((returned / "worker.json").read_bytes())
            require(worker_receipt.get("worker_run_id") == str(selected["id"])
                    and worker_receipt.get("worker_run_attempt") == str(selected["run_attempt"]),
                    "WORKER_RUN_ATTEMPT_MISMATCH")
            write(output / "consolidation.json", result)
            return save("EXACT_BYTES_CONSOLIDATED", remote_execution_verified=True)
        time.sleep(min(20, max(0, deadline - time.monotonic())))
    save("HOLD_REMOTE_EXECUTION_PENDING", run_id=selected.get("id") if selected else None)
    raise ValueError("MESH_EXECUTION_PENDING_REOBSERVE_EXACT_RUN")


def verify_source(bundle, expected_digest, repository):
    """Before executing source code, authenticate its current trusted Main/run."""
    bundle = Path(bundle)
    raw = (bundle / "work.json").read_bytes()
    require(digest(raw) == expected_digest, "WORK_DIGEST_MISMATCH")
    work = json.loads(raw)
    require(work.get("schema") == "qikvrt_review_mesh_work_v1", "WORK_SCHEMA_INVALID")
    source = work["source_repository"]
    require(PAIR.get(source) == repository == work["worker_repository"], "WORKER_ROLE_MISMATCH")
    require(re.fullmatch(r"[0-9a-f]{40}", work.get("source_main_sha", "")), "SOURCE_MAIN_INVALID")
    source_run = work.get("source_run_id", "")
    require(isinstance(source_run, str) and source_run.isdecimal() and int(source_run) > 0,
            "SOURCE_RUN_INVALID")
    require(source_run == os.environ.get("SOURCE_RUN_ID"), "SOURCE_ARTIFACT_RUN_MISMATCH")
    token = os.environ.get("QIKVRT_MESH_TOKEN") or os.environ.get("GH_TOKEN", "")
    api = ObservationClient(source, token, bundle / "source-observations", lane="MESH_READ_ONLY")
    main = api.get(f"repos/{source}/commits/main")[0]
    require(main.get("sha") == work["source_main_sha"], "SOURCE_TRUSTED_MAIN_DRIFT")
    run = api.get(f"repos/{source}/actions/runs/{source_run}")[0]
    event = run.get("event")
    if event in {"pull_request_target", "pull_request_review"}:
        # GitHub's run metadata names the PR head even though this job checks
        # out trusted Main. Bind that event to its exact PR subject separately.
        subject_bound = run.get("head_sha") == work.get("head_sha") and any(
            pr.get("number") == work.get("pr_number")
            and (pr.get("base") or {}).get("ref") == "main"
            for pr in run.get("pull_requests", []))
    else:
        subject_bound = run.get("head_branch") == "main"
    require(run.get("path") == f".github/workflows/{WORKFLOW}"
            and str(run.get("id")) == source_run
            and (run.get("repository") or {}).get("full_name") == source
            and subject_bound
            and run.get("run_attempt") == int(work["source_run_attempt"])
            and event in {"pull_request_target", "pull_request_review", "issue_comment", "workflow_run", "workflow_dispatch"},
            "SOURCE_TRUSTED_RUN_MISMATCH")
    return {"repository": source, "sha": work["source_main_sha"],
            "worker_head": git("rev-parse", "HEAD"), "worker_tree": git("rev-parse", "HEAD^{tree}")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--root", required=True)
    p.add_argument("--output", required=True)
    w = sub.add_parser("worker")
    w.add_argument("--bundle", required=True)
    w.add_argument("--expected-digest", required=True)
    w.add_argument("--repository", required=True)
    w.add_argument("--output", required=True)
    c = sub.add_parser("consolidate")
    c.add_argument("--bundle", required=True)
    c.add_argument("--returned", required=True)
    e = sub.add_parser("execute")
    e.add_argument("--bundle", required=True)
    e.add_argument("--output", required=True)
    s = sub.add_parser("verify-source")
    s.add_argument("--bundle", required=True)
    s.add_argument("--expected-digest", required=True)
    s.add_argument("--repository", required=True)
    args = parser.parse_args()
    if args.command == "pack":
        print(pack(args.root, args.output))
    elif args.command == "worker":
        print(json.dumps(worker(args.bundle, args.expected_digest, args.repository, args.output), sort_keys=True))
    elif args.command == "consolidate":
        print(json.dumps(consolidate(args.bundle, args.returned), sort_keys=True))
    elif args.command == "execute":
        print(json.dumps(execute(args.bundle, args.output), sort_keys=True))
    else:
        print(json.dumps(verify_source(args.bundle, args.expected_digest, args.repository), sort_keys=True))


if __name__ == "__main__":
    main()
