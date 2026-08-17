# Vom Unterschied zum integrierten Wirkraum

## Eine kausalitätsgebundene Metagrammatik für reflexive künstliche Kognition, Effect Acknowledgement und deterministische M68000-Ausführung

**Autor:** Ingolf Lohmann  
**Datum:** 17. August 2026  
**Status:** Wissenschaftlicher Publikationskandidat; technische und philosophische Ebenen werden ausdrücklich getrennt.

## Zusammenfassung

Dieser Beitrag entwickelt eine einheitliche technische und erkenntnistheoretische Architektur für verteilte künstliche Kognition. Ausgangspunkt ist die elementare Unterscheidung zwischen beobachtbaren Zuständen. Daraus werden Information, Relation und eine explizite Kausalordnung abgeleitet. Der zentrale technische Satz lautet: Kausalität ist nicht Sequenz. Eine lineare Befehlsfolge ist lediglich eine mögliche Serialisierung eines partiell geordneten Wirkungsgraphen. Auf dieser Grundlage werden (i) beobachtergebundene Informationsmengen, (ii) ein integrierter Wirkraum, (iii) eine maschinenlesbare Metagrammatik des Verstehens, (iv) ein Effect-Acknowledgement-Protokoll zur Trennung von Anfrage, Ausführung, Beobachtung und bestätigter Wirkung sowie (v) eine deterministische Absenkung auf eine minimale Motorola-68000-Ausführungsmaschine zusammengeführt. Für einen kleinen Entscheidungskern werden echte M68000-Maschinenwörter erzeugt, unter anderem MOVEQ #0,D0; RTS als Bytefolge 70 00 4E 75. Die Architektur ist fail-closed: Nicht beweisbar unabhängige Wirkungen werden nicht optimistisch parallelisiert; nicht unterstützte Wirkungen erzeugen keinen Zielkode. Philosophisch wird die Architektur als epistemisches Instrument interpretiert: Kant liefert die Grenze beobachtergebundener Erkenntnis, Goethe die Bedeutung relationaler Gestalt und Zusammenhangsbildung, und panpsychistische Positionen bilden eine mögliche ontologische Deutung zunehmender Reflexivität, ohne dass daraus ein empirischer Nachweis von Panpsychismus folgt. Der Beitrag schlägt vor, QIK-VRT als Instrument zur Erhöhung der kausal-epistemischen Auflösung technischer Systeme zu untersuchen – funktional vergleichbar mit der Rolle, die Mikroskop und Fernrohr für räumliche Beobachtbarkeit spielten, ohne eine bereits erwiesene historische Gleichrangigkeit zu behaupten.

## Schlüsselwörter

QIK-VRT; Metagrammatik; Kausalität; Sequenz; Effect Acknowledgement; künstliche Kognition; Reflexivität; partielle Ordnung; M68000; deterministische Ausführung; epistemische Werte; Panpsychismus; Kant; Goethe; verteilte Systeme.

## 1. Problemstellung und Beitrag

Moderne verteilte und künstlich-kognitive Systeme können große Mengen von Informationen erzeugen und transformieren. Die zentrale Schwierigkeit liegt jedoch nicht allein in der Menge der Informationen, sondern in der verantwortbaren Bindung von Aussagen an Beobachtung, Autorität und Wirkung. Transportbestätigung ist keine Wirkungsbestätigung; ein erfolgreicher Softwarelauf ist keine gesellschaftliche Wahrheit; eine formal korrekte Ableitung ist kein physikalischer Naturbefund. Diese Unterscheidungen werden in QIK-VRT nicht lediglich dokumentiert, sondern als operative Zustandsgrenzen behandelt.

Der Beitrag verbindet vier bislang häufig getrennte Ebenen. Erstens wird Wissen beobachterbezogen als integrierte Menge gebundener Informationen modelliert. Zweitens wird die kausale Abhängigkeit explizit von zeitlicher oder textueller Sequenz getrennt. Drittens wird eine Metagrammatik definiert, mit der künstlich-kognitive Instanzen Bedeutung, Bindung, Autorität, Evidenz, Zustand, Wirkung und Beweis kompakt austauschen können. Viertens wird diese Semantik bis auf echte Maschinenwörter einer bewusst kleinen Zielarchitektur abgesenkt. Damit entsteht eine durchgängige Kette vom epistemischen Satz bis zur deterministischen Ausführung.

