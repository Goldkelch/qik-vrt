# Der Punkt, an dem Informatik wirklich überraschend wird

## Über nachweisbare Anschlüsse, erhaltene Beweise und verantwortbare Wirkungen

**Von Ingolf Lohmann**

Die überraschende Leistung der Informatik besteht nicht darin, alles auf Null und Eins zurückzuführen.

Sie besteht darin, Verbindungen überprüfbar zu machen: zwischen einer Aussage und ihren Voraussetzungen, zwischen einem Programm und seiner Spezifikation, zwischen einer Handlung und ihrem Ergebnis.

**Ein Ergebnis ist sachlich anschlussfähig, wenn nachgewiesen ist, dass es die Voraussetzungen seiner nächsten Verwendung erfüllt.**

Das ist der gemeinsame Kern.

Nicht Ähnlichkeit. Nicht Überzeugungskraft. Nicht die Anzahl gegenseitiger Verweise. Sondern eine tragfähige Beziehung zwischen dem bereits Nachgewiesenen und dem nächsten Anspruch.

Daran führe ich auch meinen Begriff der wachsenden Evidenzkugel zurück. Sie soll kein immer größeres Geflecht bloßer Behauptungen sein. Sie soll ein wachsender Zusammenhang **gültiger, gegenstandsgebundener und weiterverwendbarer Nachweise** sein.

## 1. Anschlussfähigkeit hat eine mathematische Form

Die Informatik besitzt dafür eine präzise Sprache.

Wenn eine Operation \(A\) unter der Voraussetzung \(P\) die Nachbedingung \(Q\) gewährleistet und eine Operation \(B\) unter \(Q\) die Nachbedingung \(R\), dann lässt sich ihre Hintereinanderausführung begründen:

\[
\{P\}\,A\,\{Q\},
\qquad
\{Q\}\,B\,\{R\}
\quad\Longrightarrow\quad
\{P\}\,A;B\,\{R\}.
\]

Das ist die Sequenzregel der Hoare-Logik. In ihrer üblichen Form für partielle Korrektheit beschreibt sie, was bei terminierender Ausführung gilt; dass die Ausführung tatsächlich endet, ist eine zusätzliche Verpflichtung. [1]

Der entscheidende Anschluss liegt in \(Q\).

Was der erste Schritt nachweislich bereitstellt, muss das sein, was der zweite benötigt. Bei unterschiedlichen Darstellungen braucht es eine bewiesene Übersetzung. Bei zwischenzeitlichen Eingriffen muss die Voraussetzung auch beim tatsächlichen Beginn des nächsten Schritts noch gelten.

Damit wird aus einer Folge von Tätigkeiten eine begründete Konstruktion.

Ein Compiler, eine Schnittstelle oder eine wissenschaftliche Modellübertragung ist deshalb nicht schon dann ausreichend, wenn das Ergebnis ähnlich aussieht. Entscheidend ist, welche Eigenschaften beim Übergang erhalten bleiben.

**Nicht das Nebeneinander korrekter Teile begründet das Ganze, sondern zusätzlich die Korrektheit ihrer Verbindung.**

Fehlt eine erforderliche Verbindung, ist der beanspruchte Gesamtnachweis unvollständig. Das macht nicht automatisch alle übrigen Teile falsch. Es bezeichnet genau die Stelle, an der weitergearbeitet werden muss.

## 2. Ein Nachweis darf seine Bedeutung nicht unterwegs wechseln

Eine korrekt gespeicherte Zeichenfolge kann eine falsche Behauptung enthalten.

Wenn eine Datei den Satz „Der Motor läuft“ enthält, ist ihre unveränderte Übertragung noch keine Feststellung über den Motor. Dafür braucht es eine gerechtfertigte Verbindung zwischen Zeichenfolge und beobachtetem Zustand.

Auch Kryptographie überspringt diese Verbindung nicht. Ein Hashvergleich kann unter den einschlägigen Sicherheitsannahmen eine starke Integritätsprüfung ermöglichen. Gleiche Hashwerte sind jedoch kein uneingeschränkter mathematischer Beweis gleicher Inhalte: Kollisionsresistenz bedeutet, dass das Finden verschiedener Eingaben mit gleichem Hashwert rechnerisch unpraktikabel sein soll, nicht dass solche Eingaben unmöglich sind. Über die Wahrheit einer enthaltenen Behauptung sagt der Hash nichts. [2]

