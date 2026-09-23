# QIK-VRT MVP — TEMDD Reference Runtime Contract

Author: Ingolf Lohmann
Status: normative MVP contract
Principle: HALTE, PUNKT / epistemic spiral

## Runtime chain

```text
COMPILE → BIND → RESOLVE → EXECUTE → TEST → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE
```

COMPILE = model → executable plan. BIND = exact subject/artifact/identity binding. RESOLVE = runtime capabilities and authority. EXECUTE = intended effect. TEST = assertions and negative/failure paths. OBSERVE = actual successor state. READBACK = fresh independent effect readback. ACCEPT = acceptance criteria applied to current evidence. EFFECT_ACK_DONE = terminal evidence-bound haltpoint of the complete execution.

```text
EXECUTE != DONE
TEST != DONE
OBSERVE != DONE
TRANSPORT_ACK != EFFECT_ACK
HISTORICAL_PASS != CURRENT_PASS
```

For one exact bound subject:

```text
EFFECT_ACK_DONE iff
  COMPILE AND BIND AND RESOLVE AND EXECUTE AND TEST
  AND OBSERVE AND READBACK AND ACCEPT
```

A mutation creates a successor subject and invalidates predecessor evidence for claims requiring exact-current binding.

## Safety / Progress

```text
StateV_Gamma(phi) != VERIFIED
  -> HALT_CLAIM(phi)

HALT_CLAIM(phi)
AND OPEN_EVIDENCE_PATH(Gamma, phi)
  -> CONTINUE_EVIDENCE(phi)
```

Therefore: not verified → do not claim. Not verified + admissible evidence path → continue evidence work. HALT_CLAIM is not HALT_COMPUTATION.

## QV_min assertion kernel

```text
Permission_Gamma(Assert(phi)) iff
  Gamma |-V phi
  AND NOT (Gamma |-V NOT phi)

Gamma[n+1] = Gamma[n] (+) E[n]
E[n] = Readback(Action[n])
```

Evidence revision is non-monotonic. A new readback may confirm, refute, leave undetermined, or conflict with a previous judgment.

## Reference implementation acceptance

```text
BOOTABLE_IMAGE
AND REPRODUCIBLE_BUILD
AND VIRTUAL_ATARI_BOOT
AND M68000_EXECUTION_WITNESS
AND TRANSPUTER_ROUNDTRIP
AND UNIVERSAL_TERMINAL_OPERATION
AND TEMDD_TESTED_EVENT_TRACE
AND FAILURE_PATH_TESTED
AND FRESH_EFFECT_READBACK
AND PUBLIC_ARTIFACT_READBACK
--------------------------------
REFERENCE_IMPLEMENTATION_ACCEPTED
```

Canonical causal path:

```text
reproducible Linux image
→ Atari/M68000 boot witness
→ deterministic Transputer roundtrip
→ same roundtrip through Universal Terminal
→ TEMDD trace + negative failure test
→ public image
→ SHA-256 public readback
→ acceptance
→ EFFECT_ACK_DONE
```

## Fail-closed invariants

- UNKNOWN is neither TRUE nor FALSE.
- Missing, stale, contradictory or differently-bound required evidence MUST NOT be promoted.
- Command success, transport ACK, workflow start/completion, commit, persistence, test or observation MUST NOT by itself imply EFFECT_ACK_DONE.
- Claim scope MUST NOT exceed evidence scope.
- Predecessor evidence MUST NOT transfer to a mutated successor unless explicitly permitted and independently verified.
- A blocked mutation MUST NOT imply global idleness while independent admissible work/evidence paths remain open.

## Architecture correspondence

```text
EVENT → PROCESS → CARRIER → EFFECT → OBSERVATION → READBACK → INVARIANT → ACK / CONTINUE
```

This is the common control primitive connecting TEMDD, Effect Acknowledgment, the haltpoint, Universal Transputer / Terminal, Metatransistor semantics and artificial cognition.

## Scientific boundary

This software contract is engineering control semantics. It does not itself establish physical claims about QIK, spacetime, quantum gravity or new laws of nature; those require their own formal and empirical evidence.

## Canonical maxim

```text
Safety prevents unsupported assertion.
Progress prevents epistemic restraint from becoming operational passivity.

HALTE, PUNKT:
Stop the claim at the evidence boundary.
Continue admissible evidence work while the required effect remains open.
```
