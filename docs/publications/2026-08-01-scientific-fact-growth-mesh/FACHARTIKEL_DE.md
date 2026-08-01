<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Ein Spiegel für Ursachen: Wie QIK-VRT aus Daten einen überprüfbaren Erkenntnisweg macht

Von Ingolf Lohmann

Ein Computersystem kann heute in Sekunden mehr Text durchsuchen, als ein
Mensch in einem Leben lesen könnte. Trotzdem bleibt eine überraschend einfache
Frage oft unbeantwortet: *Warum sollen wir genau dieser Aussage vertrauen?*

Ein Suchtreffer kann eine Behauptung wiederholen. Ein Sprachmodell kann sie
flüssig erklären. Ein Messgerät kann Zahlen liefern. Ein Beweisassistent kann
eine Formel akzeptieren. Aber keiner dieser Vorgänge ist für sich allein der
ganze wissenschaftliche Weg. Es fehlen möglicherweise Quelle, Kalibrierung,
Prämissen, Unsicherheit, Gegenbelege, Entscheidung oder die Rückmeldung, was in
der realen Welt tatsächlich geschah.

Genau hier setzt QIK-VRT an. Ein QIK-VRT-Repository lässt sich als
**Kausalitätsspiegel** verstehen: Es speichert nicht nur ein Ergebnis, sondern
bildet den überprüfbaren Weg von der Beobachtung über Transformation und
Hypothese bis zur Entscheidung, beabsichtigten Wirkung und beobachteten
Rückwirkung ab.

Der Spiegel ist nicht die Wirklichkeit. Das ist seine wichtigste Grenze. Er
macht sichtbar, welche Verbindung belegt ist, welche nur angenommen wird und
welche noch fehlt.

## Sechs Arten, recht zu haben – oder noch nicht

In gewöhnlichen Datenbanken steht häufig nur ein Wahrheitswert: wahr oder
falsch. Wissenschaft ist feiner. QIK-VRT unterscheidet deshalb sechs
epistemische Klassen:

1. **Formal bewiesen:** Ein genau benannter Satz folgt in einem genau
   benannten formalen Modell und wurde von einem gebundenen Kernel geprüft.
2. **Empirisch gestützt:** Eine begrenzte Beobachtung ist mit Messmethode,
   Kalibrierung, Unsicherheit und Provenienz verbunden.
3. **Quellengebunden:** Eine identifizierte Quelle enthält die Aussage. Das
   System bestätigt dadurch noch nicht ihre Wahrheit.
4. **Normativ:** Es handelt sich um eine Regel, Definition oder
   Wertentscheidung.
5. **Interpretativ:** Es handelt sich um eine nachvollziehbare Deutung.
6. **Offen:** Ein notwendiger Beweis, Versuch oder Brückenschritt fehlt.

Diese Trennung klingt unspektakulär, verhindert aber fundamentale Fehler. Ein
mathematischer Beweis sagt nichts darüber, ob ein Sensor richtig kalibriert
war. Ein Messwert beweist keinen Allgemeinsatz. Eine DOI macht ein Dokument
zitierbar und unveränderlich auffindbar, aber nicht automatisch richtig. Und
eine technische Möglichkeit ist noch keine Erlaubnis, einen Aktor zu bewegen.

## Was tatsächlich maschinell bewiesen ist

Die neue Formalisierung umfasst 21 Sätze in Lean 4.19.0. Lean ist ein
Beweisassistent, dessen Kernel jeden Ableitungsschritt kontrolliert. Der
Kandidat wurde ohne ausgelassene Beweise und ohne projektspezifische Axiome
kompiliert.

Bewiesen ist unter anderem:

- Ein bestehendes Erkenntnisobjekt bleibt bei einer additiven Erweiterung
  erhalten.
- Die Vereinigung zweier Objektbestände ist in ihrer Mitgliedschaft
  kommutativ, assoziativ und idempotent. Reihenfolge und Doppellieferung ändern
  das Ergebnis auf dieser Ebene nicht.
