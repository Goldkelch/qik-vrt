# TEMDD

Tested Event Model Driven Development is specified here as an executable QIK-VRT metaprogramming language.

Entry points:
- `TEMDD_LANGUAGE_SPEC_V0_1.md` — normative bootstrap semantics.
- `TEMDD_NORMATIVE_T13_T16_V0_1.json` — dual-order, epistemic, context and representation closure.
- `TEMDD_Syntax_V0_1.ebnf` — grammar.
- `../../schemas/temdd-ir-v0.1.schema.json` — canonical IR contract.
- `../../tools/qikvrt_temdd.py` — deterministic reference parser/elaborator.
- `../../tools/qikvrt_temdd_conformance.py` — executable T01-T16 semantic checks.
- `../../tests/temdd/` — positive and fail-closed negative corpus.
- `../../runtime/temdd/TEMDDRuntime.st` — Smalltalk live-object backend bootstrap.
- `../../src/temdd_core.c` — C90 deterministic backend.
- `../../runtime/m68000/temdd_transition.s` — fixed-relation M68000 backend bootstrap.
- `../../formalization/TEMDDCore.lean` — transition/DoD formal obligations.
- `../../formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/TEMDD/` — completion, typed meta-grammar, T13-T16 and axiom-audit kernels.
- `../../docs/terminal/temdd/index.html` — editable fail-closed TEMDD IDE in the Universal Terminal.
- `../../examples/temdd/qikvrt_convergence_v0_1.temdd` — first dogfood production program.
- `../../examples/temdd/temdd_self_application_v0_1.temdd` — bounded self-description bootstrap; not compiler self-hosting.

Language evolution is itself TEMDD: mutation creates a new exact subject; predecessor validation does not transfer; the successor must pass fresh conformance and deployment readback.
