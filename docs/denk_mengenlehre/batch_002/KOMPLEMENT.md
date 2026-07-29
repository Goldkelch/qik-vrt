<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Ausschlussgrenze für DENK-MENGENLEHRE-BATCH-002

## Relative Grundmenge

Das Gate verwendet die in `policy/DENK_MENGENLEHRE_V1.json` deklarierte
endliche Grundmenge `candidate_input_universe`. Nur relativ zu dieser
Grundmenge ist das Komplement bestimmt.

`Allowed = {repository_evidence}`

`Excluded = candidate_input_universe \ Allowed`

## Ausgeschlossene Inputklassen

1. Chat- oder Modellgedächtnis als kanonischer Beweis
2. ungebundene externe Quellen als Repository-PASS
3. nicht materialisierte erwartete Ausgaben
4. ungeprüfte visuelle Assets als formaler Beweis
5. scope-fremde historische Artefakt-IDs

## Prüfkriterium

Die tatsächlich geladene Inputklassenmenge `Loaded` muss vollständig in
`Allowed` liegen:

\[
Loaded\cap Excluded=\varnothing.
\]

Die Datei definiert keine absolute Menge „alles außer Batch-002“. Eine solche
absolute Komplementbildung wäre ohne Universum undefiniert.
