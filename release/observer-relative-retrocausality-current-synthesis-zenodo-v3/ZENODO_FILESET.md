<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Exakter v3-Uploaddateisatz

`PUBLISH_REQUEST_DRAFT.json` ist die maschinenlesbare Quelle für Reihenfolge,
Zenodo-Namen, Bytes, SHA-256 und Git-Blobs.

- Position 1–17: öffentliche Kandidaten;
- Position 18–22: Claim-Matrix, Quellenbindungen, Grenztest,
  Änderungsvermerk und Return-Receipt;
- Position 23: `MACHINE_PROOF_BUNDLE.json`.

Nicht im Upload: Vorbereitung, Finalizer, Entwürfe, Gate-Status,
`SHA256SUMS`, Work-Unit, spätere Owner-Autorisierung, Produktionsmanifest,
Workflow und Publikationsreceipt.

Die Quell-M4A ist `UNTRANSCRIBED`. Die Textdatei ist
`OWNER_SUPPLIED_CANONICAL_TEXT`, nicht ASR und nicht akustisch als Wortlaut
bestätigt.
