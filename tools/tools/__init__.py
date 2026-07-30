# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Package shim for direct execution of scripts located in ``tools/``.

When ``python tools/example.py`` is used, Python puts the tools directory rather
than the repository root on ``sys.path``. This package is then discovered as
``tools``. Extending its package path with the parent tools directory preserves
both ``from tools import sibling`` and ``from tools.sibling import name``.
Normal repository-root imports continue to use the outer namespace package.
"""
from __future__ import annotations
import pathlib
_parent = str(pathlib.Path(__file__).resolve().parents[1])
if _parent not in __path__:
    __path__.append(_parent)
