<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation documentation: OpenAI Codex. -->

# Universal Transputer: C90 core and durable IP bus

The Transputer connects layers through a common, explicitly bound message format.
The core is C90: Boolean kernel, wire encoding, reassembly, participant admission
and addressed request/reply routing. Rust supplies TCP/IP, authentication, durable
storage, the TEMDD compiler and the local terminal. The application executes the
C90 kernel through its octet ABI; the Rust layer does not replace that kernel.

Start a new session at [AI](AI). Stable component names and source entrypoints are
in [TARGET_ENTRYPOINTS.json](TARGET_ENTRYPOINTS.json). Resolve the actual Git HEAD
and TREE before interpreting evidence. This branch extends product integration
`26bc470bf553f471abc02e65950acaffb3e5302a`; its existence does not promote it to Main.

## Build and reproduce

For the C90 library and native assembler round trip, with a host C compiler:

```sh
make -C next/core test assembly
```

This produces `next/core/build/libqikvrt_transputer.a`, the standalone
`qikvrt-c90` transport adapter and an assembled/relinked kernel test. The inner
core uses no OS, network, heap allocation or Rust. It requires eight-bit bytes
and an exact 32-bit unsigned C type. Port-specific code may replace the kernel
behind the same 14-byte input / 6-byte output ABI and must pass the same checks.
The tested assembler target is the host x86-64 CPU. Physical boards, MC68000 boot,
FPGA placement, timing and resource closure require separate validation.

For the higher runtime on Linux x86-64, install the locked tools into an isolated
directory. This is also exposed through `tools/bootstrap-runtime.sh --profile target`.

```sh
python3 next/tools/bootstrap.py --prefix "$PWD/../qikvrt-tools" --install
. ../qikvrt-tools/target-env.sh
"$QIKVRT_CARGO" build --release --locked --manifest-path next/Cargo.toml
python3 next/tools/run_checks.py --output-dir "$PWD/../qikvrt-evidence"
```

The complete check requires a clean committed checkout. It records its exact
HEAD/TREE and hashes the executable and logs. After dependencies are cached,
add `--offline`. Python 3.11+, make, ar, a C90 compiler and dpkg-deb are host
tools; Rust, Cargo dependencies and GHDL are locked. No system replacement is
performed. Other hosts can provide their own toolchains explicitly.

## Connect participants

Create an exact subject file, for example from the current checkout:

```sh
python3 - <<'PY' > ../subject.json
import json, subprocess
def git(*args): return subprocess.check_output(['git', *args], text=True).strip()
print(json.dumps({'repository':'Goldkelch/qik-vrt', 'subject_id':'bus-session',
                  'head':git('rev-parse','HEAD'), 'tree':git('rev-parse','HEAD^{tree}')}))
PY
next/target/release/qikvrt-next bus-config ../private-bus bus ../subject.json A B C
next/target/release/qikvrt-next init ../bus-store bus
next/target/release/qikvrt-next init ../a-store A
next/target/release/qikvrt-next init ../b-store B
next/target/release/qikvrt-next bus-serve ../bus-store ../private-bus/bus.json 127.0.0.1:8772
```

In separate terminals, start A and B. Use a routable address instead of loopback
to connect separate machines; IPv6 addresses use `[address]:port`.

```sh
next/target/release/qikvrt-next bus-peer ../a-store ../private-bus/A.json 127.0.0.1:8772
next/target/release/qikvrt-next bus-peer ../b-store ../private-bus/B.json 127.0.0.1:8772
```

Each participant can send requests and responses concurrently over its persistent
TCP connection. `JOINED` contains the public participant directory and exact
subject digest. On the participant's standard input, send JSON lines:

```json
{"op":"send","destination":"B","subject":"<subject digest from JOINED>","codec":2,"payload_hex":"68616c6c6f"}
```

The receiver reports `RECEIVED`, including source, subject, session, nonce,
message ID and the complete request correlation digest. To answer a request,
use `op: "reply"`, destination equal to its source, codec 3, and copy those exact
binding fields into the reply. Responses may arrive in any order. They are
matched by binding, not by arrival order. `check_bus.py` is the executable example
for three participants sending simultaneously and answering in reverse order.

