#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.issue_agent.handlers import descriptor_sha256, unavailable_descriptor
from scripts.issue_agent.binding import json_loads_strict

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


def section(markdown: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(title)}\s*$\n(.*?)(?=^##\s+|\Z)",
        markdown,
    )
    return match.group(1).strip() if match else ""


def section_count(markdown: str, title: str) -> int:
    return len(re.findall(rf"(?m)^##\s+{re.escape(title)}\s*$", markdown))


def disposition_token(markdown: str) -> str | None:
    value = section(markdown, "Issue disposition")
    if not value:
        return None
    token = value.strip().strip("`")
    return token if token in ALLOWED_DISPOSITIONS else None


def write_unavailable_answer(answer: Path, request_fingerprint: str) -> None:
    handler = unavailable_descriptor()
    handler_id = handler["handler_id"]
    handler_sha256 = descriptor_sha256(handler)
    answer.write_text(
        "# Repository answer\n\n"
        "The autonomous model step was not available, failed, or returned an invalid control "
        "envelope. No scientific or technical answer is asserted. The exact request and repository "
        "context remain available for a bounded causal continuation.\n\n"
        "## Evidence used\n\nRepository request and materialized context only.\n\n"
        "## Formal status\n\nNOT_EVALUATED\n\n"
        "## Empirical status\n\nNOT_EVALUATED\n\n"
        "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
        "## Disposition reason\n\nMODEL_INFERENCE_UNAVAILABLE\n\n"
        "## Required next action\n\nResume the bounded issue transaction when a trusted inference or deterministic work-unit path is available.\n\n"
        "## Gate result\n\nBLOCK\n\n"
        "## Evaluation mode\n\nUNAVAILABLE\n\n"
        f"## Handler id\n\n{handler_id}\n\n"
        f"## Handler SHA-256\n\n{handler_sha256}\n\n"
        f"## Request fingerprint\n\n{request_fingerprint}\n",
        encoding="utf-8",
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--directory", required=True)
    p.add_argument("--inference-outcome", required=True)
    args = p.parse_args()

    directory = Path(args.directory)
    request_value = json_loads_strict((directory / "REQUEST.json").read_text(encoding="utf-8"))
    request_fingerprint = request_value.get("request_fingerprint")
    answer = directory / "ANSWER.md"
    inference_succeeded = (
        args.inference_outcome == "success"
        and answer.exists()
        and answer.stat().st_size > 0
    )
    if not inference_succeeded:
        write_unavailable_answer(answer, request_fingerprint)

    markdown = answer.read_text(encoding="utf-8")
    reserved_sections = ("Evaluation mode", "Handler id", "Handler SHA-256", "Request fingerprint")
    reserved_binding_unique = all(section_count(markdown, title) == 1 for title in reserved_sections)
    evaluation_mode = section(markdown, "Evaluation mode")
    handler_id = section(markdown, "Handler id")
    handler_sha256 = section(markdown, "Handler SHA-256")
    answer_fingerprint = section(markdown, "Request fingerprint")
    evaluation_binding_valid = (
        reserved_binding_unique
        and evaluation_mode in TRUSTED_EVALUATION_MODES
        and bool(handler_id)
        and bool(re.fullmatch(r"[0-9a-f]{64}", handler_sha256))
        and answer_fingerprint == request_fingerprint
    )
    disposition = disposition_token(markdown)
    reason = section(markdown, "Disposition reason")
    next_action = section(markdown, "Required next action")
    disposition_valid = (
        disposition is not None
        and bool(reason)
        and bool(next_action)
        and (
            disposition in CLOSURE_DISPOSITIONS
            or next_action.strip().upper() != "NONE"
        )
    )

    if inference_succeeded and (not evaluation_binding_valid or not disposition_valid):
        write_unavailable_answer(answer, request_fingerprint)
        markdown = answer.read_text(encoding="utf-8")
        evaluation_mode = "UNAVAILABLE"
        handler = unavailable_descriptor()
        handler_id = handler["handler_id"]
        handler_sha256 = descriptor_sha256(handler)
        answer_fingerprint = request_fingerprint
        evaluation_binding_valid = False
        disposition = "BLOCKED_WITH_NEXT_ACTION"
        reason = "MODEL_INFERENCE_UNAVAILABLE"
        next_action = "Resume the bounded issue transaction when a trusted inference or deterministic work-unit path is available."
        disposition_valid = True

    if not disposition_valid:
        disposition = "BLOCKED_WITH_NEXT_ACTION"
        reason = "ISSUE_DISPOSITION_MISSING_OR_INVALID"
        next_action = "Regenerate the repository-grounded answer with one allowed disposition, a reason, and one concrete next action."

    status_value = (
        "BLOCK"
        if disposition in {"CLARIFICATION_REQUIRED", "BLOCKED_WITH_NEXT_ACTION"}
        else "CONTINUE"
    )
    status = {
        "schema": "qikvrt_issue_agent_status_v2",
        "status": status_value,
        "issue_materialized": True,
        "model_inference_completed": evaluation_binding_valid and evaluation_mode == "MODEL_INFERENCE",
        "deterministic_contract_completed": evaluation_binding_valid and evaluation_mode == "DETERMINISTIC_OWNER_CONTRACT",
        "evaluation_completed": evaluation_binding_valid,
        "evaluation_mode": evaluation_mode if evaluation_binding_valid else "UNAVAILABLE",
        "handler_id": handler_id,
        "handler_sha256": handler_sha256,
        "request_fingerprint": request_fingerprint,
        "issue_disposition": disposition,
        "disposition_reason": reason,
        "next_action": next_action,
        "closure_recommended": disposition in CLOSURE_DISPOSITIONS,
        "automatic_issue_close": False,
        "automatic_merge": False,
        "mirror_sync_required": False,
        "common_tag_required": False,
        "generated_at": request_value.get("binding", {}).get("source_updated_at"),
        "no_false_pass": True,
        "claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
            "ISSUE_CLOSE": False,
            "MIRROR_SYNC": False,
            "TAG": False,
            "PUBLICATION": False,
            "DEPLOYMENT": False,
        },
    }
    evaluation = {
        "schema": "qikvrt_issue_agent_evaluation_binding_v1",
        "answer_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "evaluation_completed": evaluation_binding_valid,
        "evaluation_mode": status["evaluation_mode"],
        "handler_id": handler_id,
        "handler_sha256": handler_sha256,
        "request_fingerprint": request_fingerprint,
    }
    evaluation_bytes = (json.dumps(evaluation, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
    (directory / "EVALUATION.json").write_bytes(evaluation_bytes)
    (directory / "EVALUATION.sha256").write_text(
        f"{hashlib.sha256(evaluation_bytes).hexdigest()}  EVALUATION.json\n",
        encoding="utf-8",
    )
    (directory / "STATUS.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
