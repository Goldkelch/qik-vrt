# Observation Bandwidth, Reobservation, and Causal Order

## A Falsifiable Experimental Program Derived from the QIK-VRT Computational Architecture

**Ingolf Lohmann**

### Status

```text
PROPOSED_NOT_EXECUTED
```

This manuscript is a preregistration-oriented research program. It does not report a completed physical experiment. It separates already executed computational evidence from hypotheses that remain untested.

### Abstract

QIK-VRT is a computational architecture designed to preserve distinctions that are frequently collapsed in automated systems: temporal sequence versus causal order, execution versus observed effect, change versus improvement, and monitoring versus complete observation. A repository-native precursor has demonstrated, within a bounded Linux/Firefox/loopback setting, an adaptive sampling contract, a real browser-mediated `DISCOVER -> PREPARE -> COMMIT` sequence, post-effect backend reobservation, and exact-head re-execution of causal-transition and Motorola-68000 source tests. That result is computational and repository-bound; it is not evidence that physical time is identical to a software-defined causal order.

This paper converts the precursor into a falsifiable experimental program. Five active hypotheses are registered. They test whether (H-OBS-01) observation rate controls missed-transition and aliasing error in a defined finite-bandwidth event process; (H-EFF-02) post-effect reobservation reduces false completion claims relative to transport acknowledgement alone under injected faults; (H-CAU-03) explicit predecessor bindings reconstruct intervention-consistent causal order more accurately than timestamp order under delay, skew, and reordering; (H-ORD-04) observer-relative receive-order inversion can occur without inversion of the intervention-defined causal graph; and (H-PHY-05) causal-order features add out-of-sample predictive information beyond timestamps in independently instrumented physical systems. Each hypothesis includes a null, primary endpoint, controls, and rejection rule. The stronger identity claim `PHYSICAL_TIME == QIKVRT_CAUSAL_TIME` is not registered as an active hypothesis because it currently lacks an operational definition capable of distinguishing it from adjacent models.

The contribution is therefore methodological: computational distinctions are transformed into measurements that can fail. Repository evidence motivates the protocol but does not count as the physical result.

---

## 1. Research question

The central computational invariant is:

```text
CAUSALITY != SEQUENCE
```

The corresponding experimental question is not whether this slogan is persuasive. It is whether a measurement program can distinguish:

```text
timestamp order
receive order
explicit dependency order
intervention-defined causal order
effect acknowledgement
post-effect reobservation
```

and whether the distinctions improve error rates, causal reconstruction, or prediction under controlled perturbations.

The program also asks a second question:

```text
What may an observer claim when the observation channel is not demonstrably able to distinguish all relevant transitions?
```

This turns observation adequacy into an explicit part of the evidence contract.

---

## 2. Computational precursor and its limits

The precursor is the successful `QIKVRT Universal Terminal System Test` executed on integrated source head:

```text
a7cea28de6ab435c01211d522613fb811bfd91b2
```

with tree:

```text
2ef860cfebd6005d7993818d2881b46b7dcf3212
```

workflow run `32536665914` and job `96938778530`.

Within that exact bounded execution:

- the adaptive Shannon/Nyquist admission and VBR-like rate-control tests succeeded;
- Firefox `153.0.4` executed through a pinned WebDriver path;
- the extension completed `DISCOVER -> PREPARE -> COMMIT`;
- the bounded loopback `terminal_input` effect reached `EFFECT_ACK_DONE`;
- the backend was reobserved after commit;
- exactly one `TERMINAL_INPUT_ACCEPTED` event with nonce `QIKVRT-FIREFOX-E2E-NONCE-0001` was present;
- causal-transition and Motorola-68000 source tests were re-executed at separately bound source head `98d66de02e98d67af81655b028d15fbd60869bbc`.

The receipt SHA-256 is:

```text
f081469cdab77d951adb60a406d8012e5e773368fa92d850a2f499981838dacf
```

The precursor also records:

```text
external_effect = NONE
physical_megast_execution = false
authority_main_effect = false
general_effect_ack_done = false
independent_review_authority = false
```

Accordingly, the precursor establishes a bounded software-system result only. It supplies an implementation and a source of testable distinctions. It does not supply physical observations for the hypotheses below.

