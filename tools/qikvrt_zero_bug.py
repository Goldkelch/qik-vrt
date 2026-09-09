#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

POLICY = Path("policy/ZERO_BUG_CONTINUOUS_V1.json")
PERFECT = Path("policy/PERFECT_OPTIMUM_V1.json")
EVENT_INGRESS_WORKFLOW = Path(".github/workflows/qikvrt_zero_bug_continuous.yml")


def load_policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def event_ingress_check(policy=None):
    """Verify that the zero-bug auditor has only native event ingress.

    Direct authorized requests are handled by the caller outside GitHub Actions.
    The repository workflow itself must remain free of periodic, manual, and
    synthetic continuation paths.
    """
    policy = policy or load_policy()
    ingress = policy.get("base_algorithm", {}).get("event_ingress", {})
    expected_sources = ["pull_request", "push", "DIRECT_AUTHORIZED_REQUEST"]
    forbidden_sources = [
        "schedule",
        "workflow_dispatch",
        "repository_dispatch",
        "api_workflow_dispatch",
        "polling",
        "retry_without_new_event",
    ]
    if not isinstance(ingress, dict):
        return {"native_only": False, "reason": "EVENT_INGRESS_MISSING"}
    workflow_path = ingress.get("workflow_path")
    if workflow_path != str(EVENT_INGRESS_WORKFLOW):
        return {"native_only": False, "reason": "EVENT_INGRESS_WORKFLOW_MISMATCH"}
    try:
        trigger_surface = EVENT_INGRESS_WORKFLOW.read_text(encoding="utf-8").split(
            "permissions:", 1
        )[0]
    except OSError:
        return {"native_only": False, "reason": "EVENT_INGRESS_WORKFLOW_MISSING"}
    expected_native_triggers = all(
        f"  {source}:" in trigger_surface for source in ("pull_request", "push")
    )
    forbidden_absent = all(token not in trigger_surface for token in forbidden_sources)
    native_only = (
        ingress.get("mode") == "EXACT_NATIVE_REPOSITORY_EVENT_ONLY"
        and ingress.get("accepted_sources") == expected_sources
        and ingress.get("forbidden_sources") == forbidden_sources
        and ingress.get("no_new_event_state")
        == "HOLD_UNVERIFIED_AWAIT_NEXT_NATIVE_EVENT"
        and ingress.get("synthetic_reentry") == "FORBIDDEN"
        and ingress.get("periodic_automation") == "FORBIDDEN"
        and expected_native_triggers
        and forbidden_absent
        and "/dispatches" not in trigger_surface
        and "sleep " not in trigger_surface
    )
    return {
        "native_only": native_only,
        "mode": ingress.get("mode"),
        "workflow_path": workflow_path,
        "accepted_sources": ingress.get("accepted_sources"),
        "forbidden_sources": ingress.get("forbidden_sources"),
        "reason": None if native_only else "EVENT_INGRESS_CONTRACT_MISMATCH",
    }



DEBUGGING_STAGES = (
    ("symptom", "CORRECT_FAILURE"),
    ("cause", "IDENTIFY_AND_CORRECT_CAUSE"),
    ("regression", "VERIFY_REGRESSION"),
    ("original_flow", "REOBSERVE_ORIGINAL_FLOW"),
)


