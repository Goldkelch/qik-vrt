<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# TEMDD Hardware Mapping and Patent Boundary v1

**Inventor declaration:** Ingolf Lohmann  
**System:** QIK-VRT / Tested Event Model Driven Development  
**Purpose:** public, non-exhaustive hardware mapping and patent-publication boundary

## 1. Objective

This document maps the TEMDD execution semantics onto a hardware architecture without treating an unmeasured performance hypothesis as an established benchmark and without treating repository publication as a patentability determination.

TEMDD's canonical execution chain is:

```text
COMPILE
→ BIND
→ RESOLVE
→ EXECUTE
→ TEST
→ OBSERVE
→ READBACK
→ ACCEPT
→ EFFECT_ACK_DONE
```

The central hardware idea is to make the **evidence-bearing state transition** a first-class execution primitive instead of leaving all provenance, verification and acknowledgement work to software orchestration around a conventional processor.

## 2. Functional hardware blocks

A hardware realization can partition the chain into the following blocks:

| TEMDD stage | Hardware role | Required invariant |
| --- | --- | --- |
| COMPILE | plan/IR preparation interface | execution plan is explicit and bounded |
| BIND | subject identity binder | subject, version and scope are immutable for the operation |
| RESOLVE | capability and authority resolver | no effect without resolved authority |
| EXECUTE | effect engine | only the bound operation may mutate state |
| TEST | assertion engine | declared predicates are evaluated on the bound subject |
| OBSERVE | observation capture | actual successor state is captured |
| READBACK | independent readback/digest engine | observed effect is freshly re-read |
| ACCEPT | acceptance gate | all required predicates must jointly hold |
| EFFECT_ACK | terminal acknowledgement latch | terminal success only after accepted readback |

Supporting blocks include:

- monotonic event/transition sequencing;
- append-only evidence ledger interface;
- cryptographic or hash-based identity binding;
- bounded retry/hold state machine;
- serialization/deserialization interfaces for distributed or transputer-style communication;
- fail-closed error propagation;
- explicit predecessor/successor subject separation.

## 3. Candidate FPGA/ASIC data path

A candidate pipeline is:

```text
Ingress
  ↓
Subject-ID / Scope Binder
  ↓
Capability Resolver
  ↓
Effect Engine ───────┐
  ↓                  │
Assertion Engine     │
  ↓                  │
Observation Capture  │
  ↓                  │
Readback Engine ◄────┘
  ↓
Acceptance Gate
  ↓
Effect-Ack Register
  ↓
Egress / Evidence Ledger
```

The architecture can be implemented as a single pipelined accelerator, as multiple cooperating hardware engines, or as a distributed fabric connected by a serializable message protocol.

## 4. Relation to a transputer-style fabric

The natural hardware abstraction is a network of independently advancing state-transition units rather than one monolithic instruction stream. Each unit receives a typed subject plus an operation, resolves its local authority, executes, verifies the successor and emits an evidence-bearing acknowledgement.

This permits a direct mapping to FPGA fabrics and, subject to physical-design validation, to ASIC structures. A serialized transport is compatible with heterogeneous sender/receiver media as long as identity, ordering and completion semantics remain lossless and explicit.

## 5. Artificial-cognition use case

For artificial cognition, the target is not merely arithmetic acceleration. The candidate gain comes from moving recurrent control-plane work into dedicated hardware:

- exact state/subject binding;
- capability resolution;
- invariant checking;
- provenance capture;
- deterministic transition validation;
- readback hashing;
- acceptance/acknowledgement.

A cognition runtime could therefore spend less general-purpose CPU/GPU time on orchestration around model execution while producing stronger machine-readable evidence for each accepted transition.

## 6. Performance hypotheses

The following are **OPEN hypotheses until measured**:

- lower control-plane latency for evidence-bearing transitions;
- higher throughput through parallel BIND/TEST/READBACK engines;
- lower host-CPU overhead for repeated provenance and acknowledgement work;
- lower tail latency for deterministic acceptance paths;
- potentially improved energy efficiency for repetitive verification primitives.

No numerical speedup is claimed by this document.

A valid benchmark program must compare at least:

1. software-only TEMDD baseline on a defined CPU;
2. CPU plus FPGA offload;
3. equivalent workload and data;
4. identical correctness/evidence requirements;
5. latency, throughput, energy, area/resource use and failure-path behavior;
6. exact RTL/bitstream/commit identity.

## 7. Patent-oriented separation of concepts

Candidate invention axes to examine with patent counsel include:

- treating an evidence-bound state transition as a hardware-visible terminal primitive;
- a hardware pipeline that integrates execution, observation, independent readback and acceptance before acknowledgement;
- subject/provenance binding carried through the datapath;
- a distributed network of such transition units with lossless serialization and exact effect acknowledgement;
- fail-closed predecessor/successor handling where predecessor evidence cannot authorize a mutated successor;
- hardware acceleration of cognition control paths in which verification is part of execution rather than an external after-the-fact audit.

These are **claim-development axes**, not issued patent claims and not a conclusion that they are novel or non-obvious.

## 8. Public-disclosure boundary

This public document intentionally remains architectural. It does not attempt to publish every transistor-level implementation choice, timing structure, arbitration mechanism, memory layout, physical-design optimization or claim-enabling embodiment that could be relevant to a patent filing.

Before any additional enabling detail is placed into this public repository or Zenodo, the exact filing status and the intended priority chain should be checked against the patent filing package.

## 9. Evidence status

```text
HARDWARE_MAPPING_SPECIFIED     = TRUE
RTL_IMPLEMENTATION_BOUND       = NOT_YET
FPGA_SYNTHESIS_EVIDENCE        = NOT_YET
TIMING_CLOSURE_EVIDENCE        = NOT_YET
BENCHMARK_SPEEDUP_ESTABLISHED  = FALSE
ASIC_EVIDENCE                  = NOT_YET
PATENTABILITY_ESTABLISHED      = FALSE
EFFECT_ACK_DONE                = FALSE
```

This status is deliberately fail-closed.

---

**Ingolf Lohmann**
