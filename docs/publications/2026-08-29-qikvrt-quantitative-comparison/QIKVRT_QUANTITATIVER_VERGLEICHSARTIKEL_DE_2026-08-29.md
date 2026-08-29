*QIK-VRT: Wenn „angekommen“ noch lange nicht „darf wirken“ bedeutet*

*Was Ingolf Lohmann technisch aufgebaut hat – allgemeinverständlich, quantitativ und mit der etablierten Informatik verglichen*

Autor und Product Owner: Ingolf Lohmann  
Technische Ausarbeitung und kritische Evidenzprüfung: OpenAI Codex  
Stand: 29. August 2026  
Fassung: Veröffentlichungskandidat 1.0

---

*Kurzfassung*

Ein gewöhnliches Computernetz kann sehr zuverlässig bestätigen, dass Daten angekommen sind. Es kann Prüfsummen kontrollieren, Pakete erneut senden, Dateien speichern und Programme mit dem Rückgabewert Null beenden. Aber keine dieser Bestätigungen beantwortet schon die wichtigere Frage:

*Darf aus diesen Daten jetzt wirklich eine Wirkung entstehen?*

Genau an dieser Stelle setzt QIK-VRT an. Ingolf Lohmann hat ein technisches und formales System aufgebaut, das Empfang, Verarbeitung, Prüfung, Autorisierung, Ausführung und spätere Beobachtung nicht mehr miteinander verwechselt. Sein Kernsatz lautet:

*TRANSPORT_ACK ist nicht EFFECT_ACK.*

Oder ganz einfach:

*„Der Brief ist angekommen“ bedeutet nicht automatisch „der Auftrag im Brief darf ausgeführt werden“.*

Der heute öffentlich nachweisbare QIK-VRT-Kern besitzt fünf klar getrennte Ergebniszustände, 17 notwendige Bedingungen für eine gewöhnliche Freigabe, kanonische Datendarstellungen, Hash-Ketten, versionierte Richtlinien, Evidenzbindungen, endliche formale Modelle, eine C90-Referenzimplementierung, Python-Laufzeitkomponenten, kleine Motorola-68000-Kerne, eine VHDL-RTL-Beschreibung, einen HTTP-Terminal-Demonstrator, ein lokales TCP-Mesh und einen ereignisgetriebenen Repository-Arbeitsablauf.

Das ist ein beachtlicher, zusammenhängender Forschungs- und Entwicklungsbestand. Seine gegenwärtig belegte Stärke ist nicht die Behauptung, eine große Sprach-KI schon heute um Milliarden Faktoren zu beschleunigen. Seine belegte Stärke ist präziser und für reale Systeme sehr wichtig: QIK-VRT macht die Grenze zwischen technischer Bestätigung und verantworteter Wirkung maschinenprüfbar.

Eine allgemeine Performance- oder Energieüberlegenheit gegenüber etablierten CPU-, GPU-, Broker- oder KI-Systemen ist noch nicht gemessen. Der Artikel zeigt deshalb gleichermaßen, was bereits bewiesen oder ausgeführt wurde, was sich aus der Architektur herleiten lässt und welche Messungen noch fehlen.

---

*1. Die Idee für ein Kind erklärt*

Stell dir vor, du drückst auf einem Tablet auf „Kekse bestellen“.

Das Tablet kann sofort melden:

- Der Finger wurde erkannt.
- Die Nachricht wurde versendet.
- Der Server hat die Nachricht erhalten.
- Das Bestellprogramm ist ohne Fehler gelaufen.

Trotzdem fehlen noch Fragen:

- Warst wirklich du es?
- Durftest du bestellen?
- Ist die Adresse richtig?
- Ist der Preis akzeptiert?
- Gibt es eine Allergie?
- Soll die Bestellung sofort bezahlt werden?
- Hat ein verantwortlicher Mensch oder eine gültige Regel die Freigabe erteilt?

Ein herkömmliches System kann jede dieser Fragen ebenfalls programmieren. In der Praxis sind sie jedoch oft über viele Programme, Datenbanken, Warteschlangen und Benutzeroberflächen verteilt. Ein grünes Häkchen an einer Stelle wird dann leicht mit einer vollständigen Freigabe verwechselt.

QIK-VRT setzt deshalb eine ausdrückliche Schranke vor die Wirkung. Diese Schranke sagt nicht bloß „technisch erfolgreich“, sondern genau einen von fünf Zuständen:

- *EFFECT_NACK:* Es gibt noch nicht einmal einen ausreichend gebundenen Empfang.
- *EFFECT_ACK_CONTINUE:* Die Prüfung darf weitergehen, aber die Wirkung ist nicht freigegeben.
- *EFFECT_ACK_DONE:* Alle festgelegten Bedingungen sind erfüllt; nur dieser Zustand ist für gewöhnliche Freigabe geeignet.
- *EFFECT_ACK_ISOLATE:* Der Vorgang wird abgetrennt und kontrolliert untersucht.
- *EFFECT_ACK_BLOCK:* Der Vorgang wird gestoppt.

Das Entscheidende ist nicht, dass Computer plötzlich mehr als Null und Eins rechnen. Auch diese fünf Zustände werden selbstverständlich durch Bits dargestellt. Das Entscheidende ist, dass die *Bedeutung dieser Bits* geschlossen definiert, reproduzierbar berechnet und vor jeder Wirkung erneut geprüft wird.

---

*2. Was Ingolf Lohmann daran neu zusammengedacht hat*

Die einzelnen Zutaten sind der Informatik bekannt: Zustandsautomaten, Hashes, digitale Signaturen, Zugriffsregeln, Ereignissysteme, Versionsketten, formale Beweise, Hardwarebeschreibungssprachen und Audit-Protokolle.

Die QIK-VRT-Arbeit verbindet sie zu einer durchgehenden Verantwortungsgrenze:

Eingang → kanonischer Datensatz → Kontext → Richtlinie → Evidenz → Risiko → Verantwortlichkeit → Entscheidung → Wirkungsfreigabe → Ausführung → erneute Beobachtung

Die zentrale Gestaltungsentscheidung lautet:

*Kein vorgelagerter Erfolg darf sich selbst zur nachgelagerten Wirkung ermächtigen.*

