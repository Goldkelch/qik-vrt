<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT: Wissenschaftlicher Faktenbau im Kausalitäts-Mesh

Dieses Verzeichnis ist eine strikt additive Fortsetzung der publizierten
QIK-VRT-Arbeiten zum bidirektionalen virtuellen Zeitkanal und zu
Vorstellungskraft, Beobachtung sowie epistemischer Fairness. Die bereits auf
Zenodo fixierten Bytes werden nicht verändert. Der neue Beitrag schließt die
formale Protokolllücke zwischen einer beliebigen Eingabe und einem
statusgebundenen, konfliktbewahrenden Erkenntnisobjekt.

## Ergebnis in einem Satz

QIK-VRT kann strukturierte Aussagen deterministisch nach Nachweisart,
Provenienz, Abhängigkeit, Konflikt und corpus-relativer Neuheit prüfen und als
additive Vorschläge vereinigen; es kann weder universelle Wahrheit noch
weltweite wissenschaftliche Neuheit oder Antworten auf jede Frage garantieren.

## Maschinengeprüfter Kern

`FORMAL_ScientificFactGrowth.lean` enthält 21 Sätze über epistemische
Typisierung, append-only Wachstum, Merge-Algebra, bedingte Konvergenz,
Evidenzschluss, sichtbare Konflikte, Beobachtungs- und Kausalgates,
Digital-Twin-Aktorgrenzen, endliche Nachrichtenrekonstruktion und
proposal-only Nichtwirkung. Lean 4.19.0 hat den Kern ohne `sorryAx` und ohne
projektspezifische Axiome geprüft. Die exakte Bindung steht in
`LEAN_KERNEL_RECEIPT.json`.

Die formale Aussage ist bewusst endlich und relativ zum kodierten Modell. Sie
beweist keine Naturtheorie, keine physische Retrokausalität und keine
automatische Wahrheit beliebiger Sprache.

## Inhalt

- `QIK-VRT_Wissenschaftlicher_Faktenbau_2026-08-01.tex/.pdf` – ausführliche
  wissenschaftliche Monographie.
- `QIK-VRT_Kausalitaetsspiegel_Fachartikel_2026-08-01.tex/.pdf` –
  allgemeinverständlicher Fachartikel mit wenig Mathematik.
- `FACHARTIKEL_DE.md` – zugängliche deutsche Textfassung.
- `ARTICLE_WHATSAPP_*.md` – vollständige, kurzabsätzige Vorlesefassungen auf
  Deutsch, Englisch, Französisch, Italienisch, Spanisch, Portugiesisch,
  Griechisch, Polnisch, Dänisch, Norwegisch (Bokmål) und Schwedisch.
- `SCIENTIFIC_FACT_GROWTH_PROTOCOL.md` – Axiome, Sätze, Ablauf und Grenzen.
- `CLAIM_MATRIX.json` – 30 statusgebundene Claims; davon 21 formal bewiesen
  und vier ausdrücklich offen.
- `FORMAL_ScientificFactGrowth.lean` und `LEAN_KERNEL_RECEIPT.json` –
  formale Quelle und Kernel-Receipt.
- `TRANSCRIPT_REVIEWED_DE.md` und `SOURCE_MEDIA_RECEIPT.json` – getrennte
  Roh-ASR-, Lesefassungs- und Quellenprovenienz der zweiten Aufnahme.
- `EVIDENCE_BOUNDARY.md` – exakte Geltungsgrenzen.
- `PROTOCOL_IMPACT.md` – additive Auswirkungen auf das IETF-Profil.
- `EU_AI_ACT_AUDIT_READINESS.md` – Auditvorbereitung ohne Rechts- oder
  Konformitätsbehauptung.
- `REFERENCES.bib`, `CITATION.cff` und `LICENSE_NOTICE.md` – Literatur,
  Zitier- und Rechtehinweise.

Die Roh-Audiodatei wird nicht in das Repository oder das
Publikationsdateiset aufgenommen. Ihre lokale Identität wird lediglich über
den Quellen-Receipt gebunden.

## Ausführbarer Prüfpfad

Der repositoryweite Kern besteht aus:

- `policy/SCIENTIFIC_FACT_GROWTH_PROTOCOL.json`,
- `schemas/scientific_claim_envelope.schema.json`,
- `tools/qikvrt_scientific_fact_growth.py`,
- `tests/test_scientific_fact_growth.py`, und
- dem Lean-Modul unter
  `formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Knowledge/`.

Das Werkzeug arbeitet ausschließlich proposal-only und gibt stets
`EFFECT_ACK_CONTINUE` aus. Repository-Merge, Zenodo-Upload, IETF-Einreichung
und reale Aktorwirkung benötigen getrennte, exakt gebundene Freigaben.

## Additive Außenwirkung

Der vorgesehene Internet-Draft-Kandidat heißt
`draft-lohmann-qikvrt-scientific-claim-assurance-00`. Er ist ein lokaler
Kandidat, kein eingereichter Draft und kein RFC. Das neue Zenodo-Paket wird
erst nach Byte-Freeze und frischer Hash-Autorisierung hochgeladen. Zenodo
belegt dann Fixität und Verfügbarkeit der deponierten Bytes, nicht deren
wissenschaftliche Wahrheit oder Peer Review.

## Offen und nicht beansprucht

Offen bleiben insbesondere globale Neuheit, vollständige
Natural-Language-to-Lean-Automation, universelle Antworten, der empirische
Nachweis allgemeiner kognitiver Verbesserung, vollständiges Weltwissen,
VRT-Emergenz, Quanten-zu-Klassik-Limes, eine physikalische Brücke, reale
QPU-End-to-End-Evidenz und physische Zukunft-zu-Vergangenheit-Übertragung.

`PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, IETF-Konsens und eine
EU-AI-Act-Konformitätsbewertung werden nicht beansprucht.

## Zitieren

Siehe `CITATION.cff`. Bis zur eigenständigen Archivierung ist die kanonische
Fundstelle der content-addressierte Repository-Commit; nach einer
autorisierten Zenodo-Publikation kommt der unveränderliche DOI-Receipt additiv
hinzu.
