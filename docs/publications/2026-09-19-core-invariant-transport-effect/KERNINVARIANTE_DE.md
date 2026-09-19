<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Empfang, Freigabe und Wirkungsnachweis

## Die Kerninvariante von QIK-VRT

Technische Notiz · Version 1.0.0 · 19. September 2026 (UTC)

Konzept und Auftrag zur dauerhaften Festhaltung: Ingolf Lohmann. Quellenprüfung und redaktionelle Ausarbeitung: OpenAI ChatGPT / Codex. Die Annahme eines KI-Entwurfs verändert dessen Beitragsherkunft nicht.

### C1 — Empfang ist keine Wirkungsfreigabe

`TRANSPORT_ACK ≠ EFFECT_ACK`. Der bestätigte Empfang einer Information, eine erfolgreiche Berechnung oder Speicherung erteilen für sich allein keine Erlaubnis, den nachgelagerten Effekt freizugeben. QIK-VRT trennt diesen technischen Erfolg von der verantwortungsgebundenen Freigabeentscheidung.

### C2 — Genau ein Zustand erlaubt ordinary release

Für ein gültiges Ergebnis des untersuchten Referenzkerns gilt `ordinary_release(result) ⇔ result.state = EFFECT_ACK_DONE`. Die übrigen vier normativen Zustände — `EFFECT_NACK`, `EFFECT_ACK_CONTINUE`, `EFFECT_ACK_ISOLATE` und `EFFECT_ACK_BLOCK` — erteilen diese Freigabe nicht. Die Äquivalenz beschreibt den untersuchten Entscheidungskern; sie ist keine allgemeine Fertigmeldung für das Gesamtprodukt.

### C3 — Die Integration trägt die Nachweispflicht

Der reine Referenzkern verarbeitet übergebene Prüfaussagen. Er authentifiziert selbst keine externe Herkunft und untersucht keinen externen Evidenzspeicher. Eine reale Integration muss diese Aussagen aus authentischen Prüfungen ableiten und kontrollieren, wer Freigabeanfragen erstellen darf. Ein gesetztes Wahrheitsfeld ersetzt diese Arbeit nicht.

### C4 — Das Demo zeigt Entscheidungsfälle

Das untersuchte Demo berechnet vier voneinander getrennte Anfragen: offene Prüfungen, Isolation, Sperre und vollständig gesetzte Freigabebedingungen. Es übergibt dabei kein Vorgängerprotokoll. Seine vier Ausgaben dokumentieren deshalb keine verkettete Zustandsentwicklung eines realen Außeneffekts. Der fünfte normative Zustand `EFFECT_NACK` wird in diesem Demo nicht vorgeführt.

### C5 — Die Hash-Kette hat eine genaue Integritätsgrenze

Die Referenzimplementierung prüft Protokollhashes sowie Wurzel-, Versions- und Vorgängerverknüpfungen. Um ein vollständiges Umschreiben einer Kette einschließlich neu berechneter Hashes zu erkennen, verlangt ihre dokumentierte Vertrauensgrenze zusätzlich einen vertrauenswürdig außerhalb der veränderbaren Kette gehaltenen Hash oder eine geeignete Signaturschicht.

### C6 — Kausalität verlangt mehr als Reihenfolge

„Ein erkanntes Muster kann einen Zusammenhang beschreiben. Kausalität verlangt den Nachweis, wodurch die Wirkung zustande kam.“ — Ingolf Lohmann. Als methodische Regel für diese Notiz bedeutet das: Zeitliche Reihenfolge und eine konsistente Aufzeichnungskette allein begründen keine kausale Beziehung. Behauptete Ursache, beobachtete Wirkung, genauer Gegenstand und Nachweis ihrer Verbindung müssen getrennt benannt werden.

### C7 — Freigabe und beobachteter Außeneffekt bleiben getrennt

Für die praktische Anwendung dieser Invariante ist vorab festzulegen, welcher Effekt nachgewiesen werden soll. Die Entscheidung, einen Effekt freizugeben, und die spätere Beobachtung dieses Effekts sind unterschiedliche Nachweisgegenstände. Ein erfolgreicher Abruf des Nachweises genügt erst zusammen mit dessen passendem, geprüftem Inhalt. Diese Notiz erklärt keine konkrete externe Transaktion für erfolgreich.

### C8 — Der Nachweisumfang bleibt begrenzt

Diese Notiz bindet ihre Implementierungsaussagen an `Goldkelch/qik-vrt`, HEAD `a86054139b49c13c5cd344753b248b46b5daf66f`, TREE `feff1cae2401a3df83febc3b9458de70d79b818e`. Sie behauptet weder einen neuen Lean-Kernelbeweis noch eine frische Gesamtvalidierung des Repositorys, unabhängige wissenschaftliche Bestätigung oder einen universellen Sicherheitsnachweis. Eine spätere Archivierung dieser Bytes ersetzt keinen dieser Nachweise.

## Quellen und Geltungsbereich

- [Referenzkern](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/src/qikvrt_effect_ack.py): C1–C3 und C5.
- [Referenzdemo](https://github.com/Goldkelch/qik-vrt/blob/a86054139b49c13c5cd344753b248b46b5daf66f/examples/effect_haltpoint_demo.py): C4.
- C6 und C7 sind ausdrücklich methodische Festlegungen, keine zusätzlich behaupteten mathematischen Theoreme. C8 begrenzt den Anspruch dieser Notiz.
- Die begleitende `CLAIM_MATRIX.json` ordnet jeden nummerierten Claim seiner epistemischen Klasse und seinen genauen Quellen zu. Ausführungsnachweise gelten ausschließlich für ihren jeweils bezeichneten Prüfumfang.

Copyright 2026 Ingolf Lohmann. Dokumentation: CC BY-NC-ND 4.0. Quellcode in den zugehörigen Nachweisen behält seine jeweilige Dateilizenz.