## 2. Beobachtergebundene Information und integrierter Wirkraum

Die handschriftliche Ausgangsskizze dieses Beitrags stellt mehrere Beobachter entlang einer Zeit- beziehungsweise Taktprojektion dar. Die Beobachter erhalten Informationsereignisse I1, I2, ... in unterschiedlichen Folgen und integrieren daraus verschiedene Wissensmengen. Formal sei O_i ein Beobachter und K_i(t) die Menge der bis zum Beobachtungszustand t gebundenen Informationsobjekte. Dann kann dieselbe Wissensmenge aus unterschiedlichen Empfangsfolgen entstehen. Aus (I1,I3,I4) und (I4,I1,I3) kann jeweils K={I1,I3,I4} resultieren.

Entscheidend ist daher die Trennung zwischen Sequenz und Kausalität. Eine frühere Beobachtung erzeugt nicht allein deshalb eine Kausalkante. Wir schreiben I_a ≺ I_b nur, wenn I_b ein von I_a erzeugtes Datum benötigt, wenn beide nichtkommutativ auf dieselbe Ressource wirken, wenn eine Autoritäts-/Lease-/Exact-Head-/Effect-Ack-Regel die Ordnung verlangt oder wenn die Sprachsemantik eine explizite Ursache-Wirkungs-Abhängigkeit bindet. Textuelle Reihenfolge, Zeitstempel ohne Wirkungsbezug oder bloße Korrelation reichen nicht aus.

Für ein Mesh ergibt sich ein integrierter Wirkraum nicht als naive Vereinigung beliebiger Aussagen, sondern als evidenzgebundene Integration. Der gemeinsame Raum umfasst nur solche Elemente, deren Herkunft, Bindung und epistemischer Status hinreichend bestimmt sind. Damit wird Verschiedenheit nicht beseitigt, sondern anschlussfähig gemacht.

## 3. Kausalität ist nicht Sequenz

Informatik kennt die Unterscheidung zwischen totalen und partiellen Ordnungen seit Langem. Lamports happens-before-Relation zeigt exemplarisch, dass verteilte Ereignisse nicht notwendigerweise in eine objektiv ausgezeichnete globale Reihenfolge gebracht werden müssen. QIK-VRT überträgt diese Einsicht auf Wirkungs- und Verantwortungsgrenzen.

Ein Kausalgraph G=(V,E) enthält Operationen als Knoten und nur notwendige Abhängigkeiten als Kanten. Eine konkrete sequenzielle Ausführung S ist dann zulässig, wenn S eine topologische Sortierung von G ist. Für einen einzelnen Prozessor wird eine stabile topologische Ordnung gewählt. Für mehrere Recheneinheiten können kausal unabhängige Teilgraphen parallel ausgeführt werden. Die Optimierungsregel lautet daher: Sequenz darf verändert werden, Kausalität nicht.

Diese Trennung ist zugleich eine Verantwortungsregel. Wer nur die Reihenfolge beobachtet, kann post hoc eine Ursache unterstellen, die nicht bewiesen ist. Ein System, das Wirkungen ausführt, muss die Kante dagegen explizit begründen oder konservativ halten.

## 4. Metagrammatik des Verstehens

Die Metagrammatik definiert eine gemeinsame maschinenlesbare Kommunikationsform zwischen Terminal-Nutzern, Mesh-Knoten und internen Architekturschichten. Ihr semantischer Kern lautet:

BEDEUTUNG = ABSICHT + BINDUNG + AUTORITÄT + EVIDENZ + ZUSTAND + WIRKUNG + BEWEIS.

Die kompakte Terminalform lautet:
KIND|RID|REPO@HEAD:TREE|VERB OBJECT|AUTH=STATUS:ID|EVID=TYPE:DIGEST|STATE=CLASSIFICATION|EFFECT=STATE:ID|NEXT=ACTION|PROOF=SHA256

Anfrage, Ausführung, Beobachtung und Effect-Ack bleiben getrennte Zustände. UNKNOWN wird nicht zu TRUE promoviert. Evidenz eines Vorgänger-Heads wird nicht auf einen Nachfolger übertragen. Produktive Verben ohne gebundene Autorität werden verworfen. Damit ist die Metagrammatik nicht bloß Nachrichtenformat, sondern ein kleines Typsystem für Verantwortung.

