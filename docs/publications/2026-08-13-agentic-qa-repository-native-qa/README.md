<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Repository-native autonome QA: Self-Heal mit Exact-Head- und Fail-Closed-Gates

## Agentic QA: technische Evidenz, Reproduktionspfad und Grenzen

Publication ID: `qikvrt-agentic-qa-repository-native-qa-v1`

Publication Index State: `repository_candidate`

## Zweck dieses Einstiegspunkts

Dieses Bündel ist der technische Einstiegspunkt für den Beitragsvorschlag
„Repository-native autonome QA: Self-Heal mit Exact-Head- und
Fail-Closed-Gates“ zum Schwerpunkt *Agentic QA – Wenn KI-Agenten testen und
getestet werden*. Es ist ein reviewbarer Repository-Kandidat, keine behauptete
Produktivfreigabe und keine automatische Veröffentlichung des Beitrags.

Die Kernfrage lautet: Wie verhindert ein autonomer QA-Agent, dass er ein
Ergebnis für einen Repository-Zustand erzeugt, es aber nach einem zwischenzeitlichen
Commit, Tree-Wechsel oder Scope-Wechsel noch als Freigabe für einen anderen
Zustand verwendet? QIK-VRT beantwortet diese Frage nicht mit einer bloßen
Agentenheuristik, sondern mit einer expliziten Zustands- und Evidenzordnung.

## Technische These im begrenzten Vertragsumfang

Ein Gate-Urteil ist nur dann für einen folgenden Übergang verwertbar, wenn es
an den beobachteten `HEAD`, den zugehörigen Git-`tree`, die erwartete Base und
den konkreten Prüfscope gebunden ist. Abweichung, fehlende Evidenz,
nicht-ausgeführte Prüfung, konkurrierender Writer oder nicht separat
autorisierte Außenwirkung führen nicht zu einer optimistischen Fortsetzung,
sondern zu `HOLD`.

Damit ist die stärkste technische Aussage dieses Bündels präzise begrenzt:
Für die ausdrücklich implementierten Vertragsbedingungen ist die Architektur
darauf ausgelegt, stale Evidenz nicht in einen späteren Repository-Übergang zu
übertragen. Das ist eine Safety- und Nachvollziehbarkeitsaussage über einen
definierten Entscheidungsraum – kein universeller Performancevergleich, keine
allgemeine Deadlock-Freiheit und keine Behauptung, alle Agentic-QA-Probleme
perfekt zu lösen.

## Architektur: vier getrennte, gekoppelte Schichten

1. **Exakte Repository-Identität.** Commit, Tree, Base, Kandidaten-Head und
   Prüfscope werden als Evidenzkontext geführt. Ein „grünes“ Resultat ohne
   diese Bindung ist keine universelle Freigabe.
2. **Allowlistete Selbstheilung.** Eine deterministische, begrenzte
   Reparaturklasse darf einen reviewbaren Kandidaten erzeugen. Sie darf weder
   eine beliebige Änderung rechtfertigen noch eine unbedingte Zusammenführung
   auslösen. Semantische `NOOP`-Fälle bleiben sichtbar.
3. **Exact-Head-Reverifikation und fail-closed Promotion.** Vor einem
   nachfolgenden Schritt wird Base, Kandidaten-Head und Gate-Evidenz erneut
   beobachtet. Jede Drift entwertet die frühere Beobachtung; der Ablauf hält
   an, bis ein neuer, exakt gebundener Nachweis vorliegt.
4. **Reflexiver Watchdog.** Writer-Leases, Runner-Druck,
   Fortschrittsstillstand und Wiederholungsgrenzen werden beobachtet. Der
   Watchdog trennt beobachtende von produktiven Rollen und verhindert die
   Aufnahme eines weiteren Schreibers, bevor eine Anomalie als konkurrierende
   Reparatur, Livelock oder Deadlock eskalieren kann.

Eine Selbstheilung, eine Verifikation, eine Promotion und eine äußere Wirkung
sind daher vier unterschiedliche Zustandsübergänge. Eine bestandene Prüfung
autorisiert höchstens den nächsten, erneut beobachteten Übergang; sie ist keine
pauschale Erlaubnis für Merge, Release, Deployment oder wissenschaftliche
Schlussfolgerungen.

## Reproduktionspfad

