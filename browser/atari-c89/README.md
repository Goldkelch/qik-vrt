# QIKVRT Atari Browser C89 Capsule

This directory binds the first executable portability layer from the repository's Firefox reference terminal to an ANSI C89 / ISO C90 core suitable for later Motorola 68000 and Atari TOS builds.

## Identity and provenance

This is **not Firefox, Gecko, SpiderMonkey, or a Mozilla product**, and it does not claim source-level equivalence with them. No Mozilla source file was copied or translated into this implementation. The code is an original, bounded behavioral implementation derived from public web protocol behavior and from the QIKVRT repository's own Firefox WebExtension contract.

The existing Firefox adapter remains the reference implementation for browser observation and bounded loopback Effect-Acknowledgement. This C89 capsule extracts only the smallest portable behavior needed to start an Atari-side browser path:

- parse bounded `http://` URLs without credentials or fragments;
- serialize an HTTP/1.0 `GET` request using fixed output storage;
- split an HTTP/1.x response into status and body without network effects;
- project a bounded HTML subset into plain terminal text;
- decode basic ASCII/numeric entities;
- suppress `script` and `style` content;
- preserve `<pre>` whitespace;
- extract a bounded link table;
- provide a TOS-friendly `qikbrow.c` command-line shell.

The reusable core performs no allocation, no network I/O, no repository write, no protected effect, and no implicit acknowledgement transition.

## Explicitly absent in V1

V1 does not implement HTTPS/TLS, certificates, DNS, HTTP redirects, chunked transfer encoding, cookies, caching, Unicode layout, CSS layout, images, audio/video, JavaScript, WebAssembly, DOM mutation, browser extensions, accessibility trees, fonts, tabs, multiprocess isolation, or a GEM/AES graphical frontend.

Therefore:

```text
ANSI_C89_CORE_COMPILES != M68000_BINARY_EXECUTED
M68000_BINARY_EXECUTED != HATARI_MEGAST_OBSERVED
HATARI_MEGAST_OBSERVED != PHYSICAL_MEGAST_EXECUTION
HTML_TEXT_PROJECTED != FIREFOX_EQUIVALENT
PREPARE != PROTECTED_EFFECT
```

## Build and local verification

From the repository root:

```sh
CC=cc sh tests/test_atari_browser_c89.sh
```

The command compiles the reusable core and test program with:

```text
-std=c90 -pedantic -Wall -Wextra -Werror
```

It also compiles `runtime/atari-megast/qikbrow.c` and exercises it against a bounded local HTML fixture.

## Atari continuation

The next history-preserving stages are:

1. bind an Atari C89 compiler identity and produce a deterministic M68000/TOS executable;
2. execute that exact binary under Hatari/EmuTOS and reobserve rendered text and links;
3. connect a transport adapter to the already bounded guest TCP/IP work unit;
4. add a GEM/AES view without weakening the fixed-memory core;
5. add the QIKVRT terminal Prepare/Commit adapter while preserving the repository's separate bounded Effect-Ack contract.

No stage is inherited from a predecessor merely because its source is present. Each new binary/head requires fresh exact-head and execution evidence.
