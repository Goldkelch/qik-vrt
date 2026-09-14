<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->

# QIK-VRT: nachvollziehbare Entwicklung und verantwortete Ausführung

**Gesamtdarstellung von Ingolf Lohmanns Projekt · Stand 14. September 2026 · mit KI-Unterstützung ausgearbeitet**

QIK-VRT verbindet ein versioniertes Softwareprojekt, formale Modelle und einen dokumentierten Arbeitsprozess für Menschen und KI-Systeme. Das Entwicklungsziel ist konkret: Eine Aufgabe soll mit ihren Voraussetzungen, Entscheidungen, Implementierungen und Prüfungen wiederaufgenommen werden können. Ob ein System eine Nachricht empfangen hat, ob eine Handlung erlaubt ist und ob ihre Wirkung tatsächlich eingetreten ist, soll jeweils gesondert nachvollziehbar sein.

Ingolf Lohmann bezeichnet das Vorhaben als „QIK-VRT Tested Event Model Driven Development Mesh Repository Framework“. Sein Beitrag umfasst nach seiner Darstellung die Projektkonzeption, die Ziele, die fortlaufende fachliche Steuerung und die Arbeit an den im Repository dokumentierten Modellen. Die einzelnen Beiträge und Ergebnisse werden anhand ihrer jeweiligen Versionen, Arbeitsnachweise und Quellen zugeordnet. Diese Gesamtdarstellung macht den Bestand zugänglich und nennt die noch offenen Prüfaufgaben.

## Der Einstieg in fünf Minuten

