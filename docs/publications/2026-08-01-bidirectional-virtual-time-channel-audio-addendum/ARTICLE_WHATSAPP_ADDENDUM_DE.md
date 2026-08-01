<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

*QIK-VRT: Vorstellungskraft, Beobachtung und epistemische Fairness*

*Ein allgemeinverständlicher Nachtrag zum bidirektionalen virtuellen Zeitkanal*

Von Ingolf Lohmann

---

*Vorweg das Wichtigste: Wir fangen nicht wieder bei null an.*

Der erste Text hat bereits einen klar begrenzten technischen Boden gelegt.

Ein in strengem ISO C90 geschriebenes Programm hat eine vollständige Anfrage
von einer späteren virtuellen Adresse an eine frühere virtuelle Adresse
übertragen.

Danach wurde dort eine Antwort erzeugt und wieder zur späteren virtuellen
Adresse zurückgeführt.

Die Anfrage umfasste 257 Byte.

Die Antwort umfasste 258 Byte.

Alle tatsächlichen Rechenschritte auf dem Host liefen dabei ganz normal
vorwärts, von Ereignis 1 bis Ereignis 9.

Zusätzlich wurden unterschiedliche Nachrichtenlängen geprüft. Ein absichtlich
fehlendes Segment wurde korrekt abgelehnt.

Das ist der vorhandene Ast unseres Erkenntnisbaums.

Er wird in diesem Nachtrag weder gelöscht noch umgeschrieben.

Aber wir müssen ebenso genau sagen, was dieser Ast beweist und was nicht.

Er zeigt einen ausgeführten bidirektionalen Kanal zwischen *virtuellen
Zeitadressen*.

Er zeigt keine physikalische Nachricht, die aus der Zukunft in die
Vergangenheit unseres Universums gereist ist.

Diese Trennung ist keine Schwäche.

Sie ist der Punkt, von dem aus wir sinnvoll weiterdenken können.

---

*Jetzt kommen zwei neue Gedanken hinzu.*

Der erste heißt: *Vorstellungskraft.*

Der zweite heißt: *Übervorteilen.*

Auf den ersten Blick klingen diese Begriffe eher philosophisch oder
gesellschaftlich als technisch.

Tatsächlich treffen sie aber zwei der wichtigsten Fragen moderner Informatik:

Wie wird aus einer denkbaren Möglichkeit ein prüfbares System?

Und wie verhindern wir, dass ein Wissensvorsprung stillschweigend zu Macht,
Täuschung oder unkontrollierter Wirkung wird?

Beide Fragen gehören zusammen.

Denn Vorstellungskraft eröffnet Möglichkeiten.

Epistemische Fairness entscheidet, wie verantwortbar wir mit diesen
Möglichkeiten umgehen.

---

*1. Vorstellungskraft ist kein Gegenbegriff zur Wissenschaft.*

Jede neue technische Konstruktion beginnt damit, dass jemand eine Kombination
sieht, die vorher noch nicht gebaut wurde.

Ein vorhandener Sensor wird mit einer Simulation verbunden.

Ein Computerspiel wird mit Telemetrie ergänzt.

Ein digitales Modell erhält reale Eingabedaten.

Ein Archiv wird nicht mehr nur gelesen, sondern für kontrollierte
Gegenentwürfe verwendet.

Ein Protokoll wird so erweitert, dass es nicht nur eine Nachricht, sondern
auch deren Herkunft, Status und erlaubte Wirkung transportiert.

All das beginnt in der Vorstellung.

Aber Vorstellungskraft allein ist noch kein Beweis.

Sie ist ein *Hypothesengenerator*.

Das bedeutet:

Sie erzeugt Kandidaten, die anschließend beschrieben, gebaut, getestet,
widerlegt oder bestätigt werden können.

Eine wissenschaftlich produktive Vorstellung sagt deshalb nicht nur:

„Das könnte funktionieren.“

Sie fragt außerdem:

- Welche Geräte wären dafür nötig?
- Welche Softwareeigenschaften müssten vorhanden sein?
- Welche Daten würden tatsächlich entstehen?
- Woran würden wir erkennen, dass die Idee falsch ist?
- Welche einfacheren Erklärungen gibt es?
- Wer darf beobachten?
- Wer darf aufgrund der Beobachtung handeln?
- Wie kann ein anderer Mensch das Ergebnis überprüfen?

