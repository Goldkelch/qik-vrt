# QIK-VRT M68000/TOS Consumer and Spark Benchmark V2

## End-to-end ring

```text
FIVE-KERNEL COMPILED REGISTRY
→ deterministic Atari TOS image compiler
→ MLP.TOS
→ Mega ST / MC68000 execution in Hatari
→ target-local 200 Hz benchmark
→ GEMDOS QIKVRT.RCP write
→ host-side receipt reobservation
→ exact five-kernel provenance verification
→ Authority-main execution
→ append-only main-effect receipt
→ ledger reobservation
```

## Embedded proof-bound kernels

The deterministic consumer embeds, calls and benchmarks all five registered kernels:

1. `lean_gate_v1` — 24 bytes;
2. `lean_v2_d3_step_v1` — 20 bytes;
3. `lean_v2_mesh_recovery_v1` — 24 bytes;
4. `lean_spark_branch_pass_v1` — 82 bytes;
5. `lean_spark_branch_plan_v1` — 134 bytes.

The immutable machine-code payload is 284 bytes. `MLP.TOS` binds the exact registry SHA-256 and the SHA-256 of each embedded kernel.

## Actual TOS execution

The generated file has an Atari executable header (`0x601A`) and position-independent Motorola 68000 text. It invokes every kernel as a native subroutine, measures `262144` repeated calls per kernel through the TOS `hz_200` system timer, writes `QIKVRT.RCP` with GEMDOS `Fcreate`, `Fwrite` and `Fclose`, then terminates with `Pterm0`.

The protected `$000004BA` timer is read only through XBIOS function 38 `Supexec`; direct user-mode reads remain rejected by regression tests.

```text
USER_MODE_READ($04BA) = INVALID
XBIOS_SUPEXEC(read_hz_200) = REQUIRED
```

## Receipt V2

The 320-byte `QIKM68K2` receipt contains:

- exact registry digest;
- all five kernel digests;
- exact iteration count;
- gate outputs for all four low-bit certificate classes;
- D0/D2/D3 lifecycle output and preserved `0xA5` witness;
- Mesh recovery outputs for cut points `0..7`;
- Spark local-capsule outputs for COMPLETE, REOBSERVE, REQUEST_AUTHORITY and HOLD;
- Spark complete-plan outputs for invalid, already-complete, request-authority, merge-to-close and rebase-to-close observations;
- five nonzero 200-Hz benchmark durations;
- execution-complete marker.

The host verifier rejects missing, malformed, provenance-mismatched, semantically incorrect, zero-duration or incomplete receipts.

## Performance meaning

Each kernel executes `262144` times in the same qualified Mega-ST/MC68000 emulator profile. This provides directly comparable target-local throughput for the two Spark kernels and the three predecessor kernels.

```text
TARGET_THROUGHPUT_MEASURED
!= PHYSICAL_HARDWARE_SPEEDUP_RATIO
```

The measured hot path demonstrates that the finite rules are compiled once, embedded once and reused without Python, JSON or Lean interpretation for each target invocation. It does not prove a physical Mega ST wall-clock ratio.

## Spark-cycle boundary

The plan kernel selects one complete bounded plan in one M68000 pass. The local capsule kernel closes one already materialized bounded capsule in one M68000 pass. Repository mutations, review authority, merge and post-main reobservation remain host-side effects.

```text
ONE PLAN PASS = ONE COMPLETE PLAN SELECTED
ONE CAPSULE PASS = ONE LOCAL CAPSULE DISPOSITION
ONE SPARK CYCLE = PLAN + SERIAL EFFECT ADAPTER + REOBSERVATION + CLOSURE
ONE PLAN PASS != GITHUB MERGE EFFECT
```

## Authority-main effect

On a matching push to `main`, the workflow repeats the entire five-kernel chain and writes `QIKVRT_M68000_TOS_MAIN_EFFECT_RECEIPT_V2` by non-force fast-forward CAS to:

```text
refs/heads/qikvrt/m68000-tos-systemtest-ledger-v1
receipts/<authority-main-head>/<workflow-run-id>.json
```

The bounded ring closes only after the run-specific ledger receipt is read back and its exact Head, Tree, registry, five machine kernels, functional outputs, benchmark values, TOS image and GEMDOS receipt agree.

### Non-polling acquisition and ledger boundary

The CI path makes exactly one time-bounded EmuTOS download attempt and emits
`QIKVRT_M68000_TOS_EMUTOS_ACQUISITION_RECEIPT_V1`.  A network failure is
`HOLD_EMUTOS_SINGLE_FETCH_FAILED`; a digest mismatch is
`BLOCK_EMUTOS_ARCHIVE_SHA256_MISMATCH`.  Neither condition retries or silently
substitutes an archive.

The Authority-main receipt uses one exact ledger-reference observation, one
non-force fast-forward write attempt, and one post-write reference
reobservation.  A missing ledger branch is a distinct initial-create case.  A
transport failure, reference drift, collision, or failed post-write observation
emits `QIKVRT_M68000_TOS_LEDGER_WRITE_RECEIPT_V3` with `HOLD` or `BLOCK`; it is
not retried by that workflow run.  The post-write transport observation remains
distinct from `EFFECT_ACK_DONE`.

## Non-claims

```text
HATARI_M68000_EXECUTION != PHYSICAL_M68000_EXECUTION
EMULATED_TARGET_THROUGHPUT != PHYSICAL_SPEEDUP_RATIO
SYSTEMTEST_RECEIPT != GENERAL_EFFECT_ACK_DONE
```

No physical Atari claim, physical speedup, `PASS`, `FINAL_PASS` or general `EFFECT_ACK_DONE` follows from this benchmark.
