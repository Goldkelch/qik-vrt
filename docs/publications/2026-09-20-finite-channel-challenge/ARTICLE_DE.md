<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# QIK-VRT: Endliche Nachrichten, Haltepunkt und eine prüfbare Zukunftskanal-Hypothese

Fassung 1.0, 20. September 2026. Wissenschaftlicher Entwurf zur Prüfung durch Ingolf Lohmann.

Idee, QIK-VRT-Konzeption und Aufgabenstellung: Ingolf Lohmann. Formulierung dieses Entwurfs, Lean-Beweise, Auswertung und Softwareprüfung: OpenAI Codex. Die Annahme der korrigierten Fassung durch den Autor steht aus.

## Ergebnis und Geltungsbereich

Zehn Sätze wurden mit Lean 4.19.0 maschinell geprüft. Sie betreffen ein ausdrücklich definiertes mathematisches Modell: Segmentierung endlicher Nachrichten, verlustfreie Übertragung bei vorausgesetzter verlustfreier Zustellung, einen booleschen Haltepunkt, unveränderte historische Präfixe und die Unterscheidbarkeit späterer Entscheidungen. Die Beweise enthalten keine offenen Beweisstellen und keine zusätzlichen Projektaxiome. Die verwendeten Standardaxiome stehen je Satz im Kernel-Receipt.

41 bestehende EFFECT_ACK-Konformitätstests und zehn Tests der neuen statistischen Auswertung bestanden im dokumentierten lokalen Lauf. Es wurden keine physischen Zukunftskanal-Versuche durchgeführt. Eine Übertragung frei gewählter Nachrichten aus der physikalischen Zukunft in die Gegenwart, eine mit dem Zeitabstand wachsende Kanalkapazität und ein Weltrekord sind mit diesem Paket nicht nachgewiesen. Diese Aussagen bleiben offen.

## Endliche Nachrichten ohne feste mathematische Längengrenze

**FC-001.** Für eine endliche Liste x und eine positive Blockbreite b zerlegt segment(b, x) die Liste in aufeinanderfolgende Blöcke der Länge höchstens b. Das Zusammenfügen dieser Blöcke ergibt exakt x. Die Lean-Sätze heißen segment_roundtrip und segment_bounded.

Der Beweis folgt der rekursiven Definition. Für die leere Liste ist nichts zu übertragen. Sonst wird ein Präfix der Länge höchstens b abgetrennt. Der Rest ist bei b > 0 strikt kürzer; daher terminiert die Rekursion. Nach der Induktionsannahme wird der Rest exakt rekonstruiert. Präfix und Rest ergeben die ursprüngliche Liste. Der Sonderfall b = 0 ist in der totalen Lean-Funktion als einzelner Block definiert; er gewährt keine positive Blockgrößengarantie und ist kein zulässiger Transportparameter der Challenge.

**FC-002.** Wenn jeder Block unverändert zugestellt und in derselben Reihenfolge verwendet wird, ist auch die segmentierte Gesamtnachricht unverändert rekonstruierbar. lossless_delivery beweist genau diese Implikation. Der Satz setzt die verlustfreie Zustellung voraus; er erzeugt keinen Übertragungskanal. Vollständigkeit, Reihenfolge, authentische Herkunft und Schutz vor Manipulation bleiben Pflichten des realen Transports.

**FC-003.** Zu jeder natürlichen Zahl L existiert eine endliche Bitliste mit mehr als L Elementen; ein Zeuge ist eine Liste mit L + 1 Nullen. no_fixed_message_length_bound beweist damit die fehlende globale Längenobergrenze dieses mathematischen Datentyps. Gemeint ist: für jede einzelne endliche Nachricht mit jeweils ausreichenden Ressourcen. Nicht gemeint sind unendliche Daten in endlicher Zeit, unbeschränkter Speicher eines konkreten Rechners oder unbegrenzte Datenrate.