- Zwei Replikate konvergieren wieder, wenn sie dieselben Updates erhalten und
  dieselbe Policy benutzen.
- Ein bereits vollständiger Begründungspfad bleibt nach einer Erweiterung
  auffindbar.
- Ein expliziter Konflikt bleibt sichtbar.
- Exakte Neuheit ist immer relativ zum untersuchten Korpus und kein Beweis
  weltweiter wissenschaftlicher Priorität.
- Dieselbe Ereignisliste kann mit verschiedenen physischen
  Ursachenzuschreibungen verbunden sein. Ein Trace allein bestimmt also keine
  physische Ursache.
- Eine reale Digital-Twin-Wirkung benötigt im Modell eine qualifizierte
  Beobachtung und eine separate Wirkungsquittung.
- Eine proposal-only Analyse autorisiert niemals von selbst eine
  Außenwirkung.

Ebenso wichtig ist das formale Gegenbeispiel: Ein leerer Korpus beantwortet
keine Frage. Die Struktur kann daher nicht garantieren, jede erdenkliche Frage
zu beantworten. Unbekannte Tatsachen, unentscheidbare Probleme, mehrdeutige
Sprache und normative Konflikte bleiben reale Grenzen.

## Warum „Kausalitätsspiegel“ das richtige Bild ist

Stellen wir uns eine Fabrikanlage vor. Ein Temperatursensor meldet 94 Grad. Ein
Modell prognostiziert einen Ausfall. Ein Assistenzsystem empfiehlt, die Anlage
abzuschalten. Ein Mensch bestätigt. Der Aktor reagiert. Später fällt die
Temperatur.

Eine gewöhnliche Logdatei zeigt vielleicht nur Zeitstempel. Ein
Kausalitätsspiegel fragt zusätzlich:

- Welcher Sensor und welche Kalibrierung erzeugten den Wert?
- Welche Zeitbasis und welche Messunsicherheit galten?
- Welche Software- und Modellversion verarbeiteten ihn?
- Welche Eingangsdaten und Prämissen trugen die Prognose?
- War die Abschaltung Empfehlung, Freigabe oder ausgeführte Aktion?
- Bestätigte der Aktor den Befehl?
- Welche Rückmessung belegt die Wirkung?
- Welche alternative Ursache könnte die Abkühlung erklären?

Damit wird aus einer Geschichte ein prüfbarer Graph. Doch auch ein perfekter
Graph beweist nicht automatisch Ursache und Wirkung. Dafür braucht man je nach
Fragestellung Interventionen, Kontrollgruppen, Identifikationsannahmen oder ein
validiertes physikalisches Modell. QIK-VRT erzwingt, dass dieser Brückenschritt
nicht stillschweigend übersprungen wird.

## Vom analogen Sensor bis zum digitalen Zwilling

Die Architektur ist nicht auf reine Informatik beschränkt. Ein analoges Signal
wird durch einen Sensor, eine Übertragungsfunktion, Abtastung, Quantisierung
und Zeitstempel in digitale Daten verwandelt. Wer später aus diesen Daten eine
physikalische Aussage ableiten will, muss die Brücke zurück kennen.

QIK-VRT kann Messwert, Geräteidentität, Kalibrierparameter,
Unsicherheitsmodell, Abtastrate und Auswertecode zusammenbinden. Bei einer
Korrektur wird der alte Stand nicht unsichtbar überschrieben; ein neuer Knoten
verweist auf ihn. So bleibt nachvollziehbar, welche Veröffentlichung oder
Reglerentscheidung auf welchem Messstand beruhte.

Für digitale Zwillinge ist das besonders nützlich. Ein Twin verbindet ein
physisches Objekt mit einem Modell, das laufend Messdaten empfängt und
Prognosen oder Steuerimpulse erzeugt. Fehler entstehen häufig an den
Übergängen: veraltete Modelle, falsche Einheiten, fehlende Kalibrierung,
unbemerkte Datenlücken oder eine Empfehlung, die irrtümlich wie eine
ausgeführte Aktion behandelt wird. Der Kausalitätsspiegel macht diese
Übergänge zu expliziten, prüfbaren Kanten.