def recursive_debugging_plan(inventory):
    """Validate a finite causal worklist; never execute payloads or grant authority.

    Input receipts must come from the existing authoritative observers. This
    reducer checks their declared bindings, not their authenticity. Historical
    red reproductions are never accepted as current-head green validation.
    """
    result = {
        "schema": "qikvrt_recursive_debugging_plan_v1",
        "state": "HOLD_INVENTORY_UNVERIFIED",
        "complete": False,
        "actions": [],
        "unresolved": [],
        "maximum_writers_per_subject": 1,
        "external_effect": "NONE",
        "universal_bug_freedom_claimed": False,
    }

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def subject_ok(value):
        return (
            isinstance(value, dict)
            and text(value.get("repository"))
            and all(
                isinstance(value.get(key), str)
                and len(value[key]) == 40
                and all(c in "0123456789abcdef" for c in value[key])
                for key in ("base_sha", "head_sha", "tree_sha")
            )
        )

    if not isinstance(inventory, dict):
        return result
    subject = inventory.get("subject")
    units = inventory.get("work_units")
    if (
        inventory.get("schema") != "qikvrt_recursive_debugging_inventory_v1"
        or not subject_ok(subject)
        or not text(inventory.get("scope"))
        or not text(inventory.get("inventory_receipt_id"))
        or not isinstance(units, list)
        or len(units) > 4096
    ):
        return result
    nodes = {}
    for unit in units:
        if not isinstance(unit, dict) or not text(unit.get("id")):
            return result
        if unit["id"] in nodes:
            return result
        if not text(unit.get("original_scope")) or not text(unit.get("observation_receipt_id")):
            return result
        for edge in ("blocked_by", "causes"):
            links = unit.get(edge)
            if not isinstance(links, list) or not all(text(x) for x in links) or len(set(links)) != len(links):
                return result
        if not isinstance(unit.get("receipts"), dict):
            return result
        nodes[unit["id"]] = unit

    # Kahn-style worklist: no Python recursion limit and no polling/retry loop.
    pending = set(nodes)
    closed = set()
    processed = set()
    while pending:
        ready = sorted(
            key for key in pending
            if set(nodes[key]["blocked_by"] + nodes[key]["causes"]) <= processed
        )
        if not ready:
            break
        for key in ready:
            unit = nodes[key]
            predecessor = unit["observation_receipt_id"]
            seen_receipts = {predecessor}
            action = None
            if not set(unit["blocked_by"]) <= closed:
                action = "HOLD_DEPENDENCY_OPEN"
            else:
                for stage, required_action in DEBUGGING_STAGES:
                    if stage == "cause" and not set(unit["causes"]) <= closed:
                        action = "HOLD_CAUSE_WORK_UNIT_OPEN"
                        break
                    receipt = unit["receipts"].get(stage)
                    exact = (
                        isinstance(receipt, dict)
                        and receipt.get("subject") == subject
                        and receipt.get("status") == "success"
                        and text(receipt.get("id"))
                        and receipt["id"] not in seen_receipts
                        and receipt.get("after") == predecessor
                    )
                    if exact and stage in {"symptom", "cause"}:
                        exact = text(receipt.get("effect_receipt_id"))
                    if exact and stage == "cause":
                        exact = text(receipt.get("mechanism"))
                    if exact and stage == "regression":
                        red = receipt.get("red")
                        exact = (
                            isinstance(red, dict)
                            and text(receipt.get("test_id"))
                            and red.get("test_id") == receipt["test_id"]
                            and red.get("status") == "failure"
                            and text(red.get("id"))
                            and red["id"] != receipt["id"]
                            and subject_ok(red.get("subject"))
                        )
                    if exact and stage == "original_flow":
                        exact = receipt.get("scope") == unit["original_scope"]
                    if not exact:
                        action = required_action
                        break
                    predecessor = receipt["id"]
                    seen_receipts.add(predecessor)
            if action is None:
                closed.add(key)
            else:
                result["unresolved"].append(key)
                result["actions"].append({"work_unit": key, "next_action": action})
            pending.remove(key)
            processed.add(key)
    for key in sorted(pending):
        result["unresolved"].append(key)
        result["actions"].append({
            "work_unit": key,
            "next_action": "HOLD_CAUSAL_GRAPH_CYCLE_OR_MISSING_DEPENDENCY",
        })
    result["actions"].sort(key=lambda item: item["work_unit"])
    result["unresolved"].sort()
    result["inventory_complete"] = inventory.get("inventory_complete") is True
    result["complete"] = result["inventory_complete"] and not result["unresolved"]
    result["state"] = (
        "NO_KNOWN_ERRORS_OR_BLOCKERS_IN_BOUND_SCOPE" if result["complete"]
        else "REPAIR_OBLIGATIONS_OPEN" if result["unresolved"]
        else "HOLD_INVENTORY_UNVERIFIED"
    )
    return result


def evaluate(observation, policy=None):
    policy = policy or load_policy()
    debugging = recursive_debugging_plan(observation.get("recursive_debugging_inventory"))
    required = {
        "exact_head_and_tree_bound": bool(observation.get("exact_head_and_tree_bound")),
        "known_deterministic_defects_zero": observation.get("known_deterministic_defects", 1) == 0,
        "repository_integrity_verifies": bool(observation.get("repository_integrity_verifies")),
        "bound_deterministic_gate_bundle_verifies": bool(observation.get("bound_deterministic_gate_bundle_verifies")),
        "repository_writer_lease_contract_verifies": bool(observation.get("repository_writer_lease_contract_verifies")),
        "stale_evidence_reuse_zero": observation.get("stale_evidence_reuse", 1) == 0,
        "registered_improvers_only": bool(observation.get("registered_improvers_only")),
        "reobserve_after_every_mutation": bool(observation.get("reobserve_after_every_mutation")),
        "full_tracked_tree_sha256_bound": bool(observation.get("full_tracked_tree_sha256_bound")),
    }
    if "recursive_debugging_inventory" in observation and not debugging["complete"]:
        required["known_deterministic_defects_zero"] = False
    missing = [k for k in policy["hard_invariants"] if not required.get(k, False)]
    if not missing:
        state = "ZERO_KNOWN_DETERMINISTIC_BUGS_LOCAL"
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
        "recursive_debugging": debugging,
        "local_gate_success_is_repair_completion": False,
        "platform_promotion_evidence_required": True,
        "universal_bug_freedom_claimed": False,
    }


