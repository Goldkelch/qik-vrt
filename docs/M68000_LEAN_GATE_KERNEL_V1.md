# QIK-VRT Lean → Motorola 68000 Gate Kernel V1

This work unit compiles the finite executable projection of the formally proved QIK-VRT gate rule into Motorola 68000 machine code.

## Formal source

The source theorem remains `QIKVRT.evaluateGate` in `QIKVRTFormalization/Gates.lean`. The additional module `QIKVRTFormalization/M68000Kernel.lean` proves that when PASS and BLOCK certificate propositions are represented exactly by two Boolean evidence-presence bits, the finite Boolean evaluator is extensionally equal to the formal evaluator.

The priority is therefore fixed by proof rather than convention:

```text
BLOCK certificate present -> BLOCK
else PASS certificate present -> PASS
else -> CONTINUE
```

`BLOCK` dominates `PASS` when both bits are present.

## M68000 ABI

```text
D0 bit 0 = PASS certificate present
D0 bit 1 = BLOCK certificate present

return D0:
0 = CONTINUE
1 = PASS
2 = BLOCK
```

The deterministic compiler emits exactly 24 bytes:

```text
08000001670470024e7508000000670470014e7570004e75
```

The emitted kernel has a maximum of six dynamically executed M68000 instructions on any of the four semantic input classes. The repository verifier executes all 256 possible low-byte inputs in a bounded reference interpreter and proves equality with the finite reference rule.

## What is accelerated

This replaces repeated interpretation of the three-way gate priority with a fixed native M68000 decision kernel on an M68000 target. Once linked into an M68000 runtime, each gate decision is bounded by the compiled instruction path rather than by Lean, Python, JSON, or repository-policy interpretation.

Compilation itself is deterministic and cacheable: identical formal projection + compiler version yields identical machine bytes. Reuse therefore does not require recompiling or reinterpreting the rule on every decision.

## What is not yet measured

The repository does **not** claim a physical speedup number yet. Current CI proves source-to-byte determinism and bounded instruction semantics using a reference interpreter; it does not execute these bytes on a physical Motorola 68000 or Atari Mega ST. A physical cycle/time comparison belongs to a separate target benchmark after the bytes are linked into that runtime.

Therefore:

```text
COMPILED_M68000_KERNEL = TRUE
LEAN_PROJECTION_KERNEL_CHECKED = REQUIRED_BY_GATE
EXHAUSTIVE_FINITE_EQUIVALENCE = 256/256 INPUT BYTES
PHYSICAL_M68000_EXECUTION_OBSERVED = FALSE
PHYSICAL_SPEEDUP_MEASURED = FALSE
```

The compiler boundary is deliberately narrow. It compiles only the finite decision kernel whose correspondence to the Lean gate semantics is proved. It does not pretend that arbitrary proposition-valued Lean predicates, repository effects, physical observations, or authority decisions have become M68000 instructions.