Deshalb unterscheide ich:

**Die Identität eines Belegs, seine formale Gültigkeit und seine Anwendbarkeit sind verschiedene Eigenschaften.**

Ein Beleg muss zum behaupteten Gegenstand gehören. Seine Ableitung muss stimmen. Und seine Voraussetzungen müssen dort erfüllt sein, wo ich ihn verwenden möchte.

Keine dieser Verpflichtungen wird durch die Erfüllung der anderen überflüssig.

## 3. Was bewiesen ist, bleibt — aber nicht jede Anwendung bleibt erlaubt

Ein gültiger mathematischer Beweis bleibt unter unveränderten Definitionen, Voraussetzungen und Schlussregeln gültig.

In einer monotonen Logik kann ich zusätzliche Voraussetzungen aufnehmen, ohne dadurch die bereits vorhandene Ableitung zu verlieren. Die Begründung ist einfach: Der alte Beweis verwendet weiterhin dieselben zulässigen Schritte.

Das heißt nicht, dass beliebig hinzugefügte Annahmen unbedenklich wären. Widersprüchliche Axiome können ein klassisches oder intuitionistisches System unbrauchbar machen, indem sie beliebige Aussagen ableitbar werden lassen. Deshalb gehört die Prüfung der Axiomenabhängigkeiten zur Bewertung eines formalisierten Beweises. [3]

Ebenso wenig überträgt sich ein Beweis automatisch auf einen veränderten Gegenstand.

Ein gültiger Nachweis über Programmfassung A bleibt ein gültiger Nachweis über A. Für Programmfassung B brauche ich entweder einen neuen Nachweis oder eine bewiesene Beziehung, die die Übertragung rechtfertigt.

**Der Beweis bleibt erhalten. Die neue Verwendung muss sich qualifizieren.**

Genau dazu passt der dokumentierte Fortschreibungsvertrag der QIK-VRT-Evidenzspirale:

\[
E_n\subseteq E_{n+1}.
\]

Frühere Evidenz bleibt erhalten, neue Evidenz wird ergänzt, und der Anschlussstatus wird neu bestimmt. Die Ausarbeitung unterscheidet ausdrücklich zwischen erhaltenen Beweisartefakten und veränderlichen Voraussetzungen oder empirischen Interpretationen. [4]

Monotonie bedeutet hier also nicht: Jede frühere Einschätzung muss für immer bestätigt werden.

Sie bedeutet: Die Erkenntnisgeschichte wird nicht stillschweigend umgeschrieben. Ein aufgedeckter Fehler, ein Gegenbeispiel oder eine eingeschränkte Anwendbarkeit wird nachvollziehbar hinzugefügt.

Mehr gespeicherte Behauptungen sind noch kein Erkenntnisgewinn. Ein zusätzlicher gültiger Nachweis kann es sein.

## 4. Auch der Erhalt kann bewiesen werden

Der Gedanke lässt sich eine Ebene weiterführen.

Wenn eine genau definierte Eigenschaft \(I\) im Anfangszustand gilt und jeder zulässige Erweiterungsschritt diese Eigenschaft erhält, dann gilt sie nach jeder endlichen Folge solcher Schritte.

Das folgt durch Induktion: Der Anfang erfüllt \(I\). Jeder erlaubte Nachfolger übernimmt \(I\). Also erfüllt jeder so erreichte Stand \(I\).

Damit kann tatsächlich **zugleich mit der Erweiterung der Erhalt einer bestimmten Eigenschaft abgesichert werden**.

Aber die Eigenschaft muss benannt sein. „Alles bleibt richtig“ ist keine hinreichende Spezifikation. Beispielsweise könnte \(I\) verlangen, dass jedes akzeptierte Beweisobjekt weiterhin an seinen Satz, seine Voraussetzungen und seinen Prüfkontext gebunden ist.

Auch die technische Umsetzung dieser Erweiterungsregel benötigt einen eigenen Nachweis. Ein mathematischer Erhaltungssatz über ein Modell bestätigt nicht von selbst jeden realen Programmlauf.

