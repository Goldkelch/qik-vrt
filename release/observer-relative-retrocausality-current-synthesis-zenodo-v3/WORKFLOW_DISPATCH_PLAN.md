<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Nicht ausführbarer v3-Workflowplan

Dieser SOURCE-Kandidat enthält absichtlich keinen v3-Publish-Workflow.

Ein späterer Workflow muss mindestens:

- ausschließlich `workflow_dispatch` verwenden;
- Repository, `main`, actor und triggering actor exakt prüfen;
- `PUBLISH_OBSERVER_RELATIVE_RETROCAUSALITY_ZENODO_V3` verlangen;
- feste, später bekannte SOURCE- und EXECUTION-Heads auschecken;
- exakt 23 Uploadpfade und den erlaubten SOURCE→EXECUTION-Delta prüfen;
- v2- und v3-Replay-/Receipt-Grenzen vor dem Effekt prüfen;
- dieselbe Concurrency-Gruppe wie v2 verwenden;
- eine vorab geschützte, v3-spezifische Zenodo-Produktionsumgebung benutzen;
- Receipt/Recovery-Evidenz auf einem separaten PR persistieren.

Das bestehende, derzeit unkonfigurierte `zenodo-production` darf nicht durch
einen Dispatch implizit erzeugt werden.
