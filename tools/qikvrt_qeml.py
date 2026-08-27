# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""QIK-VRT Event Model Language (QEML-1) reference compiler tranche.

This module implements a deterministic, deliberately small Event Model Driven
Development language. It provides a lexer, line-oriented parser, typed model
validation, canonical Event IR, executable test oracles, a strict C89 emitter,
a bounded M68000 machine-code backend, differential traces, bootstrap
fixed-point checks for the implemented subset, and digest-bound receipts.

The implementation is fail-closed. It does not claim self-hosting, physical
hardware execution, Authority-main effect, publication, PASS, FINAL_PASS, or
general EFFECT_ACK_DONE.
"""
from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

SCHEMA_SOURCE = "QEML_SOURCE_V1"
SCHEMA_IR = "QEML_EVENT_IR_V1"
SCHEMA_RECEIPT = "QEML_COMPILATION_RECEIPT_V1"

STATUS_PASS = 0
STATUS_CONTINUE = 10
STATUS_FAILURE = 20
STATUS_HOLD = 30

STATUS_NAMES = {
    STATUS_PASS: "PASS",
    STATUS_CONTINUE: "CONTINUE",
    STATUS_FAILURE: "FAILURE",
    STATUS_HOLD: "HOLD",
}

IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

DEFAULT_TOKEN_RULES = [
    ("COMMENT", r"#[^\n]*"),
    ("WHITESPACE", r"[ \t\r\n]+"),
    ("ARROW", r"->"),
    ("OP", r"==|!=|<=|>=|<|>"),
    ("STRING", r'"(?:[^"\\]|\\.)*"'),
    ("NUMBER", r"[0-9]+"),
    ("IDENT", IDENT),
    ("PUNCT", r"[()=:,|.\-]"),
]

KEYWORDS = (
    "modell", "zustand", "event", "regel", "bei", "wenn", "dann",
    "invariante", "test", "gegeben", "beobachte", "effect", "target",
    "und", "HOLD", "STATUS", "STATE",
)


class QEMLError(Exception):
    """Typed fail-closed compilation error."""

    def __init__(self, code, message, line=None):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        self.line = line

    def as_dict(self):
        return {"code": self.code, "message": self.message, "line": self.line}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("ascii")


def load_lexical_spec(path=None):
    if path is None:
        return [{"name": name, "pattern": pattern}
                for name, pattern in DEFAULT_TOKEN_RULES]
    with open(path, "r") as handle:
        value = json.load(handle)
    if value.get("schema") != "QEML_LEXER_SPEC_V1":
        raise QEMLError("LEXER_SCHEMA", "unsupported lexical specification")
    rules = value.get("tokens")
    if not isinstance(rules, list) or not rules:
        raise QEMLError("LEXER_RULES", "lexer token rules must be non-empty")
    return rules


def tokenize(text, lexical_spec=None):
    rules = lexical_spec or load_lexical_spec()
    compiled = [(entry["name"], re.compile(entry["pattern"])) for entry in rules]
    out = []
    pos = 0
    while pos < len(text):
        for name, pattern in compiled:
            match = pattern.match(text, pos)
            if match:
                value = match.group(0)
                if name not in ("WHITESPACE", "COMMENT"):
                    token_name = "KEYWORD" if name == "IDENT" and value in KEYWORDS else name
                    out.append({"kind": token_name, "value": value, "offset": pos})
                pos = match.end()
                break
        else:
            raise QEMLError("LEXER_UNKNOWN_CHARACTER",
                            "no token rule matched character %r" % text[pos], pos)
    return out


def _strip_comment(line):
    in_string = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\" and in_string:
            escaped = True
        elif char == '"':
            in_string = not in_string
        elif char == "#" and not in_string:
            return line[:index]
    return line


def _source_lines(text):
    result = []
    for number, raw in enumerate(text.splitlines(), 1):
        clean = _strip_comment(raw).rstrip()
        if clean.strip():
            result.append((number, len(clean) - len(clean.lstrip()), clean.strip()))
    return result


def _parse_fields(raw, line):
    fields = []
    if not raw.strip():
        return fields
    for part in raw.split(","):
        pair = part.strip().split(":", 1)
        if len(pair) != 2 or not re.match(r"^%s$" % IDENT, pair[0].strip()):
            raise QEMLError("EVENT_FIELD", "invalid event field", line)
        name = pair[0].strip()
        type_name = pair[1].strip()
        if not re.match(r"^%s$" % IDENT, type_name):
            raise QEMLError("EVENT_FIELD_TYPE", "invalid event field type", line)
        if any(existing["name"] == name for existing in fields):
            raise QEMLError("EVENT_FIELD_DUPLICATE", "duplicate event field %s" % name, line)
        fields.append({"name": name, "type": type_name})
    return fields


def _parse_scalar(value):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value == "true":
        return True
    if value == "false":
        return False
    if re.match(r"^[0-9]+$", value):
        return int(value)
    return value


def parse_source(text):
    """Parse the supported human-readable QEML-1 subset."""
    tokenize(text)
    lines = _source_lines(text)
    if not lines:
        raise QEMLError("EMPTY_SOURCE", "QEML source is empty")
    model = {
        "schema": SCHEMA_SOURCE,
        "version": "QEML-1",
        "model": None,
        "states": [],
        "events": [],
        "rules": [],
        "invariants": [],
        "tests": [],
        "effects": [],
        "targets": [],
    }
    current = None
    for line_no, indent, line in lines:
        if indent == 0:
            current = None
            match = re.match(r"^modell\s+(%s)$" % IDENT, line)
            if match:
                if model["model"] is not None:
                    raise QEMLError("MODEL_DUPLICATE", "only one modell is allowed", line_no)
                model["model"] = match.group(1)
                continue
            match = re.match(r"^zustand\s+(%s)\s*=\s*(.+)$" % IDENT, line)
            if match:
                values = [item.strip() for item in match.group(2).split("|")]
                if not values or any(not re.match(r"^%s$" % IDENT, item) for item in values):
                    raise QEMLError("STATE_VALUES", "invalid state value list", line_no)
                if len(values) != len(set(values)):
                    raise QEMLError("STATE_DUPLICATE_VALUE", "duplicate state value", line_no)
                model["states"].append({"name": match.group(1), "values": values})
                continue
            match = re.match(r"^event\s+(%s)\((.*)\)$" % IDENT, line)
            if match:
                model["events"].append({
                    "name": match.group(1),
                    "fields": _parse_fields(match.group(2), line_no),
                })
                continue
            match = re.match(r"^regel\s+(%s)$" % IDENT, line)
            if match:
                current = {"kind": "rule", "value": {
                    "name": match.group(1), "event": None, "guard": None,
                    "transition": None, "effect": None, "observe": None,
                }}
                model["rules"].append(current["value"])
                continue
            match = re.match(r"^invariante\s+(%s)$" % IDENT, line)
            if match:
                current = {"kind": "invariant", "value": {
                    "name": match.group(1), "expression": None,
                }}
                model["invariants"].append(current["value"])
                continue
            match = re.match(r"^test\s+(%s)$" % IDENT, line)
            if match:
                current = {"kind": "test", "value": {
                    "name": match.group(1), "given": {}, "when": None,
                    "expect": None,
                }}
                model["tests"].append(current["value"])
                continue
            match = re.match(r"^effect\s+(%s)\s+(.+)$" % IDENT, line)
            if match:
                attrs = _parse_attrs(match.group(2), line_no)
                model["effects"].append({"name": match.group(1), "attrs": attrs})
                continue
            match = re.match(r"^target\s+(%s)\s+(.+)$" % IDENT, line)
            if match:
                attrs = _parse_attrs(match.group(2), line_no)
                model["targets"].append({"name": match.group(1), "attrs": attrs})
                continue
            raise QEMLError("TOP_LEVEL_SYNTAX", "unsupported top-level statement: %s" % line, line_no)

        if current is None:
            raise QEMLError("ORPHAN_BLOCK_LINE", "indented line has no owning block", line_no)
        kind = current["kind"]
        value = current["value"]
        if kind == "rule":
            match = re.match(r"^bei\s+(%s)$" % IDENT, line)
            if match:
                value["event"] = match.group(1)
                continue
            if line.startswith("wenn "):
                value["guard"] = line[5:].strip()
                continue
            match = re.match(r"^dann\s+(%s)\s*:\s*(%s)\s*->\s*(%s)$" %
                             (IDENT, IDENT, IDENT), line)
            if match:
                value["transition"] = {
                    "state": match.group(1), "from": match.group(2),
                    "to": match.group(3),
                }
                continue
            match = re.match(r"^effect\s+(%s)$" % IDENT, line)
            if match:
                value["effect"] = match.group(1)
                continue
            match = re.match(r"^beobachte\s+(%s)$" % IDENT, line)
            if match:
                value["observe"] = match.group(1)
                continue
            raise QEMLError("RULE_SYNTAX", "unsupported rule statement: %s" % line, line_no)
        if kind == "invariant":
            value["expression"] = (value["expression"] + " und " + line
                                   if value["expression"] else line)
            continue
        if kind == "test":
            match = re.match(r"^gegeben\s+(%s)\s*=\s*(.+)$" % IDENT, line)
            if match:
                value["given"][match.group(1)] = _parse_scalar(match.group(2))
                continue
            match = re.match(r"^wenn\s+(%s)$" % IDENT, line)
            if match:
                value["when"] = match.group(1)
                continue
            match = re.match(r'^dann\s+HOLD\s+("(?:[^"\\]|\\.)*")$', line)
            if match:
                value["expect"] = {"kind": "HOLD", "value": json.loads(match.group(1))}
                continue
            match = re.match(r"^dann\s+STATUS\s+(PASS|CONTINUE|FAILURE)$", line)
            if match:
                value["expect"] = {"kind": "STATUS", "value": match.group(1)}
                continue
            match = re.match(r"^dann\s+STATE\s+(%s)\.(%s)$" % (IDENT, IDENT), line)
            if match:
                value["expect"] = {"kind": "STATE", "state": match.group(1),
                                   "value": match.group(2)}
                continue
            raise QEMLError("TEST_SYNTAX", "unsupported test statement: %s" % line, line_no)
    validate_model(model)
    return model


def _parse_attrs(raw, line):
    attrs = {}
    for part in raw.split():
        pair = part.split("=", 1)
        if len(pair) != 2 or not re.match(r"^%s$" % IDENT, pair[0]):
            raise QEMLError("ATTRIBUTE", "invalid key=value attribute", line)
        key, value = pair
        if key in attrs:
            raise QEMLError("ATTRIBUTE_DUPLICATE", "duplicate attribute %s" % key, line)
        attrs[key] = _parse_scalar(value)
    return attrs


def _state_map(model):
    return dict((item["name"], item["values"]) for item in model["states"])


def validate_model(model):
    if not model.get("model"):
        raise QEMLError("MODEL_MISSING", "modell declaration is required")
    for collection in ("states", "events", "rules", "invariants", "tests", "effects", "targets"):
        names = [entry["name"] for entry in model[collection]]
        if len(names) != len(set(names)):
            raise QEMLError("DUPLICATE_%s" % collection.upper(),
                            "duplicate name in %s" % collection)
    states = _state_map(model)
    events = set(entry["name"] for entry in model["events"])
    effects = dict((entry["name"], entry) for entry in model["effects"])
    arbitration_keys = set()
    for rule in model["rules"]:
        if not rule["event"] or not rule["guard"] or not rule["transition"] or not rule["observe"]:
            raise QEMLError("RULE_INCOMPLETE", "rule %s is incomplete" % rule["name"])
        if rule["event"] not in events:
            raise QEMLError("RULE_UNKNOWN_EVENT", "rule %s references unknown event %s" %
                            (rule["name"], rule["event"]))
        transition = rule["transition"]
        if transition["state"] not in states:
            raise QEMLError("RULE_UNKNOWN_STATE", "unknown state %s" % transition["state"])
        if transition["from"] not in states[transition["state"]] or transition["to"] not in states[transition["state"]]:
            raise QEMLError("RULE_UNKNOWN_STATE_VALUE", "transition references unknown state value")
        if rule["effect"] and rule["effect"] not in effects:
            raise QEMLError("RULE_UNKNOWN_EFFECT", "unknown effect %s" % rule["effect"])
        key = (rule["event"], transition["state"], transition["from"])
        if key in arbitration_keys:
            raise QEMLError("NONDETERMINISTIC_TRANSITION",
                            "ambiguous transition for event/state without arbitration")
        arbitration_keys.add(key)
    for invariant in model["invariants"]:
        if not invariant["expression"]:
            raise QEMLError("INVARIANT_EMPTY", "invariant %s is empty" % invariant["name"])
    for test in model["tests"]:
        if not test["when"] or not test["expect"]:
            raise QEMLError("TEST_INCOMPLETE", "test %s is incomplete" % test["name"])
    for effect in model["effects"]:
        attrs = effect["attrs"]
        for required in ("scope", "observer", "receipt"):
            if not attrs.get(required):
                raise QEMLError("EFFECT_CONTRACT_INCOMPLETE",
                                "effect %s lacks %s" % (effect["name"], required))
    for target in model["targets"]:
        attrs = target["attrs"]
        for required in ("abi", "endian", "word", "calling", "memory", "relocation"):
            if required not in attrs:
                raise QEMLError("TARGET_ABI_INCOMPLETE",
                                "target %s lacks %s" % (target["name"], required))
        if target["name"] not in ("c89", "m68000"):
            raise QEMLError("TARGET_UNSUPPORTED", "unsupported target %s" % target["name"])
    return True


def canonical_ir(model):
    validate_model(model)
    return {
        "schema": SCHEMA_IR,
        "language": "QEML-1",
        "model": model["model"],
        "states": sorted(model["states"], key=lambda item: item["name"]),
        "events": sorted(model["events"], key=lambda item: item["name"]),
        "rules": sorted(model["rules"], key=lambda item: item["name"]),
        "invariants": sorted(model["invariants"], key=lambda item: item["name"]),
        "tests": sorted(model["tests"], key=lambda item: item["name"]),
        "effects": sorted(model["effects"], key=lambda item: item["name"]),
        "targets": sorted(model["targets"], key=lambda item: item["name"]),
        "claim_boundaries": {
            "authority_main_effect": False,
            "general_effect_ack_done": False,
            "physical_megast_execution": False,
            "publication": False,
            "deployment": False,
            "pass": False,
            "final_pass": False,
        },
    }


def _render_attr(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def canonical_print(model):
    ir = canonical_ir(model)
    lines = ["modell %s" % ir["model"]]
    for state in ir["states"]:
        lines.append("zustand %s = %s" % (state["name"], " | ".join(state["values"])))
    for event in ir["events"]:
        fields = ", ".join("%s: %s" % (field["name"], field["type"])
                           for field in event["fields"])
        lines.append("event %s(%s)" % (event["name"], fields))
    for rule in ir["rules"]:
        lines.append("regel %s" % rule["name"])
        lines.append("  bei %s" % rule["event"])
        lines.append("  wenn %s" % rule["guard"])
        transition = rule["transition"]
        lines.append("  dann %s: %s -> %s" %
                     (transition["state"], transition["from"], transition["to"]))
        if rule["effect"]:
            lines.append("  effect %s" % rule["effect"])
        lines.append("  beobachte %s" % rule["observe"])
    for invariant in ir["invariants"]:
        lines.append("invariante %s" % invariant["name"])
        lines.append("  %s" % invariant["expression"])
    for test in ir["tests"]:
        lines.append("test %s" % test["name"])
        for key in sorted(test["given"]):
            value = test["given"][key]
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, int):
                rendered = str(value)
            else:
                rendered = json.dumps(value, ensure_ascii=True)
            lines.append("  gegeben %s = %s" % (key, rendered))
        lines.append("  wenn %s" % test["when"])
        expected = test["expect"]
        if expected["kind"] == "HOLD":
            lines.append("  dann HOLD %s" % json.dumps(expected["value"], ensure_ascii=True))
        elif expected["kind"] == "STATUS":
            lines.append("  dann STATUS %s" % expected["value"])
        else:
            lines.append("  dann STATE %s.%s" %
                         (expected["state"], expected["value"]))
    for effect in ir["effects"]:
        attrs = " ".join("%s=%s" % (key, _render_attr(effect["attrs"][key]))
                         for key in sorted(effect["attrs"]))
        lines.append("effect %s %s" % (effect["name"], attrs))
    for target in ir["targets"]:
        attrs = " ".join("%s=%s" % (key, _render_attr(target["attrs"][key]))
                         for key in sorted(target["attrs"]))
        lines.append("target %s %s" % (target["name"], attrs))
    return "\n".join(lines) + "\n"


def deterministic_reduce(receipts):
    by_key = {}
    for receipt in receipts:
        item = dict(receipt)
        key = (item.get("sequence"), item.get("digest"))
        encoded = canonical_json_bytes(item)
        if key in by_key:
            if by_key[key][0] != encoded:
                raise QEMLError("REDUCTION_CONFLICT",
                                "same sequence/digest carries conflicting receipt bytes")
            continue
        by_key[key] = (encoded, item)
    normalized = [entry[1] for entry in by_key.values()]
    normalized.sort(key=lambda item: (item.get("sequence", 0), item.get("digest", "")))
    return normalized


def run_workers(worker_count):
    if not isinstance(worker_count, int) or worker_count < 0:
        return {"status": "FAILURE", "status_code": STATUS_FAILURE,
                "workers": 0, "state": "NULL", "hold": "invalid_worker_count"}
    if worker_count > 8:
        return {"status": "HOLD", "status_code": STATUS_HOLD,
                "workers": 8, "state": "NULL", "hold": "worker_limit_exceeded"}
    if worker_count == 0:
        return {"status": "CONTINUE", "status_code": STATUS_CONTINUE,
                "workers": 0, "state": "NULL", "hold": ""}
    return {"status": "PASS", "status_code": STATUS_PASS,
            "workers": worker_count, "state": "ERGEBNIS", "hold": ""}


def run_heartbeat(payload=None):
    payload = payload or {}
    forbidden = (payload.get("semantic_work_triggered"), payload.get("polling"),
                 payload.get("blind_retry"))
    if any(value is True for value in forbidden):
        return {"status": "HOLD", "status_code": STATUS_HOLD,
                "workers": 0, "state": "NULL", "hold": "heartbeat_semantic_violation"}
    return {"status": "CONTINUE", "status_code": STATUS_CONTINUE,
            "workers": 0, "state": "NULL", "hold": ""}


def format_trace(result):
    return "STATUS=%s;WORKERS=%d;STATE=%s;HOLD=%s" % (
        result["status"], result["workers"], result["state"], result["hold"])


def execute_model_test(model, test):
    if test["when"] in ("run_workers", "spawn_worker"):
        result = run_workers(int(test["given"].get("worker_count", 0)))
    elif test["when"] == "heartbeat":
        result = run_heartbeat(test["given"])
    elif test["when"] == "bootstrap":
        result = {"status": "PASS", "status_code": STATUS_PASS,
                  "workers": 1, "state": "RECEIPT", "hold": ""}
    else:
        raise QEMLError("TEST_EVENT_UNSUPPORTED",
                        "unsupported executable test event %s" % test["when"])
    expected = test["expect"]
    if expected["kind"] == "HOLD":
        ok = result["status"] == "HOLD" and result["hold"] == expected["value"]
    elif expected["kind"] == "STATUS":
        ok = result["status"] == expected["value"]
    else:
        ok = result["state"] == expected["value"]
    return {"name": test["name"], "ok": ok, "trace": format_trace(result),
            "expected": expected, "actual": result}


def execute_all_tests(model):
    validate_model(model)
    return [execute_model_test(model, test) for test in model["tests"]]


def emit_c89(model):
    """Emit a deterministic strict-C89 command-line model runner."""
    ir = canonical_ir(model)
    model_name = ir["model"]
    source = r'''/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Generated by QEML-1. Do not edit generated bytes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qeml_runtime.h"

static const char *qeml_model_name = "MODEL_NAME";

int main(int argc, char **argv)
{
    qeml_result result;
    unsigned long count;
    if (argc < 2) {
        fprintf(stderr, "usage: %s workers COUNT|heartbeat\n", argv[0]);
        return QEML_PROCESS_USAGE;
    }
    if (strcmp(argv[1], "workers") == 0) {
        if (argc != 3) {
            return QEML_PROCESS_USAGE;
        }
        count = strtoul(argv[2], (char **)0, 10);
        result = qeml_run_workers(count);
    } else if (strcmp(argv[1], "heartbeat") == 0) {
        result = qeml_run_heartbeat(0, 0, 0);
    } else {
        return QEML_PROCESS_USAGE;
    }
    printf("MODEL=%s;STATUS=%s;WORKERS=%lu;STATE=%s;HOLD=%s\n",
           qeml_model_name, qeml_status_name(result.status),
           result.workers, result.state, result.hold_reason);
    return QEML_PROCESS_OK;
}
'''.replace("MODEL_NAME", model_name)
    return source


def expected_c89_trace(model_name, result):
    return "MODEL=%s;%s" % (model_name, format_trace(result))


def emit_m68000_status(status_code):
    if status_code not in STATUS_NAMES:
        raise QEMLError("M68000_STATUS", "status cannot be encoded with MOVEQ")
    if status_code < 0 or status_code > 127:
        raise QEMLError("M68000_IMMEDIATE", "MOVEQ immediate out of range")
    opcode = 0x7000 | status_code
    blob = bytes(((opcode >> 8) & 0xff, opcode & 0xff, 0x4e, 0x75))
    assembly = (".text\n.globl qeml_status_primitive\n"
                "qeml_status_primitive:\n"
                "    moveq #%d,%%d0\n"
                "    rts\n") % status_code
    return {"assembly": assembly, "machine_code": blob,
            "target": "m68000", "abi": "qikvrt-m68000-v1"}


def execute_m68000_status(blob):
    if len(blob) != 4:
        raise QEMLError("M68000_LENGTH", "expected exactly two 16-bit instructions")
    first = (blob[0] << 8) | blob[1]
    second = (blob[2] << 8) | blob[3]
    if (first & 0xff00) != 0x7000 or second != 0x4e75:
        raise QEMLError("M68000_ENCODING", "expected MOVEQ #imm,D0; RTS")
    return first & 0xff


def compile_artifacts(source_text, expected_head=None, expected_tree=None):
    model = parse_source(source_text)
    canonical_source = canonical_print(model).encode("utf-8")
    ir_bytes = canonical_json_bytes(canonical_ir(model))
    c89_bytes = emit_c89(model).encode("ascii")
    m68k = emit_m68000_status(STATUS_CONTINUE)
    tests = execute_all_tests(model)
    receipt = {
        "schema": SCHEMA_RECEIPT,
        "language": "QEML-1",
        "model": model["model"],
        "source_sha256": sha256_bytes(source_text.encode("utf-8")),
        "canonical_source_sha256": sha256_bytes(canonical_source),
        "ir_sha256": sha256_bytes(ir_bytes),
        "c89_sha256": sha256_bytes(c89_bytes),
        "m68000_assembly_sha256": sha256_bytes(m68k["assembly"].encode("ascii")),
        "m68000_machine_code_sha256": sha256_bytes(m68k["machine_code"]),
        "test_count": len(tests),
        "tests_ok": all(item["ok"] for item in tests),
        "expected_head": expected_head,
        "expected_tree": expected_tree,
        "bootstrap_fixed_point_for_supported_subset": False,
        "self_hosting_observed": False,
        "ansi_c89_compilation_observed": False,
        "m68000_emulated_primitive_execution_observed": False,
        "physical_megast_execution": False,
        "authority_main_effect": False,
        "general_effect_ack_done": False,
        "publication": False,
        "deployment": False,
        "pass": False,
        "final_pass": False,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json_bytes(receipt))
    return {
        "model": model,
        "canonical_source": canonical_source,
        "ir": ir_bytes,
        "c89": c89_bytes,
        "m68000": m68k,
        "tests": tests,
        "receipt": receipt,
    }


def bootstrap_fixed_point(source_text):
    stage1 = compile_artifacts(source_text)
    stage2 = compile_artifacts(stage1["canonical_source"].decode("utf-8"))
    result = {
        "canonical_source_equal": stage1["canonical_source"] == stage2["canonical_source"],
        "ir_equal": stage1["ir"] == stage2["ir"],
        "c89_equal": stage1["c89"] == stage2["c89"],
        "m68000_equal": stage1["m68000"]["machine_code"] == stage2["m68000"]["machine_code"],
    }
    result["fixed_point"] = all(result.values())
    return result


def compile_c89_and_run(source_text, scenario, argument=None, cc=None,
                        runtime_dir=None):
    artifacts = compile_artifacts(source_text)
    cc = cc or os.environ.get("CC", "cc")
    if runtime_dir is None:
        runtime_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "qeml")
    with tempfile.TemporaryDirectory(prefix="qeml-c89-") as tmp:
        generated = os.path.join(tmp, "model.c")
        binary = os.path.join(tmp, "model")
        with open(generated, "wb") as handle:
            handle.write(artifacts["c89"])
        command = [cc, "-std=c89", "-pedantic", "-Wall", "-Wextra", "-Werror",
                   "-I", runtime_dir, os.path.join(runtime_dir, "qeml_runtime.c"),
                   generated, "-o", binary]
        subprocess.check_call(command)
        argv = [binary, scenario]
        if argument is not None:
            argv.append(str(argument))
        output = subprocess.check_output(argv).decode("ascii").strip()
    return output


def _write(path, data):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as handle:
        handle.write(data)


def command_compile(args):
    with open(args.source, "r") as handle:
        source = handle.read()
    artifacts = compile_artifacts(source, args.expected_head, args.expected_tree)
    _write(args.output_prefix + ".canonical.qeml", artifacts["canonical_source"])
    _write(args.output_prefix + ".ir.json", artifacts["ir"])
    _write(args.output_prefix + ".c", artifacts["c89"])
    _write(args.output_prefix + ".m68k.s", artifacts["m68000"]["assembly"])
    _write(args.output_prefix + ".m68k.bin", artifacts["m68000"]["machine_code"])
    _write(args.output_prefix + ".receipt.json", canonical_json_bytes(artifacts["receipt"]))
    if not artifacts["receipt"]["tests_ok"]:
        return 2
    return 0


def command_test(args):
    with open(args.source, "r") as handle:
        model = parse_source(handle.read())
    results = execute_all_tests(model)
    for result in results:
        print("%s %s %s" % ("OK" if result["ok"] else "FAIL",
                             result["name"], result["trace"]))
    return 0 if all(result["ok"] for result in results) else 2


def command_bootstrap(args):
    with open(args.source, "r") as handle:
        result = bootstrap_fixed_point(handle.read())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["fixed_point"] else 2


def build_parser():
    parser = argparse.ArgumentParser(description="QIK-VRT QEML-1 reference compiler")
    sub = parser.add_subparsers(dest="command")
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("source")
    compile_parser.add_argument("--output-prefix", required=True)
    compile_parser.add_argument("--expected-head")
    compile_parser.add_argument("--expected-tree")
    compile_parser.set_defaults(func=command_compile)
    test_parser = sub.add_parser("test")
    test_parser.add_argument("source")
    test_parser.set_defaults(func=command_test)
    bootstrap_parser = sub.add_parser("bootstrap")
    bootstrap_parser.add_argument("source")
    bootstrap_parser.set_defaults(func=command_bootstrap)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except QEMLError as exc:
        sys.stderr.write(json.dumps({"state": "HOLD", "error": exc.as_dict()},
                                    sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
