<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT Global System Closure v1

## Erkenntnis

QIK-VRT ist nach außen genau dann als ein geschlossenes System behandelbar,
wenn jede Interaktion durch denselben kanonischen Übergang läuft und genau
einen überprüfbaren Folgezustand erzeugt:

`INTERACTION -> EVIDENCE -> WORK_UNIT -> CANDIDATE -> GATES -> EFFECT_ACK -> EFFECT -> RECEIPT -> OBSERVATION`

„Monolithisch“ bezeichnet dabei eine einzige Eintrittsstelle, einen
kanonischen Zustand, eine geordnete Work Unit, genau einen nächsten Effekt und
eine Receipt-Kette. Es verlangt keinen unwartbaren Ein-Datei-Monolithen. Die
internen Implementierungen bleiben austauschbare, testbare Fähigkeiten.

## Funktionsnachweis und Beweisgrenze

`system-closure/ARCHITECTURE_FUNCTIONALITY_EVIDENCE.json` bindet die
Materialisierung des Denk-Mengenlehre-Modells in Pull Request 202 an einen
exakten Authority-Commit und -Tree sowie an sechs erfolgreiche
Exact-Head-Workflows. Das ist maschinell überprüfbare
`EMPIRICALLY_EVIDENCED`-Ausführungsevidenz dafür, dass die Kette

`Idee -> Spezifikation -> Artefakte -> Tests -> Integrität -> Remote-Checks`

im Architekturansatz funktioniert.

Diese Evidenz ist kein Lean-Kernel-Beweis der Leitthese, kein Merge-Nachweis,
keine Authority/Mirror-Gleichheit, keine Zenodo-Veröffentlichung und kein
repository-weites `PASS`.

## Monotone Verbesserung

Eine Interaktion darf den kanonischen Zustand nur auf eine von zwei Arten
fortschreiben:

1. mindestens eine erklärte, gemessene Gate-Metrik verbessert sich und keine
   Schutzmetrik regressiert; oder
2. der Zustand bleibt byteidentisch und wird als `NO_OP` quittiert.

Eine Regression wird nicht kanonisiert. Sie bleibt als abgelehnter Kandidat
mit Failure Class und Receipt sichtbar. Dieses Kriterium ist
Nichtregression, nicht die unbeweisbare Behauptung universeller qualitativer
Verbesserung.

## Kleine Persistenz- und Recovery-Stufen

Jeder Übergang erhält einen inhaltsadressierten Checkpoint. Checkpoints sind
linear, binden den Vorgängerhash und werden in kleinen Git-Commits
materialisiert:

1. `CONTRACT_BOUND`
2. `ANTICIPATION_MATERIALIZED`
3. `EFFECT_INTENTS_GATED`
4. `CANDIDATE_VERIFIED`
5. `AUTHORITY_OBSERVED`
6. `MIRROR_OBSERVED`
7. `RECEIPT_CLOSED`

Vor einer externen Mutation ist ein lokaler Rücksprung auf einen früheren
Commit möglich. Nach einer möglicherweise ausgeführten Remote-Mutation wird
kein Rollback behauptet. Der Zustand wechselt in
`EXTERNAL_STATE_UNKNOWN`, wird durch read-only Beobachtung rekonstruiert und
nur per idempotentem Replay oder Forward Repair fortgesetzt.

## Effektgrenze

Der vorhandene fünfstufige `EFFECT_ACK`-Automat bleibt die einzige
Freigabeinstanz. Adaptive Beobachtung und Antizipation dürfen Vorschläge,
Work Units und Effekt-Intents erzeugen, aber niemals
`EFFECT_ACK_DONE` erfinden.

Eine vorab autorisierte Orchestrierung darf einen exakt begrenzten
Arbeitsschritt automatisch ausführen. Jeder externe Einzeleffekt erfordert
zusätzlich unmittelbar vor Ausführung:

- exakte Payload-, Ziel-, Zeit- und Policy-Bindung;
- frische Herkunfts- und Kontextprüfung;
- benannten Verantwortungsträger;
- einen für exakt diesen Effekt neu ausgewerteten `EFFECT_ACK_DONE`;
- einen nachfolgenden Effekt-Receipt.

Transportannahme ist kein Effekt-Receipt.

## Zielgerichtete zeitgebundene Übertragung

Eine Übertragung an einen einzelnen Mesh-Node wird als separat signierbarer
äußerer Envelope um den unveränderten EFFECT_ACK-v1-Datensatz modelliert.
Broadcasts, Wildcards und mehrdeutige Ziele sind ausgeschlossen. Ein Scheduler
signalisiert nur Fälligkeit; er erteilt keine Freigabe.

Die Zustandsfolge lautet:

`QUEUED -> ELIGIBILITY_VERIFIED -> DISPATCH_ATTEMPTED -> TRANSPORT_ACK -> EFFECT_RECEIPT_VERIFIED`

Ohne exakten aktiven Registry-Treffer, innerhalb des Zeitfensters und ohne
frischen effect-spezifischen `EFFECT_ACK_DONE` bleibt der Effekt
`NOT_DISPATCHED`.

## Zenodo

Zenodo-Absichten werden nur als inerte Warteschlange materialisiert. Eine
Produktionsmutation bleibt gesperrt, bis die bestehende Policy
`NO_MACHINE_PROOF_NO_ZENODO_UPLOAD` vollständig erfüllt ist: eingefrorene
Bytes, vollständige Claim-Disposition, Lean/Lake-Kernel-Receipts für formale
Claims, negative und Grenztests, Korrektur und kandidatenspezifische
Rücklieferung, exakte Upload-Freigabe, v2-Proof-Bundle sowie anschließender
öffentlicher Byte-Redownload.

## Implementierter Snapshot

Die Referenzmaterialisierung liegt unter `anticipation/` und
`receipts/anticipation/`. Der äußere Envelope
`anticipation/effects/TARGETED_EFFECT_ENVELOPE.json` bindet eine inerte
Readiness-Information an genau den registrierten Node
`a84f157a-cef2-4c47-bca9-8f407085bdbe` und an das feste Zeitfenster
`2026-08-01T12:00:00Z` bis `2026-08-01T12:15:00Z`. Die deterministische
Auswertung blockiert, weil die persistierte Node-Freshness abgelaufen ist;
Herkunft und effect-spezifischer ACK sind ebenfalls nicht freigegeben. Es
wurde nichts übertragen.

`release/system-closure-v1/ZENODO_PUBLICATION_QUEUE.json` hält die spätere
Publikationsabsicht fest, jedoch weder einen eingefrorenen Kandidaten noch eine
Upload-Freigabe. Der Zustand ist
`BLOCKED_AWAITING_MACHINE_PROOF`; es wurde kein Zenodo-Netzwerkeffekt
versucht.

## Abschluss

Der neue Scope heißt `qikvrt-global-system-closure-v1`. Er ist ausdrücklich
vom historischen `qikvrt-global-claim-scope-v1` getrennt. Bis alle
Exact-Head-, Authority-, Mirror-, Receipt- und gegebenenfalls
Publikationsgates vorliegen, bleibt sein Effektzustand
`EFFECT_ACK_CONTINUE`.
