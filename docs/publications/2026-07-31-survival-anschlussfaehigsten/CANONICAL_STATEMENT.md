<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Kanonische Computerzeitalter-Fassung

**Autor und Urheber der hier vorgelegten QIK-VRT-Operationalisierung:** Ingolf Lohmann<br>
**Version:** 1.0-candidate<br>
**Status:** `CANDIDATE_PREPUBLICATION`<br>
**Formaler Unterbau:** `KERNEL_VERIFIED` für FIT-001 bis FIT-003 und MAT-001 bis MAT-002<br>
**Statusmaterialisierung:** `KERNEL_VERIFIED`

Die von Ingolf Lohmann festgelegte informatische Übertragung lautet:

> **Survival of the fittest = Survival of the Anschlussfähigsten.**

Für die wissenschaftliche Verwendung ist das Gleichheitszeichen als
**festgelegte Übersetzungs- und Interpretationsregel für das Computerzeitalter**
zu lesen. Es behauptet keine lexikalische Wortgleichheit und ersetzt nicht die
biologische Fachdefinition von Fitness.

Die operationale Ausfaltung lautet:

> **Fitness im Computerzeitalter = Unterscheidungsfähigkeit +
> Anpassungsfähigkeit + Wirkungserhaltung + Anschlussfähigkeit.**

Dabei bedeutet Anschlussfähigkeit nicht grenzenlose Offenheit. Gemeint ist die
Fähigkeit eines Systems, unter wechselnden Bedingungen gültige Beziehungen und
Fortsetzungen herzustellen, ohne seine ausgewiesenen Invarianten,
Sicherheitsgrenzen, Provenienz oder Wahrheitsgrenzen zu verlieren.

Die maschinenprüfbare Kernaussage ist enger:

> In dem ausdrücklich definierten endlichen Fortsetzungsmodell erfordert jede
> positive Überlebensdauer eine Kette gültiger, lebensfähiger Anschlüsse; ohne
> einen lebensfähigen Nachfolger ist keine Fortsetzung um einen weiteren
> Schritt möglich.

Diese formale Aussage, die beiden präzisen Simulationssätze und die beiden
diskreten gewichteten Sätze wurden auf ihren exakten Git-Heads mit Lean 4.19.0
kernelgeprüft. Es handelt sich um konditionale Modelleigenschaften. Das beweist
weder eine neue biologische Gesetzmäßigkeit noch die empirische Überlegenheit
beliebiger Schnittstellen. Der Übergang von der Formalisierung zu einer
konkreten Software, Organisation oder biologischen Population benötigt jeweils
eine eigene Modellkorrespondenz und empirische Prüfung.

Der erweiterte Beweiskern formalisiert zusätzlich Monotonie und strikten
Vorteil endlicher natürlich gewichteter Anschluss-Sprachen bei gemeinsamem
positivem Normalisierer. Dieser zusätzliche Scope wurde im Exact-Head-Lauf
`30627411130` am Commit `37a946b9eefc21ab369ad56b5fbb1e9c436766e1`
mit leeren Axiomenlisten bestätigt. Die darauf beruhende Statusmaterialisierung
wurde im eigenen Exact-Head-Nachfolgelauf `30628327497` am Commit
`5196495f07c6f696faf6d23f9cfe353532ac042e` erneut mit fünf leeren
Axiomenlisten bestätigt und in `KERNEL_RECEIPT.json` gebunden. Repository-
Promotion, Zenodo-Publikation, DOI und systemweiter Abschluss bleiben davon
getrennt und offen.

Kurzform:

```text
SURVIVAL_OF_THE_FITTEST
  := SURVIVAL_OF_THE_ANSCHLUSSFAEHIGSTEN

COMPUTER_AGE_FITNESS
  := DISTINCTION_CAPACITY
   + ADAPTABILITY
   + EFFECT_PRESERVATION
   + CONNECTABILITY

UNQUALIFIED_OPENNESS
  != CONNECTABILITY
```

*q.e.d. Ingolf Lohmann*
