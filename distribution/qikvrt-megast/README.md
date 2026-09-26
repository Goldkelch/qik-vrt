# QIK-VRT Mega ST Distribution

This directory defines the downloadable QIK-VRT Linux distribution whose desktop deliberately recalls an Atari Mega ST while remaining a modern GNU/Linux workstation and QIK-VRT Universal Terminal.

## Definition of Done for this distribution

The distribution lane is not complete merely because an ISO builds. Its terminal predicate requires all of the following on one exact trusted-Main subject:

1. a reproducible bootable amd64 ISO is built from the repository;
2. the ISO contains the QIK-VRT TEMDD/Effect-ACK contract and Universal Terminal client surface;
3. a graphical session presents a deliberately Mega-ST/GEM-inspired visual shell;
4. Hatari starts the ST environment with the hash-locked, redistributable EmuTOS ROM; no proprietary Atari ROM is redistributed by this project;
5. modern software remains available through native Debian packages, Flatpak, OCI/Podman and the web browser instead of being trapped inside the 68k guest;
6. build manifest, ISO SHA-256 and exact git subject are emitted as receipts;
7. the released asset is downloadable from the stable release path and independently read back after publication;
8. EFFECT_ACK_DONE is claimed only after that download, checksum and boot/runtime contract have been reobserved.

Canonical download target after a legitimate trusted-Main publication:

`https://github.com/Goldkelch/qik-vrt/releases/latest/download/qikvrt-megast-amd64.iso`

## Architecture

The host is Debian Live. Xfce is the modern desktop substrate. `qikvrt-megast-session` applies a restrained GEM/Mega-ST visual vocabulary (light grey work surface, dark borders, compact controls, monospaced terminal) while keeping ordinary Linux applications usable. Hatari supplies the MC68000-era Atari hardware environment. QIK-VRT services stay on the Linux side and therefore can evolve without pretending that contemporary applications execute natively on a 1980s 68000.

Compatibility is intentionally layered:

- **Atari layer:** Hatari with the bundled, hash-locked EmuTOS ROM;
- **native Linux layer:** Debian packages;
- **portable desktop layer:** Flatpak;
- **service/container layer:** Podman/OCI;
- **universal application layer:** Firefox/Web;
- **QIK-VRT layer:** TEMDD, exact-subject receipts, Effect Acknowledgement, Mesh/Universal Terminal integration.

The desktop opens the existing universal Transputer terminal at
`http://127.0.0.1:8772/AI`. `qikvrt-next` runs the C90 core through its existing
Rust adapter. The `qikvrt-transputer` service retains its identity and events in
`/var/lib/qikvrt-transputer/store`; it provisions a new identity only in a new,
empty state directory. A provisioning marker with a missing or damaged store
blocks startup and requires explicit recovery. A Live session needs a persistent
volume or an explicit store snapshot to retain this state across VM replacement.

The guest runtime witness compiles the installed TEMDD program through this
terminal, executes its Boolean operation in the C90 core, and replays the exact
stored result. Its receipt binds the image HEAD/TREE and executable digest.
The complete receipt travels through the existing boot-scoped journal relay
when the desktop user cannot write the serial device. The receiving boot client
requires that complete, matching receipt; a success marker alone is rejected.
This local operation does not claim `EFFECT_ACK_DONE`. The existing Effect-Ack
endpoint remains at port 8771. Authenticated peer connections use the same
`qikvrt-next bus-config`, `bus-serve` and `bus-peer` entrypoints documented in
[the universal Transputer guide](../../next/README.md); no public bus listener or
peer credentials are created by the image.

This is a compatibility envelope, not a claim that literally every existing program can execute on every CPU or license regime.

## Local build

Run as root or in a Debian runner with `live-build`, `debootstrap`, `xorriso` and `squashfs-tools` installed:

```sh
sudo ./distribution/qikvrt-megast/build.sh
```

