# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic source-bound segmentation for fail-closed journey translation."""
from __future__ import annotations
import re
from collections.abc import Callable

MODEL_INPUT_LIMIT = 512
MODEL_OUTPUT_LIMIT = 512
SEGMENT_INPUT_LIMIT = 256

# Prefer stable sentence/clause boundaries. If a single clause itself exceeds
# the bounded segment contract, a deterministic whitespace boundary is the
# narrowest source-preserving fallback: no word bytes are changed or invented.
_BOUNDARY = re.compile(r'(?<=[.!?;:,\u2013\u2014])\s+')
_WORD_BOUNDARY = re.compile(r'\s+')


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


def _candidate_ends(source: str, start: int, tokenizer, limit: int,
                    pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    ends = [match.end() for match in pattern.finditer(source)]
    if not ends or ends[-1] != len(source):
        ends.append(len(source))
    candidates: list[tuple[int, str]] = []
    for end in ends:
        if end <= start:
            continue
        candidate = source[start:end].strip()
        if candidate and token_count(tokenizer, candidate) <= limit:
            candidates.append((end, candidate))
    return candidates


def segment_plan(source: str, tokenizer, limit: int = SEGMENT_INPUT_LIMIT) -> list[str]:
    """Return a deterministic >=2-part source plan or fail closed.

    Sentence/clause boundaries are preferred. A whitespace boundary is used
    only when the current clause cannot otherwise be subdivided within the
    token limit, or when forced subdivision of an otherwise bounded source is
    required after observed output nontermination. The plan never substitutes
    source text and always makes strict progress.
    """
    if not source.strip():
        raise ValueError('EMPTY_SOURCE_BLOCK')
    parts: list[str] = []
    start = 0
    while start < len(source):
        candidates = _candidate_ends(source, start, tokenizer, limit, _BOUNDARY)
        force_subdivide = start == 0 and bool(candidates) and candidates[-1][0] == len(source)
        if force_subdivide:
            if len(candidates) >= 2:
                end, candidate = candidates[-2]
                parts.append(candidate)
                start = end
                continue
            candidates = []
        if not candidates:
            candidates = _candidate_ends(source, start, tokenizer, limit, _WORD_BOUNDARY)
            if start == 0 and candidates and candidates[-1][0] == len(source):
                if len(candidates) < 2:
                    raise ValueError('NO_SAFE_SEGMENT_BOUNDARY')
                end, candidate = candidates[-2]
            elif candidates:
                end, candidate = candidates[-1]
            else:
                raise ValueError('NO_SAFE_SEGMENT_BOUNDARY')
        else:
            end, candidate = candidates[-1]
        if end <= start:
            raise ValueError('NO_SAFE_SEGMENT_BOUNDARY')
        parts.append(candidate)
        start = end
    if len(parts) < 2 or any(token_count(tokenizer, part) > limit for part in parts):
        raise ValueError('NO_SAFE_SEGMENT_BOUNDARY')
    return parts


def translate_segmented(source: str, tokenizer,
                        generate: Callable[[str], list[int]]) -> tuple[str, list[str]]:
    """Translate a subdivided source, recursively refining nonterminal children."""
    plan = segment_plan(source, tokenizer)
    translated: list[str] = []
    leaves: list[str] = []
    for part in plan:
        seq = generate(part)
        try:
            text = decode_terminal(seq, tokenizer)
            child_plan = [part]
        except ValueError as exc:
            if str(exc) != 'OUTPUT_TRUNCATED_NO_ACCEPTANCE':
                raise
            text, child_plan = translate_segmented(part, tokenizer, generate)
        translated.append(text)
        leaves.extend(child_plan)
    result = ' '.join(translated).strip()
    if not result or result == source or '\n\n' in result:
        raise ValueError('SEGMENT_REASSEMBLY_REJECTED')
    return result, leaves


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
