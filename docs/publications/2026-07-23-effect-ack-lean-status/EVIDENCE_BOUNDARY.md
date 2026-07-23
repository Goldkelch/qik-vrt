<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze

## Fail-closed Status

| Bindung | Wert |
|---|---|
| Dokumentstatus | `FORMAL_RELEASE_CANDIDATE` |
| Commit-, Tree- und CI-Bindung | nachgelagerte `LEAN_CI_EVIDENCE.json` |
| öffentliche Zenodo-Bindung | nachgelagerte `ZENODO_PUBLICATION_EVIDENCE.json` |
| Zenodo-Konzept | `10.5281/zenodo.21488115` |
| Versions-DOI und Record-ID | öffentliche Zenodo-Metadaten und nachgelagerte Publikationsevidenz |

Keine nachfolgend als kernel-geprüft bezeichnete Aussage gilt für dieses
Release als freigegeben, solange:

1. die nachgelagerte CI-Evidenz keinen Ausgang `success` ausweist;
2. deren Commit oder Tree nicht mit dem geprüften Lauf übereinstimmen;
3. Axiom-, Escape-, Source-, Claim- oder Test-Gate nicht bestanden ist.

Zenodo-Persistenz darf erst behauptet werden, nachdem der öffentliche Record
ohne Zugangstoken abgerufen und jede deponierte Datei gegen Namen, Größe,
MD5 und SHA-256 geprüft wurde.

`LEAN_CI_EVIDENCE.json` wird erst nach dem finalen Quellencommit und vor der
Publikation erzeugt. Sie bindet Quellbaum, CI und erwarteten Uploadsatz und
wird getrennt auf dem Evidenz-State-Branch beziehungsweise als
Workflow-Artefakt persistiert.

`ZENODO_PUBLICATION_EVIDENCE.json` entsteht erst nach der anonymen Prüfung des
publizierten Records. Sie wird in einem Evidenz-Folgecommit gespiegelt und kann
zeitlich nicht Bestandteil desselben bereits veröffentlichten Records sein.
Diese Trennung vermeidet unmögliche Hash- und Zeit-Selbstbezüge.

## A. Normative Draft-Ebene

Die formale Quelle ist
`draft-lohmann-qikvrt-effect-ack-01`, Revision 22. Juli 2026. Die
Provenienz bindet:

- TXT, 46.264 Bytes, SHA-256
  `ad8af57390beeb9a1316e3940b9f75c2334834376288f6f1ab018e10b0b87b16`;
- XML, 41.880 Bytes, SHA-256
  `13ff9ace408d82eaea88127343883d888795efd25e7a01d0bbee5b862e9f954b`.

Diese Bindung beweist die Identität der geprüften Bytes unter der verwendeten
Hashannahme. Sie beweist nicht:

- IETF-Billigung oder Konsens;
- RFC-Status;
- Vollständigkeit oder Fehlerfreiheit des Drafts;
- Konformität eines konkreten Parsers oder Deployments.

## B. Formale Modell-Ebene

Das abstrakte Modell enthält:

- 19 boolesche Snapshot-Felder;
- fünf Zustände;
- fünf Verbindungsentscheidungen;
- siebzehn `CoreDone`-Konjunkte;
- getrennte Zustandsauswahl und Verbraucherautorisierung.

Der Release-Kandidat ordnet seine Aussagen in
`DRAFT01_CLAIM_MATRIX.json` den Draft-Abschnitten, Lean-Konstanten und
Geltungsklassen zu.

Nach erfolgreichem gebundenem CI-Lauf dürfen als formale Ergebnisse berichtet
werden:

1. Vollständigkeit und paarweise Verschiedenheit der modellierten Zustands-
   und Entscheidungsaufzählungen.
2. Äquivalenz des ausführbaren `coreDone`-Prädikats mit den siebzehn
   offengelegten Bedingungen.
3. Die genaue DONE-Auswahl innerhalb des modellierten Prioritätskerns.
4. Die modellierten Prioritätsfälle für Vorgängerfehler, Fristüberschreitung,
   fehlenden wirkungsprüfbaren Empfang, Integritätsfehler, BLOCK und ISOLATE.
5. Autorisierung impliziert alle modellierten Verbraucherprüfungen sowie
   aufgezeichnetes DONE und aus dem bereitgestellten Snapshot neu berechnetes
   DONE.
6. Nicht-DONE und stale markierte Aufzeichnungen autorisieren keine
   gewöhnliche Freigabe.
