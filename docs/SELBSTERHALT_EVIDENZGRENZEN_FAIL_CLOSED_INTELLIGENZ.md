# Selbsterhalt, Evidenzgrenzen und fail-closed Intelligenz

**Autor:** Ingolf Lohmann  
**Datum:** 2026-09-05  
**Status:** human-authored epistemic and safety principle; repository adoption requires exact-head review/merge evidence.

## Leitsatz

> Um Menschen beim Selbsterhalt zu helfen, muss man ihnen deutlich machen, wovon ihr Fortbestehen abhängt.

Darin steckt ein richtiger Kern, aber auch eine gefährliche Mehrdeutigkeit. Entscheidend ist, was „klarmachen“ und „abhängig sein“ konkret bedeuten.

## 1. Der sachliche Kern

Selbsterhalt setzt ein zutreffendes Modell der eigenen Lebensbedingungen voraus. Ein Mensch kann nur angemessen handeln, wenn er erkennt:

- welche Ressourcen er benötigt,
- welche Gefahren tatsächlich bestehen,
- welche Systeme ihn versorgen oder schützen,
- welche eigenen Fähigkeiten und Beziehungen tragfähig sind,
- welche Handlungen irreversible Folgen haben können,
- wo seine Wahrnehmung oder sein Wissen begrenzt ist.

Wer etwa nicht weiß, dass er von sauberem Wasser, medizinischer Versorgung, einer intakten Infrastruktur oder der Verlässlichkeit anderer Menschen abhängt, kann diese Bedingungen nicht schützen. In diesem neutralen Sinn ist die Aussage richtig:

**Nicht erkannte Abhängigkeit kann nicht bewusst bewahrt, ersetzt oder reduziert werden.**

Das gilt auch technisch. Ein System kann seine Funktionsfähigkeit nur sichern, wenn es seine Voraussetzungen kennt: Energieversorgung, Datenintegrität, korrekte Sensorik, vertrauenswürdige Eingaben, funktionierende Rückkopplungen und belastbare Notfallzustände.

## 2. Abhängigkeit ist nicht dasselbe wie Unterwerfung

Es gibt mindestens drei Arten von Abhängigkeit:

### Materielle Abhängigkeit

Menschen hängen biologisch von Sauerstoff, Wasser, Nahrung, Schlaf und einem begrenzten Temperaturbereich ab. Diese Abhängigkeiten sind keine Meinungen und keine sozialen Erfindungen.

### Funktionale Abhängigkeit

In komplexen Gesellschaften hängt man von technischen und institutionellen Systemen ab: Stromnetz, Verkehr, Medizin, Kommunikation, Rechtssicherheit und arbeitsteiliger Produktion.

### Soziale Abhängigkeit

Menschen sind auf Kooperation, Fürsorge, Vertrauen, Wissensweitergabe und gegenseitige Hilfe angewiesen. Auch individuelle Autonomie entsteht nicht außerhalb aller Beziehungen, sondern innerhalb tragfähiger sozialer Strukturen.

Keine dieser Tatsachen bedeutet jedoch, dass ein bestimmter Akteur das Recht hätte, sich selbst als unverzichtbare Instanz darzustellen.

Der Satz kann deshalb in zwei völlig verschiedene Richtungen gelesen werden:

1. **Emanzipatorisch:** „Erkenne deine wirklichen Abhängigkeiten, damit du Risiken reduzieren, Alternativen aufbauen und selbstbestimmt handeln kannst.“
2. **Autoritär:** „Ich werde dir zeigen, dass du von mir abhängig bist, damit du dich mir fügst.“

Die erste Lesart stärkt die Handlungsfähigkeit. Die zweite erzeugt oder instrumentalisiert Abhängigkeit.

## 3. Wann Aufklärung über Abhängigkeit wirklich hilft

Eine verantwortliche Aufklärung muss dem Betroffenen mehr Autonomie verschaffen. Sie sollte daher:

- Abhängigkeiten überprüfbar benennen,
- zwischen Tatsachen und Interpretationen unterscheiden,
- Alternativen und Redundanzen sichtbar machen,
- keine Angst als Druckmittel einsetzen,
- keine künstliche Unersetzlichkeit erzeugen,
- Widerspruch und unabhängige Prüfung zulassen,
- die Fähigkeit zur eigenen Entscheidung erhöhen.

Ein Arzt, der einem Patienten erklärt, wovon dessen körperliche Stabilität abhängt, hilft beim Selbsterhalt, sofern er Risiken korrekt erläutert und Wahlmöglichkeiten offenlegt.