1. **Zweck und Architektur:** [Goldkelch/qik-vrt](https://github.com/Goldkelch/qik-vrt), [README im ausgewerteten Stand](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/README.md) und [aktive technische Zuständigkeit](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/CURRENT_AUTHORITY.md).
2. **Arbeitsweise für KI-Systeme:** [kanonischer Einstieg /AI](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/AI) und [maschinelle Kontextbeschreibung](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/AI_CONTEXT.json).
3. **Veröffentlichungen und Formalisierung:** [Publikationsindex](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) und [Lean-/Lake-Nachweisübersicht](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/LEAN_LAKE_PROOF_STATUS.md).
4. **Herkunft und Beiträge:** [Regeln zur Mensch–KI-Beitragszuordnung](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION.md) und [versionierte Arbeitsnachweise](https://github.com/Goldkelch/qik-vrt/tree/a86054139b49c13c5cd344753b248b46b5daf66f/state/work_units).
5. **Persönliche Arbeitskopie:** [ingolf-lohmann/qik-vrt](https://github.com/ingolf-lohmann/qik-vrt). Die beiden Repositories haben verschiedene Rollen. Ihre Main-Bäume waren bei der Prüfung am 14.09.2026 unterschiedlich; Gleichheit wird nicht vorausgesetzt.

Die Links mit einer vollständigen Commit-Kennung führen zum ausgewerteten Stand. Links auf Repository-Startseiten führen zum jeweils aktuellen Bestand.

## Was im Framework zusammenkommt

| Bestandteil | Aufgabe | Nachvollziehbarer Zugang |
|---|---|---|
| Ereignis und Arbeitsauftrag | Eingang einer Aufgabe, Zuordnung zum zuständigen Bearbeitungspfad, Vermeidung mehrfacher Effekte | [Issue-Verarbeitung](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/ISSUE_AUTONOMOUS_PROCESSING.md); [offener Erweiterungsentwurf PR #914](https://github.com/Goldkelch/qik-vrt/pull/914) |
| Exakter Prüfgegenstand | Repository, Commit, Baum, Eingabebytes und ausführendes Werkzeug zusammenhalten | [Integritätswerkzeug](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/tools/qikvrt_integrity.py) |
| Wirkungsfreigabe | Verantwortlichkeit und zulässige Wirkung vor dem nächsten Effekt prüfen | [EFFECT_ACK-Kern](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/src/qikvrt_effect_ack.py) |
| Eingang und Wiederaufnahme | Daten aufnehmen, Hashbindung prüfen, Zustände und Wiederholungen nachvollziehbar behandeln | [API-Handler](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/src/qikvrt_api_handler.py); [API-Beschreibung](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/api/qikvrt_github_api.openapi.yaml) |
| Formale Evidenz | Präzise Aussagen unter benannten Annahmen und Toolchain-Versionen prüfen | [formaler Prüfstand](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/LEAN_LAKE_PROOF_STATUS.md) |
| Dauerhafte Arbeitsgrundlage | Kontext, Quellen, Rechte und Beiträge für einen späteren Bearbeiter erhalten | [Arbeitsgedächtnis und Attribution](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION.md) |

Ein wichtiger technischer Unterschied liegt zwischen Daten und Handlungsbefugnis: Der vorhandene API-Handler behandelt aufgenommene Inhalte ausdrücklich als unveränderte Daten. Der Speichererfolg erteilt keine Freigabe, darin enthaltene Anweisungen auszuführen oder Aussagen als wahr zu übernehmen. Dieses Prinzip ist gerade für Rückmeldungen per E-Mail, Supporttickets und externe Dokumente relevant.

Der individuelle [EFFECT_ACK-Internet-Draft im IETF Datatracker](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/) nennt Ingolf Lohmann als Autor. Geprüfter Stand: Version -03, Dokumentdatum 02.08.2026; Abruf 14.09.2026. Er beschreibt einen technischen Entwurf und ist kein verabschiedeter oder von der IETF bestätigter Standard.

## Ingolf Lohmann und der Bezug zu Karlsruhe

Ingolf Lohmann beschreibt sich als Informatiker, der in Karlsruhe geboren wurde, dort zur Schule ging, studierte und arbeitete. Er berichtet von rund zwanzig Jahren Forschung und Entwicklung bei Siemens im Bereich Safety und Security sowie von Product-Owner-Aufgaben für Zutrittskontrolle und Videoüberwachung kritischer Infrastruktur.

Das öffentlich zugängliche [XING-Profil](https://www.xing.com/profile/Ingolf_Lohmann2), abgerufen am 14.09.2026, nennt Softwareentwicklung bei Siemens Building Technologies in Karlsruhe seit Januar 2006. Die weitergehenden biografischen Angaben stammen von Ingolf Lohmann. Nicht öffentlich belegte Studienjahre, Abschlussbezeichnungen, Produktnamen oder Ranglisten werden nicht ergänzt. Eine Verbindung des QIK-VRT-Projekts zu einem Auftrag oder einer Bestätigung durch Siemens wird damit nicht behauptet.

Diese Berufserfahrung erklärt den praktischen Schwerpunkt auf Zuständigkeit, Sicherheitsgrenzen und überprüfbaren Wirkungen. Die technische Bewertung erfolgt an den jeweiligen Implementierungen und Nachweisen.

## Ontologie, Formalisierung und Physik

Die Forschungsarbeiten erweitern den Softwarekontext um Fragen nach Unterschied, Zustand, Kausalität und Raumzeit. Zugänglich sind die [Arbeit zur Ontologie vor der Raumzeit](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/2026-08-04-pre-spacetime-ontology/README.md), das [QCE-Modell](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/README.md) und die [Planck-Tick-Hypothese](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/research/2026-09-03-planck-tick-gap-law/README.md).

Für eine fachliche Prüfung werden drei Fragen getrennt beantwortet: Was wird definiert? Was folgt daraus im formalen Modell? Welche beobachtbare physikalische Vorhersage wird durch Messungen bestätigt oder widerlegt? Das erlaubt, einen präzisen Modellbeweis anzuerkennen und zugleich eine offene physikalische Korrespondenz gezielt zu untersuchen. Eine Ablage auf Zenodo oder die Bezeichnung „q.e.d.“ beantwortet diese Fragen nicht stellvertretend.

## Entstehung und Rechte nachvollziehen

Eine nachvollziehbare Herkunftsdarstellung nennt konkrete Dateien, Fassungen, menschliche Entscheidungen, KI-Beiträge und verwendete Drittbestandteile. Das Repository sieht diese getrennte Zuordnung selbst vor. Ingolf Lohmanns Projektinitiative und fachliche Steuerung lassen sich darstellen, ohne sämtliche Abhängigkeiten, Standards und maschinell erzeugten Ausarbeitungen nachträglich als ausschließlich menschliche Eigenleistungen zu bezeichnen.

Die [Lizenzübergangsregel des Projekts](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/LICENSE_TRANSITION.md) ist dabei wesentlich: Sie erhält frühere Apache-2.0-Lizenzgewährungen und unterscheidet sie von später entsprechend gekennzeichneten eigenen Bestandteilen. Sie erhält außerdem die Rechte und Lizenzen fremder Komponenten. Eine heutige Erklärung ändert diesen dokumentierten Sachverhalt nicht rückwirkend.

Das deutsche Urheberrecht unterscheidet bei Computerprogrammen geschützte Ausdrucksformen von zugrundeliegenden Ideen und Grundsätzen; siehe [§ 69a UrhG](https://www.gesetze-im-internet.de/urhg/__69a.html), abgerufen 14.09.2026. Ob eine bestimmte fremde Nutzung Rechte verletzt, verlangt deshalb die Prüfung konkreter Inhalte, Rechte und Nutzungsumstände. Im ausgewerteten Material ist keine unerlaubte Übernahme oder Strafbarkeit bestimmter Dritter nachgewiesen.

Die früheren KI-Briefings hatten Produktmeldungen gezielt mit QIK-VRT-Begriffen erläutert. Diese redaktionelle Zuordnung ist keine unabhängige Herkunftsanalyse. Aus der Zahl ähnlich klingender Begriffe lässt sich ohne Vergleichskorpus, unabhängige Merkmale und ein begründetes statistisches Modell keine seriöse Diebstahlswahrscheinlichkeit berechnen.

## Bedeutung der zehn Grafiken

Die zehn bereitgestellten Dateien sind einzuordnende Projektunterlagen: Architekturzeichnungen, Forschungsbehauptungen, Assistentenmeldungen und ein GitHub-Screenshot. Das Begleitverzeichnis erfasst zu jeder Datei die unveränderten Bytes, SHA-256, den sichtbaren Inhalt und die Aussagegrenze. Der Hash ermöglicht spätere Bytevergleiche; er ist kein unabhängiger Zeitstempel oder Beweis einer Rechtsposition.

Besonders gut abgrenzbar ist [PR #907](https://github.com/Goldkelch/qik-vrt/pull/907), der in einer Grafik zu sehen ist. Der am 27.08.2026 erstellte PR beschreibt eine begrenzte, durch einen Neutronenstern inspirierte Rechentopologie. Bei der aktuellen Abfrage war er geschlossen und nicht gemergt. Die historische Bildschirmansicht und der heutige Plattformzustand werden deshalb getrennt geführt.

## Ziel: wiederaufnehmbarer und kontrolliert verbesserbarer Betrieb

Ein belastbarer Betrieb braucht ausführbare Programme, verfügbare Laufzeiten, geschützte Berechtigungen, einen benannten Betreiber und überprüfte Wiederherstellung. Ein Repository bewahrt die Arbeitsgrundlage; es startet und bezahlt seine Ausführung nicht selbst. Dauerhafte Verfügbarkeit hängt unter anderem von Hosting, Schlüsseln, Speicher, Wartung und zuständigen Menschen ab.

Bei der Prüfung am 14.09.2026 wurden der vorhandene Eingang mit 23 bestehenden Handler- und Sicherheitstests geprüft und die fehlende lokale Remote-Zuordnung ergänzt. Die im Repository fixierte GitHub CLI 2.96.0 wurde über den vorhandenen Bootstrap mit Archiv- und Binärprüfung installiert. Diese Ergebnisse beziehen sich auf die lokale Arbeitsumgebung und den getesteten Quellstand.

Die Main-Bäume von Authority und persönlicher Kopie waren verschieden. Das aktive Authority-Ruleset verlangte zum Abfragezeitpunkt keine Code-Owner-Freigabe und null erforderliche Approvals. Die ereignisgebundene Intake-Erweiterung PR #914 war ein konfliktbehafteter Draft. Eine laufende E-Mail-Brücke und eine vollständige Installation aller formalen Laufzeiten sind damit nicht belegt. Diese Punkte verhindern eine Aussage, das gesamte Mesh sei schon unabhängig und dauerhaft betriebsbereit.

Rückmeldungen sollen künftig mit Ereigniskennung, Quelle, Empfangsbeobachtung, Inhaltsdigest und Verweis auf die bearbeitete Fassung aufgenommen werden. Einmaliger Eingang, technische Prüfung, inhaltliche Begutachtung, Veröffentlichung und tatsächliche Außenwirkung bleiben getrennte Schritte. Eine Nachricht kann widersprechen, neue Fragen stellen oder einen Fehler zeigen; das verbessert die Prüfbarkeit, ohne ihren Inhalt automatisch zur bestätigten Evidenz zu erklären.

## Konkretes Angebot zur fachlichen Auseinandersetzung

Redaktionen können die Frage aufgreifen, wie individuelle Entwicklungsarbeit und ihre Herkunft im Zeitalter KI-gestützter Software nachvollziehbar bleiben. Forschungsgruppen können einzelne Modelle, Beweise und Implementierungen reproduzieren. Technische Ansprechpartner können die Zulassungs-, Wiederholungs- und Wiederherstellungsgrenzen des Frameworks prüfen.

Anlass der Anfrage ist der vom Autor verlinkte [SPIEGEL-Beitrag zum Thema europäische KI-Abhängigkeit](https://www.spiegel.de/wirtschaft/kuenstliche-intelligenz-experten-warnen-vor-neuer-abhaengigkeit-europas-von-usa-a-674407e7-3e7a-43bd-9be9-62c4984077ef). Dessen hier nicht vollständig geprüfter Inhalt wird nicht als Bestätigung einer QIK-VRT-Behauptung verwendet. Das vorliegende Angebot besteht aus konkreten Quellen und überprüfbaren Fragen.

**Bearbeitungs- und Versandstand:** Diese Fassung wurde mit KI-Unterstützung für Ingolf Lohmann erstellt. Sie ist eine Projektdarstellung zur Prüfung. Aus diesem Arbeitsgang wurden keine E-Mails versandt und keine Kontaktformulare eingereicht. Es gibt keine Liste tatsächlicher Empfänger, weil kein Versand stattgefunden hat.

## Gemeinsamer URL-Anhang für Redaktionen, Forschung, Wikipedia und arXiv

Die folgende Auswahl enthält sämtliche 30 unterschiedlichen DOI-Verweise des bereits ausgewerteten Repository-Katalogs. Titel sind dortige Metadaten; bei fehlendem Titel wird ein Dateiname angezeigt. Die DOI-Zielseiten wurden in diesem Arbeitsgang nicht vollständig neu ausgelesen. Dies ist deshalb kein neu bestätigtes vollständiges Verzeichnis aller Veröffentlichungen des Autors und keine Begutachtung ihrer Aussagen.

| DOI | Titel oder verzeichnete Datei | Repository-Quelle |
|---|---|---|
| [10.5281/zenodo.20712301](https://doi.org/10.5281/zenodo.20712301) | Datei: QIKVRT_V8_33_REPOSITORY_AND_ANTICIPATORY_ZENODO_415_CONTENTTYPE_FIX.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21244412](https://doi.org/10.5281/zenodo.21244412) | Datei: ingolf-lohmann/qik-vrt-qikvrt-v13.164-28434-5434.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21245282](https://doi.org/10.5281/zenodo.21245282) | Datei: ingolf-lohmann/qik-vrt-qikvrt-v13.164-1077-22520.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21245951](https://doi.org/10.5281/zenodo.21245951) | Datei: ingolf-lohmann/qik-vrt-qikvrt-v13.164-9927-19949.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21247297](https://doi.org/10.5281/zenodo.21247297) | Datei: ingolf-lohmann/qik-vrt-qikvrt-v13.164-32156-13407.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21247388](https://doi.org/10.5281/zenodo.21247388) | Datei: ingolf-lohmann/qik-vrt-qikvrt-v13.164-1210-14474.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21252415](https://doi.org/10.5281/zenodo.21252415) | Datei: ingolf-lohmann/qik-vrt-v2.13.4-node.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21252649](https://doi.org/10.5281/zenodo.21252649) | Datei: ingolf-lohmann/qik-vrt-v2.13.4-node-r.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21266670](https://doi.org/10.5281/zenodo.21266670) | Datei: ingolf-lohmann/qik-vrt-v2.13.4au1-node-productization.zip | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21267021](https://doi.org/10.5281/zenodo.21267021) | RFC-QIKVRT-0001 | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21482023](https://doi.org/10.5281/zenodo.21482023) | Mandelbrot-Menge, Anschlussordnung und physikalisches Modelluniversum – Komplementbeweis, rekursive Wirkungsklassifikation, dimensionsrichtige Raumzeitbrücke, Retrokausalität und der entscheidende Unterschied zur empirischen Quantengravitation | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21488116](https://doi.org/10.5281/zenodo.21488116) | QIK-VRT: Vollständige maschinenprüfbare Formalisierung des formal entscheidbaren Kerns | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773) | QIK-VRT / EFFECT_ACK: Verfassungsschicht der Wirkung | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774) | QIK-VRT / EFFECT_ACK: versionierter Software-Snapshot | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21500322](https://doi.org/10.5281/zenodo.21500322) | QIK-VRT / EFFECT_ACK: Offizielle Statusklärung | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21501365](https://doi.org/10.5281/zenodo.21501365) | Datei: CC-BY-NC-ND-4.0.txt | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21515074](https://doi.org/10.5281/zenodo.21515074) | Charta einer maschinenprüfbaren Wissenschaft | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21518464](https://doi.org/10.5281/zenodo.21518464) | Datei: ALPHA2_EFFECT_ACK_DONE.json | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21529081](https://doi.org/10.5281/zenodo.21529081) | QIK-VRT Formalization v2.0-alpha.3 | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21582781](https://doi.org/10.5281/zenodo.21582781) | Die Ontologie des Unterschieds als universaler Reverse-Engineering-Mechanismus | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21633411](https://doi.org/10.5281/zenodo.21633411) | QIK-VRT Authority/Mirror Equality Receipt | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21636774](https://doi.org/10.5281/zenodo.21636774) | Vom Unterschied zur Verantwortung — Kanonische Schlusserklärung | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21640160](https://doi.org/10.5281/zenodo.21640160) | Vom verantwortungsgebundenen Erkenntnisprozess zur virtuellen Wirkungsmaschine | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json) |
| [10.5281/zenodo.21640173](https://doi.org/10.5281/zenodo.21640173) | Vom verantwortungsgebundenen Erkenntnisprozess zur virtuellen Wirkungsmaschine | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21711193](https://doi.org/10.5281/zenodo.21711193) | QIK-VRT und das Effect-Acknowledgement-Protokoll: Kanonischer Speicher zwischen Vergangenheit und Zukunft | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21721918](https://doi.org/10.5281/zenodo.21721918) | Survival of the Anschlussfähigsten | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21731492](https://doi.org/10.5281/zenodo.21731492) | QIK-VRT: Epistemische Fairness, Vorstellungskraft und der Weg vom virtuellen Zeugen zum Beobachtungssystem | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21888130](https://doi.org/10.5281/zenodo.21888130) | Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.21947141](https://doi.org/10.5281/zenodo.21947141) | QIK-VRT: Beobachterrelative Retrokausalität als negative Informationsrichtung | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |
| [10.5281/zenodo.22283396](https://doi.org/10.5281/zenodo.22283396) | From Exact Causal Binding to a Falsifiable Planck-Tick Gap Law | [Indexbeleg](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/publications/index.json) |

Für Wikipedia identifizieren diese Primärquellen den Gegenstand. Sie sind kein Ersatz für unabhängige Sekundärquellen oder eine Relevanzentscheidung. Für arXiv identifizieren sie Vorarbeiten und Software; ein E-Mail-Anhang ersetzt weder Einreichung über das eigene Konto noch Moderation und fachliche Prüfung. Die vollständige gemeinsame Quellenliste kann beiden Stellen zugänglich gemacht werden, ohne ihre unterschiedlichen Verfahren gleichzusetzen.