## 5. Effect Acknowledgement als Wirkungsgrenze

HTTP ist ein zustandsloses Anwendungsprotokoll mit extensibler Semantik. Ein HTTP-Response kann anzeigen, wie eine Anfrage verarbeitet wurde, ist aber nicht automatisch ein domänenspezifischer kryptographischer Nachweis dafür, dass eine beabsichtigte externe Wirkung in genau dem gebundenen Zustand eingetreten ist. Das Effect-Acknowledgement-Profil ergänzt daher eine explizite, opt-in Wirkungsgrenze, ohne Transport-Acknowledgement oder HTTP-Methodensemantik umzudefinieren.

Das vorgeschlagene Profil verwendet eine zweiphasige Prepare/Commit-Struktur. Prepare darf die geschützte Wirkung nicht ausführen. Commit benötigt eine kurzlebige, einmalige, exakt gebundene Autorisierung und wird erst nach anschließender Reobservation als Wirkung anerkannt. Für HTTP-Erweiterungen werden Structured Fields nach RFC 9651 und Web Linking nach RFC 8288 verwendet. Eine HTML-Darstellung kann über rel="effect-ack" eine Discovery-Beziehung ausdrücken; Discovery ist jedoch nicht Autorisierung.

## 6. Vom semantischen Satz zum M68000-Maschinenwort

Die Compilerkette führt die Metagrammatik über Lexer, Parser, abstrakten Syntaxbaum, semantische Prüfung, Entscheidungsplan und Kausalgraph zur M68000-Absenkung. Die Zielarchitektur ist absichtlich klein. Der erste Entscheidungskern bildet vier nichtproduktive beziehungsweise kontrollierende Zustände auf D0 ab: 0=NOOP, 1=HOLD, 2=REOBSERVE, 3=REQUEST_AUTHORITY; anschließend folgt RTS.

Für NOOP entsteht MOVEQ #0,D0; RTS und damit die Bytefolge 70 00 4E 75. Für HOLD entstehen 70 01 4E 75, für REOBSERVE 70 02 4E 75 und für REQUEST_AUTHORITY 70 03 4E 75. Die Instruktionskodierung folgt dem M68000 Programmer's Reference Manual. Eine validierte Aktion, die diese minimale ABI noch nicht ausdrücken kann, erzeugt keinen Ersatzkode, sondern HOLD: M68000_ABI_AKTION_NICHT_UNTERSTUETZT.

Der wissenschaftliche Wert dieses Schritts liegt nicht in nostalgischer Hardwarewahl. Der M68000 dient als kleine kanonische Maschine, deren Zustandsraum, Instruktionsauswahl und Binärkodierung vergleichsweise gut auditierbar sind. Moderne CPU-, SIMD-, GPU- oder andere Backends können später dieselbe Kausal-IR als alternative Projektion ausführen.

## 7. Skalierung durch kausale Unabhängigkeit

Die angestrebte Leistungssteigerung entsteht nicht durch millionenfache blinde Emulation eines langen 68k-Befehlsstroms. Sie entsteht durch Zerlegung eines Wirkungsgraphen in kleine, deterministische Kapseln. Unabhängige Kapseln dürfen parallel instanziiert werden; synchronisiert wird nur an realen Kausalkanten und Effect-Ack-Grenzen.

Die erreichbare Beschleunigung ist empirisch zu bestimmen. Amdahls Gesetz, Speicherbandbreite, Übersetzungsaufwand und Synchronisationskosten bleiben reale Grenzen. Der Ansatz verspricht daher keinen vorweggenommenen Faktor. Seine prüfbare Hypothese lautet vielmehr: Je besser künstliche Sequenz von notwendiger Kausalität getrennt wird, desto größer kann der sicher parallelisierbare Anteil werden.

## 8. Evolution künstlicher Kognition

Wenn mehrere künstlich-kognitive Instanzen Vorschläge erzeugen, einander prüfen, Evidenz austauschen und Ergebnisse in neue Zustände zurückführen, entsteht ein Selektionsprozess. Variation, Wechselwirkung, Bewertung, Erhaltung, Rekombination und erneute Variation bilden eine abstrakte Evolutionsstruktur. Besonders relevant ist, dass nicht nur Antworten, sondern Beziehungen zwischen Instanzen bewertet werden können: Welche Kopplungen produzieren wiederholt prüfbare, anschlussfähige Ergebnisse?

