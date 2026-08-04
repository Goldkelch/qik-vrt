<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Korrektur der zuvor behaupteten Ausführung

Vor dieser Repository-Materialisierung wurde in einem Chat eine Ausführung mit
dem Claim-Namen `R7-RK-001` beschrieben. Diese Beschreibung war keine gültige
Repository-Evidenz.

Insbesondere:

- `r7rk001a9b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0` ist keine gültige
  Git-Objekt-ID, weil sie Zeichen außerhalb des Hexadezimalalphabets enthält;
- die dort genannten SHA-256-Werte waren erkennbare Platzhaltermuster;
- `SHA256_PLATZHALTER` band keine Datei;
- für `STATUS=QUEUED` und `121/121` wurde weder Run-ID noch Workflow-URL
  geliefert;
- die angegebene Bildkennung war kein aufgelöstes Repository-Artefakt;
- aus dem Chattext folgten daher weder Persistenz noch Commit, CI-Erfolg,
  Promotion oder Effect Acknowledgement.

Der Namespace `R7` wird hier nicht wiederverwendet. Im Authority-Repository
existiert bereits ein sachfremder H3-Recovery-Branch mit `R7` im Namen. Die
vorliegende Korrektur verwendet deshalb die eigenständigen Claim-IDs
`VPR-001` bis `VPR-003`.

Diese Notiz verändert den historischen Chattext nicht. Sie fügt einen neuen,
prüfbaren Repository-Record hinzu und hält damit genau die Regel ein, die sie
beschreibt: Korrektur erfolgt additiv, nicht durch rückwirkende Umschreibung.
