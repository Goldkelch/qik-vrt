<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->

# Autorisiert; Ausführung am fehlenden Zugang angehalten

Die kanonische Freigabe `erkenntnis-20260920-v1-05d27257` wurde von Ingolf Lohmann tatsächlich erteilt und unter Authority-Commit `6db81f9e6b77efce6addcfe629748b9cff481260` gespeichert. Sie gilt für genau 13 Dateien mit 104667 Bytes. Die Upload-Dateien, Metadaten, Rücklieferung und das Prüfarchiv sind unverändert. Eine Wiederholung derselben menschlichen Freigabe ist nicht erforderlich.

Der generische v2-Publisher wurde am sauberen Commit `6db81f9e6b77efce6addcfe629748b9cff481260`, Tree `55dbed167d50c29f739960693920ededb68c6429`, ausgeführt. Manifestprüfung, Bindung an den gespeicherten Commit und Authority-Origin-Prüfung waren erfolgreich. Der Prozess endete am 20.09.2026 um 07:29:11 UTC mit Exitcode 2:

```text
BLOCK: ZENODO_ACCESS_TOKEN is missing or structurally invalid
```

Die Beobachtung der lokalen Umgebung ergab: `ZENODO_ACCESS_TOKEN` und `GITHUB_TOKEN` sind nicht gesetzt. Die Konfiguration von Repository-Secrets wurde nicht eingesehen; daraus wird keine Aussage über dort gespeicherte Zugänge abgeleitet. Dieser Publisher benötigt beide Fähigkeiten: Zenodo für den Datensatz und GitHub für die einmalige Verbrauchssperre. Der hier verfügbare GitHub-Connector kann Repository-Dateien speichern, stellt dem CLI aber kein entsprechendes Token und keinen Workflow-Dispatch bereit. Die vorhandenen untersuchten Produktionsworkflows sind auf andere Publikationen und feste Commits gebunden.

Die Anhaltung erfolgt in `_validated_network_secrets()` vor der Erzeugung eines Netzwerkclients und vor der Verbrauchssperre. Die anschließende genaue GitHub-Abfrage ergab keine Ref für diese Entscheidung. Dieser Lauf hat keinen Zenodo-Datensatz erzeugt, keine Datei hochgeladen, keinen DOI reserviert und keine Veröffentlichung bestätigt. Das maschinenlesbare Protokoll steht in [PUBLICATION_EXECUTION_STATUS.json](PUBLICATION_EXECUTION_STATUS.json).

## Kleinster nächster Schritt

Ein bereits authentifizierter Ausführungsdienst mit Zugriff auf beide erforderlichen Fähigkeiten führt den unveränderten vorhandenen Publisher aus. Die gültige Entscheidung und die Nonce werden dabei wiederverwendet. Credentials werden über die geschützte Umgebung des Ausführungsdienstes bereitgestellt.

1. Einen sauberen Authority-Checkout von `6db81f9e6b77efce6addcfe629748b9cff481260` herstellen. Ein Nachfolgecommit ist nur zulässig, wenn die vorhandenen Publisher-Prüfungen sämtliche gebundenen Dateien unverändert bestätigen. `origin` muss `Goldkelch/qik-vrt` bezeichnen.
2. Die vorhandene Tool-Cache-Prüfung und die lokale Manifestprüfung ausführen. Den tatsächlich ausgecheckten Commit als Ausführungssubjekt übergeben.
3. Mit sicher bereitgestellten `ZENODO_ACCESS_TOKEN` und `GITHUB_TOKEN` starten:

```bash
python3 -B tools/qikvrt_tool_cache.py verify
export GITHUB_REPOSITORY=Goldkelch/qik-vrt
export GITHUB_SHA="$(git rev-parse --verify 'HEAD^{commit}')"
python3 -B tools/qikvrt_zenodo_publish.py \
  --manifest release/schrittweise-erkenntnis-2026-09-20-v1/publish-request.json
```

Diese Umgebungsbindung bezeichnet den realen CLI-Checkout und ist keine Behauptung eines GitHub-Actions-Laufs. Der Publisher bleibt für alle Zugangs-, Einmaligkeits-, Datei-, Metadaten-, Herkunfts- und öffentlichen Rückleseprüfungen verantwortlich. Eine bereits vorhandene Verbrauchsref darf nicht gelöscht oder überschrieben werden; gegebenenfalls ist der bestehende Wiederaufnahmepfad mit der tatsächlich vorhandenen Recovery-Evidenz zu verwenden.

Die Verbrauchsref lautet:

```text
refs/tags/qikvrt-zenodo-auth/64beacf91a9fb67dec653dcfff66aea0b5f8e8e660d80040203ace86389a96d0
```

Erst nach erfolgreicher Veröffentlichung und bytegenauer öffentlicher Rücklesung ist `zenodo-publication.json` der Publikationsnachweis. Anschließend sind dieser Nachweis und die aktualisierten Verweise samt Integritätsdateien im Repository zu persistieren. Die vorhandene Repository-Policy verlangt für eine Behauptung der Authority/Mirror-Gleichheit zusätzlich die entsprechende beidseitige Persistenz und Rücklesung. Native PR-Prüfungen, Merge und Mirror-Gleichheit sind eigenständige Zustände; hier wird keiner davon als erledigt behauptet.

## Gültige Bindungen

| Bestandteil | SHA-256 |
| --- | --- |
| Rücklieferung | `63765ef9fd18d4f59e5d4141c501873d289d7bc986101a9fe74783a563bc097f` |
| Kanonische Metadaten | `bc1e769a7daba366cf6c9b79422e559d94b50767afb9cc39f7c6bacd3003f7ea` |
| Prüfarchiv | `d735cd3ed5eaa16691a4d3cf43eaf38ee29fe91e00fd4e369945410f63ed219c` |
| Endgültige Autorisierung | `f79b76082ea8b58e4b8632b322268925f70439685917fb61a4283537051d25ab` |
| Ausführbares Manifest | `a8f2a21b54287749173c4cf1566a600eafc4d0d472a1e3ae50bbbd5934989d8d` |

Die ersten drei Werte entsprechen wortgetreu der tatsächlichen menschlichen Freigabe. Die beiden letzten Werte identifizieren die daraus erzeugten Repository-Kontrollen. Dieses Dokument und das Ausführungsprotokoll gehören nicht zum eingefrorenen Zenodo-Upload-Dateisatz.
