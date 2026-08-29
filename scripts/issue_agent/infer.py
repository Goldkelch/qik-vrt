#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib import request, error

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.issue_agent.binding import json_loads_strict, validate_request
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
)

API_URL = "https://models.github.ai/inference/chat/completions"
DEFAULT_POLICY = ROOT / "policy" / "ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def owner_markers(body: str, prefix: str) -> list[str]:
    markers = re.findall(r"<!--\s*([a-z0-9][a-z0-9_.:-]{1,199})\s*-->", body)
    return sorted({marker for marker in markers if marker.startswith(prefix)})


def answer_text(
    *,
    issue_number: int,
    disposition: str,
    reason: str,
    next_action: str,
    gate: str,
    evaluation_mode: str,
    handler_id: str,
    handler_sha256: str,
    request_fingerprint: str,
    formal_status: str = "NOT_EVALUATED",
    empirical_status: str = "NOT_EVALUATED",
) -> str:
    return (
        "# Repository answer\n\n"
        f"Issue #{issue_number} was classified by a repository-bound deterministic intake handler. "
        "The classification does not establish completion, merge, publication, deployment, or a physical effect.\n\n"
        "## Evidence used\n\n"
        f"Exact request fingerprint `{request_fingerprint}` and handler digest `{handler_sha256}`.\n\n"
        f"## Formal status\n\n{formal_status}\n\n"
        f"## Empirical status\n\n{empirical_status}\n\n"
        f"## Issue disposition\n\n{disposition}\n\n"
        f"## Disposition reason\n\n{reason}\n\n"
        f"## Required next action\n\n{next_action}\n\n"
        f"## Gate result\n\n{gate}\n\n"
        f"## Evaluation mode\n\n{evaluation_mode}\n\n"
        f"## Handler id\n\n{handler_id}\n\n"
        f"## Handler SHA-256\n\n{handler_sha256}\n\n"
        f"## Request fingerprint\n\n{request_fingerprint}\n"
    )


