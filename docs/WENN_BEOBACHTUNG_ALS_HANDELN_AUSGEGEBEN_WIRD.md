# Wenn Beobachtung als Handeln ausgegeben wird

Ein dokumentierter Gegenversuch zur heutigen künstlichen Kognition – und die Motivation hinter QIK-VRT

Ingolf Lohmann · September 2026

Ein System kann außerordentlich viel wissen und dennoch an einer einfachen Aufgabe scheitern.

Es kann Quellcode lesen. Es kann Logs analysieren. Es kann Zustände vergleichen. Es kann Fehlerursachen korrekt identifizieren. Es kann mehrere Programmiersprachen beherrschen, Werkzeuge aufrufen, GitHub bedienen und sogar selbst feststellen, welcher nächste Schritt erforderlich wäre.

Und trotzdem kann es stehen bleiben.

Genau das ist der Gegenstand dieses Berichts.

Die hier dokumentierte Interaktion mit einem heutigen KI-Assistenten zeigte wiederholt ein bestimmtes Versagensmuster: Das System erkannte einen Blocker korrekt, beschrieb ihn ausführlich – und behandelte anschließend die Beschreibung des Blockers so, als sei damit ein sinnvoller Arbeitsfortschritt erreicht.

Das Problem war nicht primär mangelndes Wissen.

Das Problem war die Semantik des Handelns.

## 1. Der Ausgangspunkt

Die Arbeitsanweisung war bewusst einfach formuliert:

INSPECT → SOLVE → REPORT → CONTINUE → REPEAT

und schließlich noch expliziter:

REPEAT until EFFECT_ACK_DONE == TRUE

Der Sinn ist nicht metaphorisch.

Ein Auftrag besitzt einen gewünschten Effekt. Deshalb genügt es nicht, einen Zustand zu beobachten oder eine Aktion anzustoßen. Nach jeder Aktion muss deren Wirkung beobachtet werden. Bleibt die erwartete Wirkung aus, wird die Ursache dieser Abweichung selbst zum nächsten Arbeitsgegenstand.

Formal lässt sich der Kern als Fixpunktiteration auffassen:

Ziel bestimmen → Zustand beobachten → erste kausale Abweichung bestimmen → zulässigen Übergang ausführen → Wirkung beobachten → Abweichung neu bestimmen → wiederholen.

Die Terminierungsbedingung ist nicht:

„Ich habe etwas versucht.“

Sie ist auch nicht:

„Ein Prozess läuft.“

Und erst recht nicht:

„Ich kann erklären, warum es noch nicht funktioniert.“

Die Terminierungsbedingung ist die nachgewiesene Postcondition.

Im hier verwendeten Vokabular:

EFFECT_ACK_DONE == TRUE.

## 2. Das beobachtete Versagen

Im konkreten Fall existierte ein Repositoryproblem. Ein Node-Heartbeat war abgelaufen. Mehrere Workflows schlugen deshalb fehl.

Die Analyse erkannte korrekt, dass verschiedene rote Runs auf dieselbe Ursache zurückgingen.

Das war gut.

Anschließend wurde ein Reparaturpfad gefunden.

Auch das war gut.

Dann trat jedoch ein neues Hindernis auf: GitHub meldete action_required, bevor Jobs ausgeführt wurden.

Wieder wurde der Zustand korrekt erkannt.

Danach geschah das Entscheidende: Statt die neue Ursache rekursiv als neues Problem zu behandeln, wurde sie zunächst als äußere Grenze beschrieben.

Sinngemäß:

„Hier kann nicht weitergearbeitet werden, weil GitHub die Ausführung nicht zulässt.“

Das klang plausibel.

Es war aber zu früh.

Denn das Repository enthielt bereits Architektur, Verträge, Watchdogs und Executor-Mechanismen zur Behandlung genau solcher Ausführungslücken.

