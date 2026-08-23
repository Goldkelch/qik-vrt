# QIK-VRT Circular Spark M68000 Architecture V1

## Status

This is the first executable architecture tranche after the proof-bound M68000 registry and the MLP.TOS / Hatari system-test ring.

It does **not** replace the physical Motorola 68000 register model. `D0...D7` remain 32-bit data registers. Larger rings are virtual, sparse, provenance-bound structures managed by compiler, interpreter, storage and target-execution stages.

## Ring ladder

```text
0
→ 1
→ 2
→ 2^3 = 8 bits = one byte
→ 2^8 = 256 possible byte values
→ explicitly defined virtual ring width of 256 bits
→ symbolic outer state cardinality 2^(256^3)
```

The distinctions are mandatory:

```text
256 STATES != 256 BITS
VIRTUAL RING WIDTH != PHYSICAL REGISTER WIDTH
2^(256^3) != EAGER MEMORY ALLOCATION
```

`2^(256^3)` is retained as a symbolic cardinality. No implementation attempts to allocate that many bits, bytes, nodes or objects. The outer ring is represented through sparse, content-addressed descriptors and only materializes causally active work.

## Alternating architecture

```text
VIRTUAL INTERPRETER
  prepares an exact bounded branch descriptor
        ↓
PROOF-PRESERVING COMPILER
  reuses or emits a finite M68000 kernel
        ↓
MOTOROLA 68000 MICROKERNEL
  executes one bounded branch-pass disposition
        ↓
VIRTUAL INTERPRETER
  performs permitted non-local repository or system effects
        ↓
OBSERVATION / REOBSERVATION
        ↓
COLLECT → PERSIST → RELEASE
        ↓
NEXT RING
```

A physical M68000 may occupy the hardware stage when independently available and observed. In current automated evidence, Hatari executes the M68000 instruction stream under a Mega-ST/EmuTOS target profile. Emulator execution is real instruction-stream execution, but it is not physical hardware execution.

## Bounded branch-pass ABI

```text
D0.L input  = thirteen-bit branch-work descriptor
D1.L output = 0 IDLE, 1 ACTIVE, 2 HOLD, 3 COMPLETE
D3.B in/out = 0 QUIESCENT, 1 ACTIVE
```

The low thirteen descriptor bits bind:

```text
PROBLEM
MODEL
EXPLICIT DISTINCTIONS
INVARIANTS
ARCHITECTURE
IMPLEMENTATION
EXECUTION
OBSERVATION ADMISSION
VERIFICATION
RESULT COLLECTION
RESULT PERSISTENCE
RESOURCE RELEASE
NEXT-STATE REOBSERVATION
```

The microkernel implements:

```text
invalid D3 or unknown D0 bits → HOLD
D0 = 0 and D3 = 0             → IDLE
partial valid descriptor       → ACTIVE, D3 := 1
all thirteen predicates        → COMPLETE, D3 := 0
```

`COMPLETE` means that one already-materialized bounded work descriptor satisfies its complete local closure contract. It does not itself create a Git commit, submit an independent review, merge a pull request, publish externally or establish `EFFECT_ACK_DONE`.

```text
BRANCH_PASS_COMPLETE != GIT_BRANCH_MERGED
```

The software stage remains responsible for authorized non-local effects and their subsequent reobservation.

## Why this can improve performance

Stable finite predicates are compiled once into small immutable M68000 kernels and reused. Variable, non-finite, text-heavy, networked or authority-dependent work remains in the interpreter. The architecture therefore avoids repeatedly interpreting a high-level rule where a proved finite projection already exists.

```text
HOT STABLE FINITE RULE
→ COMPILE ONCE
→ CACHE BY PROOF / SOURCE DIGEST
→ REUSE MACHINE BYTES

VARIABLE OR UNBOUND RULE
→ INTERPRETER
→ HOLD OR MATERIALIZE MORE EVIDENCE
```

This is the same compiler/interpreter alternation that has historically made computing systems practical, but with explicit provenance and evidence boundaries.

Performance must still be measured per target generation. A small instruction path and high target throughput do not by themselves prove a cross-architecture or physical speedup ratio.

## Current and next evidence rings

Current tranche:

```text
formal reference model
→ Lean/Lake candidate proof
→ deterministic M68000 compiler
→ exact machine bytes
→ bounded interpreter execution
→ exhaustive valid-domain verification
```

Next target tranche:

```text
register Spark kernel
→ embed in MLP.TOS successor
→ execute under Hatari Mega ST / MC68000
→ benchmark target ticks
→ write and reobserve receipt
→ compare against interpreter baseline on the same semantic work unit
→ only then state a bounded speedup ratio
```

Physical-hardware execution remains a separately observed successor.

## Non-claims

```text
PHYSICAL_M68000_EXECUTION_OBSERVED = false
PHYSICAL_SPEEDUP_MEASURED          = false
PASS                               = false
FINAL_PASS                         = false
EFFECT_ACK_DONE                    = false
```
