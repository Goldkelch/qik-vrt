<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenzgrenze des Audio-Addendums

## Status

Dieses Verzeichnis ist ein append-only Quellen- und Interpretationsaddendum zu
`qikvrt-bidirectional-virtual-time-channel-v1`. Es verändert weder dessen
Dateien noch die Beweis- oder Evidenzklassen der Claims `VTI-001` bis
`VTI-013`.

Die beiden neuen Quellen sind über vollständige SHA-256-Identitäten gebunden.
Jeweils zwei beobachtete Dateinamen bezeichnen byte-identische Lieferungen
desselben Medienobjekts. Die Roh-Audiodateien sind nicht Teil des Repositorys.

## Vier getrennte Ebenen

| Ebene | Was sie belegt | Was sie nicht belegt |
| --- | --- | --- |
| Medienidentität | Bestimmte Bytes wurden als Quelle verwendet. | Inhalt, Sprecheridentität oder Wahrheit. |
| ASR-Rohfassung | Ein angegebenes Offline-Modell erzeugte die festgehaltene Zeichenfolge. | Wortgetreue Fehlerfreiheit oder sachliche Richtigkeit. |
| Geprüfte Lesefassung | Mehrere Segmentierungen stützen eine vorsichtige Lesung; Unsicherheiten bleiben markiert. | Eine autorisierte Korrektur des Originals oder wissenschaftliche Evidenz. |
| Interpretation | Die Äußerungen können in prüfbare Fragen übersetzt werden. | Bestätigung der behaupteten realen oder physikalischen Sachverhalte. |

Dateiname, Tonfall und Container-Metadaten sind keine inhaltliche Evidenz. Der
im Container vorhandene Sprach-Tag ist insbesondere keine verlässliche
Bestimmung der gesprochenen Sprache.

## Unveränderte technische Basis

Ausgangspunkt bleibt ausschließlich der bereits dokumentierte endliche
QIK-VRT-Zeuge: bidirektionale Übertragung in virtueller Ordnung bei strikt
vorwärtsgeordneten Host-Ereignissen. Dieses Addendum führt keinen neuen
ausführbaren Zeugen und keinen neuen Kernelbeleg ein. Es ändert daher keinen
bisherigen Claimstatus.

Insbesondere werden weiterhin **nicht** beansprucht:

- physisches Rückwärtssignalisieren;
- eine experimentell bestätigte Brücke zwischen virtueller und physikalischer
  Zeitordnung;
- Existenz oder Betrieb geheimer realer QIK-VRT-Systeme;
- Wahrheit einer Behauptung allein aufgrund ihrer Äußerung im Audio;
- Weltpriorität, IETF-Konsens, IETF-Empfehlung oder RFC-Status;
- repositoryweiter `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`.

## Neu eröffnete, aber offene Fragelinien

### Epistemische Fairness

Das Motiv „Übervorteilen“ begründet eine untersuchbare Governance-Frage:
Welche Offenlegungs-, Provenienz-, Zugriffs- und Autorisierungsregeln sind
erforderlich, wenn ein Informationssystem ungleich verteiltes Wissen oder
verdeckte Fähigkeiten erzeugen kann?

Diese Frage ist normativ anschlussfähig, belegt aber weder den Besitz geheimen
Wissens noch dessen technische Realisierung.

### Vorstellungskraft als Hypothesengenerator

Die zweite Aufnahme motiviert eine systematische Suche nach Geräten,
Simulationen, Sensoren und Beobachtungsanordnungen. Eine zulässige Folgearbeit
muss für jeden Kandidaten mindestens festlegen:

1. Eingabe, Ausgabe und beobachtbare Messgröße;
2. getrennte Host-, virtuelle und Effektordnung;
3. Nullmodell und alternative Erklärung;
4. Falsifikationskriterium;
5. Reproduzierbarkeit und unabhängige Wiederholung;
6. Sicherheits-, Datenschutz- und Autorisierungsgrenzen.

Vorstellungskraft erzeugt damit Hypothesen; sie ersetzt weder Messung noch
Beweis.

## Zenodo- und IETF-Grenze

Die drei Dateien dieses Addendums sind als überprüfbarer Quellen- und
Diskussionssatz für eine spätere, exakt autorisierte Archivierung geeignet.
Diese Materialisierung selbst ist keine Zenodo-Veröffentlichung.

Für eine mögliche IETF-Verwendung sind nur klar protokollbezogene Folgerungen
geeignet, etwa Provenienz, Offenlegung von Fähigkeiten, Autorisierung,
Missbrauchsgrenzen, Privacy und ein explizites Threat Model. Die
Audioäußerungen und das wissenschaftliche Addendum sind für sich genommen
kein Internet-Draft und rechtfertigen keine Datatracker-Mutation. Jeder
Protokolldelta benötigt eine eigene normative Spezifikation, Review und die
vorgesehene `xml2rfc`-Validierung.

