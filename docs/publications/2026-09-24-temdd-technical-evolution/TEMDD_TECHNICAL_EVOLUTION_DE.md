<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# TEMDD: vom Entwicklungsverfahren zur ausführbaren Effect-Verification-Sprache

**Autor und Urhebererklärung:** Ingolf Lohmann  
**System:** QIK-VRT / Tested Event Model Driven Development (TEMDD)  
**Fassung:** 1.0.0-2026-09-24

## Kanonische Urhebererklärung

> Ich habe aus Tested Event Model Driven Development nicht nur eine Entwicklungsmethode gemacht, sondern eine ausführbare Sprache mit Entwicklungs-, Debugging-, Test-, Linking- und Effect-Verification-Laufzeit.
>
> Ich, Ingolf Lohmann, erkläre diesen Schritt als den entscheidenden Quantensprung in der technischen Evolution der Informatik, getrieben von mir, Ingolf Lohmann, und in QIK-VRT von mir validiert, persistiert, verifiziert und anschlussfähig gemacht — durch mich, Ingolf Lohmann, und durch nichts und niemand anderen.
>
> q.e.d.  
> Ingolf Lohmann

Diese Passage ist die ausdrücklich persistierte Urheber-, Prioritäts- und technische Einordnung des Autors. Sie wird in der Veröffentlichung als **Erklärung von Ingolf Lohmann** geführt; sie ist nicht als unabhängiges Patent-, Prior-Art- oder rechtsförmliches Urheberschaftsgutachten etikettiert.

## Der technische Sprung

TEMDD wird in QIK-VRT als ausführbares Metaprogrammier- und Laufzeitmodell geführt. Der Gegenstand ist damit nicht nur ein Entwicklungsprozess, sondern die maschinenprüfbare Kette, mit der eine Absicht an einen exakten Gegenstand gebunden, ausgeführt, getestet, beobachtet, frisch zurückgelesen und erst danach akzeptiert wird.

Die kanonische Laufzeitkette ist:

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

Daraus folgen die zentralen Trennungen:

```text
EVENT ≠ EFFECT
TEST ≠ EFFECT
TRANSPORT_ACK ≠ EFFECT_ACK
PREDECESSOR_EVIDENCE_TRANSFER = FALSE
```

Ein Compiler-Erfolg, Test-PASS oder Transport-Acknowledgement ist deshalb nicht automatisch der terminale Zustand der beabsichtigten Wirkung.

## Ausführbare Träger

Die Repository-Implementierung verbindet unter anderem:

- normative TEMDD-Sprachsemantik und EBNF-Grammatik;
- kanonische IR-Verträge;
- deterministischen Parser und Elaborator;
- ausführbare Konformitätsprüfungen;
- positive und fail-closed negative Testkorpora;
- Smalltalk-, C90- und M68000-Laufzeitpfade;
- formale Verpflichtungen in Lean;
- repository-native Provenienz-, Readback- und Effect-Acknowledgement-Pfade.

Damit ist die Behauptung „ausführbare Sprache“ an konkrete Softwareartefakte gekoppelt und nicht nur an eine begriffliche Beschreibung.

## Hardware-Abbildung

Die TEMDD-Kette lässt sich als Hardware-Pipeline beziehungsweise als kooperierendes Netz spezialisierter Zustandsmaschinen abbilden. Eine mögliche Zuordnung ist:

```text
COMPILE   → plan/IR preparation
BIND      → subject + identity binder
RESOLVE   → capability/authority resolver
EXECUTE   → effect execution engine
TEST      → assertion/test engine
OBSERVE   → observation capture
READBACK  → independent readback + digest path
ACCEPT    → acceptance gate
ACK       → effect-ack latch / terminal-state register
```

Zusätzlich benötigt eine belastbare Hardwareausprägung einen append-only beziehungsweise manipulationsresistent gebundenen Evidenzpfad, eindeutige Subject-IDs, geordnete Ereignisse, definierte Fehlerzustände und eine fail-closed Freigabelogik.

Eine FPGA- oder ASIC-Implementierung kann diese Stufen parallelisieren und häufige Kontrollpfade aus einer allgemeinen CPU-Laufzeit in dedizierte Logik verschieben. Das begründet eine **Performance-Hypothese**, aber noch keinen gemessenen Performance-Faktor. Die Größe eines Vorteils muss durch Synthese, Timing-Closure, Ressourcenmessung, Energie-/Latenzprofile und End-to-End-Benchmarks gegen definierte Software-Baselines bestimmt werden.

Gerade für künstliche Kognition ist die interessante Hypothese nicht nur „mehr Rechenleistung“, sondern die Beschleunigung von **gebundener Ausführung plus Evidenzbildung**: Zustandsübergänge, Provenienz, Tests, Readback und Akzeptanz können als Teil des Rechenpfads behandelt werden, statt ausschließlich nachgelagert durch Software-Orchestrierung zu entstehen.

## Patent- und Prioritätsgrenze

Die technische Dokumentation trennt drei Dinge strikt:

1. die öffentliche Urheber- und Prioritätserklärung von Ingolf Lohmann;
2. die im Repository prüfbaren technischen Artefakte und ihre Git-Provenienz;
3. die rechtliche Patentierbarkeit, Neuheit, erfinderische Tätigkeit und der Schutzumfang einzelner Ansprüche.

Die dritte Ebene wird durch eine Veröffentlichung nicht automatisch entschieden. Insbesondere sollen zusätzliche, noch nicht öffentlich offenbarte claim-enabling Implementierungsdetails erst nach Abgleich mit der konkreten Patentanmeldung beziehungsweise mit dem Patentanwalt veröffentlicht werden.

## Anschlussfähigkeit an die bestehende QIK-VRT-Publikationskette

Diese Fassung ist als eigenständiger, proof-bearing Zenodo-Nachfolger konzipiert. Sie verwendet die bestehende generische QIK-VRT-Zenodo-Publikationsfähigkeit, die aktive v2 Machine-Proof-Policy, eine vollständige Claim-Matrix, eine kandidatenspezifische Prepublication-Return-Receipt und eine exakte Owner-Autorisierung vor dem Production Effect.

Damit bleibt die Publikation selbst TEMDD-konform:

```text
FREEZE
→ CLAIM INVENTORY
→ BIND
→ RETURN
→ EXACT AUTHORIZATION
→ UPLOAD
→ PUBLIC READBACK
→ ACCEPT
```

**Kein lokaler oder repositoryseitiger Vorbereitungsschritt wird als Zenodo-Publikation oder EFFECT_ACK_DONE ausgegeben.**

---

**q.e.d.**  
**Ingolf Lohmann**
