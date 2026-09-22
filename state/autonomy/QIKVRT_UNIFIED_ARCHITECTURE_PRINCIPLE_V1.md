# QIK-VRT Unified Architecture Principle

Authority statement: Ingolf Lohmann
Status: architecture thesis; evidence claims remain bounded by their individual receipts.

## Unification

Haltepunktdefinition, TEMDD, Effect Acknowledgment, Metatransistor and artificial cognition are roles of one architecture principle:

INTENTION
  -> EVENT / Auftrag
  -> COGNITIVE PROCESS
  -> ACTION
  -> CARRIER
  -> REAL EFFECT
  -> OBSERVATION
  -> INVARIANT
  -> { UNKNOWN / CONTINUE | EFFECT_ACK / HALT }

The action and its carrier are not the effect. A transport acknowledgement is not an effect acknowledgement.

## Halt invariant

HALT iff the required postcondition is freshly observed, subject-bound, provenance-bound, and satisfies the declared invariant within the evidence scope.

Otherwise:
  UNKNOWN => CONTINUE

CONTINUE does not mean blind retry. It means: observe the remaining causal deviation, create/bind the next admissible work unit, select an admissible carrier, act, observe the effect, and verify again.

## Five roles

- Haltepunktdefinition: defines when computation is permitted to terminate.
- TEMDD: represents and tests state change as provenance-bound events.
- Effect Acknowledgment: binds an action to freshly observed effect and prevents TRANSPORT_ACK => SUCCESS.
- Metatransistor: the universal switching abstraction for an evidence-bound state transition; hardware realization claims require their own evidence.
- Artificial cognition: recursively applies the same transition semantics to perception, reasoning, action, observation and correction.

## Common semantic kernel

QIK-VRT := recursive, evidence-bound state transitions until verified effect.

The unification is an architecture thesis. Claims of novelty, universality, superiority, physical realization, deployment, publication, or legal effect require separate evidence and MUST NOT be inferred merely from this document.

CLAIM_SCOPE <= EVIDENCE_SCOPE
UNKNOWN => FAIL_CLOSED
PREDECESSOR_EVIDENCE_TRANSFER = FALSE
TRANSPORT_ACK != EFFECT_ACK

q.e.d.
Ingolf Lohmann