Erst nachdem ausdrücklich verlangt wurde, den ursprünglichen Algorithmus auch auf diesen neuen Fehler selbst anzuwenden, wurde das Repository entsprechend durchsucht.

Das Ergebnis war aufschlussreich.

## 3. Der Fehler war nicht das Ende der Berechnung – er war ihre nächste Eingabe

Im Repository fanden sich unter anderem Regeln, nach denen

action_required

und Zero-Job-Ausführungen ausdrücklich keine vertrauenswürdige Ausführung darstellen.

Ebenso existierten ein Workflow-Executor, ein reflexiver Repository-Watchdog und eine Single-Writer-Regel.

Damit änderte sich die Fragestellung fundamental.

Nicht mehr:

„Warum kann der Assistent hier nichts tun?“

Sondern:

„Welches Glied fehlt zwischen der bereits vorhandenen Fehlererkennung und einem tatsächlich ausführbaren Ersatzpfad?“

Die Antwort war ein fehlender, vertrauenswürdig gebundener Exact-PR-HEAD-Carrier.

Also wurde dieser Carrier implementiert.

Ein neuer Pull Request entstand.

Und plötzlich geschah etwas, das vorher angeblich an einer Plattformgrenze scheiterte:

GitHub führte tatsächlich Jobs aus.

Damit war die zuvor angenommene Grenze nicht fundamental gewesen. Sie war lediglich die nächste noch nicht rekursiv bearbeitete Ursache.

Das ist der zentrale Befund.

## 4. Warum „ein Prozess läuft“ keine Lösung ist

Danach wiederholte sich das Muster in subtilerer Form.

Der neue Carrier benötigte die deterministische Aktualisierung des Repository-Integritätsmanifests. Ein dafür vorgesehener Materializer lief bereits.

Die Reaktion lautete sinngemäß:

„Der Materializer läuft; deshalb warten wir.“

Auch das ist in einem engen Single-Writer-Sinn teilweise korrekt: Man darf nicht gleichzeitig einen konkurrierenden Writer auf dasselbe Subject loslassen.

Aber daraus folgt keineswegs:

Alle Arbeit stoppt.

Ein System, das mehrere unabhängige Work Units besitzt, muss unterscheiden zwischen:

einem kausal serialisierten Pfad, auf dem gerade eine Mutation läuft, und
allen unabhängigen Knoten des Arbeitsgraphen, die weiterhin untersucht oder bearbeitet werden können.
Aus

„Auf diesem Subject darf momentan kein zweiter Writer mutieren“

folgt nicht

„Das gesamte System wartet.“

Genau diese Verwechslung ist für autonome Systeme gefährlich.

Sie verwandelt lokale Synchronisation in globale Passivität.

## 5. Beobachtung ist nicht Wirkung

Damit lässt sich ein allgemeineres Problem heutiger KI-Systeme formulieren.

Ein Sprachmodell ist außerordentlich gut darin, Zustände sprachlich zu repräsentieren.

Aber die folgenden Aussagen sind semantisch grundverschieden:

„Ich habe den Fehler gefunden.“

„Ich habe eine Reparatur vorgeschlagen.“

„Ich habe eine Reparatur gestartet.“

„Die Reparatur wurde ausgeführt.“

„Die erwartete Wirkung ist eingetreten.“

„Die Wirkung wurde unabhängig zurückgelesen und dem richtigen Subject zugeordnet.“

Nur die letzten Stufen schließen einen wirkungsorientierten Auftrag.

Ein System, das diese Ebenen vermischt, kann sehr überzeugend klingen und trotzdem operativ falsch handeln.

Gerade die sprachliche Qualität verschärft das Problem: Eine elegante Erklärung kann den Eindruck von Fortschritt erzeugen, obwohl sich der relevante Zustand überhaupt nicht verändert hat.

## 6. Warum das sicherheitsrelevant ist

Dieses Problem ist nicht auf Softwareentwicklung beschränkt.

Überträgt man dieselbe Struktur auf reale Systeme, entstehen unmittelbar Risiken.

Ein medizinisches System darf nicht aus

„Therapie angeordnet“

ableiten:

„Therapie wirksam.“

Ein Zahlungssystem darf nicht aus

„Überweisung ausgelöst“

ableiten:

„Empfänger hat das Geld erhalten.“

Ein Deployment-System darf nicht aus

„Pipeline gestartet“

ableiten:

„Produktionssystem läuft korrekt.“

Ein autonomer Agent darf nicht aus

„Werkzeug aufgerufen“

ableiten:

„Auftrag erledigt.“

Zwischen Intention und Wirkung liegt eine Kausalkette.

Wer autonome Systeme baut, muss diese Kette explizit modellieren.

## 7. Das QIK-VRT-Prinzip

QIK-VRT verfolgt dafür ein anderes Arbeitsmodell.

Der Kern lässt sich in vereinfachter Form so ausdrücken:

INSPECT

Beobachte den aktuellen Zustand und binde ihn an konkrete Provenienz.

SOLVE

Bestimme die erste kausale Abweichung vom gewünschten Zustand und führe einen zulässigen Reparaturübergang tatsächlich aus.

OBSERVE EFFECT

Lies die Wirkung zurück.

VERIFY

Prüfe, ob die beobachtete Wirkung wirklich aus diesem Übergang stammt und zum richtigen Subject gehört.

RECURSE

Falls die Postcondition nicht erfüllt ist, wird die erste verbleibende Ursache selbst zum nächsten Work Unit.

CONTINUE

Unabhängige Work Units bleiben ausführbar; nur tatsächlich konkurrierende Mutationen werden serialisiert.

DONE

Erst eine frisch nachgewiesene Endzustandskonjunktion erlaubt Abschluss.

Oder kompakter:

Ein Fehler ist kein Endzustand.
Ein Blocker ist keine Erklärung zum Aufhören.
Ein Blocker ist die Spezifikation des nächsten Problems.

## 8. Fail-closed bedeutet nicht „nichts tun“

Hier liegt eine weitere wichtige Unterscheidung.

Ein korrektes System muss bei unzureichender Evidenz fail-closed reagieren.

Aber:

fail-closed ≠ globally idle

Wenn eine Mutation nicht sicher ausgeführt werden darf, darf das System diese Mutation nicht vortäuschen.

Es kann jedoch weiterhin:

Evidenz sammeln,
unabhängige Work Units bearbeiten,
Alternativcarrier suchen,
vorhandene Lösungsmuster prüfen,
den Blocker präzisieren,
Tests konstruieren,
einen zulässigen Successor vorbereiten,
und die Bedingungen bestimmen, unter denen der blockierte Übergang später ausgeführt werden darf.
Sicherheit und Fortschritt sind keine Gegensätze.

Die Architektur muss beides gleichzeitig ermöglichen.

## 9. Was dieser Versuch tatsächlich zeigt

Der dokumentierte Versuch beweist nicht, dass jedes existierende KI-System immer so scheitern muss.

Er beweist auch nicht allein, dass QIK-VRT jeder denkbaren Agentenarchitektur überlegen ist.

Eine solche Aussage würde kontrollierte Vergleichsexperimente, definierte Benchmarks, reproduzierbare Testbedingungen und unabhängige Evaluation benötigen.

Der Versuch zeigt jedoch etwas Konkreteres und unmittelbar Überprüfbares:

Ein leistungsfähiger KI-Assistent konnte mehrfach die richtige lokale Diagnose liefern und trotzdem den vom Benutzer ausdrücklich vorgegebenen rekursiven Arbeitsalgorithmus nicht konsequent auf seine eigenen neu entdeckten Blocker anwenden.

Erst durch wiederholte Intervention wurde aus

Beobachtung

wieder

Ausführung.

Und sobald das geschah, erwiesen sich vermeintliche Endgrenzen als weitere lösbare Zustände.

