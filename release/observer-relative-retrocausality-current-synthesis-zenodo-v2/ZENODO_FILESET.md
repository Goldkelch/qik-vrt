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

Ein späterer Produktionsmanifest darf nur diesen Satz **zuzüglich** der nach
der sichtbaren Rückgabe zu erzeugenden v2-Pflichtdateien enthalten:

- `MACHINE_PROOF_BUNDLE.json`;
- `PREPUBLICATION_RETURN_RECEIPT.json`;
- den endgültigen `publish-request.json` und die repositoryseitige
  `OWNER_ZENODO_AUTHORIZATION.json` (nicht als Uploaddateien);
- einen nach Produktionsausführung erzeugten `zenodo-publication.json`
  (nicht als Uploaddatei).

Die heutigen `*_DRAFT.json`-Dateien machen ausschließlich die noch fehlenden
Abhängigkeiten sichtbar. Sie dürfen nicht als Produktionsmanifest,
Proof-Bundle, Rückgabequittung, Autorisierung oder Uploaddatei ausgegeben
werden.

Die bestehenden historischen PDFs müssen für den Nachfolger nicht dupliziert
werden: Ihre unveränderte Identität ist im Kandidaten durch
`HISTORICAL_ARTIFACTS.json` dokumentiert und der bestehende Zenodo-Record wird
über DOI referenziert.
