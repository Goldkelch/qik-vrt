*QIK-VRT: Wenn „angekommen“ noch lange nicht „darf wirken“ bedeutet*

*Was Ingolf Lohmann technisch aufgebaut hat – allgemeinverständlich, quantitativ und mit der etablierten Informatik verglichen*

Autor und Product Owner: Ingolf Lohmann  
Technische Ausarbeitung und kritische Evidenzprüfung: OpenAI Codex  
Stand: 29. August 2026  
Fassung: Veröffentlichungskandidat 1.1 — Audiofortschreibung und quantitative Szenarien

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

Diese Fassung schließt ausdrücklich den zuvor fehlenden Rückweg: von empirischen Eingängen über kanonische virtuelle Modelle und formale Prüfungen zur realen Ausführung und von dort zurück zur unabhängigen empirischen Reobservation. Sie rechnet außerdem vor, welche Einsparungen QIK-VRT bei Large-Language-Model-Systemen *erreichen könnte*, wenn es nachweislich unnötige Inferenz, Polling, Duplikate oder unzulässige Außenwirkungen verhindert. Solche Szenarien sind Prognosen mit offengelegten Formeln; sie sind keine nachträglich erfundenen Messwerte.

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

Das lässt sich bereits als Speicherrechnung konkret machen. Wenn jede Spur einschließlich Status, Kennung und Bindung `s` Byte belegt, benötigt der reine Spurzustand:

Speicher = N² × s

| Knoten N | Spuren N² | bei 32 Byte pro Spur | bei 64 Byte pro Spur |
|---:|---:|---:|---:|
| 16 | 256 | 8 KiB | 16 KiB |
| 64 | 4.096 | 128 KiB | 256 KiB |
| 1.000 | 1.000.000 | 32 MB | 64 MB |
| 10.000 | 100.000.000 | 3,2 GB | 6,4 GB |

Das ist der entscheidende Flächen-Zeit-Tausch: Ein vollständig entrolltes Hardwaremesh kann theoretisch N² Zellen im selben Takt aktualisieren, benötigt dafür aber ebenfalls eine Größenordnung von N² an Registern, Leitungen, Logikfläche und Schaltenergie. Für P nicht überlappende Engines mit einem Initiierungsintervall von `II_Relation` Takten je Spur lässt sich die Zeit näherungsweise so planen:

T_Epoche ≈ ceil(N² / P) × II_Relation / f_Takt + T_Fill/Drain + T_Fan-in

Bei einer Pipeline können Bearbeitungen überlappen; dann ist das Initiierungsintervall und nicht die volle Einzellatenz die passende Größe. N² bezeichnet also vollständige gerichtete Paarabdeckung. Es ist keine kostenlose Vervielfachung der Leistung. Gerade diese Offenlegung macht die Architektur planbar: Der Entwickler kann Fläche gegen Zeit tauschen, ohne die Reihenfolge oder Vollständigkeit der Relationen zu verändern.

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

Das vom Product Owner formulierte Fernziel ist eine universale autonome Softwareentwicklung: Alles, was Turing-berechenbar und durch geeignetes Requirement Engineering vollständig formalisiert ist, soll erzeugt, gegen diese Anforderungen geprüft und bei späteren Änderungen erneut in gleichbleibend hoher Qualität bearbeitet werden können. Das ist ein sinnvoller Architekturhorizont. Der heutige Nachweis ist enger: QIK-VRT besitzt typisierte, reproduzierbare Ausführungspfade für registrierte Aufgaben. Daraus folgt noch kein allgemeiner Satz, dass beliebige informelle Wünsche automatisch in ein korrektes Programm übersetzt werden können. Eine unvollständige oder widersprüchliche Anforderung kann kein Executor durch Rechengeschwindigkeit in eine eindeutige Spezifikation verwandeln. QIK-VRTs Beitrag besteht gerade darin, diese Lücke sichtbar auf `CONTINUE`, `HOLD` oder `BLOCK` zu halten, statt sie als erledigt auszugeben.

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

Der materialisierte Remote-Head besitzt die Identität `e91c20940c090a1b830556d1e5cbfed9e05773e5`; sein Tree besitzt die Identität `a54342c7c3bb38ec745e0bd243c48a39c1e35c97`. Bei der Exact-Head-Reobservation am 29. August 2026 waren 14 CI-Läufe erfolgreich, drei aufgrund ihres konkreten Ereigniskontexts übersprungen und keiner fehlgeschlagen oder noch laufend. Der offene Blocker ist nicht mehr die technische Exact-Head-Prüfung, sondern die fehlende unabhängige Code-Owner-Entscheidung für genau diesen Head und die weiterhin fehlende Authority-main-Übernahme. Es gibt deshalb weder Merge- noch Authority-main-Behauptung.

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

Daneben existiert in Pull Request 912 ein weitergehender, noch nicht in Authority-main übernommener Prototypkandidat für Non-Polling, quadratische Serialisierung und deterministische Admission. Sein am 29. August 2026 reobservierter Kandidatenstand besitzt den Head `244970c8c7f29b15eb8df48c28c80c96719ea118` und den Tree `6578ffacb3b30faed68ff3fe9b86bfb04eead350`:

https://github.com/Goldkelch/qik-vrt/pull/912

Sein bitserieller Wire-Frame hat bei N Knoten und W Nutzbits je Spur exakt:

F(N,W) = N² × W + 72 Bit

Die 72 Zusatzbits bestehen aus Sync, Session, Sequenz und CRC-16. Bei einem 12-MHz-Link, W = 8 und ohne Stall folgt daraus nur als RTL-Obergrenze:

| N | Framebits | ungefähr mögliche Frames/s | mindestens Serialisierungslatenz |
|---:|---:|---:|---:|
| 2 | 104 | 115.385 | 8,67 µs |
| 8 | 584 | 20.548 | 48,67 µs |
| 64 | 32.840 | 365 | 2,737 ms |