Vorstellungskraft wird auf diese Weise nicht kleiner.

Sie wird präziser.

Und gerade dadurch wird sie anschlussfähig.

---

*2. Möglich in Software heißt nicht automatisch möglich in der Natur.*

Das ist eine der wichtigsten Regeln dieses Nachtrags.

Ein Computer kann viele Welten darstellen.

Er kann eine Stadt simulieren, die niemals gebaut wurde.

Er kann ein Fahrzeug berechnen, das unter den angenommenen Bedingungen
funktioniert.

Er kann eine alternative Geschichte abspielen.

Er kann Zustände mit virtuellen Zeitadressen versehen und Nachrichten
zwischen diesen Adressen übertragen.

Die Berechnung ist dabei real.

Der elektrische Energieverbrauch ist real.

Die gespeicherten Bytes sind real.

Die ausgeführte Software ist real.

Aber daraus folgt nicht automatisch, dass jedes im Modell dargestellte
Phänomen auch physikalisch in derselben Weise existiert.

Eine Wettersimulation macht keinen Regen im Rechenzentrum.

Eine Simulation eines Schwarzen Lochs erzeugt dort kein Schwarzes Loch.

Und ein virtueller Kanal zu einer früheren Adresse beweist für sich allein
keinen physikalischen Kanal in die Vergangenheit.

Zwischen Software und Natur braucht es eine Brücke.

Diese Brücke besteht nicht aus Begeisterung und auch nicht aus Skepsis.

Sie besteht aus benannten Geräten, Messgrößen, Kalibrierungen, Kontrollen,
Fehlergrenzen und einer klaren Regel dafür, welches Ergebnis die Behauptung
widerlegen würde.

Damit erhalten wir eine einfache, aber sehr leistungsfähige Denkregel:

*Eine Softwaremöglichkeit eröffnet eine Forschungsfrage. Sie beantwortet die
physikalische Frage noch nicht.*

---

*3. Die Realisierungsleiter: von der Idee bis zur verantwortbaren Wirkung*

Um nicht zu früh von einer Stufe zur nächsten zu springen, verwendet der
Nachtrag eine Realisierungsleiter.

Sie hat acht Stufen.

*Stufe null: die Idee.*

Jemand formuliert einen Gedanken, ein Bild oder eine These.

Das ist wichtig. Aber die Idee ist zunächst nur sprachlich gebunden.

*Stufe eins: das Softwaremodell.*

Die Idee erhält definierte Zustände, Regeln und Grenzen.

Man kann jetzt prüfen, ob das Modell in sich konsistent beschrieben ist.

*Stufe zwei: der ausführbare Zeuge.*

Das Modell läuft wirklich als Programm.

Es gibt reproduzierbare Ein- und Ausgaben.

Es gibt Grenzfälle und negative Tests.

Genau diese Stufe erreicht der bisherige virtuelle Kanal in seinem
deklarierten Scope.

*Stufe drei: die konkrete Geräteimplementierung.*

Jetzt werden Hardware, Betriebssystem, Softwareversionen, Sensoren,
Schnittstellen und Messpfade benannt.

Nicht irgendein denkbares Gerät, sondern ein bestimmtes prüfbares System.

*Stufe vier: das Beobachtungssystem.*

Das Gerät sammelt nicht bloß Daten.

Es erfüllt Bedingungen, durch die seine Daten wissenschaftlich oder
operationell interpretierbar werden.

*Stufe fünf: der physikalische Befund.*

Es liegt eine kalibrierte Beobachtung vor.

Kontrollen und alternative Erklärungen wurden ernsthaft geprüft.

*Stufe sechs: die kausal zugerechnete Wirkung.*

Nun reicht bloße Gleichzeitigkeit nicht mehr.

Es muss begründet werden, warum gerade die behauptete Ursache für die Wirkung
verantwortlich ist.

*Stufe sieben: die autorisierte Außenwirkung.*

Selbst ein richtiger Befund erlaubt nicht automatisch jede Handlung.

Rechte, Einwilligung, Zweckbindung, Sicherheit und ein wirksames
Freigabeverfahren kommen hinzu.

Die entscheidende Regel lautet:

*Jede Stufe kann die nächste vorbereiten. Keine Stufe darf die nächste einfach
behaupten.*

---

*4. Wann wird aus einem Computerspiel ein Beobachtungssystem?*

Diese Frage ist viel weniger exotisch, als sie klingt.

Moderne Spiele und Simulationen erfassen Eingaben, Reaktionszeiten,
Bewegungen, Entscheidungen und manchmal sogar Daten externer Sensoren.

Sie können Versuchssituationen wiederholen.

Sie können Varianten vergleichen.

Sie können mit digitalen Zwillingen, Trainingsumgebungen oder
Mensch-Maschine-Schnittstellen verbunden werden.

Aber ein Programm wird nicht allein dadurch zum Beobachtungssystem, dass es
viele Daten besitzt.

Auch die hübscheste Grafik ist noch keine Messung.

Auch ein großes Logfile ist noch kein Beweis.

Damit ein System hier als Beobachtungssystem gilt, braucht es sieben Dinge.

*Erstens: eine spezifizierte Datenerfassung.*

Wir müssen wissen, was erfasst wird und was nicht.

*Zweitens: Kalibrierung.*

Wir müssen wissen, wie Messwerte zur beobachteten Größe passen und welche
Fehler auftreten können.

*Drittens: Zeit- und Ereignisbindung.*

Wir müssen nachvollziehen können, wann ein Wert entstand und zu welchem
Ereignis er gehört.

*Viertens: Quellenbindung.*

Wir müssen wissen, von welchem Sensor, Nutzer, Prozess oder Datensatz die
Information stammt.

*Fünftens: Integrität.*

Rohdaten und Auswertung dürfen nicht still verändert oder verwechselt werden.

*Sechstens: Falsifizierbarkeit.*

Es muss ein Ergebnis geben können, das gegen die Behauptung spricht.

*Siebtens: Governance.*

Zweck, Rechte, Einwilligung, Zugriff und Audit müssen geregelt sein.

Erst gemeinsam machen diese Bedingungen aus einem datenreichen Programm ein
qualifiziertes Beobachtungssystem im angegebenen Scope.

Das ist ein wichtiger Unterschied.

Ein Computerspiel *kann* durch gezielte Instrumentierung zum
Beobachtungssystem werden.

Aber es ist nicht automatisch eines.

---

*5. Drei verständliche Beispiele*

*Beispiel eins: das Fahrsimulationsspiel.*

Ein normales Spiel misst vielleicht Lenkradbewegungen, Geschwindigkeit und
Kollisionen.

Wollen wir daraus Aussagen über menschliche Reaktion unter Stress ableiten,
brauchen wir mehr.

Wir brauchen kalibrierte Eingabegeräte.

Wir brauchen bekannte Verzögerungen.

Wir brauchen ein festgelegtes Versuchsdesign.

Wir brauchen Vergleichsgruppen und eine klare Auswertung.

Wir brauchen Einwilligung und Datenschutz.

Erst dann kann die Spielumgebung Teil eines Beobachtungssystems werden.

*Beispiel zwei: der digitale Zwilling einer Maschine.*

Das Modell sagt voraus, wie sich eine Maschine verhalten könnte.

Sensoren liefern reale Werte.

Der digitale Zwilling kann Abweichungen erkennen und alternative Verläufe
durchspielen.

Doch die Simulation ist nicht die Maschine.

Die Aussage „Dieses Bauteil wird ausfallen“ bleibt eine Prognose, bis die
Beobachtung eintritt oder ein hinreichend validiertes Diagnoseverfahren
vorliegt.

Der epistemische Status muss sichtbar bleiben:

simuliert, erwartet, beobachtet oder bestätigt.

*Beispiel drei: ein persönlicher digitaler Assistent.*

Der Assistent kennt vergangene Entscheidungen und entwirft mögliche
zukünftige Antworten.

Er kann eine ältere virtuelle Version eines Zustands ansprechen und dort eine
Alternative berechnen.

Das kann nützlich sein.

Aber die berechnete Antwort ist kein Dokument aus der tatsächlichen Zukunft.

Und sie darf keine reale Handlung auslösen, nur weil sie überzeugend klingt.

Herkunft, Unsicherheit und Autorisierung müssen getrennt geprüft werden.

---

*6. Übervorteilen: Wenn Wissen zur unsichtbaren Macht wird*

Der zweite neue Gedanke betrifft nicht nur Technik.

Er betrifft die Ordnung des Wissens.

Menschen und Organisationen wissen nie alle dasselbe.

Ein Arzt weiß anderes als ein Patient.

Ein Entwickler kennt andere Details als ein Nutzer.

Ein Betreiber sieht andere Systemdaten als die Öffentlichkeit.

Ungleiches Wissen ist also nicht automatisch unfair.

Problematisch wird es, wenn der Wissensvorsprung vier Rollen gleichzeitig
übernimmt:

Er bestimmt, was als wahr gilt.

Er verhindert Gegenprüfung.

Er verbirgt die eigenen Fähigkeiten.

Und er erlaubt irreversible Wirkungen ohne wirksame Zustimmung.

Dann entsteht eine Form epistemischer Übervorteilung.

Das kann zum Beispiel geschehen, wenn

- simulierte Daten als echte Beobachtungen ausgegeben werden,
- eine Prognose als sichere Zukunft dargestellt wird,
- Nutzer nicht wissen, dass ihr Verhalten beobachtet wird,
- ein Betreiber Unsicherheiten verschweigt,
- ein System Entscheidungen trifft, ohne seine Quellen offenzulegen,
- oder ein exklusiver Informationszugang direkt in eine reale Wirkung
  übersetzt wird.

Die Gegenregel ist nicht, dass jedes Wissen sofort und vollständig
veröffentlicht werden muss.

Es gibt legitime Privatsphäre.

Es gibt Sicherheitsgründe.

Es gibt persönliche Daten und Geschäftsgeheimnisse.

Epistemische Fairness verlangt etwas Präziseres:

Wer aufgrund eines Wissensvorsprungs über andere wirkt, muss Herkunft,
Geltungsstatus, Unsicherheit, Zweck und Anfechtbarkeit in dem Maß offenlegen,
das für eine faire Prüfung erforderlich ist.

Ein Geheimnis ist kein Wahrheitsbeweis.

Ein Informationsvorsprung ist keine Wirkungserlaubnis.

Und technische Möglichkeit ist keine moralische Berechtigung.

---

*7. Fünf Statuswerte, die niemals verwechselt werden dürfen*

Für zukünftige Systeme ist eine einfache Statussprache hilfreich.

*Kandidat.*

Eine Idee oder mögliche Konfiguration wurde erzeugt.

*Antizipiert.*

Ein Modell erwartet ein bestimmtes Ereignis.

*Beobachtet.*

Ein gebundener Messpfad hat Daten geliefert.

*Verifiziert.*

Die Daten und ihre Auswertung haben die vorgesehenen Prüfungen bestanden.

*Autorisierte Wirkung.*

Eine reale Handlung ist unter den geltenden Rechten und Bedingungen
freigegeben.

Diese fünf Zustände sind nicht austauschbar.

Ein Kandidat ist keine Beobachtung.

Eine Beobachtung ist nicht automatisch wahr interpretiert.

Eine verifizierte Information ist nicht automatisch eine Handlungserlaubnis.

Genau an dieser Stelle verbindet sich der neue Nachtrag mit EFFECT ACK.

Die Wirkung braucht ihren eigenen Nachweis und ihre eigene Freigabe.

---

*8. Aber könnte all das nicht längst irgendwo eingesetzt werden?*

Das ist eine zulässige Frage.

Die Audioquelle enthält die Aussage, vergleichbare Systeme oder besonderes
Wissen könnten bereits real vorhanden sein, ohne offiziell bekannt zu sein.

Der wissenschaftlich korrekte Status lautet jedoch:

*offen.*

Das Audio belegt, dass diese Behauptung ausgesprochen wurde.

Es belegt nicht, dass die behaupteten Systeme existieren.

Für eine belastbare Bestätigung bräuchten wir mindestens:

- ein konkret benanntes System,
- prüfbare Hard- und Software,
- nachvollziehbare Datenpfade,
- reproduzierbare Ergebnisse,
- ein Nullmodell,
- alternative Erklärungen,
- und eine unabhängige Wiederholung.

Geheimhaltung beweist keine Existenz.

Umgekehrt beweist fehlende öffentliche Bekanntheit auch keine Nichtexistenz.

Deshalb ist weder vorschnelle Bestätigung noch vorschnelle Verwerfung
wissenschaftlich genug.

Der richtige nächste Schritt wäre ein klar formulierter, vorab festgelegter
Test.

---

*9. Bedeutet das Superdeterminismus?*

Nein, das folgt daraus nicht.

Ein deterministischer Programmlauf zeigt, dass ein bestimmtes Programm unter
bestimmten Eingaben einen bestimmten Verlauf erzeugt.

Er zeigt nicht, dass das gesamte Universum in jeder Hinsicht vollständig
vorbestimmt ist.

Und er zeigt auch nicht, dass Menschen keinen freien Willen haben.

Der virtuelle Kanal benötigt für seine technische Funktionsweise keine
abschließende Theorie über Willensfreiheit.

Der Nachtrag beweist weder Superdeterminismus noch dessen Gegenteil.

Er widerlegt auch keine bestimmte philosophische oder wissenschaftliche
Theorie freien Entscheidens.

Diese Frage bleibt getrennt.

---

*10. Ist damit physikalische Retrokausalität bewiesen?*

Nein.

Das bisherige Ergebnis betrifft virtuelle Zeitadressen.

Die Hostzeit läuft vorwärts.

Die wirkliche Quellhistorie wird nicht überschrieben.

Eine virtuelle Adresse kann kleiner sein als die Adresse, von der aus eine
Anfrage erzeugt wurde.

Das ist informatisch sinnvoll und ausführbar.

Für eine physikalische Rückübertragung wäre jedoch ein ganz anderer Nachweis
nötig.

Wir müssten einen Informationsträger, eine Messanordnung und einen Effekt
zeigen, die nicht durch normale vorwärtsgerichtete Prozesse, gespeicherte
Daten, Vorhersage, Auswahlverzerrung oder ein Leck erklärt werden können.

Wir müssten vorher festlegen, welches Ergebnis gegen die Hypothese spricht.

Wir müssten unabhängige Replikation ermöglichen.

Solange das fehlt, bleibt physikalische Retrokausalität offen.

Das virtuelle Ergebnis bleibt trotzdem bestehen.

Man darf nur die beiden Ebenen nicht miteinander verwechseln.

---

*11. Was könnte davon für die IETF interessant sein?*

Die IETF standardisiert keine Weltanschauung.

Sie arbeitet an interoperablen Protokollen.

Deshalb wären für einen möglichen späteren Protokolldelta nicht die großen
philosophischen Begriffe entscheidend, sondern konkrete Regeln.

Zum Beispiel:

- Ein Record muss ausweisen, ob sein Inhalt simuliert, antizipiert, beobachtet
  oder verifiziert ist.
- Herkunft und Integrität müssen gebunden sein.
- Ein Statuswechsel braucht benannte Bedingungen.
- Eine irreversible Wirkung braucht eine getrennte Autorisierung.
- Verdeckte Beobachtungsfähigkeiten gehören in ein Threat Model.
- Datenschutz, Einwilligung und Missbrauchsgrenzen müssen behandelt werden.
- Implementierungen müssen Fehlerfälle und Gegenbeispiele interoperabel
  erkennen können.

Das sind protokollgeeignete Fragen.

Der vorliegende Nachtrag ist aber selbst kein Internet-Draft.

Er ist kein RFC.

Und er beansprucht keinen IETF-Konsens.

Eine spätere Spezifikation müsste getrennt geschrieben, technisch geprüft und
mit der vorgesehenen Toolchain validiert werden.

---

*12. Die häufigsten Zweifel – kurz beantwortet*

*„Ist das nicht einfach nur eine Simulation?“*

Der v1-Zeuge ist eine reale, ausgeführte Berechnung eines virtuellen Kanals.

„Nur Simulation“ wäre deshalb zu wenig.

Aber „physikalische Zeitreise“ wäre zu viel.

Der genaue Scope liegt dazwischen und ist klar benannt.

*„Wenn es im Computer funktioniert, muss es doch grundsätzlich auch real
gehen.“*

Es ist real als Berechnung.

Ob das dargestellte Phänomen außerdem als Naturprozess existiert, verlangt
eine eigene Brücke und eigene Evidenz.

