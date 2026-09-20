# QIK-VRT: erster Rückkopplungszyklus für einen Kooperationsversuch

Stand: 20. September 2026. Lokaler ausführbarer Prototyp, Protokoll v0.2.

**Vorbereitet und mit künstlichen Daten prüfbar. Der Versuch mit Menschen hat noch nicht begonnen.** Ziele und Grenzwerte sind Vorschläge, über die die Beteiligten entscheiden müssen. Der Algorithmus vergleicht Messwerte; er ersetzt diese Entscheidung nicht.

## Start

Python 3.10 oder neuer genügt; keine Zusatzpakete und keine Netzwerkverbindung erforderlich. Im entpackten Verzeichnis:

```sh
python3 -B run_cycle.py data/synthetic_demo.json --output reports/demo.json
python3 -B run_cycle.py data/live_template.json --output reports/live.json
python3 -B -m unittest discover -s tests -v
```

Der erste Aufruf zeigt einen künstlichen Vergleich, der zweite meldet `NEED_BASELINE`. Exitcode 0 bedeutet, dass ein Bericht erstellt wurde; er bedeutet keine menschliche Verbesserung. Ungültige Gesamteingaben liefern `HOLD` und Exitcode 2. Ungültige einzelne Kandidaten bleiben im Bericht als `HOLD` sichtbar.

## Die erste reale Änderung

Vorschlag: Für eine bestehende freiwillige Gruppe wird bei einer wiederkehrenden gemeinsamen Aufgabe **jede Zusage mit Person, kleinem Ergebnis und Termin festgehalten; ein Hindernis wird vor Ablauf angesprochen**. Das ist eine erste überprüfbare Hypothese über Verlässlichkeit, keine bereits berechnete beste Lösung. Die erste Änderung muss mangels Daten zunächst vereinbart werden.

1. Gruppe, Aufgabe, vergleichbare Aufgabenvarianten, Messfenster und Arbeitsbudget vereinbaren. Personen erhalten pseudonyme Kennungen. Eine Aufgabenwiederholung pro Person ist der Einstieg; die Zahl bleibt für Vergleiche gleich.
2. Ausgangsfenster messen. Aufgaben-, Koordinations- und Einrichtungszeit, Fehler sowie die Zahl abgeschlossener Aufgaben pro Person vollständig erfassen. Fehlerarten und die Abgrenzung der drei Zeitkategorien vorher definieren. Keine Minute doppelt zählen. Nicht erledigte Aufgaben sind kein schnellerer Erfolg und werden vom Vergleich zurückgehalten.
3. Genau die vereinbarte Änderung erproben und im nächsten gleich definierten Fenster erneut messen. Lern- und Reihenfolgeeffekte dokumentieren.
4. Messwerte vergleichen. Bei verschlechterter Belastung oder Fehlerzahl einer Person erfolgt im konservativen Pilot keine automatische Empfehlung zur Übernahme. Die Gruppe kann eine andere Lösung oder eine transparent neu vereinbarte Regel prüfen.
5. Die nächste Entscheidung mit Gründen protokollieren. Änderungen an Aufgabe, Gruppe, Zielen oder Regelwerk erfordern einen neuen gebundenen Vergleich. Alte Bewertungen werden nicht automatisch übertragen.

Für die Datenerfassung stehen `data/live_template.json` und `data/observation_form.json` bereit. Das Formular enthält absichtlich leere Werte. Ein unverändert ausgefüllter Dateiname oder ein auf `true` gesetztes Feld ist kein Beweis für ein Ereignis.

## Vergleichsregel

Pro Person wird gerechnet:

`Gesamtzeit = Aufgabenzeit + Koordinationszeit + Einrichtungszeit`.

Ein Kandidat erfüllt die vorläufige Verbesserungsregel genau dann, wenn gegenüber der gebundenen Ausgangsmessung bei **keiner Person** Gesamtzeit oder Fehlerzahl steigen und mindestens ein Wert besser wird. Alle tatsächlichen Einrichtungskosten im vereinbarten Fenster sind enthalten. Künftige Einsparungen werden nicht vorweggenommen.