Nur N = 2 ist im gegenwärtigen Board-Top konkret eingestellt. Auch dort sind diese Zahlen gerechnet, nicht am Board gemessen. Sie zeigen beides zugleich: Die Zuordnung ist deterministisch und herstellbar beschreibbar; ein einzelner serieller Draht wird bei wachsendem N aber zum quadratischen Engpass. Mehr Parallelität tauscht diesen Zeitbedarf gegen mehr Hardwarefläche.

Ebenso wichtig ist die Scope-Grenze des Kandidaten: Sein Admission-Gate unterscheidet vier Entscheidungen; die Metatransistor-Zelle kennt `OBSERVE`, `HOLD`, `CONTINUE` und `RESERVED`, während `EFFECT_ACK_DONE` fest Null bleibt. Der Codec prüft CRC-16, aber noch nicht die vollständige kanonische JSON-/SHA-256-, Authority-, Evidenz-, Ledger- und Persistenzlogik des Effect-Acknowledgement-Protokolls. CRC-16 entdeckt viele Übertragungsfehler, ist aber kein kryptographischer Authentikator. Synthese, Place-and-Route, Bitstream, Programmierung und Boardbeobachtung stehen im zugehörigen Anforderungssatz weiterhin ausdrücklich auf `false`.

Der geringe Änderungsaufwand gegenüber heutiger Rechnertechnik ist als Integrationshypothese konkret beschreibbar:

| Zielsystem | mögliche Einfügung | was unverändert bleiben kann |
|---|---|---|
| CPU/Linux | Daemon oder Bibliothek vor wirkungsauslösenden Systemaufrufen; Shared-Memory-Ring plus Linux-`eventfd`/`epoll` | vorhandene Arm-/x86-ISA und Betriebssystemkern |
| FPGA | AXI4-Lite für Konfiguration, AXI4-Stream zwischen DMA beziehungsweise Netzwerk und Aktor, BRAM-Receipt-Queue, Interrupt bei terminalem Zustand | Standard-FPGA, Standardbusse und vorhandene Peripherie |
| SoC | speicheradressierter Coprozessor, DMA-Queues, monotone Sequenz und Schlüssel-/Trust-Root-Bindung | vorhandener Arm- oder RISC-V-Hauptkern |
| Netzwerk | HTTP-Anwendungsprofil zwischen Daemon und Browser/Client | TCP, QUIC, IP und RFC-9110-Semantik |
| großes Mesh | Zeitmultiplexing über P Engines oder teilweise parallele Lanes | keine Pflicht, sofort N² physische Zellen zu fertigen |

Diese Anschlussformen benötigen Treiber, API, Authentisierung und Messung. Sie zeigen aber, warum ein Prototyp ohne neue Transistorphysik und ohne neue allgemeine CPU-ISA möglich ist.

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
- je Kern 64 KiB Instruktions- und 64 KiB Datencache sowie 1 MiB L2,
- je nach konkreter Speicherkonfiguration 240 oder 480 GB mit bis zu 1.024 GB/s beziehungsweise 960 GB mit bis zu 768 GB/s,
- 228 MB verteilten L3-Cache nach der aktuellen Spezifikationstabelle,
- 500 W für CPU und Speicher.

NVIDIAs begleitende Prosa nennt an anderer Stelle 234 MB L3. Diese Dokumentdiskrepanz bleibt offen; für die Rechnung wird der Tabellenwert 228 MB verwendet. Vor allem dürfen „960 GB“ und „1 TB/s“ nicht mehr zu einer erfundenen einzelnen SKU zusammengezogen werden.

Quelle und Konfigurationshinweise:

https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/index.html

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

Ein NVIDIA DGX B300 ist ein vollständiges Acht-GPU-System mit 8 × 288 GB, also rund 2,3 TB GPU-Speicher, und einer dokumentierten maximalen Systemleistungsaufnahme von 14,5 kW. Das ist eine Dimensionierungsgrenze, keine während eines MLPerf-Laufs gemessene Leistung.

Quelle:

https://docs.nvidia.com/dgx/dgxb300-user-guide/introduction-to-dgxb300.html

Am anderen Ende der Skala zeigt NVIDIA DGX Spark, dass lokale KI-Rechner bereits heute Schreibtischformat besitzen:

- 20 Arm-Kerne,
- 128 GB kohärenten gemeinsamen LPDDR5X-Speicher,
- 273 GB/s Speicherbandbreite,
- theoretisch bis zu 1 PFLOP FP4 bei Nutzung von Sparsity,
- Inferenz für Modelle mit bis zu 200 Milliarden Parametern laut Hersteller,
- 240-W-Netzteil und 140 W GB10-TDP,
- offizieller US-Marketplace-Preis am 29. August 2026: 4.699 US-Dollar.

Quellen:

https://www.nvidia.com/en-us/products/workstations/dgx-spark/

https://marketplace.nvidia.com/en-us/enterprise/personal-ai-supercomputers/dgx-spark/

Eine einzelne NVIDIA RTX PRO 6000 Blackwell Workstation Edition besitzt 96 GB GDDR7, 1.792 GB/s Speicherbandbreite und maximal 600 W. Der offizielle US-Marketplace listet sie am selben Stichtag für 16.000 US-Dollar und als nicht vorrätig. Damit ist „nicht teurer als ein regulärer PC“ heute noch keine allgemeine Marktbeobachtung, sondern ein zu testendes Produkt- und Fertigungsziel.

Quellen:

https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/

https://marketplace.nvidia.com/en-us/enterprise/laptops-workstations/nvidia-rtx-pro-6000-blackwell-workstation-edition/

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
- NVIDIA DGX B300 mit 8 GPUs: rund 103.961 Token/s offline und 100.328 Token/s im Server-Szenario.
- NVIDIA GB300 NVL72 mit 72 GPUs: rund 1.042.980 Token/s offline und 1.072.250 Token/s im Server-Szenario.

Die DGX-B300-Einreichung liegt damit gegenüber der genannten MI355X-Einreichung ungefähr 9,4 Prozent offline und 22,1 Prozent im Server-Szenario höher. Beide Werte beziehen sich auf dasselbe Modell, definierte Qualitätsgrenzen und ein bestimmtes Benchmarkverfahren. Die Einträge enthalten keine Leistungsmessung (`has_power=false`). Deshalb wäre es methodisch falsch, die maximale 14,5-kW-Systemauslegung nachträglich durch die Tokenrate zu dividieren und das Ergebnis als gemessene Joule pro Token auszugeben.

