            raise OrchestratorBlock("candidate file response lacks filename")
        result.append(filename)
    return sorted(result)


def successful_exact_head_status(client: GitHubClient, sha: str) -> bool:
    statuses = client.paged(f"/commits/{sha}/statuses")
    matching = [item for item in statuses if item.get("context") == STATUS_CONTEXT]
    if not matching:
        return False
    latest = max(matching, key=lambda item: item.get("created_at") or "")
    return latest.get("state") == "success"


def known_writer_runs(
    client: GitHubClient, contract: Mapping[str, Any], current_run_id: str | None
) -> list[dict[str, Any]]:
    data = client.json("GET", "/actions/runs?status=in_progress&per_page=100")
    if not isinstance(data, Mapping) or not isinstance(data.get("workflow_runs"), list):
        raise OrchestratorBlock("in-progress workflow response is malformed")
    fragments = [
        value.lower()
        for value in contract["global_writer_lease"]["known_writer_workflow_name_fragments"]
    ]
    result = []
    for run_value in data["workflow_runs"]:
        if current_run_id and str(run_value.get("id")) == str(current_run_id):
            continue
        name = str(run_value.get("name") or "").lower()
        if any(fragment in name for fragment in fragments):
            result.append(
                {
                    "id": run_value.get("id"),
                    "name": run_value.get("name"),
                    "head_sha": run_value.get("head_sha"),
                    "event": run_value.get("event"),
                }
            )
    return result


def promote(*, execute: bool) -> dict[str, Any]:
    _delegation, contract, _queue, promotion = load_state()
    client = GitHubClient(str(contract["authority_repository"]))
    if not client.token:
        raise OrchestratorBlock("GitHub token is required for promotion observation")
    candidates = open_orchestrator_candidates(client)
    if not candidates:
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "NO_OPEN_CANDIDATE",
            "external_effect": "NONE",
        }
    if len(candidates) != 1:
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "BLOCKED_MULTIPLE_OPEN_CANDIDATES",
            "candidates": [candidate.__dict__ for candidate in candidates],
            "external_effect": "NONE",
        }
    candidate = candidates[0]
    main_first = client.json("GET", "/branches/main")
    if not isinstance(main_first, Mapping):
        raise OrchestratorBlock("main branch response is malformed")
    main_sha = require_sha(main_first.get("commit", {}).get("sha"), HEX40, "current main")
    if main_sha != candidate.base_sha:
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "BLOCKED_BASE_DRIFT",
            "candidate": candidate.__dict__,
            "current_main": main_sha,
            "external_effect": "NONE",
        }
    delay = int(contract["global_writer_lease"].get("double_observe_main_seconds", 2))
    time.sleep(max(0, min(delay, 10)))
    pr_second = client.json("GET", f"/pulls/{candidate.pr_number}")
    main_second = client.json("GET", "/branches/main")
    if pr_second.get("head", {}).get("sha") != candidate.head_sha:
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "BLOCKED_HEAD_MOVED",
            "candidate": candidate.__dict__,
            "external_effect": "NONE",
        }
    if main_second.get("commit", {}).get("sha") != main_sha:
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "BLOCKED_MAIN_MOVED",
            "candidate": candidate.__dict__,
            "external_effect": "NONE",
        }
    _candidate_queue, unit = candidate_queue_and_unit(client, candidate)
    if unit.get("effect_class") != promotion.get("allowed_effect_class"):
        raise OrchestratorBlock("candidate effect class is not promotable")
    if unit.get("handler") not in promotion.get("allowed_handlers", []):
        raise OrchestratorBlock("candidate handler is not promotable")
    paths = candidate_files(client, candidate.pr_number)
    unexpected = [path for path in paths if not path_allowed(path, unit["allowed_paths"])]
    if unexpected:
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "BLOCKED_DIFF_NOT_ALLOWLISTED",
            "candidate": candidate.__dict__,
            "unexpected_paths": unexpected,
            "external_effect": "NONE",
        }
    if not successful_exact_head_status(client, candidate.head_sha):
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "WAITING_EXACT_HEAD_GATE",
            "candidate": candidate.__dict__,
            "external_effect": "NONE",
        }
    competing = known_writer_runs(
        client, contract, os.environ.get("GITHUB_RUN_ID")
    )
    if competing:
        return {
            "schema": "qikvrt_autonomous_promotion_result_v2",
            "state": "WAITING_COMPETING_WRITER",
            "candidate": candidate.__dict__,
            "competing_writers": competing,
            "external_effect": "NONE",
        }
    result = {
        "schema": "qikvrt_autonomous_promotion_result_v2",
        "state": "ELIGIBLE_FOR_EXPECTED_HEAD_PROMOTION",
        "candidate": candidate.__dict__,
        "changed_paths": paths,
        "conditions": list(PROMOTION_CONDITIONS),
        "external_effect": "NONE",
        "completion_claims": contract["completion_claims"],
    }
    if not execute:
        return result
    merged = client.json(
        "PUT",
        f"/pulls/{candidate.pr_number}/merge",
        payload={
            "sha": candidate.head_sha,
            "merge_method": "merge",
            "commit_title": f"Merge autonomous work unit {candidate.work_unit_id}",
            "commit_message": (
                "Expected-head-bound repository-internal promotion. "
                "No external effect, PASS, FINAL_PASS, or EFFECT_ACK_DONE is claimed."
            ),
        },
        expected=(200,),
    )
    if not isinstance(merged, Mapping) or merged.get("merged") is not True:
        raise OrchestratorBlock(f"GitHub did not merge candidate: {merged}")
    result.update(
        {
            "state": "MERGED",
            "merge_commit_sha": merged.get("sha"),
            "repository_mutation": "EXPECTED_HEAD_BOUND_MERGE",
        }
    )
    return result


def validate_only() -> dict[str, Any]:
    _delegation, contract, queue, promotion = load_state()
    index = validate_queue(queue, contract)
    selected = select_work_unit(queue, contract)
    return {
        "schema": "qikvrt_autonomous_orchestrator_validation_v2",
        "state": "VALID",
        "contract_id": contract["contract_id"],
        "queue_id": queue["queue_id"],
        "queue_revision": queue["revision"],
        "work_units": len(index),
        "queue_summary": queue_summary(queue),
        "next_eligible_work_unit": selected["id"] if selected else None,
        "promotion_contract": promotion["contract_id"],
        "external_effect": "NONE",
        "completion_claims": contract["completion_claims"],
    }


def print_json(value: Any) -> None:
    print(canonical_json(value), end="")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("plan")
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--work-unit")
    diff_parser = sub.add_parser("validate-diff")
    diff_parser.add_argument("--work-unit", required=True)
    diff_parser.add_argument("--base-ref", default="HEAD^")
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            result = validate_only()
        elif args.command == "plan":
            result = plan()
        elif args.command == "apply":
            result = apply_one(args.work_unit)
        elif args.command == "validate-diff":
            result = validate_diff(args.work_unit, args.base_ref)
        elif args.command == "promote":
            result = promote(execute=args.execute)
        else:  # pragma: no cover
            raise OrchestratorBlock(f"unknown command: {args.command}")
    except (
        OrchestratorBlock,
        OSError,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ) as exc:
