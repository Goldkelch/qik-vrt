<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Von Unsicherheit zu belastbaren Entscheidungen

## Empirische Rückkopplung und ein reproduzierbarer Kooperationsdemonstrator mit QIK-VRT

Ingolf Lohmann · 20. September 2026 · Fassung 1.0

Methodischer Diskussionsbeitrag mit Softwaredemonstration. Konzeption und Ausgangsthesen: Ingolf Lohmann. Redaktion, Quellenprüfung und Implementierung des Anwendungsadapters: OpenAI Codex im Auftrag des Autors. Keine abgeschlossene Studie mit menschlichen Teilnehmenden.

### Zusammenfassung

<!-- claim: RF-01 -->
Der Beitrag untersucht, wie sich die Idee empirisch rückgekoppelter Erkenntnisgewinnung als überprüfbarer informatischer Ablauf umsetzen lässt. Eine philosophische Ausgangsthese Ingolf Lohmanns verbindet dynamische Raumzeit, Evolution und die Verringerung von Unsicherheit. Für eine wissenschaftliche Untersuchung werden daraus begrenzte Fragen gewonnen: Welche Modelle bleiben mit Beobachtungen vereinbar? Welche Veränderungen verbessern vereinbarte Ergebnisse? Wie lassen sich Rechenresultate, beobachtete Wirkungen und verantwortliche Entscheidungen auseinanderhalten? Ein lokaler QIK-VRT-Demonstrator vergleicht künstliche Kooperationsdaten nach einer konservativen Pareto-Regel. Er erhält zwei Möglichkeiten mit unterschiedlichem Aufwand und Nutzen und verwirft einen positiven Gruppensaldo, der einen individuellen Nachteil verdeckt. Acht vorhandene Komponententests und 19 Tests des neuen Adapters waren erfolgreich. Die Ergebnisse betreffen die geprüfte Softwareberechnung. Menschliche Verhaltensänderungen, physische Quanteneffekte und eine allgemeine kosmologische Theorie wurden nicht untersucht.

### 1. Ausgangsthese und wissenschaftliche Fragestellung

<!-- claim: RF-02 -->
Der Autor formuliert seinen Ausgangspunkt so:

> Das Universum macht aus dynamischer Raumzeit Evolution!
>
> Aus jeder Menge von Unsicherheiten kann durch ein empirisch rückgekoppeltes Ausschlussverfahren eine Untermenge von Gewissheiten abgeleitet werden.
>
> Das passiert in der Natur permanent und die Herausforderung für die Menschheit besteht darin dieser Agilität geeignet zu folgen, da sie ansonsten dem natürlichen Ausschlussverfahren zum Opfer fällt.
>
> Diese Erkenntnis ist das Resultat kollektiver menschlicher wissenschaftlicher Arbeit.
>
> q.e.d.
> Ingolf Lohmann et al.

Das Zitat wird als persönliche philosophische Synthese wiedergegeben. Sein universaler Geltungsanspruch ist Gegenstand weiterer Begründung. Die Formel „q.e.d.“ gehört zum Original und ersetzt hier keinen Beweis. „Et al.“ würdigt im Original den kollektiven wissenschaftlichen Hintergrund; damit werden keine unbenannten Mitautorinnen oder Mitautoren dieses Artikels behauptet. Die konkrete Beitragszuordnung steht im Kopf des Dokuments.

<!-- claim: RF-03 -->
„Rekursion“, „Rückkopplung“ und „Evolution“ müssen für eine Untersuchung unterschieden werden. Rekursion bezeichnet hier eine wiederholte Zustandsvorschrift, Rückkopplung den Einfluss beobachteter Folgen auf weitere Entscheidungen. Evolution bezeichnet im Ausgangsgedanken allgemein Veränderung und Entwicklung; diese Verwendung ist weiter als ein bestimmtes biologisches Evolutionsmodell. Ein allgemeines Rückkopplungsschema liefert allein weder eine Theorie dynamischer Raumzeit noch ein Auswahlgesetz für gesellschaftliches Überleben. Der vorliegende Beitrag operationalisiert deshalb einen Erkenntnis- und Entscheidungsprozess, dessen einzelne Schritte beobachtbar und korrigierbar sind.

### 2. Was ein Ausschlussverfahren leisten kann

