# QIK-VRT Mesh Scaling Campaign V1

This campaign repeats the fan-out / lossless-consolidation experiment under
multiple observable Mesh states. It separates **repository state**, **runtime
state**, **measurement**, and **patent/hardware interpretation**.

## Human Definition of Done / final idle

The final idle benchmark is admitted only when both repositories independently
satisfy:

```text
Authority:
  all productive branches merged to main
  AND open pull requests = 0
  AND open issues = 0

Mirror:
  all productive branches merged to main
  AND open pull requests = 0
  AND open issues = 0
```

The Authority and Mirror main TREE values are recorded. Tree equality is not
silently added as an idle requirement because the two repository roles can have
role-local state unless equality is separately required.

## Scenarios

1. **CURRENT_BACKLOG** — real repository backlog exists; measurement is marked
   busy/non-idle.
2. **STEADY_CONCURRENT** — mixed opposing routes, fan-out 1/2/4/8/16.
3. **RESTART_RECOVERY** — one node is restarted and rebound before the measured
   workload.
4. **PARTITION_RECOVERY** — a route is deliberately made unavailable, fail-closed
   behavior is observed, the node is restored, then the measured workload runs.
5. **FINAL_IDLE** — only after the dual-repository idle predicate is freshly true.

## Evidence already established

A baseline using the original node-wide lock was lossless only at fan-out 1.
At fan-out 2, 4, 8 and 16 the median trial completed 0/20 messages and observed
`TimeoutError`.

After scoping the lock to `message_id`, all 15 measured trials
(5 fan-out levels × 3 repetitions × 20 messages) were lossless. The successor
also has explicit concurrent reverse-route and same-message replay regressions.

Those two historical runs used different hosted CPU models, so their numerical
throughput values are **not** treated as a direct hardware-independent speedup.
A same-runner A/B workflow in this campaign removes that confounder.

## Patent / hardware boundary

These measurements are useful engineering evidence about software control-flow,
fan-out, concurrency, exact result consolidation, and the consequences of a
haltpoint/serialization design. They do not by themselves establish novelty,
non-obviousness, physical MC68000 speedup, FPGA timing, ASIC/silicon speedup,
or patentability. Those remain separate evidence subjects.
