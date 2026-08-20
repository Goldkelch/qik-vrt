# TEMDD MLP — Machine Learning Program vertical slice

## Goal

This slice turns the existing QIK-VRT metagrammar → causal plan → M68000 path into an observable user-facing control chain named **MLP — Machine Learning Program**.

The chain is deliberately split across causal and epistemic boundaries:

```text
semantic event model
→ validated plan
→ M68000 request capsule
→ Atari/TOS MLP front end
→ shared REQUESTED frame
→ Ubuntu ANSI-C host bridge
→ bounded Firefox proxy launch
→ Firefox repository/effect observation
→ separately authorized EFFECT_ACK adapter
```

The purpose is not to make a 68000 run Firefox. Firefox remains an Ubuntu-host process. The Mega-ST side is the deterministic reference machine and request surface. The host bridge is the platform adapter. This preserves:

```text
ATARI REQUEST != HOST EXECUTION
HOST EXECUTION != BROWSER OBSERVATION
BROWSER OBSERVATION != EFFECT ACKNOWLEDGEMENT
```

## TEMDD contract

TEMDD means **Tested Event Model Driven Development** in this repository profile. Every productive transition must be preceded by an explicit event model, executable validation, and a fail-closed boundary.

The v1 MLP event model is `mlp/TEMDD_MLP_EVENT_MODEL_V1.json`. It keeps the standing distinctions:

- `CAUSALITY != SEQUENCE`
- `REQUESTED != EXECUTED`
- `EXECUTED != OBSERVED`
- `OBSERVED != ACKNOWLEDGED`
- `TRANSPORT_ACK != EFFECT_ACK`
- `CODE != AUTHORITY`

Unknown, missing-authority, unbound, or drifted states remain nonproductive.

## Lowest-frequency / pure-assembler boundary

The leaf routine is `runtime/megast/mlp_kernel_68000.s` and contains only four Motorola 68000 instructions:

```asm
moveq #3,d1
moveq #1,d2
moveq #3,d0
rts
```

Exact bytes:

```text
72 03 74 01 70 03 4E 75
```

Meaning:

```text
D0 = 3  REQUEST_AUTHORITY
D1 = 3  semantic kernel + type-boundary witnesses; authority not yet bound
D2 = 1  REQUESTED
```

This is intentionally nonproductive. It requests the next authority-bound transition; it cannot represent merge, publication, deployment, arbitrary browser mutation, or acknowledged external effect.

## ANSI-C layer

`runtime/megast/mlp_main_ansic.c` is the TOS-facing C89 source. On execution it displays the MLP title, calls the assembly leaf, requires `D0 == REQUEST_AUTHORITY`, and writes the canonical `C:\MLP.OPEN` request frame. Any mismatch or persistence failure terminates on a fail-closed path.

`runtime/host/mlp_host_ansic.c` is the Ubuntu-host C89 adapter. It accepts only the exact request frame, invokes the already bounded QIK-VRT Firefox delegation bridge, and writes a local host receipt with:

```text
HOST_STATE BROWSER_LAUNCH_EXECUTED
OBSERVED false
ACKNOWLEDGED false
NEXT REOBSERVE
```

It therefore cannot turn a successful process launch into an EFFECT_ACK claim.

## Firefox / EFFECT_ACK boundary

The existing QIK-VRT Firefox terminal remains the browser-side implementation surface. MLP launches that surface through `tools/qikvrt_firefox_proxy_delegate.py`; browser authentication stays under human control, while repository/effect operations remain exact-bound and fail closed.

A later browser observation may authorize a subsequent adapter, but `BROWSER_LAUNCH_EXECUTED` itself is never sufficient.

## Mega-ST virtualization

The cloud entrypoint uses Hatari with the repository's established reference profile:

```text
machine     = megast
CPU         = 68000
clock       = 8 MHz
addressing  = 24 bit
RAM         = 1 MiB
FPU         = none
MMU         = false
```

The EmuTOS ROM is supplied externally and must match `EMUTOS_ROM_SHA256` before boot. `MLP.TOS` must already be present in the shared GEMDOS drive. Hatari autostarts it from `C:\MLP.TOS`.

The current slice does **not** claim physical Mega-ST execution. A successful Hatari observation is virtualization evidence for the exact bound emulator/ROM/program tuple only.

## Ubuntu / Docker cloud layer

`runtime/cloud/Dockerfile.mlp` provides an Ubuntu 24.04 userland containing Hatari, the ANSI-C host bridge, X11/VNC plumbing and a Firefox installation. Firefox and the QIK-VRT XPI are external build inputs with mandatory SHA-256 bindings; the image build fails closed if any required URL or digest is absent or mismatched.

The container is a cloud runtime envelope, not a claim that Docker itself is a hardware VM. Hatari supplies the Atari Mega-ST virtualization inside that envelope. If a full Ubuntu VM image is required later, the same container entry contract can be placed around a separately attested VM disk without changing the MLP event semantics.

## What remains before an observable end-to-end demo

This slice deliberately leaves two external artifacts unclaimed:

1. a cross-built `MLP.TOS` from the provided C89 + M68000 sources, bound to its toolchain and digest;
2. a distributable Firefox XPI whose signing/deployment status is independently evidenced.

Those are the next materialization targets. Their absence must not be normalized into success.

## Completion boundary

This candidate establishes source, event-model, assembler, ANSI-C host, browser-delegation and cloud-container contracts. It does not by itself establish physical hardware execution, a signed Firefox distribution, a booted cloud deployment, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