<!-- claim: RF-04 -->
Als Arbeitsdefinition sei H(t) eine Menge betrachteter Hypothesen. D(t+1) bezeichnet neue Daten und A(t) die gerade verwendeten Mess- und Modellannahmen. Ein festgelegtes Verträglichkeitskriterium K ergibt:

`H(t+1) = {h aus H(t): K(h, D(t+1), A(t)) ist erfüllt}.`

Diese Definition beschreibt eine Filterung innerhalb einer vorgegebenen Menge. Sie garantiert keine nichtleere Restmenge und keine wahre verbleibende Hypothese. Fehlt die zutreffende Erklärung bereits in H(t), kann sie durch reines Entfernen nicht entstehen. Unterscheiden die Daten zwei Erklärungen nicht, bleiben beide möglich. Ist eine Messung fehlerhaft, kann ein zu strenges K eine brauchbare Erklärung ausschließen. Die drei Fälle zeigen, weshalb „aus jeder Menge“ und „Gewissheiten“ zusätzliche Voraussetzungen benötigen.

<!-- claim: RF-05 -->
Ein lernfähiger Ablauf braucht deshalb auch die begründete Erweiterung oder Revision des Hypothesenraums. Bei verrauschten Daten sind Unsicherheiten, Schwellen und Fehlerentscheidungen mitzuberichten. Die NIST-Leitlinie TN 1297 verlangt für Messergebnisse eine nachvollziehbare Darstellung der Unsicherheitskomponenten und ihrer Ermittlung; eine Wahrscheinlichkeitsinterpretation benötigt eine angegebene Grundlage. Für diesen Beitrag bedeutet „belastbar“ deshalb: unter genannten Bedingungen ausreichend gestützt, mit dokumentierten Grenzen und offen für Revision. Die Bedingungen selbst bleiben prüfbar. [S1]

### 3. Mathematik, Modell und Wirklichkeit

<!-- claim: RF-06 -->
Mathematik untersucht Strukturen und Folgerungen aus Voraussetzungen. Eine widerspruchsfreie Beschreibung enthält noch keine Garantie, dass ein entsprechender Gegenstand in der Natur existiert. Für die Anwendung werden mathematische Größen mit Messverfahren, Einheiten, Anfangsbedingungen und beobachtbaren Folgen verbunden. Diese Zuordnung wird durch die jeweilige Fachwissenschaft geprüft. Die Gefahr liegt in der Verwechslung einer Herleitung innerhalb des Modells mit dem Nachweis seiner Anwendbarkeit.

Daraus entsteht eine produktive Arbeitsteilung: Mathematik macht Annahmen und Folgerungen präzise; Informatik macht Abläufe ausführbar und reproduzierbar; empirische Wissenschaften prüfen ihre Beziehung zu beobachtbaren Vorgängen. Eine allgemeinverständliche Übersetzung kann diesen Zusammenhang zugänglich machen, muss aber die Voraussetzungen und Grenzen erhalten. Der Autor bewertet diese gemeinsame Sprache als besonders wertvoll für eine internationale Verständigung über sein Vorhaben.

<!-- claim: RF-07 -->
Auch bei spieltheoretischen Modellen ist die Ebene entscheidend. Nashs Gleichgewichtsbegriff beschreibt eine Kombination von Strategien, bei der sich niemand durch einseitiges Abweichen verbessern kann, während die Strategien der anderen festgehalten werden. Daraus folgt kein allgemeiner zeitlicher Verlauf und keine unvermeidliche gesellschaftliche „Todesspirale“. Kommunikation, Lernen, andere Präferenzen und veränderte Institutionen betreffen die Modellierung des Spiels oder seiner Dynamik. Sie widerlegen den Gleichgewichtsbegriff nicht. [S2]

### 4. Die informatische Umsetzung

<!-- claim: RF-08 -->
Ein Arbeitszyklus wird als Folge aus Beobachtung, Kandidatenbildung, vereinbarter Entscheidung, Umsetzung und erneuter Beobachtung beschrieben. Die tatsächliche Entwicklung hängt auch von nicht kontrollierten Einflüssen ab. Deshalb gilt in diesem Projekt: Zeitliche Reihenfolge allein begründet keinen Kausalnachweis; eine angekommene Nachricht ist noch kein bestätigter Effekt. QIK-VRT/TEMDD wird hier als Gerüst für Zustandsbindung, Prüfungen und nachvollziehbare Entscheidungen verwendet. Die Bezeichnung TEMDD steht im Projekt für Tested Event Model Driven Development. [S3]