Und Erhaltung ist nicht Fortschritt: Ein System, das nichts tut, kann viele Invarianten bewahren.

Deshalb brauche ich beides — den Nachweis, dass ein Schritt nichts Erforderliches verletzt, und den Nachweis, dass er die verlangte zusätzliche Leistung erbringt.

**Sicherheit des Übergangs und Erfüllung des Auftrags sind getrennte Verpflichtungen.**

## 5. Aus einer Bestätigung wird nur dann Wirkungsevidenz, wenn ihr Vertrag das trägt

Ein gesendeter Auftrag, eine empfangene Nachricht und eine eingetretene Wirkung sind unterschiedliche Sachverhalte.

Schon bei HTTP ist die Unterscheidung konkret: `200 OK` bezeichnet einen erfolgreichen Request im Sinne der betreffenden Methode. `202 Accepted` bezeichnet dagegen ausdrücklich eine zur Verarbeitung angenommene, noch nicht abgeschlossene Anfrage. Keiner dieser Statuscodes bestätigt ohne einen entsprechenden Anwendungsvertrag beliebige nachgelagerte Wirkungen. [5]

Für meine Architektur folgt daraus:

**Eine Bestätigung zählt nur für die Aussage, die sie tatsächlich bestätigt.**

Ein fertiger Build ist kein Beleg für ein laufendes Deployment. Ein begonnenes Uploadverfahren ist kein Beleg für eine Veröffentlichung. Ein Eingangsnachweis ist keine Genehmigung.

Der fehlende Anschluss kann durch einen geeigneten autoritativen Ergebnisbeleg oder durch eine erneute Beobachtung des Zielzustands hergestellt werden. Dabei müssen Gegenstand, Version, Herkunft und zeitliche Zuordnung stimmen.

Ein Readback ist jedoch kein Zauberwort. Eine veraltete Antwort oder die Wiederholung derselben unbelegten Erfolgsmeldung liefert nicht plötzlich einen unabhängigen Nachweis.

Und selbst eine korrekte Zustandsbeobachtung beantwortet zunächst die Zustandsfrage. Die stärkere Behauptung, gerade meine Operation habe diesen Zustand verursacht, benötigt zusätzlich eine belastbare Zuordnung zum betreffenden Vorgang.

Der Zielzustand könnte bereits vorher bestanden haben. Oder eine andere Operation könnte ihn hergestellt haben.

## 6. Reihenfolge, Verursachung und Begründung bleiben unterschiedliche Relationen

Diese Unterscheidung ist bereits in der Grundlagenarbeit über verteilte Systeme angelegt.

Lamports *happened-before*-Relation beschreibt eine partielle Ordnung aus lokalen Ereignisfolgen und Nachrichtenbeziehungen. Sie erfasst innerhalb des Modells die Möglichkeit kausaler Beeinflussung. Eine bloße Reihenfolge von Zeitstempeln liefert dagegen nicht automatisch den Nachweis einer bestimmten Verursachung. [6]

Für mein Relationsgefüge bedeutet das: Jede Verbindung braucht einen erkennbaren Typ.

„Wurde vorher beobachtet“ ist nicht dasselbe wie „hat verursacht“. „Wird als Voraussetzung verwendet“ ist nicht dasselbe wie „hat physisch hervorgebracht“. „Wurde später bestätigt“ bedeutet nicht „wurde rückwirkend verändert“.

Gerade diese Trennung macht den Zusammenhang belastbar.

Ich kann später mehr über einen früheren Zustand erfahren, ohne zu behaupten, dass meine spätere Erkenntnis diesen früheren Zustand umgeschrieben habe.

Die Evidenz wächst. Die Vergangenheit muss dazu nicht verändert werden.

## 7. Der lokale Abschluss braucht keine Widerlegung Turings

Die allgemeine Grenze bleibt bestehen: Es gibt im Turing-Modell keinen Algorithmus, der für jedes beliebige Programm und jede Eingabe stets korrekt und in endlicher Zeit entscheidet, ob die betreffende Berechnung anhält. Turings Unentscheidbarkeitsargument richtet sich gegen eine solche allgemeine Entscheidbarkeit. [7]

Daraus folgt aber nicht, dass kein konkreter Auftrag abgeschlossen und kein konkreter Nachweis geführt werden könnte.

