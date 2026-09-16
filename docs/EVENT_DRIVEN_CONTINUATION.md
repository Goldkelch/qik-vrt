# QIK-VRT event-driven continuation

The repository core progresses from native GitHub events, never from polling or a schedule.

1. Every continuation is bound to one current pull request head.
2. Head drift is `HOLD_UNVERIFIED`; predecessor evidence is never transferred.
3. Native review is an authority boundary. Automation never synthesizes or upgrades an approval.
4. An exact-head `APPROVED` review causes fresh reobservation only; it does not imply P4, P5, Main, deployment, publication, or `EFFECT_ACK_DONE`.
5. Workflow completion and pull-request state changes wake the trusted requested-review executor, which remains responsible for gate classification, durable receipts and fail-closed successor selection.
6. The wake-up carrier has no merge capability and no contents-write capability.
7. Repository-core scheduling and polling are forbidden; scheduling belongs outside this core.

Causal spine: `event -> exact subject -> predecessor verification -> admissible edge -> authoritative readback -> next event`.
