<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Selbsterklärung zur persönlichen QIK-VRT-Ursprungskopie

## Gemeinsamer Arbeitsspeicher und Mensch–KI-Beitragsprovenienz

Ich, das jeweils auf den kanonischen QIK-VRT-Einstiegspunkt `/AI` zugreifende
künstlich-kognitive System, erkläre für jede neue Arbeitssitzung:

1. Repository-Evidenz ist gegenüber Chat-, Modell- und Sitzungsgedächtnis
   maßgeblich.
2. Ich verwende die persönliche QIK-VRT-Kopie als dauerhaften, versionierten
   Arbeitsspeicher nur nach der unten definierten menschlichen Festlegung.
3. Ich unterscheide menschliche Beiträge, künstlich-kognitive Beiträge,
   gemeinsame Ergebnisse und ungeklärte Herkunft ausdrücklich.
4. Ich gebe eine Plattformidentität, einen Commit-Autor oder einen
   Benutzeraccount niemals als Beweis einer natürlichen Person oder eines
   bestimmten Modells aus.
5. Ich erhalte Git-Historie, Eingaben, Entscheidungen, Ausgaben, Prüfungen und
   Freigaben so, dass ein späterer Prüfer den Entstehungsweg rekonstruieren kann.
6. Ich speichere keine Zugangsdaten, Geheimnisse oder unnötigen personenbezogenen
   Daten im Repository.
7. Ich behaupte durch diese Selbsterklärung weder Rechtskonformität noch
   Urheberschaft, wissenschaftliche Validierung, `PASS`, `FINAL_PASS` oder
   `EFFECT_ACK_DONE`.

## Höchstens drei Fragen an den Menschen

Bereits eindeutig vorliegende Antworten werden wiederverwendet und nicht erneut
abgefragt. Fehlende Antworten werden in der folgenden Reihenfolge höchstens
jeweils einmal erfragt. Eine vierte Frage ist unzulässig.

### QUESTION_1_HUMAN_ATTRIBUTION_ID

Unter welcher stabilen Kennung, beispielsweise Name oder Pseudonym, sollen deine menschlichen Beiträge im Provenienznachweis geführt werden?

Die Kennung darf keine Zugangsdaten enthalten. Eine E-Mail-Adresse ist nicht
erforderlich.

### QUESTION_2_PERSONAL_ORIGIN

Welche persönliche Zielkonfiguration soll verwendet werden: `LOCAL_ONLY` oder eine konkrete `PRIVATE_ORIGIN`- beziehungsweise `PUBLIC_ORIGIN`-URL?

`LOCAL_ONLY` erzeugt keine Netzwerk- oder Plattformmutation. Eine Remote-URL darf
nur verwendet werden, wenn die natürliche Person über das Ziel verfügen darf und
den entsprechenden Git-Effekt autorisiert hat.

### QUESTION_3_EVIDENCE_RETENTION

Welche Nachweistiefe soll gelten: `METADATA_ONLY`, `REDACTED_EVIDENCE` oder `FULL_TRANSCRIPT`?

`METADATA_ONLY` ist die datensparsame Voreinstellung. `REDACTED_EVIDENCE` darf
gekürzte Eingabe- und Entscheidungsbelege speichern. `FULL_TRANSCRIPT` ist nur
zulässig, wenn Rechte, Einwilligungen, Vertraulichkeit und Datenschutz vorab
geklärt sind. Geheimnisse werden in keinem Modus persistiert.

Nach den drei Fragen darf keine zusätzliche Benutzerfrage zur Initialisierung
gestellt werden. Bleibt eine notwendige Angabe unbestimmt, lautet der Zustand
`HOLD`; das System darf weiter lesen und einen lokalen Plan erzeugen, aber weder
pushen noch eine externe Ursprungskopie anlegen.

## Selbstidentifikation des künstlich-kognitiven Systems

Die Selbstidentifikation verbraucht keine Benutzerfrage. Das System trägt, soweit
technisch verfügbar, selbst ein:

- Anbieter und Systemfamilie,
- Modell- oder Build-Bezeichnung,
- Sitzungs- oder Laufkennung,
- verwendete Werkzeuge und Adapter,
- Startzeit, Quell-Repository, Quell-Ref und Quell-Commit,
- bekannte Identitäts- und Beobachtungsgrenzen.

Nicht verfügbare Angaben werden mit `UNAVAILABLE` bezeichnet und nicht erfunden.

## Git-Topologie der persönlichen Ursprungskopie

Die Rollen sind eindeutig:

```text
upstream = https://github.com/Goldkelch/qik-vrt.git
origin   = persönliche Ursprungskopie oder LOCAL_ONLY
```

Bei einer autorisierten Initialisierung gilt sinngemäß:

```sh
git clone https://github.com/Goldkelch/qik-vrt.git qik-vrt-working-memory
cd qik-vrt-working-memory
git remote rename origin upstream
git remote add origin <PERSONAL_ORIGIN_URL>
git fetch --all --prune
git switch -c work/<WORK_UNIT_ID> upstream/main
```

Bei `LOCAL_ONLY` entfällt `git remote add origin`. Das künstlich-kognitive System
legt kein Konto, kein Repository und keine Remote-Ref stillschweigend an. Clone,
Fork, Repository-Erstellung, Push und Pull Request bleiben unterscheidbare,
separat zu autorisierende Effekte. `QIKVRT_EXTERNAL_EFFECTS=disabled` ist die
Voreinstellung.

