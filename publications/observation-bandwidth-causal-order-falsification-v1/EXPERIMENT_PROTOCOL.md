# Experimental Protocol

## Observation Bandwidth, Reobservation, and Causal Order — Version 1

### Protocol status

```text
PROPOSED_NOT_EXECUTED
```

No observation generated while designing this protocol may be counted as a primary result.

## 1. Frozen inputs

Before any primary run, freeze and hash:

- `HYPOTHESIS_REGISTRY.json`;
- source code for generators, clients, backends, observers, and analysis;
- apparatus and calibration records;
- random seeds or seed-generation procedure;
- exclusion rules;
- primary endpoint and decision rule for each hypothesis;
- raw-data schema.

A change after primary data collection starts creates a new protocol version. Results from different versions are not silently pooled.

## 2. Common event schema

Each event record must include:

```json
{
  "event_id": "unique identifier",
  "source_id": "originating source",
  "emission_index": 0,
  "emitted_at": "raw local clock reading",
  "received_at": {"observer_id": "raw observer clock reading"},
  "predecessors": ["zero or more explicit event identifiers"],
  "intervention_id": "registered intervention or null",
  "state_before_digest": "sha256 or null",
  "state_after_digest": "sha256 or null",
  "transport_ack": false,
  "effect_ack": false,
  "reobserved": false,
  "calibration_id": "bound calibration receipt"
}
```

Raw clocks are preserved. Corrected clocks are derived fields and may not overwrite raw values.

## 3. H-OBS-01 procedure

### 3.1 Generator

Generate transition processes with:

- registered `f_max`;
- phase uniformly swept across the polling interval;
- duty cycles covering short pulses and persistent states;
- jitter strata: 0%, 1%, 5%, and 10% of the nominal interval;
- load strata: 25%, 50%, 75%, and 95% of the registered capacity ceiling;
- at least 30 independent seeds;
- at least 1,000 transitions per condition per seed.

### 3.2 Observation conditions

Evaluate polling at:

```text
0.5 × f_max
1.0 × f_max
2.0 × f_max
2.5 × f_max
4.0 × f_max
```

and an event-driven condition with explicit sequence numbers and gap detection.

A condition may claim complete polling reconstruction only if its signal assumptions and boundary are satisfied. Event-driven capture with unknown bandwidth may report observed events and detected gaps but not undiscoverable completeness.

### 3.3 Primary analysis

For each seed and stratum:

```text
missed_transition_rate =
  missed_registered_transitions / registered_transitions
```

Compare the strongest sub-boundary polling condition with the registered above-bound condition using paired seed-level differences and a bootstrap confidence interval.

## 4. H-EFF-02 procedure

### 4.1 System separation

Use four independently logged components:

```text
client
transport
effect backend
post-effect observer
```

The post-effect observer may not derive its result from the client response.

### 4.2 Fault matrix

Inject at least these classes:

1. dropped commit after prepare;
2. acknowledgement without application;
3. delayed application beyond freshness;
4. replayed commit;
5. stale read;
6. backend rollback;
7. response substitution;
8. observer gap.

Run at least 100 trials per fault class per classification method.

### 4.3 Classifiers

- `ACK_ONLY`: completion is inferred from transport/protocol acknowledgement.
- `REOBSERVE`: completion requires the registered postcondition to be independently observed.

Both receive the same non-observation inputs.

### 4.4 Primary analysis

A false completion occurs when the classifier returns complete while the authoritative postcondition is false.

Report false completion, false hold, and time to valid completion.

## 5. H-CAU-03 procedure

### 5.1 Ground truth

Construct 100 acyclic causal graphs through controlled interventions. Each edge must have a declared mechanism in the benchmark.

### 5.2 Perturbations

Apply ten replicates per graph across combinations of:

- clock skew;
- variable delay;
- packet reordering;
- batching;
- duplication;
- omission.

### 5.3 Reconstructions

Freeze two primary methods:

- timestamp-order reconstruction;
- explicit-predecessor reconstruction.

Both methods receive equal admissible event payloads. The explicit predecessor field is the treatment under study and must be declared as such.

### 5.4 Primary analysis

Compare macro-F1 against the intervention graph. Report cycle and direction errors separately.

## 6. H-ORD-04 procedure

Create paired observer paths with deliberately inverted receive order. The emission set and intervention graph remain fixed.

No predecessor may be added after the receive traces are observed.

The primary result is the fraction of trials in which both observer-local traces reconstruct the same intervention-defined graph.

## 7. H-PHY-05 procedure

### 7.1 Apparatus requirement

Use two apparatuses with independent acquisition paths. A software-only simulator does not satisfy this requirement.

Each apparatus must provide:

- controlled interventions;
- calibrated raw timestamps;
- independent state observation;
- at least 1,000 intervention trials;
- a frozen postcondition;
- immutable raw-data digests.

### 7.2 Models

Model T receives timestamp features and the registered noncausal controls.

Model C receives all Model T inputs plus explicit causal-order features that are not derived from the outcome or held-out labels.

Use identical train/test folds and hyperparameter budgets.

### 7.3 Blinding

The final held-out labels remain unavailable until feature extraction, analysis code, and decision rules are hashed.

### 7.4 Primary analysis

For each apparatus:

```text
delta_log_loss =
  log_loss(Model T) - log_loss(Model C)
```

Support requires `delta_log_loss >= 0.01` and a bootstrap 95% confidence interval with lower bound greater than zero in both apparatuses.

## 8. Exclusions

Exclude a trial only for a preregistered reason:

- calibration invalid before the intervention;
- raw record corrupt or digest mismatch;
- intervention not delivered;
- independent observer unavailable;
- apparatus safety shutdown.

Do not exclude because the outcome is inconvenient, unchanged, degraded, or inconsistent with the hypothesis.

Every exclusion remains in the audit log.

## 9. Stopping

Do not stop early for apparent success. Safety shutdown may stop an apparatus. A protocol defect may stop the experiment, but the defect and all data already collected are disclosed and the primary result remains unclaimed.

## 10. Result vocabulary

Allowed primary dispositions:

```text
SUPPORTED_WITHIN_REGISTERED_SCOPE
NOT_SUPPORTED
FALSIFIED_WITHIN_REGISTERED_SCOPE
INCONCLUSIVE
HOLD_PROTOCOL_DEFECT
HOLD_CALIBRATION_DEFECT
```

Disallowed upgrades:

```text
SUPPORTED_WITHIN_REGISTERED_SCOPE -> FUNDAMENTAL_LAW
REPOSITORY_SUCCESS -> PHYSICAL_CONFIRMATION
RECEIVE_ORDER_INVERSION -> RETROCAUSALITY
```