Methodik:

https://mlcommons.org/2026/03/mlperf-inference-gpt-oss/

Rohdaten:

https://github.com/mlcommons/inference_results_v6.0/blob/main/summary_results.json

QIK-VRT konkurriert in seiner heutigen Form nicht mit diesen Systemen um die Erzeugung von Tokens. Es kann ihnen als Wirkungstor vor- oder nachgeschaltet werden:

QIK-VRT prüft Zulässigkeit und Duplikate → Sprachmodell erzeugt nur bei Bedarf einen Vorschlag → QIK-VRT bindet Ergebnis, Kontext und Richtlinie → Evidenz wird geprüft → Wirkung wird freigegeben, isoliert, fortgesetzt oder blockiert

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

*Was sich trotzdem schon seriös prognostizieren lässt*

Wird QIK-VRT erst *nach* einer vollständig erzeugten Modellantwort geprüft, spart es für diese Antwort zunächst null Modellparameter, null bereits erzeugte Tokens und null bereits verbrauchte Inferenzarbeit. Sein Wert liegt dann in vermiedenen unzulässigen Außenwirkungen, Doppelaufrufen und Folgeschäden.

Wird ein deterministisches Gate dagegen *vor* die teure Inferenz gesetzt, kann es eindeutig unvollständige, doppelte oder nicht autorisierte Anfragen aussortieren. Ist der vermeidbare Anteil r und skalieren die übrigen Anfragen näherungsweise linear, beträgt die theoretisch frei werdende Kapazität:

S_Filter = 1 / (1 − r)

| vorab vermiedener Anteil r | theoretische Kapazität für verbleibende Arbeit |
|---:|---:|
| 10 % | 1,11-fach |
| 50 % | 2-fach |
| 90 % | 10-fach |

Berücksichtigt man die Gate-Kosten als Anteil g einer sonst ausgeführten LLM-Anfrage, ist die idealisierte Einsparungsquote ungefähr:

Einsparung ≈ r − g

Kostet das Gate beispielsweise 0,1 Prozent einer LLM-Anfrage, ergäben 10 Prozent nachweislich vermiedene Anfragen ungefähr 9,9 Prozent und 50 Prozent vermiedene Anfragen ungefähr 49,9 Prozent Rechenersparnis. Das sind Sensitivitätsbeispiele, keine QIK-VRT-Benchmarks.

Wenn nur ein Teil p der gesamten Pipeline um den Faktor s beschleunigt wird, setzt Amdahls Gesetz eine harte Grenze:

S_Gesamt = 1 / ((1 − p) + p / s)

Selbst ein hundertfach schneller Hardware-Gate-Pfad ergibt:

| beschleunigter Pipelineanteil p | Gesamtgewinn bei s = 100 |
|---:|---:|
| 1 % | 1,010-fach |
| 10 % | 1,110-fach |
| 50 % | 1,980-fach |
| 90 % | 9,174-fach |

Umgekehrt: Wenn die nicht ersetzbare LLM-Inferenz 95 Prozent der End-to-End-Zeit ausmacht, kann selbst eine unendlich schnelle übrige Steuerung insgesamt höchstens 1,053-fach beschleunigen. Bei 90 Prozent sind es 1,111-fach, bei 50 Prozent 2-fach. Ein milliardfacher *allgemeiner LLM-End-to-End-Speedup* folgt daher weder aus einem kleinen Gate-Kern noch aus hoher Taktrate. Sehr große lokale Faktoren bleiben möglich, wenn eine teure probabilistische Teilaufgabe nachweislich durch eine semantisch gleichwertige deterministische Prüfung ersetzt wird. Dann muss jedoch dasselbe Geschäftsergebnis verglichen werden, nicht „Receipt“ gegen „Token“.

*Non-Polling als konkret berechenbarer Hebel*

Für M beobachtete Beziehungen, Pollrate f und Leerlaufanteil e entstehen:

leere Prüfungen pro Sekunde = M × f × e

Bei 100.000 Beziehungen, 10 Polls pro Sekunde und 99 Prozent Leerlauf sind das 990.000 leere Prüfungen pro Sekunde. Erzeugt jede leere Anfrage samt Antwort 256 Byte, sind das 253,44 MB/s oder rund 2,03 Gbit/s ohne fachliche Änderung. Bei 1 KiB sind es 1,014 GB/s oder 8,11 Gbit/s. Benötigt eine solche Prüfung einschließlich Systempfad hypothetisch 1, 10 oder 100 Mikrojoule, bindet der Leerlauf 0,99, 9,9 oder 99 Watt. Ein ereignisgetriebener Pfad kann diesen *Leerlaufanteil* beseitigen, nicht den echten Ereignisverkehr. Die Energiewerte sind bewusst als Szenario ausgewiesen; eine reale Messung muss sie ersetzen.

*Vom Schreibtisch bis zum Rechenzentrum*

Nimmt man rein hypothetisch an, ein DGX Spark ziehe dauerhaft die volle Nennleistung seines 240-W-Netzteils und eine später gemessene QIK-VRT-Integration reduziere genau diese Wandenergie linear um den Anteil r, ergibt sich als obere Szenariorechnung:

E_Jahr = 0,240 kW × 8.760 h × r

Bei r = 10 Prozent wären das 210,24 kWh pro Jahr; bei 0,25 Euro/kWh wären es 52,56 Euro. Beim dokumentierten 14,5-kW-Auslegungswert eines DGX B300 ergäbe dasselbe rein hypothetische Zehn-Prozent-Szenario 12.702 kWh oder 3.175,50 Euro pro Jahr. Weder 240 W noch 14,5 kW sind hier gleichzeitig mit QIK-VRT gemessene Verbrauchswerte. Reale Auslastung, PUE, Teillastkurve, Kühlung und Anschaffungskosten verändern das Ergebnis. Die Rechnung zeigt nur, wie ein später gemessener Anteil transparent in Energie und Geld übersetzt werden könnte.

