<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT: kanonischer Speicher zwischen Vergangenheit und Zukunft

Dieses Verzeichnis enthält den reproduzierbaren Publikationskandidaten
`qikvrt-canonical-temporal-memory-effect-ack-v1`.

Die wissenschaftlich engste Kernaussage lautet:

> Im QIK-VRT Effect-Acknowledgement-Protokoll ist eine kanonisch
> repräsentierte, zukunftsindexierte Wirkungsbedingung ein nicht eliminierbarer
> und kontrafaktisch relevanter Eingang der gegenwärtigen Freigabe. Diese
> operationale Retrokausalität überschreibt keinen bestehenden
> Vergangenheitsrecord und behauptet kein rückwärts gerichtetes physikalisches
> Signal.

## Artefakte

| Datei | Rolle |
|---|---|
| `QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.pdf` | zitierfähiger 15-seitiger Working-Paper-Kandidat |
| `QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex` | reproduzierbare XeLaTeX-Quelle |
| `CLAIM_MATRIX.json` | vollständige typisierte Claim-Inventur |
| `SOURCE_EVIDENCE_BINDINGS.json` | DOI-, Standard-, Draft- und Repository-Bindungen |
| `BOUNDARY_TEST_REPORT.json` | positive und negative Modell-/Repository-Gates |
| `EVIDENCE_BOUNDARY.md` | explizite Nachweis- und Nichtnachweisgrenzen |
| `PDF_RENDER_VALIDATION.json` | Build-, Font-, Seiten- und visuelle QA-Evidenz |
| `CITATION.cff` | Zitationsmetadaten ohne vorweggenommenen DOI |
| `LICENSE_NOTICE.md` | dateibezogene Lizenzgrenzen |
| `ZENODO_FILESET.md` | vorgesehener, noch nicht autorisierter Upload-Scope |

Der formale Kern liegt in:

- `formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck/CanonicalTemporalMemory.lean`

Ein kandidaten- und Exact-Head-gebundener `KERNEL_RECEIPT.json`, ein
`PREPUBLICATION_RETURN_RECEIPT.json`, das
`MACHINE_PROOF_BUNDLE.json` und ein v2-`publish-request.json` werden erst nach
den zugehörigen Gates materialisiert. Ihr Fehlen im Kandidatenstadium ist
fail-closed und keine Publikationsbehauptung.

## PDF reproduzieren

Vom Publikationsverzeichnis:

```sh
xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex
xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex
xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex
```

Der gespeicherte PDF-Kandidat wird zusätzlich mit Poppler vollständig in
Seitenbilder gerendert und jede Seite auf Schnitt, Überlagerung,
Schriftlesbarkeit, Tabellenumbruch und Leerseiten geprüft.

## Veröffentlichungsstatus

Der momentane Zustand ist `CANDIDATE_PREPUBLICATION`.

- kein Zenodo-DOI wird vorweggenommen;
- kein IETF-Portalupdate wird vorweggenommen;
- kein Repository-weites `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` wird
  behauptet;
- die ontische physikalische und die panpsychistische Erweiterung bleiben
  ausdrücklich offen beziehungsweise interpretativ.

Nach einer bytegenauen Rückgabe an Ingolf Lohmann ist eine separate,
kandidatengebundene Uploadfreigabe erforderlich. Nach Veröffentlichung müssen
öffentlicher Record, öffentliche Dateien und Re-Downloads bytegenau geprüft,
in Authority und Mirror persistiert und erneut reziprok verglichen werden.