The script writes `out/qikvrt-megast-amd64.iso`, `out/qikvrt-megast-amd64.iso.sha256` and `out/qikvrt-megast-build-receipt.json`.

## Network image and executing receiver

The same build now exports `qikvrt-megast-vmlinuz`, `qikvrt-megast-initrd`,
`qikvrt-megast-filesystem.squashfs` and `QIKVRT_BOOT.BIN`. The machine-readable
`qikvrt-netboot.json` binds their byte counts, SHA-256 values, source commit,
host architecture and fixed boot method. `qikvrt-netboot-client.py` downloads
only those files, validates the caller-provided manifest digest and starts
QEMU with the exact kernel/initrd and an HTTP-fetched live root filesystem.
It attaches no CD-ROM. No command supplied by the remote manifest is executed.

After legitimate publication, use the exact release's client and manifest hash:

```sh
python3 qikvrt-netboot-client.py receive MANIFEST_URL EXPECTED_MANIFEST_SHA256 ./qikvrt-received --boot
```

The client needs Python 3.11+ and `qemu-system-x86_64` on Linux x86_64. HTTPS is
required for public downloads; an explicit private IP supports an isolated test
network. It reobserves the network-booted guest's Xfce/Firefox window, loopback
Effect-Ack endpoint, 7,864,387 C90 assertions, restored Smalltalk image and the
received MC68000 program's actual execution under `qemu-m68k`. The serial log
and receipt retain source and manifest hashes. The receipt names the immutable
`qikvrt-netboot-witness.log` snapshot it hashes; the live serial log may keep
growing during use and shutdown. This is an emulated CPU-family
witness, not a physical Atari boot or an independent human release approval.

The C90 bootstrap receiver additionally implements the existing fixed file-id 1
UDP route: discover, offer, request, data, done; 128-byte chunks, FNV1A32 frame
checks, two-second receive timeout and three bounded attempts. It binds every
reply to nonce, offset and total size, verifies a separately supplied full-image
SHA-256 and re-reads the persisted file. The maximum bootstrap program is 4 MiB;
large operating-system images use the manifest/HTTP lane. A content `done`
datagram is never the guest-execution receipt.

Build and test sources:
`src/cloud_transputer/qikvrt_boot_receive.c`, `src/smalltalk/`, `boot.py` and
`runtime-witness.py`. The existing distribution workflow runs the complete
C90/Smalltalk comparison and the real network boot before its Main-only
publication step.

## Opt-in SSH connection to the Linux guest

The image reuses `deploy/universal-terminal/sshd_config`. SSH starts only when
the VM owner supplies one Ed25519 public key. Password and root login remain
disabled. Stock SSH units are masked, and image-build host keys are removed;
each new live guest generates its own host key. The guest permits the live user
`qikvrt`, whose privileges are those of the existing live workstation account.

Start the verified network image with your **public** key:

```sh
python3 qikvrt-netboot-client.py receive MANIFEST_URL EXPECTED_MANIFEST_SHA256 ./qikvrt-received \
  --boot --ssh-public-key ~/.ssh/id_ed25519.pub
```

After the guest runtime has started, connect from another local terminal:

```sh
ssh -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=./qikvrt-received/qikvrt-netboot-known-hosts \
  -i ~/.ssh/id_ed25519 -p 2222 qikvrt@127.0.0.1
```

QEMU carries only the public key through `fw_cfg` and exposes guest port 2222
at host **127.0.0.1:2222**. Use `--ssh-port` to select another local port. The
host-key trust file comes from the verified guest's serial console. No unverified
network key scan or disabled host-key check is used. The HTTP server serves only
the four fixed boot assets, never receipts or keys.