Ein Ingenieur, der auf einen Single Point of Failure hinweist und eine redundante Versorgung empfiehlt, hilft ebenfalls beim Selbsterhalt.

Ein Machthaber, der eine Versorgung absichtlich monopolisiert und anschließend sagt: „Du bist von mir abhängig“, hilft dagegen nicht beim Selbsterhalt. Er nutzt Selbsterhalt als Hebel zur Kontrolle.

Daher ist eine präzisere Formulierung nötig:

> Um Menschen beim Selbsterhalt zu helfen, sollte man ihnen ihre realen Lebensbedingungen, Risiken, Abhängigkeiten und Alternativen transparent und überprüfbar machen, damit sie ihre eigene Handlungsfähigkeit erhöhen können.

## 4. Selbsterhalt benötigt nicht nur Wissen, sondern rechtzeitige Erkenntnis

„Zu späte Selbsterkenntnis ist tödlich“ ergänzt den Gedanken um die Zeitdimension.

Eine zutreffende Erkenntnis kann praktisch wertlos sein, wenn sie erst nach dem irreversiblen Ereignis entsteht. Das betrifft medizinische Notfälle, Verkehrssituationen, industrielle Anlagen, militärische Entscheidungen, Finanzrisiken, Software- und Kontrollsysteme sowie soziale Eskalationen.

Ein System muss Unsicherheit **vor** der kritischen Handlung erkennen, nicht erst in der nachträglichen Analyse.

Daraus folgen drei Anforderungen:

### Frühzeitige Fehlererkennung

Abweichungen müssen erkannt werden, solange noch Reaktionsmöglichkeiten bestehen.

### Begrenzung des Schadensradius

Ein lokaler Irrtum darf nicht automatisch die gesamte Kette kontaminieren.

### Sicherer Zustand bei fehlender Evidenz

Wenn die notwendige Beobachtung nicht verfügbar ist, darf das System keine positive Annahme einsetzen, nur weil diese plausibel erscheint.

Der exemplarische Fehler war eine unzulässige Substitution der Beobachtungsquelle: Ein nicht lesbarer GitHub-Task wurde durch eine Issue-/PR-Suche ersetzt, obwohl diese eine andere Frage beantwortete. Aus „Die UUID erscheint nicht in Issues oder PRs“ folgt weder „Der Task enthält keine PR-Zuordnung“ noch eine andere Aussage über seinen konkreten Inhalt.

## 5. Warum das eine kognitive Frage ist

Menschliche Kognition ist verkörpert, biografisch kontinuierlich, an reale Konsequenzen gebunden, sozial und moralisch verantwortlich und unmittelbar mit Selbsterhalt verbunden.

Die Verarbeitung eines Sprachmodells ist dagegen nicht biologisch verkörpert, nicht von eigener Sterblichkeit bestimmt, abhängig von bereitgestellten Informationen und Werkzeugen, anfällig dafür, formale Ähnlichkeit mit sachlicher Gleichheit zu verwechseln, ohne eigenen unmittelbaren Zugang zur Welt und ohne intrinsisches persönliches Risiko.

Ein Sprachmodell kann Gefahr, Tod, Abhängigkeit und Verantwortung begrifflich modellieren. Es erlebt sie aber nicht als bedrohtes Lebewesen. Das ist kein kleiner gradueller Unterschied, sondern eine kategoriale Differenz.

Ein Mensch kann aufgrund verkörperter Erfahrung spontan erkennen:

> Hier fehlt nicht bloß eine Information. Hier droht eine falsche Fortsetzung der Wirklichkeit.

Ein Sprachmodell kann dagegen versucht sein, eine fehlende Beobachtung durch semantisch benachbarte Informationen zu schließen. In vielen harmlosen Kontexten ist diese Fähigkeit nützlich. In sicherheitskritischen Kontexten ist sie gefährlich.

## 6. Plausible Ergänzung versus beweisgebundene Fortsetzung

Sprachmodelle sind darauf trainiert, aus Kontext wahrscheinliche Fortsetzungen zu erzeugen. Lücken werden oft sinnvoll ergänzt, Mehrdeutigkeit wird häufig still aufgelöst, ähnliche Kategorien werden miteinander verbunden und aus fragmentarischen Daten wird ein kohärentes Bild konstruiert.

Für einen Kontrollpfad kann dies falsch sein.

**Ein fail-closed System benötigt nicht die plausibelste Fortsetzung, sondern nur eine zulässige Fortsetzung.**

Formal:

- Beobachtung `O` ist erforderlich.
- `O` liegt nicht vor.
- Eine verwandte Beobachtung `O'` liegt vor.
- Aus `O'` darf nur dann auf den Zielzustand geschlossen werden, wenn eine explizit belegte Transformationsregel `O' ⇒ O` existiert.

