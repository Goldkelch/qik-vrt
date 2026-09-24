# QIK-VRT Recursive Execution Acceleration V1

Status: normative architecture contract.  
Owner: Ingolf Lohmann.  
Machine policy: `policy/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.json`.

The optimization target is **verified progress per causal iteration**, not fewer
checks. Acceleration comes from removing synthetic waits, rebinding successors
immediately, parallelizing independent work and serializing only real writer
conflicts.

## Canonical execution loop

```text
COMPILE
-> BIND
-> RESOLVE
-> EXECUTE
-> TEST
-> OBSERVE
-> READBACK
-> ACCEPT
-> EFFECT_ACK_DONE
```

If the declared scope is not done:

```text
observed successor
-> validate identity/provenance
-> NEXT_BOUND_INPUT
-> determine first causal blocker
-> smallest authorized effect
-> fresh readback
-> repeat
```

The predecessor is immutable history, never the active subject after a verified
successor exists.

## Acceleration invariants

```text
BLOCKER -> NEXT_WORK_UNIT
EXPLANATION != PROGRESS
ACTION_REQUIRED(0 jobs) != JOBS_EXECUTED
QUEUED != EXECUTED
PENDING != EXECUTED
TRANSPORT_ACK != EFFECT_ACK
FAIL_CLOSED != GLOBAL_IDLE
PREDECESSOR_EVIDENCE_TRANSFER = false
```

Independent work units SHOULD progress concurrently. Only mutations that compete
for the same writer, protected ref, external resource or exact effect boundary
are serialized. A local lease never justifies repository-wide inactivity.

Missing authority is scope-local: the protected effect remains blocked, while
diagnosis, evidence collection, read-only observation, independent work and
successor preparation continue where authorized.

## Node and interface inheritance

Every current or future QIK-VRT node, Mesh instance, agent adapter, runtime,
workflow carrier and architecture interface inherits this contract through:

```text
/AI
-> AI_CONTEXT.json
-> required_read_order
-> policy/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.json
```

Compatibility adapters MUST resolve `/AI`; they do not carry independent copies
of this policy. Local interfaces may strengthen the contract but may not weaken,
omit or reinterpret exact-subject binding, blocker recursion, successor rebinding,
writer isolation, fresh readback or Effect-Acknowledgement semantics.

Explicit integration surfaces include the repository agent protocol, Universal
Transputer entrypoint, TEMDD normative core, Mesh self-explanation contract, real
Mesh runtime, Cloud/Universal Terminal boundary and Firefox proxy boundary.

## Completion boundary

A successful local carrier is not repository-wide completion. A publication
Effect-Ack is not a merge Effect-Ack. A native review is not a merge. A merge is
not Main readback. Each scope is a separate subject and must be freshly bound,
executed, observed and accepted.

```text
LOCAL_EFFECT_ACK != REPOSITORY_EFFECT_ACK_DONE
PUBLICATION_EFFECT_ACK_DONE != REPOSITORY_EFFECT_ACK_DONE
OPEN_PRODUCTIVE_WORK -> REPOSITORY_EFFECT_ACK_DONE = false
```
