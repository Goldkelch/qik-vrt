#!/usr/bin/env python3
from dataclasses import dataclass

@dataclass(frozen=True)
class State:
    repository_processing: bool
    durable_readback: bool
    chat_trigger: bool
    observation: bool
    continuation: bool
    fresh_validation: bool

def closed(s: State) -> bool:
    return all((s.repository_processing, s.durable_readback, s.chat_trigger,
                s.observation, s.continuation, s.fresh_validation))

def status(s: State) -> str:
    return "CLOSED" if closed(s) else "HOLD_UNVERIFIED"

if __name__ == "__main__":
    current = State(True, True, False, False, False, False)
    assert status(current) == "HOLD_UNVERIFIED"
    witness = State(True, True, True, True, True, True)
    assert status(witness) == "CLOSED"
