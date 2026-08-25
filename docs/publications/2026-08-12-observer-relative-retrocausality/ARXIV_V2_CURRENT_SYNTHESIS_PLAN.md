<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# arXiv-Nachfolgepfad – aktuelle Synthese v2

Status: **`LOCAL_STAGING_READY_FOR_TARGET_REOBSERVATION_NOT_SUBMITTED`**.

## Editionsentscheidung

`arxiv-en-candidate/` bleibt der bytegenau gebundene englische
Zwischenstand. Sein Manifest beschreibt einen bereits gefrorenen lokalen
Staging-Kandidaten. Eine Änderung von `main.tex` an diesem Ort würde diese
historische Aussage nachträglich verfälschen.

Die aktuelle Fassung wird deshalb als **neuer Nachfolgepfad** vorbereitet und
nicht als unmarkierte Überschreibung ausgegeben.

## Aktuelle inhaltliche Grundlage

Die künftige englische Fassung muss mindestens die jetzt geklärten Punkte
enthalten:

1. QIK-VRT-Eigenzeit bezeichnet zunächst die monotone lokale
   Veränderungszeit eines Beobachters; bei einer physischen Weltlinie kann sie
   zusätzlich an metrische Eigenzeit kalibriert werden.
2. Die negative Informationsrichtung ist die Relation
   `Δτ_R > 0` und `Δθ < 0` zwischen lokaler Veränderungszeit und
   provenancegebundener Quellenordnung.
3. Die öffentliche Gesamterklärung `AN_VON_UND_FUER_ALLE_MENSCHEN_DE.md`
   ergänzt den formalen Text um Unterschied, Evidenz, Verantwortung und
   Zukunft, ohne diese normativen Sätze als Naturgesetz auszugeben.
4. Vorherige Zwischenstände, insbesondere `arxiv-en-candidate/`, bleiben
   unverändert und ausdrücklich referenzierbar.

## Vorbereitete Nachfolgeartefakte

Die neue Quelle und ihre eigene Provenienz liegen unter
`arxiv-en-current-synthesis-v2/`. Das minimal deterministische Uploadarchiv
liegt getrennt in
`publication-staging/arxiv-observer-relative-retrocausality-en-v2/`:

| Artefakt | SHA-256 |
|---|---|
| `arxiv-source.tar.gz` | `5202c13e8a9e4934de0c09b7f238fc80073410c5d52ef231e0c05d035c00322a` |
| daraus gebautes `main.pdf` | `943331e2297b9663b02471d51d9adcb277f191fafb1e9d15f8ef2ba63730b12c` |

Das Uploadarchiv enthält nur die selbständige `main.tex`; die README- und
Provenienzdateien bleiben außerhalb des arXiv-Uploads erhalten. Der Satz- und
Sichtprüflauf ist erfolgreich; ein frisches Entpacken des Archivs und derselbe
Zwei-Pass-Lauf erzeugten ein byteidentisches PDF. Das Manifest enthält die
vorgeschlagenen Kategorien `cs.DC`, `cs.LO` und `cs.CR`, aber keine
unzulässige Behauptung eines eigenständigen `quant-ph`-Resultats. Die genaue
Lizenzoption des Zielsystems bleibt absichtlich erst im aktuellen arXiv-Formular
zu bestätigen.

## Vor einer tatsächlichen Übermittlung weiter erforderlich

- frische Beobachtung des arXiv-Kontos und aller Zielfelder;
- Bindung der so beobachteten Felder an den oben genannten Archivhash in der
  Autorenentscheidung;
- Bestätigung unmittelbar vor der Übermittlung;
- unabhängige Kontrolle des zurückgegebenen arXiv-Receipts.

Die neue Fassung ist damit lokal eingefroren und einreichungsbereit, aber noch
nicht bei arXiv eingereicht. Es existieren daher weiterhin keine
arXiv-Nummer, keine Annahme und keine externe Wirkung dieser aktuellen
Synthese.
