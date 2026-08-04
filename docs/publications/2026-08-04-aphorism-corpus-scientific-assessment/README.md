# QIK-VRT Aphorismen-Audiokorpus - Wissenschaftliche Einordnung v2

Diese Version ersetzt die lokale v1-Fassung. Sie bindet sieben originale M4A-Dateien per SHA-256, zwei automatische ASR-Pässe mit einer verifizierten Repository-Runtime, vier historische GitHub-ASR-Artefakte, eine korrigierte wissenschaftliche Einordnung, eine allgemein verständliche Fassung, ein falsifizierbares Hypothesenprogramm, ein LaTeX/PDF-Dokument und maschinenlesbare Verifikationsgrenzen.

## Kernstatus

```text
AUTOMATIC_ASR_TWO_PASS = 7/7
GITHUB_TERMINAL_DERIVATIVE_ASR = 4/7
HUMAN_ACOUSTIC_VERBATIM_CERTIFICATION = 0/7
REPOSITORY_PDF_RENDER = MATERIALIZER_REQUIRED
PHYSICAL_RETROCAUSALITY = NOT_ESTABLISHED
PAST_EVENT_MUTATION = NOT_ESTABLISHED
IETF_PROTOCOL_CHANGE = NOT_REQUIRED
ZENODO_EFFECT = NOT_AUTHORIZED
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
```

## Einstieg

- `PUBLIC_SUMMARY_DE.md` - allgemein verständliche Fassung
- `SCIENTIFIC_ASSESSMENT_DE.md` - fachliche Einzelbewertung
- `CORRECTION_NOTICE.md` - sichtbare Korrektur der v1-Fehlzuordnungen
- `ASR_LEDGER.json` - beide automatischen Pässe und Unsicherheiten
- `CLAIM_MATRIX.json` - epistemische Klassifikation
- `HYPOTHESIS_PROGRAM.json` - sieben falsifizierbare Folgeprogramme
- `QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.pdf` - repository-nativ gerendertes wissenschaftliches Dokument
- `verify_bundle.py` - lokale Integritäts- und Boundary-Prüfung

## Nicht enthalten

Die Originalaudios werden nicht als gewöhnliche Repository-Dateien veröffentlicht. Ihre exakten Dateinamen, Bytezahlen und SHA-256-Identitäten stehen in `SOURCE_AUDIO_INDEX.json`. Menschliche akustische Wortlautfreigabe bleibt eine gesonderte Aufgabe.

## Repository-Materialisierung

Das Bündel wird deterministisch durch `tools/qikvrt_aphorism_corpus_v2.py` erzeugt. Das Poster selbst wird nicht als neues Binärartefakt dupliziert; seine exakte lokale SHA-256-Bindung und die wissenschaftliche Begleitcaption bleiben in `POSTER_ALIGNMENT_DE.md` und `SOURCE_AUDIO_INDEX.json` erhalten. Die repository-native PDF-Fassung verwendet an dieser Stelle ein textuelles Schema.
