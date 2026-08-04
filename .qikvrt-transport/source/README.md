# Prä-raumzeitliche Ontologie der Unterscheidung

## Publikationsidentität

```text
publication_id = qikvrt-pre-spacetime-ontology-20260804-v1
```

## Enthaltene Dateien

### Wissenschaftliche Grundfassung

- `PAPER.tex` - wissenschaftliches LaTeX-Dokument
- `REFERENCES.bib` - zitierte Primärliteratur als BibTeX-Datenbank
- `WHATSAPP_READALOUD.md` - WhatsApp-optimierte Vorlesefassung für Kinder und Erwachsene

### Epistemische Dreierbeziehung und Abbildungen

- `FIGURE_ORIGINAL_SKETCH.jpeg` - exakt gebundene, vom Product Owner übermittelte Handskizze
- `FIGURE_PROFESSIONAL_POSTER.jpeg` - exakt gebundene professionelle Erläuterungsabbildung
- `SOURCE_FIGURE_INDEX.json` - Byte-, Digest-, Rollen- und Provenienzbindung
- `EPISTEMIC_TRIAD_DE.md` - wissenschaftliche und allgemein verständliche Einordnung
- `CLAIM_MATRIX.json` - typisierte Claims und Dispositionen
- `EVIDENCE_BOUNDARY.md` - Evidenz-, Wahrheits- und Kausalitätsgrenzen
- `NEGATIVE_AND_BOUNDARY_TESTS.json` - Gegenmodelle gegen überstarke Lesarten

### Routing

- `PUBLICATION_ROUTING.json` - hashgebundene Routingentscheidung
- `ZENODO_CANDIDATE.json` - staged Zenodo-Artikelkandidat ohne Publikationseffekt
- `IETF_DISPOSITION.json` - begründete Nicht-Submission als eigenständiger Internet-Draft

## Zentraler methodischer Grundsatz

> „Prä-raumzeitlich“ bezeichnet eine Ordnung der Erklärungsabhängigkeit, nicht ein zeitliches Davor in einem bereits vorhandenen Raum.

Für die epistemische Dreierbeziehung gilt:

```text
WIRKLICHKEIT
-> SELEKTIVE_WAHRNEHMUNG
-> INTERNES_MODELL
-> SPRACHLICHE_AUSSAGE
```

aber:

```text
KOHÄRENZ_VON_WELTBEZUG_MODELL_AUSSAGE
!= AUTOMATISCHE_WAHRHEITSGARANTIE
```

Die Formulierung „3 ist gut“ bleibt eine anschauliche Heuristik. Wahrheit wird zusätzlich gegen Beobachtungen, Gegenbeispiele, Fehlerquellen und alternative Modelle geprüft.

## Zeit- und Informationsgrenze

```text
FRÜHERES_EREIGNIS
-> PHYSISCHES_ARTEFAKT
-> GEGENWÄRTIGE_REZEPTION
-> MÖGLICHE_ZUKÜNFTIGE_WIRKUNG
```

Diese Kette ist vorwärts gerichtet. Sie etabliert weder eine zeitlose, trägerunabhängige Information noch physikalische Rückwärtskausalität oder Vergangenheitsmutation.

## Routinggrenzen

- Repository: neuer additiver Kandidat erst nach atomarer Source-Persistenz, deterministischer Integritätsregeneration und Exact-Head-Gates.
- Zenodo: erst nach exakter Kandidatenrückgabe, kandidaten- und hashgebundener Owner-Autorisierung, Veröffentlichung und öffentlicher Byteverifikation.
- IETF: keine eigenständige Submission, solange kein implementierbares Protokolldelta vorliegt.
- Keine Behauptung von `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`.

## Lokaler Build

```bash
latexmk -xelatex PAPER.tex
```