---

## 3. Conceptual model

### 3.1 Orders

Let an event record contain:

- `t_emit`: local emission timestamp;
- `t_receive(O)`: time at which observer `O` receives the record;
- `pred`: an explicit predecessor identifier or set;
- `intervention`: an externally controlled change;
- `state_before` and `state_after`;
- `effect_receipt`: protocol-level acknowledgement;
- `reobservation`: a later observation of the affected state.

The program distinguishes:

```text
TIMESTAMP_ORDER
RECEIVE_ORDER
DECLARED_PREDECESSOR_ORDER
INTERVENTION_ORDER
```

No order is treated as causal solely because it is total or chronologically convenient.

### 3.2 Effect lifecycle

The effect lifecycle is typed:

```text
REQUESTED
-> PREPARED
-> COMMITTED
-> REOBSERVED
```

A transport acknowledgement may support `PREPARED` or `COMMITTED` depending on protocol semantics. It does not automatically establish the postcondition of the affected system.

### 3.3 Observation adequacy

For a deliberately constructed signal class with a justified finite maximum relevant frequency `f_max`, a polling monitor that claims complete reconstruction is tested at rates below, at, and above `2*f_max`.

This is not a universal claim that arbitrary event streams are band-limited. If the relevant transition bandwidth is unknown, nonstationary, or unbounded, the program requires event-driven capture with gap detection or refuses a completeness claim.

---

## 4. Registered hypotheses

The machine-readable registry is `HYPOTHESIS_REGISTRY.json`. The prose below is explanatory; the registry controls if the two differ.

### H-OBS-01 — Observation-rate adequacy

**Question.** In a defined finite-bandwidth transition generator, does polling at or above the registered observation boundary reduce missed transitions and aliasing relative to sub-boundary polling?

**Null.** After controls for phase, load, jitter, and event count, observation rate has no practically relevant effect on missed-transition or aliasing error.

**Primary endpoint.** Missed-transition rate.

**Secondary endpoints.** State-reconstruction error, alias classification rate, detection latency, and gap-detection rate.

**Falsification boundary.** The QIK-VRT rate-admission policy is not empirically supported for the registered generator if the above-bound conditions fail to improve the primary endpoint by the preregistered margin or if the result disappears under phase and jitter controls.

This experiment tests a monitor contract, not a new sampling theorem.

### H-EFF-02 — Reobservation versus acknowledgement

**Question.** Does post-effect state reobservation reduce false completion claims compared with transport-acknowledgement-only classification under injected faults?

**Null.** Reobservation provides no reduction in false completion classifications.

**Primary endpoint.** False completion rate: the proportion of trials classified complete despite failure of the registered postcondition.

**Fault classes.** Dropped commit, acknowledged-but-not-applied write, delayed write, replay, stale state, backend rollback, response substitution, and observer gap.

**Falsification boundary.** The reobservation claim is rejected if its false completion rate is not lower by the registered margin or if lower error is explained solely by unequal information or additional intervention authority.

### H-CAU-03 — Causal reconstruction under clock disorder

**Question.** Do explicit predecessor bindings reconstruct an intervention-grounded causal graph more accurately than timestamp order under clock skew, variable delay, batching, and packet reordering?

**Null.** Explicit predecessor bindings do not improve causal-edge precision/recall over timestamp order when both receive the same admissible information.

**Primary endpoint.** Macro-averaged F1 score against the intervention-defined ground-truth graph.

**Falsification boundary.** The explicit-binding approach is rejected for the registered benchmark if it fails the preregistered improvement margin or if its advantage depends on information unavailable to the timestamp baseline.

### H-ORD-04 — Receive-order inversion without causal inversion

**Question.** Can two observers receive the same emissions in different orders while preserving one intervention-consistent causal graph?

**Null.** A receive-order inversion necessarily changes the reconstructed causal graph under the registered controls.

**Primary endpoint.** Graph invariance across observers despite receive-order inversion.

**Falsification boundary.** The model is rejected for the registered setting if the explicit evidence cannot preserve the intervention-defined graph without introducing hidden or post hoc edges.

