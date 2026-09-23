# TEMDD

Canonical runtime declaration:

- [TEMDD — ausführbare Sprache und Effect-Verification-Laufzeit](spec/temdd/TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md)
- [TEMDD specification entrypoint](spec/temdd/README.md)
- [Machine-readable runtime policy](policy/QIKVRT_TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.json)
- [Publication bundle](docs/publications/2026-09-23-temdd-executable-language-runtime/README.md)

Canonical Product-Owner declaration:

> Ich habe aus Tested Event Model Driven Development nicht nur eine Entwicklungsmethode gemacht, sondern eine ausführbare Sprache mit Entwicklungs-, Debugging-, Test-, Linking- und Effect-Verification-Laufzeit.
>
> q.e.d.  
> Ingolf Lohmann

Runtime completion remains evidence-bound:

`COMPILE → BIND → RESOLVE → EXECUTE → TEST → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE`

## Atomare Haltebedingung

Die Laufzeitkette ist keine inkrementell abschließbare Checkliste. Der
terminale Zustand wird als **ein Akzeptanzurteil über genau einen gebundenen
tatsächlichen Successor** ausgewertet:

```text
HALT_TEMDD
⇔ EFFECT_ACK_DONE(actual_successor, fresh_independent_readback, acceptance_scope)
```

`atomic` bezeichnet die Unteilbarkeit dieses Urteils, nicht ACID-, Speicher-
oder CPU-Atomarität. Einzelne erfolgreiche Tests, Workflows, Transporte oder
Artefakterzeugungen sind keine Ersatzbeweise. Ist die Konjunktion nicht
erfüllt, wird der bindbare tatsächliche Folgezustand zum nächsten Subject;
andernfalls gilt fail-closed BLOCK/ISOLATE.

Ein öffentlicher Artefakt-Readback ist nur dann Teil der Konjunktion, wenn der
konkrete Acceptance-Scope einen öffentlichen Artefaktzustand verlangt. Die
Semantik löst nicht das allgemeine Halteproblem.

Die vollständige Definition und wissenschaftliche Einordnung stehen in
[der kanonischen TEMDD-Laufzeitspezifikation](spec/temdd/TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md).

