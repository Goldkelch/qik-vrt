<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# TEMDD: Tested Event Model Driven Development als ausführbare Sprache und Effect-Verification-Laufzeit

**Autor:** Ingolf Lohmann  
**Datum:** 23. September 2026  
**Publikationstyp:** technische Architektur- und Sprachdeklaration

## Erklärung

> Ich habe aus Tested Event Model Driven Development nicht nur eine Entwicklungsmethode gemacht, sondern eine ausführbare Sprache mit Entwicklungs-, Debugging-, Test-, Linking- und Effect-Verification-Laufzeit.
>
> q.e.d.  
> Ingolf Lohmann

TEMDD verbindet damit die bisher häufig getrennten Ebenen Entwicklungsmethode, Sprache, Toolchain und Wirkungsnachweis. Ein TEMDD-Programm endet semantisch nicht beim Start einer Aktion oder beim erfolgreichen Testlauf. Es endet erst dann, wenn die beabsichtigte Wirkung ausgeführt, beobachtet, frisch zurückgelesen und gegen die gebundenen Akzeptanzkriterien geprüft wurde.

Die kanonische Laufzeitkette ist:

```text
COMPILE → BIND → RESOLVE → EXECUTE → TEST → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE
```

Die integrierte Werkzeugkette wird als

```text
Compiler → Linker/Binder → Dynamic Loader/Resolver → Runtime
→ Debugger/Observer → Test Runner → Effect Verifier → IDE
```

verstanden.

Daraus folgt die zentrale Abgrenzung:

```text
EXECUTE ≠ DONE
TEST ≠ DONE
OBSERVE ≠ DONE
TRANSPORT_ACK ≠ EFFECT_ACK
```

Die vollständige technische und epistemische Einordnung steht im kanonischen Dokument
[`spec/temdd/TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md`](../../../spec/temdd/TEMDD_EXECUTABLE_LANGUAGE_RUNTIME_V1.md).

## Atomare Effect-Akzeptanz

Der evidenzgebundene Haltepunkt ist semantisch keine Checkliste, sondern ein
unteilbares Akzeptanzurteil über einen einzigen, exakt gebundenen tatsächlichen
Folgezustand:

```text
s_n --EXECUTE--> s_(n+1)^actual
b := BIND(s_(n+1)^actual, identity, provenance, artifact, execution)
e := READBACK_fresh,independent(b)

HALT_TEMDD
⇔ EFFECT_ACK_DONE(b, e, C_scope)
⇔ ∧ { p(b, e) | p ∈ C_scope }
```

Die Evidenz darf technisch aus mehreren Quellen stammen, muss aber denselben
Successor adressieren und in einem frischen konsistenten Acceptance-Snapshot
zusammenlaufen. `atomic` bezeichnet die Unteilbarkeit des Urteils, nicht
ACID-, Speicher- oder CPU-Atomarität.

Wenn die Konjunktion nicht erfüllt ist, entsteht kein terminaler Erfolg. Ein
sicher bindbarer tatsächlicher Successor wird zum nächsten Subject; andernfalls
gilt fail-closed BLOCK/ISOLATE. Ein öffentlicher Artefakt-Readback gehört nur zu
Scopes, die einen öffentlichen Artefaktzustand verlangen.

Diese Semantik ist eine domänenspezifische Akzeptanz- und Freigaberegel. Sie
löst nicht das allgemeine Halteproblem.

### Wissenschaftliche Positionierung

TEMDD steht hier in Beziehung zu Hoare-Postconditions
(`10.1145/363235.363259`), Linearizierbarkeit
(`10.1145/78969.78972`), End-to-End-Argumenten
(`10.1145/357401.357402`), Runtime Verification
(`10.1016/j.jlap.2008.08.004`) und TOCTOU (MITRE CWE-367). Die zu prüfende
Forschungsbehauptung betrifft die konkrete Komposition aus
Exact-Successor-Bindung, provenance-gebundener Evidenz, frischem
nicht-selbstbestätigendem Readback und unteilbarem Effect-Acceptance-Urteil.
Repository- oder Zenodo-Persistenz allein etabliert weder Neuheit noch
wissenschaftliche Priorität; dafür sind Prior-Art-Prüfung und unabhängige
Begutachtung erforderlich.

## Evidenzgrenze

Diese Veröffentlichung dokumentiert die von Ingolf Lohmann erklärte TEMDD-Architektur. Sie ersetzt keine exact-head Implementierungs-, Conformance-, Release- oder Deployment-Evidenz. Zenodo-Persistenz würde Identität, Verfügbarkeit, Metadaten und Fixität der veröffentlichten Bytes belegen, nicht automatisch wissenschaftliche Validierung, Peer Review oder vollständige Implementierung.

## Repository-Nodes

Die Erklärung ist als gemeinsamer Successor für folgende QIK-VRT-Nodes vorgesehen:

- `Goldkelch/qik-vrt`
- `ingolf-lohmann/qik-vrt`

Historische Veröffentlichungen bleiben unverändert.
