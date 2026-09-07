# QIK-VRT Cloud Transputer v1

This carrier extends the existing durable Firefox universal terminal into a repository-native IP service appliance while preserving QIK-VRT effect boundaries.

## Stable surface

The fixed public entry point is:

`https://goldkelch.github.io/qik-vrt/cloud-transputer/`

GitHub Pages is only the stable launcher/proxy UI. It is **not** the long-running compute origin. A deployment must bind an operator-controlled HTTP(S) runtime origin through `QIKVRT_MESH_PUBLIC_URL`; the resulting runtime receipt records that exact value.

## Runtime planes

The OCI image contains:

- Firefox ESR, Xvfb, x11vnc and noVNC, reverse-proxied by nginx;
- the existing QIK-VRT Effect_ack HTTP capability and strict ANSI-C90 Effect_ack core;
- bounded local SMTP reception without an external relay path;
- dnsmasq DNS, Net-SNMP snmpd and OpenSSH sshd;
- PostgreSQL with a SQL-92 smoke/readback path;
- a one-shot bare mirror of `https://github.com/Goldkelch/qik-vrt.git`;
- `gcc-m68k-linux-gnu` plus `qemu-m68k` to compile and execute a real M68000-family binary built from the repository's C90 Effect_ack core.

The default Compose exposure is loopback-only. A cloud ingress may deliberately set `QIKVRT_BIND_ADDRESS`, but that is an operator deployment effect and must be separately secured by TLS/firewall/authentication policy.

## Personal POSIX source slot

The persistent volume `/var/lib/qikvrt/personal-posix` is reserved for the owner's actual POSIX implementation. If it contains executable `build-qikvrt-m68k.sh`, the runtime invokes it with:

- `CC=m68k-linux-gnu-gcc`
- strict C90 flags (`-std=c90 -pedantic -Wall -Wextra -Werror -static`)
- `QIKVRT_M68K_RUNNER=qemu-m68k`

`QIKVRT_REQUIRE_PERSONAL_POSIX=1` changes absence of that exact source/build entrypoint from a recorded UNBOUND state into a fail-closed startup blocker.

The built-in M68000 Effect_ack probe is real compilation and M68000 execution evidence, but it is **not** relabelled as the complete personal POSIX implementation and does not claim a standalone M68000 TCP/IP stack. The container's TCP/IP services are kernel-backed POSIX networking until an exact standalone stack is separately supplied and verified.

## Credentials

No service secret is stored in the repository. Optional runtime files provide:

- `QIKVRT_VNC_PASSWORD_FILE`
- `QIKVRT_SQL_PASSWORD_FILE`
- `QIKVRT_SSH_AUTHORIZED_KEYS_FILE`
- `QIKVRT_SNMP_COMMUNITY_FILE`

SSH password authentication is disabled. SMTP accepts only the configured local mesh domain and performs no external relay.

## Authority mirror

`qikvrt-authority-mirror-refresh` executes once at boot or when explicitly invoked. It enforces the canonical Authority HTTPS URL, uses a bare mirror, reads `refs/heads/main` and persists the observed SHA/tree. It never polls and never pushes to Authority.

## Local execution

```sh
QIKVRT_MESH_PUBLIC_URL=https://runtime.example.invalid \
  docker compose -f deploy/cloud-transputer/compose.yaml up --build
```

Then the HTTP terminal proxy is at the configured host port (default `127.0.0.1:8080`). Raw protocol planes default to loopback host bindings in Compose.

## Verification boundary

The dedicated GitHub Actions workflow builds the exact PR head, starts the image, reobserves all protocol planes, executes the C90→M68000 Effect_ack probe, checks the Authority mirror receipt and PostgreSQL SQL query, restarts with persistent state, and uploads an exact-head evidence artifact.

CI execution proves that exact container artifact on the GitHub runner. It does not by itself establish persistent public cloud reachability, a DNS/TLS effect, physical M68000 hardware execution, the owner's complete POSIX implementation, `PASS`, `FINAL_PASS`, or general `EFFECT_ACK_DONE`.