In der Regelungstechnik können Sollwert, Zustandsabschätzung, Reglerausgang,
Aktorquittung und Pflanzenantwort getrennt erfasst werden. In der
Nachrichtentechnik kommen Framing, Reihenfolge, Fehlererkennung, Latenz und
Kanalkapazität hinzu. Ein mathematischer Rekonstruktionssatz über endliche
Nachrichten ersetzt keinen realen Kanaltest – aber er sagt präzise, welcher
Teil bereits bewiesen ist.

## Die Quantenebene: wichtig, aber nicht magisch

Warum lohnt es sich, die Architektur bis zur Quantenkausalität zu öffnen?

Quantenexperimente bestehen längst nicht nur aus „Quanten“. Ein klassischer
Computer formuliert den Schaltkreis, ein Compiler übersetzt ihn, ein Backend
hat eine bestimmte Kalibrierung, Messshots werden klassisch gespeichert und
statistisch ausgewertet. Wenn an irgendeiner Stelle Versionen oder
Unsicherheiten fehlen, ist das Ergebnis schwer reproduzierbar.

QIK-VRT kann diese gesamte Kette content-addressiert binden: Schaltkreis,
Compiler, Backend, Kalibrierung, Shots, klassische Auswertung, Nullmodell und
Claim. Neuartige Modelle – etwa Prozesse ohne fest vorgegebene globale
Kausalordnung – können formal beschrieben werden, ohne daraus voreilig einen
nutzbaren Nachrichtenkanal in die Vergangenheit abzuleiten.

Das ist der entscheidende Wert der „Quantenkausalebene“: Sie zwingt das System,
zwischen mathematischem Modell, experimenteller Anordnung, beobachteter
Statistik und physikalischer Interpretation zu unterscheiden. Sie schafft eine
gemeinsame Evidenzsprache für klassische und quantenbasierte Komponenten.

Nicht bewiesen sind damit VRT-Emergenz, ein Quanten-zu-Klassik-Limes, eine
physikalische Retrokausalitätsbrücke oder ein realer QPU-End-to-End-Kanal. Diese
Punkte bleiben als konkrete offene Forschungsziele erhalten.

## Wie ein verteilter Erkenntnisbaum wachsen kann

Jedes akzeptierte Objekt trägt eine Inhaltsidentität. Repositories können ihre
Objektmengen vereinigen, ohne alte Knoten umzuschreiben. Erhalten zwei
Replikate schließlich dieselben zulässigen Objekte und wenden sie dieselben
Regeln an, entsteht dieselbe Projektion. Widersprüche werden nicht
wegoptimiert, sondern mit ihren Quellen und Methoden erhalten.

Das ermöglicht eine andere Art von Suche. Statt nur ähnliche Wörter zu finden,
kann ein System nach folgenden Beziehungen fragen:

- Welche Claims hängen von dieser Messung ab?
- Welche Version eines Satzes wurde tatsächlich vom Kernel geprüft?
- Welcher Gegenbeleg bestreitet eine Aussage?
- Welche Antworten besitzen einen vollständigen Evidenzpfad?
- Wo fehlt nur eine Kalibrierung, wo ein Experiment und wo eine Definition?

Eine Antwort kann dann als begrenzter Begründungsgraph ausgegeben werden. Das
ist für Menschen und künstlich-kognitive Systeme nützlich, weil nicht nur das
Ergebnis, sondern auch sein Weg überprüfbar wird.

Ob dadurch *jede* Nutzerin und *jeder* Nutzer kognitiv besser wird, ist eine
empirische Frage. Man müsste „Verbesserung“ messen, Vergleichsgruppen bilden,
Aufgaben vorab festlegen, Datenschutz beachten und die Studie replizieren. Die
Architektur macht eine solche Prüfung möglich; sie ersetzt sie nicht.

