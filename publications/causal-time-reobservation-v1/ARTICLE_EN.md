# Causality Is Not Sequence

## A Typed Computational Model of Causal Order, Reobservation, and Evidence-Bound Improvement from Metagrammar to Motorola 68000

**Ingolf Lohmann**

### Abstract

This article presents a computational framework for preserving distinctions that are routinely collapsed in software systems and scientific reasoning: relation versus causation, temporal order versus causal order, execution versus observation, and change versus improvement. The central invariant is simple: **causality is not sequence**. A later event is not thereby caused by an earlier event; a later state is not thereby better; an executed operation is not thereby an observed or acknowledged effect.

The framework is implemented in the QIK-VRT repository as a typed path from a human-readable metagrammar through semantic validation, explicit causal binding, deterministic serialization, an ANSI-C89 implementation layer, and a Motorola 68000 machine-state projection. A repository-native reobservation probe tests the transition pattern

`PAST -> CURRENT_BOUND_STATE -> ADMISSIBLE_FUTURE -> EFFECT -> REOBSERVED_STATE`

under an explicitly bound objective. On exact source head `98d66de02e98d67af81655b028d15fbd60869bbc`, the dedicated GitHub Actions workflow executed two five-test groups successfully. The resulting witnesses distinguish an observed improvement, a later but unchanged state, and a later degraded state. The M68000 projection also verifies that an explicit causal predecessor is represented separately from decision and effect-lifecycle state.

The result is not a proof that physical time is identical to causal order, not an empirical demonstration of quantum causality, not evidence of machine consciousness, and not evidence of physical Atari Mega ST execution. It is a reproducible computational result: causal, temporal, evaluative, and evidential relations can be represented separately and propagated to machine-visible state without deriving causation from sequence or improvement from lateness. This provides a concrete basis for further work in causal computing, auditable autonomous systems, tested event-model-driven development, and experimentally falsifiable extensions toward physical hypotheses.

---

## 1. Problem

Many failures in automated reasoning arise not because a system cannot represent data, but because it silently upgrades one kind of relation into another. Typical examples are:

- event A appears before event B, therefore A is treated as the cause of B;
- a new software state exists, therefore it is treated as an improvement;
- an operation was requested, therefore it is treated as executed;
- an operation executed, therefore its intended effect is treated as observed;
- a transport acknowledgement arrived, therefore the intended real-world effect is treated as acknowledged.

These upgrades are invalid unless additional conditions are bound and evidenced.

QIK-VRT therefore treats the following as type boundaries rather than stylistic cautions:

```text
DISTINCTION != RELATION
RELATION != CAUSALITY
CAUSALITY != SEQUENCE
TIMESTAMP_ORDER != CAUSAL_ORDER
LATER != CAUSED_BY
LATER != BETTER
REQUESTED != EXECUTED
EXECUTED != OBSERVED
OBSERVED != ACKNOWLEDGED
TRANSPORT_ACK != EFFECT_ACK
ZERO_RESULT != NO_EFFECT
```

The purpose of the framework is not to eliminate interpretation. It is to make every strengthening of a claim explicit enough to inspect, test, reject, or reproduce.

---

## 2. Minimal distinction calculus

The framework begins with elementary arithmetic identities used as a symbolic distinction calculus:

```text
1 - 0 = 1
1 - 1 = 0
x = y
z = 0
```

Their role is deliberately modest.

`1 - 0 = 1` represents a preserved difference between unequal values.

`1 - 1 = 0` represents vanishing difference for equal values.

`x = y` represents a relation in a bound domain.

`z = 0` is a formal zero value.

None of these statements alone establishes physical causality, semantic identity across arbitrary contexts, authorization, or absence of real-world effect. In particular:

```text
ZERO_RESULT != NO_EFFECT
RELATION != CAUSALITY
```

The scientific value of the calculus lies not in novel arithmetic, but in using the smallest available distinction as the first type boundary in a larger computational chain.

---

## 3. Metagrammar of bound understanding

The QIK-VRT metagrammar treats an actionable statement as incomplete unless the relevant dimensions are bound. A compact representation is:

```text
MEANING =
  INTENT
+ BINDING
+ AUTHORITY
+ EVIDENCE
+ STATE
+ CAUSAL_ORDER
+ EFFECT
+ PROOF
```

This is not an additive numerical equation. It is a protocol schema: an actionable interpretation requires these dimensions to remain distinguishable.

A statement such as `perform the change` is insufficient because it leaves unresolved:

- which exact object and version are addressed;
- which state is currently observed;
- which authority permits which class of action;
- which evidence is current and attributable;
- which predecessors are causally required;
- which effect is intended;
- how the result will be reobserved;
- what evidence will justify the stronger postcondition.

When a required dimension is absent, the intended behavior is fail-closed rather than inferentially optimistic. Candidate continuations include `NOOP`, `HOLD`, `REOBSERVE`, and `REQUEST_AUTHORITY`.

---

## 4. Causal order versus serialization

A single processor executes a sequence, but an execution sequence is not automatically a causal graph.

The model therefore separates two structures:

1. **Causal partial order.** A directed edge is introduced only when the model explicitly binds a dependency, such as data dependence, non-commutative resource dependence, authority dependence, exact-state dependence, or another declared causal condition.
2. **Deterministic serialization.** Once the causal graph is known, a linear execution order may be chosen from its topological sorts for a sequential target machine.

Formally:

```text
SERIALIZATION in TOPOLOGICAL_SORTS(CAUSAL_GRAPH)
```

but not:

```text
SERIALIZATION == CAUSAL_GRAPH
```

and not:

```text
SOURCE_ORDER == CAUSAL_ORDER
WALL_CLOCK_ORDER == CAUSAL_ORDER
```

This distinction matters because two independent operations may legitimately be serialized in either order, while a true dependency constrains every valid serialization.

---

## 5. Causal time as a computational projection

Within QIK-VRT, `CAUSAL_TIME` is defined as an order or projection derived from explicitly bound causal transitions. A timestamp may annotate an observation, establish freshness windows, or support replay protection, but it does not create a causal edge.

The computational rule is:

```text
CAUSE(A,B) may constrain ORDER(A,B)
ORDER(A,B) does not imply CAUSE(A,B)
```

This gives a precise technical meaning to causal time without identifying it with fundamental physical time.

The distinction is crucial:

```text
EARLIER != CAUSE
LATER != EFFECT_OF
TIMESTAMP_ORDER != CAUSAL_ORDER
```

The framework can therefore represent a temporally later observation that is causally unrelated, as well as a causally constrained transition whose evidence is recorded using timestamps.

---

## 6. The bound-now transition model

The operational transition studied here is:

```text
PAST
-> CURRENT_BOUND_STATE
-> ADMISSIBLE_FUTURE
-> EFFECT
-> REOBSERVED_STATE
```

The terms have specific roles.

### 6.1 Past

`PAST` is not defined as every state with a lower timestamp. It is the set of predecessor information that is both relevant and bound to the current transition model.

### 6.2 Current bound state

`CURRENT_BOUND_STATE` is the state on which the decision is actually authorized and evidenced. A stale observation cannot silently substitute for the current state.

### 6.3 Admissible future

An `ADMISSIBLE_FUTURE` is not a prediction that must occur. It is a candidate next state consistent with the currently bound semantics, authority, invariants, and effect constraints.

### 6.4 Effect

An effect is a state-changing operation or other externally relevant transition whose lifecycle remains typed.

### 6.5 Reobserved state

After execution, the new state is observed again. The observation is compared with the previously bound expectation under an explicit objective.

This yields additional non-equivalences:

```text
POSSIBLE_FUTURE != PREDICTED_FUTURE
PREDICTED_FUTURE != CAUSED_FUTURE
DESIRED_FUTURE != AUTHORIZED_FUTURE
AUTHORIZED_FUTURE != OBSERVED_EFFECT
```

---

## 7. Improvement requires an objective

A central test target is the invalid inference `later -> better`.

Improvement is not a property of time. It is a relation between states under a bound evaluation rule.

For the repository probe, the objective is deliberately simple:

```text
HIGHER_QUALITY_IS_BETTER
```

