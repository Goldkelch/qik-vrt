<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT / EFFECT_ACK: universalisierbare Wirkungssteuerung

Dieses reproduzierbare Working-Paper-Bündel dokumentiert die wissenschaftlich
präzisierte Konsequenz des EFFECT_ACK-Mechanismus:

- Prozessuniversalität für endliche, zugängliche Digitalartefakte in Aufnahme,
  Klassifikation, Verantwortungsbindung und vollständig mediierter
  Wirkungssteuerung;
- semantische Rekonstruktion genau bei Konstanz der Zielsemantik auf den
  Beobachtungsfasern;
- exakte historische Inversion nur bei injektiver Beobachtung;
- konditionale cyberphysische Übertragung nur bei vollständiger Mediation,
  frischer authentisierter Verbraucherprüfung, treuem Executor und empirisch
  validiertem Systemmodell.

## Inhalte

| Datei | Rolle |
|---|---|
| `QIK-VRT_EFFECT_ACK_Universalisierbare_Wirkungssteuerung_2026-07-22.pdf` | zitierfähige Working-Paper-Fassung |
| `QIK-VRT_EFFECT_ACK_Universalisierbare_Wirkungssteuerung_2026-07-22.tex` | reproduzierbare XeLaTeX-Quelle |
| `ARTICLE_DE.md` | allgemeinverständliche Langfassung in vier WhatsApp-Teilen |
| `effect_ack_universality_proof.py` | ausführbare endliche Modellprüfung |
| `proof-report.json` | maschinenlesbarer Prüfbericht |
| `inputs/` | exakt gehashte Draft-01-Eingaben |
| `EVIDENCE_BOUNDARY.md` | Nachweis- und Nichtnachweisgrenzen |
| `DRAFT_IMPACT.md` | Prüfung, ob der veröffentlichte Draft geändert werden muss |
| `IETF_RENDER_VALIDATION.json` | Offline-Validierung und bytegenauer Rendernachweis für XML, TXT und HTML |
| `CITATION.cff` | Zitationsmetadaten |
| `zenodo-deposition.json` | vorbereitete Working-Paper-Metadaten |
| `ZENODO_FILESET.md` | lizenzhomogene Dateigrenze des eigenständigen Zenodo-Records |
| `LICENSE_NOTICE.md` | dateibezogene Lizenzgrenzen |
| `SHA256SUMS` | SHA-256-Index des Bündels |

## Modellprüfung reproduzieren

Vom Repository-Wurzelverzeichnis:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  docs/publications/2026-07-22-effect-ack-universal-effect-control/effect_ack_universality_proof.py \
  --draft-txt docs/publications/2026-07-22-effect-ack-universal-effect-control/inputs/draft-lohmann-qikvrt-effect-ack-01.txt \
  --draft-xml docs/publications/2026-07-22-effect-ack-universal-effect-control/inputs/draft-lohmann-qikvrt-effect-ack-01.xml \
  --runtime src/qikvrt_effect_ack.py \
  --output /tmp/proof-report.json

cmp /tmp/proof-report.json \
  docs/publications/2026-07-22-effect-ack-universal-effect-control/proof-report.json
```

Der Prüfer muss außerdem optimierten Python-Modus ausdrücklich verweigern:

```sh
python3 -O \
  docs/publications/2026-07-22-effect-ack-universal-effect-control/effect_ack_universality_proof.py \
  --draft-txt docs/publications/2026-07-22-effect-ack-universal-effect-control/inputs/draft-lohmann-qikvrt-effect-ack-01.txt \
  --draft-xml docs/publications/2026-07-22-effect-ack-universal-effect-control/inputs/draft-lohmann-qikvrt-effect-ack-01.xml \
  --runtime src/qikvrt_effect_ack.py
```

## PDF reproduzieren

```sh
xelatex -interaction=nonstopmode -halt-on-error \
  docs/publications/2026-07-22-effect-ack-universal-effect-control/QIK-VRT_EFFECT_ACK_Universalisierbare_Wirkungssteuerung_2026-07-22.tex
```

Das veröffentlichte PDF wurde zusätzlich mit Poppler gerendert und auf
Seitenschnitt, Überlagerungen, Schriftlesbarkeit und vollständige sechs Seiten
visuell geprüft.

## Wissenschaftlicher Status

Der Prüfbericht trägt `PASS_WITH_EXPLICIT_BOUNDARIES`; die vollständige
Draft-01-Wire-Implementierung bleibt `CONTINUE_DRAFT01_WIRE_IMPLEMENTATION`.
Zenodo-Persistenz belegt Identität, Version und Fixität der veröffentlichten
Bytes. Sie ersetzt weder Peer Review noch empirische Bestätigung.

Die [Draft-Auswirkungsprüfung](DRAFT_IMPACT.md) kommt zu dem Ergebnis, dass
Revision `-01` unverändert bleiben kann. Eine spätere informative Revision
`-02` wäre möglich, ist aber weder erzeugt noch beim Datatracker eingereicht.
Die erneute Offline-Validierung mit `xml2rfc 3.34.0` war warnungsfrei; TXT und
sauberes HTML stimmen bytegenau mit den bestehenden versionierten Dateien
überein. Deshalb wurde keine inhaltsgleiche Scheinversion erzeugt. XML und TXT
stimmen außerdem mit dem offiziellen IETF-Archiv überein. Das dort ausgelieferte
HTML enthält abweichende Generator-Nebenabhängigkeiten und serverseitig
injizierten Code; diese Auslieferungsdifferenz ist im Validierungsbericht
explizit abgegrenzt.

## Zenodo-Dateigrenze

Das Repository-Bündel bleibt vollständig und gemischt lizenziert. Der
eigenständige Working-Paper-Record lädt dagegen ausschließlich die in
[`ZENODO_FILESET.md`](ZENODO_FILESET.md) benannten
`CC-BY-NC-ND-4.0`-Dateien hoch. Der PolyForm-Prüfer und die IETF-Eingaben werden
nicht umgelizenziert; sie folgen im verknüpften, getaggten Software-Snapshot.
Ein eigener `ZENODO_SHA256SUMS`-Index bindet nur die tatsächlich deponierten
Dateien.

## Verknüpfte Primärquellen

- [Working-Paper-DOI 10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773)
- [Versionierte QIK-VRT-Software DOI 10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774)
- [Internet-Draft -01](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/01/)
- [Historische QIKVRT-V8.33-Software DOI 10.5281/zenodo.20712301](https://doi.org/10.5281/zenodo.20712301)
- [Maschinenprüfbare Formalisierung DOI 10.5281/zenodo.21488116](https://doi.org/10.5281/zenodo.21488116)
- [Goldkelch-Tag v2026.07.22-effect-ack-universality-1.0.0](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
- [Ingolf-Tag v2026.07.22-effect-ack-universality-1.0.0](https://github.com/ingolf-lohmann/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