## Warum Mathematiker und Physiker davon profitieren können

Mathematische Ergebnisse leben in Abhängigkeiten. Ein Satz kann korrekt
bewiesen sein, aber auf einer Definition beruhen, die später geändert wurde.
QIK-VRT bindet die genaue Aussage, Bibliotheksversion, Prämissen und das
Kernel-Receipt. Korrekturen werden neue Knoten. So wächst ein versionierter
Beweisgraph, in dem sichtbar bleibt, was womit bewiesen wurde.

Für Experimentalphysik gilt Entsprechendes. Rohdaten, Geräteaufbau,
Kalibrierung, Auswertecode, Unsicherheitsrechnung und Interpretation bleiben
unterscheidbar. Zwei konkurrierende Modelle können dieselben Daten referenzieren,
ohne dass eines die Daten des anderen überschreibt. Das erleichtert
Replikation, Metaanalyse und die genaue Lokalisierung wissenschaftlicher
Kontroversen.

Der langfristige Wert liegt deshalb nicht in einer gigantischen Datenablage,
sondern in einem feingliedrigen Netz überprüfbarer Beziehungen. Je mehr
Fachgebiete ihre eigenen Nachweisregeln sauber anschließen, desto besser kann
das Mesh über Disziplingrenzen hinweg suchen, ohne die Unterschiede zwischen
Beweis, Messung und Interpretation einzuebnen.

## Verantwortung ist ein Teil des Protokolls

Technische Macht braucht überprüfbare Verantwortung. Ein System, das eine
Aussage klassifiziert oder sogar formal beweist, darf deshalb nicht automatisch
publizieren, mergen oder einen realen Aktor bewegen. QIK-VRT trennt Analyse,
Review, Repository-Promotion, Zenodo-Ablage, IETF-Einreichung und physische
Wirkung.

Diese Trennung ist auch für Audits künstlicher Intelligenz wichtig. Ein
prüfbares System sollte zeigen können, welche Daten und Modellversion eine
Ausgabe erzeugten, welche Unsicherheit bekannt war, welcher Mensch oder Prozess
freigab und welche Wirkung beobachtet wurde. Das unterstützt
Auditbereitschaft. Es ist aber weder automatisch eine EU-AI-Act-Zertifizierung
noch Rechtsberatung; konkrete Pflichten hängen von System, Rolle, Risiko und
aktuellem Recht ab.

## Ein großer Anspruch – präzise genug, um nützlich zu sein

QIK-VRT beweist nicht, alles zu wissen. Es beweist etwas praktisch
Grundlegenderes: In dem angegebenen endlichen Modell können Erkenntnisobjekte
statusgebunden wachsen, Konflikte erhalten bleiben, Mesh-Replikate stabil
vereinigen und Außenwirkungen getrennt autorisiert werden.

Damit entsteht kein Orakel. Es entsteht eine belastbare Infrastruktur für
Forschung: Eine Behauptung kann zur prüfbaren Frage werden. Ein fehlender
Nachweis wird sichtbar. Ein Experiment kann genau dort ansetzen. Ein formaler
Beweis kann sauber integriert werden. Und eine spätere Korrektur zerstört
nicht die Geschichte, sondern erweitert sie.

Das ist der Sinn des Kausalitätsspiegels: Nicht die Welt durch ein Repository
zu ersetzen, sondern die Wege unseres Wissens so genau zu spiegeln, dass
Menschen und Maschinen sie gemeinsam prüfen, bestreiten und verbessern können.

---

*Geltungsgrenze: Die 21 Lean-Sätze betreffen das ausdrücklich kodierte endliche
Modell. Universelle Wahrheit, weltweite wissenschaftliche Neuheit,
vollständige Sprachformalisierung, Antworten auf jede Frage und eine physische
Quanten- oder Retrokausalitätsbrücke werden nicht beansprucht.*