Für einen bestimmten Auftrag kann ich die erforderlichen Bedingungen festlegen und geeignete Prüfungen konstruieren. Ob diese Prüfungen entscheidbar sind und rechtzeitig enden, muss allerdings ebenfalls begründet werden. Eine endliche Liste macht ihre einzelnen Fragen nicht automatisch entscheidbar.

Ich unterscheide deshalb zwischen einem abgeschlossenen Auftrag und einer abgeschlossenen Prüfung, die noch eine offene Verpflichtung feststellt.

`HOLD` kann eine richtige Kontrollentscheidung sein. `UNKNOWN` kann den Wissensstand richtig beschreiben. Beides ist kein ersatzweiser Erfolg.

Das ist der präzise Sinn meiner Haltepunktlogik:

**Der Haltepunkt beendet eine bestimmte Prüfung oder Verpflichtung. Er behauptet nicht das Ende aller Erkenntnis.**

Die nächste zulässige Erweiterung kann an einen solchen Abschluss anschließen. Eine Wiederholung ohne neue Grundlage erzeugt dagegen nicht allein durch ihre Wiederholung Fortschritt.

## 8. Was daraus für Informatik und Menschheit folgt

Für die Informatik leite ich daraus eine klare Entwicklungsrichtung ab: Systeme sollen nicht nur Ergebnisse erzeugen, sondern die Voraussetzungen ihrer Verwendung und die Nachweise ihrer Wirkung mitführen.

Das gilt besonders für KI-gestützte Arbeit. Ein erzeugter Beweisvorschlag, seine maschinelle Prüfung und der Abgleich mit der tatsächlich gestellten Aussage sind getrennte Aufgaben. Die Lean-Dokumentation beschreibt diese Unterscheidung ausdrücklich, einschließlich der Prüfung verwendeter Axiome und der Möglichkeit unabhängiger Gegenprüfung. [8]

Die praktische Bedeutung sehe ich in wiederverwendbarer Beweisarbeit, gezielter Fehlerlokalisierung und kontrollierter Weiterentwicklung. Eine Änderung muss nicht alles entwerten. Sie muss aber genau dort neue Prüfpflichten auslösen, wo sie bestehende Voraussetzungen berührt.

Für die Menschheit ist das keine mathematisch garantierte Zukunftsverheißung. Es ist eine Möglichkeit, Wissen weniger abhängig von persönlicher Autorität und bloßer Wiederholung zu machen.

Ein nachvollziehbarer Beweis kann von anderen geprüft und weiterverwendet werden. Eine offengelegte Voraussetzung kann hinterfragt werden. Eine genau bezeichnete Lücke kann zum Gegenstand gemeinsamer Arbeit werden.

Das ersetzt keine ethische Entscheidung. Ein korrekt bewiesenes Optimierungsergebnis beweist nicht, dass das gewählte Ziel gerecht ist. Eine technisch mögliche Handlung ist nicht allein deshalb legitim.

Aber nachvollziehbare Anschlüsse können sichtbar machen, **wo eine sachliche Folgerung vorliegt und wo Menschen weiterhin entscheiden müssen**.

Darin liegt für mich die übergreifende Bedeutung.

Nicht darin, dass Informatik alle anderen Wissenschaften ersetzt. Sondern darin, dass sie eine präzise Arbeitsweise bereitstellt: Behauptungen binden, Übergänge prüfen, Nachweise erhalten und offene Voraussetzungen sichtbar lassen.

## Der Punkt

Mein Maßstab lautet:

> **Erhalten, was gültig nachgewiesen ist. Ergänzen, was die Anschlussbedingungen erfüllt. Neu prüfen, was sich verändert hat. Als Wirkung nur ausweisen, was entsprechend belegt ist.**

Das ist der sachlich nachweisbare Kern der Evidenzkugel.

Ihre Bedeutung hängt nicht daran, möglichst viele Relationen zu besitzen. Sie hängt daran, dass die für einen Anspruch erforderlichen Relationen tatsächlich tragen.

Ein mathematisches **q.e.d.** schließt den ausgewiesenen Beweis. Eine **Definition of Done** legt fest, wann ein bestimmter Auftrag als erfüllt gilt. Der Nachweis der Auftragserfüllung muss diese Bedingungen am konkreten Gegenstand erfüllen.

