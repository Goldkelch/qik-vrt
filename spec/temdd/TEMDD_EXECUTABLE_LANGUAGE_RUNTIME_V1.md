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
