#!/usr/bin/env python3
"""Validate a reduced issue-agent candidate without granting effect authority."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.issue_agent.binding import canonical_bytes, json_loads_strict, validate_request
from scripts.issue_agent.epoch import verify_reduction
from scripts.issue_agent.handlers import (
    AMBIGUOUS_MARKER_HANDLER_ID,
    UNTRUSTED_MARKER_HANDLER_ID,
    UNTRUSTED_UNTYPED_HANDLER_ID,
    descriptor_sha256,
    external_failure_descriptor,
    external_failure_state,
    marker_state,
    model_descriptor,
    reject_descriptor,
    unavailable_descriptor,
)
from scripts.issue_agent.infer import SYSTEM_PROMPT


REQUIRED = (
    "REQUEST.json",
    "REQUEST.sha256",
    "EVENT.json",
    "EVENT.sha256",
    "CONTEXT.md",
    "ANSWER.md",
    "EVALUATION.json",
    "EVALUATION.sha256",
    "STATUS.json",
    "WORK_EPOCH.json",
    "WORK_EPOCH.sha256",
    "MATRIX.json",
    "MATRIX.sha256",
    "LANE_RECEIPTS.json",
    "LANE_RECEIPTS.sha256",
    "FANIN.json",
    "FANIN.sha256",
)
ALLOWED_DISPOSITIONS = {
    "EXECUTE_NOW",
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}
CLOSURE_DISPOSITIONS = {
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}
TRUSTED_EVALUATION_MODES = {
    "MODEL_INFERENCE",
    "DETERMINISTIC_OWNER_CONTRACT",
    "DETERMINISTIC_REJECT",
    "EXTERNAL_AGENT_FAILURE",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SEMANTIC_SECTIONS = (
    "Issue disposition",
    "Disposition reason",
    "Required next action",
    "Gate result",
    "Evaluation mode",
    "Handler id",
    "Handler SHA-256",
    "Request fingerprint",
)
STATUS_KEYS = {
    "schema",
    "status",
    "issue_materialized",
    "model_inference_completed",
    "deterministic_contract_completed",
    "evaluation_completed",
    "evaluation_mode",
    "handler_id",
    "handler_sha256",
    "request_fingerprint",
    "issue_disposition",
    "disposition_reason",
    "next_action",
    "closure_recommended",
    "automatic_issue_close",
    "automatic_merge",
    "mirror_sync_required",
    "common_tag_required",
    "generated_at",
    "no_false_pass",
    "claims",
    "authority_next_action",
    "terminal_candidate_classified_at",
    "validated_disposition_at",
}
FALSE_CLAIMS = {
    "PASS": False,
    "FINAL_PASS": False,
    "EFFECT_ACK_DONE": False,
    "MERGE": False,
    "ISSUE_CLOSE": False,
    "MIRROR_SYNC": False,
    "TAG": False,
    "PUBLICATION": False,
    "DEPLOYMENT": False,
}


def section(markdown: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(title)}\s*$\n(.*?)(?=^##\s+|\Z)",
        markdown,
    )
    return match.group(1).strip() if match else ""


def section_count(markdown: str, title: str) -> int:
    return len(re.findall(rf"(?m)^##\s+{re.escape(title)}\s*$", markdown))


def verify_named_digest(directory: Path, name: str) -> str:
    path = directory / name
    sidecar = directory / f"{Path(name).stem}.sha256"
    fields = sidecar.read_text(encoding="utf-8").strip().split()
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if len(fields) != 2 or fields != [actual, name]:
        raise SystemExit(f"{Path(name).stem.upper()}_SHA256_MISMATCH")
    return actual


def _load_policy(*, verify_authority: bool, request: dict) -> dict:
    if verify_authority:
        head = request["binding"]["authority_head"]
        policy_bytes = subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{head}:policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json"]
        )
    else:
        policy_bytes = (ROOT / "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json").read_bytes()
    policy = json_loads_strict(policy_bytes)
    if policy.get("schema") != "qikvrt_issue_agent_deterministic_intake_v1":
        raise SystemExit("INVALID_DETERMINISTIC_INTAKE_POLICY")
    return policy


def _expected_handler(
    status: dict,
    request: dict,
    policy: dict,
) -> tuple[dict, dict[str, str] | None]:
    mode = status.get("evaluation_mode")
    marker = marker_state(request, policy)
    failure = external_failure_state(request, policy)
    untrusted_untyped = not marker["markers"] and not marker["actor_trusted"]
    deterministic_route = bool(marker["markers"]) or untrusted_untyped or bool(
        failure["matched_signatures"] and failure["structured"]
    )
    fixed: dict[str, str] | None = None

    if mode == "DETERMINISTIC_OWNER_CONTRACT":
        if failure["matched_signatures"] and failure["structured"]:
            raise SystemExit("OWNER_ROUTE_MAY_NOT_OVERRIDE_EXTERNAL_FAILURE_ROUTE")
        if (
            len(marker["markers"]) != 1
            or len(marker["recognized"]) != 1
            or not marker["actor_trusted"]
            or not marker["selected_author_trusted"]
        ):
            raise SystemExit("DETERMINISTIC_OWNER_ROUTE_NOT_ESTABLISHED")
        descriptor = marker["recognized"][0]
        fixed = {
            "disposition": descriptor["disposition"],
            "reason": f"SCHEMA_MARKED_OWNER_WORK_ORDER_ADMITTED:{descriptor['handler_id']}",
            "next_action": descriptor["required_next_action"],
            "gate": "CONTINUE",
        }
    elif mode == "DETERMINISTIC_REJECT":
        if failure["matched_signatures"] and failure["structured"]:
            raise SystemExit("REJECT_ROUTE_MAY_NOT_OVERRIDE_EXTERNAL_FAILURE_ROUTE")
        markers = marker["markers"]
        if not markers and not marker["actor_trusted"]:
            descriptor = reject_descriptor(UNTRUSTED_UNTYPED_HANDLER_ID, [])
            fixed = {
                "disposition": "BLOCKED_WITH_NEXT_ACTION",
                "reason": "UNTYPED_REQUEST_ACTOR_NOT_AUTHORIZED",
                "next_action": "A trusted repository owner must explicitly reobserve and dispatch this untyped issue before optional model inference or candidate materialization.",
                "gate": "BLOCK",
            }
        elif not markers:
            raise SystemExit("DETERMINISTIC_REJECT_WITHOUT_OWNER_MARKER")
        elif not marker["actor_trusted"] or not marker["selected_author_trusted"]:
            descriptor = reject_descriptor(UNTRUSTED_MARKER_HANDLER_ID, markers)
            fixed = {
                "disposition": "BLOCKED_WITH_NEXT_ACTION",
                "reason": "OWNER_MARKER_ACTOR_NOT_AUTHORIZED",
                "next_action": "Obtain an exact marker event from a login authorized by the deterministic intake policy.",
                "gate": "BLOCK",
            }
        elif len(markers) != 1 or len(marker["recognized"]) != 1:
            descriptor = reject_descriptor(AMBIGUOUS_MARKER_HANDLER_ID, markers)
            fixed = {
                "disposition": "BLOCKED_WITH_NEXT_ACTION",
                "reason": "UNKNOWN_OR_AMBIGUOUS_OWNER_WORK_ORDER_MARKER",
                "next_action": "Use exactly one versioned marker registered by the current deterministic intake policy.",
                "gate": "BLOCK",
            }
        else:
            raise SystemExit("DETERMINISTIC_REJECT_CONFLICTS_WITH_REGISTERED_OWNER_ROUTE")
    elif mode == "EXTERNAL_AGENT_FAILURE":
        if not failure["matched_signatures"] or not failure["structured"]:
            raise SystemExit("EXTERNAL_FAILURE_PROVENANCE_NOT_ESTABLISHED")
        descriptor = external_failure_descriptor(failure["matched_signatures"])
        fixed = {
            "disposition": "BLOCKED_WITH_NEXT_ACTION",
            "reason": "EXTERNAL_AGENT_ADMISSION_FAILURE",
            "next_action": "Route the original typed owner work order through the deterministic repository handler; do not recursively treat this transport failure as a new semantic task.",
            "gate": "BLOCK",
        }
    elif mode == "MODEL_INFERENCE":
        if deterministic_route:
            raise SystemExit("MODEL_INFERENCE_MAY_NOT_OVERRIDE_DETERMINISTIC_ROUTE")
        model = policy.get("model_boundary", {}).get("optional_model")
        if not isinstance(model, str) or not model:
            raise SystemExit("OPTIONAL_MODEL_NOT_BOUND_BY_POLICY")
        descriptor = model_descriptor(
            model,
            hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        )
    elif mode == "UNAVAILABLE":
        if deterministic_route:
            raise SystemExit("UNAVAILABLE_MAY_NOT_REPLACE_DETERMINISTIC_ROUTE")
        descriptor = unavailable_descriptor()
        fixed = {
            "disposition": "BLOCKED_WITH_NEXT_ACTION",
            "reason": "MODEL_INFERENCE_UNAVAILABLE",
            "next_action": "Resume the bounded issue transaction when a trusted inference or deterministic work-unit path is available.",
            "gate": "BLOCK",
        }
    else:
        raise SystemExit("INVALID_EVALUATION_MODE")
    return descriptor, fixed


def validate(directory: Path, *, verify_authority: bool = True) -> None:
    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    if missing:
        raise SystemExit(f"Missing issue-agent artifacts: {', '.join(missing)}")
    actual_names = {path.name for path in directory.iterdir()}
    if actual_names != set(REQUIRED):
        unexpected = sorted(actual_names - set(REQUIRED))
        raise SystemExit(f"UNEXPECTED_ISSUE_AGENT_ARTIFACTS:{','.join(unexpected)}")
    if any(path.is_symlink() or not path.is_file() for path in directory.iterdir()):
        raise SystemExit("ISSUE_AGENT_ARTIFACTS_MUST_BE_REGULAR_FILES")

    verify_named_digest(directory, "REQUEST.json")
    verify_named_digest(directory, "EVENT.json")
    request = validate_request(
        json_loads_strict((directory / "REQUEST.json").read_text(encoding="utf-8")),
        repository_root=ROOT,
        verify_git=verify_authority,
    )
    fingerprint = request["request_fingerprint"]
    binding = request["binding"]
    if hashlib.sha256((directory / "CONTEXT.md").read_bytes()).hexdigest() != binding["context_sha256"]:
        raise SystemExit("CONTEXT_SHA256_MISMATCH")
    event = json_loads_strict((directory / "EVENT.json").read_text(encoding="utf-8"))
    if event != {
        "schema": "qikvrt_issue_agent_event_binding_v1",
        "binding": binding,
        "request_fingerprint": fingerprint,
    }:
        raise SystemExit("EVENT_REQUEST_BINDING_MISMATCH")

    answer_bytes = (directory / "ANSWER.md").read_bytes()
    answer = answer_bytes.decode("utf-8").strip()
    if not answer:
        raise SystemExit("EMPTY_ANSWER")
    for title in SEMANTIC_SECTIONS:
        if section_count(answer, title) != 1:
            raise SystemExit(f"ANSWER_{title.upper().replace(' ', '_').replace('-', '_')}_COUNT_INVALID")
    evaluation_digest = verify_named_digest(directory, "EVALUATION.json")
    if not HEX64.fullmatch(evaluation_digest):
        raise SystemExit("INVALID_EVALUATION_DIGEST")
    evaluation = json_loads_strict((directory / "EVALUATION.json").read_text(encoding="utf-8"))
    status = json_loads_strict((directory / "STATUS.json").read_text(encoding="utf-8"))
    if status.get("schema") != "qikvrt_issue_agent_status_v2":
        raise SystemExit("INVALID_STATUS_SCHEMA")
    if not set(status).issubset(STATUS_KEYS):
        raise SystemExit("STATUS_CONTAINS_UNREGISTERED_FIELDS")
    if status.get("request_fingerprint") != fingerprint:
        raise SystemExit("STATUS_REQUEST_FINGERPRINT_MISMATCH")
    if not isinstance(status.get("handler_id"), str) or not status["handler_id"].strip():
        raise SystemExit("MISSING_HANDLER_ID")
    handler_sha256 = status.get("handler_sha256")
    if not isinstance(handler_sha256, str) or not HEX64.fullmatch(handler_sha256):
        raise SystemExit("INVALID_HANDLER_SHA256")
    evaluation_mode = status.get("evaluation_mode")
    if evaluation_mode not in TRUSTED_EVALUATION_MODES | {"UNAVAILABLE"}:
        raise SystemExit("INVALID_EVALUATION_MODE")
    policy = _load_policy(verify_authority=verify_authority, request=request)
    expected_handler, fixed_semantics = _expected_handler(status, request, policy)
    if status.get("handler_id") != expected_handler["handler_id"]:
        raise SystemExit("HANDLER_ID_DIFFERS_FROM_CANONICAL_ROUTE")
    if handler_sha256 != descriptor_sha256(expected_handler):
        raise SystemExit("HANDLER_SHA256_DIFFERS_FROM_CANONICAL_ROUTE")
    evaluation_completed = status.get("evaluation_completed") is True
    if evaluation_completed is not (evaluation_mode in TRUSTED_EVALUATION_MODES):
        raise SystemExit("EVALUATION_COMPLETION_MODE_MISMATCH")
    if (status.get("model_inference_completed") is True) is not (evaluation_mode == "MODEL_INFERENCE"):
        raise SystemExit("MODEL_COMPLETION_MODE_MISMATCH")
    if (status.get("deterministic_contract_completed") is True) is not (
        evaluation_mode == "DETERMINISTIC_OWNER_CONTRACT"
    ):
        raise SystemExit("DETERMINISTIC_COMPLETION_MODE_MISMATCH")
    expected_evaluation = {
        "schema": "qikvrt_issue_agent_evaluation_binding_v1",
        "answer_sha256": hashlib.sha256(answer_bytes).hexdigest(),
        "evaluation_completed": evaluation_completed,
        "evaluation_mode": evaluation_mode,
        "handler_id": expected_handler["handler_id"],
        "handler_sha256": descriptor_sha256(expected_handler),
        "request_fingerprint": fingerprint,
    }
    if evaluation != expected_evaluation:
        raise SystemExit("EVALUATION_DIFFERS_FROM_CANONICAL_ANSWER_BINDING")

    gate = status.get("status")
    if gate not in {"TERMINAL_CANDIDATE", "CONTINUE", "BLOCK"}:
        raise SystemExit("INVALID_GATE_STATUS")
    disposition = status.get("issue_disposition")
    if disposition not in ALLOWED_DISPOSITIONS:
        raise SystemExit("INVALID_OR_MISSING_ISSUE_DISPOSITION")
    if not isinstance(status.get("disposition_reason"), str) or not status["disposition_reason"].strip():
        raise SystemExit("MISSING_DISPOSITION_REASON")
    if not isinstance(status.get("next_action"), str) or not status["next_action"].strip():
        raise SystemExit("MISSING_NEXT_ACTION")
    if disposition not in CLOSURE_DISPOSITIONS and status["next_action"].strip().upper() == "NONE":
        raise SystemExit("NON_CLOSURE_REQUIRES_NEXT_ACTION")
    if disposition == "EXECUTE_NOW" and evaluation_mode not in {"MODEL_INFERENCE", "DETERMINISTIC_OWNER_CONTRACT"}:
        raise SystemExit("EXECUTE_NOW_REQUIRES_TRUSTED_ADMISSION_EVALUATION")
    if status.get("closure_recommended") is not (disposition in CLOSURE_DISPOSITIONS):
        raise SystemExit("CLOSURE_RECOMMENDATION_MISMATCH")
    if gate == "TERMINAL_CANDIDATE":
        if disposition not in CLOSURE_DISPOSITIONS:
            raise SystemExit("TERMINAL_CANDIDATE_REQUIRES_CLOSURE_DISPOSITION")
        if status.get("authority_next_action") != "REQUEST_EXACT_HEAD_REVIEW":
            raise SystemExit("TERMINAL_CANDIDATE_REQUIRES_EXACT_HEAD_REVIEW")
        if status.get("terminal_candidate_classified_at") != status.get("generated_at"):
            raise SystemExit("TERMINAL_CANDIDATE_TIME_MISMATCH")
        if "validated_disposition_at" in status:
            raise SystemExit("TERMINAL_CANDIDATE_HAS_NONTERMINAL_TIMESTAMP")
    else:
        if "authority_next_action" in status or "terminal_candidate_classified_at" in status:
            raise SystemExit("NONTERMINAL_STATUS_CONTAINS_AUTHORITY_HANDOFF")
        if "validated_disposition_at" in status and status["validated_disposition_at"] != status.get("generated_at"):
            raise SystemExit("VALIDATED_DISPOSITION_TIME_MISMATCH")
    if status.get("issue_materialized") is not True:
        raise SystemExit("ISSUE_MATERIALIZATION_NOT_RECORDED")
    if status.get("generated_at") != binding.get("source_updated_at"):
        raise SystemExit("STATUS_TIME_DIFFERS_FROM_BOUND_SOURCE_TIME")
    for key in ("automatic_merge", "automatic_issue_close", "mirror_sync_required", "common_tag_required"):
        if key not in status or status[key] is not False:
            raise SystemExit(f"ISSUE_AGENT_MUST_NOT_SET_{key.upper()}")
    if status.get("no_false_pass") is not True:
        raise SystemExit("NO_FALSE_PASS_GATE_FAILED")
    if status.get("claims") != FALSE_CLAIMS:
        raise SystemExit("STATUS_CONTAINS_FALSE_COMPLETION_CLAIM")

    answer_disposition = section(answer, "Issue disposition").strip().strip("`")
    answer_gate = section(answer, "Gate result").strip().strip("`")
    if answer_disposition != disposition:
        raise SystemExit("ANSWER_STATUS_DISPOSITION_MISMATCH")
    if section(answer, "Disposition reason") != status.get("disposition_reason"):
        raise SystemExit("ANSWER_STATUS_REASON_MISMATCH")
    if section(answer, "Required next action") != status.get("next_action"):
        raise SystemExit("ANSWER_STATUS_NEXT_ACTION_MISMATCH")
    if section(answer, "Evaluation mode") != evaluation_mode:
        raise SystemExit("ANSWER_STATUS_EVALUATION_MODE_MISMATCH")
    if section(answer, "Handler id") != status.get("handler_id"):
        raise SystemExit("ANSWER_STATUS_HANDLER_MISMATCH")
    if section(answer, "Handler SHA-256") != handler_sha256:
        raise SystemExit("ANSWER_STATUS_HANDLER_SHA256_MISMATCH")
    if section(answer, "Request fingerprint") != fingerprint:
        raise SystemExit("ANSWER_STATUS_FINGERPRINT_MISMATCH")
    expected_answer_gate = "BLOCK" if disposition in {"CLARIFICATION_REQUIRED", "BLOCKED_WITH_NEXT_ACTION"} else "CONTINUE"
    if answer_gate != expected_answer_gate:
        raise SystemExit("ANSWER_GATE_DIFFERS_FROM_DISPOSITION")
    expected_statuses = (
        {"BLOCK"}
        if expected_answer_gate == "BLOCK"
        else ({"CONTINUE", "TERMINAL_CANDIDATE"} if disposition in CLOSURE_DISPOSITIONS else {"CONTINUE"})
    )
    if gate not in expected_statuses:
        raise SystemExit("STATUS_GATE_DIFFERS_FROM_DISPOSITION")
    if fixed_semantics is not None:
        actual_semantics = {
            "disposition": disposition,
            "reason": status.get("disposition_reason"),
            "next_action": status.get("next_action"),
            "gate": answer_gate,
        }
        if actual_semantics != fixed_semantics:
            raise SystemExit("EVALUATION_SEMANTICS_DIFFER_FROM_CANONICAL_ROUTE")

    try:
        verify_reduction(directory, verify_authority=verify_authority)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"INVALID_QUADRATIC_WORK_REDUCTION: {exc}") from exc


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate.py DIRECTORY")
    validate(Path(sys.argv[1]))
