<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT / EFFECT_ACK — Lean-Status zu Draft-01

> **Dokumentstatus:** `FORMAL_RELEASE_CANDIDATE`
> Dieses Bundle bleibt ein Kandidat, bis sowohl die nachgelagerte Datei
> `LEAN_CI_EVIDENCE.json` den finalen Quellenstand mit einem erfolgreichen
> Lauf bindet als auch `ZENODO_PUBLICATION_EVIDENCE.json` den Zenodo-Record
> anonym öffentlich geprüft hat. Ein Kandidat ist keine
> Publikationsbehauptung.

Dieses additive Release-Bundle dokumentiert die formale Rekonstruktion des
abstrakten Entscheidungs- und Freigabekerns von
`draft-lohmann-qikvrt-effect-ack-01` in Lean 4. Es ergänzt:

- das Working Paper
  [QIK-VRT/EFFECT_ACK: universalisierbare Wirkungssteuerung](https://doi.org/10.5281/zenodo.21498773),
  das eine exhaustive endliche Modellprüfung und die wissenschaftliche
  Geltungsgrenze dokumentiert;
- die bestehende, partielle Manuskriptformalisierung im Zenodo-Konzept
  [10.5281/zenodo.21488115](https://doi.org/10.5281/zenodo.21488115).

Es ersetzt weder das Working Paper noch den Internet-Draft und ändert keine
bereits veröffentlichte Version.

## Öffentlich inventarisierter Zenodo-Ausgangsstand

Vor der Alpha-2-Reservierung wurde die öffentliche Linie am 23. Juli 2026
zweimal anonym geprüft. Das Konzept
[10.5281/zenodo.21488115](https://doi.org/10.5281/zenodo.21488115) enthielt
genau drei publizierte Versionen:

1. `1.0.0`, Record
   [21488116](https://zenodo.org/records/21488116);
2. `2026.07.22-effect-ack-universality-1.0.0`, Record
   [21498774](https://zenodo.org/records/21498774);
3. `2.0.0-alpha.1`, Record
   [21501365](https://zenodo.org/records/21501365), damals `latest`, mit
   vierzehn Dateien und zusammen 808.699 Bytes.

Das Working Paper [21498773](https://zenodo.org/records/21498773), das
62-seitige Manuskript [21482023](https://zenodo.org/records/21482023) und die
Legacy-Software [20712301](https://zenodo.org/records/20712301) gehören zu
getrennten Zenodo-Konzeptlinien. Diese Ausgangsinventur ist
Provenienzdokumentation, kein Peer Review und kein inhaltlicher
Totalitätsnachweis.

## Gebundene Release-Identität

| Feld | Wert |
|---|---|
| Version | `2.0.0-alpha.2` |
| Commit-, Tree- und CI-Bindung | nachgelagerte `LEAN_CI_EVIDENCE.json` |
| öffentliche Zenodo-Bindung | nachgelagerte `ZENODO_PUBLICATION_EVIDENCE.json` |
| Zenodo-Konzept | [10.5281/zenodo.21488115](https://doi.org/10.5281/zenodo.21488115) |
| Versions-DOI und Record-ID | werden ausschließlich aus den öffentlichen Zenodo-Metadaten übernommen |

Vor einer Freigabe bindet `LEAN_CI_EVIDENCE.json` Commit, Tree, CI-Lauf und
den erwarteten Uploadsatz. Nach der Publikation prüft
`ZENODO_PUBLICATION_EVIDENCE.json` die tatsächlichen öffentlichen Metadaten
und Uploadbytes. Diese zweite Evidenz kann zeitlich nicht Bestandteil
desselben bereits veröffentlichten Records sein und wird deshalb in einem
Folgecommit persistiert. Keine dieser Identitäten steht selbstreferenziell im
eigenen Quellenbaum.

## Vier getrennte Aussageebenen

### 1. Normativer Draft

Der formale Ausgangspunkt ist ein **aktiver individueller Internet-Draft**:

> *QIK-VRT Effect Acknowledgement: Separating Receipt from Authorization for
> Downstream Effect*, Revision `-01`, 22. Juli 2026.

Der Draft ist ein Arbeitsdokument. Er ist kein RFC, kein IETF-Konsens und kein
Nachweis einer interoperablen Implementierung. Maßgeblich bleiben die
offiziellen IETF-Dateien:

- [Datatracker](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/01/)
- [TXT](https://www.ietf.org/archive/id/draft-lohmann-qikvrt-effect-ack-01.txt)
- [XML](https://www.ietf.org/archive/id/draft-lohmann-qikvrt-effect-ack-01.xml)

Die lokale Provenienzdatei bindet deren exakte Bytes durch SHA-256.

### 2. Formale Erweiterung

Die Lean-Bibliothek `QIKVRTEffectAck` modelliert den abstrakten Draft-01-Kern:

- fünf Zustände und fünf Verbindungsentscheidungen;
- die siebzehn `CoreDone`-Bedingungen;
- die offengelegte Prioritätsordnung der Zustandsauswahl;
- getrennte Verbraucherprüfung und DONE-only-Autorisierung;
- ein konkretes Gegenbeispiel gegen die Gleichsetzung von
  Transportbestätigung und Wirkungsautorisierung;
- vollständige Mediation als explizite Softwareannahme;
- einen konditionalen Übergang zu physikalischen Vorkommnissen;
- die Grenze semantischer und historischer Rekonstruktion.

Der maschinenprüfbare Status dieser Aussagen wird ausschließlich durch den
oben gebundenen CI-Lauf und die zugehörigen Axiom-, Escape-, Source- und
Claim-Audits bestimmt.

### 3. Bedingungen

Der Software-Satz über ausgeführte Wirkungen setzt vollständige Mediation
voraus: Jede geschützte Ausführung muss den modellierten Autorisierungspfad
durchlaufen.

Die cyberphysische Aussage setzt zusätzlich eine treue kausale Brücke voraus.
Hardwarekorrektheit, Sensor- und Aktorvertrauen, Kalibrierung,
Fehlerabdeckung, Nichtumgehbarkeit und physische Sicherheit sind keine
Folgerungen allein aus dem Lean-Beweis.

### 4. Scope-Grenzen

Nicht bewiesen werden:

- vollständige Draft-01-Wire-Konformität;
- JCS-/SHA-256-, Parser-, Versions-, Authentisierungs- oder
  Interoperabilitätskonformität einer konkreten Implementierung;
- IETF-Konsens, RFC-Status oder Peer Review;
- garantierte Terminierung oder eventual `EFFECT_ACK_DONE`;
- voraussetzungslose physische Sicherheit;
- ein universeller Decoder oder die Rückgewinnung verlorener Information;
- das vollständige Reverse Engineering aller Informatik, Mathematik, Physik,
  Metaphysik, Spiritualität oder des Universums.

Das formale Gegenbeispiel einer kollabierten Beobachtung zeigt vielmehr eine
allgemeine Inversionsgrenze: Ohne hinreichend informative Beobachtung ist
exakte historische Rekonstruktion nicht generell möglich.

## Dateien

| Datei | Funktion |
|---|---|
| `STATUSERKLAERUNG_WHATSAPP_DE.md` | kurze, WhatsApp-optimierte Erklärung im Namen Ingolf Lohmanns |
| `EVIDENCE_BOUNDARY.md` | genaue Trennung von Beweis, Bedingung, Evidenz und offenen Punkten |
| `CITATION.cff` | maschinenlesbare Zitationsmetadaten |
| `ZENODO_FILESET.md` | verbindliche Dateigrenze für das additive Zenodo-Release |

Die vollständigen Lean-Quellen, Claim-Matrix, Draft-Provenienz, Audits,
Tests und exakten Eingabedateien gehören in das verknüpfte
Software-Release-Archiv.

## Lizenz- und Herkunftsgrenze

Die Dokumente dieses Verzeichnisses stehen, soweit nicht anders
gekennzeichnet, unter CC BY-NC-ND 4.0. Lean- und Prüfcode folgt seinen
dateibezogenen Code-Lizenzen. Die IETF-Quelldateien behalten ihre eigenen
IETF-Trust-Hinweise. Eine gemeinsame Ablage ändert keine dieser Lizenzen.

— Ingolf Lohmann
