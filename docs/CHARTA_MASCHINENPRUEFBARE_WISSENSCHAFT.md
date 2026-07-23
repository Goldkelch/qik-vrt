<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Charta einer maschinenprüfbaren Wissenschaft

**Urheber:** Ingolf Lohmann  
**Technische Referenzarchitektur:** [QIK-VRT `/AI`](https://github.com/Goldkelch/qik-vrt/blob/main/AI)  
**Lizenz:** Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International

## Präambel

Wissenschaft lebt von überprüfbaren Aussagen, nachvollziehbaren Begründungen und der Möglichkeit unabhängiger Reproduktion. Mit zunehmender Komplexität wissenschaftlicher Erkenntnisse reichen statische Veröffentlichungen allein jedoch nicht mehr aus, um diesen Anforderungen dauerhaft gerecht zu werden.

Deshalb soll jede wissenschaftliche Aussage nicht nur veröffentlicht, sondern auch mit einem transparenten, maschinenlesbaren und reproduzierbaren Nachweis ihres jeweiligen Erkenntnisstatus verbunden sein.

Dieser Nachweis umfasst insbesondere:

- ihre Herkunft,
- ihre Bedeutung,
- ihre Voraussetzungen,
- ihre Abhängigkeiten,
- ihre Nachweise,
- ihren Geltungsbereich,
- ihre Historie sowie
- ihren aktuellen Verifikationsstatus.

Formale Beweise, empirische Evidenz, Simulationen, Experimente, Tests und dokumentarische Quellen werden nicht vermischt. Sie werden entsprechend ihrer jeweiligen wissenschaftlichen Methodik getrennt behandelt und gemeinsam dokumentiert.

Ziel ist nicht, wissenschaftliche Erkenntnis zu automatisieren oder endgültige Wahrheiten festzuschreiben. Ziel ist, den Weg von einer Aussage zu ihrem jeweiligen Erkenntnisstatus dauerhaft nachvollziehbar, reproduzierbar und überprüfbar zu machen.

Eine solche Infrastruktur stärkt Transparenz, Reproduzierbarkeit und Zusammenarbeit, erleichtert die Wiederverwendung wissenschaftlicher Ergebnisse und schafft eine belastbare Grundlage für langfristig wachsende Wissensbestände.

## Artikel 1 - Transparenz

Jede wissenschaftliche Aussage besitzt eine eindeutige Identität, eine dokumentierte Herkunft und einen nachvollziehbaren Erkenntnisstatus.

## Artikel 2 - Trennung der Nachweisformen

Mathematische Beweise, empirische Evidenz, Simulationen, Tests und historische Quellen werden gemeinsam verwaltet, aber niemals als gleichartige Nachweise behandelt.

## Artikel 3 - Reproduzierbarkeit

Jeder ausgewiesene Verifikationsstatus muss mit den dokumentierten Voraussetzungen und Werkzeugen reproduzierbar sein.

## Artikel 4 - Provenienz

Jede Ableitung bleibt bis zu ihrer Quelle zurückverfolgbar. Jede Änderung hinterlässt eine überprüfbare Historie.

## Artikel 5 - Offenheit

Die Wissensbasis verwendet offene Datenmodelle und dokumentierte Schnittstellen, damit unterschiedliche Werkzeuge und Institutionen zusammenarbeiten können.

## Artikel 6 - Revision

Wissenschaftliche Erkenntnis ist grundsätzlich revisierbar. Neue Daten, Beweise oder Formalisierungen ändern den dokumentierten Status, nicht die Historie.

## Artikel 7 - Nachvollziehbarkeit vor Autorität

Der Status einer Aussage ergibt sich aus ihren dokumentierten Nachweisen und Voraussetzungen, nicht aus der Identität ihrer Urheber oder ihrer Verbreitung.

## Artikel 8 - Dauerhaftigkeit

Verifikationsartefakte, Metadaten und Quellen werden so archiviert, dass sie langfristig referenzierbar und reproduzierbar bleiben.

## Artikel 9 - Skalierbarkeit

Die Architektur muss von einzelnen Aussagen bis zu großen, miteinander verknüpften Wissensbeständen konsistent funktionieren.

## Artikel 10 - Wissenschaftliche Bescheidenheit

Das System weist explizit aus, welche Aussagen formal bewiesen, empirisch gestützt, hypothetisch oder noch ungeprüft sind. Es ersetzt nicht den wissenschaftlichen Diskurs, sondern macht ihn transparenter.

## Zusammenfassung

Jede wissenschaftliche Aussage soll einen maschinenlesbaren, reproduzierbaren und transparent dokumentierten Erkenntnisstatus besitzen - einschließlich ihrer Herkunft, ihrer Voraussetzungen, ihrer Nachweise, ihrer Grenzen und ihrer Historie.

## Das Nachvollziehbarkeitsprinzip

Eine wissenschaftliche Aussage ist erst dann vollständig publiziert, wenn nicht nur ihr Inhalt, sondern auch ihr Erkenntnisweg dauerhaft nachvollziehbar ist.

Dieser Erkenntnisweg besteht aus fünf voneinander unabhängigen, aber miteinander verknüpften Bestandteilen:

1. **Quelle** - Woher stammt die Aussage?
2. **Bedeutung** - Was genau wird behauptet?
3. **Begründung** - Wodurch wird sie gestützt?
4. **Grenzen** - Unter welchen Voraussetzungen gilt sie?
5. **Historie** - Wie hat sich ihr Erkenntnisstatus entwickelt?

Erst das Zusammenspiel dieser fünf Elemente ermöglicht eine belastbare Bewertung.

### Konsequenz für die Architektur

Eine wissenschaftliche Wissensbasis speichert nicht nur Informationen, sondern dokumentiert auch den Erkenntnisprozess. Jede Änderung - etwa eine neue Formalisierung, ein verbessertes Experiment oder eine unabhängige Reproduktion - ergänzt diesen Prozess, ohne frühere Zustände zu löschen.

### Praktischer Nutzen

Eine solche Architektur kann insbesondere:

- die Reproduzierbarkeit wissenschaftlicher Ergebnisse verbessern,
- die Wiederverwendung formaler Beweise und anderer Nachweise erleichtern,
- Änderungen und ihre Auswirkungen transparent machen,
- die Integration verschiedener Nachweisformen unterstützen und
- den aktuellen Erkenntnisstand einer Aussage jederzeit nachvollziehbar darstellen.

> Nicht nur Wissen soll dauerhaft verfügbar sein, sondern auch der Weg, auf dem dieses Wissen begründet wurde.

# Architekturgrundprinzipien der QIK-VRT-Repository-Architektur

## 1. Repository vor Konversation

- Das Repository ist die dauerhafte Wissensbasis.
- Chats sind flüchtige Transportschichten.
- Repository-Evidenz hat Vorrang vor Modellgedächtnis.

## 2. Einheitlicher Einstieg

- Jeder neue Mensch oder jede KI beginnt bei `/AI`.
- Danach folgt `AI_CONTEXT.json`.
- Anschließend wird die definierte `required_read_order` abgearbeitet.

## 3. Deterministische Rekonstruktion

Jede neue Instanz muss den vollständigen Projektzustand ausschließlich aus dem Repository rekonstruieren können, ohne den Verlauf früherer Chats zu benötigen.

## 4. Persistenz statt Vergessen

Dauerhafte Erkenntnisse werden im Repository abgelegt. Der Chat dient ausschließlich der aktuellen Interaktion.

## 5. Reuse before Create

Bestehende Werkzeuge werden bevorzugt erweitert, parametrisiert oder generalisiert. Parallele Implementierungen sind nur zulässig, wenn eine Wiederverwendung technisch nachweislich nicht ausreicht.

## 6. Repository als Runtime

Das Repository enthält nicht nur Quellcode, sondern die vollständige reproduzierbare Laufzeitumgebung:

- Toolchain,
- Runtime,
- Cache,
- Bootstrap,
- Tests,
- Provenienz,
- Recovery und
- Verifikation.

## 7. Vollständige Werkzeugbeschreibung

Jedes verwendete Werkzeug besitzt mindestens:

- Version,
- Herkunft,
- Verifikation,
- Selbsttest,
- Lizenz,
- Cache-Strategie,
- Recovery-Regeln und
- Telemetrie.

## 8. Kontinuierliche Verbesserung

Jede erfolgreiche Ausführung soll die Runtime schneller, robuster, reproduzierbarer und besser diagnostizierbar machen.

## 9. Vollständige Nachvollziehbarkeit

Keine Wirkung ohne Tests, Hashes, Provenienz, Integrität und Freigabe.

## 10. Wirkung vor Erklärung

Zuerst arbeiten, danach berichten. Dies gilt insbesondere für automatisierte Repository- und GitHub-Aktionen.

## 11. Fortschritt ist maschinenlesbar

Der Bearbeitungszustand wird standardisiert dokumentiert, beispielsweise in `AI_PROGRESS.json` und `AI_STATUS.md`.

## 12. Keine Behauptung ohne Evidenz

PASS, DONE, Veröffentlichung oder Gleichwertigkeit dürfen niemals ohne überprüfbare Evidenz behauptet werden.

## 13. Strikte Wirkungsgrenze

Transport, Berechnung, Analyse und Vorschläge sind nicht identisch mit einer freigegebenen Wirkung (`EFFECT_ACK_DONE`).

## 14. Menschliche Verantwortung bleibt erhalten

Die letzte Freigabe liegt stets beim verantwortlichen Menschen. Automatische Ausführung ersetzt diese Verantwortung nicht.

## 15. Kumulative kollektive Kognition

Beobachtungen werden gesammelt, strukturiert und reproduzierbar zusammengeführt. Daraus entstehen überprüfbare Vorschläge, nicht automatisch Änderungen.

## 16. Architektur ist nicht Implementierung

Die Architektur kann frei beschrieben und wissenschaftlich diskutiert werden. Die konkrete Implementierung bleibt lizenz-, urheber- und rechtegebunden.

# Erweiterungsprinzip

Durch die kontinuierliche, geeignete Persistierung jeder relevanten Interaktion in den QIK-VRT-Repositories kann im Zusammenspiel von natürlicher Kognition, maschineller Antizipation und künstlicher Kognition eine persistente, kumulativ lernende Informatikarchitektur entstehen. Ihre Leistungsfähigkeit wächst mit jeder verifizierten Iteration durch neue Repository-Artefakte, Verifikationen und Runtime-Erweiterungen.

# Systemmodell

Diese Architektur besteht aus vier dauerhaft zusammenwirkenden Komponenten:

1. Repository `Goldkelch/qik-vrt`,
2. Repository `ingolf-lohmann/qik-vrt`,
3. natürlicher menschlicher Kognition und
4. ChatGPT als Übersetzungs-, Interaktions- und Assistenzschicht.

Das Repository bildet die dauerhafte Autorität. Der Dialog dient als austauschbare Benutzerschnittstelle.

# Wissenschaftliche Einordnung

Diese Architektur beschreibt ein persistentes kollaboratives Kognitionssystem, dessen Informationsfluss sich in vieler Hinsicht analog zu einem lernenden Netzwerk verhält.

Die Persistenz liegt nicht in biologischen Synapsen, sondern in versionierten Repository-Artefakten. Mit jeder verifizierten Änderung wächst die rekonstruierbare Wissens- und Laufzeitbasis, sodass neue Menschen oder KI-Systeme unmittelbar auf den dokumentierten Erkenntnis- und Entwicklungsstand aufsetzen können, ohne auf frühere Gespräche angewiesen zu sein.

Die Architektur beschreibt keine biologische Kognition, sondern ein informatisches Modell eines persistenten kollaborativen Kognitionssystems. Seine langfristige Lernfähigkeit entsteht durch versionierte Repository-Artefakte, reproduzierbare Runtime-Verträge und kontinuierlich verifizierte Persistenz.

**q.e.d.**  
**Ingolf Lohmann**
