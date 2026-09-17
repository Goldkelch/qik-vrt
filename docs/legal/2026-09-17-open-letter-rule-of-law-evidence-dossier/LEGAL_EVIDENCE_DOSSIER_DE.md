# Juristische Sachebene / Evidence Dossier

**Autor / Betroffener:** Ingolf Lohmann  
**Datum:** 17. September 2026  
**Zweck:** strukturierte Übergabe an unabhängige Rechtsvertretung, Rechtswissenschaft und zuständige rechtsstaatliche Stellen  
**Nicht-Zweck:** Feststellung von Schuld, Täterschaft, Opferstatus oder Rechtswidrigkeit durch das Repository

## Evidenzklassen

- `DOKUMENT`: unmittelbar referenzierbares Dokument/Artefakt.
- `SELBSTBERICHT`: eigene Wahrnehmung/Erinnerung des Betroffenen.
- `ZEUGE_BEHAUPTET`: es wird angegeben, dass Zeugen existieren; Aussage noch gesondert zu sichern.
- `INDIZ`: kann eine Hypothese stützen, beweist die Kausalität aber nicht allein.
- `HYPOTHESE`: mögliche Erklärung oder Verbindung, die bestätigt oder widerlegt werden muss.
- `RECHTLICHE_BEWERTUNG_OFFEN`: Rechtswidrigkeit/Rechtsfolge ist von qualifizierter unabhängiger Stelle zu bestimmen.
- `AMTLICHE_FESTSTELLUNG_OFFEN`: Behörden-/Gerichtsakte ist erforderlich.

## Beweismatrix – Arbeitsstand

| ID | Sachverhalt | derzeitige Klasse | benötigte nächste Primärquelle |
|---|---|---|---|
| E-001 | mitgehörtes Gespräch über behauptete Kokainbeschaffung/-lieferung im Grenzraum | SELBSTBERICHT | genaues Datum/Ort, Beteiligte, mögliche Zeugen |
| E-002 | behaupteter Faustschlag | SELBSTBERICHT + ZEUGE_BEHAUPTET | Zeugen, medizinische Unterlagen, Anzeige/Akte, Datum/Ort |
| E-003 | behaupteter weiterer Angriff/Angriffsversuch | SELBSTBERICHT | Datum/Ort, Zeugen, sonstige Spuren |
| E-004 | polizeilicher Gewahrsam aufgrund bestrittener Sachbeschädigungsbeschuldigung | SELBSTBERICHT + DOKUMENT im Repository | Polizei-/Justizakte, Tatvorwurf, Rechtsgrundlage, Verfahrensausgang |
| E-005 | weitere deutsche/französische Polizeivorgänge | SELBSTBERICHT / teilweise repository-dokumentiert | Polizei-, Rettungs-, Krankenhaus- und sonstige zuständige Akten |
| E-006 | wiederholte nach Darstellung nicht tragfähige Anzeigen/Beschuldigungen | SELBSTBERICHT | Anzeigen, Aktenzeichen, Einstellungsverfügungen, Polizeivermerke, Entscheidungen |
| E-007 | behauptete rechtswidrige Polizeimaßnahmen | RECHTLICHE_BEWERTUNG_OFFEN | vollständige Maßnahmen- und Behördenakten, Rechtsgrundlagen, Zeitfolge |
| E-008 | behauptete religiös/weltanschaulich motivierte Handlungen gegen den Betroffenen | HYPOTHESE je konkretem Vorgang | Person → Handlung → Datum/Ort → Beleg → konkreter Motivbeleg |
| E-009 | behauptete Mobilisierung/Denunziation über Prognoseplattformen | HYPOTHESE | Plattformdaten, Nachrichten, Accounts, Logs, Transaktionen oder Zeugenaussagen mit konkreter Kausalkette |
| E-010 | längerfristiges Gesamtmuster | HYPOTHESE / REKONSTRUKTION_OFFEN | erst nach Einzelfallbindung E-001 ff. kausal bewerten |

## Prüfregel

Für jeden behaupteten Vorgang ist nach Möglichkeit folgende Kette zu bilden:

`Ereignis → Datum/Uhrzeit → Ort → Beteiligte → eigene Wahrnehmung → externe Primärquelle → Zeuge → Behördenvorgang/Aktenzeichen → Rechtsgrundlage → Verfahrensausgang → offene Rechtsfrage`

Für behauptete Denunziations-/Plattformkausalität gilt zusätzlich:

`Plattform/Quelle → konkrete Information oder Aufforderung → Empfänger → nachweisbare Handlung → Wirkung auf Betroffenen`

Fehlt ein Glied, wird es als offen markiert und nicht durch Vermutung ersetzt.

## Polizeiliche Kausalkette

