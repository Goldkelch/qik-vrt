# QIK-VRT manuscript formalization v2.0

Copyright 2026 Ingolf Lohmann. Non-source documentation: CC BY-NC-ND 4.0.

**Status: formal-environment coverage complete with explicit epistemic and conditional boundaries.**

This directory is the theorem-by-theorem reconstruction of the locked 62-page manuscript **Mandelbrot, Anschlussordnung, Physik und Retrokausalität**. The formalization is attached to the exact TeX and PDF bytes published under DOI `10.5281/zenodo.21482023`; it does not silently rewrite the manuscript.

## Locked source

- TeX SHA-256: `c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf`
- PDF SHA-256: `b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f`
- Physical PDF pages: 62

## Current verified coverage

The generated claim graph and proof map record:

- 40 / 40 formal LaTeX environments inventoried;
- 20 / 20 definitions source-bound and kernel-checked;
- 20 / 20 theorem-like environments formally closed;
- 17 / 17 explicit manuscript proof blocks attached;
- 34 / 34 appendix matrix rows epistemically classified;
- 42 strong source-bound Lean bindings;
- six conditional bindings whose additional premises are explicit in their Lean types;
- zero pending formal definition, theorem or conditional nodes.

`KERNEL_CHECKED` denotes a direct source-bound Lean proposition. `CONDITIONAL_CHECKED` denotes a kernel proof under assumptions that remain explicit in the Lean type. It is not an unconditional theorem about physical reality.

The authoritative generated projections are:

- `claims/TEX_ENVIRONMENTS.json`
- `claims/APPENDIX_MATRIX.json`
- `claims/CLAIM_GRAPH.json`
- `MANUSCRIPT_PROOF_MAP.md`
- `VERIFICATION_REPORT.md`
- `proofs/PROOF_OBJECT_MANIFEST.json`

The repository-wide completion projection is generated separately as:

- `../../GLOBAL_CLAIM_INVENTORY.json`
- `../../GLOBAL_TRACEABILITY.json`
- `../../GLOBAL_KERNEL_RECEIPTS.json`
- `../../GLOBAL_COMPLETION_RECEIPT.json`

## Epistemic boundary

Formal completion means that every registered formal manuscript environment has a source-bound machine-checkable disposition. It does not convert empirical, interpretive, metaphysical, spiritual, retrocausal, quantum-gravitational or normative statements into mathematical theorems. Such statements are retained as evidence-bound classifications, interpretations, normative premises, open boundaries or out-of-scope content.

The global inventory therefore distinguishes exactly:

`KERNEL_PROVED`, `KERNEL_PROVED_CONDITIONAL`, `EMPIRICAL_EVIDENCE_BOUND`, `INTERPRETIVE`, `NORMATIVE`, `OPEN`, and `OUT_OF_SCOPE`.

An explicit `OPEN` disposition is a terminally recorded boundary, not a proof and not a `FINAL_PASS`.

## Reproducible checks

```sh
python3 scripts/verify_source_lock.py
python3 scripts/materialize_completion.py --check
python3 scripts/render_completion_proof_map.py --check
python3 scripts/render_completion_verification_report.py --check
python3 scripts/validate_completion_claim_graph.py
python3 scripts/validate_effect_ack_claims.py
python3 -m unittest discover -s tests -v
lake build
python3 scripts/audit_lean_axioms.py
python3 scripts/audit_completion_axioms.py
python3 scripts/audit_proof_escapes.py
python3 scripts/materialize_completion_proof_manifest.py --check
python3 scripts/verify_proof_object_manifest.py
python3 ../../tools/qikvrt_global_completion.py check
```

Lean is pinned by `lean-toolchain`. Cache reuse may accelerate a build but may not replace kernel verification. CI rejects stale source hashes, missing source environments, dependency cycles, forbidden epistemic promotions, project axioms, `sorry`, `admit`, unchecked constants and stale generated evidence.

## Completion claim boundary

The strongest current manuscript statement is:

```text
LOCKED_62_PAGE_MANUSCRIPT_FORMAL_ENVIRONMENT_COVERAGE_COMPLETE
ALL_KERNEL_ELIGIBLE_MANUSCRIPT_ENVIRONMENTS_CHECKED
CONDITIONAL_ASSUMPTIONS_EXPLICIT
```

This directory alone does not establish an unqualified repository-wide `PASS`, `FINAL_PASS`, timeless `EFFECT_ACK_DONE`, empirical truth or fully kernel-verified overall completion.
