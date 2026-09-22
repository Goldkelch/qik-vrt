# Claim–Evidence Matrix: zeitübergreifende Quantenkorrelationen / QIK-VRT

Status: 2026-09-22  
Source: Ingolf Lohmann, *Die wissenschaftliche Realität zeitübergreifender Quantenkorrelationen*, Vorveröffentlichungsfassung 1.0, 2026-08-31.

## Anschlussregel

Diese Matrix ist bidirektional: Sie bewahrt die frühere Aussageebene und bindet sie an den heutigen Evidenzstatus, ohne Ebenen zu substituieren.

`EXPERIMENTAL != FORMAL_PROVED != REPOSITORY_EVIDENCE != INTERPRETATIVE != OPEN`

`TRANSPORT_ACK != EFFECT_ACK`

Ein neuer Repository-, Mess- oder Publikationsstand mutiert den Subject-Status; historische Evidenz bleibt historische Evidenz und wird nicht rückwirkend zu frischer Evidenz.

## Claim–Evidence-Matrix

| ID | Claim | Typ | Beleg in v1.0 | Was damit belegt ist | Was ausdrücklich nicht folgt | Offene Prüfpflicht |
|---|---|---|---|---|---|---|
| Q1 | Zeitübergreifende Quantenkorrelationen sind experimentell beobachtet. | EXPERIMENTAL / Literatur | §§2.1–2.4; Kim et al.; Ma et al.; Megidish et al.; Bienfait et al. | Reproduzierbare Korrelationen über zeitlich getrennte Messkontexte. | Kein frei modulierbarer Rückwärtskanal. | Literatur-/Replikationsstand fortlaufend prüfen. |
| Q2 | Lokale unsortierte Früherstatistik bleibt im Standardformalismus von der späteren Wahl unabhängig. | FORMAL_PROVED | Satz 2.1 | No-signalling in der lokalen Randverteilung. | Konditionierte/joint Verteilungen müssen nicht unabhängig sein. | Annahmen des POVM-Modells explizit halten. |
| Q3 | Retrokausale/zeitsymmetrische Modellklassen sind wissenschaftlich formulierbar. | LITERATURE / INTERPRETATIVE | §3; ABL, Wharton/Argaman, Drummond/Reid | Solche Modellklassen existieren und können Anfangs-/Endbedingungen gemeinsam verwenden. | Weder Einzigkeit noch experimenteller Rückwärtskanal. | Unterscheidende Vorhersagen separat prüfen. |
| Q4 | QIK-VRT trennt Host-, virtuelle, semantische und Evidenzordnung. | FORMAL / ARCHITECTURAL | §4.1 | Definierte Ordnungssemantik. | Keine physische Wirkung vor Ursache. | Implementierung exact-subject-gebunden prüfen. |
| Q5 | Zukunftsindizierung und relative Nachrichtenüberholung sind mit azyklischer Host-Ordnung vereinbar. | FORMAL_PROVED | §4.2, Satz 4.1 | Virtuell/semantisch rückwärts gerichtete Ordnung ohne Host-Kausalzyklus. | Keine Retro-Signalübertragung. | Repository-Tests an exaktem HEAD/TREE. |
| Q6 | Vollständige Receipts erlauben eindeutige Vorgängerrekonstruktion. | FORMAL_PROVED | §4.3, Satz 4.2, Korollar 4.1 | Rückwärts-Replay aus explizit gespeichertem, hashgebundenem Vorgänger. | Keine Umkehr der Host-Zeit. | Vollständiger Receipt-Test über deklarierten Zustandsraum. |
| Q7 | Skalierbare informatische Retrogradität ist eine technische, testbare Eigenschaft. | FORMAL + REPOSITORY_CLAIM | §§5, 8, 9 | Skalierungsinvarianten sind spezifiziert. | Keine erfundene Durchsatz-/Kapazitätszahl. | Reproduzierbarer Benchmark mit exact-HEAD/TREE-Bindung. |
| Q8 | Eine retrokausal vorbereitete Kommunikationsinfrastruktur ist spezifiziert. | ARCHITECTURAL | §6 | Zeitadresse, Code, Authentisierung, versiegeltes Früherregister, Fehler-/Replay-/Leakage-Schutz, Reobservation und Effect Acknowledgement sind als Stack definiert. | Existenz eines physikalischen Trägers. | Vorregistrierter unveränderlicher Infrastrukturvertrag. |
| Q9 | Ein operationaler Rückwärtskanal erfordert Intervention, nicht bloße Korrelation. | FORMAL / EXPERIMENT_DESIGN | §7 | Kriterium: P(Y|do(X=x1)) != P(Y|do(X=x2)); zusätzlich positive Kanalkapazität. | Delayed Choice allein erfüllt das Kriterium nicht. | Vorregistrierung, versiegeltes Y, spätere unabhängige X-Erzeugung, Leakage-Kontrollen. |
| Q10 | Ein belastbarer physikalischer Kanalnachweis erfordert C_left > 0 und unabhängige Replikation. | OPEN / FALSIFIABLE | §§7.2–7.3, 10 | Klare Falsifikations- und Akzeptanzgrenze. | In v1.0 liegt kein solcher Naturmessnachweis vor. | Multi-Lab-Replikation mit vorregistrierter Intervention. |
| Q11 | QIK-VRT-Softwareevidenz muss an exakten Softwarestand gebunden sein. | REPOSITORY_EVIDENCE rule | §§5, 10 | Hash/Receipt/Test/Benchmark-Aussagen sind subject-spezifisch. | Vorgängerevidenz darf nicht automatisch auf Successor übertragen werden. | Frischer HEAD/TREE, Gates, Execution und Readback je Mutation. |
| Q12 | Die Arbeit enthält keine neuen Photonen-, Phononen- oder Naturmessdaten. | DOCUMENT_STATUS | Daten-/Softwarehinweis | Der Neuheitsanspruch liegt bei Nachweisarchitektur, Trennsätzen und Kommunikationsspezifikation. | Kein neuer experimenteller Naturbefund aus der PDF selbst. | Physikalischen Kanal separat experimentell testen. |