For automated verification, `--ssh-identity /outside/image/private-key` performs
a real SSH command and checks the live user, source HEAD and source TREE against
the manifest. It requires a noninteractive identity; private keys never belong
in the image directory. `--ssh-reject-identity` additionally requires an unrelated
key to be explicitly rejected. The distribution workflow generates two temporary
keys outside its download/upload directories and deletes them after the VM test.
With `--verify-only` the guest is closed after verification; without that flag
the session remains available until the VM exits.

`qikvrt-netboot-ssh-receipt.json` records this SSH evidence separately from
`chatgpt_pairing: NOT_ESTABLISHED`. The ISO contains no personal Codex login or
pre-established client connection. The included upstream CLI does provide native
manual pairing: `codex remote-control pair`. This is distinct from the login
code issued by `codex login --device-auth`.

The image includes the complete official Codex CLI **0.155.1** Linux package,
including its Code Mode host and sandbox helpers. The versioned archive is bound
by size and SHA-256 in `runtime/toolchains/codex-0.155.1.lock.json`; the existing
image downloader verifies cached and fresh bytes before extraction. The package
retains bundled license notices and source references. A mismatch aborts the
build without replacing an existing installation.

The automated SSH readback also starts `codex app-server --listen stdio://`
through the guest's login shell, performs `initialize` / `initialized`, and reads
`account/read` without refreshing a token or requesting a model response. Its
receipt requires the fresh image to have no signed-in account. It proves protocol
availability through SSH; owner login and native client pairing remain separate.

In the running Linux desktop, open **ChatGPT verbinden** from the application
menu. The terminal stays open to display the result. This owner-invoked entry
point checks login status, requests device login if needed, then runs:

```sh
codex remote-control start
codex remote-control pair
```

Enter the actual short-lived code printed by the CLI into the client's pairing
dialog. No invented code, login secret, or pairing code is stored in build logs
or receipts. The CLI commands are experimental; successful pairing still requires
a reachable OpenAI service and acceptance in the user's supported client. Stop
the remote-control daemon with `codex remote-control stop`. This native relay
connection and SSH access have separate lifecycles.

For the desktop client's SSH connection method, sign in **inside the VM** and
add its SSH host in Settings → Connections. For a VM running on that same desktop,
an SSH configuration can reuse the verified host key file:

```sshconfig
Host qikvrt-vm
    HostName 127.0.0.1
    Port 2222
    User qikvrt
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking yes
    UserKnownHostsFile /absolute/path/qikvrt-received/qikvrt-netboot-known-hosts
```

Keep the VM boot process running without `--verify-only` while using it. A GitHub
Actions verification VM ends with its job and is not a persistent connection host.

Sources: [OpenAI remote connections](https://learn.chatgpt.com/docs/remote-connections),
[OpenAI authentication](https://learn.chatgpt.com/docs/auth),
[OpenAI app-server protocol](https://learn.chatgpt.com/docs/app-server),
[Pinned upstream native pairing implementation](https://github.com/openai/codex/blob/rust-v0.155.1/codex-rs/cli/src/remote_control_cmd.rs),
[QEMU fw_cfg](https://www.qemu.org/docs/master/system/qemu-manpage.html).

## Principle

**Stay fail closed and keep future open.** Missing runtime or publication evidence leaves the lane open; it never converts transport success into effect. The return path carries the original request, material descendants, artifacts, effects, failures, repairs, successors and still-open obligations back into the evidence chain.

## Gesicherte Repository-Nodes

Das Image enthält `/opt/qikvrt/node.py` und die Vorlage
`qikvrt-repository-node@.service`. Sie verwenden denselben C90-Transputer mit
gegenseitig authentifiziertem TLS 1.3, expliziten Zertifikats-Fingerprints und
eigenem dauerhaftem Store je Repository-Node. Das Terminal wird vom laufenden
Bus-Teilnehmer mitbedient. Zertifikate, Schlüssel, konkrete Gegenstellen und
Node-Profile werden durch den Betreiber provisioniert; sie sind nicht im
Image enthalten. Die Anleitung steht in `next/README.md`.
