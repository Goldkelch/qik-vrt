# Patentansprüche — Arbeitsentwurf, nicht eingereicht

1. Hardware-Übergangseinheit für ein digitales Verarbeitungssystem, mit
   einem Datenpfad zur Verarbeitung wenigstens eines Eingangsdatenwertes,
   einem Metadatenpfad zur Aufnahme wenigstens einer einem zu verarbeitenden Zustandsübergang zugeordneten Bindungsinformation,
   einer Übergangslogik, die aus dem Datenpfad und dem Metadatenpfad einen Ergebniswert und einen Übergangszustand bestimmt, und
   einer Freigabelogik, die eine Gültigkeit des Ergebniswertes nur dann freigibt, wenn eine vorgegebene Menge maschinenprüfbarer Übergangsbedingungen erfüllt ist, wobei die Freigabelogik bei wenigstens einer nicht erfüllten erforderlichen Übergangsbedingung einen nicht freigegebenen Haltezustand erzeugt.

2. Hardware-Übergangseinheit nach Anspruch 1, wobei die Übergangsbedingungen wenigstens eine Autoritätsinformation umfassen.

3. Hardware-Übergangseinheit nach Anspruch 1 oder 2, wobei die Übergangsbedingungen eine Unterscheidungsinformation zur Unterscheidung des gebundenen Zustandsübergangs von einem anderen Zustandsübergang umfassen.

4. Hardware-Übergangseinheit nach einem der vorhergehenden Ansprüche, wobei eine Driftinformation bei angezeigter Drift die Ergebnisfreigabe sperrt.

5. Hardware-Übergangseinheit nach einem der vorhergehenden Ansprüche, wobei der Übergangszustand wenigstens einen Beobachtungszustand, einen Haltezustand und einen Fortsetzungszustand kodieren kann.

6. Hardware-Übergangseinheit nach einem der vorhergehenden Ansprüche, realisiert als synthetisierbare Logik in einem FPGA oder ASIC.

7. Rechnersystem mit wenigstens einer Hardware-Übergangseinheit nach einem der Ansprüche 1 bis 6 und einer Kommunikationsschnittstelle, die eine dem Zustandsübergang zugeordnete Gegenstandsidentität gemeinsam mit Nutzdaten überträgt.

8. Rechnersystem nach Anspruch 7, wobei eine Bestätigung des Empfangs oder der Integrität der übertragenen Daten getrennt von einer Bestätigung eines durch die Daten beabsichtigten nachgelagerten Zustands geführt wird.

9. Rechnersystem nach Anspruch 7 oder 8, mit einem Rücklesepfad zur Erfassung eines nach Ausführung beobachteten Folgezustands und einer Akzeptanzlogik zur Prüfung des Folgezustands gegen wenigstens eine Akzeptanzbedingung.

10. Rechnersystem nach Anspruch 9, wobei ein terminaler Abschlusszustand des gebundenen Zustandsübergangs erst nach erfolgreicher Prüfung des zurückgelesenen Folgezustands freigegeben wird.

11. Verfahren zum Steuern eines digitalen Zustandsübergangs, umfassend:
    Binden eines auszuführenden Zustandsübergangs an eine Gegenstandsidentität;
    Erfassen wenigstens einer maschinenprüfbaren Übergangsbedingung;
    Verarbeiten von Nutzdaten;
    Bestimmen eines Übergangszustands; und
    Sperren der Gültigkeit eines Verarbeitungsergebnisses, solange wenigstens eine erforderliche Übergangsbedingung nicht erfüllt ist.

12. Verfahren nach Anspruch 11, ferner umfassend das Beobachten eines durch die Verarbeitung erzeugten Folgezustands, Rücklesen des Folgezustands über einen logisch von der Ausführung getrennten Rücklesevorgang und Freigeben eines terminalen Abschlusszustands erst nach Prüfung einer Akzeptanzbedingung.

13. Verfahren nach Anspruch 11 oder 12, wobei eine Transportbestätigung nicht als terminale Bestätigung des beabsichtigten Zustandsübergangs verwendet wird.

14. Verfahren nach einem der Ansprüche 11 bis 13, wobei ein akzeptierter Folgezustand für einen nachfolgenden Zustandsübergang erneut an dessen Gegenstandsidentität gebunden wird.
