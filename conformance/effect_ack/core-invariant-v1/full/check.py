#!/usr/bin/env python3
"""Interpret the frozen declarative cubes and compare six complete streams."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

CONTRACT_SHA256 = "0c7dc0f5b27d4c7879f56afcfb58c1a64b406ea33a926481490df7142f61186a"
CORE_CASES = 9437184
CONSUMER_CASES = 18432
CARRIERS = frozenset(("c90", "m68000", "smalltalk", "temdd", "lean", "ada_spark"))


def digest(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def compile_cubes(rules, first, second, result):
    return [(sum(1 << n for n in rule.get("ones", [])),
             sum(1 << n for n in rule.get("zeros", [])),
             frozenset(rule.get(first, range(6))),
             frozenset(rule.get(second, range(6))), rule[result])
            for rule in rules]


def lookup(cubes, mask, first, second):
    for ones, zeros, allowed_first, allowed_second, value in cubes:
        if mask & ones == ones and mask & zeros == 0 and first in allowed_first and second in allowed_second:
            return value
    raise ValueError("neutral contract has an uncovered input")


def expected(contract):
    core = compile_cubes(contract["core_rules"], "risk", "decision", "state")
    consumer = compile_cubes(contract["consumer_rules"], "derived", "declared", "release")
    output = bytearray()
    for mask in range(262144):
        # Partial evaluation of declarative masks only, with no carrier import.
        applicable = [cube for cube in core if mask & cube[0] == cube[0] and mask & cube[1] == 0]
        for risk in range(6):
            for decision in range(6):
                output.append(48 + lookup(applicable, mask, risk, decision))
    for derived in range(6):
        for declared in range(6):
            for mask in range(512):
                output.append(48 + lookup(consumer, mask, derived, declared))
    return bytes(output)


def input_set_digests():
    """Hash the declared ordered inputs, independently of carrier outputs."""
    core = hashlib.sha256()
    suffixes = [bytes((risk, decision)) for risk in range(6) for decision in range(6)]
    for mask in range(262144):
        prefix = mask.to_bytes(3, "big")
        core.update(b"".join(prefix + suffix for suffix in suffixes))
    consumer = hashlib.sha256()
    for derived in range(6):
        for declared in range(6):
            prefix = bytes((derived, declared))
            consumer.update(b"".join(prefix + mask.to_bytes(2, "big") for mask in range(512)))
    return {
        "core": {"sha256": core.hexdigest(), "bytes": CORE_CASES * 5,
                 "encoding": "mask:u24be,risk:u8,decision:u8; contract order"},
        "consumer": {"sha256": consumer.hexdigest(), "bytes": CONSUMER_CASES * 4,
                     "encoding": "derived:u8,declared:u8,mask:u16be; contract order"},
        "scope": "canonical declared enumeration, not separately instrumented carrier input traces",
    }


def carrier_paths(paths):
    names = [path.stem for path in paths]
    if len(names) != len(CARRIERS) or set(names) != CARRIERS:
        raise ValueError("require exactly the six distinct carrier streams")
    if len({path.resolve() for path in paths}) != len(CARRIERS):
        raise ValueError("aliased carrier paths")
    return dict(zip(names, paths))


def compare_bytes(actual, oracle):
    if len(actual) != CORE_CASES + CONSUMER_CASES:
        raise ValueError("truncated, extended or malformed carrier domain")
    if actual != oracle:
        index = next(i for i, (a, b) in enumerate(zip(actual, oracle)) if a != b)
        if index < CORE_CASES:
            mask, rem = divmod(index, 36)
            risk, decision = divmod(rem, 6)
            case = f"core mask={mask} risk={risk} decision={decision}"
        else:
            pair, mask = divmod(index - CORE_CASES, 512)
            derived, declared = divmod(pair, 6)
            case = f"consumer derived={derived} declared={declared} mask={mask}"
        raise ValueError(f"divergence at {case}: got byte {actual[index]}, expected {oracle[index]}")


def check_proofs(directory):
    evidence = {}
    for name, marker, token in (
        ("lean.log", "lean.marker", "QIKVRT_FULL_LEAN_PASS"),
        ("spark.log", "spark.marker", "QIKVRT_FULL_SPARK_PASS"),
    ):
        if (directory / marker).read_text().strip() != token:
            raise ValueError("missing successful workflow proof receipt")
        text = (directory / name).read_text()
        if not text.strip():
            raise ValueError("empty proof log")
        if name == "lean.log":
            if "sorryAx" in text or "declaration uses 'sorry'" in text:
                raise ValueError("Lean proof hole")
            for theorem in ("choose_contract_iff", "core_correct", "choose_done_iff", "core_done_iff", "admission_iff",
                            "positive_done", "positive_admission",
                            "transport_alone_insufficient", "composition_refinement"):
                if "QIKVRT.FullDraft03." + theorem not in text:
                    raise ValueError("missing Lean theorem axiom audit: " + theorem)
        if name == "spark.log" and "Summary" not in text:
            raise ValueError("missing complete GNATprove summary")
        evidence[name] = digest(directory / name)
        evidence[marker] = digest(directory / marker)
    return evidence


def compare(args):
    if not all(re.fullmatch(r"[a-f0-9]{40}", value) for value in (args.head, args.tree)):
        raise ValueError("invalid exact subject")
    if digest(args.contract)["sha256"] != CONTRACT_SHA256:
        raise ValueError("frozen contract changed")
    contract = json.loads(args.contract.read_text())
    paths = carrier_paths(list(args.directory / (name + ".out") for name in sorted(CARRIERS)))
    oracle = expected(contract)
    if len(oracle) != CORE_CASES + CONSUMER_CASES or oracle[:CORE_CASES].count(b"2") != 4 or oracle[CORE_CASES:].count(b"1") != 1:
        raise ValueError("neutral domain or positive witness corrupted")
    backends = {}
    for name, path in paths.items():
        compare_bytes(path.read_bytes(), oracle)
        backends[name] = {"result": "PASS", "evidence": digest(path)}
    proofs = check_proofs(args.directory)
    return {
        "schema": "qikvrt_full_finite_cross_conformance_v1",
        "subject": {"head": args.head, "tree": args.tree},
        "contract": digest(args.contract),
        "contract_frozen_before_carrier_commit": "62ce6932adfc5f557034be9b9f5662c52ff02c5c",
        "oracle_sha256": hashlib.sha256(oracle).hexdigest(),
        "input_sets": input_set_digests(),
        "core_output_bound": {"minimum": 0, "exclusive_maximum": 6},
        "core": {"cases": CORE_CASES, "boolean_inputs": 18, "risk_classes": 6,
                 "decision_classes": 6, "exhaustive": True,
                 "result_counts": {chr(k): v for k, v in sorted(Counter(oracle[:CORE_CASES]).items())}},
        "consumer": {"cases": CONSUMER_CASES, "validator_bits": 9,
                     "derived_classes": 6, "declared_classes": 6,
                     "exhaustive": True, "positive_cases": 1},
        "backends": backends, "proof_receipts": proofs,
        "composition": "Kernel-checked substitution theorem plus finite component equality and core output bound < 6; full Cartesian product not individually executed.",
        "proof_receipts_require_trusted_workflow": True,
        "independent_reviewer": "NOT_ESTABLISHED",
        "validator_implementations_verified": False,
        "physical_claims_verified": False,
        "implementation_used_as_oracle": False,
        "predecessor_evidence_transfer": False,
        "forecast_resolved": False,
        "overall": "PASS",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    inputs = {args.contract.resolve()} | {(args.directory / name).resolve()
        for name in [*(carrier + ".out" for carrier in CARRIERS),
                     "lean.log", "spark.log", "lean.marker", "spark.marker"]}
    if args.output.resolve() in inputs:
        parser.error("output would overwrite evidence")
    try:
        result = compare(args)
        code = 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": "qikvrt_full_finite_cross_conformance_v1",
                  "subject": {"head": args.head, "tree": args.tree},
                  "overall": "FAIL", "error": str(exc), "forecast_resolved": False}
        code = 1
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), file=sys.stdout if code == 0 else sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
