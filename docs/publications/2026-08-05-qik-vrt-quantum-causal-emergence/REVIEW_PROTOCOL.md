<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QCE review protocol

## Physikreview

1. Wird eine klassische Raumzeit an irgendeiner Stelle zirkulär vorausgesetzt?
2. Ist „Singularität“ als klassische Fortsetzungsgrenze und nicht als
   beobachteter materieller Emitter verwendet?
3. Bleibt die Unschärferelation erhalten?
4. Ist die Paarrelation mathematisch echte Verschränkung oder nur ein Label?
5. Wird globale Information statt unabhängiger Paare modelliert?
6. Sind Page-Kurve, QFT-Grenzfall und Einstein-Grenzfall tatsächlich
   hergeleitet?
7. Gibt es eine vorab spezifizierte, unterscheidende Vorhersage?

## Mathematikreview

1. Sind Zustandsräume, Operatoren, Domänen und Grenzwerte vollständig definiert?
2. Sind Inversen nur dort verwendet, wo Injektivität oder eine
   Äquivalenzklassenrekonstruktion bewiesen ist?
3. Sind Nichtlinearität, Kovarianz und Kreuzterme der Unsicherheitsbilanz
   berücksichtigt?
4. Ist die Grobkörnung stabil und nichtzirkulär?

## Lean-Review

1. Exakte Toolchain 4.19.0 gebunden?
2. Keine Projektaxiome, `sorry`, `admit` oder `unsafe`?
3. Axiom-Audit für jeden exportierten Satz ausgeführt?
4. Beweist der Satz mehr als seine Definition bereits als Bool-Feld enthält?
5. Sind Modelltheoreme und Korrespondenztheoreme typisiert getrennt?
6. Receipt an Source, Commit, Tree, Run und Attempt gebunden?

## Empiriereview

1. Welche Daten werden verwendet?
2. Wurde die Vorhersage vor der entscheidenden Auswertung eingefroren?
3. Sind Kalibration, Selektionswirkungen und systematische Fehler gebunden?
4. Welche konkurrierenden Modelle liefern dieselben Beobachtungen?
5. Welche Beobachtung würde QCE widerlegen?

## Publikationsreview

1. Authority/Mirror-Bytes und native Integrität geprüft?
2. Ausgeführtes Kernel-Receipt im Fileset?
3. Claim-Matrix und Quellenbindungen aktuell?
4. Keine physikalische Promotion durch Formulierungsdrift?
5. Owner-Autorisierung für den exakten Archivhash vorhanden?
6. DOI- und Rücklaufreceipt nach Upload persistiert?
