# QIK-VRT M68000/TOS Consumer and Benchmark V1

## End-to-end ring

```text
COMPILED KERNEL REGISTRY
→ deterministic Atari TOS image compiler
→ MLP.TOS
→ Motorola 68000 execution under TOS
→ target-local 200 Hz benchmark
→ GEMDOS receipt write
→ host-side receipt reobservation
→ exact registry/kernel provenance verification
```

The consumer reads `runtime/m68000/QIKVRT_COMPILED_KERNELS_V1.json` at build time and embeds the exact immutable bytes selected by these kernel IDs:

- `lean_gate_v1`
- `lean_v2_d3_step_v1`
- `lean_v2_mesh_recovery_v1`

`runtime/m68000/tos/MLP.TOS.hex` is the deterministic Atari executable image. The build fails if the registry path, byte count, or persisted image differs.

## Actual TOS consumer

The generated file has a real 28-byte Atari program header (`0x601A`) and position-independent Motorola 68000 text. It invokes the three registered kernels as native subroutines, measures repeated invocation with the TOS `hz_200` system timer, creates `QIKVRT.RCP` through GEMDOS `Fcreate`, writes the receipt through `Fwrite`, closes it through `Fclose`, and terminates through `Pterm0`.

The receipt contains:

- SHA-256 of the exact registry bytes;
- SHA-256 of each embedded machine kernel;
- functional outputs from all finite gate inputs, a D0/D2/D3 lifecycle witness, and all recovery cut-point byte classes needed for the bounded observation;
- `262144` repeated native invocations per kernel;
- elapsed 200 Hz target ticks;
- an execution-complete marker.

Host verification rejects a missing, malformed, provenance-mismatched, semantically incorrect, zero-duration, or incomplete receipt.

## Execution environment

The workflow uses Hatari in Mega ST / Motorola 68000 mode with an open-source EmuTOS image, a writable GEMDOS host directory, exact 68000 CPU selection, and automatic launch of `C:\MLP.TOS`.

This establishes:

```text
REAL_ATARI_TOS_EXECUTABLE              = TRUE
MOTOROLA_68000_INSTRUCTION_EXECUTION   = OBSERVED_IN_HATARI
TOS_GEMDOS_EFFECT                      = RECEIPT_FILE_WRITTEN
POST_EFFECT_HOST_REOBSERVATION         = REQUIRED
```

It does not establish:

```text
PHYSICAL_ATARI_MEGA_ST_EXECUTION       = FALSE
PHYSICAL_M68000_HARDWARE_EXECUTION     = FALSE
GENERAL_EFFECT_ACK_DONE                = FALSE
```

An emulator execution is a real execution of the M68000 instruction stream and TOS ABI inside a qualified emulator. It is not a physical-hardware claim.

## Benchmark meaning

Each registered kernel is invoked `262144` times. The elapsed value is measured by the TOS 200 Hz clock, and the verifier derives calls per emulated target second.

This is a target-execution throughput benchmark. It is not yet a physical wall-clock comparison against a Mega ST, and it is not a claimed ratio against Lean, Python, or JSON processing on a different architecture.

```text
NATIVE_TARGET_THROUGHPUT_MEASURED
!=
PHYSICAL_SPEEDUP_RATIO_PROVEN
```

The compiled path nevertheless removes repeated higher-level rule interpretation from every applicable M68000 invocation: the already proved finite rule is loaded once as immutable machine bytes and reused directly.
