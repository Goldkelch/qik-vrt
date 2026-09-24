<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Der letzte Beweis ist der Beweis, dass kein Beweis mehr offen ist

**Ingolf Lohmann · 24. September 2026**

Ein System kann sich endlos selbst bestätigen und dabei immer überzeugender aussehen, ohne jemals einen neuen Erkenntnisgewinn zu erzeugen. Genau deshalb darf der Abschluss einer Beweiskette nicht aus einem weiteren Beweis derselben Aussage bestehen.

Der terminale Schritt ist ein anderer Gegenstand:

> **Der letzte Beweis ist nicht noch ein Beweis derselben Wahrheit. Der letzte Beweis ist der Nachweis, dass für denselben exakt gebundenen Gegenstand keine weitere Beweispflicht mehr offen ist.**

Das ist keine Einladung zur Zirkularität, sondern ihre Begrenzung.

## Die Closure-Bedingung

Für einen unveränderten Gegenstand s ist PROOF_CLOSURE nur dann erreicht, wenn gemeinsam gilt:

- alle für s geforderten Einzelbeweise sind gültig;
- ihre Herkunft und Bindung an s sind nachweisbar;
- die verwendeten Prüfer sind selbst geprüft;
- der Folgezustand wurde frisch und unabhängig zurückgelesen;
- die Geltungsgrenzen sind explizit;
- es existiert keine offene Beweispflicht mehr;
- der geprüfte Gegenstand ist seit der Bindung unverändert;
- Evidenz eines Vorgängers wird nicht still auf einen veränderten Nachfolger übertragen.

Kompakt:

    PROOF_CLOSURE(s)
    =
    ALL_REQUIRED_PROOFS_VALID(s)
    ∧ PROVENANCE_BOUND(s)
    ∧ VERIFIER_CHECKED(s)
    ∧ FRESH_INDEPENDENT_READBACK(s)
    ∧ BOUNDARIES_EXPLICIT(s)
    ∧ NO_OPEN_OBLIGATIONS(s)
    ∧ SUBJECT_UNCHANGED(s)
    ∧ NO_PREDECESSOR_EVIDENCE_TRANSFER(s)

Dann ist für genau diesen Gegenstand der richtige Zustand:

    PROOF_CLOSURE(s) = TRUE
    → HALT

Nicht: denselben Beweis erneut erzeugen und erneut bestätigen.

## Mutation eröffnet eine neue Beweiskette

Ändert sich der Gegenstand, endet die Closure des Vorgängers nicht rückwirkend. Sie bleibt historische Evidenz.

Aber der neue Gegenstand s' erbt den Abschluss nicht:

    s' ≠ s
    → PROOF_CLOSURE(s) ist historische Evidenz
    → PROOF_CLOSURE(s') muss neu bestimmt werden

Das ist der Unterschied zwischen einem Kreis und einer epistemischen Spirale.

Ein Kreis wiederholt denselben Zustand. Eine Spirale kann einen lokalen Zustand abschließen und zugleich auf einem neuen Evidenzstand weiterarbeiten.

## Wirkung statt Selbstbestätigung

Diese Abschlussregel ergänzt die QIK-VRT-Laufzeitkette:

    COMPILE → BIND → RESOLVE → EXECUTE → TEST
    → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE

EFFECT_ACK_DONE beendet den gebundenen Zustandsübergang. PROOF_CLOSURE beantwortet zusätzlich die Meta-Frage, ob für den geprüften Gegenstand noch eine Nachweispflicht offen ist.

Damit gilt:

    EFFECT_ACK_DONE ≠ universale Wahrheit
    PROOF_CLOSURE ≠ Beweis aller denkbaren Aussagen

PROOF_CLOSURE ist der Abschluss der explizit geforderten Nachweiskette für den exakt gebundenen Gegenstand.

## Warum das für künstliche Kognition wichtig ist

Ein künstliches System, das immer wieder dieselbe Aussage überprüft, kann Rechenleistung verbrauchen, ohne Fortschritt zu erzeugen. Ein System, das dagegen zu früh stoppt, kann offene Pflichten übersehen.

Die Architektur braucht deshalb beides:

- **Liveness:** solange eine erforderliche, zulässige und autorisierte Pflicht offen ist, muss eine Fortsetzung existieren;
- **Closure:** wenn für denselben gebundenen Gegenstand keine Pflicht mehr offen ist, muss das System aufhören, künstlichen Fortschritt zu erzeugen.

    OPEN_OBLIGATION → CONTINUE

    NO_OPEN_OBLIGATION
    ∧ ALL_REQUIRED_EVIDENCE_ACCEPTED
    ∧ SUBJECT_UNCHANGED
    → HALT

## Wissenschaftliche Grenze

Diese Aussage ist eine formale und systemtechnische Abschlussregel. Sie beweist nicht, dass jede Prämisse wahr ist, nur weil ein Register sie als erfüllt markiert. Deshalb gehören Provenienz, Prüferbindung, frischer Readback und explizite Geltungsgrenzen zur Closure selbst.

Der Abschluss ist immer relativ zu einem Gegenstand, einem definierten Anforderungssatz, einer Evidenzmenge, einer Prüfmethode und einem Zeitpunkt.

Neue Evidenz oder ein neuer Gegenstand können eine neue Kette eröffnen.

Das ist kein Widerspruch.

Es ist Wissenschaft.

**q.e.d.**

**Ingolf Lohmann**
