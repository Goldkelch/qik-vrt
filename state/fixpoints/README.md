# QIK-VRT positional fixpoints

Canonical V1 contract: `QIKVRT_HARDWARE_MACHINE_LANGUAGE_FIXPOINT_V1.json`.

Traversal is exact and positional:

```text
hardware
└── machine_language
```

The associated observer is read-only, exact-head/tree bound, event-driven and depth-first. Its `OBSERVE` state is local observation only and is never a substitute for PASS, FINAL_PASS, Authority effect, publication, deployment or EFFECT_ACK_DONE.
