# Beschreibung — Entwurf

## Bezeichnung
Rechnerarchitektur und Hardware-Übergangseinheit zur evidenzgebundenen Steuerung von Zustandsübergängen

## Technisches Gebiet
Die Erfindung betrifft digitale Rechnerarchitekturen, Hardware-Zustandsmaschinen, verteilte Verarbeitungssysteme und Verfahren zur Steuerung der Gültigkeit von Daten- und Zustandsübergängen.

## Technischer Hintergrund
In digitalen Systemen können Berechnung, Übertragung, Empfang, Speicherung und die tatsächliche Erreichung eines beabsichtigten Folgezustands zeitlich und logisch auseinanderfallen. Eine Bestätigung der Übertragung oder der Byte-Integrität belegt nicht notwendigerweise, dass ein beabsichtigter nachgelagerter Zustand erreicht und akzeptiert wurde.

## Technische Aufgabe
Bereitgestellt werden soll eine Hardware- und Rechnerarchitektur, welche die Freigabe eines resultierenden Daten- oder Folgezustands von maschinenprüfbaren Bedingungen des zugehörigen Zustandsübergangs abhängig macht und bei nicht erfüllten Bedingungen fail-closed bleibt.

## Grundgedanke
Eine Übergangseinheit verarbeitet Nutzdaten zusammen mit Metainformationen, welche wenigstens eine Bindungsinformation für den Gegenstand des Übergangs und eine Freigabeinformation repräsentieren können. Weitere Ausführungsformen verwenden Autoritäts-, Unterscheidungs-, Provenienz-, Drift-, Readback- oder Akzeptanzinformationen.

Die Einheit erzeugt neben einem Ergebnis einen Übergangszustand. Solange erforderliche Bedingungen nicht erfüllt sind, wird die Gültigkeit des Ergebnisses nicht freigegeben. Dadurch wird die Gültigkeit eines Rechenergebnisses von der bloßen Erzeugung oder Übertragung des Ergebnisses getrennt.

## Beispielhafte Zustände
Eine Ausführungsform verwendet OBSERVE, HOLD und CONTINUE. Diese Namen und die Anzahl der Zustände sind nicht wesentlich. HOLD bezeichnet einen Zustand, in dem ein Ergebnis nicht als gültige Fortsetzung freigegeben wird. CONTINUE bezeichnet eine zulässige Fortsetzung. Ein übergeordneter Effect-Acknowledgement-Zustand kann erst nach zusätzlicher Beobachtung, Rücklesung und Akzeptanz erreicht werden und ist nicht mit Transportbestätigung gleichzusetzen.

## Ausführungsform 1 — lokale Hardware-Übergangseinheit
Eine digitale Einheit weist Dateneingänge A und B, eine Funktionsauswahl, Steuereingänge und Ausgänge für Ergebnis, Übergangszustand und Ergebnisgültigkeit auf. In einer konkreten Ausführungsform umfassen die Steuereingänge binding, authority, distinction, drift und requested.

Fehlt eine erforderliche Bindung, Autorisierung oder Unterscheidbarkeit oder wird Drift angezeigt, nimmt die Einheit einen HOLD-Zustand an und sperrt die Ergebnisgültigkeit. Sind die Bedingungen erfüllt, kann ein angeforderter zulässiger Übergang ausgeführt werden. Eine konkrete RTL-Ausführungsform implementiert eine bitweise, über eine Lookup-Tabelle auswählbare Boolesche Funktion.

## Ausführungsform 2 — registrierte/mehrtaktige Einheit
Die Übergangsinformationen können in Registern gehalten und über mehrere Takte ausgewertet werden. Daten- und Metadatenpfad können getrennt geführt werden. Die Ergebnisfreigabe kann durch ein Valid-Signal, Clock Enable, Write Enable, Commit Gate oder ein funktional entsprechendes Hardwaremittel erfolgen.

## Ausführungsform 3 — FPGA/ASIC
Die Übergangseinheit kann in VHDL, Verilog oder einer anderen Hardwarebeschreibungssprache beschrieben, synthetisiert und in FPGA-, ASIC- oder vergleichbarer programmierbarer bzw. kundenspezifischer Logik realisiert werden. Mehrere Einheiten können hierarchisch oder parallel gekoppelt werden.

## Ausführungsform 4 — Kommunikationskopplung
Eine Kommunikationsschnittstelle überträgt Nutzdaten gemeinsam mit einer Identität des gebundenen Gegenstands und optional Quell-, Ziel-, Provenienz- oder Integritätsinformationen. Eine Transport- oder Integritätsbestätigung wird nicht automatisch als Bestätigung des beabsichtigten nachgelagerten Effekts behandelt.

## Ausführungsform 5 — Readback
Ein nachgelagerter Zustand kann beobachtet und über einen vom Ausführungsschritt logisch getrennten Rücklesepfad zurückgeführt werden. Eine Akzeptanzeinheit vergleicht den zurückgelesenen Zustand mit einer vorgegebenen Akzeptanzbedingung. Erst bei erfüllter Akzeptanzbedingung kann ein terminaler Abschlusszustand für den gebundenen Übergang erzeugt werden.

## Successor-Bindung
Nach einem abgeschlossenen Übergang kann der beobachtete Folgezustand als neuer gebundener Eingangszustand eines nachfolgenden Übergangs verwendet werden. Die Evidenz des vorherigen Übergangs wird dabei nicht ohne erneute Bindung als Nachweis des Nachfolgezustands behandelt.

## Technische Wirkungen
Je nach Ausführungsform können ungültige Zustandsfortschreibungen unterdrückt, Kommunikations- und Wirkungsbestätigungen getrennt, Drift fail-closed behandelt und Zustandsübergänge auf einen konkret gebundenen Gegenstand zurückgeführt werden.

## Implementierungsvarianten
Die Funktionen können kombinatorisch, sequentiell, mikroprogrammiert, als Hardware-/Software-Kopplung oder verteilt implementiert werden. Einzelne Metadatenfelder können kodiert, zusammengefasst oder durch funktional äquivalente Signale ersetzt werden.
