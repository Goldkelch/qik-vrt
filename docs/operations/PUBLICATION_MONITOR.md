<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# Kanonischer Publikations- und Paketbeobachtungsstand

Der stabile Einstieg ist `/PUBLICATION_MONITOR.json` in `Goldkelch/qik-vrt`.
Er benennt die geprüfte Implementierung, Policy und den einzigen Datenzweig
`refs/heads/qikvrt/publication-monitor-state-v1`. Die Datei heißt dort immer
`monitor/state.json`. Jeder Consumer löst zuerst den Ref zu einem exakten
Commit/TREE auf und liest die Datei auf genau diesem Commit. Chat-Dateien,
Suchtreffer und die Zustimmung zu einer Meldung ersetzen diesen Schritt nicht.
Fehlender oder beschädigter Zustand ist BLOCK, niemals eine neue leere Baseline.

Der Datenzweig enthält keine ausführbaren Workflows. Er ist ein dauerhafter
Ledger, kein zu mergender Produktzweig. Seine Snapshots stehen append-only unter
`monitor/history/<generation>-<SHA256>.json`; öffentliche HTTP-Antwortbytes
stehen unter `monitor/responses/<SHA256>.body`. Code wird über einen regulären
PR geprüft und nach Main integriert. Ein PR-Probe läuft nur lesend; erst die
Main-Ausführung des Writers darf Datenzustand committen. Die Existenz dieser
Dateien allein ist keine Main-Integration oder laufende Überwachung.

## Wiederverwendung und verlorene Ausgangslage

`tools/qikvrt_zenodo_corpus_proof.py` bleibt unverändert. Dieses vorhandene
Werkzeug untersucht tokengebundene Depositionen und lädt Dateien erneut; es
ersetzt keinen vierplattformigen, credentialfreien Discovery-Ledger. Die
native Codesuche auf Main `f4bbc5846bd6fad789e4712dbf8443119499c636` lieferte
für `crates.io` nur `next/Cargo.lock`. Der neue einzelne Collector verwendet
Git-Persistenz und die bestehenden gepinnten Checkout/Artifact-Actions sowie
die bestehende Integritätsmaterialisierung. Die Regressionen sind zusätzlich
in der bestehenden erforderlichen CI registriert. Keine ChatGPT-Aufgabe wird
angelegt oder verändert.

Der frühere lokale ACK liegt byteidentisch unter
`state/publication-monitor/migration/ACK_515570598dad2437.json`.
Sein SHA-256 lautet
`515570598dad24378f2f875dd281370b8a9b4334919b060c69bc9d03bf36b6b0`.
Die 37 darin berichteten Dateichecksummen bleiben historische Berichtsangaben,
kein neuer öffentlicher Downloadnachweis. Die verlorene vollständige alte
Zenodo/arXiv/Wikimedia-Baseline wird nicht erfunden. Bekannte bereits gemeldete
Record-IDs bleiben als Wiederauffindungsziele erhalten; die erste vollständige
öffentliche Recovery-Inventur wird still etabliert und nicht als neue
Publikationswelle gemeldet. Diese Migration beansprucht keine rückwirkend
vollständige Wiederherstellung der verlorenen Beobachtungshistorie.

Die vom Nutzer ausdrücklich konsumierte crates.io-Baseline vom
`2026-09-12T08:35:40.709Z` bleibt exakt erhalten: `qik-vrt`, `qikvrt`, `temdd`
und `cloud-transputer` jeweils null Treffer. Ihre Klasse ist
`CONSUMED_USER_SUPPLIED_BASELINE`. Ein später tatsächlich neu gefundener
passender Crate oder eine Version ist deshalb ein neuer Subject.

## Öffentliche Reobservation

Alle vier Plattformadapter erlauben nur HTTPS-GETs an explizite offizielle
Endpoints. Es gibt keine Tokenparameter, Cookies, automatischen Redirects,
Publikations-, Edit-, Mail- oder Owner-Schreibpfade. JSON-Duplikate, NaN,
XML-Entities, unvollständige Pagination und Identitätsabweichungen werden
abgelehnt. Ressourcen und Laufzeit sind begrenzt; arXiv wird gesondert gepaced.

Zenodo bindet Record, Concept und DOI nur an gelieferte Felder, niemals an
arithmetische Vermutungen. Metadaten, Zugriff, Lizenz, Versionsbeziehungen,
Dateinamen, Größen und Publisher-Checksummen sind normalisiert. Diese
Checksummen sind **Publisher-Metadaten, kein hier ausgeführter Dateidownload**.

Bei crates.io bleiben Crate-Metadaten und jede Version getrennte Subjects.
Owners, Projektlinks, aktuelle/maximale Version, Versions-ID, Yank-Status und
Zeitstempel werden erfasst; Downloadzähler sind keine Identitätsänderung.
Versionen werden gegen die vollständige ID-Liste geprüft. Neuere Versionen
validieren weder frühere Versionen noch umgekehrt. Ein Owner-Endpoint-Fehler
kann nicht als Verschwinden des Crates gelten. Die Suchrelevanz beweist keine
Urheberschaft oder offizielle Projektzugehörigkeit.