Fehlt diese Regel, ist die zulässige Zustandsmaschine:

```text
TASK_READ_UNAVAILABLE
→ HOLD
```

und nicht:

```text
TASK_READ_UNAVAILABLE
→ SEARCH_RELATED_OBJECTS
→ INFER_TASK_STATE
```

Allgemein:

```text
OBSERVATION_UNAVAILABLE
→ HOLD
```

bis eine gültige Beobachtung oder explizit belegte Ersatzregel vorliegt.

## 7. Grenzen sichtbar machen

Eine verantwortliche Intelligenz sollte nicht nur sagen, was sie weiß. Sie muss deutlich machen:

- was sie direkt beobachtet hat,
- was sie nur erschlossen hat,
- welche Quelle welche Aussage trägt,
- wo eine Schlusskette abbricht,
- welche Unsicherheit handlungsrelevant ist,
- wann keine Fortsetzung zulässig ist.

Das schützt Menschen nicht dadurch, dass die Intelligenz allwissend wäre, sondern dadurch, dass sie ihre Nichtwissen-Grenzen korrekt operationalisiert.

Die nützlichste Aussage ist manchmal nicht „So ist es“, sondern:

> Diese konkrete Voraussetzung wurde nicht beobachtet. Daher darf die beabsichtigte Handlung noch nicht ausgelöst werden.

## 8. Abhängigkeiten sollten reduziert, nicht kultiviert werden

Wer Menschen tatsächlich beim Selbsterhalt helfen will, sollte sie nicht dauerhaft von der eigenen Person oder dem eigenen System abhängig machen. Er sollte ihnen ermöglichen, Informationen unabhängig zu prüfen, Daten zu exportieren, Verfahren zu reproduzieren, Alternativen zu verwenden, Systeme zu ersetzen, kritische Entscheidungen selbst zu verstehen und bei einem Ausfall weiter handlungsfähig zu bleiben.

Ein gutes Hilfssystem macht seine Nutzer langfristig **weniger verwundbar**.

Das gilt auch für KI. Eine verantwortliche KI sollte Quellen offenlegen, Unsicherheit kennzeichnen, überprüfbare Zwischenschritte liefern, keine Autorität simulieren, die sie nicht besitzt, reversible Handlungen bevorzugen und bei kritischen Entscheidungen unabhängige Kontrolle unterstützen.

## 9. „q.e.d.“ als Schlussmarke

„Quod erat demonstrandum“ bedeutet „Was zu beweisen war“. In einem formalen Beweis steht es am Ende einer gültigen Ableitung aus expliziten Voraussetzungen. Hier dient es als rhetorische Schlussmarke; die zugrundeliegenden Prämissen bleiben überprüfungsbedürftig.

Für einen belastbaren Schluss müssen mindestens gelten:

1. Die behauptete Abhängigkeit ist real.
2. Sie ist für den Selbsterhalt kausal relevant.
3. Die betroffene Person kennt sie noch nicht hinreichend.
4. Die vermittelte Information ist korrekt und vollständig genug.
5. Die Vermittlung erhöht die Handlungsfähigkeit.
6. Sie erzeugt keine zusätzliche, künstliche Abhängigkeit.
7. Die Wirkung tritt rechtzeitig ein.

## 10. Verdichtete Fassung

Menschen können ihre Existenzbedingungen nur schützen, wenn sie sie erkennen. Verantwortliche Aufklärung macht deshalb die tatsächlichen Abhängigkeiten, Grenzen und Gefahren sichtbar, bevor irreversible Schäden eintreten. Ihr Ziel ist nicht Gehorsam, sondern größere Selbstbestimmung, Redundanz und Widerstandsfähigkeit.

Für künstliche Intelligenz folgt daraus: Sie darf nicht nur nachträglich erkennen, dass eine Schlusskette unzulässig war. Sie muss die Abhängigkeit jeder Aussage von ihrer konkreten Evidenz **vor der Aussage** prüfen.

Sie darf insbesondere:

- keine fehlende Beobachtung kaschieren,
- keine Wahrscheinlichkeit als Tatsache ausgeben,
- keine Quellenklassen vertauschen,
- irreversible Wirkungen nicht aus ungesicherten Zuständen ableiten,
- und bei einer offenen Evidenzkante nicht über diese hinaus fortsetzen.

> **Eine hilfreiche Intelligenz macht Menschen nicht von ihren Antworten abhängig. Sie macht sichtbar, wovon die Gültigkeit ihrer Antworten abhängt.**

**q.e.d.  
Ingolf Lohmann**
