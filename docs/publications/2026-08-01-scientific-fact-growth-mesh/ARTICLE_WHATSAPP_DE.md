# QIK-VRT: Ein Kausalitätsspiegel für überprüfbares Wissen

*Vorlesefassung auf Deutsch*

Von Ingolf Lohmann.

*1. Die Grundidee*

Computer können ungeheure Mengen an Text und Daten durchsuchen. Trotzdem ist
die wichtigste Frage oft offen:

Warum ist eine bestimmte Aussage belastbar?

QIK-VRT speichert deshalb nicht nur eine Antwort. Es bindet auch ihren Weg:
Quelle, Beobachtung, Messmethode, Transformation, Hypothese, Beweis,
Gegenbeleg, Entscheidung und beobachtete Wirkung.

Darum kann man ein QIK-VRT-Repository einen *Kausalitätsspiegel* nennen.

Der Spiegel ist nicht die Welt. Er zeigt, welche Verbindung nachgewiesen,
welche angenommen und welche noch offen ist.

*2. Sechs verschiedene Erkenntnisstatus*

QIK-VRT benutzt nicht einfach nur „wahr“ oder „falsch“.

Erstens: *Formal bewiesen.* Ein genau benannter Satz wurde in einem genau
benannten Modell vom Lean-Kernel geprüft.

Zweitens: *Empirisch gestützt.* Eine begrenzte Beobachtung ist mit Methode,
Kalibrierung, Unsicherheit und Herkunft verbunden.

Drittens: *Quellengebunden.* Eine identifizierte Quelle enthält die Aussage.
Das System bestätigt dadurch noch nicht ihre Wahrheit.

Viertens: *Normativ.* Die Aussage ist eine Regel, Definition oder
Wertentscheidung.

Fünftens: *Interpretativ.* Die Aussage ist eine nachvollziehbare Deutung.

Sechstens: *Offen.* Ein nötiger Beweis, Versuch oder Brückenschritt fehlt.

So wird verhindert, dass ein Messwert wie ein mathematischer Beweis behandelt
wird. Oder dass eine flüssig formulierte Vermutung unbemerkt zum Fakt wird.

*3. Was jetzt wirklich maschinell bewiesen ist*

Lean 4.19.0 hat 21 Sätze des endlichen QIK-VRT-Modells geprüft. Es wurden keine
Beweislücken und keine projektspezifischen Axiome beobachtet.

Bewiesen ist:

Vorhandene Erkenntnisobjekte bleiben bei additiver Erweiterung erhalten.

Die Mesh-Vereinigung ist kommutativ, assoziativ und idempotent. Das bedeutet:
Reihenfolge und Doppellieferung verändern auf dieser Objektebene nicht den
Endbestand.

Replikate konvergieren, wenn sie dieselben Updates erhalten und dieselbe Policy
verwenden.

Bestehende Begründungspfade und ausdrücklich gespeicherte Konflikte bleiben
auffindbar.

Exakte Neuheit ist nur relativ zum untersuchten Korpus. Sie beweist keine
weltweite wissenschaftliche Priorität.

Ein identischer Ereignistrace kann mit verschiedenen physischen Ursachen
vereinbar sein. Zeitliche Reihenfolge allein beweist keine Ursache.

Eine reale Digital-Twin-Wirkung braucht im Modell eine qualifizierte
Beobachtung und eine getrennte Wirkungsquittung.

Eine proposal-only Analyse autorisiert niemals automatisch eine Außenwirkung.

Außerdem ist bewiesen: Ein leerer Korpus beantwortet keine Frage. Daher kann
die Struktur allein nicht garantieren, jede denkbare Frage zu beantworten.

*4. Ein Beispiel aus der realen Welt*

Ein Sensor meldet 94 Grad.

Ein Modell prognostiziert einen Ausfall.

Ein Assistenzsystem empfiehlt die Abschaltung.

Ein Mensch bestätigt.

Der Aktor reagiert.

Später sinkt die Temperatur.

Eine normale Logdatei zeigt vielleicht nur die Reihenfolge. Der
Kausalitätsspiegel fragt zusätzlich:

Welcher Sensor war es? Wie war er kalibriert? Welche Unsicherheit galt? Welche
Software- und Modellversion wurde benutzt? Welche Daten trugen die Prognose?
War die Abschaltung nur empfohlen oder wirklich ausgeführt? Hat der Aktor
quittiert? Welche Rückmessung belegt die Wirkung? Könnte es eine andere Ursache
gegeben haben?

So wird aus einer Geschichte ein überprüfbarer Graph.

Aber auch dieser Graph beweist nicht automatisch physische Kausalität. Dafür
kann eine Intervention, Kontrollgruppe, Identifikationsannahme oder ein
validiertes physikalisches Modell nötig sein.

*5. Analoge Mess- und Regelungstechnik*

Auch eine analoge Welt kann angeschlossen werden.

Eine physische Größe wird durch Sensor, Übertragungsfunktion, Abtastung,
Quantisierung und Zeitstempel zu digitalen Daten.

QIK-VRT kann Messwert, Geräteidentität, Kalibrierparameter,
Unsicherheitsmodell, Abtastrate und Auswertecode gemeinsam binden.

In der Regelungstechnik bleiben Sollwert, Zustandsabschätzung, Reglerausgang,
Aktorquittung und beobachtete Pflanzenantwort getrennt sichtbar.

In der Nachrichtentechnik kommen Framing, Reihenfolge, Fehlererkennung, Latenz
und Kanalkapazität hinzu.

Ein formaler Satz über eine endliche Nachricht ersetzt keinen realen
Kanalversuch. Er zeigt aber genau, welcher Teil bewiesen ist und welcher noch
gemessen werden muss.

