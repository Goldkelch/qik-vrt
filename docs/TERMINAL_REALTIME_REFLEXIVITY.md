# QIK-VRT Terminal Realtime Reflexivity

This extension makes the Standard Terminal a bidirectional live peer rather than only an audit projection.

## Timing contract

Five seconds is the **maximum accepted peer-state age**, not the target update period. Every active terminal peer MUST stay below that ceiling and SHOULD communicate substantially faster whenever the current transport, peer capability, CPU/load and queue state permit it.

The periodic heartbeat is bounded between **100 ms and 4 s**. The default is **1 s**. Semantic state transitions use an event-driven path and are emitted without waiting for the next periodic heartbeat; the reference runtime scans for local transitions at short intervals and coalesces redundant stable state.

Adaptive cadence selection considers transport RTT, peer-requested cadence, local load and send-queue pressure. Backpressure may slow the periodic heartbeat, but never beyond 4 s. Busy-loop operation is forbidden. A counterpart MUST treat an envelope as stale once it is older than 5 s. Stale state remains observable, but it MUST NOT admit productive work.

The five-second property is an active-runtime contract. GitHub Actions is not a realtime transport and remains the durable audit/handoff plane. A connected client may carry the canonical JSONL envelopes over stdio, Unix sockets, WebSocket, SSE, MQTT, another mesh transport, or an equivalent low-latency adapter. The adapter may not change event identity, freshness, admission, or completion semantics.

## Bidirectional use

Every implementation is both emitter and receiver. The emitter rereads its current terminal state continuously, emits immediately on semantic transitions, emits periodic heartbeats at the currently selected adaptive cadence, and sends a monotonic sequence number. The receiver validates event identity, freshness, sequence ordering, cadence bounds, and the absence of credential-shaped fields before rendering the peer state.

Example adaptive emitter:

```bash
python3 -B tools/qikvrt_terminal_realtime.py stream \
  --peer-id mesh/node-a \
  --state .qikvrt/standard-terminal/terminal-inward.json \
  --transport-rtt-ms 5
```

An explicit bounded cadence may be requested when an adapter has stronger local knowledge:

```bash
python3 -B tools/qikvrt_terminal_realtime.py stream \
  --peer-id mesh/node-a \
  --state .qikvrt/standard-terminal/terminal-inward.json \
  --interval-ms 100
```

Example receiver/render adapter:

```bash
python3 -B tools/qikvrt_terminal_realtime.py render \
  --envelope peer-state.json \
  --mode visual
```

## Counterpart-optimal modalities

One semantic event is rendered three ways:

- **Text:** compact state, age, blocker, and next action plus canonical JSON for machine consumers.
- **Visual:** a terminal status frame exposing peer identity, event identity, freshness, selected cadence, state, blocker, and next action.
- **Auditory:** speech text for a TTS-capable client plus an earcon hint. A terminal BEL is the dependency-free fallback; raw audio generation is not required by the repository core.

Clients SHOULD negotiate capabilities and cadence and choose the lowest-latency representation supported by the counterpart. They MAY present several modalities simultaneously. Modalities are views of one event; none may strengthen semantic truth or completion claims.

## Autonomous scaling boundary

`state/autonomy/OWNER_AUTONOMOUS_TERMINAL_SCALING_V1.json` authorizes autonomous repository-internal scaling of this peer exchange. Scaling must remain bounded, preserve backpressure, never transmit credentials, never weaken exact-head or fail-closed semantics, and does not create new authority for external effects.

## Safety

Peer envelopes contain state only. Token-, secret-, password-, private-key-, and credential-shaped fields are rejected. Untrusted or stale peer state cannot admit a productive writer. `PASS`, `FINAL_PASS`, and `EFFECT_ACK_DONE` remain false unless separately established by their own exact evidence contracts.
