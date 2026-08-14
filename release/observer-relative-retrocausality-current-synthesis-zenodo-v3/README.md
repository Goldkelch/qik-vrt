<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Zenodo-v3-Nachfolgesatz: beobachterrelative Retrokausalität mit autorenseitigem Audio/Text-Supplement

**Publication ID:** `qikvrt-observer-relative-retrocausality-current-synthesis-v3`

Dieser Nachfolgesatz bewahrt den wissenschaftlichen Kern des unpublizierten,
exakt gebundenen v2-Satzes unverändert und ergänzt zwei öffentliche
autorenseitige Artefakte:

1. die bereitgestellte M4A-Datei;
2. die sichtbar materialisierte Textfassung.

Die v3-Quellenbindung bindet beide Artefakte zusätzlich über Pfad, Bytes,
SHA-256 und Git-Blob sowie die Mediengrenze der Aufnahme.

Die Textfassung ist `OWNER_SUPPLIED_CANONICAL_TEXT`, kein ASR-Ergebnis. Eine
akustische Wortlautprüfung wurde nicht durchgeführt; die Text-Audio-
Korrespondenz bleibt ausdrücklich `UNVERIFIED`. Aus dem Inhalt werden weder ein
neuer empirischer Energienachweis noch ein naturwissenschaftlicher Beweis oder
wissenschaftlicher Konsens abgeleitet.

Der prooftragende v3-Uploaddateisatz umfasst exakt 23 Pfade: 17 öffentliche
Kandidaten, fünf Proof-/Return-Artefakte und das Machine-Proof-Bundle selbst.
Die v2-Steuerung und ihre einmalige Autorisierung bleiben unverändert und
werden von v3 weder verbraucht noch ersetzt.

## Status

`V3_PREAUTHORIZATION_SOURCE_CANDIDATE_EXACT_EFFECT_AUTHORIZATION_PENDING`

Das im Eigentümertext enthaltene Wort „Freigabe“ ist Bestandteil des
öffentlichen Inhalts. Es ist nicht die hashgebundene Einmalautorisierung des
Produktions-Publishers. Nach Commit und sichtbarer Rückgabe der exakten
v3-Receipt-, Metadaten- und Machine-Proof-Hashes ist eine neue kanonische
`AUTHORIZE_EXACT_UPLOAD`-Entscheidung erforderlich. Vorher dürfen weder
`OWNER_ZENODO_AUTHORIZATION.json` noch `publish-request.json` oder ein
produktiver v3-Workflow erzeugt werden.

## Lokale Prüfung

```bash
python3 -B release/observer-relative-retrocausality-current-synthesis-zenodo-v3/assemble_successor_package.py --check
python3 -B tools/qikvrt_zenodo_machine_proof.py \
  --proof-bundle release/observer-relative-retrocausality-current-synthesis-zenodo-v3/MACHINE_PROOF_BUNDLE.json \
  $(jq -r '.exact_upload_paths[] | "--upload-path " + @sh' release/observer-relative-retrocausality-current-synthesis-zenodo-v3/PUBLISH_REQUEST_DRAFT.json)
```

Beide Pfade sind lokal und effektfrei.
