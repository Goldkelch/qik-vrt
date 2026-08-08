# Delayed Choice, Superdeterminism, and Authority-Mirror-Witness Recovery

This publication tranche combines three deliberately separated layers:

1. **Quantum-foundations boundary:** measurement independence conditionally excludes the defined measurement-dependent superdeterministic candidate; local/spacelike response structure alone does not establish measurement independence.
2. **General decision-sufficiency theorem:** deterministic recovery from partial observation is possible exactly when every reachable observation fiber is constant with respect to the correct action, equivalently `ker(Obs') ⊆ ker(C)`. The selector is unique only on the reachable observation image.
3. **Authority/Mirror/Witness specialization:** an independent commit witness refines the observable state so that the correct recovery action becomes fiber-constant under the stated finite fault model.

## Orientation and normative translation

The [German minimal recovery orientation](WHATSAPP_DECISION_SUFFICIENCY_DE.md)
states the decision-sufficiency theorem together with the bounded finite-model
scope. The [evidence-sufficiency imperative](../../articles/a015_evidence_sufficiency_imperative.md)
is its deliberately non-overclaiming, cross-domain normative translation. It
does not itself define a domain's correct action, prove Kantian ethics, legal
compliance, medical correctness, scientific truth, or authorize an external
effect.

## Main formal normal form

`RecoveryEquivalent h1 h2 :⇔ C(h1) = C(h2)`

`ObservationSufficient :⇔ Obs'(h1) = Obs'(h2) -> C(h1) = C(h2)`

Therefore:

- if one observation fiber mixes two different required actions, no universally correct deterministic selector can exist through that observation;
- if every reachable fiber is action-constant, `C` factors through the reachable observation image and the selector is unique there;
- a witness is decision-sufficient precisely when its refined observation kernel is contained in the correct-action kernel.

## Executed bounded verification

The finite hardware checker returned `FINITE_MODEL_EXHAUSTIVE_CHECK_PASSED` for the documented 945 / 945 / 945 / 756 / 81 / 36 / 18 case families.

## Boundaries

A successful exact-head Lean 4.19 kernel receipt for the current combined branch is not claimed until the repository runner executes and binds the proof output to the live commit/tree. Physical non-superdeterminism, SHA-256 collision resistance, arbitrary multi-fault tolerance, physical chip implementation, patent novelty, `PASS`, `FINAL_PASS`, and `EFFECT_ACK_DONE` remain outside the established scope.

Zenodo publication is candidate-only until all production gates pass. No normative Effect-ACK protocol change is introduced, therefore the IETF disposition is `NO_PROTOCOL_CHANGE_REQUIRED`.