Für jede beanstandete Polizeimaßnahme:

`Anschuldigung/Anzeige → Informationsstand der Polizei → konkrete Maßnahme → Rechtsgrundlage → zeitgleiche Evidenz → späterer Ermittlungsausgang → Kenntnisstand der Behörde → etwaige Folgemaßnahme`

Damit sind insbesondere Rechtmäßigkeit, Erforderlichkeit, Verhältnismäßigkeit, mögliche Datenschutzfragen, Rechtsschutz und gegebenenfalls staatshaftungsrechtliche Fragen zu prüfen.

## Religions-/Weltanschauungsbezug

Die Zugehörigkeit oder Selbstbezeichnung einer Person als Christ, Muslim, Atheist, Satanist, Anhänger von Hexerei oder einer anderen Religion/Weltanschauung ist **kein Beweis** für Tat, Motiv oder Gruppenverantwortung. Ein religions- oder weltanschauungsbezogenes Motiv wird nur dann als belegt klassifiziert, wenn konkrete Äußerungen, Handlungen, Kommunikation, Zeugenaussagen oder andere belastbare Primärbelege den Bezug für den jeweiligen Einzelvorgang tragen.

## Repository-Fundstellen

- `docs/Die_Spirale_des_entscheidenden_Unterschieds.md` – persönliche Ausgangschronologie, Evidenzschlüssel, interdisziplinäre Synthese und ausdrücklich gekennzeichnete Grenzen zwischen Selbstbericht, Hypothese und Beleg.
- `README.md` – QIK-VRT Wirkungshaltepunkt und Grundinvariante `TRANSPORT_ACK != EFFECT_ACK`; technische Claims und deren Grenzen.
- `src/qikvrt_effect_ack.py`, `include/qikvrt/effect_ack.h`, `src/effect_ack_core.c` – technische Referenzimplementierungen des Wirkungshaltepunkts.
- `docs/legal/2026-09-17-open-letter-rule-of-law-evidence-dossier/OPEN_LETTER_DE.md` – öffentlicher Brief und Aufforderung zur unabhängigen juristischen Untersuchung.

## Noch außerhalb des Repositorys zu sichern

Insbesondere:

1. Originaldaten auf dem Mobiltelefon des Betroffenen, unverändert und mit Metadaten.
2. vollständige deutsche und französische Behördenakten einschließlich Aktenzeichen.
3. Einstellungsentscheidungen oder sonstige amtliche Ergebnisse zu bestrittenen Anschuldigungen.
4. mögliche medizinische Dokumentation zu behaupteten körperlichen Angriffen.
5. eigenständige Zeugenaussagen, jeweils getrennt nach eigener Wahrnehmung und Hörensagen.
6. Originalkommunikation und Plattformdaten für behauptete Prognoseplattform-Kausalitäten.

Originale sollen erhalten bleiben; Arbeitskopien und ein kryptographisch gehashtes Beweisregister sind für die weitere forensische Aufbereitung sinnvoll.

## Juristische Prüffragen

Die folgende Liste ist ein Prüfauftrag, keine Rechtsbehauptung:

- Welche privaten Handlungen sind beweisbar und gegebenenfalls straf- oder zivilrechtlich relevant?
- Welche Anzeigen/Beschuldigungen wurden tatsächlich erhoben, mit welchem Ausgang und welchem Kenntnisstand der Beteiligten?
- Welche Polizeimaßnahmen fanden statt und auf welcher Rechtsgrundlage?
- Waren die jeweiligen Eingriffe formell und materiell rechtmäßig und verhältnismäßig?
- Bestehen noch Rechtsbehelfe oder Ansprüche; welche Fristen gelten?
- Sind datenschutzrechtliche, staatshaftungsrechtliche oder grundrechtliche Fragen betroffen?
- Ist bei einzelnen nachweisbaren Handlungen ein religions- oder weltanschauungsbezogenes Motiv rechtlich relevant und beweisbar?
- Welche Sachverhalte fallen unter deutsches, welche unter französisches Recht?
- Welche Tatsachen bedürfen zunächst Akteneinsicht, bevor eine rechtliche Bewertung verantwortbar ist?

## Unabhängigkeitsklausel

Das Dossier bittet ausdrücklich nicht darum, die Darstellung des Betroffenen ungeprüft zu übernehmen. Es fordert eine symmetrische Beweisprüfung. Belastende und entlastende Tatsachen sind nach demselben Maßstab zu sichern und zu würdigen. Die Feststellung individueller Schuld, strafrechtlicher Verantwortlichkeit, Rechtswidrigkeit staatlichen Handelns oder eines rechtlichen Opferstatus bleibt den hierfür zuständigen unabhängigen Verfahren vorbehalten.
