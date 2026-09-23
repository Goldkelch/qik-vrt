<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# TEMDD — ausführbare Sprache und Effect-Verification-Laufzeit

**Autor:** Ingolf Lohmann  
**Datum:** 2026-09-23  
**Status:** kanonische Product-Owner-Erklärung und Architekturvertrag für QIK-VRT/TEMDD  
**Begriff:** TEMDD = Tested Event Model Driven Development

## Kanonische Erklärung

> Ich habe aus Tested Event Model Driven Development nicht nur eine Entwicklungsmethode gemacht, sondern eine ausführbare Sprache mit Entwicklungs-, Debugging-, Test-, Linking- und Effect-Verification-Laufzeit.
>
> q.e.d.  
> Ingolf Lohmann

## Architektonische Bedeutung

TEMDD wird in QIK-VRT nicht nur als Vorgehensmodell verstanden, sondern als ausführbare Sprache mit einer integrierten Entwicklungs- und Verifikationslaufzeit. Die Sprache verbindet Modellierung, Übersetzung, Bindung, Ausführung, Beobachtung, Test und Wirkungsnachweis in einer durchgängigen Semantik.

Die kanonische Laufzeitkette lautet:

```text
COMPILE
→ BIND
→ RESOLVE
→ EXECUTE
→ TEST
→ OBSERVE
→ READBACK
→ ACCEPT
→ EFFECT_ACK_DONE
```

Die Werkzeugprojektion umfasst mindestens:

```text
Model / Source
→ Compiler
→ Linker / Binder
→ Dynamic Loader / Resolver
→ Runtime
→ Debugger / Observer
→ Test Runner
→ Effect Verifier
→ IDE
```

Dabei gilt ausdrücklich:

```text
EXECUTE ≠ DONE
TEST    ≠ DONE
OBSERVE ≠ DONE

EFFECT_ACK_DONE
⇔ COMPILE
 ∧ BIND
 ∧ RESOLVE
 ∧ EXECUTE
 ∧ TEST
 ∧ OBSERVE
 ∧ READBACK
 ∧ ACCEPT
```

`EFFECT_ACK_DONE` ist damit kein Erfolgscode eines Einzelschritts, sondern der evidenzgebundene Haltepunkt der vollständigen Ausführung.

## Atomare Effect-Akzeptanz und evidenzgebundene Haltebedingung

TEMDD behandelt den Abschluss nicht als Liste unabhängig erreichbarer Erfolgsmarker,
sondern als **eine Akzeptanzentscheidung über genau einen gebundenen tatsächlichen
Folgezustand**. `atomic` bezeichnet hier die Unteilbarkeit des
Akzeptanzurteils; es behauptet **keine** CPU-, Speicher-, Datenbank- oder
ACID-Atomarität der zugrunde liegenden Ausführung.

Sei `Σ` der Zustandsraum und

```text
s_n --EXECUTE(input_n)--> s_(n+1)^actual
```

der tatsächlich eingetretene Folgezustand. Danach wird nicht die Intention,
sondern dieser tatsächliche Successor gebunden:

```text
b_(n+1) := BIND(
    s_(n+1)^actual,
    subject_identity,
    provenance,
    artifact_identity,
    execution_identity
)
```

Die Akzeptanzevidenz wird erst nach dem Effekt und gegen denselben gebundenen
Successor erzeugt:

```text
e_(n+1) := READBACK_fresh,independent(b_(n+1))
```

`fresh` bedeutet: nach dem zu prüfenden Effekt erhoben und gegen dessen
Identität/Version gebunden. `independent` bedeutet mindestens, dass die
Akzeptanz nicht allein aus dem Erfolgsrückgabewert des Executors abgeleitet
wird; die konkrete Unabhängigkeitsklasse des Beobachtungspfads muss
dokumentierbar sein.

Für einen expliziten Acceptance-Scope `C_scope` gilt:

```text
ACCEPTED(b, e, C_scope)
    := ∧ { p(b, e) | p ∈ C_scope }

EFFECT_ACK_DONE(b, e, C_scope)
    := ACCEPTED(b, e, C_scope)

HALT_TEMDD
    ⇔ EFFECT_ACK_DONE(b_(n+1), e_(n+1), C_scope)
```

Damit gilt insbesondere:

```text
EXECUTION_OCCURRED        ≠ EFFECT_ACK_DONE
TESTS_PASSED              ≠ EFFECT_ACK_DONE
WORKFLOW_SUCCESS          ≠ EFFECT_ACK_DONE
ARTIFACT_CREATED          ≠ EFFECT_ACK_DONE
PUBLICATION_ATTEMPTED     ≠ EFFECT_ACK_DONE
PREDECESSOR_EVIDENCE      ≠ EFFECT_ACK_DONE
```

Die Konjunktion wird semantisch als **ein Urteil** ausgewertet. Technisch dürfen
die einzelnen Evidenzträger aus mehreren Messungen oder Systemen stammen; sie
müssen jedoch auf denselben gebundenen Successor referenzieren und zu einem
frischen, konsistenten Acceptance-Snapshot zusammengeführt werden. Ein
Teilprädikat darf den terminalen Zustand nicht stellvertretend behaupten.