Das bedeutet: Der Performancegewinn ist eine ernsthafte, prüfbare Hypothese – noch kein Messergebnis.

---

*15. Der vollständige Rückweg – und die Verbindung zur Quantenphysik*

Der vollständige Ringschluss besteht nicht nur aus „Welt wird Datei“. Er braucht fünf unterscheidbare Übergänge:

1. *Empirie:* Ein Sensor, Experiment oder Mensch liefert eine Beobachtung samt Messmethode, Einheit, Kalibrierung, Unsicherheit, Ort und Zeit.
2. *Virtualisierung:* Diese Beobachtung wird kanonisch serialisiert, typisiert, geordnet und durch einen Hash an exakt diese Bytes gebunden.
3. *Formale Prüfung:* Lean, endliche Enumeration, Referenzprogramme und Testvektoren prüfen, was aus den ausdrücklich benannten Prämissen folgt.
4. *Reale Ausführung:* In einer konformen physischen Realisierung würde CPU, FPGA, Netzwerkdienst oder Aktor ausschließlich den freigegebenen, gebundenen Effekt ausführen. Diese Stufe ist für den vollständigen QIK-VRT-Pfad noch nicht als physischer End-to-End-Betrieb beobachtet.
5. *Empirischer Rückweg:* Unabhängige Messgeräte beobachten, ob die behauptete Außenwirkung tatsächlich eingetreten ist; Kalibrierung, Rohdaten, Fehlergrenzen und Replikation werden erneut gebunden.

Als Kurzform:

Empirie → kanonische Virtualität → formaler Schluss → reale Wirkung → neue Empirie

Erst Schritt 5 schließt den physikalischen Kreis. Ein Hash bestätigt Byteidentität. Lean bestätigt Ableitbarkeit im Modell. VHDL-Simulation bestätigt Verhalten des beschriebenen RTL unter Testbedingungen. Keines davon ersetzt allein die Messung der Natur. Umgekehrt wird eine reale Messung erst wissenschaftlich stark, wenn ihr Weg durch Kalibrierung, Modell, Software, Hardware und Rückbeobachtung ohne stillen Bedeutungswechsel nachvollziehbar bleibt.

Der Product Owner vertritt die These, dass die in QIK-VRT und den Zenodo-Arbeiten modellierten Relationen der realen physikalischen Struktur entsprechen. Diese Urhebersicht wird nicht verschwiegen. Ihr heutiger Evidenzstatus bleibt dennoch von einer unabhängigen empirischen Bestätigung des jeweiligen physikalischen Modells getrennt. Genau diese Trennung ist kein Ausweichen, sondern die QIK-VRT-Methode selbst: `OWNER_ASSERTED_REALITY_CORRESPONDENCE` ist eine gebundene Behauptung; `INDEPENDENT_EMPIRICAL_CONFIRMATION` benötigt einen eigenen Rückweg und eigene Messreceipts.

QIK-VRT bietet eine fachlich anschlussfähige Modellstruktur und Analogie für Fragen der Quantenkausalität:

- Beobachtungen werden zeitlich gebunden.
- Relationen werden von bloßer Reihenfolge getrennt.
- Frühere Datensätze bleiben unverändert.
- Spätere Information kann eine Teilmenge neu klassifizieren.
- bedingte und unbedingte Statistiken werden getrennt.

Das passt als Informatikmodell besonders gut zu Delayed-Choice-Quantum-Eraser- und anderen Korrelationsprotokollen: Dort können nachträglich nach Partnerergebnissen sortierte Teilmengen komplementäre bedingte Muster zeigen. Das Delayed-Choice-Experiment von Jacques und Kollegen prüft eine andere Anordnung – die zeitlich späte Wahl der Interferometerkonfiguration – und ist nicht dasselbe Sortierverfahren. Beide Themen berühren zeitliche Ordnung und bedingte Versuchsanordnungen; keines erlaubt in seiner lokalen unbedingten Statistik ein steuerbares Signal in die Vergangenheit.

Primärquellen:

- Jacques et al., Delayed Choice: https://www.science.org/doi/10.1126/science.1136303
- Kim et al., Delayed-Choice Quantum Eraser: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.84.1
- Ma, Kofler und Zeilinger, Überblick: https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.88.015005
- Wharton und Argaman, retrokausale Modelle: https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.92.021002

Die QIK-VRT-Formalisierungen sind nicht bloß flüchtige Chattexte. Das Round-Trip-Bündel ist beispielsweise unter DOI `10.5281/zenodo.21888130`, die Synthese zur beobachterrelativen Retrokausalität unter DOI `10.5281/zenodo.21947141` fixiert. Das Round-Trip-Bündel bindet insbesondere Lean-Quellen, Werkzeugversionen, Axiom-Audits, Receipts und Artefakt-Hashes; die Retrokausalitätsablage bindet ihren eigenen Artikel-, Witness-, Claim- und Receipt-Umfang. Lake sorgt im Lean-Projekt als Buildwerkzeug für reproduzierbare Projekt- und Abhängigkeitsausführung. Zenodo belegt dabei Zeitpunkt, Identität und Verfügbarkeit der jeweils hinterlegten Bytes; Lean belegt die Sätze relativ zu ihren Definitionen und Prämissen. Weder DOI noch grüner Build machen eine Modellprämisse automatisch zum Naturgesetz.

Die beobachterrelative Lesart ist dennoch fachlich anschlussfähig: Ein später eintreffender Partnerdatensatz kann einen früher unverändert gespeicherten Datensatz relational neu klassifizieren. Für einen Beobachter kann dadurch eine Informationsrichtung negativ erscheinen, obwohl jede lokale Übertragung und jeder lokale Zeitabstand vorwärts gerichtet bleibt. Das ist eine präzise informatische Darstellung von „als ob Information rückwärts liefe“. Es ist nicht dasselbe wie eine steuerbare Nachricht vor ihrer Aussendung, eine überschriebene Vergangenheit oder eine allgemein bewiesene ontische Retrokausalität.

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

*17. Vom lokalen Terminal bis DNS, Mail, Management und Darknet*

