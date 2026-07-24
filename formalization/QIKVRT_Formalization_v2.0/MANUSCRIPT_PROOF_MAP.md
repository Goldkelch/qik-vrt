# Manuscript proof map

This map is deterministically generated from the locked 62-page TeX source 
and the completed v2 claim graph. `KERNEL_CHECKED` denotes an exact 
source-bound Lean proposition. `CONDITIONAL_CHECKED` denotes a kernel proof 
whose additional assumptions are explicit in the Lean type; it is not an 
unconditional claim about physical reality.

## Coverage summary

| Item | Coverage |
|---|---:|
| Formal LaTeX environments inventoried | 40 / 40 |
| Definitions source-bound and kernel-checked | 20 / 20 |
| Theorem-like environments formally closed | 20 / 20 |
| Remarks inventoried | 5 / 5 |
| Explicit manuscript proof blocks attached | 17 / 17 |
| Appendix matrix rows epistemically classified | 34 / 34 |
| Strong Lean bindings | 42 |
| Conditional checked bindings | 6 |
| Open definition nodes | 0 |
| Open theorem/conditional nodes | 0 |

## Formal environments

| Environment | Type and title | PDF page | TeX lines | Claim status |
|---|---|---:|---:|---|
| `ENV-DEF-001` | definition: Quadratische Iteration | 8 | 403–421 | `DEF-001: KERNEL_CHECKED` |
| `ENV-DEF-002` | definition: Relatives Komplement | 9 | 423–432 | `DEF-002: KERNEL_CHECKED` |
| `ENV-THM-001` | satz: Vollständige komplementäre Zerlegung | 9 | 441–457 | `SET-001: KERNEL_CHECKED` |
| `ENV-DEF-003` | definition: Fluchtzeit | 9 | 474–483 | `DEF-003: KERNEL_CHECKED` |
| `ENV-THM-002` | lemma: Fluchtradius | 10 | 485–489 | `ESC-004: CONDITIONAL_CHECKED` |
| `ENV-THM-003` | korollar: — | 10 | 507–515 | `ESC-005: CONDITIONAL_CHECKED` |
| `ENV-DEF-004` | definition: Endliche Escape-Mengen | 10 | 517–522 | `DEF-004: KERNEL_CHECKED` |
| `ENV-THM-004` | satz: Stufenweise Rekonstruktion des Komplements | 10 | 524–530 | `ESC-003: CONDITIONAL_CHECKED` |
| `ENV-DEF-005` | definition: Mandelbrot-Modelluniversum | 10 | 568–572 | `DEF-005: KERNEL_CHECKED` |
| `ENV-DEF-006` | definition: Korrespondenzabbildung | 11 | 586–599 | `DEF-006: KERNEL_CHECKED` |
| `ENV-THM-005` | satz: Raumzeitliche Urbildpartition | 11 | 601–607 | `MAP-001: KERNEL_CHECKED` |
| `ENV-DEF-007` | definition: Endliche \(\eps\)-Quantisierbarkeit | 12 | 652–664 | `DEF-007: KERNEL_CHECKED` |
| `ENV-THM-006` | satz: Quantisierbarkeit beschränkter euklidischer Bereiche | 12 | 666–670 | `QUA-004: CONDITIONAL_CHECKED` |
| `ENV-THM-007` | korollar: Endlichdimensionale normierte Räume | 12 | 687–691 | `QUA-005: CONDITIONAL_CHECKED` |
| `ENV-THM-008` | proposition: Quantisierbarkeit impliziert keine ontische Diskretheit | 13 | 731–736 | `QUA-003: KERNEL_CHECKED`, `QUA-003A: KERNEL_CHECKED` |
| `ENV-THM-009` | satz: Dimensionsunabhängigkeit | 13 | 767–773 | `SET-003: KERNEL_CHECKED` |
| `ENV-THM-010` | satz: Komplementerhaltung unter Abbildungen | 13 | 780–798 | `MAP-003: KERNEL_CHECKED` |
| `ENV-DEF-008` | definition: Erweiterte Mandelbrot-Dynamik | 14 | 838–863 | `DEF-008: KERNEL_CHECKED` |
| `ENV-DEF-009` | definition: Trajektorienraum und Shift | 15 | 869–879 | `DEF-009: KERNEL_CHECKED` |
| `ENV-DEF-010` | definition: Exakte Trajektorienklassifikation | 15 | 881–898 | `DEF-010: KERNEL_CHECKED` |
| `ENV-THM-011` | satz: Shift-Invarianz der exakten Klassifikation | 15 | 900–906 | `GAT-003: KERNEL_CHECKED` |
| `ENV-DEF-011` | definition: Zulässige PASS-Zertifikate | 16 | 946–957 | `DEF-011: KERNEL_CHECKED` |
| `ENV-DEF-012` | definition: Endliches Anschlussgate | 16 | 959–974 | `DEF-012: KERNEL_CHECKED` |
| `ENV-THM-012` | satz: Korrektheit und monotone Verfeinerung | 16 | 979–991 | `GAT-004: KERNEL_CHECKED` |
| `ENV-THM-013` | satz: Exterior-Vollständigkeit und bedingte Gesamtvollständigkeit | 16 | 1010–1024 | `GAT-005: KERNEL_CHECKED`, `GAT-006: KERNEL_CHECKED` |
| `ENV-THM-014` | satz: Grenze und Statusdiskontinuität | 17 | 1064–1076 | `GAT-007: KERNEL_CHECKED` |
| `ENV-THM-015` | proposition: Epistemische, nicht dynamische Rückbestimmung | 18 | 1101–1107 | `RET-011: KERNEL_CHECKED` |
| `ENV-DEF-013` | definition: Mandelbrot-Prozessmodelluniversum | 18 | 1129–1137 | `DEF-013: KERNEL_CHECKED` |
| `ENV-DEF-014` | definition: Allgemeines Wirkraummodell | 19 | 1169–1185 | `DEF-014: KERNEL_CHECKED` |
| `ENV-DEF-015` | definition: Dynamische Semikonjugation | 19 | 1200–1213 | `DEF-015: KERNEL_CHECKED` |
| `ENV-DEF-016` | definition: Gate-erhaltende Prozessabbildung | 19 | 1219–1231 | `DEF-016: KERNEL_CHECKED` |
| `ENV-THM-016` | satz: Faktorisierungskriterium für Gate-Erhaltung | 19 | 1233–1242 | `GAT-002: KERNEL_CHECKED` |
| `ENV-THM-017` | proposition: Dimensionshomogenität | 23 | 1483–1488 | `DIM-006: CONDITIONAL_CHECKED`, `DIM-006A: KERNEL_CHECKED` |
| `ENV-THM-018` | proposition: Lorentz-Intervall ist keine Abstandsfunktion | 24 | 1560–1564 | `DIM-007: KERNEL_CHECKED`, `DIM-007A: KERNEL_CHECKED` |
| `ENV-DEF-017` | definition: Semantische Rückbestimmung | 34 | 2199–2203 | `DEF-017: KERNEL_CHECKED` |
| `ENV-DEF-018` | definition: Physikalische Retrokausalität | 34 | 2205–2211 | `DEF-018: KERNEL_CHECKED` |
| `ENV-DEF-019` | definition: Rückwärtssignalisierung | 34 | 2213–2218 | `DEF-019: KERNEL_CHECKED` |
| `ENV-THM-019` | satz: Kausale Autonomie früher Präfixe im definierten Prozess | 42 | 2672–2681 | `RET-011: KERNEL_CHECKED` |
| `ENV-THM-020` | korollar: Reklassifikation ohne Überschreiben | 42 | 2703–2710 | `RET-011: KERNEL_CHECKED` |
| `ENV-DEF-020` | definition: Universales Schöpfungsprinzip, strukturelle Lesart | 49 | 3143–3147 | `DEF-020: KERNEL_CHECKED` |

