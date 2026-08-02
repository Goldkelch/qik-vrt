#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Reference parser and fail-closed static validator for the H5 EBNF subset."""

from __future__ import annotations

import dataclasses
import pathlib
import re
import sys
from typing import Any


class ValidationError(ValueError):
    """The candidate is syntactically invalid or violates an H5 obligation."""


TOKEN_RE = re.compile(
    r'''\s*(?:
        (?P<string>"(?:[^"\\\x00-\x1f]|\\["\\/bfnrt])+")
      | (?P<word>[A-Za-z][A-Za-z0-9_.-]*)
      | (?P<number>[0-9]+(?:\.[0-9]+)*)
      | (?P<symbol>[{}\[\]=,;])
    )''',
    re.VERBOSE,
)


@dataclasses.dataclass(frozen=True)
class Token:
    value: str
    offset: int
    kind: str


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    position = 0
    while position < len(text):
        if text[position:].strip() == "":
            break
        match = TOKEN_RE.match(text, position)
        if not match:
            raise ValidationError(
                f"unrecognized syntax at byte/character offset {position}"
            )
        kind = match.lastgroup
        assert kind is not None
        value = match.group(kind)
        if kind == "string":
            value = bytes(value[1:-1], "utf-8").decode("unicode_escape")
        tokens.append(Token(value=value, offset=position, kind=kind))
        position = match.end()
    return tokens


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.index = 0

    def peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index].value

    def take(self) -> Token:
        if self.index >= len(self.tokens):
            raise ValidationError("unexpected end of document")
        token = self.tokens[self.index]
        self.index += 1
        return token

    def expect(self, value: str) -> Token:
        token = self.take()
        if token.value != value:
            raise ValidationError(
                f"expected {value!r} at offset {token.offset}, got {token.value!r}"
            )
        return token

    def parse_scalar(self) -> Any:
        if self.peek() == "[":
            self.take()
            values: list[str] = []
            if self.peek() != "]":
                values.append(self.take().value)
                while self.peek() == ",":
                    self.take()
                    values.append(self.take().value)
            self.expect("]")
            return values
        token = self.take()
        if token.value == "true":
            return True
        if token.value == "false":
            return False
        return token.value

    def parse_block(self) -> tuple[str, str, dict[str, Any]]:
        block_type = self.take().value
        identifier = self.take().value
        self.expect("{")
        fields: dict[str, Any] = {}
        while self.peek() != "}":
            key_token = self.take()
            if key_token.value in fields:
                raise ValidationError(
                    f"duplicate field {key_token.value!r} in {block_type}"
                )
            self.expect("=")
            fields[key_token.value] = self.parse_scalar()
            self.expect(";")
        self.expect("}")
        self.expect(";")
        return block_type, identifier, fields


MANDATORY_BLOCKS = (
    "planck-bridge",
    "duality",
    "empirical-anchors",
    "limits",
    "coupling",
    "consistency",
    "prediction",
    "massive-closure",
    "virtual-cosmogenesis",
    "effect-boundary",
)

CLOSURE_FIELDS = (
    "planck-normal-form",
    "field-record-duality",
    "standard-model-limit",
    "classical-einstein-limit",
    "universal-stress-energy-coupling",
    "quantum-gravity-correspondence",
    "stability-unitarity",
    "causal-consistency",
    "non-circularity",
    "falsifiable-prediction",
    "empirical-correspondence",
    "independent-reproduction",
)


def require_fields(block: str, fields: dict[str, Any], required: set[str]) -> None:
    missing = required - set(fields)
    surplus = set(fields) - required
    if missing or surplus:
        raise ValidationError(
            f"{block} field mismatch: missing={sorted(missing)}, "
            f"surplus={sorted(surplus)}"
        )


def parse_document(text: str) -> dict[str, Any]:
    parser = Parser(tokenize(text))
    parser.expect("vrtcore-smg")
    version = parser.take().value
    parser.expect("scope")
    scope = parser.take().value
    parser.expect("author")
    author = parser.take().value
    parser.expect("effect-state")
    effect_state = parser.take().value
    parser.expect(";")

    blocks: dict[str, dict[str, Any]] = {}
    opens: list[dict[str, Any]] = []
    while parser.peek() is not None:
        block_type, identifier, fields = parser.parse_block()
        fields = {"id": identifier, **fields}
        if block_type == "open":
            opens.append(fields)
            continue
        if block_type in blocks:
            raise ValidationError(f"duplicate mandatory block {block_type!r}")
        blocks[block_type] = fields

    missing_blocks = set(MANDATORY_BLOCKS) - set(blocks)
    surplus_blocks = set(blocks) - set(MANDATORY_BLOCKS)
    if missing_blocks or surplus_blocks:
        raise ValidationError(
            f"block mismatch: missing={sorted(missing_blocks)}, "
            f"surplus={sorted(surplus_blocks)}"
        )

    document = {
        "version": version,
        "scope": scope,
        "author": author,
        "effect-state": effect_state,
        "blocks": blocks,
        "open": opens,
    }
    validate_static_obligations(document)
    return document


