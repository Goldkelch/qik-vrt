# QIK-VRT Universal Monitor Sampling V1

The monitor side of the Standard/Universal Terminal Pattern must not display more temporal certainty than it actually observes.

## Universal rule

For any monitor that claims complete reconstruction of a material-change signal with a finite declared maximum transition frequency `f_max`, the observation rate must satisfy:

```text
sample_hz >= 2 * f_max
```

The repository default recommendation is a guard factor of 2.5 rather than operating exactly on the theoretical Nyquist boundary:

```text
sample_hz >= 2.5 * f_max
```

This is a sampling-theory condition, not a causality theorem. It does not imply that sampled order is causal order, that an observed event is an effect acknowledgement, or that the monitored process is band-limited unless that bound is separately established.

## Unknown or unbounded transition bandwidth

When no finite `f_max` can be justified, polling alone may not claim Nyquist completeness regardless of how fast it polls. The monitor must use event-driven delivery with sequence/content identity and gap detection when available, or fail closed:

```text
NO_DECLARED_BANDLIMIT -> EVENT_DRIVEN_OR_HOLD
EVENT_GAP -> REOBSERVE
```

A scheduled poll remains useful as a liveness/recovery fallback. In particular, GitHub Actions' five-minute schedule is not treated as a universal sampling proof; repository workflow events are the primary channel for faster transitions.

## Everywhere means every monitor projection

This contract applies to Authority, Mirror, every future Mesh node, Standard Terminal Pattern, Universal Terminal, repository watchdogs, live-status views, workflow-executor watchdogs, Firefox/browser terminals, Effect-Acknowledgement observation, SSE/event streams, polling fallbacks and human-visible monitor projections.

Every implementation must choose one of two typed modes:

1. `FINITE_BANDLIMIT_POLLING`: declare `f_max`, declare `sample_hz`, enforce the Nyquist lower bound and preferably the 2.5 guard factor.
2. `EVENT_DRIVEN`: do not claim Nyquist reconstruction from polling; require gap detection/reobservation and use polling only as fallback.

## Observation and rendering are different

A UI may render at 60 Hz while repository observations arrive at 1 Hz. The display refresh rate does not upgrade evidence resolution.

```text
RENDER_REFRESH_HZ != OBSERVATION_HZ
OBSERVATION_ORDER != CAUSAL_ORDER
ACTIVITY != EFFECT
TRANSPORT_ACK != EFFECT_ACK
```

## Browser and Firefox

Browser-local events, SSE, WebSocket-like streams or extension events are event-driven sources. Their delivery must carry sequence/content identity where possible. Missing sequence ranges, reconnects or uncertain continuity force reobservation before a complete history is claimed. A timer-based fallback must be admitted through the same sampling guard.

## Repository and Mesh

Repository events (`push`, `pull_request`, `workflow_run`, dispatch events) are primary observation edges. Scheduled watches are liveness fallbacks. A Mesh node that cannot bind either a finite material-transition bandwidth or a gap-detectable event stream must report `HOLD_SAMPLING_BOUND_UNKNOWN` rather than silently present an apparently complete timeline.

## Scientific boundary

The Shannon/Nyquist sampling theorem applies to appropriately band-limited signals under its mathematical assumptions. This repository contract imports that condition into monitor design. It does not by itself prove that arbitrary repository, social, biological, cognitive or physical processes are band-limited, and it does not establish a new physical law.
