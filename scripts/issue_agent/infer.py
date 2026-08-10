#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from urllib import request, error

API_URL = "https://models.github.ai/inference/chat/completions"

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