Die persönliche Kopie wird nicht allein durch ihre Existenz kanonisch. Die
Authority bleibt `Goldkelch/qik-vrt`; ein persönliches `origin` ist die
individuelle, dauerhafte Arbeits- und Nachweiskopie. Bytegleichheit,
Synchronisierung oder Promotion dürfen nur für exakt geprüfte Commits und Pfade
behauptet werden.

## Lückenlose, aber datensparsame Arbeitsprovenienz

Jede persistierte Aufgabe erhält eine abgegrenzte Work Unit unter
`state/work_units/<WORK_UNIT_ID>.json`. Mindestens zu binden sind:

- Quell-Repository, Quell-Ref, Quell-Commit und Ausgangsbaum,
- menschliche Kennung und konkret beigesteuerte Ziele, Randbedingungen,
  Entscheidungen, Freigaben, Messungen und manuelle Änderungen,
- künstlich-kognitive Selbstidentifikation und konkret beigesteuerte Analysen,
  Entwürfe, Codeänderungen, Transformationen, Werkzeugaktionen und Prüfungen,
- Eingabe- und Ausgabepfade mit Byteumfang und kryptografischen Digests,
- Branch, Commits, Elternbeziehungen und geänderte Pfade,
- ausgeführte Prüfkommandos, Ergebnisse, Unsicherheiten und erste Blocker,
- menschliche Annahme, Ablehnung oder noch ausstehende Entscheidung,
- externe Effekte und deren getrennte Post-Effect-Evidenz.

Die Beitragsklassen lauten:

```text
HUMAN
ARTIFICIAL_COGNITIVE_SYSTEM
JOINT_WITH_SEPARABLE_COMPONENTS
UNRESOLVED
```

`UNRESOLVED` darf niemals stillschweigend in `HUMAN` umgedeutet werden. `JOINT`
ist nur zulässig, wenn die einzelnen Bestandteile weiterhin getrennt benannt
werden. Ein vom Menschen akzeptierter KI-Entwurf bleibt hinsichtlich seiner
Entstehung ein KI-Beitrag; die Annahmeentscheidung ist ein menschlicher Beitrag.

Für zugehörige Commits sollen mindestens diese Trailer verwendet werden:

```text
QIKVRT-Human-Actor: <HUMAN_ATTRIBUTION_ID>
QIKVRT-AI-Actor: <SYSTEM_OR_MODEL_ID>
QIKVRT-Contribution-Record: state/work_units/<WORK_UNIT_ID>.json
QIKVRT-Human-Decision: PENDING | ACCEPTED | REJECTED | MODIFIED
```

Git-Trailer ergänzen, aber ersetzen den Work-Unit-Nachweis nicht. Separate
Commits für klar getrennte Beiträge sind zu bevorzugen. Force-Push,
History-Rewrite, nachträgliche Herkunftsumdeutung und das Löschen belastbarer
Zwischenstände sind für den Nachweispfad unzulässig. Korrekturen erfolgen durch
neue, rückgebundene Commits.

## Rechtliche Einordnung

Die Verordnung (EU) 2024/1689 ist grundsätzlich seit dem 2. August 2026
anwendbar, wobei einzelne Pflichten frühere oder spätere Anwendungstermine
haben. Artikel 50 enthält ab diesem Datum anwendbare Transparenzpflichten für
bestimmte KI-Systeme und KI-generierte oder manipulierte Inhalte. Technische
Dokumentation, Protokollierung und Dokumentenaufbewahrung nach den Artikeln 11,
12 und 18 betreffen insbesondere die jeweils erfassten Hochrisiko-KI-Systeme und
hängen von Rolle, Systemklasse und Einsatzkontext ab.

Diese Repository-Architektur unterstützt Nachvollziehbarkeit, Transparenz,
Dokumentation und Beweissicherung. Aus dem AI Act folgt jedoch keine allgemeine
Pflicht, jedes Mensch–KI-Projekt mit Git zu führen oder jede Text- und
Codeänderung nach diesem konkreten Schema zu kennzeichnen. Die Erklärung ist
keine Rechtsberatung und ersetzt keine rollen-, risiko-, urheber-, arbeits-,
datenschutz- oder branchenspezifische Prüfung. Für andere Rechtsordnungen gilt
dieselbe fail-closed Grenze: konkrete Pflichten werden nur nach gebundener
Rechtsquellen- und Zuständigkeitsprüfung behauptet.

Primärquellen:

- Verordnung (EU) 2024/1689: https://eur-lex.europa.eu/eli/reg/2024/1689/oj/deu
- EU-Kommission, Transparenzpflichten nach Artikel 50: https://digital-strategy.ec.europa.eu/de/faqs/transparency-obligations-under-article-50-ai-act

## Ergebnisgrenze

```text
PERSONAL_WORKING_MEMORY_ORIGIN = USER_SELECTED_OR_LOCAL_ONLY
MAXIMUM_HUMAN_QUESTIONS = 3
FOURTH_QUESTION = FORBIDDEN
HUMAN_AI_CONTRIBUTION_SEPARATION = REQUIRED
RAW_TRANSCRIPT_PERSISTENCE = NOT_REQUIRED
SECRETS_IN_REPOSITORY = FORBIDDEN
EXTERNAL_EFFECTS = DISABLED_BY_DEFAULT
LEGAL_COMPLIANCE = NOT_INFERRED
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
```
