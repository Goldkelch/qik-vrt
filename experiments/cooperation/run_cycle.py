#!/usr/bin/env python3
"""Lokaler Kooperationspilot: gebundene Messwerte deskriptiv vergleichen.

Benutzt den unveränderten QIK-VRT-Pareto-Vergleich. Dieser Adapter ergänzt
Eingabeprüfung, individuelle Lasten, Aufwandsgrenzen und Kandidatenvergleich.
Er führt keine Intervention aus und schätzt keine kausalen Effekte.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def observation_hash(value):
    return digest(canonical(value))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def read_json(path):
    def bad_constant(value):
        raise Invalid(f"NON_FINITE_JSON_NUMBER:{value}")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object,
                      parse_constant=bad_constant)


def native_runtime(root):
    binding = read_json(root / "source_binding.json")
    source = (root / "upstream/qikvrt_perfect_optimum.py").read_bytes()
    require(digest(source) == binding["module_sha256"], "SOURCE_HASH_MISMATCH")
    namespace = {"__name__": "qikvrt_bound_component"}
    exec(compile(source, "upstream/qikvrt_perfect_optimum.py", "exec"), namespace)
    return binding, namespace["evaluate"]


def timestamp(value):
    require(isinstance(value, str), "MISSING_TIMESTAMP")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Invalid("INVALID_TIMESTAMP") from exc
    require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result


def validate_observation(obs, context, kind, policy):
    require(isinstance(obs, dict), "OBSERVATION_OBJECT_REQUIRED")
    require(obs.get("context") == context, "CONTEXT_MISMATCH")
    require(obs.get("data_kind") == kind, "MIXED_DATA_KINDS")
    require(isinstance(obs.get("id"), str) and bool(obs["id"]), "OBSERVATION_ID_REQUIRED")
    when = timestamp(obs.get("observed_at"))
    checks = obs.get("declared_checks")
    require(isinstance(checks, dict) and set(checks) == set(policy["required_checks"]),
            "INCOMPLETE_CHECK_SET")
    require(all(value is True for value in checks.values()), "CHECK_NOT_EXACT_TRUE")
    refs = obs.get("evidence_refs")
    require(isinstance(refs, list) and bool(refs)
            and all(isinstance(x, str) and bool(x.strip()) for x in refs), "EVIDENCE_REFS_REQUIRED")
    persons = obs.get("participants")
    require(isinstance(persons, dict) and set(persons) == set(context["participant_ids"]),
            "PARTICIPANT_SET_MISMATCH")
    metrics, setup = {}, 0
    for person_id, values in sorted(persons.items()):
        require(isinstance(values, dict) and set(values) == set(policy["person_fields"]),
                f"INCOMPLETE_PERSON_METRICS:{person_id}")
        for name, number in values.items():
            require(type(number) in (int, float) and math.isfinite(number) and number >= 0,
                    f"INVALID_NUMBER:{person_id}:{name}")
        require(type(values["errors"]) is int, f"INTEGER_ERRORS_REQUIRED:{person_id}")
        require(type(values["completed_repetitions"]) is int
                and values["completed_repetitions"] == context["task_repetitions"],
                f"INCOMPLETE_TASK:{person_id}")
        total = sum(values[x] for x in ("task_minutes", "coordination_minutes", "setup_minutes"))
        require(math.isfinite(total), f"NON_FINITE_TOTAL:{person_id}")
        metrics[f"{person_id}/total_minutes"] = total
        metrics[f"{person_id}/errors"] = values["errors"]
        setup += values["setup_minutes"]
    require(math.isfinite(setup) and math.isfinite(sum(metrics.values())), "NON_FINITE_AGGREGATE")
    return metrics, setup, when


def assess(payload, root=ROOT):
    binding, evaluate = native_runtime(root)
    policy = read_json(root / "experiment_policy.json")
    policy_sha = digest((root / "experiment_policy.json").read_bytes())
    require(isinstance(payload, dict), "INPUT_OBJECT_REQUIRED")
    require(payload.get("schema") == "qikvrt-cooperation-input/0.2", "INPUT_SCHEMA_MISMATCH")
    require(payload.get("source_binding") == binding, "SOURCE_BINDING_MISMATCH")
    require(payload.get("policy_sha256") == policy_sha, "POLICY_BINDING_MISMATCH")
    kind = payload.get("data_kind")
    require(kind in ("synthetic", "observed"), "UNKNOWN_DATA_KIND")
    report = {
        "schema": "qikvrt-cooperation-report/0.2", "data_kind": kind,
        "source_binding": binding, "policy_sha256": policy_sha,
        "runner_sha256": digest((root / "run_cycle.py").read_bytes()),
        "causal_effect_established": False, "external_effect": "NONE",
        "evidence_refs_automatically_verified": False,
        "claim_scope": "Deskriptiver Vergleich der angegebenen Messwerte; keine Prognose.",
        "selected_intervention": None,
    }
    baseline = payload.get("baseline")
    candidates = payload.get("candidates")
    require(isinstance(candidates, list), "CANDIDATE_LIST_REQUIRED")
    if baseline is None:
        require(not candidates, "CANDIDATES_WITHOUT_BASELINE")
        return dict(report, state="NEED_BASELINE", next_action="Gruppe, Aufgabe und Messfenster festlegen; Ausgangswerte erheben.")
    context = payload.get("context")
    require(isinstance(context, dict), "CONTEXT_REQUIRED")
    require(set(context) == {"experiment_id", "task_id", "task_repetitions", "window_definition", "participant_ids"},
            "CONTEXT_FIELDS_MISMATCH")
    for key in ("experiment_id", "task_id", "window_definition"):
        require(isinstance(context[key], str) and bool(context[key].strip()), f"CONTEXT_REQUIRED:{key}")
    ids = context["participant_ids"]
    require(isinstance(ids, list) and len(ids) >= 2
            and all(isinstance(x, str) and bool(x.strip()) for x in ids)
            and len(set(ids)) == len(ids), "INVALID_PARTICIPANT_IDS")
    require(type(context["task_repetitions"]) is int and context["task_repetitions"] > 0,
            "TASK_REPETITIONS_REQUIRED")
    before, _, baseline_time = validate_observation(baseline, context, kind, policy)
    baseline_sha = observation_hash(baseline)
    report.update(context=context, baseline_sha256=baseline_sha)
    if not candidates:
        return dict(report, state="NEED_OBSERVATIONS", next_action="Eine vereinbarte kleine Änderung erproben und vollständig messen.")
    ids = [x.get("id") if isinstance(x, dict) else None for x in candidates]
    require(all(isinstance(x, str) and bool(x) for x in ids)
            and len(set(ids)) == len(ids) and baseline["id"] not in ids, "INVALID_CANDIDATE_IDS")
    outcome_policy = {"bound_metrics": [{"id": x, "direction": "minimize"} for x in before]}
    eligible, results = {}, []
    for candidate in candidates:
        result = {"id": candidate["id"]}
        try:
            require(candidate.get("baseline_sha256") == baseline_sha, "STALE_BASELINE_BINDING")
            after, setup, candidate_time = validate_observation(candidate, context, kind, policy)
            require(candidate_time > baseline_time, "CANDIDATE_MUST_FOLLOW_BASELINE")
            changes = candidate.get("rule_changes")
            require(type(changes) is int and 1 <= changes <= policy["max_rule_changes"], "RULE_CHANGE_BUDGET")
            require(setup <= policy["max_setup_person_minutes"], "SETUP_BUDGET")
            native = evaluate(before, after, candidate["declared_checks"], outcome_policy)
            gain = sum(before[x] - after[x] for x in before if x.endswith("/total_minutes"))
            result.update(native_decision=native["decision"], findings=native["findings"],
                          observed_net_person_minutes_saved=gain,
                          setup_person_minutes=setup, rule_changes=changes)
            if native["decision"] == "ACCEPT_CANDIDATE":
                eligible[candidate["id"]] = dict(after, setup_person_minutes=setup, rule_changes=changes)
                result["state"] = "ELIGIBLE_FOR_COMPARISON"
            else:
                result["state"] = "HOLD"
        except Invalid as exc:
            result.update(state="HOLD", findings=[str(exc)])
        results.append(result)
    frontier = []
    dominance_policy = {"bound_metrics": outcome_policy["bound_metrics"] + [
        {"id": "setup_person_minutes", "direction": "minimize"},
        {"id": "rule_changes", "direction": "minimize"},
    ]}
    # Costs constrain comparison among improving interventions. Comparing a new
    # setup cost directly against a zero-cost baseline would reject every change.
    for candidate_id, metrics in eligible.items():
        dominators = sorted(other_id for other_id, other in eligible.items()
                            if other_id != candidate_id and evaluate(
                                metrics, other, {"validated_inputs": True}, dominance_policy
                            )["decision"] == "ACCEPT_CANDIDATE")
        result = next(x for x in results if x["id"] == candidate_id)
        result["dominated_by"] = dominators
        result["state"] = "DOMINATED" if dominators else "FRONTIER"
        if not dominators:
            frontier.append(candidate_id)
    return dict(report, state="SYNTHETIC_DEMONSTRATION" if kind == "synthetic" else "DESCRIPTIVE_COMPARISON",
                candidates=results, frontier=sorted(frontier),
                next_action="Zielkonflikte gemeinsam abwägen; nächsten Versuch vereinbaren und neu messen.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = assess(read_json(args.input))
        report["input_sha256"] = digest(args.input.read_bytes())
        code = 0
    except (Invalid, ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
        report = {"state": "HOLD", "error": str(exc), "external_effect": "NONE"}
        code = 2
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