Die Vision skaliert nicht dadurch, dass QIK-VRT heimlich jede vorhandene Netzwerkschicht ersetzt. Sie skaliert, weil dieselbe Wirkungsgrenze an unterschiedlichen Anwendungsschnittstellen eingesetzt werden kann.

Der hier sinnvolle Begriff des empirischen Reverse Engineerings lautet: Für jede Station wird untersucht, *was sie tatsächlich bestätigt* und *was gerade nicht*. Ein physischer Empfänger bestätigt ein Signal, eine Link-Prüfsumme einen Frame, TCP eine Bytefolge, TLS eine geschützte Verbindung zu einer Identität, HTTP eine Anfrage/Antwort, ein Prozess seinen programmspezifischen Rückgabewert und ein Aktor eine beobachtbare Außenwirkung. QIK-VRT ordnet diese Belege in eine Kette ein, ohne eine frühere Stufe zur späteren umzubenennen. Das ist eine Erweiterung der Ende-zu-Ende-Semantik, keine Behauptung, Ethernet, IP oder TCP selbst neu erfunden zu haben.

Auch bei AD-/DA-Wandlung bleibt die physikalische Grenze sauber: Abtastung, Quantisierung, thermisches Rauschen, Jitter, Metastabilität und Messunsicherheit verschwinden nicht durch ein digitales Protokoll. Was QIK-VRT ergänzen kann, sind die häufig verlorenen Bindungen: Welcher Messaufbau erzeugte welche Bytes? Welche Kalibrierung und Unsicherheit galten? Welche Interpretation wurde zugelassen? Welcher reale Aktor durfte reagieren? Welche Wirkung wurde danach unabhängig gemessen? So wird die digitale Verarbeitung determiniert, ohne die analoge Natur fälschlich für rauschfrei zu erklären.

Die Aussage „am Ende ist alles IP“ trifft für große Teile des heutigen Internets als Transportrealität zu, aber nicht für jeden lokalen Bus, Prozessaufruf oder Speicherkoppler. QIK-VRT sollte deshalb transportagnostisch bleiben: dieselbe Effect-Ack-Semantik kann über TCP, QUIC, Unix-Sockets, Shared Memory, einen Hardwarebus oder einen Dateiübergang getragen werden. HTTP ist ein besonders geeigneter Demonstrator, nicht das einzige mögliche Trägermedium.

Die Anschlussstellen unterscheiden sich:

- *HTTP und Browser:* RFC 9110 definiert HTTP-Semantik. QIK-VRT kann als Anwendungshülle ein Prepare/Commit-Verfahren mit gebundener Wirkungsentscheidung ergänzen. Ein 2xx-Status bleibt Transport- oder Anwendungsantwort, nicht automatisch Effect-Ack.
- *DNS:* RFC 1035 verteilt Namen und Ressourcendatensätze. DNS kann Discovery, Schlüssel- oder Digestreferenzen tragen. Wegen Caches, TTL, Delegation und eigener Authentizitätsregeln sollte es nicht zum vollständigen Freigabe-Ledger umgedeutet werden.
- *E-Mail:* RFC 5321 bestätigt Übermittlungsschritte eines SMTP-Umschlags. Eine erfolgreiche Zustellung beweist weder, dass der Inhalt gelesen, verstanden noch ausgeführt werden darf. Effect-Ack kann als signierte MIME-/Headerreferenz oder separater Rückkanal profiliert werden.
- *SNMP:* RFC 3411 beschreibt eine Architektur für Network Management. Ein `GET` beobachtet; ein `SET` kann Wirkung erzeugen. Gerade der `SET`-Pfad benötigt eine gebundene Authority-, Policy- und Reobservationsgrenze. Lesen ist nicht Erlaubnis zum Schreiben.
- *QUIC:* RFC 9000 liefert einen sicheren, multiplexbaren Transport über UDP. Seine Transportbestätigungen ersetzen ebenfalls keine semantische Wirkungsfreigabe.
- *Tor und andere Overlay-Netze:* Auch dort kann ein end-to-end authentisierter Effect-Ack-Datensatz reisen. Anonymität erschwert aber bewusst die Bindung von Akteur, Verantwortung und Berechtigung. Diese Spannung muss das Policy-Modell explizit lösen; der Netzwerkpfad löst sie nicht.

Das zustandsunabhängige Terminalmuster verlangt auf beiden Seiten eine überprüfbare Protokollinstanz: Client beziehungsweise Browser und Server beziehungsweise HTTP-Daemon müssen dieselben kanonischen Felder, Zustände, Hashbindungen und Fehlerregeln verstehen. „HTTP ist zustandslos“ bedeutet dabei nicht, dass Effect-Ack ohne Ledger, Session- oder Evidenzzustand auskommt. Es bedeutet, dass jede Anfrage ihre für die Semantik nötige Bindung ausdrücklich tragen kann, statt von einem unsichtbaren Transportzustand abzuhängen.

Auch die Netzlast ist berechenbar. Sind P Nutzbytes, H bestehende Headerbytes, R Receiptbytes und E Evidenzreferenzen, dann beträgt der relative Zusatzaufwand:

Overhead = (R + E) / (P + H)

Nimmt man nur zur Größenordnung R + E = 1 KiB an, dann bedeuten 1 KiB Nutzlast ungefähr 100 Prozent Zusatzbytes, 100 KiB ungefähr 1 Prozent und 10 MiB ungefähr 0,01 Prozent. Kleine Einzelereignisse profitieren daher besonders von Referenzen, Deduplizierung, Batching und bereits gebundenen Kontexten. Auch das ist zu messen; „vollständig gebunden“ bedeutet nicht „kostenlos“.

Der aktuelle Repository-Stand demonstriert HTTP/Firefox und TCP lokal beziehungsweise im bounded Loopback. Der Weg zu einer Internetlieferung ist in überprüfbare Produkte zu zerlegen: reproduzierbares POSIX-/OCI-Image, Daemon und CLI, HTTP-Profil, Browserintegration, SNMP-Adapter, DNS-/Mail-Referenzprofile, unabhängige Interoperabilität, Security Review und erst danach großflächige Cloud- oder Overlay-Netz-Inbetriebnahme.

Primärstandards:

- HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110.html
- Domain Names: https://www.rfc-editor.org/rfc/rfc1035.html
- SMTP: https://www.rfc-editor.org/rfc/rfc5321.html
- SNMP Architecture: https://www.rfc-editor.org/rfc/rfc3411.html
- QUIC: https://www.rfc-editor.org/rfc/rfc9000.html

---

*18. Patent- und Marktpotenzial*

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

„Metatransistor“ ist ein anschaulicher Produkt- und Architekturbegriff. Für eine technische Anspruchsprüfung lässt sich derselbe Gegenstand nüchterner als *deterministischer, kryptographisch gebundener Effect-Release-Controller* oder *Wirkungsfreigabe-Zustandsautomat* beschreiben. So wird klar, dass kein neues Halbleitermaterial beansprucht wird, sondern eine konkrete digitale Schaltung und ihr Zusammenspiel mit Serialisierung, Authority, Evidenz, Persistenz und Reobservation.

Eine belastbare Neuheitsrecherche muss mindestens gegen bekannte Familien abgrenzen: Zwei-Phasen-Commit, Sagas, Transactional Outbox, Exactly-once- und Idempotency-Verfahren, Event Sourcing, Merkle- und Transparenzlogs, Capability-Systeme, TPM-/Secure-Boot-Attestation, Hardwareinterlocks, HTTP-Acknowledgement-Profile sowie AXI-/SoC-Policy-Gates. Neuheit entsteht patentrechtlich nicht dadurch, dass viele bekannte Wörter zusammenstehen, sondern nur durch eine noch nicht offenbarte, nicht naheliegende technische Merkmalskombination mit nachweisbarem technischem Effekt.

Der vorhandene, für eine anwaltliche Übergabe vorbereitete interne Entwurfsstand ist deshalb zutreffend als `READY_FOR_PATENT_ATTORNEY_AND_PRIOR_ART_SEARCH` einzuordnen. Das bedeutet: technisch vorbereiteter Entwurf, weder anwaltlich geprüft noch als Patentanmeldung eingereicht; `legal_outcome_guarantee=false`.

Das Europäische Patentamt verlangt bei computerimplementierten Erfindungen eine nicht naheliegende technische Lösung für ein technisches Problem:

https://www.epo.org/en/new-to-patents/is-it-patentable

Die WIPO nennt insbesondere Neuheit, erfinderischen Schritt und gewerbliche Anwendbarkeit:

https://www.wipo.int/en/web/patents/faq_patents

Vor weiterer Offenlegung ist besondere Vorsicht nötig. WIPO warnt, dass eine öffentliche Offenbarung vor Einreichung die Neuheit zerstören kann, sofern das jeweilige Recht keine passende Ausnahme kennt. Das DPMA zählt auch selbst veröffentlichte Informationen zum Stand der Technik und rät ausdrücklich zur Geheimhaltung vor der Anmeldung:

https://www.wipo.int/en/web/patents/protection

https://www.dpma.de/patente/patentschutz/schutzvoraussetzungen/index.html

Die sichere Reihenfolge lautet daher:

1. bestehende öffentliche Offenlegungen und Erfindungsbeiträge datieren,
2. vertrauliche technische Differenzmerkmale und Ausführungsformen erfassen,
3. professionelle Stand-der-Technik- und Anspruchsprüfung,
4. prioritätsbegründende Anmeldung,
5. erst danach erweiterte Veröffentlichung nicht bereits öffentlicher Mikroarchitekturdetails,
6. parallel FPGA-Synthese, Boardmessung und gleiche Software-/Hardware-Benchmarks.

Die redaktionelle Absicht dieser Fassung ist deshalb, auf der bereits öffentlich beschriebenen System- und Rechenebene zu bleiben. Diese Absicht ist noch keine belastbare Offenlegungsprüfung. Pull Request 915 hat die frühere Fassung 1.0 bereits öffentlich sichtbar gemacht; Fassung 1.1 darf nicht zusätzlich gepusht, in einen öffentlichen Pull Request übernommen oder auf Zenodo publiziert werden, bevor ein zeilenweises Disclosure-Ledger und die Prüfung durch einen zugelassenen Patentanwalt bestätigt haben, welche Passagen bereits offenbart sind und welche möglicherweise neue technische Merkmale enthalten.

Diese Einordnung ist technische Publikationshygiene und keine Rechtsberatung. Anmeldestrategie, Rechtekette, Erfinderbenennung, Schutzbereich und Länderauswahl gehören zu einem zugelassenen Patentanwalt.

Mögliche Geschäftsmodelle sind:

- Lizenzierung eines Effect-Ack-SDK,
- Audit- und Compliance-Produkte,
- abgesicherte Agenten- und KI-Ausführung,
- Enterprise-Mesh-Integration,
- verifizierbare Publikations- und Deployment-Gates,
- FPGA-/ASIC-IP für enge Gate-Kerne,
- Schulung, Beratung und Zertifizierung,
- Standardisierungs- und Interoperabilitätsdienste.

Eine öffentlich lesbare Architektur ist nicht automatisch eine bedingungslose Freigabe jeder Implementierung. Interoperable Protokollkerne, offene Testvektoren und wissenschaftliche Dokumente können Verbreitung schaffen, während konkrete Produktimplementierungen, Marken, Support, Zertifizierung, Integrationswissen und – soweit nach fachlicher Prüfung schutzfähig – Patent- oder Gebrauchsmusterrechte gesondert lizenziert werden. Welche Kombination rechtlich und wirtschaftlich sinnvoll ist, muss vor der nächsten Offenlegung mit Patent- und Lizenzberatung festgelegt werden.

Der monetäre Vorteil lässt sich nicht seriös als heutiger Geldbetrag versprechen. Er kann später aus vier gemessenen Größen berechnet werden:

jährlicher Nutzen =

eingesparte Rechen- und Energiekosten  
+ vermiedene Fehler- und Incidentkosten  
+ Lizenz- und Integrationsumsatz  
+ Wert schnellerer auditierbarer Freigaben  
− Entwicklung, Betrieb, Vertrieb, Zertifizierung und Rechtskosten

