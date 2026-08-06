<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Autonomer Ontologie-Schließungsoperator

## Zweck

Der Operator arbeitet alle **maschinenentscheidbaren** Schritte der Ontologie-Schließung ohne wiederholte Chat-Interaktion ab. Er beobachtet GitHub-Ereignisse, wählt exakt eine berechtigte Arbeitseinheit, erzeugt einen history-preserving Nachfolger über die GitHub-API, persistiert Status und lässt anschließend die normalen Exact-Head-Gates laufen.

## Warum das Repository bisher nicht alles selbst erledigte

Die vorhandenen Bausteine für Self-Healing, Work-Unit-Fallback, Monitoring und Standing Delegation lagen überwiegend in offenen Kandidaten. Auf `main` fehlte ein kanonischer Scheduler, der:

1. offene Arbeitseinheiten priorisiert;
2. bekannte deterministische Fehlerklassen einem ausführbaren Handler zuordnet;
3. sichere Nachfolger statt direkter Main-Writes erzeugt;
4. menschliche, empirische und irreversible Grenzen ausdrücklich **nicht** automatisiert;
5. nach jedem Ergebnis selbstständig den nächsten zulässigen Schritt auswählt.

Diese Lücke schließen `tools/qikvrt_autonomous_ontology_closure.py`, die Workflowdatei und die Queue unter `state/ontology-autonomy/`.

## Automatisierbar

- read-only Reobservation;
- Publikationsindex- und Integritätsregeneration;
- formale Modell- und Axiomläufe;
- Receipt-Persistenz;
- Exact-Head-Verifikation;
- history-preserving Repair- und Successor-PRs;
- Vorbereitung eines Mirror-Ports;
- Schließung vollständig supersedierter Transportträger.

## Nicht durch Repository-Aktivität ersetzbar

- menschliches Anhören und verbatim-Zertifizieren von Audio;
- reale Messungen und Experimente;
- organisatorisch unabhängige Replikation;
- fachwissenschaftlicher Konsens;
- irreversible Zenodo-, IETF-, Release- oder Deployment-Effekte ohne exakte, noch unverbrauchte Autorisierung.

Der Operator kann diese Aufgaben planen, Evidenzanforderungen einfrieren und Ergebnisse prüfen. Er darf ihre Erfüllung nicht erfinden.

## Erste gebundene Arbeitseinheit

Die erste Arbeitseinheit reobserviert den jeweils aktuellen Head von Authority PR `#411`, erzeugt daraus einen history-preserving QCE-Nachfolger und lässt den repositoryeigenen Publikationsgenerator die fehlende Discovery-Abdeckung reparieren. Danach folgen Receipt-Persistenz, A08/A09-Artefaktprüfung und die Zerlegung des einheitlichen Ontologiekerns in endliche formale Arbeitseinheiten.

## Wirkungsschranke

```text
AUTONOMOUS_REPOSITORY_WORK = ENABLED_CANDIDATE
AUTOMATIC_HUMAN_CERTIFICATION = FORBIDDEN
FABRICATED_EMPIRICAL_EVIDENCE = FORBIDDEN
DIRECT_MAIN_WRITE = FORBIDDEN
AUTOMATIC_MERGE = FORBIDDEN_WITHOUT_EXACT_PROMOTION_AUTHORIZATION
ZENODO_PUBLICATION = NOT_AUTHORIZED_BY_THIS_OPERATOR
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
EFFECT_STATE = EFFECT_ACK_CONTINUE
```
