# MLP.PRG → Firefox QIK-VRT Terminal

This work unit binds the already materialized Atari/M68000 MLP executable to the existing Firefox QIK-VRT interactive terminal and Effect-Acknowledgement implementation.

## Exact predecessor proof

The stacked base is PR #745 exact head `a71484ba02f6ebe9169af5a291244e99468caec3`, tree `b45556a6c4ea2d9946c73264c1ed47d4f3128a76`. Exact-head run `32370359979` observed a controlled guest-originated IPv4/TCP roundtrip from the Hatari Mega-ST instance over emulated BIOS AUX/RS232/SLIP, including the exact nonce `QIKVRT-NONCE-0001`, peer response `QIK-ACK:QIKVRT-NONCE-0001`, and a causally post-response guest confirmation. That evidence does not imply Internet reachability, physical original-Mega-ST execution, Firefox execution, or Effect Ack.

## Execution topology

The Atari Mega-ST guest does **not** pretend to execute Firefox natively. The guest-visible `C:\MLP.PRG` is byte-identical to the exact `MLP.TOS` image. Starting it produces the canonical `C:\MLP.OPEN` request frame after the M68000 register and fail-closed file-publication checks. A host-side bridge validates that exact frame and source binding and may then launch a stock Mozilla Firefox instance with the repository's QIK-VRT WebExtension terminal.

Firefox therefore retains the capabilities of the actual Firefox runtime in use. QIK-VRT adds terminal semantics and effect gating; it does not reimplement Gecko or claim capabilities that the installed Firefox build does not possess.

## Terminal, not monitor-only

The Firefox extension implements an interactive terminal path against the local backend at `127.0.0.1:8771`. Protected effects use discovery, prepare, exact record/token/hash validation, explicit commit, and subsequent observation. Rendering or HTTP success alone is never executable authority.

`REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED`

`TRANSPORT_ACK != EFFECT_ACK`

The host launcher preserves these boundaries: creating a Firefox process is `EXECUTED`; it is not proof of browser readiness, user-visible rendering, a protected external effect, or `EFFECT_ACK_DONE`.

## Desktop manifestation

For the Hatari shared-drive envelope, the repository launcher stages the exact executable bytes as `C:\MLP.PRG`. That makes the program guest-visible through the mounted C drive and therefore available from the TOS desktop/file environment. Desktop icon layout is OS/desktop-specific and is deliberately not confused with program availability.

## Operating-system portability

The architecture is adapter-oriented. It does not claim that one Atari Mega-ST hardware instance can literally execute every operating system ever written or any unknown future operating system. An operating system can participate when a compatible MLP launch adapter, network/transport adapter, and Firefox/terminal counterpart exist for that environment. Unsupported environments fail closed.

## Current evidence boundary

PR #744 establishes deterministic MLP materialization and virtual Mega-ST execution. PR #745 now establishes the controlled guest-side TCP/IP roundtrip for its exact bound tuple. This successor rebinds the MLP→Firefox terminal integration to that proven generation. Browser readiness, terminal rendering, protected external effect, and `EFFECT_ACK_DONE` remain separate observations and are not claimed by source binding alone.