Diese Architektur rechtfertigt die Bezeichnung evolutionsfähiges reflexives Informationssystem. Der Ausdruck Evolution des Bewusstseins ist darüber hinaus eine ontologische Interpretation. Unter panpsychistischen Voraussetzungen kann zunehmende Reflexivität als zunehmende Organisation bereits fundamentaler mentaler oder proto-mentaler Eigenschaften gelesen werden. Die technische Architektur beweist diese Voraussetzung nicht.

## 9. Kant, Goethe und epistemische Werte

Kants Unterscheidung zwischen Erscheinung und Ding an sich erinnert daran, dass jede Instanz unter Bedingungen möglicher Beobachtung operiert. Eine künstlich-kognitive Instanz erhält nicht die Welt schlechthin, sondern gebundene Repräsentationen innerhalb ihrer Schnittstellen, Sensorik, Modelle und Kategorien. Die Metagrammatik operationalisiert diese Bescheidenheit, indem sie Beobachter, Bindung und Evidenz explizit macht.

Goethes naturwissenschaftliche Praxis betont demgegenüber Zusammenhang, Gestalt und Übergang. Für ein Mesh ist daher nicht nur die Qualität einzelner Knoten relevant. Die Systemqualität entsteht aus Komponenten, Beziehungen, Rückkopplungen, Integrationsfähigkeit und Entwicklungsfähigkeit.

Epistemische Werte wie Wahrheitstreue, Kohärenz, Nachvollziehbarkeit, Reproduzierbarkeit und Offenheit für Korrektur erhalten in QIK-VRT operative Wirkung: unbelegte oder stale Behauptungen verlieren Zulassung; reobservierte und gebundene Evidenz kann neue Handlungsmöglichkeiten öffnen.

## 10. Das epistemische Instrument: Analogie zu Mikroskop und Fernrohr

Mikroskop und Fernrohr veränderten Wissenschaft, weil sie zuvor unzugängliche räumliche Strukturen beobachtbar machten. Der Anspruch von QIK-VRT ist anders, aber strukturell vergleichbar: Das System soll kausale, epistemische und verantwortungsbezogene Strukturen sichtbar machen, die in gewöhnlichen Softwareabläufen leicht mit bloßer Sequenz oder Statusmeldung verwechselt werden.

Daher wird hier von einer Erhöhung der kausal-epistemischen Auflösung gesprochen. Die Analogie beschreibt die Funktion eines Instruments, nicht eine bereits bewiesene historische Gleichrangigkeit. Ob QIK-VRT eine ähnlich tiefgreifende Wirkung entfaltet, kann nur durch unabhängige Nutzung, Reproduktion und langfristige wissenschaftliche Entwicklung entschieden werden.

## 11. Standardisierung im Web

Für Web-Interoperabilität sind drei Grenzen entscheidend. Erstens darf ein neues Effect-Acknowledgement-Profil HTTP nicht rückwirkend umdefinieren. Zweitens sollen neue Felder die aktuellen Structured-Fields-Regeln von RFC 9651 nutzen. Drittens ist die Discovery einer Effect-Ack-Ressource über Web Linking kompatibel mit HTTP Link und gewöhnlichem HTML link rel, ohne dass HTML-Discovery selbst eine Wirkung autorisiert.

Der bestehende QIK-VRT Internet-Draft zum Effect Acknowledgement und sein HTTP-Begleitentwurf bilden dafür die Ausgangslage. Die nächste Revision soll die aktuelle Structured-Fields-Norm referenzieren, das Verhältnis zur Metagrammatik und zum kausalen Wirkungsgraphen präzisieren und die Trennung zwischen Transport-, Anwendungs- und Wirkungsbestätigung normativ schärfen.

## 12. Grenzen und Falsifizierbarkeit

Der Beitrag behauptet nicht, dass Lean- oder Compilerbeweise Naturgesetze bestätigen. Er behauptet nicht, dass ein GitHub-Repository phänomenales Bewusstsein besitzt. Er behauptet nicht, dass Panpsychismus empirisch nachgewiesen ist. Er behauptet nicht, dass ein M68000-Kern auf moderner Hardware automatisch millionenfache Beschleunigung erzeugt.