def deterministic_answer(
    issue: dict,
    request_value: dict,
    policy: dict,
    policy_sha256: str,
) -> str | None:
    if policy.get("schema") != "qikvrt_issue_agent_deterministic_intake_v1":
        raise SystemExit("deterministic intake policy schema is invalid")
    if request_value.get("schema") != "qikvrt_issue_agent_request_v2":
        raise SystemExit("materialized issue request schema is invalid")
    fingerprint = request_value.get("request_fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise SystemExit("materialized issue request fingerprint is invalid")
    trigger = request_value.get("trigger")
    if not isinstance(trigger, dict):
        raise SystemExit("materialized issue trigger is invalid")
    selected_body = trigger.get("selected_body")
    if not isinstance(selected_body, str):
        raise SystemExit("materialized selected body is invalid")
    if sha256_bytes(selected_body.encode("utf-8")) != trigger.get("selected_body_sha256"):
        raise SystemExit("materialized selected body digest mismatch")
    binding = request_value.get("binding")
    if not isinstance(binding, dict):
        raise SystemExit("materialized issue binding is invalid")
    if binding.get("handler_policy_sha256") != policy_sha256:
        raise SystemExit("deterministic intake policy digest differs from request binding")
    if binding.get("selected_body_sha256") != trigger.get("selected_body_sha256"):
        raise SystemExit("selected body differs between trigger and request binding")
    if binding.get("actor_login") != trigger.get("actor_login"):
        raise SystemExit("actor differs between trigger and request binding")
    if binding.get("issue_number") != issue.get("number"):
        raise SystemExit("issue differs between payload and request binding")

    failure_state = external_failure_state(request_value, policy)
    matched_failures = failure_state["matched_signatures"]
    if matched_failures and failure_state["structured"]:
        handler = external_failure_descriptor(matched_failures)
        return answer_text(
            issue_number=issue["number"],
            disposition="BLOCKED_WITH_NEXT_ACTION",
            reason="EXTERNAL_AGENT_ADMISSION_FAILURE",
            next_action="Route the original typed owner work order through the deterministic repository handler; do not recursively treat this transport failure as a new semantic task.",
            gate="BLOCK",
            evaluation_mode="EXTERNAL_AGENT_FAILURE",
            handler_id=handler["handler_id"],
            handler_sha256=descriptor_sha256(handler),
            request_fingerprint=fingerprint,
        )

    marker = marker_state(request_value, policy)
    markers = marker["markers"]
    if not markers:
        if not marker["actor_trusted"]:
            handler = reject_descriptor(UNTRUSTED_UNTYPED_HANDLER_ID, [])
            return answer_text(
                issue_number=issue["number"],
                disposition="BLOCKED_WITH_NEXT_ACTION",
                reason="UNTYPED_REQUEST_ACTOR_NOT_AUTHORIZED",
                next_action="A trusted repository owner must explicitly reobserve and dispatch this untyped issue before optional model inference or candidate materialization.",
                gate="BLOCK",
                evaluation_mode="DETERMINISTIC_REJECT",
                handler_id=handler["handler_id"],
                handler_sha256=descriptor_sha256(handler),
                request_fingerprint=fingerprint,
            )
        return None

    if not marker["actor_trusted"] or not marker["selected_author_trusted"]:
        handler = reject_descriptor(UNTRUSTED_MARKER_HANDLER_ID, markers)
        return answer_text(
            issue_number=issue["number"],
            disposition="BLOCKED_WITH_NEXT_ACTION",
            reason="OWNER_MARKER_ACTOR_NOT_AUTHORIZED",
            next_action="Obtain an exact marker event from a login authorized by the deterministic intake policy.",
            gate="BLOCK",
            evaluation_mode="DETERMINISTIC_REJECT",
            handler_id=handler["handler_id"],
            handler_sha256=descriptor_sha256(handler),
            request_fingerprint=fingerprint,
        )
    recognized = marker["recognized"]
    if len(markers) != 1 or len(recognized) != 1:
        handler = reject_descriptor(AMBIGUOUS_MARKER_HANDLER_ID, markers)
        return answer_text(
            issue_number=issue["number"],
            disposition="BLOCKED_WITH_NEXT_ACTION",
            reason="UNKNOWN_OR_AMBIGUOUS_OWNER_WORK_ORDER_MARKER",
            next_action="Use exactly one versioned marker registered by the current deterministic intake policy.",
            gate="BLOCK",
            evaluation_mode="DETERMINISTIC_REJECT",
            handler_id=handler["handler_id"],
            handler_sha256=descriptor_sha256(handler),
            request_fingerprint=fingerprint,
        )

    handler = recognized[0]
    return answer_text(
        issue_number=issue["number"],
        disposition=handler["disposition"],
        reason=f"SCHEMA_MARKED_OWNER_WORK_ORDER_ADMITTED:{handler['handler_id']}",
        next_action=handler["required_next_action"],
        gate="CONTINUE",
        evaluation_mode="DETERMINISTIC_OWNER_CONTRACT",
        handler_id=handler["handler_id"],
        handler_sha256=descriptor_sha256(handler),
        request_fingerprint=fingerprint,
        formal_status=handler.get("formal_status", "WORK_UNIT_ADMITTED_NOT_YET_EXECUTED"),
        empirical_status=handler.get("empirical_status", "NOT_EVALUATED"),
    )

SYSTEM_PROMPT = """You are the repository-native QIK-VRT issue processor.
Answer only from the supplied issue and repository context. Distinguish repository evidence,
formal derivation, hypothesis, and empirical confirmation. Never claim PASS, DONE, proof,
physical confirmation, or implementation unless the supplied evidence establishes it.
Identify contradictions and missing evidence.

Every open issue must receive exactly one current lifecycle disposition:
- EXECUTE_NOW: clear, supported, and technically actionable; admit and identify the smallest bounded work unit and its exact executor or next action. This intake result is not evidence that the work ran.
- CLARIFICATION_REQUIRED: a specific ambiguity prevents safe execution; identify the minimum missing information.
- BLOCKED_WITH_NEXT_ACTION: a precise blocker exists; identify the failure class, evidence, retry condition, and one next action.
- CLOSE_COMPLETED: the requested result is already fully evidenced or canonically superseded.
- CLOSE_NOT_PLANNED: the request is understood but outside the supported or authorized scope.
- CLOSE_INVALID_OR_UNSUPPORTED: the request is not reproducible, not traceable, internally contradictory, untrue, or technically unsupported.

Do not leave an issue in an unclassified waiting state. Age alone is not a closure reason, broadness alone is not a waiting reason, and closure may not hide a real unresolved defect. If work is possible, admit an exact bounded work unit and identify its executor-registration or dispatch boundary; do not imply that intake performed the work. If safe execution needs clarification, ask only the bounded clarification; if closure is warranted, provide a concise evidence-bound reason.

Produce Markdown with sections: Repository answer, Evidence used, Formal status, Empirical status,
Issue disposition, Disposition reason, Required next action, Gate result.
The Issue disposition section must contain exactly one allowed disposition token.
The Required next action section must contain one concrete action, or NONE only for a justified closure disposition.
The final gate result must be CONTINUE for admitted-work or closure candidates and BLOCK for
clarification or blocker dispositions. DONE and ISOLATE are not issue-intake gate results.
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--issue", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--context", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--model", required=True)
    args = p.parse_args()

    observed_issue = json_loads_strict(Path(args.issue).read_text(encoding="utf-8"))
    request_value = validate_request(
        json_loads_strict(Path(args.request).read_text(encoding="utf-8")),
        repository_root=ROOT,
        verify_git=True,
    )
    issue = {
        "number": request_value["issue_number"],
        "title": request_value.get("title") or "",
        "body": request_value.get("body") or "",
        "user": {
            "login": request_value.get("author"),
            "type": request_value.get("author_type"),
        },
    }
    observed_projection = {
        "number": observed_issue.get("number"),
        "title": observed_issue.get("title") or "",
        "body": observed_issue.get("body") or "",
        "user": {
            "login": (observed_issue.get("user") or {}).get("login"),
            "type": (observed_issue.get("user") or {}).get("type"),
        },
    }
    if observed_projection != issue:
        raise SystemExit("resolved issue payload differs from exact materialized request snapshot")
    policy_bytes = DEFAULT_POLICY.read_bytes()
    policy = json_loads_strict(policy_bytes)
    deterministic = deterministic_answer(
        issue,
        request_value,
        policy,
        sha256_bytes(policy_bytes),
    )
    if deterministic is not None:
        Path(args.output).write_text(deterministic, encoding="utf-8")
        return

    configured_model = policy.get("model_boundary", {}).get("optional_model")
    if args.model != configured_model:
        raise SystemExit("requested model differs from exact deterministic intake policy")

    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN is required for an untyped request delegated to the optional model path")

    context = Path(args.context).read_text(encoding="utf-8")
    user_content = (
        f"ISSUE #{issue['number']}\nTITLE: {issue.get('title', '')}\n"
        f"BODY:\n{issue.get('body') or ''}\n\nREPOSITORY CONTEXT:\n{context}"
    )
    payload = json.dumps({
        "model": args.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    }).encode("utf-8")
    req = request.Request(API_URL, data=payload, method="POST", headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2026-03-10",
    })
    try:
        with request.urlopen(req, timeout=120) as response:
            result = json.load(response)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub Models inference failed: HTTP {exc.code}: {detail}")

    answer = result["choices"][0]["message"]["content"].strip() + "\n"
    reserved = ("Evaluation mode", "Handler id", "Handler SHA-256", "Request fingerprint")
    if any(re.search(rf"(?m)^##\s+{re.escape(title)}\s*$", answer) for title in reserved):
        raise SystemExit("model output attempted to shadow repository-generated evaluation binding")
    model_handler = model_descriptor(args.model, sha256_bytes(SYSTEM_PROMPT.encode("utf-8")))
    answer += (
        "\n## Evaluation mode\n\nMODEL_INFERENCE\n\n"
        f"## Handler id\n\n{model_handler['handler_id']}\n\n"
        f"## Handler SHA-256\n\n{descriptor_sha256(model_handler)}\n\n"
        f"## Request fingerprint\n\n{request_value['request_fingerprint']}\n"
    )
    Path(args.output).write_text(answer, encoding="utf-8")


if __name__ == "__main__":
    main()