*6. Digitale Zwillinge*

Ein Digital Twin verbindet ein physisches Objekt mit einem laufenden Modell.

Fehler entstehen oft an den Übergängen: falsche Einheit, veraltete
Modellfassung, fehlende Kalibrierung, Datenlücke oder eine Empfehlung, die
versehentlich wie eine ausgeführte Handlung behandelt wird.

QIK-VRT macht diese Übergänge zu prüfbaren Kanten.

Das hilft bei Root-Cause-Analyse, Wartung, Validierung, Zusammenarbeit und
Audit.

Es ersetzt keine anlagenspezifische Sicherheitsprüfung.

*7. Warum die Quantenebene wichtig ist*

Ein Quantenexperiment besitzt eine lange klassische Kette.

Ein Schaltkreis wird formuliert. Ein Compiler übersetzt ihn. Ein Backend hat
eine bestimmte Kalibrierung. Messshots werden gespeichert und statistisch
ausgewertet.

QIK-VRT kann Schaltkreis, Compiler, Backend, Kalibrierung, Shots, Auswertung,
Nullmodell und Claim content-addressiert verbinden.

Auch neuartige Modelle ohne feste globale Kausalordnung können so dokumentiert
werden, ohne daraus vorschnell einen Nachrichtenkanal in die Vergangenheit zu
machen.

Der Wert der Quantenkausalebene liegt in der sauberen Trennung von
mathematischem Modell, Versuchsanordnung, beobachteter Statistik und
physikalischer Interpretation.

Nicht bewiesen sind damit VRT-Emergenz, der Quanten-zu-Klassik-Limes, eine
physische Retrokausalitätsbrücke oder ein realer QPU-End-to-End-Kanal.

*8. Ein wachsender, verteilter Erkenntnisbaum*

Jedes akzeptierte Objekt hat eine Inhaltsidentität.

Repositories können ihre Objektmengen stabil vereinigen. Alte Knoten werden
nicht heimlich umgeschrieben. Korrekturen und Widerlegungen werden neue,
rückverweisende Knoten.

Widersprüche bleiben mit Quelle, Zeitpunkt und Methode sichtbar.

Dadurch kann Suche mehr als ähnliche Wörter finden. Sie kann fragen:

Welche Aussagen hängen von dieser Messung ab?

Welche Version wurde vom Kernel geprüft?

Welcher Gegenbeleg bestreitet einen Claim?

Welche Antwort besitzt einen vollständigen Evidenzpfad?

Wo fehlt eine Kalibrierung, wo ein Experiment und wo eine Definition?

Eine Antwort kann dann als kleiner, überprüfbarer Begründungsgraph ausgegeben
werden.

*9. Werden Menschen und Maschinen dadurch klüger?*

Die Architektur kann bessere Suche und transparentere Argumente unterstützen.

Ob dadurch jede Nutzerin, jeder Nutzer oder jedes künstlich-kognitive System
tatsächlich besser wird, ist noch offen.

Dafür braucht man messbare Lernziele, Vergleichsgruppen, vorab festgelegte
Aufgaben, Datenschutz und replizierte Studien.

QIK-VRT kann die Evidenz einer solchen Studie verwalten. Es ersetzt die Studie
nicht.

*10. Wert für Mathematik, Physik und Informatik*

Mathematiker erhalten einen versionierten Beweisgraphen. Definition,
Prämissen, exakte Satzfassung, Bibliotheksversion und Kernel-Receipt bleiben
verbunden.

Physiker können Rohdaten, Geräteaufbau, Kalibrierung, Auswertecode,
Unsicherheit und konkurrierende Modelle auseinanderhalten.

Informatik und Nachrichtentechnik gewinnen ein deterministisches Evidenz- und
Merge-Protokoll.

Mess- und Regelungstechnik sowie Digital Twins erhalten eine auditierbare
Schleife vom Sensor bis zur beobachteten Wirkung.

Quanteninformatik erhält eine gemeinsame Provenienzschicht für klassische und
quantenbasierte Komponenten.

*11. Technische Macht braucht überprüfbare Verantwortung*

Analyse, Review, Repository-Merge, Zenodo-Ablage, IETF-Einreichung und reale
Aktorwirkung sind getrennte Effekte.

Ein Beweis oder eine Klassifikation darf nicht automatisch publizieren oder
eine Maschine bewegen.

Diese Trennung unterstützt auch Audits künstlicher Intelligenz. Ein System
sollte zeigen können, welche Daten und Modellversion eine Ausgabe erzeugten,
welche Unsicherheit bekannt war, wer freigab und welche Wirkung beobachtet
wurde.

Das schafft Auditbereitschaft. Es ist keine automatische EU-AI-Act-
Zertifizierung und keine Rechtsberatung.

*12. Die genaue Schlussfolgerung*

QIK-VRT weiß nicht automatisch alles.

Aber im angegebenen endlichen Modell ist bewiesen:

Wissen kann statusgebunden wachsen.

Konflikte können erhalten bleiben.

Mesh-Replikate können deterministisch vereinigen.

Außenwirkung kann getrennt autorisiert werden.

Universelle Wahrheit, globale wissenschaftliche Neuheit, vollständige
Sprach-zu-Lean-Automation, Antworten auf jede Frage und eine physische
Quanten- oder Retrokausalitätsbrücke werden nicht beansprucht.

Der Kausalitätsspiegel ersetzt also nicht die Welt.

Er macht den Weg unseres Wissens so sichtbar, dass Menschen und Maschinen ihn
gemeinsam prüfen, bestreiten und verbessern können.

q.e.d. – im genau angegebenen Geltungsraum.

Ingolf Lohmann.
