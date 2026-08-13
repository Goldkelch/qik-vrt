<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT: Beobachterrelative Retrokausalität

Diese Publikation ergänzt zwei unveränderte historische PDFs um die aktuelle
Hauptfassung. Sie definiert QIK-VRT-Retrokausalität als inverse Orientierung
zwischen der monotonen Eigenzeit eines Beobachters und der authentisch
gebundenen Quellenordnung seiner nacheinander empfangenen Information.

## Bestandteile

- `QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf` — gesetzte Hauptfassung.
- `QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex` — reproduzierbare Quelle.
- `WHATSAPP_ARTIKEL_BEOBACHTERRELATIVE_RETROKAUSALITAET_DE.md` —
  allgemeinverständliche, vorleseoptimierte Prosafassung mit Autoren- und
  Quellenhinweisen.
- `verify_observer_relative_retrocausality.py` — endlicher, netzwerkfreier
  Maschinenzeuge.
- `QIKVRT_RETROCAUSALITY_WITNESS.json` — kanonischer Prüfreport des Zeugen.
- `CLAIM_MATRIX.json` — typisierte Anspruchs- und Evidenzgrenzen.
- `HISTORICAL_ARTIFACTS.json` — Bytebindung der zwei erhaltenen historischen
  PDFs.
- `SHA256SUMS` — Prüfsummen des lokalen Publikationspakets.
- `arxiv-en-candidate/` — englische arXiv-Quellenkopie mit Manifest,
  Herkunftsbindung und ausdrücklichem Status `LOCAL_STAGING_NOT_SUBMITTED`.
- `ietf-temporal-provenance-00-candidate/` — RFCXML-Quellenkopie des
  begleitenden EAP-Temporal-Provenance-Profils mit Vektoren, Manifest,
  Herkunftsbindung und ausdrücklichem Status `LOCAL_STAGING_NOT_SUBMITTED`.

## Hauptsatz

Für zwei authentische, informationsführende Records kann bei einem Beobachter

```text
delta(observer proper time) > 0
delta(bound source time)    < 0
```

gelten. Genau diese negative Informations-Referenzrichtung heißt in der
Hauptfassung beobachterrelative Retrokausalität. Jeder einzelne Transportpfad
kann dabei zukunftsgerichtet und die Host-Kausalordnung azyklisch bleiben.

## Historische Kontinuität

Die Hauptfassung überschreibt weder
`QIK-VRT_Relationale_Zeit_und_wachsende_Evidenzkugel_DE.pdf` noch
`QIKVRT_Decision_Sufficiency_Delayed_Choice_Witness.pdf`. Ihre exakten
SHA-256-Digests sind im Dokument und in `HISTORICAL_ARTIFACTS.json` gebunden.

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