<!-- claim: RF-09 -->
Die verwendete native Vergleichsfunktion stammt aus `tools/qikvrt_perfect_optimum.py` auf dem Commit `a86054139b49c13c5cd344753b248b46b5daf66f`, Root-Tree `feff1cae2401a3df83febc3b9458de70d79b818e`. Ihre unveränderten Bytes werden im Demonstrator vor dem Laden geprüft. Die native Dokumentation beschreibt ein lokales Optimum relativ zu gebundenen Metriken und Invarianten. Der neue Adapter ergänzt Eingabeprüfung, individuelle Zeitrechnung, Kostenobergrenzen und den Vergleich mehrerer Kandidaten. Er prognostiziert keine menschliche Wirkung und wählt Ziele nicht eigenständig. [S3, E1]

<!-- claim: RF-10 -->
Die Anwendungspolicy ist ein Vorschlag für einen freiwilligen Kooperationspilot. Für jede Person werden Aufgabenzeit, Koordinationszeit und Einrichtungszeit innerhalb desselben festgelegten Fensters addiert. Fehler und vollständig abgeschlossene Aufgaben werden separat erfasst. Ein Kandidat ist für den weiteren Vergleich zulässig, wenn bei keiner Person Gesamtzeit oder Fehlerzahl steigen und mindestens ein Wert besser wird. Vorläufig sind höchstens zwei geänderte Regeln und 120 Personenminuten Einrichtung zulässig. Diese Grenzen drücken eine Gestaltungsentscheidung aus; sie wurden nicht als gesellschaftlich optimale Werte ermittelt.

Unter den zulässigen Kandidaten werden alle Personenwerte, die Einrichtungszeit und die Zahl geänderter Regeln gemeinsam verglichen. Eine Möglichkeit wird nur verdrängt, wenn eine andere in keiner Dimension schlechter und in mindestens einer besser ist. Mehrere Möglichkeiten können übrig bleiben. „Kleinste Änderung“ und „größte Wirkung“ werden damit als möglicher Zielkonflikt sichtbar. Über Prioritäten und faire Lastenverteilung entscheiden die Beteiligten.

### 5. Bisheriger Versuch und Ergebnisse

<!-- claim: RF-11 -->
Der bisherige Versuch ist eine Softwaredemonstration mit ausdrücklich künstlichen Daten für vier pseudonyme Personen. Die Ausgangszeit beträgt je 70 Minuten, zusammen 280 Minuten. Die künstlichen Kandidaten enthalten sämtliche für dieses Beispiel angesetzten Einrichtungs- und Koordinationszeiten. Die Werte sind weder erhobene Beobachtungen an Menschen noch Wirkungsprognosen. [E1]

| Kandidat | Einrichtung: Personenminuten | Geänderte Regeln | Nettozeitgewinn: Personenminuten | Rechenergebnis |
| --- | ---: | ---: | ---: | --- |
| A | 20 | 1 | 40 | Bleibt in der Pareto-Menge |
| B | 28 | 1 | 24 | Wird von A verdrängt |
| C | 60 | 2 | 60 | Bleibt in der Pareto-Menge |
| D | 40 | 1 | 55 | Zurückgehalten: P1 benötigt fünf Minuten mehr |

Das Ergebnis lautet somit A und C. A benötigt weniger Einrichtung, C erzielt im konstruierten Datensatz einen größeren Gewinn. Ein einziger Sieger folgt daraus nicht. D macht den Verteilungseffekt sichtbar: Ein günstiger Gruppensaldo kann mit einer Verschlechterung für eine Person einhergehen. [E1]

<!-- claim: RF-12 -->
Acht vorhandene Tests der nativen Komponente und 19 Tests des Adapters liefen erfolgreich. Die Adaptertests betreffen unter anderem fehlende Personen, unvollständige Aufgaben, ungültige Zahlen, leere Prüfbehauptungen, veraltete Ausgangsbindungen und vermischte Datenarten. Die leere Vorlage für tatsächliche Beobachtungen liefert `NEED_BASELINE`. Die Dateien und Ausführungsprotokolle sind dem Reproduktionspaket zugeordnet. Die Tests bestätigen die geprüften Fälle und Grenzen des Programms; sie sind kein Beweis allgemeiner Fehlerfreiheit. [E1]