Ein öffentlicher Artefakt-Readback ist **scope-abhängig**, nicht für jede
Berechnung universell:

```text
C_scope.requires_public_artifact
    ⇒ PUBLIC_ARTIFACT_READBACK ∈ C_scope
```

Ist die Akzeptanzkonjunktion falsch, entsteht kein synthetischer Endzustand.
Ein identifizierbarer Folgezustand wird nach erneuter Identitäts- und
Provenienzbindung zum nächsten Subject; ist er nicht sicher bindbar, ist
fail-closed zu blockieren oder zu isolieren:

```text
if EFFECT_ACK_DONE == false:
    if BINDABLE(s_(n+1)^actual):
        subject := BIND(s_(n+1)^actual)
        CONTINUE
    else:
        BLOCK_OR_ISOLATE
```

Liveness bleibt davon getrennt: Diese Semantik garantiert nicht, dass für jedes
Programm oder jede Umgebung irgendwann `EFFECT_ACK_DONE` erreicht wird. Sie
löst insbesondere **nicht** das Halteproblem für beliebige Programme; sie
definiert eine domänenspezifische Akzeptanz- und Freigabesemantik.

### Fachliche Einordnung

Die Bausteine besitzen klare Vorläufer: Postconditions und Programmkorrektheit
in der Hoare-Logik (Hoare 1969, DOI `10.1145/363235.363259`), atomare
Wirkungspunkte für nebenläufige Objekte in der Linearizierbarkeit (Herlihy &
Wing 1990, DOI `10.1145/78969.78972`), End-to-End-Prüfung statt bloßer
Schichtbestätigung (Saltzer, Reed & Clark 1984, DOI
`10.1145/357401.357402`), dynamische Trace-Prüfung in Runtime Verification
(Leucker & Schallhart 2009, DOI `10.1016/j.jlap.2008.08.004`) sowie die
TOCTOU-Problematik (MITRE CWE-367).

Der TEMDD-Forschungsgegenstand ist die konkrete Komposition aus
Exact-Successor-Bindung, provenance-gebundener Evidenz, frischem
nicht-selbstbestätigendem Readback und einem unteilbaren
Effect-Acceptance-Urteil als Laufzeit-Freigabesemantik. Ob und in welchem Umfang
diese **Komposition** wissenschaftlich neu oder prioritätsbegründend ist, ist
durch Repository- oder Zenodo-Persistenz allein nicht bewiesen und erfordert
eine systematische Prior-Art-Prüfung sowie unabhängige fachliche Begutachtung.

## Entwicklungs- und Laufzeitrollen

- **Compiler:** übersetzt TEMDD-Modelle und -Programme in eine ausführbare oder weiter bindbare Repräsentation.
- **Linker / Binder:** verbindet Module, Identitäten, Artefakte und explizite Abhängigkeiten.
- **Dynamic Loader / Resolver:** löst zur Laufzeit verfügbare Capabilities, Implementierungen und Authority auf.
- **Runtime:** führt den gebundenen Plan aus und erzeugt beobachtbare Zustandsänderungen.
- **Debugger / Observer:** macht Ursachen, Ereignisse, Zustände und Abweichungen nachvollziehbar.
- **Test Runner:** prüft positive und negative Assertions sowie Failure Paths.
- **Effect Verifier:** prüft nicht nur Rückgabewerte, sondern die tatsächlich eingetretene, frisch zurückgelesene Wirkung.
- **IDE:** integriert Modellierung, Ausführung, Debugging, Test, Evidenz und Verifikation in einer gemeinsamen Arbeitsoberfläche.

## Semantische Grenze

Die Erklärung ist eine Architektur- und Product-Owner-Erklärung. Ihre Persistenz ist nicht selbst der Nachweis, dass jede beschriebene Komponente für jeden Release-Scope vollständig implementiert, unabhängig validiert oder produktiv ausgerollt ist. Solche Aussagen benötigen weiterhin exakte HEAD/TREE-Bindung, passende Tests, frischen Readback und die jeweils erforderliche Acceptance-Evidenz.

Insbesondere:

```text
DECLARATION_PRESENT ≠ IMPLEMENTATION_COMPLETE
IMPLEMENTATION_PRESENT ≠ VALIDATED
VALIDATED ≠ RELEASED
RELEASED ≠ EFFECT_ACK_DONE
TRANSPORT_ACK ≠ EFFECT_ACK
```

## Node- und Publikationsregel

Jeder aktuelle oder zukünftige QIK-VRT-Repository-Node, der TEMDD-Konformität behauptet, soll diese Erklärung über den kanonischen Repository-Kontext auflösen. Historische Snapshots, Tags, DOI-Artefakte und bereits veröffentlichte Zenodo-Dateisätze werden nicht rückwirkend verändert; neue Aussagen werden als neuer, provenance-gebundener Successor publiziert.

Die maschinenlesbare Projektion steht in:

- `policy/QIKVRT_TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.json`

Die Publikationsprojektion steht in:

- `docs/publications/2026-09-23-temdd-executable-language-runtime/README.md`

Die Zenodo-Publikationsvorbereitung steht in:

- `release/temdd-executable-language-runtime-2026-09-23/`