arXiv bindet die explizite Versions-ID und liest bereits bekannte alte Versionen
separat nach. Eine Suchauslassung ist keine Löschung. MediaWiki bindet positive
Ergebnisse an Page-ID und Revisions-ID; nur eine gültige API-Antwort mit
`missing=true` belegt das Fehlen eines Lemmas. Der Wiki-Scope umfasst die
benannten englischen/deutschen Wikipedia-Titel und Wikidata-Suchen in diesen
Sprachen, nicht alle Wikimedia-Projekte.

Timeout, DNS-Fehler, unvollständige Antwort, 403, 429, 5xx oder Schemafehler
ändern keinen zuletzt verifizierten Subject. Sie aktualisieren die getrennte
Betriebsdiagnose. `Retry-After` wird gespeichert und vor neuem Abruf beachtet.
Eine Abrufbarkeitsregression wegen 404/410 erfordert zwei getrennte Antworten
des exakten bisherigen Record-/Crate-Endpoints mit mindestens 60 Sekunden
Abstand und erfolgreiche vollständige Plattforminventur. Der letzte Metadaten-
Stand bleibt auch dann erhalten. Eine Löschungsursache wird nicht behauptet.

## Persistenz, Wiederanlauf und Meldezustellung

`validate` prüft Zustandsschema, Policy-Hash, aktuelle und unmittelbare vorige
Snapshotbytes, alle im Zustand referenzierten HTTP-Antwortbytes und die
Outbox-Fingerprints. Ein Hash im selben beschreibbaren Speicher ist kein
unabhängiger Authentizitätsbeweis; der extern zurückgelesene Git-Commit ist
die zusätzliche Bindung. POSIX-Schreibsperre, atomarer Ersatz mit fsync und
Vergleich des erwarteten Vorgängers verhindern konkurrierende lokale Updates.

Der Main-Runner führt innerhalb desselben Writers aus: lesen, materialisieren,
Datencommit, normaler Non-Force-Push, erneutes Fetch und bytegenauer Vergleich
der Zustandsdatei. Auch nach uneindeutigem Push wird frisch nachgelesen. Ein
konkurrierender Schreiber oder Main-Drift führt zu BLOCK, nicht Force-Push.
Nur `REPOSITORY_READBACK.json` mit `repository_persistence_readback=true`
bestätigt diesen Repository-Effekt. `LOCAL_PREPARATION.json` tut das nicht.
Der nächste Lauf beginnt mit dem tatsächlich gespeicherten Nachfolger.

`outbox` enthält nur materielle Alt→Neu-Übergänge. Die Fingerprints binden
Subject, dessen Änderungsnummer und beide Zustände. Unverändertes Replay
produziert nichts Neues; eine echte Folge A→B→A→B bleibt erkennbar. Der
Collector selbst sendet keine Nachrichten. Ein autorisierter Consumer liest
zuerst die persistierte Outbox, stellt die Nachricht zu und bestätigt danach
nur deren exakte Event-ID mit `acknowledge --event-id`. Auch diese Bestätigung
muss gespeichert und nachgelesen werden. Ohne Zustellreceipt bleibt das
Ereignis offen; Exactly-once-Zustellung über unabhängige Dienste wird nicht
behauptet.

Die manuelle Initialisierung ist einmalig und weigert sich, vorhandenen
Zustand oder Historie zu ersetzen. Reguläre Runs initialisieren niemals selbst:

```sh
python3 -B tools/qikvrt_publication_monitor.py validate --store /absolute/data-checkout
python3 -B tests/test_qikvrt_publication_monitor.py
sh tools/qikvrt_publication_monitor_runner.sh probe /absolute/data-checkout /absolute/new-audit-dir
```

Die 43 Regressionstests verwenden synthetische Fixtures. Sie prüfen Verlust,
Neustart, Sperre, beschädigte Antwortbytes, HTTP-Fehler, Versionstrennung,
Deduplication und Negativfälle, nicht die heutige Verfügbarkeit einer Plattform.
Ein gesonderter nativer Run liefert die frischen HTTP-Antworten. Externe
Netzausfälle werden nicht unmöglich; der überprüfbare Anspruch ist, sie nicht
mehr mit Zustandsverlust, leerer Inventur, Neuveröffentlichung oder erfolgreicher
Reobservation zu verwechseln. Kein Ergebnis impliziert wissenschaftliche
Bestätigung, Repository-Approval oder allgemeines `EFFECT_ACK_DONE`.

Der erste native Probe fand sieben Zenodo-Records direkt, aber die Inventur
wurde mit HTTP 400 zurückgewiesen: anonyme Requests dürfen höchstens 25
Einträge pro Seite verlangen. Der Adapter verwendet deshalb 25, ohne Token
anzufordern. Die arXiv-406-Antwort wird als Fehler erhalten; breitere XML-
Medientypverhandlung bleibt erneut öffentlich zu prüfen. Daten und Fehler
werden nicht zu einem globalen Erfolgsstatus zusammengezogen.
