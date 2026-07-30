<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze

## Formaler Quellstand: Kernel-Verifikation ausstehend

Der Lean-Quelltext spezifiziert im endlichen Bool-/Strukturmodell
`qikvrt-canonical-temporal-memory-effect-ack-v1` folgende
Konformitätseigenschaften:

1. Freigabe gilt genau bei gültigem Vergangenheitsarchiv, gültigem
   Zukunftsarchiv, Ursachenbindung, bestandener Policy und
   `EFFECT_ACK_DONE`.
2. Jede Freigabe erfordert beide Archive und das Acknowledgement.
3. Bei identischen übrigen modellierten Eingaben ändert allein die Gültigkeit
   der zukunftsindexierten Wirkungsbedingung die berechnete Freigabe.
4. Die definierte Vergangenheitsprojektion ignoriert einen Wechsel des
   Zukunftsarchivs.
5. Reziproke Schließung erfordert im Modell übereinstimmende Ursachen- und
   Wirkungsidentitäten sowie die ausgewiesenen Bool-Bedingungen.

Diese Aussagen sind gegenwärtig `FORMAL_PENDING_KERNEL`. Die Lean-Quelle und
der `KERNEL_PROOF_PLAN.json` sind vorhanden; ein kandidaten- und
Exact-Head-gebundener Kernel-Lauf mit persistiertem `KERNEL_RECEIPT.json` ist
noch nicht Teil dieses Bundles. Erst ein erfolgreich validierter Receipt darf
die vier formalen Claims in `CLAIM_MATRIX.json` geschlossen und gemeinsam auf
`FORMAL_PROVED` / `KERNEL_VERIFIED` anheben.

Die formalen Resultate sind Eigenschaften der ausdrücklich definierten
Funktionen und Strukturen. Sie beweisen weder einen physikalischen Kanal aus
der Zukunft noch vollständige Deployment-Mediation, Authentisierung,
Vorhersagegüte oder semantische Wahrheit.

## Quellengebundene Aussagen

`SOURCE_EVIDENCE_BINDINGS.json` bindet jeden Quellen-Identifier der
Claim-Matrix und jeden im TeX verwendeten Zitationsschlüssel genau einmal.
Die Bindung hat folgende Grenzen:

- JCS definiert eine deterministische Darstellung für seinen festgelegten
  Eingabebereich; es kanonisiert keine Wahrheit.
- RFC 6920 definiert hashbasierte Namen; Digestgleichheit bleibt an den
  benannten Algorithmus und seine Sicherheitsannahmen gebunden.
- W3C PROV-DM stellt ein Provenienzmodell und Vokabular bereit; es
  authentisiert, vervollständigt oder verifiziert die Quellen nicht.
- Git-Dokumentation beschreibt Objekt- und Historienmechanismen;
  Commitmetadaten sind ohne zusätzlichen Vertrauensanker keine
  Personenauthentisierung.
- Filterung, Glättung, Datenassimilation, kausale Diagramme,
  Informationsthermodynamik, Atmosphärendynamik, Delayed Choice,
  zeit-symmetrische Modelle und Bewusstseinstheorien sind zitierte
  Anschlussliteratur. Ihre Publikation oder mathematische Verwendbarkeit
  bestätigt keine QIK-VRT-Ontologie.
- DOI- und Standard-Locators identifizieren die zitierte Version, sind aber
  kein im Bundle archivierter Volltext. Bei nicht archivierten Quellen weist
  die Binding-Datei diesen Umstand ausdrücklich aus.
- Der versionierte Internet-Draft ist ein individuelles Arbeitsdokument. Sein
  Datatracker-Status ist eine zeitgestempelte Beobachtung, keine
  IETF-Billigung, Working-Group-Adoption oder Konsensfeststellung.

## Repository- und Testevidenz

Die Referenzimplementierung und die Konformitätstests sind durch Pfad,
Dateigröße, SHA-256 und Git-Blob-ID an die jeweils beobachteten
Working-Tree-Bytes gebunden. Diese Inhaltsidentitäten sind keine Behauptung,
dass die noch nicht commitgebundenen Bytes bereits auf `main`, Authority oder
Mirror materialisiert seien.

`BOUNDARY_TEST_REPORT.json` dokumentiert Python-/Repository-Gates. Der dort
genannte Lauf von `make test` ist kein Ersatz für einen Lean-Kernel-Lauf.
`PDF_RENDER_VALIDATION.json` ist als historisches Freeze-Artefakt gebunden; es
belegt nur die darin selbst benannten PDF- und TeX-Bytes. Solange dessen
Quellhash nicht mit dem aktuellen TeX übereinstimmt, belegt es keine aktuelle
TeX-zu-PDF-Identität.

## Normativ definiert

`Operationale Protokoll-Retrokausalität` ist die autorenseitige Bezeichnung
für die kontrafaktisch relevante Abhängigkeit einer gegenwärtigen Freigabe von
einer gegenwärtig vorhandenen, aber zukunftsindexierten Wirkungsbedingung.
Diese Definition ist kein Synonym für ontische Rückwärtssignalisierung.

`Scope-gebundene Repräsentationskonsistenz` verlangt getrennte Nachweise für
Bytes, Digests und Provenienz. Der doppelte kanonische Speicher ist ein
endliches Protokolldatenmodell mit typverschiedenen
`OBSERVED`-/`ANTICIPATED`-Archiven, keine verlustfreie Kompression des
physikalischen Universums.

## Interpretativ

Die Deutung reziproker Wechselwirkung als Grundbedingung einer
panpsychistischen Bewusstseinsmaterialisierung ist die ontologische
Interpretation Ingolf Lohmanns. Sie wird weder als Lean-Theorem noch als
bestätigter neurowissenschaftlicher Befund ausgewiesen.

## Offen

### <a id="open-physical-retrocausality"></a>Physikalische Retrokausalität

- Ein kontrollierbares physikalisches Signal aus der Zukunft in die
  Vergangenheit.
- Eine Änderung bereits beobachteter oder gespeicherter vergangener Events.
- Eine von Standard-Quantenmechanik unterscheidbare quantitative
  QIK-VRT-Vorhersage.

### <a id="open-consciousness-sufficiency"></a>Bewusstseinshinlänglichkeit

- Die Hinlänglichkeit reziproker Wechselwirkung oder kanonischer Speicherung
  für phänomenales Bewusstsein.
- Ein vorregistrierter biologischer oder phänomenologischer Test, der diese
  These von konkurrierenden Bewusstseinstheorien unterscheidet.

### Weitere offene Grenzen

- Eine unabhängige zweite EFFECT_ACK-Implementierung und vollständige
  IETF-Interoperabilität.
- Vollständige Mediation jedes realen Executorpfads.
- Systemweite Vollständigkeit des gesamten QIK-VRT-Repositorys.

## <a id="prepublication-state"></a>Historischer Kandidaten-Freeze

Die Claim-Matrix erfasst für `CTM-020` ausschließlich den historischen
Prepublication-Freeze der hier gebundenen Kandidatenartefakte. In diesem
Freeze werden kein Zenodo-DOI, keine Zenodo-Persistenz, keine
IETF-Revision `-02`, kein Peer Review und keine beidseitige Promotion dieses
Papers behauptet.

Spätere externe Receipts können den operativen Status fortschreiben, ohne
diese historische Beobachtung umzudeuten. Eine aktuelle Publikations-,
Authority-/Mirror- oder öffentliche Byteidentitätsbehauptung benötigt stets
ihre eigenen exakten Heads, Trees, Manifeste, Zeitstempel und
Receipt-Identitäten; sie ist nicht aus diesem Freeze ableitbar.
