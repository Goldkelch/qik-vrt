<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Technical elaboration: OpenAI Codex. -->
# Runtime-Faehigkeiten dauerhaft erhalten

Owner-Auftrag vom 26.09.2026: Dies gilt fuer alle Funktionen und Faehigkeiten,
die momentan nur lokal in der Chat-Runtime existieren. Das Abschalten einer
Chat-Automation ist keine Wiederherstellung ihrer Funktion im Repository.

## Vorhandenen RCP-Pfad erweitern

Dieser Baustein ergaenzt `capabilities/rcp.json` und die bestehende
Repository Capability Self-Disclosure Specification. Deren allgemeiner
Materialisierer und API sind laut aktuellem Record noch nicht implementiert.
Er ersetzt weder dieses offene Gesamtziel noch behauptet er dessen Abschluss.

`runtime/capabilities/SESSION_SURFACE_20260926.json` inventarisiert die in der
ausfuehrenden Sitzung exponierten Tool-Namen. Es enthaelt keine Zugangsdaten,
Mailboxdaten oder proprietaeren Tool-Implementierungen. Die Grenze ist explizit:
verdeckte Plattforminterna und andere Sitzungen sind damit nicht inventarisiert.
Installierte Skills brauchen zusaetzlich eine Paket-/Lizenzpruefung.

`python3 -B tools/qikvrt_capability_continuity.py` erzeugt lesend pro Operation
einen konkreten Wiederverwendungspfad, offene Abhaengigkeiten und naechsten Effekt.
`--check` bestaetigt nur die Inventarzuordnung. Quellcodepraesenz setzt niemals
`operationally_migrated` oder `safe_to_retire_source` auf wahr.

Jede Funktion benoetigt fuer echte Paritaet: ausfuehrbare Implementierung,
gebundene Abhaengigkeiten und Rechte, autorisierten Zieladapter, privaten
Zustandstransfer, reale Ausfuehrung, Wirkungs-Readback und Wiederanlauf-Test.
Unbekannte Funktionen werden als offene Eintraege erhalten. Kontozugriffe
werden ueber autorisierte Schnittstellen angebunden, nicht aus ChatGPT exportiert.

## Outlook: verbindlicher Funktionsumfang

Die Zielanbindung arbeitet im privat konfigurierten Postfach mit den bereits
vorhandenen Ordnern. Keine weiteren Ordner anlegen. Konkrete Konto-, Ordner-
und Nachrichtenkennungen, Absenderlisten sowie Versandanker bleiben privat.

Vor Projektzuordnung wird persoenlicher Aufmerksamkeitsbedarf geprueft.
Fragen, Entscheidungen, Angebote, Fristen, substanzielle Antworten, wesentliche
Entwicklungen, Warnungen, offene Ruecklaeufer und eigene Kontroll-CC bleiben im
normalen Posteingang. Unklar bleibt sichtbar; gelesen bedeutet nicht erledigt.
Nur nachweislich automatisch abgelegte, aktuell relevante Post zurueckholen;
spaetere bewusste Nutzerablagen und historische Bestaende nicht pauschal umkehren.

Prioritaet nach dieser Regel: direkte verifizierte OpenAI-Korrespondenz;
belegte AbNan-Projektkorrespondenz; private QIK-VRT-Versandfolge; allgemeine
QIK-VRT-Korrespondenz. Inhalt, Anhaenge und Verlauf entscheiden. Sender,
Stichwort, Signatur oder zeitliche Folge allein genuegen nicht. Standard-CI-
Benachrichtigungen verbleiben ausser bei spezifischem AbNan-Bezug im GitHub-Bereich.
Private und institutionelle Versandfolge anhand des tatsaechlich beantworteten
Originals unterscheiden. Autoantwort ist keine Zustimmung oder Fachreview.

Eingang, Gesendet und Entwuerfe sowie rekursive Zielmitgliedschaft pruefen.
Entwuerfe nur verschieben, niemals senden oder bearbeiten. Kein Kopieren,
Loeschen, Weiterleiten, Empfaengeraendern oder Duplikatbereinigen. Gesendet und
CC sind eigenstaendige Nachrichten, selbst bei gleicher Internet-Message-ID.
Junk nur fuer zweifelsfrei zugehoerige Versand-Ruecklaeufer einbeziehen;
Geloeschtes niemals wiederherstellen.

Vollstaendige Pagination, mindestens 24 Stunden Ueberlappung ab letztem
erfolgreichen Checkpoint mit gemeinsamer UTC-Tagesgrenze; ohne Checkpoint sieben
Tage. Neue/geaenderte Entwuerfe zusaetzlich aktuell lesen. Hoechstens zwei Reads
parallel, Moves seriell, Retry-After beachten. Unklare POST-Ausgaenge niemals
blind wiederholen. Frische Pfad-ID-Pruefung vor Nutzung und Ziel-/Quellmitglied-
schaft nach Move. Inhalt, Anhaenge, Empfaenger, Entwurfs- und Gelesenstatus erhalten.
Zeitfenster erst nach vollstaendiger Verarbeitung schliessen. Offene Bereiche
bei Wiederanlauf nachholen. Keine routinemaessigen Erfolgsmeldungen.

`tools/qikvrt_outlook_continuity.py` implementiert den begrenzten Transaktionskern:
Snapshot-Bindung, Vorrangpruefung, Pre-Effect-Journal, neue ID, Erhaltungspruefung,
Mitgliedschaft, idempotentes Ueberspringen und Wiederanlauf ohne zweiten Move.
Semantische Klassifikation und vollstaendige private Snapshots kommen vom
autorisierten Adapter; das Modul behauptet keine eigene Inhaltsanalyse.
Journal einschliesslich Snapshots ist vertraulich, niemals Git-/Actions-Artefakt.
Der Betreiber muss private Dateirechte und exklusive Mailbox-Lease sicherstellen.

Noch offen: authentifizierter Outlook-Adapter im Zielsystem, semantischer
Klassifikator, paginierender Scan-/Draft-Controller, privater dauerhafter Runner,
Import des bestehenden privaten Checkpoints/Journals, echte Live- und Restart-
Abnahme. Kein produktiver Zeittrigger wird behauptet oder eingerichtet, solange
diese Voraussetzungen nicht nachgewiesen sind. Die ChatGPT-Aufgabe bleibt aus.

## Reproduktion

`python3 -B -m unittest tests.test_runtime_capability_continuity -v`

Diese Tests verwenden synthetische Adapter. Sie pruefen den Kern, nicht Outlook,
semantische Klassifikation, reale Credentials, Deployment oder Gesamtmigration.
