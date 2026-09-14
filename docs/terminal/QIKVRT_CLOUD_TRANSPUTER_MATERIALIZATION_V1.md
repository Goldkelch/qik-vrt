# QIK-VRT Cloud Transputer materialization v1

Recovered sources: PR #1039 (Cloud Transputer v1), PR #1040 (observable Universal Terminal service plane), and Ingolf Lohmann's recovered QIK-VRT boundary description linking the four operational states directly to the Motorola-68000 D0 ABI.

## Executable contract

One OCI image provides Firefox ESR + Xvfb + x11vnc + noVNC, nginx, OpenSSH, bounded SMTP sink, BIND DNS, Net-SNMP, PostgreSQL, Git mirror support, the QIK-VRT terminal/effect HTTP plane, an ISO-C90 IP bootstrap probe, and an MC68000 cross-development/runtime path (`gcc-m68k-linux-gnu` + `qemu-m68k`).

The MC68000-visible boundary contract now separates two concepts that were previously conflated:

- `D0[1:0]` is the invariant four-state QIK-VRT/TEMDD decision ABI: `0=NOOP`, `1=HOLD`, `2=REOBSERVE`, `3=REQUEST_AUTHORITY`.
- `0-1-2-4` is the binary composition hierarchy: zero/unset plus orthogonal weights `1`, `2`, `4`, ... . The value `3` is not a new primitive weight; it is `1+2`. Weight `4` opens the next independent composition dimension and must not redefine the meanings carried by `D0[1:0]`.
- The five-state EFFECT_ACK protocol remains `NACK=0`, `CONTINUE=1`, `ISOLATE=2`, `BLOCK=3`, `DONE=4`, but it is a separate semantic state machine and is bound to `D4` in this MC68000 contract. Ordinary release remains permitted only from stable `EFFECT_ACK_DONE`.

A statically linked `-m68000` executable witness is built inside the image and executed with qemu-m68k. It checks both state machines, verifies that D0 rejects bit weight 4 as part of the boundary code, and prints the preserved composition relation `3=1+2` and next orthogonal weight `4`. This is M68000-family machine-code execution in the emulator path, not a claim of physical 68000 hardware execution.

## Infrastructure as Code / IP bootstrap

`deploy/universal-terminal/compose.yaml` materializes a fixed `10.73.0.0/24` Mesh. The terminal occupies `10.73.0.2`, SQL `10.73.0.3`, Authority-connected mirror `10.73.0.4`, and the MC68000 development role `10.73.0.6`; service roles occupy additional fixed addresses. The recovered bootstrap contract uses server `10.73.0.1`, UDP discovery port 7331, client `10.73.0.2`, artifact `QIKVRT_BOOT.BIN`, 128-byte chunks, 2-second timeout, three retries and FNV1a32 over the discover/offer/request/data/done route.

The persistent `/var/lib/qikvrt/personal-posix` volume is the owner source slot. If `build-qikvrt-m68k.sh` exists it is invoked with MC68000 C90 compiler/runner bindings. `QIKVRT_REQUIRE_PERSONAL_POSIX=1` makes absence fail closed rather than silently claiming a complete personal POSIX implementation.

## Boundary and effect semantics

The four operational D0 values answer only: **what may happen next?** They are not the five EFFECT_ACK protocol states. The latter answer a different question about the effect-verification lifecycle. Keeping both machines separate prevents `EFFECT_ACK_DONE=4` from being misread as a fifth D0 boundary decision.

`TRANSPORT_ACK != EFFECT_ACK`. Container build, network reachability, emulator execution, authorization and physical effect remain independently observable facts. A public deployment, physical MC68000 execution, physical effect, or general EFFECT_ACK_DONE requires its own readback.
