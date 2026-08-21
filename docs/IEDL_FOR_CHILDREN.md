# PO-Receipt #245 — `IEDL_⊕_FÜR_KINDER_⊕_ERKLÄRT`

Status: `BOUND` | `TAU=♾️` | `D0=3` | `EINFACH`

## IEDL ist wie „Erst Denken, Dann Machen“

Stell dir vor, du hast einen Roboter.

Bei anderen Robotern sagst du: „Mach!“ Und er macht sofort. Auch wenn es Quatsch ist.

Dein Roboter IEDL stellt zuerst sieben Fragen:

1. **MATCH** — „Habe ich dich richtig verstanden?“
2. **PARSE** — „Weiß ich, was die einzelnen Worte bedeuten?“
3. **BIND** — „Macht das überhaupt Sinn? Ist 1 größer als 0?“
4. **BEWEIS** — „Zeig mir 3 Beweise. Ein Bild, ein Ton, und jemand sagt es.“
5. **ENTSCHEIDE** — „Okay. Soll ich jetzt GO oder lieber HOLD sagen?“
6. **MACH** — „Ich mach es. Aber ich halte meinen Lieblingsstein fest. Der Stein Nr. 3. Der darf nie kaputt gehen.“
7. **SCHAU NACH** — „Ist es wirklich besser geworden? Habe ich geholfen?“

Erst wenn alle notwendigen Freigaben für den produktiven Pfad vorliegen, darf **MACH** eine produktive Wirkung auslösen. Ein nicht erfüllter Gate darf nicht durch optimistische Annahmen übersprungen werden.

## Die drei wichtigsten Regeln

### 1. `1 - 0 = 1`

Es muss einen relevanten Unterschied geben. Sonst muss man nichts verändern.

### 2. Stein Nr. 3 bleibt Stein Nr. 3

Beim Verbessern muss die geschützte Invariante erhalten bleiben.

### 3. Kein Beweis = kein Machen

Nur reden reicht nicht. Evidenz muss vor einer produktiven Wirkung gebunden sein. Bild, Ton und Aussage sind die kindgerechten Beispiele dieses Receipts; welche Evidenz einen konkreten technischen Claim trägt, bleibt claim-spezifisch.

## Perfektes Optimum

„Besser“ bedeutet in dieser einfachen Fassung gleichzeitig:

```text
SCHUTZINVARIANTE_ERHALTEN
AND
MINDESTENS_EIN_RELEVANTER_UNTERSCHIED_VERBESSERT
```

Bloß später zu sein beweist keine Verbesserung:

```text
LATER != BETTER
ACTIVITY != IMPROVEMENT
EXECUTED != OBSERVED
```

Nach **MACH** folgt deshalb zwingend **SCHAU NACH**. Erst die Reobservation darf Evidenz darüber liefern, ob die beabsichtigte Verbesserung tatsächlich eingetreten ist.

## Siebenstufiger ausführbarer Vertrag

```text
MATCH
→ PARSE
→ BIND
→ BEWEIS
→ ENTSCHEIDE
→ MACH
→ SCHAU NACH
↺
```

Sicherheitsrichtung:

```text
MACH
→ MATCH_OK
  AND PARSE_OK
  AND BIND_OK
  AND EVIDENCE_OK
  AND DECISION_ALLOWS_EFFECT
  AND PROTECTED_INVARIANT_PRESERVED
```

Wirkungsrichtung:

```text
MACH != SUCCESS

MACH
+ SCHAU_NACH
+ PROTECTED_INVARIANT_PRESERVED
+ RELEVANT_IMPROVEMENT_OBSERVED
→ VERIFIED_IMPROVEMENT_EVIDENCE
```

## Fail-closed Negativfälle

```text
NO MATCH       → NO PRODUCTIVE EFFECT
NO PARSE       → NO PRODUCTIVE EFFECT
NO BIND        → NO PRODUCTIVE EFFECT
NO EVIDENCE    → NO PRODUCTIVE EFFECT
NO AUTHORIZED DECISION → NO PRODUCTIVE EFFECT
INVARIANT WOULD BREAK  → NO PRODUCTIVE EFFECT
```

`HOLD`, `REOBSERVE`, `REQUEST_AUTHORITY` und `NOOP` bleiben zulässige nicht-produktive Ergebnisse der technischen Entscheidungsebene. `D0=3` bleibt `REQUEST_AUTHORITY`; es wird nicht mit dem geschützten Register-/Fixpunktbegriff gleichgesetzt.

## Beweisgrenze

Dieses Dokument persistiert die Product-Owner-Semantik und den daraus abgeleiteten ausführbaren Vertrag. Es behauptet **noch nicht**, dass das siebenstufige End-to-End-Fixture bereits ausgeführt oder Lean/Lake-kernelverifiziert wurde.

Für den Implementierungsbeweis sind separat erforderlich:

- ein positiver Witness durch alle sieben Stufen;
- mindestens ein Negativfixture pro fail-closed Gate;
- Nachweis, dass `MACH` ohne die Vorgates keinen produktiven Effekt erzeugen kann;
- Nachweis der geschützten Invariante;
- Reobservation des Nachzustands;
- Vergleich gegen den gebundenen Vorzustand;
- Exact-Head/Tree-Bindung der ausgeführten Evidenz.

Damit bleibt die einfache Fassung wahr, ohne die Beweisstufen zu vermischen.

## In fünf Worten

**Erst beweisen. Dann anfassen.**

`TEMDD ist damit als Zielvertrag klar gebunden.`

`eins und nicht keins`

`q.e.d.`
