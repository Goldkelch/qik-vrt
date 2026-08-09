<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Evidenzhinreichend handeln – eine universalisierbare Entscheidungsmaxime

## Status

```text
ARTICLE_STATUS = ETHICAL_BOUNDARY
CLAIM_BOUNDARY = NORMATIVE_TRANSLATION_NOT_EMPIRICAL_OR_LEGAL_PROOF
QIKVRT_GATE = RESPONSIBILITY_REQUIRED
FORMAL_SOURCE = MINIMAL_RECOVERY_THEOREM
EXTERNAL_EFFECT_AUTHORIZATION = NOT_CREATED
```

## Die Maxime

> Handle nur dann produktiv, wenn alle nach den zulässigen Regeln noch
> möglichen Histories dieselbe erlaubte Fortsetzung verlangen. Ist dies nicht
> belegt, behandle die Unterscheidung nicht als Wissen: verfeinere die Evidenz
> oder folge der zuvor legitimierten sicheren Baseline.

Diese Maxime überträgt den Gedanken des kategorischen Imperativs als
Prüffrage in eine Entscheidungsarchitektur: Könnte jede Stelle, die denselben
Evidenzstand, dieselben Zulässigkeitsregeln und dieselbe Zuständigkeit hat,
dieselbe Regel anwenden, ohne Wahrheit, Freiheit, Würde, Sicherheit, Rechte
oder Verantwortbarkeit durch bloße Vermutung zu beschädigen?

Sie ist keine mathematische Herleitung von Kants Ethik. Sie ersetzt weder
eine moralische Abwägung noch gesetzliche, medizinische, sicherheits- oder
berufsspezifische Regeln. Sie macht nur die Mindestbedingung sichtbar, unter
der eine bereits zuständig definierte Fortsetzung durch Evidenz gerechtfertigt
ausgewählt werden kann.

## Formale Übersetzung

Für eine konkrete Domäne `D` müssen vor der Anwendung bestimmt werden:

```text
H_adm,D  = zulässige Histories und explizite Ausschlüsse
C_D      = zuständig definierte korrekte oder erlaubte Fortsetzung
Obs_D    = gebundene Beobachtung samt ihren Grenzen
K_D(o)   = { H in H_adm,D | Obs_D(H) = o }
```

Die Entscheidung ist nur dann evidenzhinreichend, wenn:

```text
K_D(o) != empty
AND
| { C_D(H) | H in K_D(o) } | = 1
```

In der kompakten Normalform:

```text
ker(Obs_D) subseteq ker(C_D)
```

Wenn diese Bedingung nicht belegt ist, lautet die Regel:

```text
FAIL_CLOSED_OR_DOMAIN_SAFE_BASELINE
```

Das ist nicht zwingend Nichtstun. Eine durch Recht, Fachstandard oder
Notfallvertrag bereits legitimierte, reversible oder schadensmindernde
Baseline kann selbst die korrekte Aktion `C_D` sein. Was unterbleiben muss,
ist die ungesicherte produktive Fortsetzung, die eine Mehrdeutigkeit als
Wissen ausgibt.

## Was jede domänenspezifische Variante sichtbar machen muss

```text
DOMAIN                         = <klar begrenzter Anwendungsbereich>
DECISION                       = <konkrete Entscheidung>
H_ADM                          = <zulässige Histories und Ausschlüsse>
CORRECT_ACTION_CONTRACT        = <Quelle von C_D; keine freie KI-Definition>
OBSERVATION                    = <Quelle, Zeitpunkt, Integrität, Grenzen>
FIBER_CONSTANCY_ARGUMENT       = <Nachweis, Test oder explizite offene Lücke>
WITNESS_REFINEMENT             = <zusätzliche zulässige Evidenz>
SAFE_BASELINE                  = <legitimierte reversible oder Notfallregel>
AUTHORITY_AND_RIGHTS_BOUNDARY  = <Zuständigkeit, Rechte, Einwilligung>
EFFECT_BOUNDARY                = <getrennt autorisierte Folgen>
STATUS                         = READY | HOLD | BLOCK | OPEN
```