Adding `--worker` applies the supported store commands and returns a bound EAP
receipt. Codec 1 carries a JSON `Command`, codec 2 an immutable object, codec 3 a
receipt. Workers invoke the C90 calculation or store operation, and preserve
results before replying. They do not execute arbitrary shell or Git commands.
`serve STORE 127.0.0.1:8771` opens the local TEMDD editor and history terminal;
one process owns a store at a time, so stop its bus peer before opening that
same store in the terminal.

## Protocol and evidence boundaries

| Layer | Contract |
| --- | --- |
| TCP/IP adapter | Full duplex IPv4/IPv6; authenticated challenge and per-frame HMAC-SHA256, channel direction and monotonically checked transport sequence |
| C90 bus | 16 configured participants, 32 unfinished calls; targeted reverse replies bound to original source, destination, subject and full request digest |
| Wire | Existing QVRT v1, 84-byte header, at most 4096-byte payload, 4-byte trailer; unchanged legacy golden bytes |
| QXT2 payload | 172-byte route including source/destination layer and identity, exact subject, complete-body hash and request correlation; 16 fragments, at most 62,784 body bytes |
| EAP | Existing `src/effect_ack_core.c`; explicit conversion between internal enum and wire D4 states; admission returns CONTINUE, never ordinary release |
| Store | Stable identity, SHA-256 objects, immutable hash-chained events, writer exclusion, create-only publication, fsync and readback; explicit causal references |

HMAC authenticates frame bytes; it provides no encryption. The operator keeps
per-peer private keys outside Git and distributes each credential to its owner.
Possessing a peer key does not prove a natural person's identity or authorize
unrelated external effects. IP reachability alone does not confer participation.
This is an addressed bus with one durable router; distributed router consensus
and automatic route discovery across independent routers are not implemented.

A complete frame or successful computation is not evidence of an external
effect. Receipt claims remain subject-bound observations. TCP/MAC sequence is
not causality. Neither a queued message nor a transport acknowledgement sets
`ordinary_release` to true.

## Retain and recover the Transputer

`init` creates a new directory explicitly. All ordinary commands open an existing
store and fail if it is absent or acknowledged history is damaged. Disconnects
and reachability expiry retain registered identity and original versions. Bus
outboxes persist before forwarding; replay is at least once, with idempotent
event IDs for already committed model effects. No global exactly-once claim is
made for arbitrary external effects. No history cleanup runs automatically.

Preserve both the earlier source catalog and this exact successor in a store:

```sh
next/target/release/qikvrt-next init ../source-store source-archive
git fetch --no-tags --depth=1 https://github.com/Goldkelch/qik-vrt.git 26bc470bf553f471abc02e65950acaffb3e5302a
python3 next/tools/carrier.py import --store ../source-store
python3 next/tools/carrier.py catalog --head HEAD > ../target-catalog.json
python3 next/tools/carrier.py import --store ../source-store --catalog ../target-catalog.json
next/target/release/qikvrt-next discover ../source-store
python3 next/tools/carrier.py restore --store ../source-store --digest <catalog-sha256> --destination ../restored-target
```

The stable `universal-transputer` registration now has both source versions.
When generating a catalog from the second repository's branch, pass
`--repository ingolf-lohmann/qik-vrt` so its distinct commit stays correctly attributed.
Restoration verifies the original bytes and Git blob identities without the
source checkout or remote access. The restored target includes the C90 library
and its original EAP dependency and can be built from those recovered sources.
The selected source catalog is not an archive of every external toolchain.

`snapshot STORE` preserves the original store's metadata, events, anchors and
objects as a content-addressed manifest. `restore-store CARRIER_STORE DIGEST
NEW_DIRECTORY` restores those original bytes, identity and checkpoint. Transfer
the manifest and every referenced object before restoring; `check_exchange.py`
executes this through TCP. Retain independent backups and checkpoints: deleting
every copy cannot be repaired from a digest alone. Historical results keep the
original producer executable digest and are not recomputed by a successor.

The runtime has finite message, peer and unfinished-call bounds and currently
loads its history into memory. This release candidate demonstrates preservation
and reconstruction within the tested profile, not unlimited physical storage or
unbounded scaling. The six-language proof sources are retained byte for byte in
`reference/full-core-draft03/`; their archived proofs are not transferred to this
successor. The fresh suite compares the linked C90 EAP against that frozen
contract and separately exercises the bus, store and hardware model.
