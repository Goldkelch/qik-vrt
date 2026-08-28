# QIK-VRT deterministic mesh admission — technical disclosure draft

**Inventor attribution:** Ingolf Lohmann  
**Status:** technical disclosure for counsel review; not a filed application,
not a novelty opinion, and not a legal conclusion.

## Technical problem

Distributed processing paths commonly leave ordering, incomplete input and
conflicting evidence to implementation-specific retry, sampling or implicit
selection.  This draft describes a finite digital mechanism that makes the
serialization mapping and admission result reproducible and externally
inspectable.

## Technical solution

1. A square mesh has `N*N` ordered lanes with `WORD_BITS` bits each.
2. Lane `(row,column)` maps to `row*N+column`; bits are serialized
   least-significant-bit first into a canonical `N*N*WORD_BITS`-bit frame.
3. Deserialization is the inverse mapping for every complete canonical frame.
4. A digital admission gate selects exactly one state in this precedence:
   `CONTINUE` for incomplete input; `HOLD` for explicit ambiguity; `ACCEPT`
   for a complete canonical match; otherwise `BLOCK`.
5. The state is output as digital logic and can be attached to a persistent
   receipt/ledger only after the separate system policy permits it.

The concrete reference embodiment is in
`hardware/vhdl/qikvrt_mesh_quadratic_codec.vhd`,
`hardware/vhdl/qikvrt_deterministic_admission_gate.vhd`, and the iCE40UP5K
breakout top-level design.

## Candidate claim themes for patent counsel

- A hardware apparatus combining the canonical square-lane codec with the
  precedence-defined deterministic admission gate.
- A method of serializing, deserializing and fail-closedly classifying a
  complete mesh frame according to the stated order.
- A computer-readable medium implementing the same canonical mapping and
  truth table, including a hardware/software equivalence test.

### Candidate independent apparatus claim — technical skeleton

A digital processing apparatus comprising: a lane store for `N*N` lanes of
`WORD_BITS` bits; a serializer that emits the lanes in the stated row-major,
least-significant-bit-first order; a deserializer that reconstructs the lanes
from the complete frame; and an admission circuit configured to emit exactly
one of `CONTINUE`, `HOLD`, `ACCEPT` and `BLOCK` in the declared precedence,
wherein an ambiguity input produces `HOLD` rather than a selected result.

### Candidate independent method claim — technical skeleton

Receiving a finite square lane array; serializing it canonically; receiving and
deserializing the resulting complete frame; comparing the reconstructed array
with a canonical reference; and emitting the precedence-defined disposition
without random selection or implicit ambiguity resolution.

## Evidence and filing prerequisites still open

- Prior-art search and claim-scope analysis by qualified patent counsel.
- Inventor review, dates, contribution record and confidentiality/publication
  assessment before disclosure or filing.
- Tool-bound VHDL analysis, synthesis, place-and-route, timing, bitstream and
  board observation for any physical performance claim.
- Benchmark plan with equal task, fixed dataset, measurement method, power
  boundary and independently reproducible results before any performance claim.

No claim in this draft asserts that the device removes physical noise, replaces
an LLM, establishes a universal performance factor, or has already been
patented or manufactured.
