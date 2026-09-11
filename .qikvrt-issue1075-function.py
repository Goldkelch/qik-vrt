def _active_writer_observation(
    repository: str,
    current_run_id: int,
    writer_names: set[str],
    relevant_heads: set[str],
) -> list[dict[str, Any]]:
    """Observe active writer projections without enumerating completed history.

    At most two literal heads (candidate and trusted main), five active states,
    and one complete page per head/state: at most ten serial reads. A partial
    page, escaped binding, duplicate run, or API/quota error fails closed; no
    history fallback, pagination, retry, or predecessor evidence is permitted.
    This observation is not a writer lock. Existing pre-effect exact-subject
    reobservation and writer admission boundaries remain mandatory.
    """
    if (
        not isinstance(repository, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository)
        is None
    ):
        raise ReviewObservationError("active writer repository binding is invalid")
    if (
        isinstance(current_run_id, bool)
        or not isinstance(current_run_id, int)
        or current_run_id < 1
    ):
        raise ReviewObservationError("active writer current run binding is invalid")
    if (
        not isinstance(writer_names, set)
        or not writer_names
        or any(not isinstance(name, str) or not name for name in writer_names)
    ):
        raise ReviewObservationError("active writer workflow binding is invalid")
    if (
        not isinstance(relevant_heads, set)
        or not 1 <= len(relevant_heads) <= 2
        or any(_git_sha1(value) is None for value in relevant_heads)
    ):
        raise ReviewObservationError("active writer relevant-head binding is invalid")

    observed: dict[int, dict[str, Any]] = {}
    seen: set[int] = set()
    for head in sorted(relevant_heads):
        encoded_head = urllib.parse.quote(head, safe="")
        for status in ACTIVE_WRITER_STATES:
            # Filter before applying the cardinality/completeness bound.
            # Completed historical runs must never consume this page budget.
            response = _gh_one(
                f"repos/{repository}/actions/runs?head_sha={encoded_head}"
                f"&status={status}&per_page=100&page=1"
            )
            if not isinstance(response, Mapping):
                raise ReviewObservationError("active writer workflow-run response is malformed")
            total = response.get("total_count")
            raw_runs = response.get("workflow_runs")
            if (
                isinstance(total, bool)
                or not isinstance(total, int)
                or total < 0
                or not isinstance(raw_runs, list)
                or len(raw_runs) > 100
                or total != len(raw_runs)
            ):
                raise ReviewObservationError(
                    "active writer exact-head workflow-run page is incomplete"
                    f" (status={status})"
                )
            for run in raw_runs:
                if not isinstance(run, Mapping):
                    raise ReviewObservationError("active writer workflow run is malformed")
                if run.get("head_sha") != head:
                    raise ReviewObservationError(
                        "active writer workflow run escaped exact-head binding"
                    )
                if run.get("status") != status:
                    raise ReviewObservationError(
                        "active writer workflow run escaped active-state binding"
                    )
                run_id = run.get("id")
                name = run.get("name")
                if (
                    isinstance(run_id, bool)
                    or not isinstance(run_id, int)
                    or run_id < 1
                ):
                    raise ReviewObservationError("active writer run id is invalid")
                if not isinstance(name, str) or not name:
                    raise ReviewObservationError("active writer workflow name is invalid")
                if run_id in seen:
                    # A duplicate cannot prove page completeness. Across
                    # states it also exposes observation-time state drift.
                    raise ReviewObservationError("active writer duplicate run observation")
                seen.add(run_id)
                # Validate all rows before excluding self or non-writers.
                if run_id == current_run_id or name not in writer_names:
                    continue
                observed[run_id] = {
                    "id": run_id,
                    "name": name,
                    "status": status,
                    "head_sha": head,
                    "workflow_id": run.get("workflow_id"),
                    "path": run.get("path"),
                    "event": run.get("event"),
                    "run_number": run.get("run_number"),
                    "run_attempt": run.get("run_attempt", 1),
                }
    return sorted(observed.values(), key=lambda item: (str(item["name"]), item["id"]))