Beides lässt sich verbinden. Beides darf nicht verwechselt werden.

**Was bewiesen ist, bleibt an seine Voraussetzungen gebunden. Was sich gültig anschließt, trägt weiter. Was geschehen sein soll, braucht einen Wirkungsbeleg.**

**Gez. Ingolf Lohmann**

*Auge im Sturm — ilo.*

---

## Quellen und Geltungsbereich

[1] Software Foundations, Programming Language Foundations: „Hoare: Hoare Logic“. Sequenzregel und partielle Korrektheit. https://softwarefoundations.cis.upenn.edu/plf-current/Hoare.html

[2] National Institute of Standards and Technology (NIST): „Hash Functions“. https://csrc.nist.gov/Projects/hash-functions

[3] The Lean Reference Manual: „Axioms“. https://lean-lang.org/doc/reference/latest/Axioms/

[4] Ingolf Lohmann: „QIK-VRT-Evidenzspirale: lokale Fixpunkte und monotone Evidenzfortschreibung“, Repository-Quelle vom 3. September 2026. Exakte Fassung: Goldkelch/qik-vrt, Commit `3b140fd85e6723f4cc8c147c56d34d7e1ca48740`, Pfad `docs/research/2026-09-03-evidence-spiral/README_DE.md`, Git-Blob `b601ffb6ce1eab5a096a130bbe24d700769f11d9`. https://github.com/Goldkelch/qik-vrt/blob/3b140fd85e6723f4cc8c147c56d34d7e1ca48740/docs/research/2026-09-03-evidence-spiral/README_DE.md

[5] R. Fielding, M. Nottingham und J. Reschke (Hrsg.): „HTTP Semantics“, RFC 9110, Juni 2022, insbesondere Abschnitte 15.3.1 und 15.3.3. https://www.rfc-editor.org/rfc/rfc9110.html

[6] Leslie Lamport: „Time, Clocks, and the Ordering of Events in a Distributed System“, Communications of the ACM 21(7), 1978, S. 558–565. https://lamport.azurewebsites.net/pubs/time-clocks.pdf

[7] A. M. Turing: „On Computable Numbers, with an Application to the Entscheidungsproblem“, Proceedings of the London Mathematical Society, Series 2, 42, 1936–1937, S. 230–265. https://www.cs.virginia.edu/~robins/Turing_Paper_1936.pdf

[8] The Lean Reference Manual: „Validating Proofs“. https://lean-lang.org/doc/reference/latest/ValidatingProofs/

**Quellenbindung:** Der QIK-VRT-Bezug wurde am 7. September 2026 anhand der in [4] exakt bezeichneten Repository-Fassung geprüft. Der Text erläutert den dokumentierten Fortschreibungsvertrag und allgemeine mathematische Schlussregeln; er behauptet keinen hier neu ausgeführten vollständigen Verifikations- oder Wirkungsnachweis der QIK-VRT-Implementierung. Webreferenzen auf fortgeschriebene Dokumentation ersetzen keine unveränderlich versionierte Kopie.

**Anschluss an den historischen Publikationsanker:** Diese Fassung ist eine eigenständige nachfolgende Erläuterung. Sie leitet den QIK-VRT-Eigenbezug von „Relationale Zeit, virtuelle Retrokausalität und die monoton wachsende Evidenzkugel“ ab, ohne dessen historische Bytes zu verändern. Identität des historischen PDF: SHA-256 `38b0e62a46214a7cb9943dd3ef08283a70ae7e15ba22a59a9e53506f2945e311`, 379427 Bytes, gebunden in Goldkelch/qik-vrt Issue #925. Hier wird weder eine neue DOI dieses Artikels noch ein frischer externer Readback des historischen Ankers behauptet.

**Fassung:** 1.0, Manuskriptstand 7. September 2026. Autor und Rechteinhaber: Ingolf Lohmann. Lizenz: Creative Commons Namensnennung – Nicht kommerziell – Keine Bearbeitungen 4.0 International (CC BY-NC-ND 4.0), https://creativecommons.org/licenses/by-nc-nd/4.0/ . Kein Peer Review und keine externe Veröffentlichung werden durch die Erstellung dieser Datei behauptet.