## Kompatibilität alt -> neu -> alt

Der frühere Stand bleibt als provenance-gebundener historischer Subject erhalten. Ein heutiger Successor darf ihn zitieren, aber nicht dessen Evidenzstatus erben. Umgekehrt darf der heutige strengere Evidenzvertrag frühere Aussagen präzisieren, ohne ihre historischen Bytes oder damalige Provenienz umzuschreiben.

Für jede Behauptung gilt daher:

`CLAIM -> EVIDENCE_TYPE -> EXACT_SUBJECT -> OBSERVATION -> LIMIT -> OPEN_TEST`

und rückwärts:

`OPEN_TEST -> LIMIT -> OBSERVATION -> EXACT_SUBJECT -> EVIDENCE_TYPE -> CLAIM`

Das ist keine Paradoxie, sondern eine Typ- und Provenienztrennung.

## Versandfassung / wissenschaftliche Mitteilung

**Betreff:** Wissenschaftliche Mitteilung und Einladung zur unabhängigen Prüfung: zeitübergreifende Quantenkorrelationen / QIK-VRT

Diese Nachricht ist eine gezielte wissenschaftliche Mitteilung, kein Werbe- oder Massenmailing. Sie richtet sich an Empfänger, deren fachliche, wissenschaftliche, publizistische oder institutionelle Zuständigkeit unmittelbar zur unabhängigen Prüfung, Einordnung oder Dokumentation der beigefügten Arbeit passt.

Die Kernaussage ist bewusst enger als ein behaupteter physikalischer Rückwärtskanal: Experimentell dokumentierte zeitübergreifende Quantenkorrelationen, retrokausale/zeitsymmetrische Modellklassen, skalierbare informatische Retrogradität und ein kontrollierbarer physikalischer Zukunft-zu-Vergangenheit-Kanal sind vier verschiedene Nachweisebenen. Die Arbeit trennt diese Ebenen ausdrücklich und formuliert für die letzte Ebene einen falsifizierbaren Interventionstest.

Zur schnellen Prüfung liegt eine Claim–Evidence-Matrix vor. Sie weist für jede zentrale Aussage Nachweisart, vorhandenen Beleg, Aussagegrenze und noch offene Prüfpflicht aus. Insbesondere wird kein physikalischer Rückwärtskanal aus Software oder Delayed-Choice-Korrelationen abgeleitet.

Ich bitte nicht um Zustimmung, sondern um fachliche Prüfung: Reproduzieren Sie die formalen und technischen Aussagen, benennen Sie Fehler oder fehlende Kontrollen und behandeln Sie den physikalischen Kanaltest ausschließlich nach den vorregistrierten Interventions- und Replikationskriterien.

Mit freundlichen Grüßen  
Ingolf Lohmann