<!-- claim: RF-13 -->
Es wurden keine menschlichen Teilnehmenden untersucht. Aussagen über bessere Kooperation, Verhaltensänderungen oder gesellschaftliche Folgen bleiben offen. Der Adapter behandelt derzeit Punktwerte und modelliert keine Messunsicherheit; kleine Differenzen dürfen daher nicht als gesicherte Wirkung interpretiert werden. Die Gesamtlaufzeit einer wissenschaftlichen Untersuchung oder ein Kostenvorteil gegenüber einem Labor wurden nicht vergleichend gemessen. [E1]

### 6. Nutzen von Simulation und Anschluss an Quantenexperimente

<!-- claim: RF-14 -->
Computermodelle erlauben bei geeigneten Aufgaben kontrollierte Varianten, wiederholbare Eingaben und Einsicht in interne Zustände. Ein Vorteil kann in der Vorbereitung, Fehlersuche und Untersuchung vieler Modellfälle liegen. Ob ein konkreter Versuch schneller, günstiger oder aussagekräftiger wird, hängt von Aufgabe, Modelltreue und Ressourcen ab. Eine Simulation prüft zunächst die Folgen des implementierten Modells. Unabhängige Beobachtungen sind erforderlich, um dessen Beziehung zur Natur zu prüfen.

<!-- claim: RF-15 -->
Der Bezug zur Quantenphysik benötigt drei getrennte Tätigkeiten: klassische Berechnung eines Quantenmodells, Verwendung eines physischen Quantensimulators oder Quantenprozessors und Messung an einem physikalischen Versuchsaufbau. Die Literatur zur Quantensimulation behandelt gerade die Ressourcen- und Kontrollgrenzen dieser Wege. Preskill diskutiert sowohl das Potenzial von Quantenrechnern als auch Rauschen, Fehlerkorrektur und Schwierigkeiten klassischer Simulation; sein Beitrag von 2018 ist eine Grundlagenreferenz, kein Bericht über den Gerätestand von 2026. Reale Bell-Tests wie der Versuch von Hensen und Mitautoren besitzen einen davon unterscheidbaren experimentellen Messaufbau. [S4, S5]

<!-- claim: RF-16 -->
Lohmann schlägt vor, QIK-VRT zur Vorbereitung und nachvollziehbaren Auswertung entsprechender Untersuchungen einzusetzen. Ein sinnvoller erster Fachbeitrag wäre ein vorab festgelegtes kleines Quantenmodell mit unabhängig berechneten Referenzwerten; später könnten ein vereinbarter Gerätezugang, Kalibrierungsdaten und reale Messergebnisse hinzukommen. Fragestellung, Observablen, Störmodell und Auswertung sollten die beteiligten Quantenfachleute festlegen. Der Autor bringt seine informatische Konzeption ein und lädt zu dieser Arbeitsteilung ein. Der hier dokumentierte Kooperationsdemonstrator führte keine Quantenberechnung und kein physisches Quantenexperiment aus. Eine allgemeine Überlegenheit der Software oder ein Ersatz für Quantenhardware ist damit nicht belegt.

### 7. Vom Demonstrator zur empirischen Untersuchung

<!-- claim: RF-17 -->
Als nächster Pilot ist eine bestehende freiwillige Gruppe mit einer wiederkehrenden Aufgabe vorgesehen. Zunächst werden Ausgangswerte erhoben. Ein erster Kandidat wäre, Zusagen mit Person, begrenztem Ergebnis und Termin festzuhalten sowie Hindernisse frühzeitig zu melden. Nach einer vereinbarten Erprobung werden Aufwand, Aufgabenabschluss, Fehler, Lastenverteilung und Rückmeldungen erneut erhoben. Wer aussteigt oder eine Aufgabe nicht abschließt, bleibt als solcher im Ergebnis sichtbar.

Der Versuchsplan unterscheidet diese praktische Erprobung von einem gesonderten Vergleich zwischen strukturiertem Gruppenaustausch und individueller Reflexion. Für einen belastbaren Kausalnachweis sind eine zur Fragestellung passende Kontrollbedingung, eine begründete Stichprobenplanung und vorab festgelegte Auswertung nötig. Ein adaptiver Pilot darf die Bedingungen eines parallel behaupteten festen Vergleichsversuchs nicht nachträglich verändern. Die Versuchsplanung knüpft an die experimentelle Untersuchung von Kommunikation und Selbstorganisation bei Ostrom, Walker und Gardner an, übernimmt daraus aber keine bestätigte Wirkung für den vorliegenden Entwurf. [S6, E1]

