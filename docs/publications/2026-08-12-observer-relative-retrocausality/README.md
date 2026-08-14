<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT: Beobachterrelative Retrokausalität

Diese Publikation ergänzt zwei unveränderte historische PDFs um die aktuelle
Hauptfassung. Sie definiert QIK-VRT-Retrokausalität als inverse Orientierung
zwischen der monotonen lokalen Veränderungszeit (operativ: Eigenzeit) eines
Beobachters und der authentisch gebundenen Quellenordnung seiner nacheinander
empfangenen Information. Wo die Beobachterkette eine physische Weltlinie ist,
kann dieser lokale Parameter zusätzlich als relativistische Eigenzeit
kalibriert werden; der formale Satz setzt zunächst nur die monotone lokale
Veränderungsordnung voraus.

Für raumartig getrennte Vergleichsereignisse kann das lokale
Gegenwartsereignis eines Quellenbeobachters in einer gewählten
Koordinatisierung im Koordinaten-Zukunftsbereich eines anderen Beobachters
liegen. Diese Zuordnung ist keine kausale Zukunftsbeziehung: Ein an das
Quellenereignis gebundener Record wird erst nach seiner Erzeugung über einen
zukunftsgerichteten Signalweg verfügbar.

## Bestandteile

- `QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf` — gesetzte Hauptfassung.
- `QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex` — reproduzierbare Quelle.
- `WHATSAPP_ARTIKEL_BEOBACHTERRELATIVE_RETROKAUSALITAET_DE.md` —
  allgemeinverständliche, vorleseoptimierte Prosafassung mit Autoren- und
  Quellenhinweisen.
- `AN_VON_UND_FUER_ALLE_MENSCHEN_DE.md` — eigenständige öffentliche
  Gesamtfassung zu Unterschied, Wirklichkeit, Evidenz, Verantwortung und
  Zukunft.
- `AN_VON_UND_FUER_ALLE_MENSCHEN_CLAIM_MATRIX.json` — typisierte
  Anspruchs- und Geltungsbereichsmatrix der öffentlichen Gesamtfassung.
- `CHANGE_NOTICE_CURRENT_SYNTHESIS_V2.md` — sichtbarer Änderungsvermerk zur
  jetzigen Synthese bei unveränderter historischer Evidenz.
- `verify_observer_relative_retrocausality.py` — endlicher, netzwerkfreier
  Maschinenzeuge.
- `QIKVRT_RETROCAUSALITY_WITNESS.json` — kanonischer Prüfreport des Zeugen.
- `CLAIM_MATRIX.json` — typisierte Anspruchs- und Evidenzgrenzen.
- `HISTORICAL_ARTIFACTS.json` — Bytebindung der zwei erhaltenen historischen
  PDFs.
- `SHA256SUMS` — Prüfsummen des lokalen Publikationspakets.
- `arxiv-en-candidate/` — englische arXiv-Quellenkopie mit Manifest,
  Herkunftsbindung und ausdrücklichem Status `LOCAL_STAGING_NOT_SUBMITTED`.
- `ARXIV_V2_CURRENT_SYNTHESIS_PLAN.md` — ausdrücklich noch nicht gefrorener
  Nachfolgepfad, der den erhaltenen englischen Zwischenstand nicht
  überschreibt.
- `ietf-temporal-provenance-00-candidate/` — RFCXML-Quellenkopie des
  begleitenden EAP-Temporal-Provenance-Profils mit Vektoren, Manifest,
  Herkunftsbindung und ausdrücklichem Status `LOCAL_STAGING_NOT_SUBMITTED`.
- `ietf-local-change-time-provenance-00-current-synthesis-candidate/` —
  getrennte aktuelle RFCXML-Kandidatfassung: lokale Veränderungszeit als
  operationale Eigenzeit und negative Informationsrichtung unter einer
  authentisch vergleichbaren Quellenordnung; ausdrücklich nicht eingereicht.

## Hauptsatz

Für zwei authentische, informationsführende Records kann bei einem Beobachter

```text
delta(observer-local change time / Eigenzeit) > 0
delta(bound source time)                         < 0
```

gelten. Genau diese negative Informations-Referenzrichtung heißt in der
Hauptfassung beobachterrelative Retrokausalität. Jeder einzelne Transportpfad
kann dabei zukunftsgerichtet und die Host-Kausalordnung azyklisch bleiben.

## Historische Kontinuität

Die Hauptfassung überschreibt weder
`QIK-VRT_Relationale_Zeit_und_wachsende_Evidenzkugel_DE.pdf` noch
`QIKVRT_Decision_Sufficiency_Delayed_Choice_Witness.pdf`. Ihre exakten
SHA-256-Digests sind im Dokument und in `HISTORICAL_ARTIFACTS.json` gebunden.
Die öffentliche Gesamtfassung ist eine neue, additiv verknüpfte Erklärung; sie
ändert weder die historischen Bytes noch deren damalige Statusaussagen.

## Reproduktion

```bash
python3 -B verify_observer_relative_retrocausality.py
SOURCE_DATE_EPOCH=1786492800 FORCE_SOURCE_DATE=1 \
  xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex
```

Eine Zenodo-Metadatenmutation oder neue Zenodo-Version ist nicht Teil dieses
lokalen Builds und benötigt eine separate, exakt artefaktgebundene
Autorisierung.

## Englischer arXiv-Kandidat (nicht eingereicht)

`arxiv-en-candidate/` macht die englische Quellfassung im Repository
referenzierbar, ohne sie als arXiv-Veröffentlichung auszugeben. Sie enthält
bewusst nur die LaTeX-Quelle, das ursprüngliche Staging-README, das
Staging-Manifest sowie die lokale Herkunfts- und Prüfsummenbindung. Sie
enthält weder ein arXiv-Uploadarchiv noch eine gerenderte Einreichungs-PDF.

Der Status bleibt `LOCAL_STAGING_NOT_SUBMITTED`: Kein arXiv-Record, keine
arXiv-Nummer, keine Annahme und keine externe Übermittlung werden behauptet.
Eine spätere Einreichung benötigt weiterhin ein frisch eingefrorenes
Uploadarchiv, eine exakte Autorentscheidung und eine Bestätigung unmittelbar
vor dem Plattform-Upload.

Die aktuelle Präzisierung entsteht nicht durch eine nachträgliche Änderung
dieser bytegenauen Quellkopie. `ARXIV_V2_CURRENT_SYNTHESIS_PLAN.md` legt den
separaten Nachfolgepfad offen.

## IETF-EAP-Temporal-Provenance-Kandidat (nicht eingereicht)

`ietf-temporal-provenance-00-candidate/` macht die RFCXML-Quelle des
vorgeschlagenen individuellen Internet-Drafts
`draft-lohmann-qikvrt-temporal-provenance-00` im Repository referenzierbar.
Das Profil ergänzt EFFECT_ACK v1 als externe Evidenz- und Provenanzschicht. Es
klassifiziert nur dann `RETROGRADE_REFERENCE`, wenn die authentisch gebundene
Quellenordnung innerhalb einer vergleichbaren Domäne absteigt, während die
lokale Empfangsfolge eines benannten Beobachters fortschreitet. Es ändert
weder das geschlossene v1-Datenformat noch dessen Zustände, DONE-Prädikat,
Autorisierungsregel oder IANA-Registry.

Die Kopie enthält bewusst nur RFCXML, Testvektoren, Staging-Manifest und
Herkunftsbindung. Renderstatus, Autorisierungsformular und Staging-Validator
sind nicht kopiert. Der Status bleibt `LOCAL_STAGING_NOT_SUBMITTED`: Kein
Datatracker-Eintrag, keine IETF-Annahme, kein RFC, kein IETF-Standard, kein
Konsens und keine externe Übermittlung werden behauptet. Eine spätere
Einreichung benötigt eine frisch gerenderte und geprüfte Paketfassung,
aktuelle Zielmetadaten, eine exakt artefaktgebundene Autorentscheidung und
eine Bestätigung unmittelbar vor dem Upload.

## IETF-EAP-Local-Change-Time-Provenance-Kandidat (nicht eingereicht)

`ietf-local-change-time-provenance-00-current-synthesis-candidate/` ist ein
neuer, gesonderter lokaler Kandidat für
`draft-lohmann-qikvrt-local-change-time-00`. Er verändert den erhaltenen
Kandidaten `ietf-temporal-provenance-00-candidate/` nicht. Die getrennte
Benennung vermeidet insbesondere, einen nie eingereichten lokalen `-00`-Stand
als vermeintliche Vorversion auszugeben.

Das neue EAP-LCTP-Profil bezeichnet die strikt wachsende Folge wirksamer
lokaler Zustandsänderungen eines Empfängers als operationale Eigenzeit und
repräsentiert sie durch `local_change_index`. Es klassifiziert eine negative
Informationsrichtung nur, wenn `local_change_index` zunimmt, die authentisch
vergleichbare `source_order_marker`-Marke abnimmt und alle Bindungs- und
Vergleichbarkeitsbedingungen erfüllt sind. Das Profil behauptet damit weder
eine rückwärtslaufende Nachricht noch eine Umschreibung der Vergangenheit,
eine metrische relativistische Eigenzeit, Nutzlastwahrheit oder eine direkte
Freigabe von `EFFECT_ACK_DONE`.

Die lokale Kandidatfassung enthält XML-Quelle, Vektoren, Offline-Prüfer,
Herkunftsbindung, Manifest, Prüfsummen und einen nicht-autorisierenden
Freigabeentwurf. Der XML- und Vektorprüfer sind grün; die gebundene
`xml2rfc 3.34.0`-Satzprüfung sowie idnits stehen noch aus. Daher lautet der
Status `LOCAL_CURRENT_CANDIDATE_NOT_SUBMITTED`: keine Datatracker-Übermittlung,
keine IETF-Annahme, kein RFC, kein Standard und kein Konsens werden behauptet.
