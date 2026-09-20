<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->

# QIK-VRT Roundtrip – statischer Snapshot v2

[HTML herunterladen und lokal öffnen](QIKVRT_Roundtrip_2026-09-20_v2.html) · [Dateibindung](SNAPSHOT.json) · [Prüfsummen](SHA256SUMS.txt)

Version 2 ergänzt den Rundgang um **„Wenn Information zum Machtmittel wird“**: Dark Web und Datenhandel, Prognosemärkte, Informationsvorsprünge und Insiderhandel, Börsenrückkopplungen sowie Nash und die historische Deutung der Rallye seit den 1980ern. Ingolf Lohmanns Wortlaut bleibt vollständig erhalten. Sieben bezeichnete Quellen tragen die sachlichen Beispiele; die weitergehende historische Kausalkette bleibt als Autorenthese erkennbar.

Der Abschnitt steht identisch in der [Online-Seite](https://qikvrt-roundtrip.ingolf-lohmann.chatgpt.site#schattenseiten) und in dieser vollständigen Einzeldatei. Die 28 bereits eingebetteten Originaltexte sind unverändert. Gestaltung, Grafiken, Quellenangaben und sämtliche neuen Lesetexte sind enthalten; keine Skripte oder nachzuladenden Ressourcen sind erforderlich.

- Größe: **560.821 Byte (0,561 MB)**; Grenze: unter 10.000.000 Byte.
- SHA-256: `8cdffdc23046a348c6ed4fe17007f40c9712bf787e29f903c4396369b20bc93c`.
- Vorgesehener Release-Tag: `qikvrt-roundtrip-2026-09-20-v2`.
- [Unveränderte Version 1](https://github.com/Goldkelch/qik-vrt/blob/c4bb95e9a1fed939cc1e582300af9b28daa614fa/docs/publications/2026-09-20-qikvrt-roundtrip-snapshot/README.md).

Die Online-Adresse führt auf die laufende Website. Der neue Snapshot wird durch seinen eigenen Git-Commit und die Prüfsumme identifiziert; der vollständige Commit-Link wird im PR und im Release-Handoff festgehalten. Die frühere Version wird nicht überschrieben.

## Prüfen

```sh
python3 -B docs/publications/2026-09-20-qikvrt-roundtrip-snapshot-v2/verify_snapshot.py
```

[VALIDATION.json](VALIDATION.json) bindet die Dateigröße, den SHA-256, 28 Originaltext-Hashes und interne Sprungziele. Die Prüfung erkennt aktive HTML-Elemente und externe HTML-/CSS-Ressourcen. Sie behauptet keinen Browser-Netzwerktest und keine unabhängige wissenschaftliche Validierung.

Urheber und Projektverantwortung: Ingolf Lohmann. Redaktionelle Einordnung, Quellenrecherche und technische Umsetzung: OpenAI Codex, auf ausdrücklichen Auftrag. Dokumentation: CC BY-NC-ND 4.0. Der bestehende Prüfcode behält PolyForm Noncommercial 1.0.0; Quellenlizenzen bleiben unverändert.
