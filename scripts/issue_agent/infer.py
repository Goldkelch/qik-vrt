#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path

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

EXCLUDED_TOOLS = (
    "bash,powershell,list_bash,list_powershell,read_bash,read_powershell,"
    "stop_bash,stop_powershell,write_bash,write_powershell,apply_patch,create,edit,view,"
    "list_agents,read_agent,task,write_agent,ask_user,glob,grep,rg,skill,web_fetch"
)


def build_prompt(issue: dict, context: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\n"
        + f"ISSUE #{issue['number']}\nTITLE: {issue.get('title', '')}\n"
        + f"BODY:\n{issue.get('body') or ''}\n\nREPOSITORY CONTEXT:\n{context}"
    )


def run_copilot(prompt: str, model: str, executable: str = "copilot") -> str:
    env = os.environ.copy()
    token = env.get("COPILOT_GITHUB_TOKEN") or env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if not token:
        raise RuntimeError("Copilot authentication token is required")
    env["COPILOT_GITHUB_TOKEN"] = token
    env["COPILOT_AUTO_UPDATE"] = "false"
    completed = subprocess.run(
        [
            executable,
            "--no-banner",
            "--stream=off",
            f"--model={model}",
            f"--excluded-tools={EXCLUDED_TOOLS}",
            "-p",
            prompt,
        ],
        text=True,
        capture_output=True,
        env=env,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Copilot CLI inference failed ({completed.returncode}): {detail}")
    answer = completed.stdout.strip()
    if not answer:
        raise RuntimeError("Copilot CLI returned an empty answer")
    return answer + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--issue", required=True)
    p.add_argument("--context", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--model", default="auto")
    p.add_argument("--provider", choices=("copilot-cli",), default="copilot-cli")
    p.add_argument("--copilot-executable", default="copilot")
    args = p.parse_args()

    issue = json.loads(Path(args.issue).read_text(encoding="utf-8"))
    context = Path(args.context).read_text(encoding="utf-8")
    prompt = build_prompt(issue, context)

    try:
        answer = run_copilot(prompt, args.model, args.copilot_executable)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(str(exc))

    Path(args.output).write_text(answer, encoding="utf-8")


if __name__ == "__main__":
    main()