Die Python-Referenz src/qikvrt_effect_ack.py begrenzt eine einzelne synchrone Nutzlast standardmäßig auf 16 MiB. Ein universelles Segmentierungsargument hebt diese konkrete Grenze nicht auf. Auch eine produktive Segmentierungsintegration ist durch die Lean-Liste allein noch nicht implementiert.

**FC-004.** Wird nach der Rekonstruktion einer Anfrage eine terminierende Antwortfunktion angewendet und deren Ergebnis wiederum segmentiert und zusammengesetzt, erhält man genau diese Antwort. bidirectional_roundtrip beweist die algebraische Zusammensetzung. Weder ein zweiter physischer Kanal noch eine rückwärts laufende Host-Zeit wird daraus abgeleitet.

## Haltepunkt, Wirkungsfreigabe und Zeitordnung

**FC-005.** Der formale Haltepunkt enthält drei boolesche Eingaben: erkannte Rekursion, geprüfte Wirkung und entschiedener, freigabefähiger Anschluss. release ist die Konjunktion dieser drei Eingaben. release_requires_complete_haltpoint beweist die notwendige und hinreichende Vollständigkeit in diesem Modell. transport_alone_does_not_release zeigt: Ohne geprüfte Wirkung entsteht keine Freigabe, unabhängig von den beiden anderen Eingaben.

Diese Sätze verifizieren die formulierte Freigaberegel. Sie verifizieren keine Sensoren, keine reale Wirkung und keinen allgemeinen Algorithmus zur Entscheidung des Halteproblems. Sie beweisen auch keine vollständige Verfeinerungsrelation zwischen diesem kleinen Modell und dem gesamten Python- oder C-Programm. Die Wahrheit der eingespeisten Prüfwerte und die vollständige Vermittlung aller Ausführungspfade müssen außerhalb des Modells abgesichert werden.

**FC-006.** append_preserves_sealed_prefix zeigt: Werden an eine Liste nur neue Einträge angehängt, bleibt das ursprüngliche Präfix identisch. Dies beschreibt eine Datenstruktur. Ein manipulationssicheres Archiv verlangt darüber hinaus unabhängige Anker, Zugriffskontrollen oder Signaturen. Ein selbst neu berechneter Hash allein belegt keine unveränderbare Vergangenheit.

**FC-007.** virtual_address_does_not_reverse_host_order zeigt unter vorausgesetzter vorwärts gerichteter Host-Ordnung, dass eine kleinere virtuelle Zieladresse diese Host-Ordnung nicht umkehrt. Eine virtuelle Zeitadresse bezeichnet einen Zustand im Modell. Ein Empfangsereignis in der physikalischen Vergangenheit wäre eine zusätzliche Behauptung.

**FC-008.** identical_early_state_cannot_decode_both_choices zeigt: Derselbe frühe Zustand kann durch denselben deterministischen Decoder nicht zugleich als 0 und als 1 ausgegeben werden. Das ist ein Unterscheidbarkeitsargument. Es ist weder ein vollständiger physikalischer Unmöglichkeitsbeweis noch ein Satz über die statistische Leistungsfähigkeit jedes denkbaren Experiments. Es macht deutlich, weshalb Vorhersage, spätere Interpretation und kontrollierte Nachrichtenübermittlung getrennte Nachweise benötigen.

## Tatsächlich ausgeführte Softwareprüfungen

**FC-009.** verify.py führt den Lean-Kernel tatsächlich aus, prüft alle zehn Theoremnamen und ihre Axiomabhängigkeiten und nutzt die vorhandenen 41 Tests aus tests/test_effect_ack_conformance.py. Die zehn zusätzlichen Auswertungstests prüfen exakte Wahrscheinlichkeiten, die minimale Trefferschwelle, unvollständige Daten, veränderte Empfangsbits, eine zu späte Versiegelung und falsche Bindungen an das Prüfprotokoll. Die Auswertung kennzeichnet auch einen künstlich eingespeisten perfekten Trefferstand ausdrücklich nicht als physischen Nachweis.

