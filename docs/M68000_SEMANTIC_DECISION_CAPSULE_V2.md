# QIK-VRT M68000 Semantic Decision Capsule ABI V2

## Purpose

ABI V2 makes a bounded subset of validated metagrammar semantics directly observable in Motorola 68000 register state while preserving the existing four-action nonproductive decision surface.

It is an additive target profile above ABI V1. The default lowerer behavior remains ABI V1 and therefore preserves existing byte contracts.

## Register contract

After successful V2 lowering and execution:

```text
D0 = decision code
D1 = semantic witness flags
D2 = effect lifecycle code
```

The subroutine then returns with `RTS`.

### D0 — decision

```text
0 = NOOP
1 = HOLD
2 = REOBSERVE
3 = REQUEST_AUTHORITY
```

No productive action is added by V2.

### D1 — semantic witness flags

```text
bit 0 (0x01) = exact compiler distinction kernel is present
bit 1 (0x02) = exact type-invariant contract is present, including CAUSALITY != SEQUENCE
bit 2 (0x04) = AUTHORITY is BOUND
bit 3 (0x08) = an explicit causal predecessor is bound (`CAUSE != -`)
```

Bits 0 and 1 are mandatory for V2. Missing or altered compiler witness material fails closed before executable IR is emitted.

The authority bit is descriptive of the already validated plan; it does not create authority. The causal-predecessor bit records an explicit dependency binding; it does not infer causality from source order or time.

### D2 — effect lifecycle

```text
0 = NONE
1 = REQUESTED
2 = EXECUTED
3 = OBSERVED
4 = ACKNOWLEDGED
5 = REJECTED
6 = UNKNOWN
```

The lifecycle code is observational state. In particular:

```text
REQUESTED != EXECUTED
EXECUTED != OBSERVED
OBSERVED != ACKNOWLEDGED
```

## Exact byte examples

The existing emitter already supports `MOVEQ` for data registers D0-D7, so V2 requires no new instruction encoding.

For a validated plan with bound authority, no explicit predecessor, `EFFECT NONE`, and `NEXT REOBSERVE`:

```text
MOVEQ #7,D1
MOVEQ #0,D2
MOVEQ #2,D0
RTS
```

raw big-endian bytes:

```text
72 07 74 00 70 02 4E 75
```

For bound authority, explicit predecessor, `EFFECT OBSERVED`, and `NEXT REOBSERVE`:

```text
72 0F 74 03 70 02 4E 75
```

For missing authority, explicit predecessor, `EFFECT REQUESTED`, and fail-closed `NEXT HOLD`:

```text
72 0B 74 01 70 01 4E 75
```

## Invocation

ABI V1 remains the default:

```sh
qikvrt_metagrammar_m68000_lower_ansic
```

ABI V2 is selected explicitly:

```sh
qikvrt_metagrammar_m68000_lower_ansic --semantic-witness-v2
```

Both consume the validated textual plan emitted by the universal ANSI-C89 frontend and feed the existing minimal M68000 emitter.

## Boundaries

V2 does not claim physical Atari Mega ST execution, performance, deployment, publication, empirical quantum causality, consciousness, or external effect completion.

Its technical claim is narrower: validated semantic distinctions can be carried deterministically into machine-visible M68000 register state without widening the productive effect surface.
