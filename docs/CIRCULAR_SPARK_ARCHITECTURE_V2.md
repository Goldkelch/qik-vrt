# QIK-VRT Circular Spark Architecture V2

## Purpose

Generation V2 turns the first virtual Spark branch capsule into a circular architecture contract whose hot path alternates proof-bound compilation, Motorola 68000 plan execution, a bounded software effect adapter, Motorola 68000 closure execution, and exact reobservation.

```text
VIRTUAL COMPILER
→ M68000 PLAN PASS
→ VIRTUAL INTERPRETER / EFFECT ADAPTER
→ M68000 CLOSURE PASS
→ REOBSERVATION
→ QUIESCENCE OR NEXT ACTIVATION
→ VIRTUAL COMPILER
```

The circle is a role cycle. It is not a claim that one physical instruction performs compilation, repository mutation, review, merge and observation at once.

## Exact scale

```text
0 → 1 → 2 → 8 → 256
```

means:

- `0`: quiescent bounded ring;
- `1`: activate one bounded work ring;
- `2`: binary distinction `0|1`;
- `2^3 = 8`: eight control bits, one byte;
- `2^8 = 256`: 256 possible values of that byte.

The independently defined evidence ring remains 256 bits wide.

The next macro-ring width is:

```text
256^3 bits
= 16,777,216 bits
= 2,097,152 bytes
= 2 MiB
```

The corresponding state cardinality is represented symbolically as:

```text
2^(256^3)
```

It is not enumerated, allocated or confused with a 256-bit width.

```text
256 BYTE STATES != 256 BIT RING WIDTH
256^3 BITS != 2^(256^3) STATES
```

Physical Motorola 68000 data registers remain 32 bits wide. Wider rings are virtual memory structures operated by 68000 instructions.

## Three structural rings

The final three denotes three structural rings:

1. `CONTROL`: one 8-bit normalized control byte;
2. `EVIDENCE`: one 256-bit SHA-256 work-unit/provenance identity;
3. `COMPLETION`: collect, persist, release, reobserve and quiesce.

The rings form a logical cycle:

```text
CONTROL → EVIDENCE → COMPLETION → CONTROL
```

## Two Spark machine kernels

Generation V2 registers two separate Motorola 68000 Spark kernels.

### Local capsule pass

`lean_spark_branch_pass_v1` consumes a finite local acceptance capsule and returns:

```text
D0=0 NOOP_COMPLETE
D0=1 HOLD
D0=2 REOBSERVE
D0=3 REQUEST_AUTHORITY
```

It also returns a completion witness in D1, a machine-owned activity flag in D2 and preserves D3 exactly.

### Complete-plan pass

`lean_spark_branch_plan_v1` consumes one normalized eight-bit branch observation and selects exactly one complete bounded remaining plan from twelve alternatives, including:

```text
REBASE → MATERIALIZE → VERIFY → MERGE → REOBSERVE → COLLECT → PERSIST → RELEASE
```

or a precise fail-closed authority/invalid hold.

The plan-selection pass does not itself perform GitHub effects. The virtual interpreter/effect-adapter layer executes the selected plan serially, with exact-head compare-and-swap and reobservation after every effect. The closure kernel then classifies the resulting bounded capsule.

Therefore:

```text
ONE PLAN PASS = ONE COMPLETE BOUNDED PLAN SELECTED
ONE SPARK CYCLE = ONE ADMITTED BOUNDED BRANCH WORK UNIT CLOSED OR HELD PRECISELY
ONE SPARK CYCLE != ONE M68000 INSTRUCTION
ONE M68000 PLAN PASS != GITHUB EFFECT
```

## Registry generation

The compiled registry contains five proof-bound kernels:

```text
lean_gate_v1
lean_v2_d3_step_v1
lean_v2_mesh_recovery_v1
lean_spark_branch_pass_v1
lean_spark_branch_plan_v1
```

The total immutable machine-code inventory is 284 bytes. Runtime consumers load the registry once and execute the machine bytes directly; they do not re-run the compiler or reinterpret the higher-level decision rule for each admitted work unit.

## Compiler/interpreter alternation

The software virtualization stage intentionally contains both forms that made previous computing generations practical:

```text
COMPILER:
  stable finite proof rule
  → immutable M68000 bytes

INTERPRETER / EFFECT ADAPTER:
  selected bounded plan
  → authorized serial host effects
  → exact reobservation after every effect
```

The compiler removes repeated rule interpretation from the hot path. The interpreter preserves dynamic authority, repository, transport and observation boundaries that cannot safely be baked into an immutable local machine kernel.

## Current evidence and next physical stage

Generation V2 proves the finite arithmetic and cycle laws in Lean/Lake, exhaustively verifies both Spark kernels, and executes the circular reference cycle through bounded virtual M68000 opcode interpreters.

The predecessor registry kernels have already executed in Hatari under EmuTOS. The two new Spark kernels have not yet been executed or benchmarked in Hatari or on physical Motorola hardware at this stage.

```text
VIRTUAL_M68000_SPARK_EXECUTION          = OBSERVED
HATARI_NEW_SPARK_KERNEL_EXECUTION       = NOT YET OBSERVED
PHYSICAL_M68000_EXECUTION               = NOT OBSERVED
PHYSICAL_SPEEDUP_RATIO                  = NOT MEASURED
```

The next performance ring is therefore exact: embed both new Spark kernels in the TOS consumer, execute them under the qualified Mega-ST/MC68000 profile, measure target-local throughput, write a GEMDOS receipt, reobserve it, promote the unchanged bytes to Authority main, and persist the main-effect receipt append-only.

No `PASS`, `FINAL_PASS`, physical-hardware claim or general `EFFECT_ACK_DONE` follows from this architecture contract.
