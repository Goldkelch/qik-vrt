<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidence boundary

## Exhaustiv im angegebenen endlichen Modell geprüft

- 19 boolesche Modellmerkmale und fünf Verbindungsentscheidungen;
- 2.621.440 Zustandsbelegungen;
- 5.242.880 Kombinationen mit gültiger oder ungültiger Verbraucherzulassung;
- Totalität und Erreichbarkeit der fünf Zustände;
- DONE-only-Freigabeautorisierung;
- Übereinstimmung mit einem getrennt strukturierten Prioritätsorakel;
- sieben gezielte Prioritätskollisionen;
- notwendiges Wegfallen von DONE beim Ausschalten jedes der 17
  CoreDone-Konjunkte;
- 49 kleine Repository-Modelle, 2.401 Paarvergleiche und 2.401
  quellgetaggte Aggregat-Roundtrips;
- 64 kleine Faktorisierungspaare sowie vollständige Inversionsuniversen
  `3 -> 3` und `3 -> 2`.

## Strukturell an Draft -01 gebunden

Die XML-Quelle wird geparst und auf 35 Wire-Felder, fünf Zustände, fünf
Verbindungsentscheidungen, die exakten 17 CoreDone-Zeilen und die
Prioritätsanker geprüft. Das ist eine strukturelle Bindung, kein vollständiger
Verhaltensbeweis jedes Parsers, Wire-Felds oder Deployments.

## Konditional

- vollständige Mediation jedes gewöhnlichen geschützten Ausführungspfads;
- schema-valide, authentisierte, frische und kettenvalide Verbraucherzulassung;
- erneute Ableitung von Zustand, Policy- und Evidenzbindung;
- treuer Executor für jede spätere physikalische Interpretation;
- Hardware-, Sensor-, Aktor- und Fehlermodell sowie empirische Validierung.

## Nicht bewiesen

- vollständige Draft-01-Wire-Konformität der aktuellen Python-Runtime;
- unabhängige Interoperabilität;
- ein universeller semantischer oder historischer Decoder;
- Erzeugung verlorener oder nie beobachteter Information;
- garantierte Terminierung oder eventual `EFFECT_ACK_DONE`;
- eine Lösung des Halteproblems oder der allgemeinen Rice-Unentscheidbarkeit;
- Nichtumgehbarkeit eines konkreten Produktionssystems ohne Systemprüfung;
- Gefahrlosigkeit eines DONE-autorisierten physikalischen Effekts;
- IETF-Konsens, RFC-Status, Peer Review oder externe Adoption.

## Präzise Rekonstruktionsgrenze

Für Beobachtung `E:S -> O` und Zielsemantik `sigma:S -> T` existiert eine
wohldefinierte Rekonstruktion `h` auf dem Bild von `E` mit
`sigma = h o E` genau dann, wenn

```text
E(s1) = E(s2)  =>  sigma(s1) = sigma(s2).
```

Exakte historische Rückgewinnung des Ursprungs verlangt Injektivität der
Beobachtung auf der betrachteten Ursprungsmenge. Ausführbarkeit verlangt
zusätzlich effektive Berechenbarkeit, autorisierten Zugriff und ausreichende
Ressourcen.

„Zugänglich“ bezeichnet eine vollständige, rechtmäßig lesbare und für den
Prüfschritt eingefrorene endliche Repräsentation. Eine SHA-256-Prüfsumme bindet
diese Bytes unter der Kollisionsresistenzannahme; sie ist weder eine injektive
Kodierung beliebiger Eingaben noch ein Herkunfts- oder Authentisierungsnachweis.