def validate_static_obligations(document: dict[str, Any]) -> None:
    blocks = document["blocks"]

    planck = blocks["planck-bridge"]
    if planck.get("gravitational-radius") != "G*m_P/c^2=l_P":
        raise ValidationError(
            "S02: gravitational radius must be G*m_P/c^2=l_P; "
            "the Schwarzschild factor two is a separate quantity"
        )
    if planck.get("physical-status") not in {"conditional", "open"}:
        raise ValidationError("S03: the Planck physical bridge remains conditional/open")

    duality = blocks["duality"]
    if duality.get("physical-completeness") != "open":
        raise ValidationError("S04: identity preservation is not physical completeness")

    anchors = blocks["empirical-anchors"]
    if anchors.get("higgs-field-excitation") != "observed":
        raise ValidationError("S05: the declared H5 baseline requires the Higgs anchor")
    if anchors.get("gravitational-wave") != "observed":
        raise ValidationError("S05: the declared H5 baseline requires the wave anchor")
    if anchors.get("graviton") != "not-observed":
        raise ValidationError("S05: H5 has no graviton observation record")
    if anchors.get("quantum-gravity-prediction") != "not-observed":
        raise ValidationError("S05: H5 has no confirmed differentiating QG prediction")

    limits = blocks["limits"]
    if limits.get("standard-model") != "open" or limits.get("classical-einstein") != "open":
        raise ValidationError("S06: SM and Einstein limits remain separate OPEN witnesses")
    if "extension" not in str(limits.get("scope", "")):
        raise ValidationError("S07: gravity must be labelled as an extension sector")

    coupling = blocks["coupling"]
    if coupling.get("source") != "stress-energy":
        raise ValidationError("S08: universal gravitational coupling uses stress-energy")
    if coupling.get("higgs-sector-included") is not True:
        raise ValidationError("S08: the Higgs sector must be explicit in the coupling scope")
    if coupling.get("universality") != "open" or coupling.get("derivation") != "none":
        raise ValidationError("S08: no universal-coupling derivation is supplied in H5")

    consistency = blocks["consistency"]
    if consistency.get("stability-unitarity") != "open":
        raise ValidationError("S09: stability/unitarity remains OPEN")
    if consistency.get("non-circularity") != "open":
        raise ValidationError("S09: non-circularity remains OPEN")

    prediction = blocks["prediction"]
    if not prediction.get("observable") or not prediction.get("falsifier"):
        raise ValidationError("S10: prediction needs observable and falsifier fields")
    if prediction.get("status") != "open":
        raise ValidationError("S10: no differentiating H5 prediction is frozen")

    closure = blocks["massive-closure"]
    required_closure = set(CLOSURE_FIELDS) | {"id", "result"}
    require_fields("massive-closure", closure, required_closure)
    closure_values = [closure[name] for name in CLOSURE_FIELDS]
    if not all(isinstance(value, bool) for value in closure_values):
        raise ValidationError("S11: every closure witness must be Boolean")
    expected_result = (
        "MASSIVE_CLOSURE_TRUE" if all(closure_values) else "MASSIVE_CLOSURE_FALSE"
    )
    if closure["result"] != expected_result:
        raise ValidationError(
            f"S11/S12: closure result must be {expected_result}, "
            f"got {closure['result']}"
        )

    cosmogenesis = blocks["virtual-cosmogenesis"]
    if cosmogenesis.get("unboundedness") != "conditional":
        raise ValidationError("S14: unbounded growth requires a strict-growth witness")
    if cosmogenesis.get("physical-cosmology-identity") != "open":
        raise ValidationError("S15: a virtual machine is not physical cosmology")

    boundary = blocks["effect-boundary"]
    if boundary.get("technical-result") == "kernel-accepted":
        if boundary.get("physical-discovery") != "open":
            raise ValidationError("S16: kernel acceptance is not physical discovery")
        if boundary.get("ordinary-release") is not False:
            raise ValidationError("S16: kernel acceptance cannot release an effect")
    if boundary.get("effect-state") != "EFFECT_ACK_CONTINUE":
        raise ValidationError("S20: H5 cannot construct EFFECT_ACK_DONE")
    if document["effect-state"] != "EFFECT_ACK_CONTINUE":
        raise ValidationError("S20: document header must remain EFFECT_ACK_CONTINUE")

    if not document["open"]:
        raise ValidationError("S17: at least one explicit OPEN obligation is required")
    required_open = {
        "id",
        "kind",
        "question",
        "required-evidence",
        "falsifier",
        "owner",
    }
    for obligation in document["open"]:
        require_fields("open", obligation, required_open)
        if obligation["kind"] != "open":
            raise ValidationError("S17/S18: an OPEN obligation must remain epistemically open")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {pathlib.Path(argv[0]).name} FILE.vrt", file=sys.stderr)
        return 2
    candidate = pathlib.Path(argv[1])
    try:
        document = parse_document(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        return 1
    print(
        "PASS: H5 syntax and S01-S20 static boundary accepted; "
        f"{len(document['open'])} OPEN obligations preserved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
