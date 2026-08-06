        raise OrchestratorBlock("orchestrator promotion boundary differs")
    lease = value.get("global_writer_lease", {})
    if lease.get("maximum_parallel_orchestrator_writers") != 1:
        raise OrchestratorBlock("orchestrator writer lease is not singular")
    if lease.get("cancel_in_progress") is not False:
        raise OrchestratorBlock("orchestrator must not cancel an active writer")
    if lease.get("require_no_other_open_orchestrator_candidate") is not True:
        raise OrchestratorBlock("orchestrator candidate serialization is disabled")
    policy = value.get("promotion_policy", {})
    delegation_policy = delegation.get("promotion_policy", {})
    if policy.get("conditions") != list(PROMOTION_CONDITIONS):
        raise OrchestratorBlock("orchestrator promotion conditions differ")
    if policy.get("conditions") != delegation_policy.get("conditions"):
        raise OrchestratorBlock("orchestrator and delegation promotion conditions differ")
    if policy.get("unconditional_automatic_merge") != "FORBIDDEN":
        raise OrchestratorBlock("orchestrator permits unconditional automatic merge")
    if policy.get("general_auto_merge_authorization") is not False:
        raise OrchestratorBlock("orchestrator general auto-merge authorization differs")
    effect_classes = value.get("effect_classes")
    if not isinstance(effect_classes, Mapping):
        raise OrchestratorBlock("effect-class map is absent")
    for name in ("HUMAN_JUDGMENT", "EXTERNAL_IRREVERSIBLE", "EMPIRICAL_REAL_WORLD"):
        if effect_classes.get(name, {}).get("automatic") is not False:
            raise OrchestratorBlock(f"{name} must not be automatic")
    if effect_classes.get("REPOSITORY_REVERSIBLE", {}).get("automatic") is not True:
        raise OrchestratorBlock("repository-reversible work must be automatic")
    if effect_classes.get("REPOSITORY_REVERSIBLE", {}).get("promotion") is not True:
        raise OrchestratorBlock("repository-reversible promotion is disabled")
    handlers = value.get("handlers")
    if not isinstance(handlers, Mapping) or not handlers:
        raise OrchestratorBlock("handler map is absent")
    for handler_name, handler in handlers.items():
        if not isinstance(handler, Mapping):
            raise OrchestratorBlock(f"handler {handler_name} is malformed")
        effect = handler.get("effect_class")
        if effect not in effect_classes:
            raise OrchestratorBlock(f"handler {handler_name} has unknown effect class")
        if handler.get("automatic") is True and effect_classes[effect].get("automatic") is not True:
            raise OrchestratorBlock(f"handler {handler_name} crosses an automatic boundary")
    require_false_claims(value.get("completion_claims"), "orchestrator contract")


def validate_promotion_contract(value: Mapping[str, Any]) -> None:
    if value.get("schema") != "qikvrt_autonomous_work_unit_promotion_contract_v2":
        raise OrchestratorBlock("work-unit promotion contract schema mismatch")
    if value.get("allowed_effect_class") != "REPOSITORY_REVERSIBLE":
        raise OrchestratorBlock("work-unit promotion effect class differs")
    if value.get("conditions") != list(PROMOTION_CONDITIONS):
        raise OrchestratorBlock("work-unit promotion conditions differ")
    if STATUS_CONTEXT not in value.get("required_gates", []):
        raise OrchestratorBlock("exact-head status context is not required")
    require_false_claims(value.get("completion_claims"), "work-unit promotion contract")


