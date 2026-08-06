#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Loader for the reviewable split QIK-VRT autonomous orchestrator source."""
from pathlib import Path

_parts = [
    Path(__file__).with_name(f"qikvrt_autonomous_orchestrator_part{index:02d}.inc")
    for index in range(1, 12)
]
_source = "".join(path.read_text(encoding="utf-8") for path in _parts)
exec(compile(_source, str(_parts[0]), "exec"), globals(), globals())