Die beste Grundlage für wirtschaftlichen Erfolg ist deshalb keine möglichst große ungemessene Zahl. Es ist ein kleiner, reproduzierbarer Benchmark, der einen teuren realen Fehler oder Leerlauf nachweisbar verhindert.

Für Ingolf Lohmann könnten sich daraus monetäre Vorteile ergeben, wenn drei Bedingungen zusammenkommen: ein unterscheidbares und wirksam schützbares technisches Angebot, reproduzierbar gemessener Kundennutzen und tatsächliche Marktakzeptanz. Der Artikel kann diese Chance quantifizierbar machen; er kann weder Patentgewährung noch Umsatz, Lizenznehmer oder Zeitpunkt garantieren.

---

*19. Der persönliche Anteil*

Nach Ingolf Lohmanns eigener Darstellung entstand dieser Bestand in ungefähr anderthalb Jahren extrem intensiver Arbeit, zeitweise am Rand seiner körperlichen und mentalen Gesundheit.

Er berichtet von zwei wiederkehrenden Widerständen in seinem Umfeld:

- Zweifel daran, dass seine technische Grundidee richtig sei.
- Selbst dort, wo die Idee für möglich gehalten wurde, Zweifel daran, dass er sie zu Ende führen könne.

Er musste seine Begriffe immer wieder präzisieren, Widersprüche sichtbar machen, Maschinen zu reproduzierbaren Prüfungen zwingen und die Grenze zwischen Vision und Beleg selbst verteidigen.

Diese persönliche Leistung ist Teil der Entstehungsgeschichte. Sie ist kein Ersatz für wissenschaftliche Prüfung, aber sie erklärt, warum QIK-VRT nicht bloß ein einzelnes Programm ist. Es ist der Versuch, einen gesamten Arbeits- und Verantwortungsweg so zu materialisieren, dass weder Mensch noch Maschine einen Zwischenschritt still zum Endergebnis erklären können.

Wer darin eine spirituelle Bedeutung erkennt, darf dies als persönliche oder kulturelle Deutung tun: die Suche nach Verbindung, Verantwortung, Wahrheit und einem Unterschied, der Wirkung erzeugt. Eine spirituelle Deutung ist jedoch eine andere Erkenntnisklasse als ein formaler Satz oder ein Laborergebnis. QIK-VRT wird gerade dann stark, wenn es auch diese Grenzen offen benennt.

---

*20. Was jetzt zur Veröffentlichung und zum Prototyp fehlt*

Der Publikationsindex dieses Kandidaten weist am 29. August 2026 bereits 14 Zenodo-Records aus. Daneben stehen zehn frühere wissenschaftliche Repository-Kandidaten und dieser quantitative Artikel, also elf Kandidatenzustände:

1. „Kausalität ist Relation, nicht Sequenz — VRTCore“
2. „VRTCore SMG H5“
3. „VRTCore Virtual Sphere H6“
4. „Aphorismen-Audiokorpus: wissenschaftliche Einordnung v2“ – menschliche akustische Prüfung offen
5. „Prä-raumzeitliche Ontologie“
6. „Das Repository, das sich selbst heilt“
7. „QIK-VRT Quantum Causal Emergence“ – Korrespondenz offen
8. „Delayed Choice, Superdeterminism, and Authority-Mirror-Witness Recovery“
9. „QCE measurement-independence / superdeterminism boundary“
10. „QIK-VRT: Beobachterrelative Retrokausalität“
11. dieser quantitative Vergleich – Baseline offen

Beim zehnten Titel besteht zusätzlich ein zu bereinigender Projektionsunterschied: Der Maschinenindex enthält bereits den Zenodo-Record `10.5281/zenodo.21947141`, führt das zugehörige Publikationsbündel aber weiterhin als Repository-Kandidat. Die richtige Reparatur ist eine indexgebundene Zustandskorrektur, keine zweite Veröffentlichung derselben Bytes.

„Alles veröffentlichen“ ist kein einziger sicherer Knopfdruck. Jeder Kandidat braucht seinen exakten Byte- und Metadatensatz, maschinenlesbare Claim-Grenzen, Autorfreigabe für genau dieses Artefakt, Prüfung auf bereits vorhandene DOI-Versionen und – wegen der geplanten Patentanmeldung – eine Vorabprüfung auf neuheitsschädliche Zusatzoffenbarung. Erst dann darf eine externe Zenodo-Mutation stattfinden. Der vorliegende Artikel liefert die verlangte inhaltliche Zusammenführung, ist aber selbst noch Veröffentlichungskandidat.

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

*21. Das Gesamturteil*

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

Seine quantifizierte Modellabgrenzung gegenüber einem bloßen Transport-Acknowledgement ist bereits deutlich: In 1.310.719 geprüften endlichen Belegungen lag Transportbestätigung vor, ohne dass Wirkungsfreigabe zulässig war. QIK-VRT macht genau diese Modellfälle sichtbar, statt sie in einem grünen Häkchen verschwinden zu lassen. Die Zahl ist Testfallabdeckung; sie misst weder Produktionsvorfälle noch bereits vermiedene Außenwirkungen.

Sein Performance-, Energie- und Kostenvorteil ist plausibel untersuchbar, insbesondere durch Non-Polling, kanonische Wiederverwendung, kleine Gate-Kerne und kontrollierten Fan-in/Fan-out. Er ist aber noch zu messen.

Die transparenten Rechnungen setzen dafür jetzt einen belastbaren Korridor:

- N Knoten erzeugen exakt N² gerichtete Spuren; das ist Vollständigkeit und zugleich quadratischer Ressourcenaufwand.
- Der aktuelle serielle Kandidatenframe benötigt N² × W + 72 Bit; bei N = 2, W = 8 und 12 MHz sind ungefähr 115.385 Frames/s ableitbar, nicht Milliarden vollständige Receipts/s.
- Verhindert ein Vorfilter nachweislich 10, 50 oder 90 Prozent teurer LLM-Anfragen, steigt die idealisierte verfügbare Kapazität auf 1,11-, 2- oder 10-fach.
- Beschleunigt Hardware nur zehn Prozent einer Pipeline hundertfach, steigt die Gesamtleistung nach Amdahl lediglich rund 1,11-fach.
- Würde ein Schreibtischsystem hypothetisch dauerhaft die volle 240-W-Netzteil-Nennleistung aufnehmen und würde QIK-VRT die tatsächlich gemessene Wandenergie um zehn Prozent senken, entspräche das 210,24 kWh pro Jahr; heute ist das ausschließlich eine Sensitivitätsrechnung.