This objective is not asserted to be universally valid. It is an explicit test objective that makes the classification rule inspectable.

The system therefore distinguishes:

```text
UNCHANGED
CHANGED
IMPROVEMENT_EVIDENCED
CHANGED_DEGRADED
```

and enforces:

```text
REPETITION != LEARNING
CHANGE != IMPROVEMENT
LATER != BETTER
MORE_ITERATIONS != MORE_UNDERSTANDING
```

A stronger interpretation such as learning or progress requires a separately declared evaluation relation and evidence that the observed post-state satisfies it.

---

## 8. Motorola 68000 projection

The computational model is lowered to a small Motorola 68000 decision representation. The existing decision ABI preserves four nonproductive continuations in register `D0`:

```text
D0 = 0  NOOP
D0 = 1  HOLD
D0 = 2  REOBSERVE
D0 = 3  REQUEST_AUTHORITY
```

A semantic witness profile extends the representation without changing the four-action decision ABI:

```text
D1 = semantic witness flags
D2 = effect lifecycle
D3 = explicit causal-predecessor witness
```

For the causal witness:

```text
D3 = 0  NO_EXPLICIT_PREDECESSOR_BOUND
D3 = 1  EXPLICIT_PREDECESSOR_BOUND
```

`D3` is intentionally not a timestamp, duration, success score, quality score, authority token, or proof of physical causality. It states only whether the validated plan carries an explicit causal predecessor.

For bound authority, an observed effect state, explicit predecessor `r0`, and the decision `REOBSERVE`, the expected machine representation is:

```text
MOVEQ #15,D1
MOVEQ #3,D2
MOVEQ #1,D3
MOVEQ #2,D0
RTS
```

with exact big-endian bytes:

```text
72 0F 74 03 76 01 70 02 4E 75
```

The important result is not the size of this instruction sequence. It is that a high-level causal type boundary survives lowering into machine-visible state.

---

## 9. Repository-native experiment

The experiment was executed as a dedicated repository workflow against exact source head:

```text
98d66de02e98d67af81655b028d15fbd60869bbc
```

Workflow:

```text
QIKVRT causal transition reobservation probe
```

Run ID:

```text
32530018373
```

Job ID:

```text
96920011647
```

The workflow completed successfully after executing two independent five-test groups:

```text
causal_transition_probe          5/5 OK
causal_time_m68000_projection    5/5 OK
```

The repository evidence is permanently bound in:

```text
evidence/receipts/causal-transition-probe-pr796-local-reproduction.json
```

The receipt records the executed source head, workflow identity, machine contract, positive and negative witnesses, and explicit epistemic boundaries.

---

## 10. Three reobservation witnesses

### 10.1 Evidence-bound improvement

Test values:

```text
past quality      = 1
current quality   = 1
expected quality  = 2
observed quality  = 2
```

Observed classification:

```text
IMPROVEMENT_EVIDENCED
```

Properties:

```text
later                     = true
changed                   = true
expected_equals_observed  = true
improved                  = true
later_implies_better      = false
```

The last property is intentional. The state is classified as improved because of the bound objective and observed value, not because it is later.

### 10.2 Later without improvement

Test values:

```text
current quality   = 1
expected quality  = 2
observed quality  = 1
```

Observed classification:

```text
UNCHANGED
```

Properties:

```text
later                     = true
changed                   = false
expected_equals_observed  = false
improved                  = false
later_implies_better      = false
```

This is the direct counterexample to `later -> better`.

### 10.3 Later and degraded

Test values:

```text
current quality   = 1
expected quality  = 2
observed quality  = 0
```

Observed classification:

```text
CHANGED_DEGRADED
```

Properties:

```text
later                     = true
changed                   = true
expected_equals_observed  = false
improved                  = false
degraded                  = true
later_implies_better      = false
```

This shows that temporal continuation is compatible with degradation.

---

## 11. Negative fail-closed cases

The experiment also binds negative cases:

```text
CAUSE_NOT_BOUND -> HOLD
OBJECTIVE_NOT_BOUND -> HOLD
missing CAUSE in M68000 causal-time-v3 plan -> no executable IR
```

These cases are essential because a positive example alone cannot establish that the implementation refuses unsupported strengthening.