Zusätzlich gelten im Entwurf höchstens zwei geänderte Regeln und 120 Personenminuten Einrichtung pro Kandidat. Das sind einstellbare Vorschläge, keine aus Daten ermittelten Optima. Die Kosten werden nicht mit frei erfundenen Gewichten gegen menschliche Nachteile verrechnet.

Unter den zulässigen Kandidaten werden sämtliche Personenwerte, Einrichtungszeit und Zahl geänderter Regeln gemeinsam verglichen. Ein Kandidat wird nur dann verdrängt, wenn ein anderer in keiner Dimension schlechter und in mindestens einer besser ist. Die verbleibende **Pareto-Menge** zeigt Zielkonflikte. Eine einzige beste Handlung wird nicht erzwungen.

Im künstlichen Beispiel mit vier Personen:

| Kandidat | Einrichtung in Personenminuten | Geänderte Regeln | Gesamte Nettozeitersparnis in Minuten | Ergebnis |
| --- | ---: | ---: | ---: | --- |
| A | 20 | 1 | 40 | In der Pareto-Menge |
| B | 28 | 1 | 24 | Von A verdrängt |
| C | 60 | 2 | 60 | In der Pareto-Menge |
| D | 40 | 1 | 55 | Zurückgehalten: P1 braucht fünf Minuten länger |

**Alle Zahlen sind künstlich.** A braucht weniger Einrichtung als C; C spart im vorgegebenen Beispiel mehr Zeit. Ohne zusätzlich vereinbarte Priorität folgt daraus keine eindeutige Wahl. Die Zahl vier dient nur dem Softwarebeispiel und ändert nicht den Vorschlag von acht Freiwilligen im Versuchsplan.

## Daten eintragen und binden

`data/live_template.json` enthält die aktuelle Quellen- und Regelwerksbindung. Eine eigene Kopie anlegen. In `context` Versuchskennung, Aufgabenkennung, Wiederholungszahl, Messfenster und vollständige Teilnehmerliste eintragen. Für Ausgangswert und jeden Kandidaten das Beobachtungsformular ausfüllen; dessen `context` muss identisch sein. Datumsangaben benötigen eine Zeitzone. Zeiten müssen endlich und nichtnegativ, Fehler ganzzahlig und nichtnegativ sein. `completed_repetitions` muss pro Person genau der vereinbarten Zahl abgeschlossener Aufgaben entsprechen.

Die fünf `declared_checks` sind manuell belegte Aussagen zu freiwilliger Teilnahme, gleichem Ergebniszugang, vergleichbaren Aufgaben, vollständiger Erfassung und vollständiger Kostenrechnung. Alle müssen ausdrücklich `true` sein. Belegverweise unter `evidence_refs` müssen vorhanden sein; ihre Wahrheit und ihr Inhalt werden durch dieses Programm **nicht** automatisch geprüft. Rohprotokolle bleiben bei den Beteiligten; Berichte enthalten keine Klarnamen.

Eine vollständig gemessene Ausgangsbeobachtung wird unter `baseline`, spätere Beobachtungen unter `candidates` eingetragen. Jeder Kandidat benötigt zusätzlich `rule_changes` und den kanonischen SHA-256 der Ausgangsbeobachtung. Nachdem `live.json` ausgefüllt wurde, lässt er sich so ausgeben:

```sh
python3 -B -c 'from pathlib import Path; from run_cycle import read_json, observation_hash; print(observation_hash(read_json(Path("live.json"))["baseline"]))'
```

`policy_sha256` bindet die exakten Bytes von `experiment_policy.json`. Eine vereinbarte Änderung dieser Datei verlangt eine neue Protokollversion, neue Bindung und eine sichtbar getrennte Auswertung; bestehende Ergebnisse bleiben an ihre ursprüngliche Fassung gebunden. Synthetische und beobachtete Daten sind getrennte Datensätze und dürfen nicht vermischt werden. Eine Kennzeichnung allein beweist keine Echtheit.

