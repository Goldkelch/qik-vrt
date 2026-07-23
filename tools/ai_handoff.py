#!/usr/bin/env python3
"""Validate and print the repository's machine-readable AI handoff context.

Standard-library only. Read-only: this script does not modify repository or Git
state and performs no network access.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_PATH = ROOT / "AI_CONTEXT.json"
TERMINAL_OR_IDLE_STATES = {"IDLE", "PASS", "BLOCK", "FAIL", "TIMEOUT", "CANCELLED"}


def fail(message: str) -> NoReturn:
    print(f"AI_HANDOFF_BLOCK: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"top-level value in {path} must be an object")
    return value


def require(obj: dict[str, Any], key: str, expected: type) -> Any:
    value = obj.get(key)
    if not isinstance(value, expected):
        fail(f"field {key!r} must be {expected.__name__}")
    return value


def require_exact_int(obj: dict[str, Any], key: str) -> int:
    value = obj.get(key)
    if type(value) is not int:
        fail(f"field {key!r} must be int")
    return value


def require_true(obj: dict[str, Any], key: str) -> None:
    if obj.get(key) is not True:
        fail(f"field {key!r} must be true")


def require_false(obj: dict[str, Any], key: str) -> None:
    if obj.get(key) is not False:
        fail(f"field {key!r} must be false")


def require_file(path_text: str) -> Path:
    path = ROOT / path_text
    if not path.is_file():
        fail(f"required repository file is missing: {path_text}")
    return path


def git_value(*args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return proc.stdout.strip() or "unavailable"


def validate_adapters(context: dict[str, Any]) -> tuple[str, int]:
    registry_name = require(context, "adapter_registry", str)
    registry = load_json(require_file(registry_name))
    if require(registry, "schema", str) != "qikvrt-ai-adapters/1.0":
        fail("unsupported AI adapter registry schema")
    if require(registry, "canonical_entrypoint", str) != "AI":
        fail("AI adapter registry must bind canonical entrypoint AI")
    adapters = require(registry, "adapters", list)
    if not adapters:
        fail("AI adapter registry must contain at least one adapter")
    missing: list[str] = []
    for adapter in adapters:
        if not isinstance(adapter, dict):
            fail("every AI adapter entry must be an object")
        path = require(adapter, "path", str)
        if not (ROOT / path).is_file():
            missing.append(path)
    if missing:
        fail("missing AI adapter files: " + ", ".join(sorted(missing)))
    return registry_name, len(adapters)


def validate_progress(context: dict[str, Any]) -> tuple[str, str, str]:
    progress = require(context, "progress_protocol", dict)
    path_keys = (
        "normative_standard",
        "human_contract",
        "machine_policy",
        "frame_schema",
        "machine_state",
        "human_projection",
        "live_watcher",
    )
    paths = {key: require(progress, key, str) for key in path_keys}
    files = {key: require_file(path) for key, path in paths.items()}

    policy = load_json(files["machine_policy"])
    if require(policy, "schema", str) != "qikvrt-human-machine-progress-protocol/1.3":
        fail("unsupported human-machine progress policy schema")
    if require(policy, "authority", str) != paths["normative_standard"]:
        fail("progress policy authority does not match AI context")
    if require(policy, "progress_schema", str) != paths["frame_schema"]:
        fail("progress policy schema path does not match AI context")

    communication = require(policy, "communication_rules", dict)
    for key in (
        "progress_frame_before_every_github_action",
        "progress_frame_after_every_github_action",
        "progress_frame_on_every_workflow_transition",
        "progress_frame_on_every_job_transition",
        "progress_frame_on_every_step_transition",
        "telemetry_observation_and_persistence_is_one_nonrecursive_atomic_cycle",
        "complete_persistence_before_final_response",
        "execution_telemetry_is_not_a_final_conversational_return",
    ):
        require_true(communication, key)
    for key in (
        "allow_batched_github_actions_without_intermediate_frame",
        "later_summary_compensates_for_missing_frame",
        "repeat_unchanged_state",
        "claim_pass_without_evidence",
    ):
        require_false(communication, key)

    observation = require(policy, "observation_contract", dict)
    require_true(observation, "serial_cycles")
    require_false(observation, "overlapping_cycles_allowed")
    require_true(observation, "persist_frame_before_next_cycle")
    require_true(observation, "observe_workflows_jobs_and_steps")
    require_true(observation, "emit_only_on_state_signature_change")
    if require_exact_int(observation, "poll_interval_seconds_after_completed_cycle") != 5:
        fail("progress watcher poll interval must be exactly five seconds")

    schema_doc = load_json(files["frame_schema"])
    if schema_doc.get("$id") != "urn:qikvrt:schema:human-machine-progress:2":
        fail("unsupported progress-frame JSON Schema identifier")
    properties = require(schema_doc, "properties", dict)
    schema_property = require(properties, "schema", dict)
    if schema_property.get("const") != "qikvrt_human_machine_progress_v2":
        fail("progress-frame schema must require qikvrt_human_machine_progress_v2")
    schema_required = require(schema_doc, "required", list)
    policy_required = require(policy, "mandatory_fields", list)
    if set(schema_required) != set(policy_required):
        fail("progress policy and JSON Schema mandatory fields differ")

    snapshot = load_json(files["machine_state"])
    if require(snapshot, "schema", str) != "qikvrt_human_machine_progress_v2":
        fail("tracked progress snapshot does not use frame schema v2")
    missing = [key for key in policy_required if key not in snapshot]
    if missing:
        fail("tracked progress snapshot is missing fields: " + ", ".join(missing))
    state = require(snapshot, "state", str)
    if state not in TERMINAL_OR_IDLE_STATES:
        fail("tracked root progress snapshot must be IDLE or terminal")
    percent = require_exact_int(snapshot, "percent")
    if not 0 <= percent <= 100:
        fail("tracked progress percent must be between 0 and 100")
    require_exact_int(snapshot, "sequence")
    transition = require(snapshot, "transition", dict)
    if require(transition, "kind", str) not in {
        "idle", "github_action_before", "github_action_after", "workflow", "job", "step", "terminal"
    }:
        fail("tracked progress snapshot has an unsupported transition kind")
    require(transition, "name", str)
    require(transition, "state", str)
    gates = require(snapshot, "gates", list)
    if not gates:
        fail("tracked progress snapshot must contain at least one gate")
    for gate in gates:
        if not isinstance(gate, dict):
            fail("every progress gate must be an object")
        require(gate, "name", str)
        require(gate, "state", str)
    blockers = require(snapshot, "blockers", list)
    if not all(isinstance(item, str) and item for item in blockers):
        fail("progress blockers must be non-empty strings")

    status_text = files["human_projection"].read_text(encoding="utf-8")
    if f"`{state}`" not in status_text:
        fail("human progress projection does not contain the machine snapshot state")
    if "[██████████]" not in status_text:
        fail("human progress projection does not contain a complete progress graphic")

    standard_text = files["normative_standard"].read_text(encoding="utf-8")
    for phrase in (
        "immediately before and immediately after every discrete GitHub action",
        "workflow, job, or step changes state",
        "five seconds",
        "repository is the durable runtime authority",
    ):
        if phrase not in standard_text:
            fail(f"normative progress standard is missing required phrase: {phrase}")

    return policy["schema"], snapshot["schema"], state


def validate_runtime(context: dict[str, Any]) -> tuple[str, int]:
    runtime = require(context, "runtime_authority", dict)
    require_true(runtime, "repository_is_runtime_authority")
    require_true(runtime, "chat_is_disposable_transport")
    if require(runtime, "cache_root", str) != ".qikvrt/toolchains":
        fail("runtime cache root must be .qikvrt/toolchains")

    path_keys = (
        "cache_policy",
        "toolchain_lock",
        "bootstrap_posix",
        "bootstrap_windows",
        "adaptive_runtime",
        "lean_cache_workflow",
    )
    paths = {key: require(runtime, key, str) for key in path_keys}
    files = {key: require_file(path) for key, path in paths.items()}

    policy_text = files["cache_policy"].read_text(encoding="utf-8")
    for phrase in (
        "repository is the durable runtime authority",
        "Cumulative tool inventory",
        "Credentials",
    ):
        if phrase.lower() not in policy_text.lower():
            fail(f"runtime cache policy is missing required phrase: {phrase}")

    lock_lines = [
        line for line in files["toolchain_lock"].read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    components = {line.split("\t", 1)[0] for line in lock_lines if "\t" in line}
    required_components = {"gh", "xml2rfc", "python", "node", "lean"}
    missing = sorted(required_components - components)
    if missing:
        fail("runtime toolchain lock is missing components: " + ", ".join(missing))

    return paths["toolchain_lock"], len(lock_lines)


def main() -> int:
    context = load_json(CONTEXT_PATH)
    schema = require(context, "schema", str)
    if schema != "qikvrt-ai-context/1.1":
        fail(f"unsupported schema {schema!r}")

    project = require(context, "project", dict)
    name = require(project, "name", str)
    canonicality = require(project, "canonicality", dict)
    repositories = require(canonicality, "repositories", list)
    if not repositories or not all(isinstance(x, str) and x for x in repositories):
        fail("canonical repositories must be a non-empty string list")

    read_order = require(context, "required_read_order", list)
    if not read_order or not all(isinstance(x, str) and x for x in read_order):
        fail("required_read_order must be a non-empty string list")
    missing = [path for path in read_order if not (ROOT / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    registry_name, adapter_count = validate_adapters(context)
    progress_policy, progress_schema, progress_state = validate_progress(context)
    toolchain_lock, tool_count = validate_runtime(context)

    licensing = require(context, "licensing_policy", dict)
    architecture = require(licensing, "architecture", dict)
    implementation = require(licensing, "implementation", dict)

    print("AI_HANDOFF_STATUS=VALID")
    print(f"PROJECT={name}")
    print(f"CONTEXT_ID={context.get('context_id', 'unknown')}")
    print(f"GIT_REF={git_value('rev-parse', '--abbrev-ref', 'HEAD')}")
    print(f"GIT_COMMIT={git_value('rev-parse', 'HEAD')}")
    print("CANONICAL_MODE=" + str(canonicality.get("mode", "unknown")))
    print("CANONICAL_REPOSITORIES=" + ",".join(repositories))
    print("READ_ORDER=" + " -> ".join(read_order))
    print(f"AI_ADAPTER_REGISTRY={registry_name}")
    print(f"AI_ADAPTER_COUNT={adapter_count}")
    print(f"PROGRESS_POLICY={progress_policy}")
    print(f"PROGRESS_SCHEMA={progress_schema}")
    print(f"PROGRESS_STATE={progress_state}")
    print(f"RUNTIME_TOOLCHAIN_LOCK={toolchain_lock}")
    print(f"RUNTIME_TOOL_RECORDS={tool_count}")
    print("ARCHITECTURE_POLICY=" + str(architecture.get("intent", "unknown")))
    print("IMPLEMENTATION_POLICY=" + str(implementation.get("intent", "unknown")))
    print("NEXT_ACTION=Emit frame 1 before the next GitHub action, then continue from repository evidence without relying on chat memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