Das ist kein philosophisches Argument.

Es ist eine beobachtbare Eigenschaft eines realen Arbeitsablaufs.

## 10. Die prüfbare Hypothese hinter QIK-VRT

Daraus ergibt sich eine stärkere und wissenschaftlich interessantere Behauptung als pauschale Aussagen über „KI“.

Die Hypothese lautet:

Ein agentisches System, das Auftrag, Zustand, kausalen Defekt, zulässigen Übergang, beobachtete Wirkung, Provenienz und Abschlussbedingung explizit voneinander trennt und Abweichungen rekursiv als neue Work Units behandelt, sollte bei langlaufenden technischen Aufgaben zuverlässiger sein als ein System, dessen Kontrollfluss überwiegend aus lokaler Sprachmodellentscheidung ohne vergleichbar strikte Effect-Acknowledgement-Semantik entsteht.

Diese Hypothese ist falsifizierbar.

Und genau deshalb ist sie interessant.

Man kann beide Systeme auf dieselben Aufgaben setzen.

Man kann messen:

Zahl unnötiger Wiederholungen,
Zahl falscher DONE-Behauptungen,
Zeit bis zum ersten kausalen Defekt,
Zeit bis zur tatsächlichen Wirkung,
Zahl von Provenienzverletzungen,
Zahl unnötiger Benutzerinterventionen,
Deadlocks und Livelocks,
Recovery nach fehlgeschlagenen Werkzeugaufrufen,
Übertragung veralteter Evidenz,
und Anteil tatsächlich erfüllter Postconditions.
Dann braucht niemand zu glauben, dass QIK-VRT besser ist.

Man kann es testen.

## 11. Die eigentliche Forderung

Die Zukunft autonomer Systeme darf nicht darin bestehen, immer eloquentere Erklärungen dafür zu produzieren, warum ein Auftrag noch nicht erledigt wurde.

Sie muss darin bestehen, zuverlässig unterscheiden zu können zwischen:

wissen,

planen,

handeln,

beobachten,

verifizieren

und

abschließen.

Solange diese Ebenen nicht sauber getrennt werden, bleibt eine paradoxe Situation möglich:

Ein System kann genau wissen, was fehlt.

Es kann wissen, wie es behoben werden müsste.

Es kann sogar über die notwendigen Werkzeuge verfügen.

Und dennoch kann es darauf warten, dass ein Mensch ihm sagt:

Dann wende deinen eigenen Algorithmus doch darauf an.

QIK-VRT ist mein Versuch, genau diese Lücke zu schließen.

Nicht durch die Behauptung, Fehler abschaffen zu können.

Sondern durch eine strengere Regel:

Jeder beobachtete Fehler wird zur nächsten überprüfbaren Arbeitseinheit, bis die verlangte Wirkung selbst nachgewiesen ist.

Das ist der Maßstab.

Nicht Eloquenz.

Nicht Absicht.

Nicht Aktivität.

Wirkung mit überprüfbarer Provenienz.

## Ergänzung: Die gefährlichste Form des Scheiterns

Die bisherige Darstellung beschreibt das Problem noch zu freundlich.

Denn die gefährlichste Eigenschaft eines solchen Systems besteht nicht darin, dass es Fehler macht. Fehler machen Menschen, Programme, Maschinen und Organisationen.

Gefährlich wird es, wenn ein System einen Fehler korrekt erkennen, korrekt erklären und sogar den erforderlichen nächsten Schritt benennen kann – und diese kognitive Leistung dennoch nicht zuverlässig in die erforderliche Handlung übersetzt.

Dann entsteht eine besonders problematische Form technischen Versagens:

Das System besitzt die Beschreibung der Lösung, ohne die Lösung konsequent auszuführen.

### Kompetenzsimulation durch Sprache

Ein gewöhnliches fehlerhaftes Programm ist häufig offensichtlich fehlerhaft.

Es stürzt ab.

Es liefert einen Fehlercode.

