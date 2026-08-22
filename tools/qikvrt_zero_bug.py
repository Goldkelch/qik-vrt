#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

POLICY = Path("policy/ZERO_BUG_CONTINUOUS_V1.json")
PERFECT = Path("policy/PERFECT_OPTIMUM_V1.json")


def load_policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def evaluate(observation, policy=None):
    policy = policy or load_policy()
    required = {
        "exact_head_and_tree_bound": bool(observation.get("exact_head_and_tree_bound")),
        "known_deterministic_defects_zero": observation.get("known_deterministic_defects", 1) == 0,
        "repository_integrity_verifies": bool(observation.get("repository_integrity_verifies")),
        "required_exact_head_gates_non_adverse": bool(observation.get("required_exact_head_gates_non_adverse")),
        "productive_writer_count_at_most_one": observation.get("productive_writer_count", 2) <= 1,
        "stale_evidence_reuse_zero": observation.get("stale_evidence_reuse", 1) == 0,
        "registered_improvers_only": bool(observation.get("registered_improvers_only")),
        "reobserve_after_every_mutation": bool(observation.get("reobserve_after_every_mutation")),
        "full_tracked_tree_sha256_bound": bool(observation.get("full_tracked_tree_sha256_bound")),
    }
    missing = [k for k in policy["hard_invariants"] if not required.get(k, False)]
    if not missing:
        state = "ZERO_KNOWN_DETERMINISTIC_BUGS"
    elif observation.get("evidence_incomplete"):
        state = "HOLD_EVIDENCE_INCOMPLETE"
    else:
        state = "HOLD_DEFECT_IDENTIFIED"
    return {
        "schema": "qikvrt_zero_bug_evaluation_v1",
        "state": state,
        "invariants": required,
        "failed_invariants": missing,
        "evidence": observation.get("evidence", {}),
        "universal_bug_freedom_claimed": False,
    }


def self_check(policy=None):
    policy = policy or load_policy()
    perfect = json.loads(PERFECT.read_text(encoding="utf-8"))
    registered = [x.get("id") for x in perfect.get("registered_improvers", [])]
    audit = policy.get("audit_surface", {})
    return {
        "schema": "qikvrt_zero_bug_self_check_v1",
        "complete": all(k in policy for k in ("schema", "hard_invariants", "state_machine", "repair_order", "continuous_revision", "audit_surface")),
        "after_mutation": policy["state_machine"].get("after_mutation"),
        "later_is_better": policy["continuous_revision"].get("later_is_better"),
        "arbitrary_unregistered_self_modification": policy["continuous_revision"].get("arbitrary_unregistered_self_modification"),
        "registered_improvers": registered,
        "required_peer_workflows": audit.get("required_peer_workflows", []),
        "writer_workflows": audit.get("writer_workflows", []),
        "bit_audit_algorithm": audit.get("bit_audit", {}).get("canonical_index_digest"),
    }


def derive_observation(args):
    bit = json.loads(Path(args.bit_audit).read_text(encoding="utf-8"))
    peers = json.loads(Path(args.peer_gates).read_text(encoding="utf-8"))
    perfect = json.loads(PERFECT.read_text(encoding="utf-8"))
    registered = [x.get("id") for x in perfect.get("registered_improvers", [])]
    markers = {
        "regressions": Path(args.regressions_marker).is_file(),
        "integrity": Path(args.integrity_marker).is_file(),
        "full_tests": Path(args.tests_marker).is_file(),
    }
    exact = (
        bit.get("head_sha") == args.head
        and bit.get("tree_sha") == args.tree
        and args.expected_head == args.head
    )
    peer_ok = bool(peers.get("required_exact_head_gates_non_adverse")) and peers.get("head_sha") == args.head
    writer_count = peers.get("productive_writer_count")
    evidence_heads = peers.get("evidence_heads", []) + [bit.get("head_sha")]
    stale_reuse = sum(1 for h in evidence_heads if h != args.head)
    registered_only = registered == ["integrity_trio_materializer"]
    reobserved = bool(peers.get("current_head_reobserved")) and peers.get("head_sha") == args.head
    bit_bound = (
        bit.get("hash_algorithm") == "sha256"
        and bit.get("source") == "git_object_database"
        and isinstance(bit.get("canonical_index_sha256"), str)
        and len(bit.get("canonical_index_sha256", "")) == 64
    )
    known_defects = 0 if all(markers.values()) and peer_ok else 1
    return {
        "exact_head_and_tree_bound": exact,
        "known_deterministic_defects": known_defects,
        "repository_integrity_verifies": markers["integrity"],
        "required_exact_head_gates_non_adverse": peer_ok,
        "productive_writer_count": writer_count if isinstance(writer_count, int) else 2,
        "stale_evidence_reuse": stale_reuse,
        "registered_improvers_only": registered_only,
        "reobserve_after_every_mutation": reobserved,
        "full_tracked_tree_sha256_bound": bit_bound,
        "evidence_incomplete": not all(markers.values()) or not peer_ok,
        "evidence": {
            "head_sha": args.head,
            "tree_sha": args.tree,
            "bit_audit_canonical_index_sha256": bit.get("canonical_index_sha256"),
            "tracked_entry_count": bit.get("entry_count"),
            "tracked_blob_bytes": bit.get("tracked_blob_bytes"),
            "local_command_markers": markers,
            "peer_gate_snapshot": peers,
            "registered_improvers": registered,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-check", action="store_true")
    p.add_argument("--observation")
    p.add_argument("--derive", action="store_true")
    p.add_argument("--head")
    p.add_argument("--tree")
    p.add_argument("--expected-head")
    p.add_argument("--bit-audit")
    p.add_argument("--peer-gates")
    p.add_argument("--regressions-marker")
    p.add_argument("--integrity-marker")
    p.add_argument("--tests-marker")
    p.add_argument("--write-observation")
    args = p.parse_args()
    if args.self_check:
        result = self_check()
        ok = (
            result["complete"]
            and result["after_mutation"] == "HOLD_UNVERIFIED"
            and result["later_is_better"] is False
            and result["bit_audit_algorithm"] == "sha256"
            and result["registered_improvers"] == ["integrity_trio_materializer"]
        )
    else:
        if args.derive:
            required_args = [args.head, args.tree, args.expected_head, args.bit_audit, args.peer_gates, args.regressions_marker, args.integrity_marker, args.tests_marker]
            if not all(required_args):
                p.error("--derive requires head/tree/evidence arguments")
            observation = derive_observation(args)
            if args.write_observation:
                Path(args.write_observation).write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        else:
            if not args.observation:
                p.error("--observation required")
            observation = json.loads(Path(args.observation).read_text(encoding="utf-8"))
        result = evaluate(observation)
        ok = result["state"] == "ZERO_KNOWN_DETERMINISTIC_BUGS"
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
