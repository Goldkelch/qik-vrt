#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path
from urllib import request, error

API_URL = "https://models.github.ai/inference/chat/completions"


OWNER_CONTRACT_SCHEMA = "qikvrt_owner_observed_repository_work_cycle_v1"
OWNER_CYCLE = [
    "EXTERNAL_REQUEST_OR_EVENT",
    "EXACT_BINDING",
    "CLASSIFY",
    "WORK",
    "RESULT",
    "MATERIALIZE",
    "REOBSERVE",
    "TERMINAL_STATUS",
    "REPORT",
    "RETURN_TO_ZERO",
]
REQUIRED_FALSE_NON_CLAIMS = {
    "independent_approval",
    "merge",
    "authority_main_effect",
    "authority_mirror_synchronization",
    "publication",
    "deployment",
    "PASS",
    "FINAL_PASS",
    "EFFECT_ACK_DONE",
    "authority_review_fanout_end_to_end_observed",
}


def extract_owner_contract(body: str) -> dict | None:
    """Return one exact schema-marked owner contract or fail closed."""
    matches = []
    for raw in re.findall(r"(?ms)^\x60\x60\x60json\s*$\n(.*?)^\x60\x60\x60\s*$", body):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == OWNER_CONTRACT_SCHEMA:
            matches.append(value)
    if len(matches) != 1:
        return None

    value = matches[0]
    hex40 = re.compile(r"^[0-9a-f]{40}$")
    if value.get("repository") != "Goldkelch/qik-vrt":
        return None
    if not isinstance(value.get("carrier_pr"), int) or value["carrier_pr"] < 1:
        return None
    if not hex40.fullmatch(value.get("observed_head", "")):
        return None
    if not hex40.fullmatch(value.get("observed_tree", "")):
        return None
    if not hex40.fullmatch(value.get("authority_main", "")):
        return None
    if value.get("cycle") != OWNER_CYCLE:
        return None
    reaction = value.get("observed_repository_reaction")
    if not isinstance(reaction, dict):
        return None
    if reaction.get("d0") not in {0, 1, 2, 3}:
        return None
    if reaction.get("state") not in {"NOOP", "HOLD", "REOBSERVE", "REQUEST_AUTHORITY"}:
        return None
    if not isinstance(value.get("finding"), str) or not value["finding"].strip():
        return None
    behavior = value.get("required_future_behavior")
    if not isinstance(behavior, list) or not behavior or not all(
        isinstance(item, str) and item.strip() for item in behavior
    ):
        return None
    non_claims = value.get("non_claims")
    if not isinstance(non_claims, dict) or any(
        non_claims.get(key) is not False for key in REQUIRED_FALSE_NON_CLAIMS
    ):
        return None
    return value


def deterministic_owner_answer(issue: dict) -> str | None:
    contract = extract_owner_contract(issue.get("body") or "")
    if contract is None:
        return None
    return (
        "# Repository answer\n\n"
        "The embedded Product-Owner work-cycle contract is structurally valid and "
        "can be processed without an external inference service. This validates the "
        "contract envelope only; referenced GitHub commits, runs, effects, and claims "
        "remain subject to exact independent reobservation.\n\n"
        "## Evidence used\n\n"
        f"Issue #{issue['number']} exact body; schema \x60{OWNER_CONTRACT_SCHEMA}\x60; "
        f"carrier PR #{contract['carrier_pr']}; exact head \x60{contract['observed_head']}\x60; "
        f"tree \x60{contract['observed_tree']}\x60.\n\n"
        "## Formal status\n\nDETERMINISTIC_OWNER_CONTRACT_VALIDATED\n\n"
        "## Empirical status\n\nREFERENCED_EVIDENCE_REQUIRES_EXACT_REOBSERVATION\n\n"
        "## Inference mode\n\nDETERMINISTIC_OWNER_CONTRACT\n\n"
        "## Issue disposition\n\nEXECUTE_NOW\n\n"
        "## Disposition reason\n\n"
        "The schema-marked owner request is unambiguous, bounded, fail-closed, and "
        "contains explicit non-claims.\n\n"
        "## Required next action\n\n"
        "Persist the validated contract on a history-preserving carrier and reobserve "
        "its exact head before deriving one next causal turn.\n\n"
        "## Gate result\n\nCONTINUE\n"
    )

SYSTEM_PROMPT = """You are the repository-native QIK-VRT issue processor.
Answer only from the supplied issue and repository context. Distinguish repository evidence,
formal derivation, hypothesis, and empirical confirmation. Never claim PASS, DONE, proof,
physical confirmation, or implementation unless the supplied evidence establishes it.
Identify contradictions and missing evidence.

Every open issue must receive exactly one current lifecycle disposition:
- EXECUTE_NOW: clear, supported, and technically actionable; identify the smallest bounded work unit.
- CLARIFICATION_REQUIRED: a specific ambiguity prevents safe execution; identify the minimum missing information.
- BLOCKED_WITH_NEXT_ACTION: a precise blocker exists; identify the failure class, evidence, retry condition, and one next action.
- CLOSE_COMPLETED: the requested result is already fully evidenced or canonically superseded.
- CLOSE_NOT_PLANNED: the request is understood but outside the supported or authorized scope.
- CLOSE_INVALID_OR_UNSUPPORTED: the request is not reproducible, not traceable, internally contradictory, untrue, or technically unsupported.

Do not leave an issue in an unclassified waiting state. Age alone is not a closure reason, broadness alone is not a waiting reason, and closure may not hide a real unresolved defect. If work is possible, progress it; if safe execution needs clarification, ask only the bounded clarification; if closure is warranted, provide a concise evidence-bound reason.

Produce Markdown with sections: Repository answer, Evidence used, Formal status, Empirical status,
Issue disposition, Disposition reason, Required next action, Gate result.
The Issue disposition section must contain exactly one allowed disposition token.
The Required next action section must contain one concrete action, or NONE only for a justified closure disposition.
The final gate result must be one of DONE, CONTINUE, ISOLATE, BLOCK.
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--issue", required=True)
    p.add_argument("--context", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--model", required=True)
    args = p.parse_args()

    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN is required")

    issue = json.loads(Path(args.issue).read_text(encoding="utf-8"))
    deterministic = deterministic_owner_answer(issue)
    if deterministic is not None:
        Path(args.output).write_text(deterministic, encoding="utf-8")
        return

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
    Path(args.output).write_text(answer, encoding="utf-8")


if __name__ == "__main__":
    main()
