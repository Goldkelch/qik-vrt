#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
VECTOR_FILE = ROOT / "conformance/temdd/interoperability-vectors-v1.json"
IMPLEMENTATIONS = (
    ("python", (sys.executable, str(ROOT / "conformance/temdd/interop_impl_python.py")), "conformance/temdd/interop_impl_python.py"),
    ("node", ("node", str(ROOT / "conformance/temdd/interop_impl_node.js")), "conformance/temdd/interop_impl_node.js"),
)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)

def exact_subject(repository: str) -> dict:
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    require(len(head) == 40 and len(tree) == 40, "EXACT_SUBJECT_UNBOUND")
    subprocess.check_call(["git", "-C", str(ROOT), "diff", "--quiet"])
    subprocess.check_call(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"])
    return {"repository": repository, "head": head, "tree": tree}

def run_implementation(command: tuple[str, ...], value: dict) -> dict:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    proc = subprocess.run(
        list(command), cwd=ROOT, input=payload, text=True,
        capture_output=True, check=False,
    )
    require(proc.returncode == 0, "IMPLEMENTATION_EXECUTION_FAILED:" + proc.stderr.strip())
    result = json.loads(proc.stdout)
    require(set(result) == {"canonical", "decision"}, "IMPLEMENTATION_RESULT_SHAPE_INVALID")
    require(isinstance(result["canonical"], str), "IMPLEMENTATION_CANONICAL_NOT_STRING")
    require(result["decision"] in {"ACCEPT", "REJECT", "HOLD_UNVERIFIED"}, "IMPLEMENTATION_DECISION_DOMAIN_INVALID")
    return result

def build_report(repository: str) -> dict:
    subject_value = exact_subject(repository)
    vectors_raw = VECTOR_FILE.read_bytes()
    vectors = json.loads(vectors_raw)
    require(vectors.get("schema") == "temdd_interoperability_vectors_v1", "VECTOR_SCHEMA_MISMATCH")
    require(vectors.get("canonical_profile") == "temdd_canonical_json_v1", "CANONICAL_PROFILE_MISMATCH")
    require(vectors.get("evaluation_semantics") == "temdd_decision_v1", "EVALUATION_SEMANTICS_MISMATCH")
    cases = vectors.get("vectors")
    require(isinstance(cases, list) and cases, "CONFORMANCE_VECTORS_REQUIRED")

    impl_meta = []
    for implementation_id, command, relpath in IMPLEMENTATIONS:
        path = ROOT / relpath
        impl_meta.append({
            "id": implementation_id,
            "runtime": command[0],
            "path": relpath,
            "sha256": "sha256:" + sha256_bytes(path.read_bytes()),
        })
    require(len({x["path"] for x in impl_meta}) == len(impl_meta), "IMPLEMENTATION_PATHS_NOT_DISTINCT")
    require(len({x["runtime"] for x in impl_meta}) == len(impl_meta), "IMPLEMENTATION_RUNTIMES_NOT_DISTINCT")

    case_reports = []
    for case in cases:
        case_id = case.get("id")
        value = case.get("input")
        expected_canonical = case.get("expected_canonical")
        expected_decision = case.get("expected_decision")
        require(isinstance(case_id, str) and case_id, "VECTOR_ID_REQUIRED")
        require(isinstance(value, dict), "VECTOR_INPUT_OBJECT_REQUIRED:" + case_id)
        require(isinstance(expected_canonical, str), "EXPECTED_CANONICAL_REQUIRED:" + case_id)
        require(expected_decision in {"ACCEPT", "REJECT", "HOLD_UNVERIFIED"}, "EXPECTED_DECISION_INVALID:" + case_id)

        observations = []
        for implementation_id, command, _ in IMPLEMENTATIONS:
            observed = run_implementation(command, value)
            require(observed["canonical"] == expected_canonical, "CANONICAL_BYTES_MISMATCH:" + case_id + ":" + implementation_id)
            require(observed["decision"] == expected_decision, "EXPECTED_DECISION_MISMATCH:" + case_id + ":" + implementation_id)
            observations.append({
                "implementation": implementation_id,
                "canonical_sha256": "sha256:" + sha256_bytes(observed["canonical"].encode("utf-8")),
                "decision": observed["decision"],
            })

        require(len({x["canonical_sha256"] for x in observations}) == 1, "IMPLEMENTATION_CANONICAL_DIVERGENCE:" + case_id)
        require(len({x["decision"] for x in observations}) == 1, "IMPLEMENTATION_DECISION_DIVERGENCE:" + case_id)
        case_reports.append({
            "id": case_id,
            "expected_decision": expected_decision,
            "canonical_sha256": "sha256:" + sha256_bytes(expected_canonical.encode("utf-8")),
            "implementations": observations,
            "status": "PASS",
        })

    return {
        "schema": "temdd_interoperability_proof_v1",
        "subject": subject_value,
        "canonical_profile": "temdd_canonical_json_v1",
        "evaluation_semantics": "temdd_decision_v1",
        "vector_set_digest": "sha256:" + sha256_bytes(vectors_raw),
        "implementations": impl_meta,
        "vectors": case_reports,
        "machine_verifiable_standard": "PASS",
        "canonical_serialization": "PASS",
        "deterministic_evaluation": "PASS",
        "conformance_vectors": "PASS",
        "independent_implementation_execution": "PASS",
        "identical_expected_decisions": "PASS",
        "overall": "INTEROPERABILITY_BY_EXECUTABLE_PROOF",
        "independence_scope": "distinct source files, runtimes and subprocesses; organizational or authorship independence is not claimed",
        "predecessor_evidence_transfer": False,
        "effect_ack_done": False,
    }

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default="Goldkelch/qik-vrt")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        report = build_report(args.repository)
    except Exception as exc:
        print("HOLD_UNVERIFIED " + str(exc), file=sys.stderr)
        return 2
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
