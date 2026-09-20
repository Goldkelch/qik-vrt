<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->

# Exakte Zenodo-Vorlage zur menschlichen Entscheidung

Die Fassung dokumentiert Erkenntnis durch Präzisierung und Korrektur. Der Monolithen-Vergleich ist eine Interpretation. Sie enthält keinen Raumzeit- oder Superdeterminismus-Beweis. Die PDF und das wissenschaftliche Prüfpaket wurden am 2026-09-20T07:00:17.044Z mit sichtbarem Änderungsvermerk über ChatGPT Work zurückgeliefert.

Die bestehende Richtlinie `policy/zenodo-machine-proof-policy-v2.json` verlangt nach dieser Rücklieferung eine gesonderte kanonische Freigabe. Der folgende Text ist ausschließlich eine vorbereitete Entscheidungszeile; er wurde nicht vom Menschen ausgegeben.

```text
AUTHORIZE_EXACT_UPLOAD authorization_id=erkenntnis-20260920-v1-05d27257 publication_id=qikvrt-schrittweise-erkenntnis-2026-09-20-v1 return_sha256=63765ef9fd18d4f59e5d4141c501873d289d7bc986101a9fe74783a563bc097f metadata_sha256=bc1e769a7daba366cf6c9b79422e559d94b50767afb9cc39f7c6bacd3003f7ea machine_proof_sha256=d735cd3ed5eaa16691a4d3cf43eaf38ee29fe91e00fd4e369945410f63ed219c
```

## Exakter Kandidat

- Publication-ID: `qikvrt-schrittweise-erkenntnis-2026-09-20-v1`
- Upload-Dateien: 13
- Gesamtumfang: 104667 Bytes
- Aggregat-SHA-256: `a05a1bac46de5601dc1cd9358c0c1b2f4aae0302a2b141968afc47f95b4bfeaf`
- Vollständiges Inventar: `FROZEN_UPLOAD_CANDIDATE.json`
- Metadaten: `ZENODO_METADATA_DRAFT.json` (kanonischer SHA-256: `bc1e769a7daba366cf6c9b79422e559d94b50767afb9cc39f7c6bacd3003f7ea`)

Die Metadaten enthalten zusätzlich das technisch erforderliche Feld `prereserve_doi: true`; dies reserviert durch die Vorbereitung allein keinen DOI. Die Entscheidung bindet die hier gezeigten vollständigen Metadaten.

## Fortsetzung

Nach einer tatsächlichen Freigabe die Repository-Quellversion erneut prüfen, die unveränderten Kandidatenbytes an den Vorautorisierungs-Commit binden und auf einem Nachfolge-Commit `OWNER_ZENODO_AUTHORIZATION.json` sowie `publish-request.json` nach dem bestehenden v2-Schema materialisieren. Ausschließlich der vorhandene `tools/qikvrt_zenodo_publish.py` führt nach seinen Gates den globalen Einmalverbrauch, Upload, die Veröffentlichung und öffentliche Byte-Rückprüfung aus. Anschließend sind Authority- und Mirror-Nachweise zu persistieren.

Keine Produktionsmutation wurde ausgeführt. Ein erfolgreiches technisches Proof-Gate ersetzt die offene menschliche Entscheidung nicht. Native GitHub-Review-, Merge- und Mirror-Zustände bleiben gesonderte Nachweise.