`C_D` wird nicht von diesem Theorem und nicht von einem KI-System erfunden.
Es kommt aus einem zuständigen Vertrag, Gesetz, Verfahren, Fachstandard oder
einer verantwortlichen menschlichen Entscheidung. Das Theorem beantwortet nur
die andere Frage: Trägt die vorhandene Evidenz diese vorgegebene Fortsetzung
eindeutig?

## Der Witness

Ein Witness ist keine magische dritte Kopie und keine Mehrheit ohne
einschlägige Kompetenz. Er muss die Beobachtung überprüfbar verfeinern:

```text
Obs_D,W = refine(Obs_D, Witness_D)
ker(Obs_D,W) subseteq ker(C_D)
```

Herkunft, Integrität, Aktualität, Zuständigkeit und Bindung an die konkrete
Domäne gehören zu dieser Bedingung. Ein plausibler, aber nicht gebundener
Zustand genügt nicht.

## Beispiele der Übersetzung

| Domäne | `C_D` wird bestimmt durch | Zulässige Verfeinerung | Sichere Grenze |
| --- | --- | --- | --- |
| Crash-Recovery | gebundener Commit-/Recovery-Vertrag | zertifizierte Epoche und Zustandsdigest | keinen Kandidaten kanonisieren |
| Software und Sicherheit | Change-, Review- und Sicherheitsvertrag | exakter Head, Tests, Reviews, Signaturen | nicht deployen; Quarantäne oder Rückfallprozedur |
| Wissenschaft | Aussageklasse und Mess-/Prüfprotokoll | reproduzierbare Messung, Fehleranalyse, unabhängige Prüfung | Behauptung als offen oder bedingt klassifizieren |
| Medizin und Pflege | Fachstandard, qualifizierte Entscheidung, Notfallprotokoll | klinisch relevante Befunde und fachliche Beurteilung | keine Diagnose oder Therapie aus dieser Leitlinie ableiten; geregelte Eskalation anwenden |
| Recht und Verwaltung | zuständiges Recht und Verfahren | verifizierte Akte, Zuständigkeit, rechtliches Gehör | keine Rechtsfolge erraten; geregeltes Verfahren nutzen |
| KI-gestützte Systeme | Auftrag, Rechte-/Sicherheitsgrenzen, menschliche Zuständigkeit | Quellenbindung, Unsicherheitsnachweis, menschliche Prüfung | abstainieren oder an die zuständige Person eskalieren |

Die Beispiele sind keine fachspezifischen Anweisungen. Sie zeigen nur, dass
die Form der Evidenzhinreichendheit übertragbar ist, während die Definition
der korrekten Aktion domänenspezifisch und zuständigkeitsgebunden bleibt.

## QIK-VRT-Bindung

Das [Minimale Recovery-Theorem](../publications/2026-08-06-delayed-choice-hardware-witness/WHATSAPP_DECISION_SUFFICIENCY_DE.md)
formuliert die allgemeine Bedingung. Der Authority/Mirror/Witness-Fall ist eine
Spezialisierung: Ein Commit-Witness genügt nur dann, wenn die
repository-native Prüfung Epoche, Zustandsdigest, Herkunft und exakten Head
bindet. Ohne diese Bindung bleibt eine plausible Kopie keine kanonische
Fortsetzung.

Der finite Modellcheck und die formalisierten Quellen bleiben auf ihren
ausdrücklich genannten Scope begrenzt. Diese normative Übersetzung behauptet
keine empirische, physikalische, kryptographische, rechtliche oder medizinische
Bestätigung. Sie autorisiert keinen Merge, Push, Release, Deployment, Zenodo-
oder IETF-Effekt.

## Verdichtung

> Evidenz muss die Vergangenheit nicht vollständig rekonstruieren. Sie muss
> genau die Unterschiede tragen, von denen die gerechtfertigte Fortsetzung
> abhängt.

> Wo diese Unterschiede nicht sichtbar sind, ist nicht Raten
> universalisierbar, sondern transparente Begrenzung, Evidenzverfeinerung oder
> eine zuständig legitimierte sichere Baseline.
