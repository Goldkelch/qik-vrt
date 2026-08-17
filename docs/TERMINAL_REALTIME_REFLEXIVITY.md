# QIK-VRT Terminal Realtime Reflexivity

This extension makes the Standard Terminal a bidirectional live peer rather than only an audit projection.

## Timing contract

Every active terminal peer emits its current inward state at least every 4 seconds. A counterpart MUST treat an envelope as stale once it is older than 5 seconds. Stale state remains observable, but it MUST NOT admit productive work. The one-second margin is intentional so ordinary scheduling jitter does not consume the whole five-second freshness budget.

The five-second property is an active-runtime contract. GitHub Actions is not a five-second transport and remains the durable audit/handoff plane. A connected client may carry the canonical JSONL envelopes over stdio, Unix sockets, WebSocket, SSE, MQTT, another mesh transport, or an equivalent low-latency adapter. The adapter may not change event identity, freshness, admission, or completion semantics.

## Bidirectional use

Every implementation is both emitter and receiver. The emitter rereads its current terminal state before each heartbeat and sends a monotonic sequence number. The receiver validates event identity, freshness, sequence ordering, and the absence of credential-shaped fields before rendering the peer state.

Example emitter:

```bash
python3 -B tools/qikvrt_terminal_realtime.py stream \
  --peer-id mesh/node-a \
  --state .qikvrt/standard-terminal/terminal-inward.json
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
- **Visual:** a terminal status frame exposing peer identity, event identity, freshness, state, blocker, and next action.
- **Auditory:** speech text for a TTS-capable client plus an earcon hint. A terminal BEL is the dependency-free fallback; raw audio generation is not required by the repository core.

Clients SHOULD negotiate capabilities and choose the lowest-latency representation supported by the counterpart. They MAY present several modalities simultaneously. Modalities are views of one event; none may strengthen semantic truth or completion claims.

## Safety

Peer envelopes contain state only. Token-, secret-, password-, private-key-, and credential-shaped fields are rejected. Untrusted or stale peer state cannot admit a productive writer. `PASS`, `FINAL_PASS`, and `EFFECT_ACK_DONE` remain false unless separately established by their own exact evidence contracts.
