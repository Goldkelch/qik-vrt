# MLP.TOS / Hatari continuous delivery

## Canonical entry point

`MLP.TOS/Hatari` is the repository-facing launcher requested for the eventual canonical URL:

`https://github.com/Goldkelch/qik-vrt/blob/main/MLP.TOS/Hatari`

The adjacent `MLP.TOS/MLP.TOS` is a committed 341-byte Atari GEMDOS executable. It is generated deterministically by `tools/qikvrt_mlp_tos_hatari.py`; the dedicated workflow regenerates it and requires byte equality with the committed binary before Hatari may run.

## Executable semantics

The program executes the exact MLP register leaf:

```text
72 03 74 01 70 03 4E 75
D1=3 semantic/type witnesses
D2=1 REQUESTED
D0=3 REQUEST_AUTHORITY
RTS
```

It then validates all three registers. Only the matching path writes the canonical request frame to `C:\MLP.TMP`, closes it, and renames it to `C:\MLP.OPEN`. Any mismatch, short write, close failure, or rename failure terminates fail-closed and does not publish `C:\MLP.OPEN`.

The resulting frame remains nonproductive:

```text
STATE REQUESTED
AUTHORITY MISSING
EFFECT REQUESTED
```

`REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED` and `TRANSPORT_ACK != EFFECT_ACK` remain mandatory.

## Continuous and dynamic availability

`.github/workflows/qikvrt_mlp_tos_hatari.yml` runs on relevant pull-request changes, relevant pushes to `main`, manual dispatch, and a daily UTC liveness reobservation. Each successful exact-head run:

1. regenerates `MLP.TOS` and compares it byte-for-byte with the committed binary;
2. verifies the committed SHA-256 binding;
3. installs Hatari 2.4.1 and verifies the exact EmuTOS 1.4 archive and ROM digests;
4. executes the program as an Atari Mega ST / 68000 / 8 MHz / 24-bit / 1 MiB virtual machine;
5. requires an exact `C:\MLP.OPEN` frame and no surviving `C:\MLP.TMP`;
6. emits a head/tree/binary/ROM/trace-bound JSON receipt and preserves the binary, trace and frame as a 30-day Actions artifact.

The scheduled run keeps a current reproducible artifact available after promotion to the default branch. Pull-request evidence remains bound to its exact source head and does not transfer across head, tree, base, or scope drift.

## Boundary

A successful workflow is virtualized Hatari/Mega-ST evidence for the exact bound tuple. It is not physical original-hardware execution, Firefox GUI observation, regular-network multi-instance interaction, independent review, merge authority, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