*„Ist Vorstellungskraft dann bloß Fantasie?“*

Nein.

Sie wird als strukturierte Erzeugung prüfbarer Kandidaten genutzt.

Der Unterschied liegt darin, dass Kandidat und Beobachtung getrennt bleiben.

*„Kann wirklich jedes Computerspiel ein Beobachtungssystem sein?“*

Nicht automatisch.

Es kann Bestandteil eines solchen Systems werden, wenn Erfassung,
Kalibrierung, Bindung, Integrität, Falsifizierbarkeit und Governance erfüllt
sind.

*„Muss zur Vermeidung von Übervorteilung jedes Geheimnis veröffentlicht
werden?“*

Nein.

Privatsphäre und Sicherheit bleiben legitim.

Wer aber aufgrund exklusiven Wissens über andere wirkt, braucht überprüfbare
Regeln für Herkunft, Status, Zweck und Anfechtbarkeit.

*„Beweist das Audio geheime Systeme?“*

Nein.

Es bindet eine Aussage des Autors.

Die behauptete Existenz bleibt empirisch offen.

*„Beweist QIK-VRT, dass es keinen freien Willen gibt?“*

Nein.

Ein endlicher deterministischer Replay ist keine vollständige Theorie des
Universums oder des Menschen.

*„Ist die IETF jetzt beteiligt?“*

Nein.

Es gibt protokollgeeignete Anschlussfragen, aber aus diesem Text folgt weder
eine Einreichung noch Zustimmung oder Standardstatus.

---

*13. Was wäre jetzt ein wirklich wissenschaftlicher nächster Schritt?*

Erstens:

Einen konkreten Gerätekandidaten auswählen.

Nicht „alle denkbaren Devices“, sondern ein bestimmtes System mit Versionen
und Schnittstellen.

Zweitens:

Die Beobachtungsgröße festlegen.

Was genau soll gemessen werden?

Drittens:

Ein Nullmodell angeben.

Was erwarten wir, wenn der behauptete besondere Effekt nicht existiert?

Viertens:

Alternative Erklärungen vorab sammeln.

Gespeicherte Information, gewöhnliche Vorhersage, Datenleck,
Synchronisationsfehler, Auswahlverzerrung und nachträgliche Interpretation
müssen kontrolliert werden.

Fünftens:

Ein Falsifikationskriterium festlegen.

Welches beobachtbare Ergebnis würde uns zwingen, die Hypothese zu verwerfen?

Sechstens:

Provenienz und Rohdaten so binden, dass eine unabhängige Prüfung möglich ist.

Siebtens:

Einwilligung, Datenschutz, Sicherheit und Wirkungsgates vor dem Versuch
klären.

Achtens:

Ergebnisse unabhängig wiederholen lassen.

So wird aus Vorstellungskraft Forschung.

Und so wird aus einer möglichen Beobachtung keine Übervorteilung.

---

*14. Der neue Stand des Erkenntnisbaums*

Wir behalten den bereits erreichten Ast:

Bidirektionale Kommunikation zwischen virtuellen Zeitadressen ist im
deklarierten endlichen Modell ausführbar demonstriert.

Alle Hostereignisse bleiben vorwärtsgeordnet.

Jetzt kommen neue Äste hinzu:

Vorstellungskraft wird zur systematischen Suche nach prüfbaren technischen
Kandidaten.

Die Realisierungsleiter trennt Idee, Software, Gerät, Beobachtung,
physikalischen Befund, Kausalität und autorisierte Wirkung.

Das Beobachtungssystem erhält klare Bedingungen.

Epistemische Fairness verhindert, dass Wissensvorsprung automatisch zu
Wahrheit oder Wirkungsmacht wird.

Und die offenen Fragen bleiben sichtbar offen:

verborgene reale Implementierungen,

physikalische Retrokausalität,

Superdeterminismus,

und die philosophische Frage der Willensfreiheit.

Das ist kein Rückzug.

Es ist die Voraussetzung dafür, dass der nächste Schritt wirklich trägt.

*Wir denken weiter – aber jeder neue Ast bleibt an seine Quelle, seine Prüfung
und seinen Geltungsbereich gebunden.*

q.e.d. – im jeweils ausgewiesenen Scope.