## Was aus QIK-VRT stammt und was hier ergänzt wurde

Quelle: [Goldkelch/qik-vrt, Commit a8605413](https://github.com/Goldkelch/qik-vrt/tree/a86054139b49c13c5cd344753b248b46b5daf66f).

- Commit: `a86054139b49c13c5cd344753b248b46b5daf66f`.
- Root-Tree: `feff1cae2401a3df83febc3b9458de70d79b818e`.
- `upstream/qikvrt_perfect_optimum.py` ist eine unveränderte Kopie von `tools/qikvrt_perfect_optimum.py`. Ihr SHA-256 steht in `source_binding.json` und wird vor dem Laden geprüft.
- Der native Vergleich `evaluate` wird mit einer **neuen anwendungsspezifischen Messgrößenliste** aufgerufen. Die ursprüngliche Repository-Policy wird damit nicht geändert. Der native CLI-Self-Check wird auf die ursprüngliche Policy im Quellrepository angewendet, nicht auf diesen Anwendungsentwurf.
- Neu sind `run_cycle.py`, Eingabeprüfung, individuelle Zeitrechnung, Budgetprüfung, Paarvergleich der Kandidaten, Formulare und Tests. Das ist ein lokaler Adapter, kein im Hauptrepository integriertes Produktmerkmal.
- Die zusätzliche Prüfung verlangt vollständige Invarianten mit exaktem booleschem Wert und endliche Zahlen. Der native Vergleich allein prüft diese Eingabequalität nicht vollständig.

Die unveränderte Kopie ist für einen offline nachvollziehbaren Komponentenlauf enthalten. Quellnotice und Softwarelizenz liegen unter `upstream/`. Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder. Das Quellrepository wurde nicht inhaltlich verändert.

## Aussagegrenzen und Prüfstand

Rückkopplung wird hier als wiederholtes Beobachten, Entscheiden, Handeln und erneutes Beobachten operationalisiert. Der Versuch setzt keine kosmologische Behauptung voraus. Nash-Gleichgewichte beschreiben wechselseitige beste Antworten unter Modellannahmen; daraus folgt keine allgemeine gesellschaftliche Todesspirale. Bewusstsein und Lernen können modellierte Präferenzen, Erwartungen oder Strategien verändern, ohne die Mathematik zu widerlegen.

Der native QIK-VRT-Ansatz beschreibt ausdrücklich ein lokales Optimum relativ zu Metriken und Invarianten. Unser Adapter findet eine Pareto-Menge **innerhalb der gelieferten, vergleichbaren Kandidaten**, nicht unter allen denkbaren Eingriffen. Er prognostiziert keine Wirkung und modelliert noch keine Messunsicherheit. Kleine Messabweichungen sind daher kein Wirksamkeitsbeweis. Unzuverlässige Daten verlangen Wiederholung und Prüfung.

Vorher-nachher-Vergleiche liefern noch keinen kausalen Effekt der Änderung. Der getrennte kontrollierte Versuch in Abschnitt 7 des Versuchsplans bleibt ein eigener, vorab festgelegter Untersuchungsablauf. Adaptive Eingriffe aus diesem Pilot dürfen dessen Bedingungen nicht nachträglich verändern.

Prüfprotokolle liegen unter `verification/`; Softwareberichte unter `reports/`. Die Repository-Bootprüfung hat den Zustand `CONTINUE` wegen nicht vollständig vorhandener optionaler Laufzeitwerkzeuge, die kollektive Bootstrap-Prüfung wegen sechs noch ausstehender Audioverifikationen. Diese Aufgaben gehören nicht zum hier geprüften Python-Komponentenlauf. Kein vollständiger Repository-Release, keine externe Wirkung und keine menschliche Wirksamkeit werden daraus abgeleitet.
