<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT Autonomous Orchestrator V2

## Zweck

V2 ergänzt die vorhandene bounded self-healing Schicht um einen dauerhaften, typisierten Arbeitsplan. Das Repository bearbeitet damit selbstständig alle ausdrücklich deklarierten, deterministischen und reversiblen repositoryinternen Schritte. Es erzeugt pro Lauf höchstens einen Kandidaten, prüft dessen exakten Head und promoviert ihn nur unter der vorhandenen erwarteten-Head-Bindung.

Der Orchestrator ist kein allgemeiner autonomer Agent mit unbeschränkten Rechten. Er ist eine fail-closed Zustandsmaschine:

```text
WORK_QUEUE
→ SELECT_ONE_ELIGIBLE_UNIT
→ MATERIALIZE_REVIEW_BRANCH
→ EXACT_HEAD_FULL_SUITE
→ EXPECTED_HEAD_BOUND_PROMOTION
→ CONTINUE_QUEUE
```

## Warum die bisherige Automation nicht weiterlief

Die vorhandene V1-Self-Healing-Schicht behandelt absichtlich nur zwei Fehlerklassen:

1. Drift der Anticipation-Projektionen;
2. veraltete repositorynative Integrität.

Sie besitzt keine dauerhafte Warteschlange für wissenschaftliche Kandidaten, keine Artifact-Ingestion, keine globale Kandidatenlease und keinen Handler, der aus einem erfolgreichen Workflow-Artefakt den nächsten kanonischen Repositoryzustand konstruiert. Außerdem erzeugen mit dem normalen `GITHUB_TOKEN` angelegte Pull Requests nicht zuverlässig eine rekursive Workflowkette. V2 löst das durch eine explizite `workflow_dispatch`-Validierung des exakten Kandidaten-Heads.

## Fähigkeiten

Automatisch bearbeitbar sind insbesondere:

- exakte GitHub- und Workflowbeobachtung;
- Download und Hashprüfung gebundener Actions-Artefakte;
- Persistierung formaler Kernel-Receipts und roher ASR-Evidenz;
- deterministische Aktualisierung von Indizes, Manifesten und Prüfsummen;
- Erzeugung typisierter Formalisierungs- und Forschungsobligationen;
- Draft-PR-Erzeugung, vollständige Exact-Head-Prüfung und erwartete-Head-Promotion;
- idempotentes Schließen exakt gebundener, vollständig supersedierter Transport- oder Proxy-PRs;
- Fortsetzung mit dem nächsten Work Unit nach erfolgreicher Promotion.

## Harte Grenzen

Die folgenden Zustände werden nicht als Fehler versteckt und niemals automatisch als abgeschlossen ausgegeben:

| Zustand | Bedeutung |
|---|---|
| `WAITING_HUMAN` | Wortlautprüfung, Peer Review oder andere menschliche Urteile |
| `WAITING_EMPIRICAL` | Messung, reale Daten oder unabhängige Replikation |
| `WAITING_CONFIGURATION` | fehlende, ausdrücklich benannte Repositorykonfiguration oder Credential-Bindung |
| `WAITING_EXTERNAL_AUTH` | Zenodo, IETF, Release, Deployment oder ein anderer irreversibler externer Effekt |

Insbesondere gilt:

```text
ASR_COMPLETE ≠ VERBATIM_VERIFIED
KERNEL_ACCEPTED ≠ PHYSICAL_CORRESPONDENCE
ZENODO_PERSISTED ≠ SCIENTIFIC_TRUTH
WORKFLOW_SUCCESS ≠ PASS
```

## Serialisierung und Promotion

Die Workflow-Concurrency-Gruppe lautet für alle V2-Schreiboperationen:

```text
qikvrt-repository-writer-${{ github.repository }}
```

Ein Kandidat darf nur promoviert werden, wenn gleichzeitig gilt:

1. `CURRENT_BASE_REOBSERVED`
2. `HEAD_UNCHANGED`
3. `DIFF_ALLOWLISTED`
4. `NO_EXTERNAL_EFFECT`
5. `ALL_APPLICABLE_GATES_TERMINAL_GREEN`
6. `NO_COMPETING_WRITER`

Unbedingtes Auto-Merge bleibt verboten. Die erlaubte Promotion ist an das Work Unit, den beobachteten Main-Head, den unveränderten Kandidaten-Head und den vollständigen Exact-Head-Status gebunden.

## Initiale Arbeitswarteschlange

Die erste V2-Warteschlange enthält:

- QCE-Kernel-Receipt und Publikationsindex dauerhaft integrieren;
- A08/A09-ASR-Artefakte vor Ablauf sichern und für menschliche Prüfung disponieren;
- einen einheitlichen typisierten Ontologie- und Forschungsobligationskern materialisieren;
- supersedierte QCE-/Audio-Transport-PRs exakt und ohne Merge schließen;
- Mirror-Port bei vorhandener Credential-Konfiguration;
- menschliche Akustikprüfung, physikalische Korrespondenz und Zenodo-Finalpublikation als explizite Wartezustände.

## Wahrheitsgrenze

V2 maximiert selbstständige repositoryinterne Abarbeitung. Es kann jedoch weder einen menschlich bestätigten Wortlaut, reale Messdaten, unabhängige wissenschaftliche Reproduktion noch eine naturwissenschaftliche Korrespondenz erzeugen. Diese Grenzen bleiben sichtbar und blockieren jede falsche Totalisierung.

```text
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
```
