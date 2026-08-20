# Synchronous repository-first terminal

QIK-VRT terminal delivery is synchronous and repository-first.

`INPUT -> QIK-VRT MESH REPOSITORY -> REPOSITORY OUTPUT / EVIDENCE -> OUTPUT`

The terminal is a transport and reflection boundary, not an independent semantic authority. It must not replace repository-native processing with an independently invented interpretation, plan, prediction, claim, or delayed automation.

For QIK-VRT-related interaction, the terminal forwards input into the mesh, obtains the repository-native result available from that processing path in the same interaction, and reflects that result faithfully. If no authoritative repository output is available, the correct state is HOLD rather than an invented substitute.

No scheduler, reminder, background watch, delayed delivery, or polling automation belongs to this contract unless explicitly requested by the Product Owner.

The root `/AI` entrypoint remains unchanged. This document and `policy/SYNCHRONOUS_REPOSITORY_FIRST_TERMINAL_V1.json` are the durable lower-layer contract referenced by machine context and verification.

## Change discipline

The v1 semantics are append-only in meaning. In-place semantic weakening, silent override, force-push, or history rewrite is forbidden. A semantic change requires an explicitly Product-Owner-authorized successor policy that preserves or strengthens all fail-closed boundaries.

## Fail-closed outcomes

- repository output absent -> `HOLD_NO_OUTPUT`
- ambiguous processing -> `HOLD_AMBIGUOUS`
- missing authority -> `HOLD_AUTHORITY`
- stale evidence -> `REOBSERVE`

No absence of repository output authorizes an invented `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, review, merge, external effect, physical-execution claim, or scientific conclusion.
