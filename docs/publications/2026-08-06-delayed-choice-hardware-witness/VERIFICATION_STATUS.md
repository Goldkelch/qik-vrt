# Verification status

## Executed finite model

`verify_authority_mirror_nvm_finite.py` was executed in the current runtime and returned:

`FINITE_MODEL_EXHAUSTIVE_CHECK_PASSED`

with counts 945 / 945 / 945 / 756 / 81 / 36 / 18 for the documented case families.

## General decision-sufficiency theorem

The formal recovery criterion is now expressed generally as observation-kernel refinement of the correct-action kernel:

`Obs'(h1) = Obs'(h2) -> C(h1) = C(h2)`.

Equivalently, `C` factors through the reachable observation image. If one observation fiber contains two admissible histories requiring different actions, no universally correct deterministic selector can factor through that observation. Authority/Mirror/Witness is treated as a specialization in which the witness refines the observable state until the correct action is constant on every reachable fiber.

## Lean

The Lean sources and axiom-audit files are materialized. The repository exact-head workflow is the required execution path. A successful execution-bound Lean 4.19 kernel receipt for the current combined head has not yet been observed.

Therefore:

- `LEAN_SOURCE_MATERIALIZED = true`
- `LEAN_KERNEL_EXECUTION = NOT_ESTABLISHED`
- `EXACT_HEAD_KERNEL_RECEIPT = ABSENT`

## Publication

Zenodo production is fail-closed until final exact-byte artifacts, machine-proof/kernel receipts, authorization/credential gates, and post-effect verification are present.

The formalization introduces no normative Effect-ACK protocol delta, so the IETF disposition is `NO_PROTOCOL_CHANGE_REQUIRED`.
