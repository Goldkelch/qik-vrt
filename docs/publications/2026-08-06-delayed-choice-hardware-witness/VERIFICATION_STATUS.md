# Verification status

## Executed now

`verify_authority_mirror_nvm_finite.py` was executed in the current runtime and returned:

`FINITE_MODEL_EXHAUSTIVE_CHECK_PASSED`

with counts 945 / 945 / 945 / 756 / 81 / 36 / 18 for the documented case families.

## Lean

The Lean sources and axiom-audit files are materialized. This runtime does not contain Lean/`lake`, and outbound network access from the code container is unavailable, so an independent local Lean 4.19 execution could not be performed here. The repository exact-head workflow is the required execution path.

Therefore:

- `LEAN_SOURCE_MATERIALIZED = true`
- `LEAN_KERNEL_EXECUTION = NOT_ESTABLISHED`
- `EXACT_HEAD_KERNEL_RECEIPT = ABSENT`

## Publication

Zenodo production is fail-closed until final exact-byte artifacts, machine-proof/kernel receipts, authorization/credential gates, and post-effect verification are present.

The formalization introduces no normative Effect-ACK protocol delta, so the IETF disposition is `NO_PROTOCOL_CHANGE_REQUIRED`.