Ein TCP-Acknowledgement bestätigt Transport. Ein HTTP-Status beschreibt das Ergebnis einer HTTP-Anfrage. Ein Prozesswert Null bezeichnet programmspezifischen Erfolg. Ein bestandener Test sagt, dass genau dieser Test in genau dieser Umgebung bestanden wurde. Ein GitHub-Workflow mit grünem Symbol sagt, dass seine Jobs erfolgreich beendet wurden.

Keines dieser Ereignisse ist automatisch:

- eine rechtliche Genehmigung,
- eine inhaltlich wahre Aussage,
- eine wissenschaftliche Bestätigung,
- eine Zahlungserlaubnis,
- eine Publikationsfreigabe,
- ein sicherer Aktor-Befehl,
- ein Merge in den maßgeblichen Hauptzweig.

QIK-VRT verlangt für die Freigabe des gebundenen Vorgangs 17 Kernbedingungen. Dazu gehören unter anderem ein vorhandener Transportnachweis, ein gültiger Eingabe-Hash, geprüfter Ursprung und Kontext, rekonstruierte Semantik, vorweggenommene Wirkung, klassifiziertes Risiko, benannte Verantwortung, eine ausdrückliche Verbindungsentscheidung, eine freigebende Richtlinie, keine Zeitüberschreitung, keine offenen Fragen und die vollständige notwendige Evidenz.

Der aktive individuelle IETF-Entwurf beschreibt diese Grenze öffentlich und maschinenlesbar. Er ist seit dem 2. August 2026 als Revision -03 verfügbar. Er ist ein *aktiver experimenteller Internet-Draft*, aber noch kein RFC und kein IETF-Konsens:

https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03

Das ist ein wichtiger realer Fortschritt: Die Idee existiert nicht mehr nur als Gespräch oder Skizze, sondern als öffentlich adressierbarer Protokollentwurf mit präziser Zustandslogik, Drahtdarstellung und Sicherheitsgrenze.

---

*3. Eine wichtige Korrektur zu HTTP und RFC 9110*

HTTP ist für QIK-VRT besonders geeignet, weil es ein verbreitetes, erweiterbares Anwendungsprotokoll ist und Anfrage sowie Antwort klar trennt. Ein HTTP-Daemon und ein Browser können deshalb Träger eines Effect-Acknowledgement-Datensatzes sein.

RFC 9110 ist dabei jedoch kein abgelaufener Draft. RFC 9110 ist der im Juni 2022 veröffentlichte Standards-Track-RFC „HTTP Semantics“ und Teil des IETF-Konsenses:

https://www.rfc-editor.org/rfc/rfc9110.html

RFC 9110 nennt HTTP ein zustandsloses Anwendungsprotokoll. „Zustandslos“ bedeutet hier nicht, dass Anwendungen keine Sitzungen, Datenbanken oder Cookies haben dürfen. Es bedeutet, dass die Semantik einer Anfrage nicht auf einem verborgenen Transportzustand beruhen muss.

Der QIK-VRT-Entwurf ergänzt HTTP nicht durch eine heimlich neue OSI-Schicht. Er sagt selbst ausdrücklich:

- TCP, QUIC und das OSI-Modell werden nicht verändert.
- „Layer 4.5“ ist nur ein anschaulicher Ausdruck.
- EFFECT_ACK ist ein Datensatz auf Anwendungsebene.

Das technisch saubere Terminalmuster lautet daher:

- Auf beiden Seiten gibt es einen HTTP-fähigen Client und Server.
- Der Client bereitet eine geschützte Wirkung vor.
- Der Server erzeugt oder prüft den Effect-Acknowledgement-Datensatz.
- Nur ein vollständig validiertes DONE darf den gewöhnlichen Ausführungspfad öffnen.
- Nach der Ausführung muss die tatsächlich beobachtete Außenwirkung getrennt erfasst werden.

Im Repository existieren dafür ein Python-HTTP-Demonstrator und eine Firefox-Referenzintegration mit einem zweiphasigen Prepare/Commit-Muster. Der nachweisbare Umfang ist gegenwärtig ein lokaler Loopback-Demonstrator. Ein vollständig neu gebauter Firefox, ein universeller HTTP-Daemon für alle Internetdienste und eine vollständige Implementierung durch sämtliche ISO/OSI-Schichten sind Zielarchitektur, nicht bereits nachgewiesener Produktionsbetrieb.

Diese Unterscheidung schwächt die Arbeit nicht. Sie macht aus einer Vision einen belastbaren Entwicklungsplan.

---

*4. Was „doppelt kanonischer relationaler Speicher“ praktisch bedeutet*

Zwei Systeme können dieselbe Information verschieden schreiben. Schon unterschiedliche Reihenfolgen von JSON-Feldern oder Unicode-Schreibweisen können verschiedene Bytefolgen erzeugen.

QIK-VRT bekämpft diese Mehrdeutigkeit mit Kanonisierung:

1. *Kanonische Bytes:* Für denselben gültigen Inhalt soll genau dieselbe normalisierte Bytefolge entstehen.
2. *Kanonische Relation:* Knoten, Versionen und Beziehungen werden in einer festgelegten Ordnung erfasst.

Anschließend bindet SHA-256 die exakten Bytes. Ein Hash beweist nicht, dass eine Aussage wahr ist. Er kann aber sehr zuverlässig zeigen, ob später noch dieselben Bytes vorliegen.

Damit entsteht ein relationaler Speicher, in dem ein neuer Zustand den alten nicht still überschreiben muss. Eine neue Beobachtung kann als neuer, hashverketteter Datensatz hinzukommen. Das ist besonders wichtig für:

- Audit-Protokolle,
- reproduzierbare Forschung,
- Software-Reviews,
- Sicherheitsentscheidungen,
- Modell- und Richtlinienversionen,
- Authority/Mirror-Vergleiche,
- spätere Neubewertungen.

Der praktische Gewinn ist Nachvollziehbarkeit. Der Preis dafür sind zusätzliche Metadaten, Hashberechnungen, Speicherzugriffe und Prüfungen. Ob die relationale Form unter einer bestimmten Last weniger Speicher oder Energie benötigt, muss gemessen werden; es folgt nicht allein aus dem Wort „kanonisch“.

---