def self_check(policy=None):
    policy = policy or load_policy()
    perfect = json.loads(PERFECT.read_text(encoding="utf-8"))
    registered = [x.get("id") for x in perfect.get("registered_improvers", [])]
    audit = policy.get("audit_surface", {})
    platform = policy.get("platform_promotion_surface", {})
    ingress = event_ingress_check(policy)
    return {
        "schema": "qikvrt_zero_bug_self_check_v1",
        "recursive_debugging_contract_bound": (
            policy.get("base_algorithm", {}).get("id") == "CORRECT_FAILURE_THEN_CAUSE_RECURSIVELY_V1"
            and policy["base_algorithm"].get("steps") == [step for _, step in DEBUGGING_STAGES]
        ),
        "complete": all(k in policy for k in ("schema", "hard_invariants", "state_machine", "repair_order", "continuous_revision", "audit_surface", "platform_promotion_surface")),
        "after_mutation": policy["state_machine"].get("after_mutation"),
        "after_fresh_local_exact_head_success": policy["state_machine"].get("after_fresh_local_exact_head_success"),
        "later_is_better": policy["continuous_revision"].get("later_is_better"),
        "arbitrary_unregistered_self_modification": policy["continuous_revision"].get("arbitrary_unregistered_self_modification"),
        "registered_improvers": registered,
        "required_peer_workflows": platform.get("required_peer_workflows", []),
        "writer_workflows": audit.get("writer_workflows", []),
        "bit_audit_algorithm": audit.get("bit_audit", {}).get("canonical_index_digest"),
        "event_ingress_mode": ingress.get("mode"),
        "event_ingress_native_only": ingress.get("native_only"),
        "event_ingress_reason": ingress.get("reason"),
    }


def derive_observation(args):
    bit = json.loads(Path(args.bit_audit).read_text(encoding="utf-8"))
    perfect = json.loads(PERFECT.read_text(encoding="utf-8"))
    registered = [x.get("id") for x in perfect.get("registered_improvers", [])]
    markers = {
        "regressions": Path(args.regressions_marker).is_file(),
        "integrity": Path(args.integrity_marker).is_file(),
        "full_tests": Path(args.tests_marker).is_file(),
        "writer_lease_contract": Path(args.writer_lease_marker).is_file(),
    }
    exact = (
        bit.get("head_sha") == args.head
        and bit.get("tree_sha") == args.tree
        and args.expected_head == args.head
    )
    registered_only = registered == ["integrity_trio_materializer"]
    bit_bound = (
        bit.get("hash_algorithm") == "sha256"
        and bit.get("source") == "git_object_database"
        and isinstance(bit.get("canonical_index_sha256"), str)
        and len(bit.get("canonical_index_sha256", "")) == 64
    )
    local_bundle = markers["regressions"] and markers["integrity"] and markers["full_tests"]
    known_defects = 0 if local_bundle and markers["writer_lease_contract"] else 1
    observation = {
        "exact_head_and_tree_bound": exact,
        "known_deterministic_defects": known_defects,
        "repository_integrity_verifies": markers["integrity"],
        "bound_deterministic_gate_bundle_verifies": local_bundle,
        "repository_writer_lease_contract_verifies": markers["writer_lease_contract"],
        "stale_evidence_reuse": 0 if bit.get("head_sha") == args.head else 1,
        "registered_improvers_only": registered_only,
        "reobserve_after_every_mutation": exact,
        "full_tracked_tree_sha256_bound": bit_bound,
        "evidence_incomplete": not all(markers.values()) or not exact or not bit_bound,
        "evidence": {
            "head_sha": args.head,
            "tree_sha": args.tree,
            "bit_audit_canonical_index_sha256": bit.get("canonical_index_sha256"),
            "tracked_entry_count": bit.get("entry_count"),
            "tracked_blob_bytes": bit.get("tracked_blob_bytes"),
            "local_command_markers": markers,
            "registered_improvers": registered,
            "platform_promotion_evidence": "SEPARATE_REQUIRED",
        },
    }
    return observation


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-check", action="store_true")
    p.add_argument("--observation")
    p.add_argument("--derive", action="store_true")
    p.add_argument("--repair-inventory", help="Evaluate retained exact recursive repair receipts; no effects")
    p.add_argument("--head")
    p.add_argument("--tree")
    p.add_argument("--expected-head")
    p.add_argument("--bit-audit")
    p.add_argument("--regressions-marker")
    p.add_argument("--integrity-marker")
    p.add_argument("--tests-marker")
    p.add_argument("--writer-lease-marker")
    p.add_argument("--write-observation")
    args = p.parse_args()
    if args.repair_inventory:
        result = recursive_debugging_plan(json.loads(Path(args.repair_inventory).read_text(encoding="utf-8")))
        ok = result["complete"]
    elif args.self_check:
        result = self_check()
        ok = (
            result["complete"]
            and result["recursive_debugging_contract_bound"]
            and result["after_mutation"] == "HOLD_UNVERIFIED"
            and result["after_fresh_local_exact_head_success"] == "ZERO_KNOWN_DETERMINISTIC_BUGS_LOCAL"
            and result["later_is_better"] is False
            and result["bit_audit_algorithm"] == "sha256"
            and result["registered_improvers"] == ["integrity_trio_materializer"]
            and result["event_ingress_native_only"] is True
        )
    else:
        if args.derive:
            required_args = [args.head, args.tree, args.expected_head, args.bit_audit, args.regressions_marker, args.integrity_marker, args.tests_marker, args.writer_lease_marker]
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
        ok = result["state"] == "ZERO_KNOWN_DETERMINISTIC_BUGS_LOCAL"
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