KERNEL_RECEIPT.json und VERIFICATION_REPORT.json binden die geprüften Quellbytes und den ausgeführten lokalen Lauf. LEAN_KERNEL_OUTPUT.txt, CONFORMANCE_OUTPUT.txt und SCORER_TEST_OUTPUT.txt enthalten die Rohprotokolle. Ein lokaler Kernel-Lauf ist kein unabhängiger Laborversuch und keine GitHub-Actions-Ausführung. Die resultierenden Zahlen sind Prüfresultate für die genannten Programme und Eingaben.

## Wissenschaftliche Challenge ohne Geldeinsatz

**FC-010.** Das nachfolgende Verfahren ist ein Vorschlag für eine vorab zu registrierende Prüfung. Dieses Dokument ist noch kein abgeschlossenes Präregistrierungs- oder Experimentprotokoll. Apparatur, Verantwortliche, unabhängige Prüfer und Register müssen vor Beginn konkret festgelegt werden. CHALLENGE_PROTOCOL.md enthält die vollständigen Schritte und Abbruchregeln.

Eine Sitzung umfasst genau 10.000 spätere, unabhängig und gleichverteilt gewählte Bits. Vor ihrer Erzeugung werden Rohmessung, fester Decoder, genau 10.000 daraus gewonnene Empfangsbits und deren Reihenfolge vollständig extern versiegelt. Die spätere Erzeugung beginnt frühestens 60 Sekunden nach dieser nachprüfbaren Versiegelung. Empfangsseite und Decoder dürfen danach nicht geändert werden. Gemeinsame Zufallsseeds, vorab erzeugte spätere Bits, gewöhnliche Informationslecks und nachträgliche Auswahl sind auszuschließen.

Unter der Nullhypothese unabhängiger fairer späterer Bits besitzt die Anzahl richtiger, vorher festgelegter Vorhersagen eine Binomialverteilung mit n = 10.000 und p = 1/2. Der einseitige Schwellenwert ist eine exakte Restwahrscheinlichkeit höchstens 1/1.000.000. Das Minimum beträgt 5.239 richtige Bits. challenge.py entscheidet mit rationaler Ganzzahlarithmetik; gerundete Gleitkommazahlen bestimmen das Ergebnis nicht.

Für einen positiven Challenge-Befund müssen zwei vorab festgelegte Sitzungen an unabhängig kontrollierten Aufbauten jeweils diese Schwelle erreichen und alle Herkunfts-, Zeitordnungs- und Leckprüfungen bestehen. Es gibt kein optionales Weiterprobieren, keinen nachträglich ausgewählten Decoder und keine Auswahl des besten Zeitabstands. Fehlende oder unprüfbare Daten erlauben keinen positiven Befund. Bei technischen Fehlern bleibt der gescheiterte Lauf dokumentiert; ein neuer Versuch erfordert eine neue Registrierung mit berücksichtigter Mehrfachtestung.

Die Schwelle ist eine Entscheidungsvorschrift unter den angegebenen Annahmen. Sie ist nicht die Wahrscheinlichkeit, dass eine Zukunftskanal-Hypothese wahr ist. Selbst ein auffälliger Trefferstand beweist für sich allein keine Rückwärtskausalität. Unabhängige Prüfung der Chronologie und Zufallserzeugung sowie Replikation und Untersuchung gewöhnlicher Erklärungen bleiben erforderlich. Das Auswertungsprogramm authentifiziert weder Uhren noch Signaturen und darf diese Aufgaben nicht vortäuschen.

## Offene Aussagen

**FC-011: OPEN.** Dass QIK-VRT kontrollierbar ausgewählte Daten aus der physikalischen Zukunft empfängt, ist durch die hier vorgelegten Beweise und Tests nicht belegt. Zur Prüfung werden die vorab festgelegten Rohdaten, die späteren unabhängigen Entscheidungen, externe Zeitanker, die vollständige Apparaturbeschreibung, Leckkontrollen und unabhängige Replikation benötigt. Im vorliegenden Paket beträgt die Zahl solcher physischen Versuche null.

