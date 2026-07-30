#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Compatibility shim when a file inside ``tools/`` is executed directly.

Direct execution places the tools directory, rather than the repository root,
on ``sys.path``. In that one context ``from tools import sibling`` resolves this
module. Attribute access then imports the requested sibling by its top-level
name. Normal repository-root package imports continue to use the ``tools``
namespace package and do not load this shim.
"""
from __future__ import annotations
import importlib
from types import ModuleType

def __getattr__(name: str) -> ModuleType:
    if not name.startswith('qikvrt_'):
        raise AttributeError(name)
    module = importlib.import_module(name)
    globals()[name] = module
    return module