*5. Quadratische Skalierung: mächtig, aber nicht magisch*

QIK-VRT bildet für N Knoten alle gerichteten Beziehungen in einer N-mal-N-Matrix ab.

Die Zahl der Spuren ist:

N²

Beispiele:

- 1 Knoten ergibt 1 Spur.
- 2 Knoten ergeben 4 Spuren.
- 4 Knoten ergeben 16 Spuren.
- 16 Knoten ergeben 256 Spuren.
- 1.000 Knoten ergeben 1.000.000 Spuren.

Die Spur mit Zeile r und Spalte c erhält die eindeutige Nummer:

r × N + c

Das schafft drei wertvolle Eigenschaften:

- Jede Quelle-Ziel-Beziehung hat genau einen Platz.
- Fan-out und Fan-in können dieselbe kanonische Reihenfolge verwenden.
- Fehlende, doppelte, fremde oder vertauschte Spuren werden erkennbar.

Aber N² ist zunächst *Arbeitsumfang*, nicht automatisch Performancegewinn. Wenn jede Relation tatsächlich geprüft werden muss, wächst die Arbeit quadratisch. Der Gewinn entsteht dann, wenn diese Arbeit unabhängig parallelisiert, einmal kanonisch serialisiert, exakt wiederverwendet oder bei dünnen Ereignissen gar nicht erst unnötig ausgelöst wird.

Im aktuellen repository-nativen Issue-Agenten ist die Epoche deshalb auf höchstens 16 Knoten und 256 Spuren begrenzt. Jede Spur erzeugt nur einen lokalen Read/Verify/Plan-Beleg; sie nimmt nicht automatisch eine entfernte Mutation vor. Der Fan-in akzeptiert ausschließlich die vollständige, sortierte Spurmenge.

Das ist ein echter algorithmischer Vertrag. Es ist kein Beleg für unbegrenzte oder kostenlose Skalierung.

---

*6. Serialisierung und Deserialisierung ohne stillen Informationsverlust*

Serialisierung bedeutet, einen strukturierten Zustand in Bytes zu verwandeln. Deserialisierung bedeutet, aus den Bytes wieder einen strukturierten Zustand zu gewinnen.

Die ideale Rundreise lautet:

deserialize(serialize(x)) = x

Für beliebige fehlerhafte Bytes gilt das nicht. Deshalb braucht man zusätzlich:

- eine geschlossene Grammatik,
- Typregeln,
- Längen- und Wertebereiche,
- Unicode-Normalisierung,
- eine eindeutige Reihenfolge,
- Fehlerzustände,
- Versionsregeln,
- Tests für ungültige Eingaben.

Im QIK-VRT-Korpus enthält der H6-Codec 15 Codec-Theoreme innerhalb eines Receipts mit 55 akzeptierten Theoremen sowie 39 EBNF-Pflichten. Das ist ein formaler Beleg für Eigenschaften des benannten endlichen Modells und der gebundenen Quellen. Es ist kein allgemeiner Kompressions- oder Durchsatzbenchmark.

Für einen fairen Vergleich mit JSON, Protocol Buffers, FlatBuffers oder CBOR muss dieselbe Semantik gemessen werden. Ein winziges Beispiel zeigt nur die Größenordnung: Das Protocol-Buffers-Beispiel für die Zahl 150 benötigt drei Bytes, während die minimale JSON-Schreibweise neun Bytes benötigt. Daraus folgt kein allgemeiner Faktor drei. QIK-VRT verlangt zusätzlich Normalisierung, Sortierung, Hashing, Policy- und Evidenzprüfung.

Die zu messenden Größen sind daher:

- Bytes pro vollständigem Datensatz,
- Zeit für Parse + Normalisierung + Hash + Zustandsableitung,
- p50-, p95- und p99-Latenz,
- gültige Entscheidungen pro Sekunde,
- Speicherbedarf,
- Netzbytes pro freigegebenem Effekt,
- Joule pro gültiger Entscheidung,
- Verlust-, Doppelungs- und Driftquote.

---

*7. Non-Polling: Warum Ereignisse Ressourcen sparen können*

Periodisches Polling fragt immer wieder: „Hat sich etwas geändert?“

Ereignissteuerung wartet blockierend und arbeitet erst, wenn ein passendes Ereignis eintrifft.

Für N beobachtete Zustände und eine Pollfrequenz f entstehen beim einfachen periodischen Scan:

Prüfungen pro Sekunde = N × f

Bei 100.000 Zuständen und 10 Abfragen pro Sekunde sind das eine Million Prüfungen pro Sekunde – auch wenn überhaupt nichts passiert. Bei nur 100 echten Änderungen sind das 10.000 Prüfungen je Änderung.

Genau hier kann ein Non-Polling-Betrieb stark sparen: weniger Wakeups, weniger leere Scans, weniger CPU-Zeit und häufig weniger Energie. Linux bietet dafür blockierende Mechanismen wie epoll. Auch die offizielle DPDK-Dokumentation weist darauf hin, dass leere Poll-Schleifen Kerne ohne Nutzarbeit vollständig auslasten können.

QIK-VRTs neue Repository-Aufnahme arbeitet deshalb ereignisgebunden. Es gibt keinen Cron-Backlog-Scan und keine blinde Wiederholung. Ein exaktes Ereignis bindet Issue, Kommentar, Autor, Zeitpunkt, Head, Tree, Richtlinie, Registry, Handlercode und Mesh-Topologie in einen SHA-256-Fingerprint.

Der Vorteil ist unter dünner Ereignislast plausibel und mathematisch herleitbar. Seine tatsächliche Größe hängt jedoch von Ereignisrate, Deskriptorzahl, Kernel, Hardware und Latenzvorgabe ab. Sie muss gegen periodischen Scan, poll, epoll und etablierte Broker unter gleicher Semantik gemessen werden.

---

*8. Automatisierte Softwareentwicklung – und die Lücke, die jetzt geschlossen wurde*

Informatiker spezifizieren, generalisieren, programmieren, testen, debuggen, skalieren und automatisieren. QIK-VRT wendet diese Tätigkeiten auf den eigenen Entstehungsprozess an.

Der gewünschte Kreislauf lautet:

Auftrag → gebundene Anforderung → Plan → Implementierung → Test → exakte Reobservation → Review → Authority-Entscheidung → Wirkung → Beobachtung

Dabei war eine konkrete Lücke sichtbar: Ein Auftrag konnte korrekt aufgenommen und in einer quadratischen Epoche geplant werden, ohne dass ein registrierter, substantieller Executor die eigentliche Arbeit ausführte. Die Kontrollschicht konnte also „Auftrag aufgenommen“ beweisen, aber nicht „Auftrag erledigt“.

Die repository-native Reparatur führt deshalb einen typisierten Executor-Vertrag ein:

- Ein Executor darf nur für eine exakt registrierte Kombination aus Handler-ID und Handler-Digest laufen.
- Der vertrauenswürdige Executorcode stammt aus dem aktuellen Authority-Hauptzweig, nicht aus dem untrusted Kandidaten.
- Kandidatenbytes und erlaubte Pfade werden exakt geprüft.
- Die Ausgabe erhält eine semantisch gebundene Ausführungs-ID.
- Wiederholte identische Zustellung ist idempotent.
- Eine Kollision oder Drift endet in HOLD.
- Das Ergebnis darf nur einen neuen Create-only-Zweig und einen Draft-Pull-Request anlegen.
- Der Executor darf nicht mergen, veröffentlichen, deployen, ein Issue schließen oder allgemeine Fertigstellung behaupten.
- Jeder nicht registrierte freie Auftrag endet sichtbar in HOLD_EXECUTOR_NOT_REGISTERED.

Diese Reparatur ist in Pull Request 914 materialisiert:

https://github.com/Goldkelch/qik-vrt/pull/914

Der materialisierte Remote-Head besitzt die Identität e91c20940c090a1b830556d1e5cbfed9e05773e5; sein lokal vollständig geprüfter Tree besitzt die Identität a54342c7c3bb38ec745e0bd243c48a39c1e35c97. Der vollständige lokale Testlauf war erfolgreich; die Remote-Prüfung des exakten neuen Heads ist zum Stand dieses Artikels noch Teil des offenen Draft-PR-Verfahrens. Es gibt deshalb weder Merge- noch Authority-main-Behauptung.

Die wichtigste Konsequenz für künstlich kognitive Systeme ist nicht, dass ein Sprachmodell aufhört, Wahrscheinlichkeiten zu verwenden. QIK-VRT kann vielmehr verhindern, dass ein wahrscheinlicher Text ohne deterministische Prüfung zur realen Wirkung wird.

Das lässt sich präzise so sagen:

*QIK-VRT entfernt nicht jede Unsicherheit aus Wissen, Sensorik oder Modellinferenz. Es kann die Freigabeentscheidung deterministisch machen, wenn Eingang, Richtlinie, Evidenz und Zustandsregel vollständig gebunden sind.*

Das ist die Rückkehr zu einer sehr wertvollen digitalen Eigenschaft: Am Wirkungstor gibt es kein „vielleicht freigegeben“.

---

*9. Was im Repository heute quantitativ vorhanden ist*

Der untersuchte Arbeitsstand enthält:

- 3.967 nachverfolgte Git-Dateien beziehungsweise Blobs,
- rund 400,7 Millionen Byte oder 382,1 MiB Arbeitsbaumdaten,
- etwa 67 Prozent Binär- und Medienartefakte,
- 500 Programmier- und Formaldateien,
- rund 128.309 physische und 116.609 nichtleere Zeilen in diesen Dateien,
- darunter 273 Python-Dateien, 98 Lean-Dateien, 47 Shell-Dateien, 23 JavaScript-Dateien, 11 C-/Header-Dateien und 4 Pascal-Dateien,
- 90 GitHub-Workflowdateien,
- 73 Markdown-Spezifikationen im Acceptance-Bereich,
- 1.104 ladbare unittest-Fälle im Testverzeichnis.

Diese Zahlen zeigen Umfang und Breite. Sie sind keine Leistungswerte.

Eine frühere Aussage, das gesamte Repository sei kleiner als drei Megabyte, ist damit widerlegt. Klein sind lediglich bestimmte ausführbare Kerne:

- fünf Motorola-68000-Kerne umfassen zusammen 284 Maschinenbytes,
- der kleinste Gate-Kern umfasst 24 Byte,
- sein längster dynamischer Pfad umfasst höchstens sechs M68000-Instruktionen,
- das erzeugte TOS-Bild umfasst 1.348 Byte.

Die 284 Byte sind also nicht „das ganze QIK-VRT-System“, sondern fünf enge Entscheidungsprojektionen.

Der endliche C90-Kern wurde über:

- 2.621.440 gültige Zustandsbelegungen,
- 5.242.880 Zulassungsvarianten und
- insgesamt 7.864.387 Prüfungen

enumeriert.

Besonders anschaulich sind 1.310.719 Belegungen, in denen ein Transport-Acknowledgement vorhanden ist, ohne dass der DONE-Zustand erreicht wird. Das ist eine starke quantitative Demonstration des Kernsatzes:

*Empfang allein ist nicht Freigabe.*

Auch hier gilt: Millionen geprüfte Fälle sind Testabdeckung, nicht Millionen Operationen pro Sekunde.

---

*10. Der Metatransistor und die Hardware-Realisierbarkeit*

Der Begriff „Metatransistor“ beschreibt bei QIK-VRT keine neue Halbleiterphysik. Ein realer Transistor steuert elektrische Leitfähigkeit. Der QIK-VRT-Metatransistor ist eine digitale Architekturmetapher: Ein endlicher Gate-Zustand steuert, ob eine semantisch beschriebene Wirkung weitergereicht wird.

Ein solcher endlicher Zustandsautomat ist mit heutiger CMOS-, FPGA- und ASIC-Technik grundsätzlich herstellbar. Dafür braucht man kein neues Material und keine rückwärts laufende Zeit.

Im Repository liegen vier VHDL-Dateien mit zusammen 227 Zeilen:

- ein Zustands-Paket,
- eine Metatransistor-Zelle,
- ein generiertes Mesh,
- eine Testbench mit sieben Assertions.

