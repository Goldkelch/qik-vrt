# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Canonical TEMDD outer main-loop semantics.

The production loop is intentionally unbounded. Tests use run_bounded() so
verification terminates without redefining EFFECT_ACK_DONE as PROGRAM_DONE.
"""
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Protocol, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class StageEvidence:
    compile: bool
    bind: bool
    resolve: bool
    execute: bool
    test: bool
    observe: bool
    readback: bool
    accept: bool

    @property
    def effect_ack_done(self) -> bool:
        return all((
            self.compile,
            self.bind,
            self.resolve,
            self.execute,
            self.test,
            self.observe,
            self.readback,
            self.accept,
        ))


class Runtime(Protocol[T]):
    def cycle(self, subject: T) -> tuple[StageEvidence, T]:
        ...

    def bind_successor(self, predecessor: T, successor: T) -> T:
        ...


def run_one(runtime: Runtime[T], subject: T) -> tuple[bool, T]:
    evidence, observed_successor = runtime.cycle(subject)
    if not evidence.effect_ack_done:
        return False, subject
    return True, runtime.bind_successor(subject, observed_successor)


def run_bounded(runtime: Runtime[T], subject: T, cycles: int) -> tuple[int, T]:
    if cycles < 0:
        raise ValueError("cycles must be non-negative")
    completed = 0
    current = subject
    for _ in range(cycles):
        done, next_subject = run_one(runtime, current)
        if done:
            completed += 1
            current = next_subject
    return completed, current


def main_loop(runtime: Runtime[T], subject: T) -> None:
    current = subject
    while True:
        done, next_subject = run_one(runtime, current)
        if done:
            current = next_subject
