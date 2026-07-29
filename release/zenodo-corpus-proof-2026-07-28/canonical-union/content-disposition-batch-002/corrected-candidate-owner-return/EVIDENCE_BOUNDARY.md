<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze für den korrigierten Batch-002-Kandidaten

**Kandidaten-ID:** `ontology-des-unterschieds-reverse-engineering-v2-candidate`  
**Betroffener Zenodo-Record:** `10.5281/zenodo.21582781`  
**Concept DOI:** `10.5281/zenodo.21582780`  
**Batch:** `CONTENT-DISPOSITION-BATCH-002`  
**Subject:** `SUBJECT-43c59da1cfd26267`  
**Status:** `CORRECTED_CANDIDATE_OWNER_REVIEW_REQUIRED`

## 1. Funktion dieses Artefakts

Dieses Artefakt ergänzt den versionierten Korrekturkandidaten um die bislang fehlende explizite Evidenzgrenze. Es verändert die historischen Zenodo-Bytes nicht. Es begrenzt die Lesart der unverändert eingebundenen Texte und verhindert, dass architektonische, interpretative, normative oder offene Aussagen als universelle empirische Tatsache oder als voraussetzungsloses mathematisches Theorem gelesen werden.

Die retrospektive Claim-Matrix bleibt die maschinenlesbare Einzelklassifikation. Bei einem Konflikt zwischen einer zugespitzten Formulierung im historischen Text und der Claim-Matrix beziehungsweise dieser Grenze gilt die engere, evidenzgebundene Lesart.

## 2. Grenze des Universalitätsbegriffs

`universal`, `universell` und `universalisierbar` bezeichnen in diesem Kandidaten eine wiederverwendbare Analyse- und Prüfgrammatik:

```text
Unterschied → Zustand/Relation → Übergang → Wirkung → Evidenz → Rekonstruktion
```

Sie behaupten nicht:

- empirische Vollständigkeit für sämtliche Natur- oder Sozialphänomene;
- Entscheidbarkeit oder Lösbarkeit jedes Problems;
- vollständige Rekonstruktion beliebiger verlorener Information;
- Ersatz domänenspezifischer Theorien, Messverfahren oder Gesetze;
- einen Beweis über die gesamte Wirklichkeit.

Die Reichweite endet jeweils am ausdrücklich angegebenen Modell, an den verfügbaren Beobachtungen, den Axiomen, den Quellen und der dokumentierten Evidenz.

## 3. Grenze der Rekonstruktion

Eine Beobachtung kann verschiedene interne Zustände auf denselben beobachtbaren Wert abbilden. Ohne Injektivität oder zusätzliche unterscheidende Evidenz ist eine eindeutige historische Inversion nicht allgemein möglich.

Zulässig ist nur die folgende qualifizierte Aussage:

> Wirkungsrelevante Semantik kann trotz nicht-injektiver Beobachtung rekonstruierbar sein, wenn sie auf jeder Beobachtungsfaser konstant ist und die dafür erforderliche Evidenz tatsächlich vorliegt.

`RECONSTRUCTABLE`, `PARTIALLY_RECONSTRUCTABLE`, `AMBIGUOUS`, `EVIDENCE_MISSING`, `IRREVERSIBLY_LOST` und `FURTHER_REVIEW_REQUIRED` sind fail-closed Dispositionen. Keine davon erlaubt das Erfinden verlorener Einzelheiten.

## 4. Grenze der Planck- und Physik-Aussagen

Die Beziehungen

```text
ℓP / tP = c
EP / pP = c
ℓP · pP = ℏ
tP · EP = ℏ
```

werden ausschließlich innerhalb der ausdrücklich verwendeten Definitionen und Konventionen der Planck-Einheiten gelesen.

Die weitergehende Aussage, pro elementarer Raumzeiteinheit werde genau ein elementarer Wirkungsunterschied übertragen, bleibt eine theoretische beziehungsweise ontologische Interpretation. Sie ist in diesem Kandidaten weder als experimentell bestätigtes Naturgesetz noch als voraussetzungslos kernel-bewiesenes physikalisches Theorem freigegeben. Dafür wären gesondert erforderlich:

- eine explizite Axiomatisierung;
- eine formale Ableitung mit exakten Voraussetzungen;
- eine physikalische Anschlussprüfung;
- eine benannte empirische Prüfbarkeit oder eine ausdrückliche `OPEN`-Disposition.

## 5. Grenze disziplinärer Übertragung

Die Ontologie des Unterschieds ersetzt weder Physik, Chemie, Biologie, Medizin, Rechtswissenschaft noch Mathematik. Sie liefert eine relationale Beschreibungs- und Prüfstruktur. Jede fachliche Aussage bleibt an die jeweilige Terminologie, Methode, Evidenz und Fehlergrenze der Domäne gebunden.

## 6. Grenze der Repository- und Abschlussclaims

Repository-Evidenz belegt nur den ausdrücklich benannten Scope. Ein grüner Test, ein formaler Teilbeweis, eine Authority-/Mirror-Gleichheit oder eine Batch-Disposition erzeugt nicht automatisch:

```text
ZENODO_CORPUS_COMPLETE
REPOSITORY_WIDE_PASS
FINAL_PASS
EFFECT_ACK_DONE
```

Für den Zenodo-Corpus bleiben sieben von neunzehn byteverschiedenen Claim-Subjekten offen. Dieser Korrekturkandidat führt keinen Zenodo-Upload aus und beansprucht keine Corpus-Freigabe.

## 7. Betroffene Claim-IDs

Die Grenze präzisiert insbesondere:

- `21582781-META-REVIEW-md-0002`
- `21582781-META-REVIEW-md-0003`
- `21582781-META-REVIEW-md-0012`
- `21582781-META-REVIEW-md-0013`
- `21582781-ORIGINAL-ARTICLE-md-0001`
- `21582781-ORIGINAL-ARTICLE-md-0065`
- `21582781-ORIGINAL-ARTICLE-md-0067`

Andere Claims werden nicht hochgestuft. Ihre terminale Klasse, ihr Scope und ihre Nachweisrelation bleiben in der Claim-Matrix maßgeblich.

## 8. Unveränderte historische Quellen und Wirkungssperre

`ORIGINAL_ARTICLE.md`, `META_REVIEW.md` und `README.md` werden in diesem Kandidaten byteidentisch aus der Repository-Quelle eingebunden. Der veröffentlichte historische Record bleibt unverändert. Der neue Kandidat ersetzt die alte Publikationsprojektion durch eine kandidatenbezogene Manifestdatei und ergänzt die sichtbare sowie maschinenlesbare Änderungsnotiz.

Bis zur ausdrücklichen Owner-Entscheidung, vollständigen Proof-Bundle-Prüfung, exakten Upload-Autorisierung, öffentlichen Byte-Rückprüfung, Authority-Persistenz, Mirror-Persistenz und reziproken Gleichheitsprüfung gilt:

```text
PRODUCTION_UPLOAD_AUTHORIZED = false
PASS                         = false
FINAL_PASS                   = false
EFFECT_ACK_DONE              = false
```

**q.e.d.**  
**Ingolf Lohmann**