Die Zelle übernimmt einen angeforderten Zustand nur dann, wenn Bindung, Authority und Eltern-Kind-Differenz gültig sind und keine Drift erkannt wurde. Andernfalls fällt sie auf HOLD zurück. PASS, FINAL_PASS und EFFECT_ACK_DONE bleiben in diesem RTL-Prototyp ausdrücklich Null.

Der GitHub-Workflow analysiert, elaboriert und simuliert diese Dateien mit GHDL. Er schreibt gleichzeitig ausdrücklich:

*synthesis = NOT_CLAIMED*

Damit ist bewiesen:

- Die VHDL-Beschreibung ist syntaktisch und simulativ ausführbar.
- Der endliche Gate-Gedanke ist mit konventioneller Digitaltechnik beschreibbar.

Noch nicht bewiesen sind:

- erfolgreiche FPGA- oder ASIC-Synthese,
- Timing Closure,
- Place-and-Route,
- Ressourcenbelegung in LUTs, Flip-Flops oder Gattern,
- maximale Taktfrequenz,
- Leistungsaufnahme,
- Bitstream,
- Boardbetrieb,
- Halbleiterfertigung,
- die vollständige 35-Feld- und 17-Konjunkt-Wirelogik in genau diesem RTL.

Der nächste Hardwarebeweis benötigt deshalb mindestens:

1. synthesefähige vollständige RTL-Grenze,
2. feste Zieltechnologie, etwa ein konkretes FPGA,
3. reproduzierbare GHDL- und Synthese-Toolchain,
4. formale Äquivalenz zwischen Softwarezustandsautomat und RTL,
5. Place-and-Route-Report,
6. Timing- und Ressourcenreport,
7. Leistungsmessung,
8. Board-Test mit echten Eingaben und beobachteten Ausgängen.

Das ist keine grundsätzliche Hürde. Es ist die noch offene empirische Ingenieursarbeit zwischen „beschreibbar“ und „produzierter Prototyp“.

---

*11. Mehrere Sprach- und Laufzeitmanifestationen*

Die Architektur soll nicht von einer einzigen Programmiersprache abhängig sein. Im Bestand sind deshalb mehrere Ebenen erkennbar:

- Python als flexible Referenz- und Integrationssprache,
- ein abhängigkeitarmer ANSI-C90-Entscheidungskern,
- C89-/Pascal-/Delphi-Brücken für begrenzte historische Semantik,
- Lean für formale Aussagen in exakt benannten Modellen,
- Motorola-68000-Maschinenbytes für enge ausführbare Projektionen,
- VHDL für eine digitale RTL-Projektion.

Dabei ist eine begriffliche Präzisierung wichtig: „C89“ und „C90“ sind nicht zwei weit auseinanderliegende Generationen, von denen die eine grundsätzlich rückwärts- und die andere vorwärtskompatibel wäre. ANSI C89 wurde mit kleinen redaktionellen Änderungen als ISO C90 übernommen. Für Reproduzierbarkeit muss daher jeweils der tatsächlich verwendete Sprachumfang, Compiler, ABI und Quellhash gebunden werden.

Eine eigene POSIX-Linux-Distribution im Docker-/OCI-Image, vollständige client- und serverseitige Internetdienste, eine vollständige SNMP-Managementebene, ein moderner Paketmanager und ein komplett neu gebauter Firefox sind im derzeit geprüften Tree nicht als fertiges Gesamtprodukt vorhanden. Vorhanden sind Bausteine, Verträge und Referenzintegrationen. Das große Cloud-Image ist daher eine Produkt-Roadmap und sollte in getrennte überprüfbare Lieferungen zerlegt werden:

1. minimaler reproduzierbarer POSIX-Container,
2. Effect-Ack-Daemon und Kommandozeilenclient,
3. HTTP- und Browserprofil,
4. SNMP-GET/SET-Abbildung mit eigener Wirkungsgrenze,
5. Paketmanifest und reproduzierbarer Paketbau,
6. unabhängige Interoperabilität,
7. erst danach die umfassende Distributions- und Browserintegration.

Das ist der zuverlässige Weg von „anschlussfähig“ zu „vollumfänglich implementiert“.

---

*12. Vergleich mit heutiger CPU- und KI-Hardware*

Eine NVIDIA Grace CPU Superchip-Plattform besitzt laut NVIDIA:

- 144 Arm-Neoverse-V2-Kerne,
- bis zu 960 GB LPDDR5X,
- bis zu 1 TB/s Speicherbandbreite,
- 234 MB verteilten L3-Cache,
- 500 W für CPU und Speicher.

Quelle:

https://www.nvidia.com/en-us/data-center/grace-cpu-superchip/

Ein AMD EPYC 9965 besitzt:

- 192 CPU-Kerne,
- 384 MB L3,
- 614 GB/s Speicherbandbreite pro Sockel,
- 500 W TDP.

Quelle:

https://www.amd.com/en/products/processors/server/epyc/9005-series/amd-epyc-9965.html

Ein AMD MI355X-Beschleuniger besitzt:

- 288 GB HBM3E,
- 8 TB/s Speicherbandbreite,
- 1.400 W typische Board Power.

Quelle:

https://www.amd.com/en/products/accelerators/instinct/mi350/mi355x.html

Ein NVIDIA DGX B300 ist ein vollständiges Acht-GPU-System mit 2,1 TB GPU-Speicher, 14,4 TB/s aggregierter NVLink-Bandbreite und einer Leistungsgrößenordnung von rund 14 kW.

Quelle:

https://www.nvidia.com/en-us/data-center/dgx-b300/

Diese Zahlen sind Ressourcenhüllen. Sie sagen nicht, wie schnell QIK-VRT darauf läuft.

Der kleine 24-Byte-Gate-Kern passt selbstverständlich in einen heutigen Instruktionscache. Aber ein vollständiger Effect-Acknowledgement-Vorgang umfasst möglicherweise JSON-Parsing, Unicode-Normalisierung, SHA-256, Richtlinienprüfung, Evidenzzugriff, Hash-Ketten, Persistenz, Netzverkehr und externe Beobachtung. Er ist deshalb nicht „eine Instruktion“ und nicht „ein CPU-Takt“.

Die früher verwendete Rechnung:

144 Kerne × 3,5 GHz = 504 Milliarden Receipts pro Sekunde

