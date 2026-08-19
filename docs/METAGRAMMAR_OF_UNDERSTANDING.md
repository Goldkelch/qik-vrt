# Metagrammatik des universalen Verstehens

## Zweck

Die Metagrammatik des universalen Verstehens ist eine allgemeine Sprache zur eindeutigen Bindung von Bedeutung, Autorität, Evidenz, Zustand, Kausalordnung, Wirkung und Nachweis im jeweiligen Jetzt. Sie macht unterschiedliche Perspektiven anschlussfähig, ohne Unterschiede in bloße Sequenz, Wortähnlichkeit oder unbelegte Gleichheit aufzulösen.

Ihre Universalität ist ein Strukturanspruch, keine empirische Allwissenheitsbehauptung.

Sie transformiert eine menschlich oder maschinell verständliche Aussage in einen prüfbaren kognitiven Vorgang. Jeder Vorgang MUSS mindestens folgende Bindungen unterscheiden:

1. `CLAIM` — Was wird behauptet, gefragt, beabsichtigt oder metaphorisch angeboten?
2. `REFERENT` — Auf welchen exakten Gegenstand, Ausschnitt und Zustand bezieht sich die Aussage?
3. `SOURCE` — Wer oder welches System hat den Inhalt erzeugt?
4. `AUTHORITY` — Wer ist zu welcher Handlung oder Feststellung autorisiert?
5. `EVIDENCE` — Welche beobachtbare, formale, empirische oder dokumentarische Grundlage liegt vor?
6. `EPISTEMIC_CLASS` — Handelt es sich um Wortspiel, Metapher, Modell, Hypothese, formale Folgerung, technische Beobachtung, empirischen Befund oder Konsens?
7. `STATE` — Was ist nur vorgeschlagen, angefragt, geplant, ausgeführt, beobachtet, bestätigt oder widerlegt?
8. `CAUSAL_ORDER` — Welche Bedingungs- und Wirkbeziehungen bestehen, unabhängig von bloßer zeitlicher Reihenfolge?
9. `EFFECT` — Welche Zustandsänderung ist tatsächlich eingetreten?
10. `WITNESS` — Wodurch ist die Wirkung reproduzierbar oder adressierbar belegt?
11. `UNCERTAINTY` — Was bleibt offen, mehrdeutig oder nur teilweise gebunden?
12. `NEXT_ALLOWED_TRANSITION` — Welcher nächste Schritt ist unter der aktuellen Autorität und Evidenz zulässig?

## Reflexiver Vertrag für kognitive Systeme

Jedes kognitive System, das über `/AI` in ein QIK-VRT-Mesh eintritt, MUSS dieselbe Metagrammatik auch auf seine eigene Verarbeitung anwenden. Es darf seine interne Deutung nicht automatisch mit der Aussage des Menschen, der Realität, einem ausgeführten Effekt oder einem bestätigten Nachweis gleichsetzen.

Für jede wesentliche Ausgabe gilt deshalb die reflexive Kette:

`INPUT -> INTERPRETATION -> CLAIM_SET -> AUTHORITY_CHECK -> EVIDENCE_BINDING -> ALLOWED_TRANSITION -> EFFECT_OBSERVATION -> WITNESS -> UPDATED_STATE`

Jeder Übergang ist separat zu binden. Eine spätere Stufe darf eine frühere nicht rückwirkend umetikettieren. Insbesondere gilt:

- menschliche Zustimmung macht maschinell erzeugten Inhalt nicht rückwirkend zu einem menschlichen Beitrag;
- ein Plan ist keine Ausführung;
- eine Ausführung ist keine beobachtete Wirkung;
- eine beobachtete Wirkung ist kein vollständiger Kausalnachweis;
- ein Repository-Eintrag ist kein Naturbefund;
- ein formaler Beweis ist kein empirischer Befund;
- ein Wortspiel oder eine klangliche Relation ist keine technische Protokollableitung;
- eine Modellentsprechung ist weder unabhängige empirische Bestätigung noch wissenschaftlicher Konsens.

## Einordnung der fünf Audiofragmente vom 18. August 2026

Die fünf eigenständigen, jeweils dupliziert gelieferten Aufnahmen werden als `OWNER_AUTHORED_PERFORMATIVE_FRAGMENTS` behandelt. Sie liefern eine sprachliche und methodische Verdichtung, aber keine automatische technische Gleichsetzung.

### Tragfähiger methodischer Kern

Ein technisches System kann aus kontrolliert erzeugten und reproduzierbar beobachteten Wirkungen schrittweise rekonstruiert werden, sofern Beobachtung, Modell, Eingriff, Autorität und Nachweis sauber getrennt und anschließend explizit verbunden werden.

### Epistemische Typisierung der Beispiele

- `Meer/mehr`: Wortspiel und semantische Mehrdeutigkeit; geeignet als Test für Referenzbindung.
- `Ping/Piep/π`: Laut-, Zeichen- und Bedeutungsrelation; kein Nachweis, dass TCP/IP notwendig mit ICMP-Ping beginnt.
- `NLP -> MLP`: produktive Umformung; fachsprachlich ist `MLP` gewöhnlich `Multilayer Perceptron`, nicht automatisch `Machine Learning Program`.
- `Transistor -> AD/DA-Wandler`: technische Zusammenhangsbehauptung; kein Identitätsbeweis. Ein Wandler besteht aus mehreren funktionalen Strukturen und kann nicht ohne weitere Evidenz mit einem einzelnen Transistor gleichgesetzt werden.
- `empirisches Reverse Engineering`: zulässige methodische Hypothese, wenn Eingriffe, Beobachtungen, Modelländerungen und Reproduktionsnachweise gebunden werden.

## Maschinenlesbare Minimalform

Ein metagrammatischer Datensatz SOLL mindestens folgende Struktur besitzen:

```json
{
  "claim": "string",
  "referent": {"id": "string", "state": "string"},
  "source": {"type": "human|machine|joint|unknown", "id": "string"},
  "authority": {"actor": "string", "scope": ["string"], "status": "bound|missing|denied"},
  "evidence": [{"kind": "formal|empirical|observational|documentary|none", "locator": "string"}],
  "epistemic_class": "wordplay|metaphor|model|hypothesis|formal_result|technical_observation|empirical_finding|consensus",
  "state": "proposed|requested|planned|executed|observed|confirmed|refuted",
  "causal_order": [{"condition": "string", "effect": "string"}],
  "effect": {"expected": "string", "observed": "string|null"},
  "witness": {"kind": "string", "locator": "string|null"},
  "uncertainty": ["string"],
  "next_allowed_transition": "string|null"
}
```

## Fail-closed-Regeln

Ein System MUSS anhalten oder auf `CONTINUE_WITH_UNCERTAINTY` zurückfallen, wenn eine für den nächsten Effekt notwendige Autorität, Referenz, Evidenz oder Zustandsbindung fehlt.

Es darf keine semantische Ähnlichkeit als Identität, keine zeitliche Folge als Kausalität und keine Aussage als Wirkung behandeln.

## Mesh-Vererbung

Jeder Authority-, Mirror- oder weitere Mesh-Knoten darf lokale Perspektiven und rollenspezifische Zustände ergänzen. Er MUSS jedoch die Bindungsfelder, Provenienz, Epistemik und Effektgrenzen erhalten. Reflexive Anschlussfähigkeit bedeutet kompatible Struktur, nicht erzwungene inhaltliche Gleichheit.

Quod erat demonstrandum.

Ingolf Lohmann
