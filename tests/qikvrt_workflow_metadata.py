# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Narrow stdlib-only parser for GitHub workflow trigger metadata used by tests."""

from __future__ import annotations

import pathlib


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        quote = value[0]
        value = value[1:-1]
        if quote == "'":
            value = value.replace("''", "'")
        else:
            value = value.replace(r"\"", '"').replace(r"\\", "\\")
    return value


def _inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return [_scalar(value)] if value else []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_scalar(item) for item in inner.split(",") if item.strip()]


def workflow_document(path: pathlib.Path) -> dict[str, object]:
    """Parse only name/on/workflow_run/schedule metadata from a workflow file.

    These repository contracts need trigger topology, not arbitrary YAML
    semantics. Keeping the parser intentionally narrow avoids an undeclared
    PyYAML dependency in the mandatory stdlib-only test suite.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    document: dict[str, object] = {}

    for raw in lines:
        if raw.startswith("name:"):
            document["name"] = _scalar(raw.split(":", 1)[1])
            break

    on_index: int | None = None
    on_inline = ""
    for index, raw in enumerate(lines):
        if raw.startswith("on:"):
            on_index = index
            on_inline = raw.split(":", 1)[1].strip()
            break
    if on_index is None:
        return document

    triggers: dict[str, object] = {}
    document["on"] = triggers
    if on_inline:
        for trigger in _inline_list(on_inline):
            triggers[trigger] = {}
        return document

    index = on_index + 1
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            break
        if indent != 2 or ":" not in stripped:
            index += 1
            continue

        key, value = stripped.split(":", 1)
        key = _scalar(key)
        value = value.strip()

        if key == "workflow_run":
            workflow_run: dict[str, object] = {}
            triggers[key] = workflow_run
            index += 1
            while index < len(lines):
                nested = lines[index]
                nested_stripped = nested.strip()
                if not nested_stripped or nested_stripped.startswith("#"):
                    index += 1
                    continue
                nested_indent = len(nested) - len(nested.lstrip(" "))
                if nested_indent <= 2:
                    break
                if nested_indent == 4 and ":" in nested_stripped:
                    nested_key, nested_value = nested_stripped.split(":", 1)
                    nested_key = _scalar(nested_key)
                    nested_value = nested_value.strip()
                    values = _inline_list(nested_value) if nested_value else []
                    if not nested_value:
                        cursor = index + 1
                        while cursor < len(lines):
                            item = lines[cursor]
                            item_stripped = item.strip()
                            if not item_stripped or item_stripped.startswith("#"):
                                cursor += 1
                                continue
                            item_indent = len(item) - len(item.lstrip(" "))
                            if item_indent <= 4:
                                break
                            if item_stripped.startswith("- "):
                                values.append(_scalar(item_stripped[2:]))
                            cursor += 1
                        index = cursor - 1
                    workflow_run[nested_key] = values
                index += 1
            continue

        if key == "schedule":
            schedule: list[dict[str, str]] = []
            index += 1
            while index < len(lines):
                nested = lines[index]
                nested_stripped = nested.strip()
                if not nested_stripped or nested_stripped.startswith("#"):
                    index += 1
                    continue
                nested_indent = len(nested) - len(nested.lstrip(" "))
                if nested_indent <= 2:
                    break
                if nested_stripped.startswith("- ") and ":" in nested_stripped[2:]:
                    item_key, item_value = nested_stripped[2:].split(":", 1)
                    schedule.append({_scalar(item_key): _scalar(item_value)})
                index += 1
            triggers[key] = schedule
            continue

        triggers[key] = _inline_list(value) if value.startswith("[") else {}
        index += 1

    return document
