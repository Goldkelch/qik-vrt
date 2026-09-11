# QIK-VRT Cloud Transputer materialization v1

Recovered sources: PR #1039 (Cloud Transputer v1) and PR #1040 (observable Universal Terminal service plane). This carrier rebases their compatible runtime pieces onto trusted main `b4b0038bcaa8788098ffa529bd5d5b651dd0459c` instead of extending the stale branches.

## Executable contract

One OCI image provides Firefox ESR + Xvfb + x11vnc + noVNC, nginx, OpenSSH, bounded SMTP sink, BIND DNS, Net-SNMP, PostgreSQL, Git mirror support, the QIK-VRT terminal/effect HTTP plane, an ISO-C90 IP bootstrap probe, and an MC68000 cross-development/runtime path (`gcc-m68k-linux-gnu` + `qemu-m68k`).

The MC68000-visible contract binds D0 to the five recovered effect states: NACK=0, CONTINUE=1, ISOLATE=2, BLOCK=3, DONE=4. D1 is the session/channel id, D2 freshness/nonce, D3 source/capability context, A0 request pointer, A1 receipt pointer. The recovered overlay model has four banks, requires a fence before switching, flushes instruction prefetch, and permits ordinary release only from stable EFFECT_ACK_DONE.

A statically linked `-m68000` executable witness is built inside the image and executed with qemu-m68k. This proves the bounded software contract can be generated for and executed as M68000-family machine code in the emulated test path. It is not a claim that Debian, Docker or the host runs on physical 68000 hardware.

## Infrastructure as Code / IP bootstrap

`deploy/universal-terminal/compose.yaml` materializes a fixed `10.73.0.0/24` Mesh. The terminal occupies `10.73.0.2`, SQL `10.73.0.3`, Authority-connected mirror `10.73.0.4`, and the MC68000 development role `10.73.0.6`; service roles occupy additional fixed addresses. The recovered bootstrap contract uses server `10.73.0.1`, UDP discovery port 7331, client `10.73.0.2`, artifact `QIKVRT_BOOT.BIN`, 128-byte chunks, 2-second timeout, three retries and FNV1a32 over the discover/offer/request/data/done route. The universal service plane also contains a bounded C90 HTTP bootstrap probe used for live endpoint verification.

The persistent `/var/lib/qikvrt/personal-posix` volume is the owner source slot. If `build-qikvrt-m68k.sh` exists it is invoked with MC68000 C90 compiler/runner bindings. `QIKVRT_REQUIRE_PERSONAL_POSIX=1` makes absence fail closed rather than silently claiming a complete personal POSIX implementation.

## Boundaries

`TRANSPORT_ACK != EFFECT_ACK`. Container build, network reachability and emulator success are separate observations. A deployment, physical MC68000 execution, physical effect, public-cloud reachability, or general EFFECT_ACK_DONE requires its own effect readback.

The exact phrase/definition of the owner's **0-1-2-4-Bit-Logik** was not recovered verbatim from the searched prior conversation/library artifact or the recovered PR specifications. This implementation therefore does not invent an algebra for it. It implements only the recovered five-state D0 mapping and four-bank overlay contract until the original 0-1-2-4 definition is supplied or located.
