            "PHYSICAL_CLOSURE": False,
            "EMPIRICAL_CONFIRMATION": False,
        },
    }
    write_json(path, value)
    return path


def apply_one(identifier: str | None = None) -> dict[str, Any]:
    ensure_clean_worktree()
    _delegation, contract, queue, promotion = load_state()
    base_sha = observed_head()
    selected = find_unit(queue, identifier) if identifier else select_work_unit(queue, contract)
    if selected is None:
        return {
            "schema": "qikvrt_autonomous_orchestrator_result_v2",
            "state": "NO_ELIGIBLE_AUTOMATIC_WORK",
            "observed_base_sha": base_sha,
            "queue_revision": queue["revision"],
            "queue_summary": queue_summary(queue),
            "external_effect": "NONE",
            "completion_claims": contract["completion_claims"],
        }
    if selected["state"] != "READY":
        raise OrchestratorBlock(f"selected work unit is not READY: {selected['id']}")
    index = {item["id"]: item for item in queue["work_units"]}
    if not all(index[item]["state"] in TERMINAL_DEPENDENCY_STATES for item in selected["dependencies"]):
        raise OrchestratorBlock("selected work-unit dependencies are not terminal")
    if selected["effect_class"] != promotion["allowed_effect_class"]:
        raise OrchestratorBlock("selected work unit is outside the promotion effect class")
    if selected["handler"] not in promotion["allowed_handlers"]:
        raise OrchestratorBlock("selected handler is outside the promotion contract")
    handler = HANDLERS.get(selected["handler"])
    if handler is None:
        raise OrchestratorBlock(f"handler is not implemented: {selected['handler']}")
    branch = candidate_branch(selected["id"], base_sha)
    client = GitHubClient(str(contract["authority_repository"]))
    handler_result = handler(selected, contract, client)
    mutable = find_unit(queue, selected["id"])
    mutable["attempts"] += 1
    mutable["state"] = contract["handlers"][selected["handler"]]["final_state_after_promotion"]
    mutable["last_result"] = {
        "candidate_state": "MATERIALIZED_PENDING_PROMOTION",
        "observed_base_sha": base_sha,
        "candidate_branch": branch,
        "handler_result": handler_result,
    }
    queue["revision"] += 1
    write_json(QUEUE_PATH, queue)
    receipt = materialize_receipt(
        selected, base_sha=base_sha, branch=branch, result=handler_result
    )
    paths = changed_paths("HEAD")
    allowed = list(selected["allowed_paths"])
    unexpected = [path for path in paths if not path_allowed(path, allowed)]
    if unexpected:
        raise OrchestratorBlock(f"handler produced non-allowlisted paths: {unexpected}")
    fingerprint = semantic_fingerprint(paths)
    return {
        "schema": "qikvrt_autonomous_orchestrator_result_v2",
        "state": "CANDIDATE_READY",
        "work_unit_id": selected["id"],
        "handler": selected["handler"],
        "effect_class": selected["effect_class"],
        "observed_base_sha": base_sha,
        "candidate_branch": branch,
        "semantic_fingerprint": fingerprint,
        "changed_paths": paths,
        "receipt_path": receipt.relative_to(ROOT).as_posix(),
        "handler_result": handler_result,
        "external_effect": "NONE",
        "promotion_conditions": list(PROMOTION_CONDITIONS),
        "completion_claims": contract["completion_claims"],
    }


def open_orchestrator_candidates(client: GitHubClient) -> list[Candidate]:
    pulls = client.paged("/pulls?state=open&sort=created&direction=asc")
    candidates: list[Candidate] = []
    for pr in pulls:
        branch = pr.get("head", {}).get("ref")
        if not isinstance(branch, str) or not branch.startswith("automation/orchestrator-"):
            continue
        head_sha = pr.get("head", {}).get("sha")
        base_sha = pr.get("base", {}).get("sha")
        body = pr.get("body") or ""
        match = re.search(r"(?m)^Work unit:\s*`(AUT-[A-Z0-9-]+)`\s*$", body)
        if not match:
            raise OrchestratorBlock(f"orchestrator PR #{pr.get('number')} lacks work-unit binding")
        candidates.append(
            Candidate(
                pr_number=int(pr["number"]),
                head_branch=branch,
                head_sha=require_sha(head_sha, HEX40, "candidate head"),
                base_sha=require_sha(base_sha, HEX40, "candidate base"),
                work_unit_id=match.group(1),
            )
        )
    return candidates


