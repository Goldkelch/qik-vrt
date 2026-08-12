<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Vorgesehener exakter Zenodo-v2-Dateisatz

Publication ID: `qikvrt-observer-relative-retrocausality-current-synthesis-v2`

Die Datei `FROZEN_UPLOAD_CANDIDATE.json` bindet die derzeit eingefrorenen
Primär- und Ergänzungsdateien mit Größe, SHA-256 und Git-Blob-ID. Der spätere
Produktionsmanifest darf nur diesen Satz **zuzüglich** der nach der sichtbaren
Rückgabe zu erzeugenden v2-Pflichtdateien enthalten:

Der gefrorene Satz enthält auch `CITATION.cff`, die gemischte Lizenznotiz sowie
beide vollständigen Lizenztexte.

- `MACHINE_PROOF_BUNDLE.json`;
- `PREPUBLICATION_RETURN_RECEIPT.json`;
- den endgültigen `publish-request.json` und die repositoryseitige
  `OWNER_ZENODO_AUTHORIZATION.json` (nicht als Uploaddateien);
- einen nach Produktionsausführung erzeugten `zenodo-publication.json`
  (nicht als Uploaddatei).

Die heutigen `*_DRAFT.json`-Dateien machen ausschließlich die noch fehlenden
Abhängigkeiten sichtbar. Sie dürfen nicht als Produktionsmanifest,
Proof-Bundle, Rückgabequittung oder Autorisierung ausgegeben werden.

Die bestehenden historischen PDFs müssen für den Nachfolger nicht dupliziert
werden: Ihre unveränderte Identität ist im Kandidaten durch
`HISTORICAL_ARTIFACTS.json` dokumentiert und der bestehende Zenodo-Record wird
über DOI referenziert.
