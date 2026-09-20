#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded application-level file parts over ordinary HTTP/TCP.

Individual part hashes, order, lengths and a final whole-file hash are required.
This module provides no publication, execution or acceptance authority.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import tempfile

MIB = 1024**2
DEFAULT_PART_BYTES = 2048 * MIB
MAX_PART_BYTES = 8192 * MIB
MAX_FILE_BYTES = 64 * 1024**3
MAX_PARTS = 4096
MAX_MANIFEST_BYTES = 8 * MIB
PART_SUFFIX = re.compile(r'\.part-[0-9a-f]{16}-[1-9][0-9]*-[0-9]{6}\Z')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def part_size(value: int) -> int:
    if type(value) is not int or not 0 < value <= MAX_PART_BYTES:
        raise ValueError('part size outside contract')
    return value


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def matches(path: Path, entry: dict) -> bool:
    return (not path.is_symlink() and path.is_file() and
            path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'])


def part_name(name: str, entry: dict, limit: int, index: int) -> str:
    # Different source bytes or a changed line profile get distinct part names.
    return f'{name}.part-{entry["sha256"][:16]}-{limit}-{index:06d}'


def validate_file(name: str, entry: dict, limit: int = DEFAULT_PART_BYTES) -> None:
    part_size(limit)
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError('unsafe asset name')
    if not isinstance(entry, dict) or type(entry.get('bytes')) is not int or not 0 < entry['bytes'] <= MAX_FILE_BYTES:
        raise ValueError('invalid asset byte count')
    if not HEX64.fullmatch(str(entry.get('sha256', ''))):
        raise ValueError('invalid asset hash')
    parts = entry.get('parts')
    if parts is None:
        if entry['bytes'] > limit:
            raise ValueError('oversize file requires transfer parts')
        return
    count = (entry['bytes'] + limit - 1) // limit
    if not isinstance(parts, list) or not 1 <= len(parts) <= MAX_PARTS or len(parts) != count:
        raise ValueError('missing or excessive transfer parts')
    offset = 0
    for index, part in enumerate(parts, 1):
        if (not isinstance(part, dict) or part.get('name') != part_name(name, entry, limit, index) or
                type(part.get('offset')) is not int or part['offset'] != offset or
                type(part.get('bytes')) is not int or part['bytes'] != min(limit, entry['bytes'] - offset) or
                not HEX64.fullmatch(str(part.get('sha256', '')))):
            raise ValueError('invalid transfer part identity/order/size')
        offset += part['bytes']
    if offset != entry['bytes']:
        raise ValueError('transfer parts do not cover complete file')


def describe(path: Path, limit: int = DEFAULT_PART_BYTES) -> dict:
    """Split large input once, preserving the original and any matching old parts."""
    part_size(limit)
    if path.is_symlink() or not path.is_file():
        raise ValueError('transfer source must be a regular file')
    size = path.stat().st_size
    entry = {'bytes': size, 'sha256': digest(path)}
    if not 0 < size <= MAX_FILE_BYTES:
        raise ValueError('invalid asset byte count')
    if size <= limit:
        validate_file(path.name, entry, limit)
        return entry
    if (size + limit - 1) // limit > MAX_PARTS:
        raise ValueError('part size too small for bounded part inventory')
    parts, whole, offset = [], hashlib.sha256(), 0
    with path.open('rb') as source:
        while offset < size:
            count = min(limit, size - offset)
            part = {'name': part_name(path.name, entry, limit, len(parts)+1), 'offset': offset, 'bytes': count}
            target = path.with_name(part['name'])
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                try:
                    remaining, hashed = count, hashlib.sha256()
                    while remaining:
                        block = source.read(min(MIB, remaining))
                        if not block:
                            raise ValueError('source truncated during splitting')
                        output.write(block); hashed.update(block); whole.update(block)
                        remaining -= len(block)
                    output.flush(); os.fsync(output.fileno()); output.close()
                    part['sha256'] = hashed.hexdigest()
                    if target.exists() or target.is_symlink():
                        if not matches(target, part):
                            raise ValueError('existing transfer part differs')
                    else:
                        temporary.chmod(0o644)
                        temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
            parts.append(part); offset += count
        if source.read(1) or whole.hexdigest() != entry['sha256']:
            raise ValueError('source changed during splitting')
    entry['parts'] = parts
    validate_file(path.name, entry, limit)
    return entry


def assemble(target: Path, entry: dict, directory: Path, limit: int = DEFAULT_PART_BYTES) -> None:
    """Publish the final file atomically only after each part and the whole agree."""
    validate_file(target.name, entry, limit)
    if not entry.get('parts'):
        raise ValueError('part inventory required for assembly')
    if target.exists() or target.is_symlink():
        if matches(target, entry):
            return
        raise ValueError('existing file does not match bound image')
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            whole, total = hashlib.sha256(), 0
            for part in entry['parts']:
                path = directory / part['name']
                if path.is_symlink() or not path.is_file():
                    raise ValueError('missing or unsafe transfer part')
                hashed, count = hashlib.sha256(), 0
                with path.open('rb') as source:
                    while block := source.read(MIB):
                        count += len(block)
                        if count > part['bytes']:
                            raise ValueError('transfer part exceeds bound size')
                        output.write(block); hashed.update(block); whole.update(block)
                if count != part['bytes'] or hashed.hexdigest() != part['sha256']:
                    raise ValueError('transfer part digest/size mismatch')
                total += count
            output.flush(); os.fsync(output.fileno()); output.close()
            if total != entry['bytes'] or whole.hexdigest() != entry['sha256']:
                raise ValueError('reassembled file digest/size mismatch')
            temporary.chmod(0o644)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def receive_file(base: str, name: str, entry: dict, directory: Path, fetch,
                 limit: int = DEFAULT_PART_BYTES, *, fresh: bool = False) -> list[dict]:
    """Reuse verified parts after interruption; public readback can require fresh HTTP."""
    validate_file(name, entry, limit)
    target = directory / name
    if not entry.get('parts'):
        return [fetch(base.rstrip('/') + '/' + name, target, entry['sha256'], entry['bytes'])]
    cache = directory / (name + '.parts')
    if cache.is_symlink():
        raise ValueError('unsafe transfer cache')
    cache.mkdir(parents=True, exist_ok=True)
    observations = []
    for part in entry['parts']:
        path = cache / part['name']
        if path.is_symlink():
            raise ValueError('unsafe transfer part')
        if not fresh and path.exists():
            if not matches(path, part):
                raise ValueError('cached transfer part differs')
            observations.append({'name': part['name'], 'state': 'VERIFIED_CACHE', 'sha256': part['sha256']})
        else:
            observations.append(fetch(base.rstrip('/') + '/' + part['name'], path, part['sha256'], part['bytes']))
    assemble(target, entry, cache, limit)
    return observations


def transport_names(assets: dict) -> list[str]:
    """Release uploads contain parts in place of oversized logical files."""
    return sorted({part['name'] for name, entry in assets.items()
                   for part in entry.get('parts', [{'name': name}])})