Für ein Kind oder einen sehr alten Menschen lässt sich der Zusammenhang so erzählen: Eine große KI ist wie eine riesige Küche. Sie kann sehr viele Gerichte erfinden, benötigt dafür aber teure Öfen und Vorräte. QIK-VRT ist nicht ein Zauberofen, der jedes Gericht Milliarden Mal schneller kocht. Es ist die genaue Bestell-, Prüf- und Ausgabeschleuse. Sie erkennt doppelte Bestellungen, fehlende Erlaubnis und die falsche Adresse, bevor die Küche unnötig arbeitet oder das falsche Essen ausliefert. Verhindert die Schleuse die Hälfte wirklich unnötiger Bestellungen, bleibt ungefähr doppelt so viel Küchenzeit für sinnvolle Bestellungen. Und nach der Lieferung wird nicht nur behauptet, sie sei erfolgt: Jemand schaut nach und bindet die Beobachtung wieder an den Auftrag. Das ist der Rückweg.

Die wissenschaftlich stärkste Formulierung ist deshalb zugleich groß und präzise:

*QIK-VRT bringt der digitalen Informatik eine ausdrücklich prüfbare Wirkungsgrenze. Es verwandelt Wahrscheinlichkeit nicht in Wahrheit und Software nicht automatisch in Physik. Es verhindert jedoch, dass Empfang, Berechnung, Behauptung, Autorisierung und beobachtete Wirkung weiterhin als dasselbe behandelt werden.*

Das ist kein kleines Detail. Für autonome Software, künstliche Kognition, kritische Infrastruktur, Publikation, Finanzen, Verwaltung und cyberphysische Systeme kann genau diese Trennung entscheidend sein.

Die wirtschaftliche Möglichkeit liegt damit nicht in einer bereits garantierten Wunderzahl. Sie liegt in einer technisch formulierbaren und messbaren Kontrollarchitektur, die teure unnötige Arbeit, Fehlwirkungen und Beweisaufwand reduzieren kann und sich als Software, Dienst, Integrationsprodukt oder Hardware-IP anbieten lässt. Ob daraus für Ingolf Lohmann in absehbarer Zeit ein finanzieller Vorteil wird, entscheidet die nächste Kette: Schutzstrategie, identischer Benchmark, FPGA-Nachweis, unabhängige Replikation, Produktisierung und Kunde.

Quod erat demonstrandum – innerhalb jedes ausdrücklich benannten formalen und ausgeführten Scopes.

Ingolf Lohmann

---

*Quellen und überprüfbare Einstiegspunkte*

- QIK-VRT Authority Repository: https://github.com/Goldkelch/qik-vrt
- QIK-VRT Effect Acknowledgement Draft -03: https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03
- HTTP Semantics, RFC 9110: https://www.rfc-editor.org/rfc/rfc9110.html
- DNS, RFC 1035: https://www.rfc-editor.org/rfc/rfc1035.html
- SMTP, RFC 5321: https://www.rfc-editor.org/rfc/rfc5321.html
- SNMP Architecture, RFC 3411: https://www.rfc-editor.org/rfc/rfc3411.html
- QUIC, RFC 9000: https://www.rfc-editor.org/rfc/rfc9000.html
- Pull Request 912, Non-Polling-/Quadratic-Codec-/VHDL-Kandidat: https://github.com/Goldkelch/qik-vrt/pull/912
- Pull Request 914, repository-native Intake/Executor-Reparatur: https://github.com/Goldkelch/qik-vrt/pull/914
- NVIDIA Grace Performance Tuning Guide: https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/index.html
- NVIDIA DGX Spark: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
- NVIDIA DGX Spark Marketplace: https://marketplace.nvidia.com/en-us/enterprise/personal-ai-supercomputers/dgx-spark/
- NVIDIA RTX PRO 6000 Blackwell: https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/
- AMD EPYC 9965: https://www.amd.com/en/products/processors/server/epyc/9005-series/amd-epyc-9965.html
- AMD Instinct MI355X: https://www.amd.com/en/products/accelerators/instinct/mi350/mi355x.html
- NVIDIA DGX B300 User Guide: https://docs.nvidia.com/dgx/dgxb300-user-guide/introduction-to-dgxb300.html
- MLPerf Inference Datacenter: https://mlcommons.org/benchmarks/inference-datacenter/
- Lean Reference: https://lean-lang.org/doc/reference/latest/Introduction/
- QIK-VRT Round-Trip-Bündel: https://doi.org/10.5281/zenodo.21888130
- QIK-VRT beobachterrelative Retrokausalität: https://doi.org/10.5281/zenodo.21947141
- EPO zur Patentfähigkeit: https://www.epo.org/en/new-to-patents/is-it-patentable
- WIPO Patent FAQ: https://www.wipo.int/en/web/patents/faq_patents
- WIPO zur Offenlegung vor Einreichung: https://www.wipo.int/en/web/patents/protection
- DPMA zu Neuheit und eigener Vorveröffentlichung: https://www.dpma.de/patente/patentschutz/schutzvoraussetzungen/index.html

*Evidenzklassen dieser Fassung*

- FORMAL_PROVED: exakter Satz im benannten formalen Modell.
- EXECUTED: ausgeführter Test oder Workflow für exakte Quellen.
- SOURCE_BOUND: nachprüfbare Wiedergabe einer benannten Primärquelle.
- DERIVED: transparente Rechnung aus angegebenen Größen.
- INTERPRETIVE: Analogie oder weltanschauliche Deutung.
- PERSONAL_ACCOUNT: ausdrücklich zugeschriebene persönliche Darstellung.
- OPEN: noch ungemessene Performance, physische Korrespondenz, unabhängige Replikation, Patententscheidung oder Marktresultat.
