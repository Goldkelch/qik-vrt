# Horizon event-driven monitor contract

Horizon does not poll GitHub and does not poll its Vercel backend.

The eight visible gates are projected from repository-native `workflow_run` events through the universal terminal pattern. The event carrier observes one of the eight bound workflows, classifies its exact state, binds the exact `head_sha` at D0, sends one idempotent monitor event to the Vercel ingress, reads back the ingress receipt, and terminates without asserting an authority effect.

The Vercel ingress authenticates the GitHub Actions caller through GitHub OIDC, validates repository/event/gate/head bindings, persists the latest exact-head gate projection, and appends the transition to a Redis stream. The browser performs one snapshot read on initial connection and then holds one Server-Sent Events connection. Redis `XREAD BLOCK` wakes only when a new transition is appended; there is no interval-based state read.

Transport keep-alive comments and EventSource reconnection are connection-liveness mechanisms, not repository-state polling. A reconnect resumes from `Last-Event-ID` and the durable stream.

The former `/api/gates` timer endpoint is intentionally disabled. `/api/state` is snapshot-only and reads the durable projection; it never calls GitHub. Repository state changes reach Horizon only through repository-native events.

This surface is monitor-only. `TRANSPORT_ACK != EFFECT_ACK`; no monitor receipt implies merge, approval, deployment, publication, PASS, FINAL_PASS, or EFFECT_ACK_DONE.