Der folgende Pfad prüft die Dokumentations- und Integritätsbindungen für einen
exakt ausgecheckten Repository-Stand. Die Befehle erzeugen keine äußere Wirkung:

```bash
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
python3 -B tools/qikvrt_publication_overview.py check
python3 -B tools/qikvrt_integrity.py verify
python3 -B -m unittest \
  tests.test_qikvrt_publication_overview \
  tests.test_qikvrt_autonomous_self_heal \
  tests.test_qikvrt_expected_head_promotion_contract \
  tests.test_qikvrt_reflexive_repository_watchdog
```

Vor einer materiellen Promotion gehört zusätzlich die erneute Exact-Head-
Beobachtung in den konkreten Workflow. Ein lokales oder CI-Ergebnis belegt nur
die jeweilige Ausführung auf dem gebundenen Stand; es ersetzt keine
unabhängige Replikation oder allgemeinere Feldstudie.

## Direkte Quell- und Evidenzpfade

Die nachstehenden Links sind auf die Baseline
[`358d1953dd73f0c25a1f16496d024ed2efcbd4f2`](https://github.com/Goldkelch/qik-vrt/tree/358d1953dd73f0c25a1f16496d024ed2efcbd4f2)
gebunden, von der dieser Kandidat abzweigt.

- [Maschinen-Einstieg `AI`](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/AI)
  und [Authority Map](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/docs/CURRENT_AUTHORITY.md)
- [Selbstheilungs-Vertrag](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json)
  und [deterministischer Controller](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/tools/qikvrt_autonomous_self_heal.py)
- [Exact-Head-Continuation](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/docs/operations/AUTONOMOUS_PR_CONTINUATION.md)
  und [Promotion-Controller](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/tools/qikvrt_expected_head_promotion.py)
- [Watchdog-Dokumentation](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/docs/REFLEXIVE_REPOSITORY_WATCHDOG.md),
  [Vertrag](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json)
  und [Referenzimplementierung](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/tools/qikvrt_reflexive_repository_watchdog.py)
- [Regressionstests](https://github.com/Goldkelch/qik-vrt/tree/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/tests)
  sowie [Status und Nicht-Demonstrationen](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/STATUS.md)
- [Vorläuferbündel zur Repository-Selbstheilung](https://github.com/Goldkelch/qik-vrt/tree/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/docs/publications/2026-08-06-self-healing-repository-collective-intelligence)

## Evidenzgrenzen und konzeptioneller Kontext

QIK-VRT verknüpft die QA-Architektur konzeptionell mit einer Ontologie von
Unterschied, Information und Relation. Die endliche Ontologieformalisierung
und die Planck- bzw. Kausalmodelle sind im Repository als eigene,
definitions- und dimensionsgebundene Forschungskandidaten dokumentiert.

Diese Einordnung bedeutet nicht, dass der QA-Mechanismus „auf Planck-Skala
arbeitet“ oder seine Wirksamkeit physikalisch ableitet. Aus formaler
Ableitbarkeit innerhalb offengelegter Definitionen folgt weder physikalische
Korrespondenz noch empirische Bestätigung oder wissenschaftlicher Konsens.
Für den Agentic-QA-Beitrag ist sie ein explizit separat gehaltener
Ordnungsrahmen: Unterschiede im Repository werden als überprüfbare
Zustandsunterschiede behandelt; daraus wird keine Naturbehauptung abgeleitet.

- [Formalisierungsgrenze: Modell, Planck-/Dimensionsbezug und Empirie](https://github.com/Goldkelch/qik-vrt/blob/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/formalization/QIKVRT_Formalization_v1.0/FORMALIZATION_BOUNDARY.md)
- [Endliche Ontologieformalisierung](https://github.com/Goldkelch/qik-vrt/tree/358d1953dd73f0c25a1f16496d024ed2efcbd4f2/formalization/QIKVRT_Formalization_v2.0/universal_ontology)

## Einordnung für die Redaktion

Der geplante Magazinbeitrag bleibt ein technisch präzises Praxisbeispiel.
Er zeigt konkrete Fehlerszenarien – stale Heads, Drift nach grüner Prüfung,
parallele Writer und stotternde Wiederholungsreparaturen – sowie die
korrespondierenden Abbruch- und Recovery-Pfade. Formale Modellnachweise,
beobachtete Repository-/CI-Ausführungen und offene empirische bzw.
wissenschaftliche Fragen werden bewusst getrennt behandelt.