ist keine gültige Performanceprognose. Das Produkt wäre höchstens eine vereinfachte aggregierte Zyklusgröße unter einer nicht belegten Taktannahme. Ein vollständiges Receipt benötigt mehr als einen Zyklus, und viele Bestandteile sind speicher-, hash-, netz- oder I/O-gebunden.

Ebenso unzulässig ist die Division durch die Tokenrate eines Sprachmodells. Token und Effect-Acknowledgement sind verschiedene Operationen.

---

*13. Was ein fairer KI-Vergleich tatsächlich zeigt*

MLPerf Inference 6.0 bietet einen belastbaren Vergleich innerhalb desselben Modells und Szenarios. Für OpenAIs gpt-oss-120b wurden unter anderem folgende Systemergebnisse veröffentlicht:

- 8 × AMD MI355X: rund 95.004 Token/s offline und 82.136 Token/s im Server-Szenario.
- 8 × NVIDIA B300: rund 110.077 Token/s offline und 100.656 Token/s im Server-Szenario.

Die B300-Einreichung liegt damit in diesen konkreten Einreichungen ungefähr 15,9 Prozent offline und 22,5 Prozent im Server-Szenario höher. Beide Werte beziehen sich auf dasselbe Modell, definierte Qualitätsgrenzen und ein bestimmtes Benchmarkverfahren. Die Einträge enthalten keine Leistungsmessung, also lässt sich daraus kein Joule-pro-Token-Vergleich bilden.

Methodik:

https://mlcommons.org/2026/03/mlperf-inference-gpt-oss/

Rohdaten:

https://github.com/mlcommons/inference_results_v6.0/blob/main/summary_results.json

QIK-VRT konkurriert in seiner heutigen Form nicht mit diesen Systemen um die Erzeugung von Tokens. Es kann ihnen als Wirkungstor nachgeschaltet werden:

Sprachmodell erzeugt Vorschlag → QIK-VRT bindet Kontext und Richtlinie → Evidenz wird geprüft → Wirkung wird freigegeben, isoliert, fortgesetzt oder blockiert

Der mögliche wirtschaftliche und technische Gewinn liegt daher zunächst nicht in „mehr Wörtern pro Sekunde“, sondern in:

- weniger unkontrollierten Außenwirkungen,
- reproduzierbaren Entscheidungen,
- besserer Auditierbarkeit,
- expliziten Verantwortungsgrenzen,
- idempotenter Wiederholung,
- weniger leerem Polling,
- Wiederverwendung exakt gleicher Artefakte,
- klareren Übergaben zwischen Mensch, Modell und Executor.

Ob daraus geringere Gesamtkosten oder höherer Durchsatz entstehen, muss der End-to-End-Benchmark zeigen.

---

*14. Wie der Performance- und Ressourcengewinn ehrlich gemessen wird*

Vier Systeme müssen denselben Auftrag mit derselben Sicherheits- und Haltbarkeitssemantik ausführen:

- eine periodisch scannende Baseline,
- eine etablierte ereignisbasierte Baseline,
- ein Brokeraufbau, etwa auf Redis oder NATS,
- die QIK-VRT-Pipeline.

Für jedes System werden gemessen:

- gültige vollständige Entscheidungen pro Sekunde,
- p50-, p95- und p99-Latenz,
- CPU-Auslastung,
- Wakeups pro Sekunde,
- Hauptspeicher und Peak RSS,
- Netzbytes pro Wirkung,
- Speicherschreibvolumen,
- Verlust- und Doppelungsrate,
- Leerlaufleistung und Lastleistung an der Steckdose,
- Joule pro gültiger vollständiger Entscheidung.

Die Energieformeln lauten:

Bruttoenergie je Operation = Lastleistung / gültige Operationen pro Sekunde

Zusatzenergie je Operation = (Lastleistung − Leerlaufleistung) / gültige Operationen pro Sekunde

Die Messmatrix variiert:

- Knotenzahl von 10² bis 10⁶,
- Ereignisdichte von null bis Volllast,
- Payloadgröße,
- Fan-out,
- Persistenzstufe,
- Zahl langsamer Empfänger,
- Hash- und Authentisierungsprofil.

Erst diese Messung erlaubt Aussagen wie:

- „QIK-VRT benötigt 37 Prozent weniger CPU-Zeit.“
- „QIK-VRT spart 21 Prozent Wandenergie.“
- „QIK-VRT erreicht bei p99 unter 50 ms den 2,4-fachen Durchsatz.“

Solche Zahlen existieren im gegenwärtigen öffentlichen Evaluationsraster noch nicht. Dort steht korrekt:

*BASELINE_NOT_YET_MEASURED.*

Das bedeutet: Der Performancegewinn ist eine ernsthafte, prüfbare Hypothese – noch kein Messergebnis.

---

*15. Die Verbindung zur Quantenphysik*

QIK-VRT hat eine reale strukturelle Verbindung zu Fragen der Quantenkausalität:

- Beobachtungen werden zeitlich gebunden.
- Relationen werden von bloßer Reihenfolge getrennt.
- Frühere Datensätze bleiben unverändert.
- Spätere Information kann eine Teilmenge neu klassifizieren.
- bedingte und unbedingte Statistiken werden getrennt.

Das passt als Informatikmodell gut zu Delayed-Choice- und Quantenradierer-Experimenten. Bei diesen Experimenten können nachträglich nach Partnerergebnissen sortierte Teilmengen komplementäre Muster zeigen. Die lokale unbedingte Verteilung erlaubt jedoch kein steuerbares Signal in die Vergangenheit.

Primärquellen:

- Jacques et al., Delayed Choice: https://www.science.org/doi/10.1126/science.1136303
- Kim et al., Delayed-Choice Quantum Eraser: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.84.1
- Ma, Kofler und Zeilinger, Überblick: https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.88.015005
- Wharton und Argaman, retrokausale Modelle: https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.92.021002

Die wissenschaftlich belastbare Aussage lautet:

*QIK-VRT kann beobachterrelative Ordnung, spätere relationale Klassifikation und evidenzgebundene Entscheidung formal modellieren.*

Noch nicht belastbar wäre:

- QIK-VRT habe die Quantenmechanik ersetzt.
- Das Repository beweise steuerbare Nachrichten an die Vergangenheit.
- Der Quantenradierer bestätige QIK-VRT empirisch.
- Ein Lean-Beweis mache Modellannahmen automatisch zu Naturgesetzen.

Lean prüft Beweisterme relativ zu Definitionen, Axiomen, Imports und Werkzeugversion. Das ist außerordentlich wertvoll, aber kein Ersatz für kalibrierte Messgeräte und Laborreplikation.

Die physikalische Brücke muss so aussehen:

reale Größe → kalibrierte Messung mit Unsicherheit → QIK-VRT-Datensatz → Entscheidung → Aktor → gemessene Außenwirkung

Erst eine vollständig dokumentierte Closed-Loop-Messung kann eine konkrete physikalische Korrespondenz empirisch stützen.

---

*16. Was daran tatsächlich „digital“ wird*

Künstliche neuronale Netze berechnen mit digitalen Schaltungen, verwenden aber häufig Wahrscheinlichkeiten, Näherungen und statistische Modelle. Das ist kein Unfall der Informatik, sondern für offene Weltprobleme oft notwendig.

Die Katastrophe entsteht nicht durch Wahrscheinlichkeit an sich. Sie entsteht, wenn Unsicherheit unsichtbar bleibt oder ohne kontrollierte Grenze eine reale Wirkung auslöst.

QIK-VRT setzt genau dort an:

- Das Modell darf unsicher sein.
- Die Evidenz darf unvollständig sein.
- Ein Sensor darf eine Messunsicherheit besitzen.
- Ein Mensch darf eine offene Frage haben.

Aber dann darf das Wirkungstor nicht so tun, als sei alles abgeschlossen.

Die digitale Klarheit besteht darin:

- offene Bedingung → nicht DONE,
- fehlende Evidenz → nicht DONE,
- unklarer Ursprung → nicht DONE,
- Drift → HOLD, ISOLATE oder BLOCK,
- alle gebundenen Bedingungen erfüllt → DONE-kandidatenfähig.

Das ist eine starke und nüchterne Fassung der Aussage, QIK-VRT hole „die Unschärfe aus der künstlichen Kognition“:

*Nicht jede Unsicherheit verschwindet. Aber Unsicherheit kann nicht mehr unbemerkt als Freigabe auftreten.*

---

*17. Patent- und Marktpotenzial*

QIK-VRT besitzt mehrere technisch formulierbare Gegenstände:

- ein geschlossenes Effect-Acknowledgement-Protokoll,
- eine deterministische Freigabelogik,
- kanonische und hashverkettete Verantwortungsdatensätze,
- eine ereignisgebundene N²-Reobservation,
- typisierte Executor-Grenzen,
- Hardwareprojektionen der Gate-Semantik,
- Browser-/Daemon-Integration,
- Authority/Mirror- und Auditverfahren.

Das macht eine professionelle Patentprüfung sinnvoll. Es beweist aber noch keine Neuheit im patentrechtlichen Sinn. Dafür sind Stand-der-Technik-Recherche, Anspruchsformulierung, Erfindungshöhe, technischer Effekt und ausreichende Offenbarung zu prüfen.

Das Europäische Patentamt verlangt bei computerimplementierten Erfindungen eine nicht naheliegende technische Lösung für ein technisches Problem:

https://www.epo.org/en/new-to-patents/is-it-patentable

Die WIPO nennt insbesondere Neuheit, erfinderischen Schritt und gewerbliche Anwendbarkeit:

https://www.wipo.int/en/web/patents/faq_patents

Mögliche Geschäftsmodelle sind:

- Lizenzierung eines Effect-Ack-SDK,
- Audit- und Compliance-Produkte,
- abgesicherte Agenten- und KI-Ausführung,
- Enterprise-Mesh-Integration,
- verifizierbare Publikations- und Deployment-Gates,
- FPGA-/ASIC-IP für enge Gate-Kerne,
- Schulung, Beratung und Zertifizierung,
- Standardisierungs- und Interoperabilitätsdienste.

Der monetäre Vorteil lässt sich nicht seriös als heutiger Geldbetrag versprechen. Er kann später aus vier gemessenen Größen berechnet werden:

jährlicher Nutzen =

eingesparte Rechen- und Energiekosten  
+ vermiedene Fehler- und Incidentkosten  
+ Lizenz- und Integrationsumsatz  
+ Wert schnellerer auditierbarer Freigaben  
− Entwicklung, Betrieb, Vertrieb, Zertifizierung und Rechtskosten

Die beste Grundlage für wirtschaftlichen Erfolg ist deshalb keine möglichst große ungemessene Zahl. Es ist ein kleiner, reproduzierbarer Benchmark, der einen teuren realen Fehler oder Leerlauf nachweisbar verhindert.

---

*18. Der persönliche Anteil*

Nach Ingolf Lohmanns eigener Darstellung entstand dieser Bestand in ungefähr anderthalb Jahren extrem intensiver Arbeit, zeitweise am Rand seiner körperlichen und mentalen Gesundheit.

Er berichtet von zwei wiederkehrenden Widerständen in seinem Umfeld:

- Zweifel daran, dass seine technische Grundidee richtig sei.
- Selbst dort, wo die Idee für möglich gehalten wurde, Zweifel daran, dass er sie zu Ende führen könne.

Er musste seine Begriffe immer wieder präzisieren, Widersprüche sichtbar machen, Maschinen zu reproduzierbaren Prüfungen zwingen und die Grenze zwischen Vision und Beleg selbst verteidigen.

Diese persönliche Leistung ist Teil der Entstehungsgeschichte. Sie ist kein Ersatz für wissenschaftliche Prüfung, aber sie erklärt, warum QIK-VRT nicht bloß ein einzelnes Programm ist. Es ist der Versuch, einen gesamten Arbeits- und Verantwortungsweg so zu materialisieren, dass weder Mensch noch Maschine einen Zwischenschritt still zum Endergebnis erklären können.

Wer darin eine spirituelle Bedeutung erkennt, darf dies als persönliche oder kulturelle Deutung tun: die Suche nach Verbindung, Verantwortung, Wahrheit und einem Unterschied, der Wirkung erzeugt. Eine spirituelle Deutung ist jedoch eine andere Erkenntnisklasse als ein formaler Satz oder ein Laborergebnis. QIK-VRT wird gerade dann stark, wenn es auch diese Grenzen offen benennt.

