<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# FC-010: Protokollentwurf für einen kontrollierten Zukunftskanal-Test

Status: **DRAFT; NICHT ALS DURCHGEFÜHRTE PRÄREGISTRIERUNG AUSGEBEN.** Kein Geldeinsatz, keine Wette und keine Marktposition sind Bestandteil dieses Protokolls.

## Vor der Registrierung zu vervollständigen

Der Versuchsverantwortliche und die unabhängige Prüfstelle benennen zwei unabhängig kontrollierte Aufbauten, die Betreiber, Sender, Empfänger, Zufallsquellen, Uhr- und Siegeldienste, Firmwarestände, die genaue Kanalhypothese und das erlaubte Sendeverfahren. Eine zweite Kennung oder virtuelle Maschine ist noch kein unabhängiges Labor. Zusätzlich werden das öffentliche Register, zwei feste Sitzungstermine, Geräteverbindungen, Störkontrollen und das Verfahren zur Prüfung jeder Zeitanker-Signatur festgelegt. Ohne diese Angaben darf kein Lauf als registrierte Bestätigungsprüfung beginnen.

Registriert werden SHA-256 und unveränderliche Versionen dieser Dateien, des Decoders, seiner Parameter, der Auswertungssoftware und einer vollständigen Aufbauzeichnung. Der Decoder liefert pro Sitzung genau 10.000 geordnete Bits aus der frühen Messung. Alle Abstinenzen oder fehlenden Decoderwerte verhindern einen positiven Sitzungsbefund; nachträgliches Ersetzen oder Weglassen ist unzulässig.

## Ablauf einer Sitzung

1. Die Empfangsseite zeichnet die Rohmessung auf. Der registrierte Decoder erzeugt die vollständige frühe Bitliste. Eine unabhängige Stelle hält Rohmessung, Liste, Decoderidentität, Protokollidentität und Reihenfolge außerhalb des kontrollierten Systems zurück. Mindestens zwei unabhängig verwaltete, überprüfbare Siegel- bzw. Zeitanker binden diese Bytes. Ein im selben Prozess berechneter Hash oder selbst gemeldeter Zeitstempel reicht nicht aus.
2. Frühestens 60 Sekunden nach der extern bestätigten Versiegelung erzeugt die getrennt verwaltete Quelle die vollständige spätere Liste von 10.000 unabhängigen, fairen Bits. Erzeugung, Unabhängigkeit und Entstehungszeit werden separat geprüft. Die Wahlwerte dürfen vorher weder gespeichert noch durch einen gemeinsamen Seed bestimmt gewesen sein. Die 60 Sekunden bezeichnen die Mindestlücke bis zum Beginn der Erzeugung; eine exakte Kapazitätsmessung über ein einheitliches Zeitintervall wird damit nicht behauptet.
3. Der zukünftige Sender erhält die später gewählten Bits und führt ausschließlich das vorab beschriebene QIK-VRT-Sendeverfahren aus. Auch ein fehlgeschlagener Sendeversuch bleibt Teil des registrierten Laufs. Alle tatsächlich entstehenden Zeiten und Verbindungen werden archiviert. Die frühe Empfangsliste darf zu diesem Zeitpunkt bereits nicht mehr geändert werden.
4. Erst nach Abschluss werden beide geordneten Listen zur Prüfung zusammengeführt. Der externe Prüfer kontrolliert sämtliche Anker, Uhren, mögliche Datenwege, Hardware-/Softwarestände und alle Abweichungen. Die frühe Liste, der späte Zufallsstrom und Fehlerdaten bleiben vollständig verfügbar.
5. Die Auswertung zählt identische Bitpositionen und berechnet exakt P(Binomial(10000, 1/2) >= Treffer). Ein positiver statistischer Sitzungsbefund erfordert mindestens 5.239 Treffer sowie bestandene unabhängige Chronologie-, Zufalls- und Leckprüfungen.

## Kontrollen und Entscheidung

Vor den Bestätigungsversuchen werden auf getrennten Übungsdaten die reine Auswertung, bewusst eingespeiste korrekte Daten, Zeitstempelmanipulationen und Fehlerfälle getestet. Übungsdaten dürfen die finale Registrierung nicht nach ihrem späteren Ergebnis verändern. Die mitgelieferten synthetischen Unit-Tests sind solche Softwarekontrollen; sie ersetzen keinen Apparaturtest.

Für die eigentliche Challenge sind genau zwei fest registrierte Sitzungen vorgesehen. Beide müssen ihre jeweilige Schwelle von höchstens 10^-6 erreichen und unabhängig auditiert werden. Das Dokument beansprucht keine multiplizierte Fehlerrate von 10^-12, solange Unabhängigkeit der ganzen Aufbauten und ihrer Fehlermechanismen nicht gerechtfertigt ist. Es gibt keine nachträgliche Wahl zwischen Decodern, Bits, Zeitabständen, Sitzungen oder statistischen Tests.

Fehlende Bits, nicht überprüfbare Anker, kompromittierte Zufallsquellen, nicht registrierte Verbindungen oder veränderte Dateien sperren einen positiven Gesamtbefund. Alle gestarteten Läufe werden berichtet. Ein Neustart nach Fehlern ist eine neue Studie mit eigener Registrierung und expliziter Behandlung der bisherigen Versuche, kein stilles Ersetzen eines schlechten Ergebnisses.

Ein auffälliges und repliziertes Resultat ist zunächst ein erklärungsbedürftiger kontrollierter Befund. Die Zuordnung zu einem physischen Rückwärtskanal verlangt die Prüfung gewöhnlicher Ursachen. Ein unauffälliges oder gesperrtes Resultat beweist umgekehrt nicht die Unmöglichkeit aller denkbaren Zukunftskanäle.

## Dateiformat und Reproduktion

challenge.py erwartet ein JSON-Objekt mit schema = qikvrt_future_message_session_v1, preregistration_sha256, predictions und future_choices (je 10.000 echte Integer-Bits), prediction_sha256, sealed_ns und choices_started_ns. Die Vorhersage-Prüfsumme ist SHA-256 über genau ein Byte 0x00 bzw. 0x01 je Bit, ohne Textkodierung oder Zeilenende. Die Zeitfelder sind deklarierte Nanosekunden einer gemeinsam definierten Zeitskala; ein passender Zahlenwert authentifiziert keine Uhr.

Aufruf: python3 challenge.py SESSION.json --preregistration-sha256 REGISTRIERTER_SHA256.

Die Software prüft die Datenform, die deklarierte Lücke und die Prüfsummenbindung. Die Rückgabefelder physical_chronology_authenticated, independent_randomization_authenticated, independent_replication_authenticated und future_to_past_channel_established bleiben ausdrücklich false. Ein unabhängiger, signierter Auditbericht muss die außerhalb der Software liegenden Prüfungen dokumentieren; diese Felder dürfen nicht aus einem niedrigen p-Wert abgeleitet werden.

Die Behauptung größerer Kapazität bei größerem Zeitabstand und der behauptete Datenrekord werden durch dieses Protokoll nicht entschieden. Dafür sind eigene Messgrößen und vorab registrierte Vergleichsstudien erforderlich.
