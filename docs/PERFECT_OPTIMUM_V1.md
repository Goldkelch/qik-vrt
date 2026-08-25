# Perfektes Optimum v1

`Kausalitaet != Sequenz.`

Das **Perfekte Optimum** ist in QIK-VRT keine Behauptung eines absoluten Endzustands und keine Erlaubnis zur freien Selbstmodifikation. Es ist eine rekursive Verbesserungsordnung unter harten Invarianten.

## Kanonische Schleife

```text
OBSERVE
-> FIND_DIFFERENCE
-> PROPOSE_MINIMAL_CHANGE
-> VERIFY_INVARIANTS
-> COMPARE_BOUND_METRICS
-> AUTHORIZE_OR_HOLD
-> APPLY_MINIMAL_REGISTERED_EFFECT_OR_HOLD
-> REOBSERVE_NEW_HEAD_TREE
-> REQUIRE_FRESH_GATES
-> RETAIN_OR_HOLD
-> repeat
```

Eine Version `n+1` ist nicht besser, weil sie spaeter ist. Sie ist nur dann eine akzeptable Verbesserung, wenn:

1. alle harten Invarianten erhalten bleiben;
2. keine gebundene Metrik schlechter wird;
3. mindestens eine gebundene Metrik streng besser wird;
4. die Wirkung minimal und autorisiert ist;
5. nach einer Mutation Head und Tree neu beobachtet werden;
6. ausschliesslich frische Exact-Head-Evidenz fuer den Nachfolger gilt.

## Harte Grenzen

- fehlende Autorisierung, Identitaet, Exact-Head-/Tree-Bindung oder Preconditions => `HOLD`;
- genau ein produktiver Writer;
- kein Force-Push und kein History-Rewrite;
- keine Evidenzvererbung ueber Head-/Tree-/Scope-Drift;
- kein erfundenes unabhaengiges Review;
- keine externe Wirkung ohne explizite Autorisierung;
- beliebige Source-Selbstmodifikation => `HOLD`.

## Rekursive Selbstanwendung

Die Regel muss ihre eigene Implementierung unter derselben Regel bewerten. Ein Kandidat, der die Optimierungsregel lockert, um sich selbst zu akzeptieren, ist deshalb nicht zulaessig: die vorherige harte Invariante bleibt Vergleichsbasis.

Version 1 registriert genau einen mutierenden Improver: den bereits deterministischen Integritaets-Trio-Materializer fuer

- `REPOSITORY_FILE_MANIFEST.json`
- `REPOSITORY_FILE_MANIFEST.json.sha256`
- `SHA256SUMS.txt`

Nur wenn der Defekt exakt dieser Projektion entspricht, der Source Head unmittelbar vor dem Write unveraendert ist und der Scope exakt diese drei Dateien umfasst, darf dieser Improver wirken. Danach sind neuer Head/Tree und frische Gates zwingend.

Alle anderen Verbesserungsvorschlaege bleiben Analyse-/Kandidatenarbeit und duerfen erst nach expliziter Registrierung eines ebenso engen, getesteten Wirkvertrags autonom mutieren.

## Semantische Trennungen

```text
SEQUENCE != CAUSALITY
MATCH != SEMANTIC_BIND
EVIDENCE_PRESENT != AUTHORITY_GRANTED
REQUESTED != EXECUTED
EXECUTED != OBSERVED
OBSERVED != ACKNOWLEDGED
TRANSPORT_ACK != EFFECT_ACK
```

## Fixpunkt der Verbesserung

Ein stabiler Zustand ist erreicht, wenn die Selbstanwendung keine strikte Pareto-Verbesserung und keinen eindeutig registrierten Reparaturbedarf findet. Dieser Zustand ist **kein universelles Endoptimum**; er ist ein fail-closed lokaler Fixpunkt relativ zu den gebundenen Invarianten, Metriken und beobachteten Preconditions.