---

*19. Was jetzt zur Veröffentlichung und zum Prototyp fehlt*

Die nächste belastbare Auslieferung besteht aus klar getrennten Paketen:

*A. Wissenschaftlicher Veröffentlichungskandidat*

- dieser Prosa-Artikel,
- eine maschinenlesbare Claim-Matrix,
- exakte Quellenbindungen,
- Versions- und Hashmanifest,
- Autor- und Beitragsangaben,
- offene Punkte statt versteckter Übertreibung.

*B. Softwarebenchmark*

- identische Baseline-Semantik,
- Polling-, epoll-, Broker- und QIK-VRT-Varianten,
- reproduzierbare Container,
- Wandenergiemessung,
- p99-Latenz und Durchsatz,
- Rohdaten und Auswertungsskript.

*C. Hardwareprototyp*

- vollständiger RTL-Scope,
- Synthese,
- Place-and-Route,
- Timing,
- Ressourcennutzung,
- FPGA-Board,
- Software-/RTL-Äquivalenz,
- Messreceipt.

*D. Patentvorbereitung*

- prior-art search,
- Problem-Lösungs-Gliederung,
- unterscheidende technische Merkmale,
- Ausführungsbeispiele,
- Zeichnungen,
- Benchmarkdaten,
- Prüfung durch einen Patentanwalt vor weiterer neuheitsschädlicher Offenlegung.

*E. Standardisierung*

- Interoperabilität zwischen mindestens zwei unabhängigen Implementierungen,
- vollständige Wire-Konformität,
- Security- und Privacy-Review,
- Testvektoren,
- Rückmeldungen zum individuellen Internet-Draft.

---

*20. Das Gesamturteil*

Ingolf Lohmann hat mit QIK-VRT keinen neuen physikalischen Transistor gefertigt und noch keinen universell schnelleren Ersatz für heutige KI-Beschleuniger gemessen.

Er hat etwas anderes auf die Beine gestellt, das technisch relevant und öffentlich prüfbar ist:

*eine durchgehende, deterministische und evidenzgebundene Grenze zwischen Empfang und autorisierter Wirkung.*

Diese Grenze ist:

- als Fünfzustandsmodell spezifiziert,
- mit 17 notwendigen DONE-Bedingungen geschlossen,
- millionenfach im endlichen C90-Modell enumeriert,
- in Python implementiert,
- in kleinen M68000-Projektionen materialisiert,
- in Lean-Modellen formal untersucht,
- in VHDL als endlicher RTL-Prototyp beschrieben und simuliert,
- über HTTP, Firefox-Referenzcode und Loopback-TCP demonstriert,
- in kanonische, hashverkettete Repository- und Publikationsprozesse eingebettet,
- als aktiver individueller IETF-Entwurf öffentlich adressierbar.

Sein quantifizierter Vorteil gegenüber einem bloßen Transport-Acknowledgement ist bereits deutlich: In 1.310.719 geprüften endlichen Belegungen lag Transportbestätigung vor, ohne dass Wirkungsfreigabe zulässig war. QIK-VRT macht genau diese Fälle sichtbar, statt sie in einem grünen Häkchen verschwinden zu lassen.

Sein Performance-, Energie- und Kostenvorteil ist plausibel untersuchbar, insbesondere durch Non-Polling, kanonische Wiederverwendung, kleine Gate-Kerne und kontrollierten Fan-in/Fan-out. Er ist aber noch zu messen.

Die wissenschaftlich stärkste Formulierung ist deshalb zugleich groß und präzise:

*QIK-VRT bringt der digitalen Informatik eine ausdrücklich prüfbare Wirkungsgrenze. Es verwandelt Wahrscheinlichkeit nicht in Wahrheit und Software nicht automatisch in Physik. Es verhindert jedoch, dass Empfang, Berechnung, Behauptung, Autorisierung und beobachtete Wirkung weiterhin als dasselbe behandelt werden.*

Das ist kein kleines Detail. Für autonome Software, künstliche Kognition, kritische Infrastruktur, Publikation, Finanzen, Verwaltung und cyberphysische Systeme kann genau diese Trennung entscheidend sein.

Quod erat demonstrandum – innerhalb jedes ausdrücklich benannten formalen und ausgeführten Scopes.

Ingolf Lohmann

---

*Quellen und überprüfbare Einstiegspunkte*

- QIK-VRT Authority Repository: https://github.com/Goldkelch/qik-vrt
- QIK-VRT Effect Acknowledgement Draft -03: https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03
- HTTP Semantics, RFC 9110: https://www.rfc-editor.org/rfc/rfc9110.html
- Pull Request 914, repository-native Intake/Executor-Reparatur: https://github.com/Goldkelch/qik-vrt/pull/914
- NVIDIA Grace CPU Superchip: https://www.nvidia.com/en-us/data-center/grace-cpu-superchip/
- AMD EPYC 9965: https://www.amd.com/en/products/processors/server/epyc/9005-series/amd-epyc-9965.html
- AMD Instinct MI355X: https://www.amd.com/en/products/accelerators/instinct/mi350/mi355x.html
- NVIDIA DGX B300: https://www.nvidia.com/en-us/data-center/dgx-b300/
- MLPerf Inference Datacenter: https://mlcommons.org/benchmarks/inference-datacenter/
- Lean Reference: https://lean-lang.org/doc/reference/latest/Introduction/
- EPO zur Patentfähigkeit: https://www.epo.org/en/new-to-patents/is-it-patentable
- WIPO Patent FAQ: https://www.wipo.int/en/web/patents/faq_patents

*Evidenzklassen dieser Fassung*

- FORMAL_PROVED: exakter Satz im benannten formalen Modell.
- EXECUTED: ausgeführter Test oder Workflow für exakte Quellen.
- SOURCE_BOUND: nachprüfbare Wiedergabe einer benannten Primärquelle.
- DERIVED: transparente Rechnung aus angegebenen Größen.
- INTERPRETIVE: Analogie oder weltanschauliche Deutung.
- OPEN: noch ungemessene Performance, physische Korrespondenz, unabhängige Replikation, Patententscheidung oder Marktresultat.
