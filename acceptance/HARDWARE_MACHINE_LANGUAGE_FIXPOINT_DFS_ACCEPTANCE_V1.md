# Hardware/Machine-Language Fixpoint DFS Acceptance V1

The carrier is accepted only when all observations bind one unchanged pull-request head and tree.

## Required exact position order

```text
0 hardware
1 machine_language
```

## Required bytes

- hardware SHA-256: `4997a64fcb2f8e54837b62be3a7532c62b109a568620af36fe69aebd7b9aa330`
- machine-language SHA-256: `d2dae3448e182bfd2a899fea4e1e9b55510d4909427f966f2a4563c717458901`

## Required observation behavior

- native repository events are the primary continuation edge;
- a rotating five-minute reconciliation slot covers event-delivery gaps across all opted-in open PRs;
- every Actions run is traversed workflow → job → step;
- current-head commit statuses, submitted reviews and review requests are included;
- the first causal adverse disposition is the deepest failing step, then its job, then its workflow;
- incomplete pagination, head drift or tree drift cannot be projected as terminal completion;
- no polling loop, blind retry, merge, publication or deployment is permitted.

## Claim boundary

`OBSERVE` means only a local exact-head observation fixpoint.

```text
PASS=false
FINAL_PASS=false
EFFECT_ACK_DONE=false
AUTHORITY_MAIN_EFFECT=false
PHYSICAL_HARDWARE_EXECUTION=false
```
