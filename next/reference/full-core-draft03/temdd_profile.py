#!/usr/bin/env python3
"""Explicit finite-expression execution profile for TEMDD relation sources.

The existing parser and v1 adapter supply canonical IR. This interpreter
evaluates only a bounded, pure expression grammar; it does not import the
neutral oracle or any of the other five carriers.
"""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.temdd.v1_adapter import adapt


def expression(text, names):
    def build(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, bool):
            if type(node.value) is int and not 0 <= node.value <= 262143:
                raise ValueError("literal outside finite profile")
            return lambda env: node.value
        if isinstance(node, ast.Name) and node.id in names:
            return lambda env: env[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd):
            left, right = build(node.left), build(node.right)
            return lambda env: left(env) & right(env)
        if isinstance(node, ast.BoolOp):
            values = [build(value) for value in node.values]
            if isinstance(node.op, ast.And):
                return lambda env: all(value(env) for value in values)
            if isinstance(node.op, ast.Or):
                return lambda env: any(value(env) for value in values)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = build(node.left), build(node.comparators[0])
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                return lambda env: left(env) == right(env)
            if isinstance(op, ast.NotEq):
                return lambda env: left(env) != right(env)
            if isinstance(op, ast.Gt):
                return lambda env: left(env) > right(env)
        raise ValueError("unsupported expression in finite TEMDD profile")
    if len(text) > 1024:
        raise ValueError("oversized expression")
    return build(ast.parse(text, mode="eval").body)


def programs(ir):
    if ir.get("schema") != "temdd_ir_v1":
        raise ValueError("expected canonical TEMDD IR")
    if ir.get("request", {}).get("target") != "FULL_DRAFT03_FINITE":
        raise ValueError("wrong TEMDD profile target")
    groups = {"first_match_core": [], "first_match_admission": []}
    relation_names = set()
    seen = set()
    relations = sorted(ir["relations"], key=lambda item: item["source_order"])
    for item in relations:
        if item["name"] in relation_names:
            raise ValueError("duplicate TEMDD relation name")
        relation_names.add(item["name"])
        order = item["source_order"]
        if type(order) is not int or order in seen:
            raise ValueError("duplicate or invalid source order")
        seen.add(order)
        if item["epistemic"] != "TRUE" or item["freshness"] != "FRESH":
            raise ValueError("unusable TEMDD assertion")
        predicate = item["predicate"]
        if predicate not in groups:
            raise ValueError("unknown relation predicate")
        names = {"m", "r", "d"} if predicate == "first_match_core" else {"derived", "declared", "m"}
        target = int(item["target"])
        if str(target) != item["target"] or not 0 <= target <= (5 if predicate == "first_match_core" else 1):
            raise ValueError("invalid relation target")
        groups[predicate].append((expression(item["source"], names), target))
    if not all(groups.values()):
        raise ValueError("missing relation family")
    return groups


def evaluate(program, env):
    for condition, target in program:
        if condition(env):
            return target
    raise ValueError("uncovered TEMDD input")


def render(ir):
    groups = programs(ir)
    out = bytearray()
    env = {}
    for m in range(262144):
        env["m"] = m
        for r in range(6):
            env["r"] = r
            for d in range(6):
                env["d"] = d
                out.append(48 + evaluate(groups["first_match_core"], env))
    for derived in range(6):
        env["derived"] = derived
        for declared in range(6):
            env["declared"] = declared
            for m in range(512):
                env["m"] = m
                out.append(48 + evaluate(groups["first_match_admission"], env))
    return bytes(out)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: temdd_profile.py source.temdd output ir.json")
    ir = adapt(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path(sys.argv[3]).write_text(json.dumps(ir, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(sys.argv[2]).write_bytes(render(ir))