This experiment is a distributed-observation test. It is not, by itself, a demonstration of physical retrocausality.

### H-PHY-05 — Incremental physical relevance of causal-order features

**Question.** In independently instrumented physical systems with controlled interventions, do causal-order features improve out-of-sample prediction of registered postconditions beyond timestamp-only features?

**Null.** Causal-order features provide no reproducible incremental predictive information beyond timestamps and the same control variables.

**Primary endpoint.** Difference in held-out log loss between a timestamp-only model and a preregistered model that adds explicit causal-order features.

**Replication requirement.** The effect must satisfy the decision rule in two apparatuses with independent acquisition paths.

**Falsification boundary.** The bridge hypothesis is rejected if the registered minimum improvement is not reached, if the confidence interval includes the equivalence region, if the result fails independent replication, or if leakage, intervention imbalance, or timestamp-derived proxies explain the difference.

Even a positive result would not prove that physical time is identical to QIK-VRT causal time. It would establish only incremental empirical relevance for the registered measurements.

---

## 5. Blocked identity claim

The following statement is deliberately not an active hypothesis:

```text
PHYSICAL_TIME == QIKVRT_CAUSAL_TIME
```

It is held because no unique operationalization currently distinguishes this identity from weaker alternatives such as:

- causal-order features are useful for prediction;
- causal partial orders are convenient representations;
- intervention graphs outperform timestamps in selected tasks;
- spacetime admits a causal-order description under an existing physical theory.

The identity claim may become eligible only after a protocol specifies:

1. a measurement that differs between the identity model and at least one serious alternative;
2. an apparatus and calibration model;
3. a preregistered rejection rule;
4. an independent replication path;
5. a treatment of relativistic frame dependence and measurement uncertainty.

Until then:

```text
HOLD_NO_OPERATIONALIZATION
```

---

## 6. Experimental architecture

The program uses four separated layers.

### Layer A — Synthetic observation benchmark

A deterministic event generator produces registered signals, transitions, pulses, and state changes with controlled `f_max`, phase, jitter, duty cycle, burst structure, and noise. This layer tests H-OBS-01 and supplies calibration data. It cannot establish a physical-law claim.

### Layer B — Fault-injected effect system

A client, transport, effect backend, and independent observer are separated. Fault injection occurs after transport acknowledgement, before application, after application, and before reobservation. This layer tests H-EFF-02.

### Layer C — Distributed causal-order benchmark

A controller creates intervention-grounded event graphs. Nodes receive events with controlled skew, delay, batching, duplication, omission, and reordering. Timestamp-only and explicit-predecessor reconstructions are evaluated with equal admissible information. This layer tests H-CAU-03 and H-ORD-04.

### Layer D — Independently instrumented physical apparatus

At least two physical apparatuses are required. Each has:

- controlled interventions;
- independent acquisition paths;
- calibrated clocks;
- raw immutable measurements;
- registered postconditions;
- blinded model evaluation;
- timestamp-only and causal-feature models with the same noncausal covariates.

This layer alone may test H-PHY-05.

---

## 7. Analysis plan

### 7.1 Separation of development and evaluation

Data used to design the generators, fault classes, or feature extraction are development data. Primary endpoints are evaluated on frozen held-out runs.

### 7.2 Equal-information comparisons

A comparison is invalid if one model receives predecessor identifiers or intervention labels and the other is denied equivalent admissible information without that asymmetry being the object of study.

### 7.3 Multiple hypotheses

Each active hypothesis has one primary endpoint. Secondary endpoints are descriptive unless separately corrected. The registry records the family and decision rule.

### 7.4 Uncertainty

Report point estimates, confidence intervals, complete trial counts, exclusions, and missingness. A later or larger point estimate is not treated as better without the registered objective.

### 7.5 Negative results

A negative result is a valid outcome. It does not authorize changing the endpoint, margin, exclusion rule, or hypothesis after observing the data. Any post hoc analysis is labeled exploratory.

---

## 8. Confounds and failure modes

The program specifically controls for:

