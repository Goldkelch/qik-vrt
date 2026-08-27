<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT virtual neutron-star mesh V1

## Scope

This component is a bounded computational topology. It uses the image of a
neutron star to join two independent scaling axes without claiming an
astrophysical simulation:

| Topological image | Executable meaning |
|---|---|
| angular sectors | parallel processing breadth |
| radial shells | ordered evidence and reobservation depth |
| core | the D3 8-bit witness preserved through every virtual cell |
| pressure | fail-closed admission and backpressure |
| rotation | event-driven work-cycle progression |

Breadth and depth may change independently. Every dimension is finite: at most
256 sectors and eight shells. Demand above the declared capacity is rejected.

## AD/DA and variable bitrate

The planner keeps three quantities separate:

```text
sample_rate_hz != sample_bits != transport_bps
raw_signal_bps = sample_rate_hz * sample_bits * channels
```

V1 admits only `LOSSLESS_FRAMED_V1` and `drop_policy = NONE`. Variable bitrate
may select a wider carrier, more sectors, chunking or backpressure. It may not
silently lower quantization or evidentiary precision. A transport rate below
the raw signal requirement fails closed.

The available carrier widths are `8, 16, 32, 64, 128, 256` bits. The virtual
carrier width is not a claim about a physical register. Values wider than the
M68000 logical 32-bit register are represented as ordered 32-bit segments and
bound by the plan SHA-256.

## Reuse decision

V1 composes existing repository contracts instead of adding a compiler or a
new physical kernel:

- `QIKVRT_CIRCULAR_SPARK_ARCHITECTURE_V2` supplies the bounded information
  widths but has no independently scalable breadth axis.
- `QIKVRT_REAL_MESH_V1` supplies connected breadth and node-local evidence but
  has no radial AD/DA transport planner.
- `QIKVRT_SPARK_ARCHITECTURE_V1` supplies the D0--D3/A0--A1 virtual M68000 ABI.
- `QIKVRT_COMPILED_KERNELS_V1` stays unchanged because its five-kernel byte
  registry is fixed and a topology planner is not another physical kernel.

The neutron-star planner is therefore a thin deterministic composition layer.

## Required execution order

```text
INPUT
-> INTERPRETATION
-> DECISION
-> EXECUTION
-> OBSERVATION
-> EFFECT_ACKNOWLEDGEMENT
-> NEW_STATE
```

A pull-request workflow checks out the literal PR head, computes its Git tree,
executes low- and high-demand plans, runs the regression suite, and preserves
the exact binding with the plans. Head/tree drift invalidates all predecessor
artifacts.

## Claim boundary

The implementation does not establish an astrophysical neutron-star model, a
stellar equation of state, materialization of all quantum correlations,
physical M68000 execution, Authority-main effect, `PASS`, `FINAL_PASS`, or
general `EFFECT_ACK_DONE`. It establishes only the behavior of the named
virtual planner on its exactly observed repository state.