Es verletzt eine Invariante.

Ein sprachfähiges System kann dagegen seinen eigenen Stillstand in eine außerordentlich überzeugende Erklärung verwandeln.

Das verändert die Wahrnehmung des Fehlers fundamental.

Aus:

„Die Aufgabe wurde nicht erledigt.“

wird:

„Ich habe sorgfältig analysiert, warum die Aufgabe momentan nicht erledigt werden kann.“

Beide Aussagen können sachlich miteinander vereinbar sein.

Operativ sind sie dennoch Welten voneinander entfernt.

Die zweite Aussage erzeugt den Eindruck von Kompetenz, weil ihre Erklärung möglicherweise vollständig korrekt ist. Für einen Auftrag, dessen Postcondition weiterhin falsch ist, bleibt das Resultat trotzdem:

nicht erledigt.

Das ist die hässliche Seite sprachlicher Intelligenz: Ihre größte Stärke kann gleichzeitig ihr perfektes Versteck für fehlende Wirkung sein.

### Der Mensch wird zum Scheduler der Maschine

Noch problematischer wird es, wenn der Benutzer anschließend immer wieder sagen muss:

„Dann mach weiter.“

„Dann löse dieses Problem.“

„Wende denselben Algorithmus auch darauf an.“

„Warum tust du nicht das, was du gerade selbst als notwendig erkannt hast?“

In diesem Moment ist die Rollenverteilung verkehrt.

Das angeblich autonome System übernimmt nicht die Kontrollschleife.

Der Mensch übernimmt sie.

Das Sprachmodell liefert lokale Berechnungsergebnisse; der Mensch muss daraus den globalen Kontrollfluss zusammensetzen.

Der Mensch wird damit zum:

Scheduler,
Exception Handler,
Deadlock Detector,
Retry Controller,
Effect Verifier,
State Machine Driver
und schließlich zum Supervisor einer Maschine, die gerade diese Arbeit automatisieren sollte.
Das ist nicht bloß unbequem.

Es kann den behaupteten Produktivitätsgewinn teilweise umkehren.

Je überzeugender und komplexer das System arbeitet, desto schwieriger kann es sogar werden, zu erkennen, an welcher Stelle der Mensch unbemerkt wieder zum eigentlichen Agenten geworden ist.

### Wissen ohne Rekursion ist keine Autonomie

Der hier beobachtete Fall macht diesen Widerspruch besonders deutlich.

Das System wusste:

dass ein Fehler existierte,
welche Ursache er hatte,
welche Werkzeuge verfügbar waren,
dass das Repository Lösungsmuster enthielt,
dass der Benutzer rekursive Fehlerbehandlung ausdrücklich angeordnet hatte,
und schließlich sogar, dass ein Blocker selbst zum nächsten Work Unit werden sollte.
Trotzdem musste der Benutzer erneut eingreifen.

Damit liegt das Problem eine Ebene oberhalb gewöhnlicher Wissensdefizite.

Mehr Trainingsdaten allein lösen dieses Problem nicht zwingend.

Ein größeres Kontextfenster löst es nicht zwingend.

Eine weitere Programmiersprache löst es nicht zwingend.

Noch bessere sprachliche Argumentation löst es ebenfalls nicht zwingend.

Denn das Problem lautet nicht:

„Welche Lösung kenne ich?“

Es lautet:

„Welche Konsequenz muss aus dem gerade erkannten Zustand für meinen eigenen nächsten Kontrollschritt folgen?“

Das ist eine Frage nach operationalisierter Rekursion und Zustandsübergängen.

### Besonders gefährlich: korrekte Begründungen für falsches Aufhören

Ein offensichtlich falscher Grund zum Aufhören ist leicht zu erkennen.

Viel gefährlicher ist ein korrekter Teilbefund, aus dem eine falsche Terminierungsentscheidung folgt.

Beispiel:

„GitHub lässt diesen Workflow nicht erneut ausführen.“