## Strong source-bound Lean bindings

| Claim | Status | Scope | Batch | Lean theorem | Environment(s) |
|---|---|---|---|---|---|
| `DEF-001` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF001_checked` | `ENV-DEF-001` |
| `DEF-002` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF002_checked` | `ENV-DEF-002` |
| `DEF-003` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF003_checked` | `ENV-DEF-003` |
| `DEF-004` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF004_checked` | `ENV-DEF-004` |
| `DEF-005` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF005_checked` | `ENV-DEF-005` |
| `DEF-006` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF006_checked` | `ENV-DEF-006` |
| `DEF-007` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF007_checked` | `ENV-DEF-007` |
| `DEF-008` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF008_checked` | `ENV-DEF-008` |
| `DEF-009` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF009_checked` | `ENV-DEF-009` |
| `DEF-010` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF010_checked` | `ENV-DEF-010` |
| `DEF-011` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF011_checked` | `ENV-DEF-011` |
| `DEF-012` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF012_checked` | `ENV-DEF-012` |
| `DEF-013` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF013_checked` | `ENV-DEF-013` |
| `DEF-014` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF014_checked` | `ENV-DEF-014` |
| `DEF-015` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF015_checked` | `ENV-DEF-015` |
| `DEF-016` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF016_checked` | `ENV-DEF-016` |
| `DEF-017` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF017_checked` | `ENV-DEF-017` |
| `DEF-018` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF018_checked` | `ENV-DEF-018` |
| `DEF-019` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF019_checked` | `ENV-DEF-019` |
| `DEF-020` | `KERNEL_CHECKED` | `DEFINITION_BINDING` | `Completion-Definitions` | `QIKVRT.V2.Definitions.DEF020_checked` | `ENV-DEF-020` |
| `SET-001` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch02-Elementary` | `QIKVRT.V2.Class.SET001_checked` | `ENV-THM-001` |
| `ESC-004` | `CONDITIONAL_CHECKED` | `CONDITIONAL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.ESC004_checked` | `ENV-THM-002` |
| `ESC-005` | `CONDITIONAL_CHECKED` | `CONDITIONAL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.ESC005_checked` | `ENV-THM-003` |
| `ESC-003` | `CONDITIONAL_CHECKED` | `CONDITIONAL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.ESC003_checked` | `ENV-THM-004` |
| `MAP-001` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch02-Elementary` | `QIKVRT.V2.Class.MAP001_checked` | `ENV-THM-005` |
| `QUA-004` | `CONDITIONAL_CHECKED` | `CONDITIONAL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.QUA004_checked` | `ENV-THM-006` |
| `QUA-005` | `CONDITIONAL_CHECKED` | `CONDITIONAL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.QUA005_checked` | `ENV-THM-007` |
| `QUA-003` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.QUA003_checked` | `ENV-THM-008` |
| `QUA-003A` | `KERNEL_CHECKED` | `SOURCE_SUBCLAIM` | `Batch02-Counterexamples` | `QIKVRT.V2.QUA003A_prefix_checked` | `ENV-THM-008` |
| `SET-003` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch02-Elementary` | `QIKVRT.V2.Class.SET003_checked` | `ENV-THM-009` |
| `MAP-003` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch01A` | `QIKVRT.V2.Class.MAP003_checked` | `ENV-THM-010` |
| `GAT-003` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch04` | `QIKVRT.V2.Trajectory.GAT003_checked` | `ENV-THM-011` |
| `GAT-004` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch01A` | `QIKVRT.V2.GAT004_checked` | `ENV-THM-012` |
| `GAT-005` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch01A` | `QIKVRT.V2.GAT005_checked` | `ENV-THM-013` |
| `GAT-006` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch01A` | `QIKVRT.V2.GAT006_checked` | `ENV-THM-013` |
| `GAT-007` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.GAT007_checked` | `ENV-THM-014` |
| `RET-011` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch01A` | `QIKVRT.V2.RET011_checked` | `ENV-THM-015`, `ENV-THM-019`, `ENV-THM-020` |
| `GAT-002` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Batch02-Factorization` | `QIKVRT.V2.GAT002_checked` | `ENV-THM-016` |
| `DIM-006` | `CONDITIONAL_CHECKED` | `CONDITIONAL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.DIM006_checked` | `ENV-THM-017` |
| `DIM-006A` | `KERNEL_CHECKED` | `SOURCE_SUBCLAIM` | `Batch02-Dimensions` | `QIKVRT.V2.DIM006A_additive_checked` | `ENV-THM-017` |
| `DIM-007` | `KERNEL_CHECKED` | `FULL_ENVIRONMENT` | `Completion-Theorems` | `QIKVRT.V2.Completion.DIM007_checked` | `ENV-THM-018` |
| `DIM-007A` | `KERNEL_CHECKED` | `SOURCE_SUBCLAIM` | `Batch02-Counterexamples` | `QIKVRT.V2.DIM007A_countermodel_checked` | `ENV-THM-018` |

## Explicit conditional boundaries

- `ESC-004`: For the quadratic complex iteration, modulus greater than two is an escape certificate. Assumptions are explicit in `QIKVRT.V2.Completion.ESC004Statement`.
- `ESC-005`: The escape-radius criterion characterizes the exterior by a finite escape witness. Assumptions are explicit in `QIKVRT.V2.Completion.ESC005Statement`.
- `ESC-003`: The union of all finite escape stages reconstructs the complement. Assumptions are explicit in `QIKVRT.V2.Completion.ESC003Statement`.
- `QUA-004`: Bounded subsets of Euclidean space are finitely epsilon-quantizable. Assumptions are explicit in `QIKVRT.V2.Completion.QUA004Statement`.
- `QUA-005`: Bounded subsets of finite-dimensional normed spaces are finitely epsilon-quantizable. Assumptions are explicit in `QIKVRT.V2.Completion.QUA005Statement`.
- `DIM-006`: Every additive physical equation must be dimensionally homogeneous. Assumptions are explicit in `QIKVRT.V2.Completion.DIM006Statement`.

## Context-only remarks

| Environment | Title | PDF page | TeX lines |
|---|---|---:|---:|
| `ENV-REM-001` | Was ein endliches Bild tatsächlich beweist | 10 | 540–556 |
| `ENV-REM-002` | Kein allgemeiner Orbit-Fixpunkt | 15 | 927–936 |
| `ENV-REM-003` | — | 17 | 1052–1060 |
| `ENV-REM-004` | Dimensionsrichtigkeit zeichnet keine Abbildung aus | 25 | 1622–1632 |
| `ENV-REM-005` | Koordinaten- und Kausalrichtung | 36 | 2305–2311 |

## Appendix matrix classification

| Epistemic category | Rows | Machine theorem binding? |
|---|---:|---|
| `MATHEMATICAL` | 11 | only with an exact source-bound formal proposition |
| `CONDITIONAL` | 5 | only with an exact source-bound formal proposition |
| `BACKGROUND` | 4 | no |
| `EMPIRICAL` | 6 | no |
| `INTERPRETIVE` | 7 | no |
| `NORMATIVE` | 1 | no |

## Completion boundary

No formal definition or theorem node remains `PENDING`. This is a 
completion of the manuscript's formal environment graph, not an empirical 
confirmation of physical, metaphysical, spiritual, retrocausal, or 
quantum-gravitational interpretations. Conditional mathematical statements 
remain conditional, and all such assumptions are present in their Lean types.