- clock skew mistaken for causal inversion;
- observer delay mistaken for event delay;
- retransmission mistaken for a new effect;
- acknowledgement generated before durable application;
- state rollback after acknowledgement;
- hidden shared causes;
- unequal model inputs;
- timestamp leakage into causal features;
- intervention labels inferred from outcomes;
- event-driven capture gaps;
- saturation, buffering, batching, and queue collapse;
- nonstationary or unbounded transition bandwidth;
- selection of only successful trials;
- reusing the software precursor as physical evidence.

A test that cannot quantify these failure modes remains `HOLD`.

---

## 9. Reproducibility contract

Every executed experiment must bind:

```text
protocol version
hypothesis registry digest
source revision
apparatus identity
calibration receipt
raw-data digest
analysis-code digest
random seeds
inclusion/exclusion decisions
primary endpoint
decision rule
result
```

Execution, analysis, and publication remain separate effects.

A repository commit proves persistence of bytes. It does not prove that an apparatus was physically run. A workflow proves the recorded computation on its runner. It does not prove an external laboratory effect unless the laboratory state is independently observed and bound.

---

## 10. Relation to prior work

Nyquist and Shannon established foundational constraints on representing band-limited signals from samples. This program uses those constraints only where a signal class and relevant bandwidth are explicitly justified; it does not apply them indiscriminately to arbitrary event streams.

Lamport demonstrated that event order in distributed systems is naturally represented by a partial `happened-before` relation and that clock order is a separate construction. The present program adds intervention-grounded comparisons and effect reobservation.

Causal-set research explores physical models in which causal order has foundational significance. That literature supplies an adjacent physical research context, not validation of QIK-VRT. The present identity claim remains held until an experiment can distinguish it from weaker models.

---

## 11. What a successful program would and would not establish

A successful H-OBS-01 would support the registered observation policy for the defined generator.

A successful H-EFF-02 would support reobservation as a method for reducing false completion claims in the tested systems.

A successful H-CAU-03 or H-ORD-04 would support explicit causal bindings in the registered distributed benchmark.

A replicated successful H-PHY-05 would support incremental empirical relevance of causal-order features for the tested apparatuses.

None of these outcomes alone would establish:

```text
a new fundamental law of time
quantum retrocausality
physical-time identity
machine consciousness
general EFFECT_ACK_DONE
physical Atari Mega ST execution
```

---

## 12. Conclusion

The computational precursor has made a set of distinctions executable:

```text
CAUSALITY != SEQUENCE
TIMESTAMP_ORDER != CAUSAL_ORDER
ACTIVITY != EFFECT
TRANSPORT_ACK != EFFECT_ACK
LATER != BETTER
SAMPLED_ORDER != CAUSAL_ORDER
```

The next scientific obligation is not to repeat those distinctions more forcefully. It is to expose them to measurements that can reject them.

This manuscript therefore advances no completed physical result. It supplies a bounded route from software evidence to empirical risk:

```text
COMPUTATIONAL RESULT
-> OPERATIONAL DEFINITION
-> REGISTERED HYPOTHESIS
-> CONTROLLED INTERVENTION
-> INDEPENDENT OBSERVATION
-> FALSIFICATION OR SUPPORT
```

The decisive boundary is:

```text
REPOSITORY_EVIDENCE != PHYSICAL_EVIDENCE
```

That boundary is not a limitation to be hidden. It is the condition under which the research program can become science.

---

## References

1. H. Nyquist, “Certain Topics in Telegraph Transmission Theory,” *Transactions of the American Institute of Electrical Engineers*, 47(2), 617–644, 1928. DOI: `10.1109/T-AIEE.1928.5055024`.
2. C. E. Shannon, “Communication in the Presence of Noise,” *Proceedings of the IRE*, 37(1), 10–21, 1949. DOI: `10.1109/JRPROC.1949.232969`.
3. L. Lamport, “Time, Clocks, and the Ordering of Events in a Distributed System,” *Communications of the ACM*, 21(7), 558–565, 1978. DOI: `10.1145/359545.359563`.
4. L. Bombelli, J. Lee, D. Meyer, and R. D. Sorkin, “Space-Time as a Causal Set,” *Physical Review Letters*, 59, 521–524, 1987. DOI: `10.1103/PhysRevLett.59.521`.
