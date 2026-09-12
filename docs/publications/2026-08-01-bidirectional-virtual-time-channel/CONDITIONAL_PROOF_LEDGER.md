<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Ledger der bedingten Papierbeweise

## VTI-003 – Präfixintegrität

Voraussetzungen: Die Quellhistorie ist append-only; Replay schreibt
ausschließlich in einen neuen Branch; jeder mutierende Nebenpfad ist
ausgeschlossen.

Beweisidee: Keine erlaubte Übergangsregel besitzt die Quelle als
Schreibziel. Induktion über die Folge erlaubter Übergänge erhält daher jedes
bereits vorhandene Quellpräfix.

Kernelstatus: offen.

## VTI-004 – Hostkausalität

Voraussetzung: Jede erzeugende Operation erhält einen strikt größeren
Hostindex als ihre Vorgänger.

Beweisidee: Die virtuelle Zieladresse ist nur ein Datenfeld der Operation.
Transitive Anwendung der Hostordnung ergibt für jeden später erzeugten
Effekt einen größeren Hostindex, auch wenn seine virtuelle Adresse kleiner
ist.

Kernelstatus: offen.

## VTI-005 – Jede einzelne endliche Bitfolge

Voraussetzungen: endliche Nachricht; positive Blockgröße; vollständiges
Manifest; integre eventual delivery; ausreichende endliche Ressourcen.

Konstruktion: Zerlege n Bits in endlich viele nummerierte Blöcke, übertrage
sie mit Längen- und Integritätsbindung und reassembliere erst nach
vollständigem Manifest. Die Verkettung der geordneten Blöcke ist die
ursprüngliche Bitfolge.

Die Aussage quantifiziert über jede einzelne endliche Nachricht. Sie
behauptet nicht, dass eine feste endliche Maschine gleichzeitig unbegrenzte
Speicherkapazität besitzt.

Kernelstatus: offen.

## VTI-006 – Bidirektionaler virtueller Dialog

Voraussetzungen: VTI-005 in beiden Richtungen; terminierende
Antwortfunktion; eindeutige Session-, Branch- und Sequenzidentitäten;
vollständige Gates.

Konstruktion: Übertrage die Anfrage an die frühere virtuelle Adresse,
berechne die endliche Antwort und instanziiere dieselbe
Übertragungskonstruktion in Gegenrichtung. Die virtuelle Kante schließt
sich; die Hostordnung bleibt strikt vorwärts.

Kernelstatus: offen.

## VTI-008 – DONE-only unter vollständiger Mediation

Voraussetzungen: Jeder Pfad zum Executor führt durch dasselbe Gate;
ordinary release ist genau dann erlaubt, wenn der Record vollständig gültig
ist und den Zustand EFFECT_ACK_DONE trägt.

Beweisidee: Für jeden Non-DONE-Record ist die Gatekonjunktion falsch. Ein
Bypass wäre keine Widerlegung des bedingten Satzes, sondern eine Verletzung
seiner Mediationvoraussetzung.

Kernelstatus der neuen Deploymentschicht: offen.

## VTI-009 – Exactly-once

EFFECT_ACK allein liefert kein exactly-once für einen
nichttransaktionalen Aktuator. At-most-once verlangt atomaren
Dedup-/Effect-Commit oder Idempotenz; exactly-once verlangt zusätzlich
eventual delivery und eventual availability unter dem angegebenen
Fehlermodell.

Kernelstatus: offen.

