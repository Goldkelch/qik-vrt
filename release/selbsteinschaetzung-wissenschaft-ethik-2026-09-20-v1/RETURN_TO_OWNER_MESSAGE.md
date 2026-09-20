<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->

# Exakte Zenodo-Vorlage zur menschlichen Entscheidung

Die Fassung bewahrt die vollständige Selbsteinschätzung Ingolf Lohmanns und die vollständige vorherige Codex-Ergänzung. Neu sind Zuschreibung, Quellenzugang und Aussagenregister. Sie enthält keine eigene physikalische Beweisführung oder empirische Vergleichsstudie. Die PDF und das wissenschaftliche Prüfpaket wurden am 2026-09-20T08:02:56.954Z mit sichtbarem Änderungsvermerk über ChatGPT Work zurückgeliefert. Die bereits erteilte Autorisierung erkenntnis-20260920-v1-05d27257 bindet ausschließlich den früheren Dateisatz und bleibt davon unberührt.

Die bestehende Richtlinie `policy/zenodo-machine-proof-policy-v2.json` verlangt nach dieser Rücklieferung eine gesonderte kanonische Freigabe. Der folgende Text ist ausschließlich eine vorbereitete Entscheidungszeile; er wurde nicht vom Menschen ausgegeben.

```text
AUTHORIZE_EXACT_UPLOAD authorization_id=selbsteinschaetzung-20260920-v1-2cd162f9 publication_id=qikvrt-selbsteinschaetzung-wissenschaft-ethik-2026-09-20-v1 return_sha256=475f3afa7d21369e6380c14e70eb7f7e3bbaca76034b7e491996c23058802ed9 metadata_sha256=a3d89aa656ac50757b452d9b7413daa7e7692596b027ff13b8a32d0909fd8065 machine_proof_sha256=95da6ace539dfce85689567e639ea5a96c134e17ffb01234d81d1be67f1a70ac
```

## Exakter Kandidat

- Publication-ID: `qikvrt-selbsteinschaetzung-wissenschaft-ethik-2026-09-20-v1`
- Upload-Dateien: 15
- Gesamtumfang: 136691 Bytes
- Aggregat-SHA-256: `e09ea7b39b084eb42491a9a6219f35d7da677c79f1210872dff791bee871598d`
- Vollständiges Inventar: `FROZEN_UPLOAD_CANDIDATE.json`
- Metadaten: `ZENODO_METADATA_DRAFT.json` (kanonischer SHA-256: `a3d89aa656ac50757b452d9b7413daa7e7692596b027ff13b8a32d0909fd8065`)

Die Metadaten enthalten zusätzlich das technisch erforderliche Feld `prereserve_doi: true`; dies reserviert durch die Vorbereitung allein keinen DOI. Die Entscheidung bindet die hier gezeigten vollständigen Metadaten.

## Fortsetzung

Nach einer tatsächlichen Freigabe die Repository-Quellversion erneut prüfen, die unveränderten Kandidatenbytes an den Vorautorisierungs-Commit binden und auf einem Nachfolge-Commit `OWNER_ZENODO_AUTHORIZATION.json` sowie `publish-request.json` nach dem bestehenden v2-Schema materialisieren. Ausschließlich der vorhandene `tools/qikvrt_zenodo_publish.py` führt nach seinen Gates den globalen Einmalverbrauch, Upload, die Veröffentlichung und öffentliche Byte-Rückprüfung aus. Anschließend sind Authority- und Mirror-Nachweise zu persistieren.

Keine Produktionsmutation wurde ausgeführt. Ein erfolgreiches technisches Proof-Gate ersetzt die offene menschliche Entscheidung nicht. Native GitHub-Review-, Merge- und Mirror-Zustände bleiben gesonderte Nachweise.
