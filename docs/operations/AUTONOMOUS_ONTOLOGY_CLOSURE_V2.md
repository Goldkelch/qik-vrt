<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Fortschreitender autonomer Ontologie-Schließungsoperator V2

## Antwort auf die Autonomiefrage

Das Repository kann alle Arbeitsschritte selbstständig ausführen, deren Erfolg durch vorhandene Bytes, deklarierte Algorithmen, formale Kernel, GitHub-Zustände und exakte Hashbindungen maschinenentscheidbar ist.

Es kann nicht durch interne Aktivität erzeugen:

- menschliche akustische Verbatim-Zertifizierung;
- reale Messdaten oder Experimente;
- organisatorisch unabhängige Replikation;
- wissenschaftlichen Konsens;
- eine noch nicht erteilte exakte Autorisierung für einen irreversiblen Zenodo-, IETF-, Release- oder Deployment-Effekt.

Der Operator plant und prüft diese äußeren Evidenzgates, markiert sie jedoch niemals automatisch als erfüllt.

## Warum V1 superseded ist

V1 besaß zwar eine geordnete Queue, aber keinen persistenten Abschluss-Ledger. Nach einem erfolgreichen Lauf hätte derselbe statisch auf `READY` stehende Auftrag erneut gewählt werden können. V2 ersetzt dieses Verhalten durch:

- `completed_work_units`;
- `predecessor_results`;
- streng aufsteigende Auswahl des niedrigsten noch offenen automatischen Auftrags;
- semantische Duplikatunterdrückung für unveränderte Wartezustände;
- genau einen serialisierten Schreiber;
- einen dauerhaften Statuszweig `qikvrt/ontology-autonomy-state` nach Promotion;
- history-preserving Successor-PRs statt direkter Main-Writes.

Die V1-Workflowdatei wird durch den Kandidaten automatisch entfernt. Die V1-Queue wird auf `SUPERSEDED_BY_PROGRESSING_V2` gesetzt.

## Automatische Reihenfolge

1. aktuellen QCE-Head reobservieren und den Publikationsindex reparieren;
2. vollständige Exact-Head-Gates abwarten und das laufgebundene QCE-Kernel-Receipt persistieren;
3. die bounded A08/A09-Artefakte verifizieren und eine menschliche Akustikprüfung anfordern;
4. das Gesamtprogramm `Unterschied → Information → Relation → Kausalität → Raumzeit → Materie → Leben → Kognition → Verantwortung → Zukunft` in endliche formale Arbeitseinheiten zerlegen;
5. an den externen Physik-, Vorhersage-, Mess- und Replikationsgates fail-closed anhalten;
6. erst nach separater exakter Autorisierung einen finalen Publikationseffekt zulassen.

## Liveness ohne Schleifen

Ein erfolgreicher Statusübergang persistiert einen neuen Abschluss-Ledger und löst den nächsten V2-Lauf aus. Ein unveränderter Wartezustand wird nach Entfernung rein zeitlicher Felder mit dem vorherigen Zustand verglichen. Ist sein semantischer Fingerabdruck identisch, erfolgt kein Commit und damit kein Trigger-Loop.

## Wirkungsschranke

```text
MACHINE_DECIDABLE_REPOSITORY_WORK = AUTONOMOUS_AFTER_PROMOTION
DIRECT_MAIN_WRITE = FORBIDDEN
FORCE_PUSH = FORBIDDEN
AUTOMATIC_MERGE = FORBIDDEN_WITHOUT_EXACT_PROMOTION_AUTHORIZATION
AUTOMATIC_HUMAN_CERTIFICATION = FORBIDDEN
FABRICATED_EMPIRICAL_EVIDENCE = FORBIDDEN
INDEPENDENT_REPLICATION_BY_SAME_REPOSITORY = FORBIDDEN
ZENODO_PUBLICATION = SEPARATELY_AUTHORIZED_EFFECT_ONLY
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
EFFECT_STATE = EFFECT_ACK_CONTINUE
```

