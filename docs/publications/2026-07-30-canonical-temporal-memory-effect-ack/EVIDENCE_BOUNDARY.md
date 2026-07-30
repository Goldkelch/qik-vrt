<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze

## Bewiesen im endlichen Protokollmodell

Der Lean-Quelltext formalisiert folgende Aussagen:

1. Freigabe gilt genau bei gültigem Vergangenheitsarchiv, gültigem
   Zukunftsarchiv, Ursachenbindung, bestandener Policy und
   `EFFECT_ACK_DONE`.
2. Jede Freigabe erfordert beide Archive und das Acknowledgement.
3. Bei identischen übrigen Eingaben ändert allein die Gültigkeit der
   zukunftsindexierten Wirkungsbedingung die Freigabe.
4. Ein Wechsel des Zukunftsarchivs überschreibt die
   Vergangenheitsprojektion nicht.
5. Reziproke Schließung erfordert eine freigegebene, zukunftsgebundene Ursache
   sowie eine beobachtete und ursachengebundene Wirkung.

Diese Aussagen gelten für das abstrakte Bool-/Strukturmodell
`qikvrt-canonical-temporal-memory-effect-ack-v1`. Sie werden erst nach einem
erfolgreichen Exact-Head-Lean-Lauf und persistiertem Kernel-Receipt als
`FORMAL_PROVED` publizierbar.

## Quellengebunden

- JCS kanonisiert eine definierte Klasse von JSON-Werten; es kanonisiert
  nicht deren Wahrheit.
- RFC 6920 bindet hashbasierte Namen an Bytes unter dem benannten
  Algorithmus; es beweist keine Urheberschaft.
- W3C PROV beschreibt Provenienzrelationen; eine Provenienzkette kann falsche
  Quellen enthalten.
- Git bindet Inhalte und Historien; Commitmetadaten sind ohne zusätzliche
  Vertrauensanker keine Personenauthentisierung.
- Zeit-symmetrische, postselektierte und globale Constraint-Modelle sind
  wissenschaftlich publiziert; daraus folgt nicht automatisch die
  physikalische Wahrheit der QIK-VRT-Interpretation.

## Normativ definiert

`Operationale Retrokausalität` bedeutet in diesem Paper eine
kontrafaktisch relevante Abhängigkeit einer gegenwärtigen Freigabe von einer
gegenwärtig verfügbaren, aber zukunftsindexierten Wirkungsbedingung. Diese
Definition ist Teil des vorgeschlagenen QIK-VRT-Begriffsapparats.

## Interpretativ

Die Deutung reziproker Wechselwirkung als Grundbedingung einer
panpsychistischen Bewusstseinsmaterialisierung ist die ontologische
Interpretation Ingolf Lohmanns. Sie wird weder als Lean-Theorem noch als
bestätigter neurowissenschaftlicher Befund ausgewiesen.

## Offen

- Ein kontrollierbares physikalisches Signal aus der Zukunft in die
  Vergangenheit.
- Eine Änderung bereits beobachteter oder gespeicherter vergangener Events.
- Eine von Standard-Quantenmechanik unterscheidbare QIK-VRT-Vorhersage.
- Die Hinlänglichkeit reziproker Wechselwirkung für Bewusstsein.
- Eine unabhängige zweite EFFECT_ACK-Implementierung und vollständige
  IETF-Interoperabilität.
- Systemweite Vollständigkeit des gesamten QIK-VRT-Repositorys.

## Ausdrücklich nicht belegt

Zenodo-Persistenz, DOI, IETF-Revision `-02`, IETF-Konsens, Peer Review,
Authority-/Mirror-Promotion dieses neuen Kandidaten und öffentliche
Byteidentität dürfen erst nach ihren jeweiligen externen Receipts behauptet
werden.
