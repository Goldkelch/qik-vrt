# TEMDD — Erklärung zum technischen Evolutionssprung

**Urheber und Erklärender:** Ingolf Lohmann  
**System:** QIK-VRT / Tested Event Model Driven Development (TEMDD)  
**Status:** versionierte Urheber-, Prioritäts- und technische Einordnung  
**Repository:** `Goldkelch/qik-vrt`

## Kanonische Erklärung

> Ich habe aus Tested Event Model Driven Development nicht nur eine Entwicklungsmethode gemacht, sondern eine ausführbare Sprache mit Entwicklungs-, Debugging-, Test-, Linking- und Effect-Verification-Laufzeit.
>
> Ich, Ingolf Lohmann, erkläre diesen Schritt als den entscheidenden Quantensprung in der technischen Evolution der Informatik, getrieben von mir, Ingolf Lohmann, und in QIK-VRT von mir validiert, persistiert, verifiziert und anschlussfähig gemacht — durch mich, Ingolf Lohmann, und durch nichts und niemand anderen.
>
> q.e.d.  
> Ingolf Lohmann

## Technischer Gehalt

TEMDD wird in diesem Repository nicht nur als Prozessbeschreibung geführt, sondern als ausführbares, prüfbares Sprach- und Laufzeitsystem. Die Anschlussfähigkeit ist durch konkrete Repository-Artefakte materialisiert:

- `TEMDD_LANGUAGE_SPEC_V0_1.md` — normative Sprach- und Semantikbeschreibung.
- `TEMDD_Syntax_V0_1.ebnf` — Grammatik.
- `../../schemas/temdd-ir-v0.1.schema.json` — kanonischer IR-Vertrag.
- `../../tools/qikvrt_temdd.py` — deterministischer Referenz-Parser/Elaborator.
- `../../tools/qikvrt_temdd_conformance.py` — ausführbare semantische Konformitätsprüfung.
- `../../tests/temdd/` — positive und fail-closed negative Testfälle.
- `../../runtime/temdd/TEMDDRuntime.st` — Smalltalk-Laufzeit-Backend.
- `../../src/temdd_core.c` — deterministischer C90-Kern.
- `../../runtime/m68000/temdd_transition.s` — M68000-Backend.
- `../../formalization/TEMDDCore.lean` — formale Verpflichtungen.

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

Daraus folgen insbesondere:

```text
EVENT ≠ EFFECT
TEST ≠ EFFECT
TRANSPORT_ACK ≠ EFFECT_ACK
PREDECESSOR_EVIDENCE_TRANSFER = FALSE
```

Ein erfolgreicher Einzelschritt ist deshalb kein Abschluss. Der Abschluss ist an den gebundenen Gegenstand, tatsächliche Ausführung, Beobachtung, frischen Readback und Akzeptanz gebunden.

## Validierung, Persistierung, Verifikation und Anschlussfähigkeit

Die technische Bedeutung dieser Erklärung ist nicht, dass ein Text sich selbst beweist. Sie ist, dass der Anspruch an ausführbare Artefakte, versionierte Zustände und reproduzierbare Prüfpfade gekoppelt wird.

Für TEMDD bedeutet das:

1. **Validierung:** Semantik und Invarianten werden durch ausführbare Conformance- und Testpfade geprüft.
2. **Persistierung:** Sprache, Runtime, Tests, Formalisierung und diese Erklärung sind Git-versionierte Repository-Artefakte.
3. **Verifikation:** Ergebnisse dürfen nur aus dem jeweils gebundenen Subject und frischer Evidenz abgeleitet werden.
4. **Anschlussfähigkeit:** Änderungen erzeugen Successor-Subjects; Vorgängerevidenz wird nicht übertragen; neue Subjects müssen selbst frisch geprüft werden.
5. **Effect Verification:** Wirkung wird nicht aus Transport, Event oder Test allein abgeleitet, sondern über OBSERVE → READBACK → ACCEPT bis zum evidenzgebundenen Haltepunkt geführt.

## Attribution und Prüfgrenze

Die ausschließliche persönliche Zuordnung des technischen Evolutionssprungs zu Ingolf Lohmann ist die in diesem Dokument ausdrücklich abgegebene **Urheber- und Prioritätserklärung von Ingolf Lohmann**.

Die Repository-Artefakte können technische Inhalte, Commit-Provenienz, Ausführbarkeit und konkrete Validierungsschritte maschinenlesbar belegen. Dieses Dokument allein ist jedoch kein unabhängiges weltweites Prior-Art-, Patent- oder rechtsförmliches Urheberschaftsgutachten und erhebt nicht den Anspruch, ein solches externes Verfahren zu ersetzen.

Diese Trennung ist selbst Teil der TEMDD-Evidenzdisziplin: **Behauptung, Artefakt, Ausführung, Beobachtung und unabhängige externe Feststellung sind verschiedene Evidenzklassen und werden nicht synthetisch gleichgesetzt.**

## Bindung

Die Erklärung wurde auf Basis des Repository-Zustands

`0cb6abae0b354d5eae4d07888b36779fb611df7e`

materialisiert. Ihre konkrete persistierte Identität ergibt sich aus dem Git-Commit, Tree und Blob, in denen diese Datei gespeichert ist; diese Werte sind nach der Mutation frisch zurückzulesen.

---

**q.e.d.**  
**Ingolf Lohmann**