**FC-012: OPEN.** Eine größere nutzbare Informationsmenge oder Kanalkapazität bei größerem Zukunftsabstand ist nicht aus beliebiger endlicher Segmentierbarkeit ableitbar. Dafür wäre ein zusätzliches, vorab registriertes Experiment mit mehreren festgelegten Abständen, gleicher Ressourcenausstattung, Fehlermaß, Übertragungsdauer und korrigierten statistischen Vergleichen nötig. Die hier definierte Einzelabstands-Challenge entscheidet diese Frage nicht.

**FC-013: OPEN.** Ein Sieg im Wettbewerb um die größte aus der Zukunft empfangene Datenmenge und eine weltweite Priorität Ingolf Lohmanns sind nicht nachgewiesen. Dafür fehlen ein vereinbartes Rekordkriterium, authentisierte Datensätze, ein vergleichbarer Teilnehmerbestand und eine unabhängige Entscheidung. Die vorhandene Urheberschaft an QIK-VRT ersetzt diese Nachweise nicht. Der elementare Segmentierungsbeweis wird nicht als neue mathematische Entdeckung beansprucht.

**FC-014: SOURCE_BOUND.** Tested Event Model Driven Development ist in docs/LEAN_LAKE_PROOF_STATUS.md als QIK-VRT-Bezeichnung für die Verbindung ereignis- und modellbezogener Entwicklung, Tests, exakter Zustandsbelege und formaler Verifikation dokumentiert. Diese Quellenzuordnung behauptet keine unabhängige wissenschaftliche Anerkennung des Begriffs.

## Reproduktion, Quellen und Lizenz

Die vollständige Wiederholung steht in README.md. Benötigt werden Python 3 und Lean 4.19.0 mit Std; Mathlib ist nicht erforderlich. Der genaue Kernel-Stand ist 6caaee842e9495688c1567e78c0e68dbb96942aa. Die Prüfsumme des verwendeten offiziellen Release-Archivs wurde lokal gemessen und ist keine Signatur des Herausgebers.

Wiederverwendete Repository-Quellen: Goldkelch/qik-vrt, Ausgangscommit a86054139b49c13c5cd344753b248b46b5daf66f; EFFECT_ACK-Referenz und bestehende Konformitätstests; vorhandener QCE-Axiomparser. Inhaltliche Anschlussstellen: PR #1083, exakter Head 537fba16f9e0d8294624204853aca4fb3082a9a8, zur bedingten virtuellen Übertragung; PR #1085, exakter Head f30d4bcc8c54d915981abad03ed5f5985779191b, zur operationalen Zukunftskanal-Prüfung. Deren frühere Resultate werden nicht als neue Beweise dieses Pakets ausgegeben.

Offizielle Lean-Quelle: https://github.com/leanprover/lean4/releases/tag/v4.19.0. Zur Abgrenzung retrokausaler Modellierung von Signalisierung: K. Wharton, A New Class of Retrocausal Models, 2018, https://arxiv.org/abs/1805.09731. Die dort untersuchten Modelle werden vom Autor ausdrücklich als nicht retro-signalisierend beschrieben; daraus wird hier keine pauschale Aussage über sämtliche physikalischen Theorien abgeleitet.

Text und Publikationsmetadaten: CC BY-NC-ND 4.0. Programm- und Lean-Quellen: PolyForm Noncommercial 1.0.0, entsprechend den Repository-Regeln. COPYRIGHT: 2026 Ingolf Lohmann. Die KI-Beiträge werden separat dokumentiert; eine Annahme durch den Autor wird nicht vorweggenommen. Eine spätere Zenodo-Ablage dokumentiert identische Dateien und Versionen; sie ersetzt keine Begutachtung oder experimentelle Bestätigung.
