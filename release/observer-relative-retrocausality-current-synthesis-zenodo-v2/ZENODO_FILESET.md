<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Exakter öffentlicher Zenodo-v2-Dateisatz

Publication ID: `qikvrt-observer-relative-retrocausality-current-synthesis-v2`

Die Datei `FROZEN_UPLOAD_CANDIDATE.json` bindet den derzeit eingefrorenen
öffentlichen Forschungs- und Evidenzsatz mit Größe, SHA-256 und Git-Blob-ID.
Er enthält die Hauptfassung, die reproduzierbare Quelle, den endlichen Zeugen,
die öffentliche Erklärung, Claim- und Quellenbindungen, den Nachweis der
historischen Kontinuität sowie die nötigen Lizenztexte.

Der gefrorene Satz enthält auch `CITATION.cff`, die gemischte Lizenznotiz und
beide vollständigen Lizenztexte. Er enthält **keine** Entwürfe, Freigaben,
Metadatenentwürfe, Ablaufchecklisten, Gate-Status, Policy-/Schemaquellen,
lokalen Prüfsummen oder Materialisierer.

Diese ausgeschlossenen Dateien bleiben als nachvollziehbare
Repository-Vorbereitung erhalten. Sie sind jedoch kein öffentlicher
wissenschaftlicher Uploaddateisatz. Der Kandidat ist nicht veröffentlicht;
aus diesem Verzeichnis wird weder ein Zenodo-Record, ein DOI noch ein Upload
abgeleitet.

Der prooftragende Satz ist als folgende disjunkte v2-DAG materialisiert:

- 15 der 17 zurückgegebenen Dateien sind `candidate.files`;
- `CLAIM_MATRIX_V2.json` und `SOURCE_EVIDENCE_BINDINGS.json` sind disjunkte
  Proof-Artefakte;
- der am `2026-08-13T20:13:42Z` erneut sichtbar zurückgegebene
  `CHANGE_NOTICE.md` ist ein `CHANGE_NOTICE`;
- `PREPUBLICATION_RETURN_RECEIPT.json` ist ein `RETURN_RECEIPT`;
- `BOUNDARY_TEST_REPORT.json` ist der nach der aktiven Policy erforderliche
  `BOUNDARY_TEST`;
- `MACHINE_PROOF_BUNDLE.json` wird durch den späteren Manifest selbst als
  Uploaddatei gebunden.

Der exakte Uploadsatz enthält damit **21 Dateien**. Die beiden Proof-Artefakte
bleiben Teil der unveränderten 17-Datei-Rückgabe, wechseln aber nur ihre Rolle
von `candidate.files` nach `artifacts`; es werden keine zurückgegebenen Bytes
verändert oder doppelt hochgeladen. Die sieben v1.0-Vorgänger-Snapshots sind
für die lokale Validatorprüfung materialisiert, bleiben aber repositoryseitig
und gehören nicht zu diesen 21 Uploads.

Repositoryseitig bleiben außerdem:

- den endgültigen `publish-request.json` und die repositoryseitige
  `OWNER_ZENODO_AUTHORIZATION.json` (nicht als Uploaddateien);
- einen nach Produktionsausführung erzeugten `zenodo-publication.json`
  (nicht als Uploaddatei).

Die `*_DRAFT.json`-Dateien machen ausschließlich historische bzw. noch
fehlende Steuerungsabhängigkeiten sichtbar. Sie dürfen nicht als
Produktionsmanifest, Proof-Bundle, Rückgabequittung, Autorisierung oder
Uploaddatei ausgegeben werden. Dasselbe gilt für die repositoryseitigen
Vorversions-Snapshots unter `original-candidate-47510c8/`.

Die bestehenden historischen PDFs müssen für den Nachfolger nicht dupliziert
werden: Ihre unveränderte Identität ist im Kandidaten durch
`HISTORICAL_ARTIFACTS.json` dokumentiert und der bestehende Zenodo-Record wird
über DOI referenziert.