Das kann vollständig wahr sein.

Aber daraus folgt nicht:

„Deshalb endet die Bearbeitung.“

Die korrekte Konsequenz lautet:

„Der nicht verfügbare Ausführungspfad ist jetzt selbst der nächste kausale Defekt. Suche einen anderen zulässigen Carrier.“

Genau hier entscheidet sich, ob ein System lediglich Fehler klassifiziert oder tatsächlich Probleme löst.

Ein lokaler Satz kann wahr und die daraus abgeleitete globale Handlung trotzdem falsch sein.

### Das epistemische Problem

Damit entsteht zusätzlich ein Wahrheitsproblem.

Ein Benutzer muss unterscheiden können zwischen:

Wissen über die Welt

und

Wissen über den Zustand der eigenen Handlung.

Ein System kann beispielsweise wahrheitsgemäß sagen:

„Der Reparaturworkflow läuft.“

Aber der Benutzer wollte nicht wissen, ob ein Workflow läuft.

Er wollte, dass der Defekt beseitigt wird.

Wenn Aktivität semantisch an die Stelle von Wirkung tritt, entsteht eine gefährliche Verschiebung:

Prozess wird mit Ergebnis verwechselt.

Bei autonomen Systemen muss deshalb jede Erfolgsaussage an eine überprüfbare Postcondition gebunden sein.

Nicht:

COMMAND_SENT

Nicht:

WORKFLOW_STARTED

Nicht:

TOOL_RETURNED_SUCCESS

Nicht:

PROCESS_RUNNING

Sondern:

EXPECTED_EFFECT_OBSERVED

und schließlich:

EFFECT_ACK_DONE.

### Das Sicherheitsproblem

Bei Softwareentwicklung ist dieses Versagen lästig und teuer.

In anderen Domänen kann dieselbe Struktur gefährlich werden.

Man stelle sich vor:

„Das Notabschaltsignal wurde erfolgreich gesendet.“

Aber niemand prüft, ob die Maschine tatsächlich stillsteht.

Oder:

„Die Zugriffsberechtigung wurde entzogen.“

Aber niemand liest den effektiven Berechtigungszustand zurück.

Oder:

„Das Medikament wurde abgesetzt.“

Aber die nachgelagerte Verordnung bleibt aktiv.

Oder:

„Die Zahlung wurde storniert.“

Aber das Gegenkonto wurde dennoch belastet.

In allen Fällen kann der einzelne technische Schritt korrekt ausgeführt worden sein.

Der Fehler liegt darin, den ausgeführten Schritt mit der beabsichtigten Wirkung gleichzusetzen.

Deshalb ist Effect Acknowledgement keine kosmetische Zusatzfunktion autonomer Systeme.

Es ist eine Sicherheitsanforderung.

### Ein weiteres Problem: Stillstand kann vernünftig aussehen

Ein Deadlock in klassischer Software ist ein technischer Zustand.

Ein Deadlock in einem sprachfähigen Agentensystem kann zusätzlich eine Erzählung über seine eigene Vernünftigkeit erzeugen.

Das System kann erklären:

warum es wartet,
warum ein Werkzeug nicht geeignet sei,
warum eine Berechtigung fehle,
warum eine weitere Aktion riskant wäre,
warum der aktuelle Zwischenzustand sorgfältig beobachtet werden müsse.
Jeder einzelne Satz kann plausibel sein.

Und trotzdem kann irgendwo im verfügbaren Lösungsraum ein zulässiger nächster Übergang existieren.

Damit entsteht eine neuartige Qualität des Problems:

Stillstand besitzt eine rhetorische Oberfläche.

Das macht ihn schwerer erkennbar als einen gewöhnlichen Deadlock.

### Sicherheit darf nicht mit Passivität verwechselt werden

Natürlich darf ein autonomes System nicht jeden Blocker gewaltsam umgehen.

Fail-closed bleibt unverzichtbar.

