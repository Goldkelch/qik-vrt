# TEMDD

Tested Event Model Driven Development is specified here as an executable QIK-VRT metaprogramming language.

Entry points:
- `TEMDD_LANGUAGE_SPEC_V0_1.md` — normative bootstrap semantics.
- `TEMDD_Syntax_V0_1.ebnf` — grammar.
- `TEMDD_TECHNICAL_EVOLUTION_DECLARATION_V1.md` — human-readable authorship, priority and technical-evolution declaration by Ingolf Lohmann.
- `TEMDD_TECHNICAL_EVOLUTION_DECLARATION_V1.json` — machine-readable form of that declaration and its evidence boundary.
- `../../schemas/temdd-ir-v0.1.schema.json` — canonical IR contract.
- `../../tools/qikvrt_temdd.py` — deterministic reference parser/elaborator.
- `../../tools/qikvrt_temdd_conformance.py` — executable T01-T12 semantic checks.
- `../../tests/temdd/` — positive and fail-closed negative corpus.
- `../../runtime/temdd/TEMDDRuntime.st` — Smalltalk live-object backend bootstrap.
- `../../src/temdd_core.c` — C90 deterministic backend.
- `../../runtime/m68000/temdd_transition.s` — fixed-relation M68000 backend bootstrap.
- `../../formalization/TEMDDCore.lean` — formal semantic obligations.
- `../../examples/temdd/qikvrt_convergence_v0_1.temdd` — first dogfood production program.

Language evolution is itself TEMDD: mutation creates a new exact subject; predecessor validation does not transfer; the successor must pass fresh conformance and deployment readback.