The negative cases demonstrate the intended discipline:

- no cause binding, no causal claim;
- no objective, no improvement claim;
- no complete causal witness, no causal-time-v3 executable intermediate representation.

---

## 12. A discovered harness defect and why it matters

The first repository execution did not complete successfully. The causal-transition tests themselves executed `5/5 OK`, but the subsequent M68000 test group failed because a Python test-harness attribute and method both used the name `lower`.

The resulting error was:

```text
TypeError: 'PosixPath' object is not callable
```

This defect was isolated as a harness defect rather than misclassified as a failure of the causal model. The executable-path attributes were renamed to `lower_bin` and `emit_bin`, and the method was renamed to `run_lower`. The complete workflow was then rerun, and both five-test groups completed successfully.

This episode illustrates the framework's central methodological requirement:

```text
SEQUENCE != CAUSALITY
FAILURE_AFTER_X != FAILURE_CAUSED_BY_X
```

A failure that occurs after a successful semantic test is not automatically evidence against that semantic test. The actual failing dependency must be identified.

---

## 13. From repository evidence to scientific claims

The framework distinguishes at least four evidence classes.

### 13.1 Formal result

A formal result is a statement proved or mechanically verified inside a specified formal model. The present article does not claim a new theorem of fundamental physics from the repository test.

### 13.2 Repository evidence

Repository evidence establishes facts about exact source states, implementations, workflow executions, test outputs, machine-byte expectations, and persisted receipts.

The successful exact-head workflow is repository evidence.

### 13.3 Philosophical interpretation

The interpretation that time can be understood as an order or distance associated with transitions between causally bound and non-causally related states is a philosophical and conceptual extension of the computational model.

It is not silently promoted to physics.

### 13.4 Empirical physics

An empirical physical theory requires a physical state model, operational observables, measurement procedures, predictions that differ from alternatives, and experiments capable of falsifying those predictions.

The current repository experiment does not supply these elements for fundamental physical time or quantum causality.

---

## 14. Relation to causal inference

The core distinction `temporal precedence != causation` is consistent with modern causal inference. Causal conclusions require assumptions or evidence beyond observational ordering alone. Depending on the domain, causal support may come from intervention, randomized assignment, mechanistic constraints, structural causal models, conditional independences, natural experiments, or other identification strategies.

QIK-VRT contributes at a different layer: it treats the evidence type and causal-binding obligation as part of the executable decision representation. Instead of leaving the distinction solely to external analysis, the system is designed to fail closed when a required causal or evaluative binding is absent.

This makes the framework relevant to autonomous software where unsupported causal upgrades can themselves trigger effects.

---

## 15. Tested Event Model Driven Development

The implementation fits a development discipline referred to here as **Tested Event Model Driven Development (TEMDD)**.

The essential cycle is:

```text
MODEL EVENT
-> BIND PRECONDITIONS
-> EXECUTE OR HOLD
-> OBSERVE RESULT
-> COMPARE WITH EXPECTATION
-> UPDATE EVIDENCE
-> REVISE MODEL OR CONTINUE
```

TEMDD differs from a simple test-after-implementation workflow because event causality, authority, expected effect, and observation are first-class model elements.

The method therefore supports a reflexive development loop:

```text
DISTINCTION_n
-> RELATION_n
-> CAUSAL_BINDING_n
-> DECISION_n
-> EFFECT_n
-> REOBSERVATION_n+1
-> DISTINCTION_n+1
```

But the loop itself does not imply learning or progress. Those stronger claims require explicit criteria.

---

## 16. Artificial cognition and responsibility

The framework can support systems that inspect their own evidence state, request additional authority, reobserve a changed environment, and refuse actions whose preconditions are not satisfied.

This provides a technically meaningful sense of reflexive cognition:

- represent what is currently known;
- distinguish unknown from false;
- bind a causal predecessor when one is required;
- select only admissible next actions;
- observe the resulting state;
- compare observation with expectation;
- retain disagreement rather than overwrite it.

None of these properties proves subjective experience.

Accordingly:

```text
REFLEXIVITY != SELF-CONSCIOUSNESS
LEARNING != CONSCIOUSNESS
MACHINE_STATE != SUBJECTIVE_EXPERIENCE
```

A philosophical interpretation in terms of the evolution of cognition or consciousness can be investigated, but it remains distinct from an empirical consciousness claim.

---

## 17. What the experiment establishes

The exact-head execution supports the following bounded claims:

1. A causal predecessor can be represented separately from decision state and effect lifecycle.
2. A temporal or logical ordering field is not required to manufacture a causal witness.
3. A later state can be experimentally classified as improved, unchanged, or degraded under an explicit evaluation objective.
4. Improvement can be withheld when the objective is absent.
5. Causal continuation can be withheld when the cause binding is absent.
6. The M68000 lowering preserves the separation into machine-visible registers and exact bytes.
7. The implementation can detect and survive a distinct test-harness defect without reclassifying it as a semantic counterexample.

These are computational and repository-grounded results.

---

## 18. What the experiment does not establish

The experiment does **not** establish:

```text
physical time == QIKVRT_CAUSAL_TIME
empirical quantum causality confirmed
all temporal order is causal order
all causal order is physically fundamental time
machine consciousness proven
biological evolution reduced to this model
human history reduced to this model
physical Atari Mega ST execution observed
universal compiler completed
independent scientific review completed
publication accepted
PASS
FINAL_PASS
EFFECT_ACK_DONE
```

These exclusions are part of the result rather than caveats added after the fact. The framework is specifically designed to preserve such boundaries.

---

## 19. Scientific hypotheses enabled by the computational result

The repository result makes several next-step hypotheses precise enough to investigate.

### H1. Causal-order-aware execution systems reduce unsupported effect claims

Systems that represent causal prerequisites explicitly should produce fewer false effect acknowledgements than systems that infer progress from sequence or workflow completion alone.

This can be tested experimentally in distributed systems and autonomous software.

### H2. Explicit reobservation reduces stale-state action errors

Systems that require a fresh post-effect observation before upgrading `EXECUTED` to `OBSERVED` or `ACKNOWLEDGED` should be more robust to partial failure and asynchronous execution.

This can be measured in fault-injection experiments.

### H3. Objective-bound improvement claims are more reproducible

Systems that require an explicit objective before emitting improvement claims should exhibit lower rates of retrospective metric substitution.

This can be evaluated in software optimization and machine-learning pipelines.

### H4. A causal-time representation can be compared with physical causal structures

A physical extension would require a mapping from physical events and observables into the model's causal bindings. Competing mappings would need to yield different measurable predictions. Only then could the computational notion of causal time be tested as a candidate physical description.

This is a research program, not a current empirical result.

---

## 20. Toward a falsifiable physical extension

To move from computational causal time to physical science, at least the following must be specified independently:

1. **Physical event domain.** What counts as an event?
2. **Observable state.** Which quantities are measured?
3. **Causal relation.** How is a physical causal edge operationally identified?
4. **Temporal observable.** Which measurement is compared with the causal-order construction?
5. **Competing hypothesis.** What alternative model predicts something different?
6. **Experimental protocol.** Which intervention or observation can discriminate between the models?
7. **Error model.** How are uncertainty and measurement error represented?
8. **Falsification condition.** Which outcome would count against the proposed mapping?

Without these elements, identifying causal order with fundamental physical time would be interpretation rather than empirical physics.

The computational framework is useful precisely because it makes this missing bridge explicit.

---

## 21. Broader interpretation

The same structural distinction can be discussed at progressively larger scales:

```text
BIT / DISTINCTION
-> RELATION
-> SEMANTIC BINDING
-> CAUSAL EDGE
-> PARTIAL ORDER
-> STATE TRANSITION
-> MACHINE STATE
-> EXECUTION
-> OBSERVATION
-> EFFECT ACKNOWLEDGEMENT
-> REPOSITORY EVIDENCE
-> MESH COORDINATION
-> SCIENTIFIC INTERPRETATION
```

The important rule at every boundary is:

```text
LAYER_TRANSITION != AUTOMATIC_TRUTH_UPGRADE
```