def validate_queue(
    queue: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Mapping[str, Any]]:
    if queue.get("schema") != "qikvrt_autonomous_work_queue_v2":
        raise OrchestratorBlock("work queue schema mismatch")
    if queue.get("contract_id") != contract.get("contract_id"):
        raise OrchestratorBlock("work queue contract binding mismatch")
    if queue.get("authority_repository") != contract.get("authority_repository"):
        raise OrchestratorBlock("work queue authority mismatch")
    if not isinstance(queue.get("revision"), int) or queue["revision"] < 1:
        raise OrchestratorBlock("work queue revision is invalid")
    units = queue.get("work_units")
    if not isinstance(units, list) or not units:
        raise OrchestratorBlock("work queue has no work units")
    states = set(contract.get("states", []))
    handlers = contract.get("handlers", {})
    effects = contract.get("effect_classes", {})
    index: dict[str, Mapping[str, Any]] = {}
    for unit in units:
        if not isinstance(unit, Mapping):
            raise OrchestratorBlock("work unit is not an object")
        identifier = unit.get("id")
        if not isinstance(identifier, str) or WORK_UNIT_ID.fullmatch(identifier) is None:
            raise OrchestratorBlock(f"invalid work-unit id: {identifier!r}")
        if identifier in index:
            raise OrchestratorBlock(f"duplicate work-unit id: {identifier}")
        index[identifier] = unit
        if unit.get("state") not in states:
            raise OrchestratorBlock(f"work unit {identifier} has unknown state")
        handler_name = unit.get("handler")
        if handler_name not in handlers:
            raise OrchestratorBlock(f"work unit {identifier} has unknown handler")
        effect_class = unit.get("effect_class")
        if effect_class not in effects:
            raise OrchestratorBlock(f"work unit {identifier} has unknown effect class")
        if handler_name in handlers and handlers[handler_name].get("effect_class") != effect_class:
            # Waiting boundary units may reuse a materialization handler name, but must
            # never become READY while the effect classes differ.
            if unit.get("state") == "READY":
                raise OrchestratorBlock(
                    f"READY work unit {identifier} handler/effect mismatch"
                )
        attempts = unit.get("attempts")
        maximum = unit.get("max_attempts")
        if not isinstance(attempts, int) or attempts < 0:
            raise OrchestratorBlock(f"work unit {identifier} attempts are invalid")
        if not isinstance(maximum, int) or maximum < 1 or attempts > maximum:
            raise OrchestratorBlock(f"work unit {identifier} attempt limit is invalid")
        dependencies = unit.get("dependencies")
        if not isinstance(dependencies, list) or any(
            not isinstance(item, str) for item in dependencies
        ):
            raise OrchestratorBlock(f"work unit {identifier} dependencies are invalid")
        if len(dependencies) != len(set(dependencies)) or identifier in dependencies:
            raise OrchestratorBlock(f"work unit {identifier} dependency set is invalid")
        allowed_paths = unit.get("allowed_paths")
        if not isinstance(allowed_paths, list) or any(
            not isinstance(item, str) or not item for item in allowed_paths
        ):
            raise OrchestratorBlock(f"work unit {identifier} allowlist is invalid")
        if unit.get("state") == "READY":
            if effects[effect_class].get("automatic") is not True:
                raise OrchestratorBlock(
                    f"work unit {identifier} is READY across a non-automatic boundary"
                )
            if handlers[handler_name].get("automatic") is not True:
                raise OrchestratorBlock(f"work unit {identifier} handler is not automatic")
            promotion = unit.get("promotion")
            if effect_class == "REPOSITORY_REVERSIBLE":
                if not isinstance(promotion, Mapping) or promotion.get("allowed") is not True:
                    raise OrchestratorBlock(
                        f"work unit {identifier} lacks bounded promotion authorization"
                    )
        if unit.get("state") == "WAITING_HUMAN" and effect_class != "HUMAN_JUDGMENT":
            raise OrchestratorBlock(f"work unit {identifier} human state/effect mismatch")
        if (
            unit.get("state") == "WAITING_EXTERNAL_AUTH"
            and effect_class != "EXTERNAL_IRREVERSIBLE"
        ):
            raise OrchestratorBlock(f"work unit {identifier} external state/effect mismatch")
        if (
            unit.get("state") == "WAITING_EMPIRICAL"
            and effect_class != "EMPIRICAL_REAL_WORLD"
        ):
            raise OrchestratorBlock(f"work unit {identifier} empirical state/effect mismatch")
        if (
            unit.get("state") == "WAITING_CONFIGURATION"
            and effect_class != "REPOSITORY_CROSS_REPOSITORY"
        ):
            raise OrchestratorBlock(
                f"work unit {identifier} configuration state/effect mismatch"
            )
    for identifier, unit in index.items():
        missing = sorted(set(unit["dependencies"]) - set(index))
        if missing:
