# Prä-raumzeitliche Ontologie der Unterscheidung

## Enthaltene Dateien

- `PAPER.tex` — wissenschaftliches LaTeX-Dokument
- `REFERENCES.bib` — zitierte Primärliteratur als BibTeX-Datenbank
- `WHATSAPP_READALOUD.md` — WhatsApp-optimierte Vorlesefassung für Kinder und Erwachsene
- `PUBLICATION_ROUTING.json` — hashgebundene Routingentscheidung
- `ZENODO_CANDIDATE.json` — staged Zenodo-Artikelkandidat ohne Publikationseffekt
- `IETF_DISPOSITION.json` — begründete Nicht-Submission als eigenständiger Internet-Draft

## Zentraler methodischer Grundsatz

> „Prä-raumzeitlich“ bezeichnet eine Ordnung der Erklärungsabhängigkeit, nicht ein zeitliches Davor in einem bereits vorhandenen Raum.

Das Dokument trennt formale Sätze, empirische Evidenz, Modellannahmen, offene Fragen, normative Brücken und quellengebundene Aussagen. Fragen nach Gott, Seele, Jenseits, Telepathie und Sinn werden weder spöttisch wegdefiniert noch ohne Evidenz als Wissen ausgegeben.

## Routinggrenzen

- Repository: Kandidat nach Review und Exact-Head-Gates.
- Zenodo: als Artikel geeignet, aber nur durch einen separaten, expliziten und hashgebundenen Publikationsrequest.
- IETF: keine eigenständige Submission, solange kein implementierbares Protokolldelta vorliegt.
- Keine Behauptung von `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`.

## Lokaler Build

```bash
latexmk -xelatex PAPER.tex
```