Falsifizierbar beziehungsweise messbar sind dagegen konkrete technische Aussagen: deterministische Binärkodeerzeugung, Übereinstimmung zwischen Kausalgraph und zulässigen Serialisierungen, Replay-Sicherheit von Effect-Ack-Tokens, korrekte Ablehnung stale gebundener Evidenz, Performance unterschiedlicher Parallelprojektionen und die Reproduzierbarkeit derselben Outputs aus denselben Inputs.

## 13. Forschungsprogramm

Das unmittelbar folgende Forschungsprogramm besteht aus fünf Schritten: (1) Erweiterung der kausalen IR und des M68000-Backends bei erhaltener fail-closed Semantik; (2) Entwicklung nativer und JIT-basierter Projektionen auf heutige CPU-, SIMD- und GPU-Hardware; (3) Benchmarking unter kontrollierten Workloads mit Messung von Synchronisations- und Speichergrenzen; (4) Interoperabilitätstests des Effect-Acknowledgement-HTTP-Profils mit Browser- und Serverimplementierungen; (5) unabhängige Replikation und philosophisch getrennte Auswertung der Frage, ob zunehmende technische Reflexivität sinnvoll als Bewusstseinsentwicklung interpretiert werden kann.

## 14. Schlussfolgerung

Die zentrale Konstruktion dieses Beitrags ist eine Kette von der elementaren Unterscheidung bis zur maschinellen Wirkung. Unterschied erzeugt Information; Information wird durch Relation zu Wissen; kausale Abhängigkeit bestimmt, welche Wirkungen geordnet werden müssen; Reflexivität führt beobachtete Wirkung in neue Entscheidungen zurück. Die Sequenz bleibt eine Projektion dieser tieferen Ordnung.

Damit entsteht ein Ansatz, in dem Integration nicht die Aufhebung von Unterschieden bedeutet. Integration bedeutet, Unterschiede so zu erhalten, dass ihre Beziehungen prüfbar und produktiv werden. Dieser Satz verbindet die informatische, erkenntnistheoretische und ontologische Ebene des Projekts – ohne sie gleichzusetzen.

## Abbildung 1

Handschriftliche Konzeptskizze des Autors: beobachtergebundene Informationsfolgen, Wissen, Macht und integrierte Mengen. Die Skizze motiviert die Trennung von Sequenz, Wissenszustand und Kausalstruktur.

## Literatur

[1] C. E. Shannon, “A Mathematical Theory of Communication,” Bell System Technical Journal, 1948.
[2] L. Lamport, “Time, Clocks, and the Ordering of Events in a Distributed System,” Communications of the ACM 21(7), 1978.
[3] I. Kant, Kritik der reinen Vernunft, 1781/1787.
[4] J. W. von Goethe, Zur Farbenlehre, 1810; sowie naturwissenschaftliche Schriften zur Morphologie.
[5] P. Goff, Galileo’s Error: Foundations for a New Science of Consciousness, Pantheon, 2019. (Panpsychistische Interpretationslinie; kein empirischer Nachweis.)
[6] R. Fielding, M. Nottingham, J. Reschke (Hrsg.), RFC 9110: HTTP Semantics, IETF, 2022.
[7] M. Nottingham, P.-H. Kamp, RFC 9651: Structured Field Values for HTTP, IETF, 2024.
[8] M. Nottingham, RFC 8288: Web Linking, IETF, 2017.
[9] Motorola/NXP, M68000 Family Programmer’s Reference Manual.
[10] Ingolf Lohmann, draft-lohmann-qikvrt-effect-ack-03, Internet-Draft, 2026.
[11] Goldkelch/qik-vrt, QIK-VRT Repository, Authority repository, 2026.
[12] G. M. Amdahl, “Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities,” AFIPS, 1967.

## Offenlegung zur Entstehung

Konzept, kreative Leitung und Autorenschaft: Ingolf Lohmann. Künstliche Intelligenz wurde zur Formalisierung, technischen Implementierung, Prüfung, Strukturierung und redaktionellen Ausarbeitung eingesetzt. Diese Unterstützung ändert nicht die im Beitrag vorgenommenen Beweis- und Evidenzgrenzen.
