# Erwartungen, Wetten, Wirkung und Recht

Dieses reproduzierbare Dossier veröffentlicht drei zusammengehörige Artikel von Ingolf Lohmann und eine explizite Autorenerklärung:

1. [Die Wahrheit braucht keine Verschwörungstheorie](Die_Wahrheit_braucht_keine_Verschwoerungstheorie.txt)
2. [Wenn Erwartungen handelbar werden](WENN_ERWARTUNGEN_HANDELBAR_WERDEN_DE.md)
3. [Wenn aus einer Wette eine Tat wird](WENN_AUS_EINER_WETTE_EINE_TAT_WIRD_DE.md)
4. [Autorenerklärung und Evidenzgrenze](AUTORENERKLAERUNG_UND_EVIDENZGRENZE.md)

## Zentrale Aussage und Grenze

Ingolf Lohmann erklärt, dass er die kombinierte Hypothese finanzieller beziehungsweise wettähnlicher Positionen und daraus entstandener realer Einflussanreize unter den von ihm gegenwärtig erwogenen Möglichkeiten für die wahrscheinlichste Erklärung hält. Das Dossier veröffentlicht diese Aussage vollständig und nachvollziehbar. Es gibt sie nicht als unabhängig bestätigte wissenschaftliche Schlussfolgerung aus: Ein konkreter Markt, ein Wettender, ein Zahlungsfluss, ein Auftraggeber, ein Ausführender, eine geschlossene Kausalkette, die universelle Prognoseüberlegenheit von QIK-VRT oder die Schuld einer bestimmten Person sind hier nicht nachgewiesen.

Die Artikel erklären, warum der Autor seine Hypothese für untersuchenswert hält, welche unterscheidbaren Spuren sie bestätigen oder widerlegen könnten, wie QIK-VRT gegen Vergleichssysteme getestet werden müsste und welche rechtlichen Folgen nur unter nachgewiesenen tatsächlichen Voraussetzungen in Betracht kämen.

## Reproduzierbare Prüfung

Aus dem Repository-Root ausführen:

```sh
python3 -B docs/publications/2026-09-19-truth-needs-no-conspiracy-theory/verify_publication_scope.py
python3 -B tools/qikvrt_zenodo_machine_proof.py --proof-bundle docs/publications/2026-09-19-truth-needs-no-conspiracy-theory/MACHINE_PROOF_BUNDLE.json
python3 -B tools/qikvrt_integrity.py verify
```

Die erste Prüfung bindet die exakten Bytes aller vier Kandidatendateien, inventarisiert jede nichtleere Inhaltszeile und testet negative Grenzfälle. Die zweite prüft das unveränderte aktive v2-Machine-Proof-Gate. Dessen schemafestes `zenodo_upload_authorized` ist ausschließlich der Name eines technischen Teil-Gates. Es ersetzt nicht die separate, natürliche, kandidaten- und hashgebundene Owner-Autorisierung.

`PUBLICATION_CONTROL_PENDING.json` und `AUTHORIZE_EXACT_UPLOAD.txt` sind Repository-Kontrollmaterial und gehören nicht zum vorgesehenen Upload-Dateisatz. Solange die dort genannte exakte Autorisierungszeile nicht nach Rückgabe dieses Kandidaten erteilt und verbraucht wurde, sind Zenodo-Publikation, öffentlicher Byte-Readback, Main-Promotion und `DONE` ausdrücklich nicht behauptet. Vorgängerprüfungen werden nicht auf diese Fassung übertragen.