### 8. Vorführung, Verständigung und offener Beitrag

<!-- claim: RF-18 -->
Der Autor betont seine Begeisterung darüber, wie zugänglich die Vorführung eines solchen informatischen Ablaufs mit heutiger Computertechnik ist. Eine geeignete Demonstration zeigt dieselben Eingaben, die gebundenen Regeln, einen nachvollziehbaren Bericht und einen Fall, in dem das System wegen eines individuellen Nachteils anhält. Die erwartete Überzeugungskraft für Verantwortliche und Fachleute ist eine persönliche Einschätzung, die sich durch tatsächliche Rückmeldungen prüfen lässt.

<!-- claim: RF-19 -->
Der methodische Vorschlag verlangt Offenheit gegenüber Korrekturen auch beim eigenen Modell. Die hier beschriebenen Ideen stehen im Zusammenhang kollektiver wissenschaftlicher Arbeit. Für einen eigenständigen Neuheits- oder Prioritätsanspruch wären ein genauer Vergleich mit vorhandenen Methoden und eine externe fachliche Prüfung erforderlich. Beides ist mit diesem Demonstrator nicht abgeschlossen. Der konkrete Beitrag dieser Fassung ist eine nachvollziehbare Verbindung von Ausgangsthese, operationalisierter Vergleichsregel, ausführbarem Beispiel und ausgewiesenen Evidenzgrenzen. Die Einladung an Gunter Dueck und weitere Fachleute richtet sich auf deren Prüfung und verständliche Vermittlung.

### Daten, Code und Reproduktion

<!-- claim: RF-20 -->
Der Datensatz liegt unter `experiments/cooperation/data/synthetic_demo.json`, der Adapter unter `experiments/cooperation/run_cycle.py`. Im entpackten Ordner des beigefügten Reproduktionspakets genügt Python 3.10 oder neuer:

```sh
python3 -B run_cycle.py data/synthetic_demo.json
python3 -B run_cycle.py data/live_template.json
python3 -B -m unittest discover -s tests -v
```

Die beobachteten Softwareergebnisse sind über Dateiprüfsummen gebunden. Die aktuelle Repository-Fassung des Publikationspakets und ihr Root-Tree werden im begleitenden Repository-Beleg angegeben. Die Quellbindung der nativen Komponente bleibt davon getrennt. Ein Programmbericht ist weder eine Einwilligung von Menschen noch eine Publikationsfreigabe. Textlizenz: CC BY-NC-ND 4.0; die eigenständige Softwarelizenz ist im Reproduktionspaket enthalten.

### Quellen

[S1] Taylor, B. N.; Kuyatt, C. E. (1994): Guidelines for Evaluating and Expressing the Uncertainty of NIST Measurement Results. NIST Technical Note 1297, besonders Abschnitt 7. https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-7-reporting-uncertainty

[S2] Nash, J. (1951): Non-Cooperative Games. Annals of Mathematics 54(2), 286-295. https://www.cs.upc.edu/~ia/nash51.pdf

[S3] Lohmann, I.: QIK-VRT, `docs/PERFECT_OPTIMUM_V1.md` und `tools/qikvrt_perfect_optimum.py`, Commit a86054139b49c13c5cd344753b248b46b5daf66f. https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/docs/PERFECT_OPTIMUM_V1.md

[S4] Preskill, J. (2018): Quantum Computing in the NISQ era and beyond. Quantum 2, 79. DOI: 10.22331/q-2018-08-06-79. https://arxiv.org/html/1801.00862v3

[S5] Hensen, B. et al. (2015): Experimental loophole-free violation of a Bell inequality using entangled electron spins separated by 1.3 km. https://arxiv.org/abs/1508.05949

[S6] Ostrom, E.; Walker, J.; Gardner, R. (1992): Covenants with and without a Sword: Self-Governance Is Possible. American Political Science Review 86(2), 404-417. https://www.cambridge.org/core/journals/american-political-science-review/article/covenants-with-and-without-a-sword-selfgovernance-is-possible/2191864CCB589D4B3528090CB596C254

[E1] Begleitender QIK-VRT-Kooperationsdemonstrator, Version 0.2, einschließlich künstlichem Datensatz, Berichten, 27 gezielten Tests und Versuchsplan. Siehe `EVIDENCE_BINDINGS.json` und `REPRODUCTION_PACKAGE.zip` dieser Publikation.
