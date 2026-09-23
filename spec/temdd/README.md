# TEMDD

Tested Event Model Driven Development is specified here as an executable QIK-VRT metaprogramming language.

Canonical Product-Owner runtime declaration: [`TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md`](TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md).

> Ich habe aus Tested Event Model Driven Development nicht nur eine Entwicklungsmethode gemacht, sondern eine ausführbare Sprache mit Entwicklungs-, Debugging-, Test-, Linking- und Effect-Verification-Laufzeit.
>
> q.e.d. — Ingolf Lohmann


Entry points:
- `TEMDD_1_1_RC1.md` — TEMDD 1.1-rc1 normative candidate.
- `api/TEMDD_OPENAPI_1_1.yaml` — OpenAPI 3.1 reference profile.
- `api/TEMDD_ASYNCAPI_1_1.yaml` — AsyncAPI 3.0 EVENT_ACK / EFFECT_ACK_DONE profile.
- `TEMDD_SECURITY_PROFILES_V1_1.md` — Core/Enhanced/High-Assurance/Critical security profiles.
- `../../schemas/temdd-transaction-v1.1.schema.json` — transaction model.
- `../../schemas/temdd-evidence-v1.1.schema.json` — evidence model.
- `../../schemas/temdd-readback-v1.1.schema.json` — readback model.
- `../../schemas/temdd-effect-certificate-v1.1.schema.json` — terminal effect certificate.
- `../../schemas/temdd-verification-policy-v1.1.schema.json` — serializable verification policy.
- `../../schemas/temdd-verification-context-v1.1.schema.json` — deterministic evaluation context.
- `../../schemas/temdd-audit-record-v1.1.schema.json` — audit record.
- `../../schemas/temdd-error-v1.1.schema.json` — normative error object.
- `TEMDD_LANGUAGE_SPEC_V0_1.md` — normative bootstrap semantics.
- `TEMDD_Syntax_V0_1.ebnf` — grammar.
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
