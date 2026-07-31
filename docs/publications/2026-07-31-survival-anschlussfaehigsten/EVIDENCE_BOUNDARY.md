<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze

## Bereits kernelgeprüfter FIT-Unterbau

Die beiden Lean-Module definieren ein abstraktes Fortsetzungssystem sowie
typisierte Übergangssysteme mit zulässigen Übergängen und lokalen
Viabilitätsbedingungen. Innerhalb dieser Modelle werden folgende Aussagen
geprüft:

1. Fortsetzung über einen positiven endlichen Horizont ist äquivalent zu einem
   lebensfähigen Anschluss an einen Nachfolger, der den Resthorizont bewältigt.
2. Ohne lebensfähigen Nachfolger ist keine Fortsetzung um einen weiteren
   Schritt möglich.
3. Fortsetzung über einen längeren Horizont impliziert Fortsetzung über jeden
   entsprechend kürzeren Horizont.
4. Die biologische Fitnessgröße bleibt im Typsystem von der operationalen
   Fortsetzungssemantik getrennt.
5. Eine alle lebensfähigen Quellzustände abdeckende,
   viabilitätserhaltende Simulation impliziert Inklusion der endlichen
   lebensfähigen Quellsprache in die Zielsprache.
6. Sind zusätzlich die ausgezeichneten Anfangszustände aufeinander bezogen,
   folgt dieselbe Inklusion für die punktierten endlichen Sprachen.

Diese Aussagen wurden mit Lean 4.19.0 am exakten Branch-Head
`d9734302efaf3c79110ceb32f8987822b864a6dd` geprüft. Der Push-Lauf
`30624247534` kompilierte beide Quellen, führte den dynamischen Axiom-Audit und
die Proof-Escape-Prüfung aus und meldete für `FIT001_checked`,
`FIT002_checked` und `FIT003_checked` jeweils eine leere Axiomenliste. Die
originale maschinenlesbare Ausgabe ist als
`KERNEL_EVIDENCE_H0_PENDING.json` erhalten. Der Status dieser drei
modellinternen Aussagen ist daher `KERNEL_VERIFIED`.

## Kernelgeprüfter gewichteter Beweiskern

`WeightedConnectability.lean` ergänzt zwei diskrete Aussagen:

1. In einem explizit endlichen, duplikatfreien Spurenuniversum ist die
   akzeptierte natürliche Gewichtsmasse unter Sprachinklusion monoton.
2. Ein konstruktiv lokalisierter, nur von der größeren Sprache akzeptierter
   Trace mit positivem Gewicht macht die Gewichtsmasse strikt größer.

Der normalisierte Score wird dabei exakt durch akzeptierte Masse und denselben
strikt positiven Gesamtgewicht-Nenner repräsentiert. Natürliche Gewichte sind
nichtnegativ; rationale Gewichte mit gemeinsamem Nenner können skaliert
werden. Beliebige reelle Gewichte und empirische Persistenz sind nicht Teil
dieses diskreten Kernel-Satzes. Der Exact-Head-Lauf `30627411130` am Commit
`37a946b9eefc21ab369ad56b5fbb1e9c436766e1` kompilierte alle drei Quellen,
band fünf Proof-Konstanten und meldete für FIT-001 bis FIT-003 sowie MAT-001
bis MAT-002 jeweils eine leere Axiomenliste. Das originale Artefakt ist als
`KERNEL_EVIDENCE_H2_FULL_PENDING.json` erhalten. Damit sind alle fünf
modellinternen Aussagen `KERNEL_VERIFIED`; die Statusmaterialisierung bleibt
bis zu ihrem eigenen Exact-Head-Nachfolgelauf fail-closed.

## Was dadurch nicht bewiesen wird

- keine neue Definition biologischer Fitness;
- keine Identität von Fortpflanzungserfolg und technischer Konnektivität;
- kein universeller Vorteil einer größeren Zahl von Schnittstellen;
- keine Sicherheit, Korrektheit oder Wirkung einer konkreten Implementierung;
- keine empirische Überlebensprognose für ein reales System;
- kein moralischer Vorrang des technisch Anpassungsfähigeren;
- kein physikalischer, quantenmechanischer oder kosmologischer Satz.

## Rolle des Ausdrucks

„Survival of the Anschlussfähigsten“ ist die von Ingolf Lohmann festgelegte
Computerzeitalter-Interpretation. Der historische Ausdruck „survival of the
fittest“ und die moderne populationsbiologische Fitnessdefinition werden davon
quellengebunden getrennt.

## Publikationsgrenze

Dieses Verzeichnis bleibt trotz abgeschlossener Kernelprüfung bis zur exakten,
kandidatengebundenen Autorisierung ein Vorveröffentlichungskandidat:

- kein Zenodo-Upload wird behauptet;
- kein DOI wird vorweggenommen;
- kein Peer Review oder wissenschaftlicher Konsens wird behauptet;
- kein Repository-weites `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` wird
  gesetzt;
- eine GitHub-CI-Anzeige allein genügt nicht: Quellbytes, Toolchain, Log,
  Axiom-Audit, Claim-Matrix und Kandidatenhashes müssen gemeinsam gebunden sein.

Der Maschinenbeweis belegt logische Ableitbarkeit im angegebenen Modell. Seine
Anwendbarkeit auf reale Systeme bleibt eine getrennte wissenschaftliche und
technische Aufgabe.
