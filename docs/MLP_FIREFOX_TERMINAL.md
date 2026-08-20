# MLP.PRG → Firefox QIK-VRT Terminal

This work unit binds the already materialized Atari/M68000 MLP executable to the existing Firefox QIK-VRT interactive terminal and Effect-Acknowledgement implementation.

## Execution topology

The Atari Mega-ST guest does **not** pretend to execute Firefox natively. The guest-visible `C:\MLP.PRG` is byte-identical to the exact `MLP.TOS` image. Starting it produces the canonical `C:\MLP.OPEN` request frame after the M68000 register and fail-closed file-publication checks. A host-side bridge validates that exact frame and source binding and may then launch a stock Mozilla Firefox instance with the repository's QIK-VRT WebExtension terminal.

Firefox therefore retains the capabilities of the actual Firefox runtime in use. QIK-VRT adds terminal semantics and effect gating; it does not reimplement Gecko or claim capabilities that the installed Firefox build does not possess.

## Terminal, not monitor-only

The Firefox extension already implements an interactive terminal path against the local backend at `127.0.0.1:8771`. Protected effects use discovery, prepare, exact record/token/hash validation, explicit commit, and subsequent observation. Rendering or HTTP success alone is never executable authority.

`REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED`

`TRANSPORT_ACK != EFFECT_ACK`

The host launcher preserves these boundaries: creating a Firefox process is `EXECUTED`; it is not proof of browser readiness, user-visible rendering, a protected external effect, or `EFFECT_ACK_DONE`.

## Desktop manifestation

For the Hatari shared-drive envelope, the repository launcher stages the exact executable bytes as `C:\MLP.PRG`. That makes the program guest-visible through the mounted C drive and therefore available from the TOS desktop/file environment. Desktop icon layout is OS/desktop-specific and is deliberately not confused with program availability.

## Operating-system portability

The architecture is adapter-oriented. It does not claim that one Atari Mega-ST hardware instance can literally execute every operating system ever written or any unknown future operating system. The stronger and testable contract is:

> an operating system can participate when a compatible MLP launch adapter, network/transport adapter, and Firefox/terminal counterpart exist for that environment.

Unsupported environments fail closed. Future operating systems can be added by implementing the same boundary contracts without changing the M68000 decision semantics.

## Current evidence boundary

PR #744 establishes deterministic MLP materialization and virtual Mega-ST execution. PR #745 separately targets guest-side TCP/IP proof. This work unit implements the MLP→Firefox terminal launch/integration layer but must not claim guest TCP/IP success until #745 produces a bound guest-originated roundtrip receipt, nor browser observation or Effect Ack until those effects are independently reobserved.