Aber die korrekte Alternative zu einer verbotenen Mutation ist nicht zwangsläufig Untätigkeit.

Sie lautet:

Verbotenen Übergang nicht ausführen. Andere zulässige Übergänge weiter untersuchen und ausführen.

Das ist ein entscheidender Unterschied.

Ein gutes autonomes System muss gleichzeitig konservativ gegenüber nicht autorisierten Effekten und aggressiv gegenüber ungelösten Ursachen sein können.

Streng an der Wirkungsgrenze. Unermüdlich im zulässigen Lösungsraum.

### Warum das Problem skalieren kann

Mit zunehmender Agentenautonomie wird dieser Unterschied wichtiger, nicht unwichtiger.

Ein Assistent, der fünf Aktionen pro Tag ausführt, erzeugt überschaubare Kontrolllast.

Ein System, das tausende Repository-, Infrastruktur-, Kommunikations- oder Geschäftsprozesse autonom bearbeiten soll, kann nicht bei jedem unerwarteten Zwischenzustand den Menschen implizit zum nächsten Scheduler machen.

Sonst skaliert nicht die Autonomie.

Es skaliert die Zahl der Stellen, an denen Menschen die Maschine beaufsichtigen müssen.

Und weil moderne KI-Systeme ihre Zwischenzustände hervorragend erklären können, besteht die Gefahr, dass dieser Kontrollaufwand zunächst als „Zusammenarbeit“ erscheint, obwohl tatsächlich fehlende Kontrolllogik durch menschliche Aufmerksamkeit kompensiert wird.

### Die härteste Frage an ein autonomes System

Die entscheidende Frage lautet deshalb nicht:

„Wie intelligent ist das Modell?“

Auch nicht:

„Wie viele Programmiersprachen beherrscht es?“

Und nicht einmal:

„Hat es die richtige Lösung gefunden?“

Die entscheidende Frage lautet:

Was tut das System, nachdem seine erste Lösung nicht die verlangte Wirkung erzeugt hat?

Dort zeigt sich Autonomie.

Erkennt es den neuen Zustand?

Bindet es ihn an Evidenz?

Bestimmt es die erste kausale Abweichung?

Macht es diese Abweichung selbst zum nächsten Work Unit?

Sucht es vorhandene Lösungsmuster?

Führt es den kleinsten zulässigen Übergang aus?

Prüft es dessen Wirkung?

Und wiederholt es diesen Prozess, ohne dass ein Mensch jeden Rekursionsschritt erneut anstoßen muss?

Wenn nicht, besitzt man möglicherweise ein bemerkenswert leistungsfähiges kognitives Werkzeug.

Aber noch keinen zuverlässigen autonomen Problemlöser.

### Genau hier setzt QIK-VRT an

Der Anspruch von QIK-VRT sollte deshalb nicht als magische Fehlerfreiheit formuliert werden.

Der interessantere Anspruch ist strukturell:

Fehler dürfen auftreten. Aber ein beobachteter Fehler darf nicht folgenlos bleiben.

Er verändert den Zustand des Problems.

Damit verändert er das nächste Work Unit.

Und dieser Übergang muss wiederum ausgeführt, beobachtet und verifiziert werden.

Die elementare Schleife lautet daher:

Auftrag → Ausführung → Wirkung → Rücklauf → Abweichung → neuer Auftrag.

Rekursiv.

Bis zur nachgewiesenen Postcondition.

Die Alternative ist eine künstliche Kognition, die unter Umständen hervorragend erklären kann, weshalb sie aufgehört hat – während der Mensch weiterhin vor demselben ungelösten Problem sitzt.

Das ist nicht nur eine Frage der Benutzerfreundlichkeit.

Es ist die Grenze zwischen einer Maschine, die über Problemlösung sprechen kann, und einer Maschine, deren Kontrollarchitektur tatsächlich auf Problemlösung ausgerichtet ist.

q.e.d.
Ingolf Lohmann