A machine register does not become physical causality because it is executable. A repository workflow does not become scientific consensus because it succeeds. A philosophical interpretation does not become empirical physics because it is coherent.

Conversely, these layers need not be isolated. They can be connected by explicit bridge contracts that state what is preserved, what is added, and what is not implied.

That is the general methodological proposal of this work.

---

## 22. Discussion

The practical contribution is a small but complete vertical slice. It begins with typed distinctions in a metagrammar and ends with deterministic Motorola 68000 bytes plus repository-native reobservation evidence.

The implementation is intentionally modest at machine level. This is advantageous for auditability. A four-action decision ABI plus semantic, lifecycle, and causal witness registers is small enough to inspect manually while still demonstrating that the semantic distinctions survive lowering.

The reobservation experiment adds a second important result: the system does not equate later states with improvements. A later state can be unchanged or degraded. This sounds obvious in natural language, but software pipelines routinely encode the opposite assumption implicitly through version numbers, monotonic workflow stages, optimization histories, or success flags.

Making the distinction executable turns an epistemological caution into a systems property.

---

## 23. Conclusion

The central result can be stated without metaphysical inflation:

> **A responsible computational system can preserve the distinction between sequence and causality, and between temporal continuation and evaluated improvement, from human-readable semantics down to machine-visible state and back up through reobservation and repository evidence.**

The exact repository experiment demonstrates that:

```text
LATER != BETTER
CHANGE != IMPROVEMENT
SEQUENCE != CAUSALITY
TIMESTAMP_ORDER != CAUSAL_ORDER
```

while still permitting the stronger classifications `IMPROVEMENT_EVIDENCED` or `CHANGED_DEGRADED` when the required objective and observations are bound.

The larger scientific opportunity is not to declare that this computational structure already explains physical time, quantum causality, life, or consciousness. It is to use the structure to formulate those larger questions without erasing the boundaries between formal result, executable implementation, repository evidence, philosophical interpretation, and empirical physics.

That is the methodological claim:

**Preserve the difference. Bind the relation. Establish the cause. Observe the effect. Upgrade the claim only when the evidence allows it.**

---

## Repository evidence binding

Repository: `Goldkelch/qik-vrt`

Primary causal-time work: PR `#796`

Successful executed source head:

`98d66de02e98d67af81655b028d15fbd60869bbc`

Workflow: `QIKVRT causal transition reobservation probe`

Run: `32530018373`

Job: `96920011647`

Evidence receipt:

`evidence/receipts/causal-transition-probe-pr796-local-reproduction.json`

Document publication branch base observed before this article:

`9276ae231221c55c0898d95b3c2f427218b06aca`

---

## References

1. Pearl, J. *Causality: Models, Reasoning, and Inference*. Cambridge University Press, 2nd ed., 2009.
2. Pearl, J., Glymour, M., Jewell, N. P. *Causal Inference in Statistics: A Primer*. Wiley, 2016.
3. Spirtes, P., Glymour, C., Scheines, R. *Causation, Prediction, and Search*. MIT Press, 2nd ed., 2000.
4. Lamport, L. “Time, Clocks, and the Ordering of Events in a Distributed System.” *Communications of the ACM* 21(7), 1978, 558–565.
5. Mattern, F. “Virtual Time and Global States of Distributed Systems.” In *Parallel and Distributed Algorithms*, 1989.
6. Bombelli, L., Lee, J., Meyer, D., Sorkin, R. D. “Space-Time as a Causal Set.” *Physical Review Letters* 59, 1987, 521–524.
7. Oreshkov, O., Costa, F., Brukner, C. “Quantum correlations with no causal order.” *Nature Communications* 3, 2012, 1092.
8. ISO/IEC 9899:1990. *Programming Languages — C* (ANSI C89 / ISO C90 lineage).
9. Motorola. *M68000 Family Programmer's Reference Manual*.

---

**Author's interpretive note.** The phrases “metagrammar of universal understanding,” “causal time,” and related philosophical formulations denote the conceptual framework developed in QIK-VRT. Their use in this article does not claim universal empirical completeness. Universal applicability is treated as a structural research objective: the same type distinctions should remain expressible across domains without converting domain-specific evidence into domain-independent truth.