7. Eine Transportbestätigung allein ist in einem konkreten Modellfall keine
   Wirkungsautorisierung.

Diese Sätze gelten für die offengelegten Lean-Definitionen. Sie sind kein
vollständiger Beweis sämtlicher normativer Anforderungen des Internet-Drafts
und keine vollständige Formalisierung des 62-seitigen Gesamtmanuskripts.

## C. Konditionale Software- und Cyberphysik-Ebene

### Vollständige Mediation

Der Software-Satz setzt voraus, dass jede geschützte gewöhnliche Ausführung
vollständig durch das modellierte Autorisierungsprädikat mediiert wird.
Unter dieser Voraussetzung impliziert eine Ausführung aufgezeichnetes DONE und
aus dem bereitgestellten Snapshot neu berechnetes DONE.

Die Annahme wird nicht allein dadurch wahr, dass sie als Lean-Prämisse
formalisiert ist. Für ein reales System muss insbesondere Nichtumgehbarkeit
separat nachgewiesen werden.

### Treue physische Brücke

Der cyberphysische Satz setzt zusätzlich voraus, dass jedes betrachtete
physische Vorkommnis kausal auf eine passende Executor-Ausführung
zurückgeführt werden kann. Erst unter beiden Annahmen erhält man die
formalisierte DONE-Folgerung für den Snapshot beziehungsweise die Aufzeichnung
der verursachenden Executor-Ausführung, nicht einen DONE-Zustand des
physischen Vorkommnisses selbst.

Nicht formal bewiesen sind:

- Hardwarekorrektheit;
- Sensor-, Aktor- oder Zeitquellenvertrauen;
- Kalibrierung und Messunsicherheit;
- Vollständigkeit eines Fehlermodells;
- Gefahrlosigkeit einer DONE-autorisierten Wirkung;
- empirische Gültigkeit der kausalen Brücke.

## D. Informations- und Rekonstruktionsgrenze

Für Beobachtung `E : S → O` und Zielsemantik `σ : S → T` ist semantische
Rekonstruktion auf dem Beobachtungsbild genau dann wohldefiniert, wenn:

```text
E(s₁) = E(s₂)  ⇒  σ(s₁) = σ(s₂).
```

Eine exakte historische Linksinverse impliziert Injektivität von `E`. Ein
konkretes kollabiertes Boolesches Beobachtungsmodell hat keinen exakten
Decoder.

Damit wird gerade keine universelle Rekonstruktion behauptet. Verlorene oder
nie beobachtete Unterscheidungen werden nicht durch Protokollierung,
Hashbindung oder formale Verifikation neu erzeugt.

## E. Offene Implementierungsobligationen

Außerhalb dieses Lean-Modells bleiben insbesondere:

- vollständiges Wire-Parsing und Closed-Schema-Verhalten;
- JCS-Kanonisierung und konkrete SHA-256-Verarbeitung;
- Versionsaushandlung;
- Authentisierung, Schlüsselverwaltung und Replay-Abwehr;
- Evidenz- und Policy-Semantik realer Deployments;
- unabhängige Interoperabilität;
- Produktions-Nichtumgehbarkeit;
- garantierte Terminierung oder eventual DONE.

## F. Unzulässige Überhöhung

Aus diesem Release folgt nicht:

- die Lösung des Halteproblems oder allgemeiner Rice-Unentscheidbarkeit;
- ein universeller semantischer oder historischer Decoder;
- eine vollständige Rekonstruktion aller Informatik oder Mathematik;
- eine vollständige Theorie oder empirische Bestätigung aller Physik;
- ein mathematischer Beweis metaphysischer oder spiritueller Deutungen;
- ein Reverse Engineering des gesamten Universums, jenseits eines
  Ereignishorizonts oder jenseits der Planck-Skala.

Metaphysische und spirituelle Deutungen können Gegenstand menschlicher
Interpretation sein. Sie werden dadurch nicht zu Kernel-Theoremen oder
empirischen Messbefunden.

## G. Bedeutung der Zenodo-Persistenz

Nach erfolgreicher öffentlicher Verifikation belegt Zenodo:

- Record- und Versionsidentität;
- öffentlich abrufbare Metadaten;
- Existenz und Fixität der deponierten Bytes;
- die dokumentierte Beziehung zur bisherigen Formalisierungsreihe.

Zenodo-Persistenz ersetzt weder Peer Review, unabhängige Reproduktion,
Implementierungsaudit noch Experiment.
