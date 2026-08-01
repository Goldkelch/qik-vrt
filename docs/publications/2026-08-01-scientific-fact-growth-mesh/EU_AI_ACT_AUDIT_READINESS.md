<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# EU-AI-Act-Auditbereitschaft ab 2. August 2026

## Statushinweis

Dies ist eine technische Vorbereitung, keine Rechtsberatung, keine
Konformitätsbewertung und kein Zertifikat. Einsatzrolle, Risikoklasse,
Jurisdiktion und aktueller konsolidierter Normtext müssen für jedes reale
System separat bestimmt werden.

Nach den am 1. August 2026 abrufbaren Angaben der Europäischen Kommission gilt
der AI Act grundsätzlich ab 2. August 2026; einzelne Pflichten gelten bereits
seit 2025, während bestimmte Hochrisikoregeln durch die 2026 beschlossene
Omnibus-Änderung spätere Termine besitzen. Die Kommission nennt für Artikel 50
den 2. August 2026 als Anwendungsbeginn. Maßgeblich bleiben EUR-Lex und die
jeweils geltende konsolidierte Rechtslage.

## Technische Anschlussstellen

| Auditfrage | QIK-VRT-Objekt | Grenze |
| --- | --- | --- |
| Welche Ausgabe wurde wann erzeugt? | content-addressed claim/output object + Zeitbindung | Uhr- und Identitätsvertrauen separat prüfen |
| War Inhalt KI-generiert oder transformiert? | Provenienzkette mit Tool-/Modellversion und Human-/Machine-Rollen | Provenienz beweist nicht Richtigkeit |
| Welche Daten, Modelle und Policies wirkten mit? | source, evidence, model und policy digests | Vollständigkeit muss auditiert werden |
| Welche Unsicherheit und Alternativen waren bekannt? | observation envelope + open questions | keine automatische Angemessenheitsgarantie |
| Warum wurde eine Wirkung freigegeben? | Gate-Report + EFFECT_ACK + Effect Receipt | vollständige Mediation real nachweisen |
| Kann eine betroffene Person widersprechen? | versionierter Dispute-/Redress-Knoten | rechtliche Eignung separat prüfen |
| Wurden offene Claims als Fakten ausgegeben? | epistemische Klassifikation + Projection Gate | Natural-Language-Extraktion bleibt reviewpflichtig |
| Sind Änderungen nachvollziehbar? | append-only Vorgänger-/Nachfolgerkette | Git allein ist keine Aufbewahrungsgarantie |

## Auditpaket pro Entscheidung

Ein belastbares Auditpaket sollte mindestens enthalten:

1. Rollen- und Systemklassifikation;
2. exakten Input- und Outputdigest;
3. Modell-, Software- und Policyversion;
4. Datenherkunft, Rechtsgrundlage und Zweckbindung;
5. epistemische Claimklassifikation;
6. Mess-, Unsicherheits- und Kalibrierungsangaben;
7. Risiken, Gegenclaims und bekannte Grenzen;
8. Human-Oversight- und Redresspfad;
9. Gateauswertung und separate Effect-Autorisierung;
10. beobachtete Nachwirkung und Incident-Verknüpfung;
11. Aufbewahrungs-, Zugriffs- und Löschregeln; und
12. exakten Authority-/Mirror- beziehungsweise Archivstand.

## Noch zu auditieren

Das vorliegende Paket implementiert eine epistemische und technische
Nachweisschicht. Es bewertet noch nicht:

- die konkrete Anbieter-/Betreiberrolle;
- die Risikoklasse eines realen Systems;
- Grundrechte-Folgenabschätzung, Datenschutz-Folgenabschätzung oder
  Cybersecurity-Konformität;
- Artikel-für-Artikel-Erfüllung;
- Qualität und Repräsentativität realer Trainings-/Testdaten;
- reale Human-Oversight-Wirksamkeit;
- Barrierefreiheit und sprachliche Verständlichkeit im Einsatz;
- Marktüberwachung, Incident-Meldung oder Post-Market-Monitoring; und
- harmonisierte Normen beziehungsweise Common Specifications.

## Primärquellen

- Verordnung (EU) 2024/1689, EUR-Lex, CELEX `32024R1689`.
- Europäische Kommission, „Navigating the AI Act“, abgerufen am 1. August
  2026.
- Europäische Kommission, FAQ zu Transparenzpflichten nach Artikel 50,
  abgerufen am 1. August 2026.