def plan() -> dict[str, Any]:
    _delegation, contract, queue, _promotion = load_state()
    base_sha = observed_head()
    client = GitHubClient(str(contract["authority_repository"]))
    candidates: list[Candidate] = []
    if client.token:
        candidates = open_orchestrator_candidates(client)
    if len(candidates) > 1:
        return {
            "schema": "qikvrt_autonomous_orchestrator_plan_v2",
            "state": "BLOCKED_MULTIPLE_OPEN_CANDIDATES",
            "observed_base_sha": base_sha,
            "candidates": [candidate.__dict__ for candidate in candidates],
            "queue_summary": queue_summary(queue),
            "external_effect": "NONE",
        }
    if candidates:
        return {
            "schema": "qikvrt_autonomous_orchestrator_plan_v2",
            "state": "CANDIDATE_EXISTS",
            "observed_base_sha": base_sha,
            "candidate": candidates[0].__dict__,
            "queue_summary": queue_summary(queue),
            "external_effect": "NONE",
        }
    selected = select_work_unit(queue, contract)
    if selected is None:
        waiting = [
            {
                "id": item["id"],
                "state": item["state"],
                "effect_class": item["effect_class"],
                "title": item["title"],
            }
            for item in queue["work_units"]
            if item["state"] in WAITING_STATES or item["state"] == "BLOCKED"
        ]
        return {
            "schema": "qikvrt_autonomous_orchestrator_plan_v2",
            "state": "NO_ELIGIBLE_AUTOMATIC_WORK",
            "observed_base_sha": base_sha,
            "queue_revision": queue["revision"],
            "queue_summary": queue_summary(queue),
            "waiting_boundaries": waiting,
            "external_effect": "NONE",
        }
    return {
        "schema": "qikvrt_autonomous_orchestrator_plan_v2",
        "state": "READY",
        "observed_base_sha": base_sha,
        "work_unit_id": selected["id"],
        "handler": selected["handler"],
        "effect_class": selected["effect_class"],
        "candidate_branch": candidate_branch(selected["id"], base_sha),
        "priority": selected["priority"],
        "dependencies": selected["dependencies"],
        "queue_revision": queue["revision"],
        "queue_summary": queue_summary(queue),
        "external_effect": "NONE",
    }


def validate_diff(identifier: str, base_ref: str = "HEAD^") -> dict[str, Any]:
    _delegation, contract, queue, _promotion = load_state()
    unit = find_unit(queue, identifier)
    paths = changed_paths(base_ref)
    unexpected = [path for path in paths if not path_allowed(path, unit["allowed_paths"])]
    if unexpected:
        raise OrchestratorBlock(f"candidate diff has non-allowlisted paths: {unexpected}")
    return {
        "state": "DIFF_ALLOWLISTED",
        "work_unit_id": identifier,
        "base_ref": base_ref,
        "changed_paths": paths,
        "semantic_fingerprint": semantic_fingerprint(paths) if paths else None,
        "external_effect": "NONE",
        "completion_claims": contract["completion_claims"],
    }


def candidate_queue_and_unit(
    client: GitHubClient, candidate: Candidate
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    queue = client.file_json("state/autonomy/WORK_QUEUE_V2.json", candidate.head_sha)
    contract = client.file_json("state/autonomy/AUTONOMOUS_ORCHESTRATOR_V2.json", candidate.head_sha)
    index = validate_queue(queue, contract)
    unit = index.get(candidate.work_unit_id)
    if unit is None:
        raise OrchestratorBlock("candidate queue lacks bound work unit")
    if unit.get("state") != "DONE":
        raise OrchestratorBlock("candidate work unit is not DONE in candidate state")
    last = unit.get("last_result", {})
    if last.get("observed_base_sha") != candidate.base_sha:
        raise OrchestratorBlock("candidate work-unit base binding mismatch")
    if last.get("candidate_branch") != candidate.head_branch:
        raise OrchestratorBlock("candidate work-unit branch binding mismatch")
    return queue, unit


def candidate_files(client: GitHubClient, number: int) -> list[str]:
    files = client.paged(f"/pulls/{number}/files")
    result = []
    for item in files:
        filename = item.get("filename")
        if not isinstance(filename, str):
