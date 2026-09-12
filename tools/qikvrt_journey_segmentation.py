# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic source-bound segmentation for fail-closed journey translation."""
from __future__ import annotations
import re
from collections.abc import Callable

MODEL_INPUT_LIMIT = 512
MODEL_OUTPUT_LIMIT = 512
SEGMENT_INPUT_LIMIT = 256

# Split only at stable sentence/clause boundaries. Whitespace is consumed by
# the boundary and is not semantic fallback material.
_BOUNDARY = re.compile(r'(?<=[.!?;:,\u2013\u2014])\s+')


def token_count(tokenizer, text: str) -> int:
    return len(tokenizer(text, add_special_tokens=True)['input_ids'])


def decode_terminal(seq: list[int], tokenizer) -> str:
    # Decoder start may itself be EOS: require a generated terminal EOS.
    if tokenizer.eos_token_id not in seq[2:]:
        raise ValueError('OUTPUT_TRUNCATED_NO_ACCEPTANCE')
    text = tokenizer.decode(seq, skip_special_tokens=True).strip()
    if not text or '\n\n' in text:
        raise ValueError('EMPTY_OR_MALFORMED_OUTPUT_BLOCK')
    return text


def segment_plan(source: str, tokenizer, limit: int = SEGMENT_INPUT_LIMIT) -> list[str]:
    """Return a deterministic >=2-part source plan or fail closed.

    The caller invokes this only for an over-bound or non-terminating block, so
    returning the original block as one segment is never admissible.
    """
    if not source.strip():
        raise ValueError('EMPTY_SOURCE_BLOCK')
    ends = [match.end() for match in _BOUNDARY.finditer(source)]
    if not ends or ends[-1] != len(source):
        ends.append(len(source))
    parts: list[str] = []
    start = 0
    while start < len(source):
        candidates: list[tuple[int, str]] = []
        for end in ends:
            if end <= start:
                continue
            candidate = source[start:end].strip()
            if candidate and token_count(tokenizer, candidate) <= limit:
                candidates.append((end, candidate))
        if not candidates:
            raise ValueError('NO_SAFE_SEGMENT_BOUNDARY')
        end, candidate = candidates[-1]
        # A fallback must actually subdivide the original source block.
        if start == 0 and end == len(source):
            if len(candidates) < 2:
                raise ValueError('NO_SAFE_SEGMENT_BOUNDARY')
            end, candidate = candidates[-2]
        parts.append(candidate)
        start = end
    if len(parts) < 2 or any(token_count(tokenizer, part) > limit for part in parts):
        raise ValueError('NO_SAFE_SEGMENT_BOUNDARY')
    return parts


def translate_segmented(source: str, tokenizer,
                        generate: Callable[[str], list[int]]) -> tuple[str, list[str]]:
    plan = segment_plan(source, tokenizer)
    translated: list[str] = []
    for part in plan:
        translated.append(decode_terminal(generate(part), tokenizer))
    result = ' '.join(translated).strip()
    if not result or result == source or '\n\n' in result:
        raise ValueError('SEGMENT_REASSEMBLY_REJECTED')
    return result, plan


def accept_or_segment(source: str, seq: list[int], tokenizer,
                      generate: Callable[[str], list[int]]) -> tuple[str, list[str] | None]:
    try:
        return decode_terminal(seq, tokenizer), None
    except ValueError as exc:
        if str(exc) != 'OUTPUT_TRUNCATED_NO_ACCEPTANCE':
            raise
    return translate_segmented(source, tokenizer, generate)


def reassemble_blocks(original: list[str], results: dict[str, str],
                      protected: Callable[[str], bool]) -> list[str]:
    values: list[str] = []
    for block in original:
        if protected(block):
            values.append(block)
        elif block in results:
            values.append(results[block])
        else:
            raise ValueError('MISSING_TRANSLATION_BLOCK')
    if len(values) != len(original):
        raise ValueError('SOURCE_BLOCK_COUNT_DRIFT')
    return values
