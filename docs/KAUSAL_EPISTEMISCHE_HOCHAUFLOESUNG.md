# Kausal-epistemische Hochauflösung

## Kanonischer Satz

> **Kontext, Autorität und Bedeutung gehören zusammen.**
>
> q.e.d.  
> Ingolf Lohmann

## Zweck

Kausal-epistemische Hochauflösung bezeichnet die Fähigkeit eines Systems, handlungsrelevante Unterschiede über die gesamte Wirkungs- und Nachweiskette hinweg zu erhalten.

Eine Aussage ist nicht allein deshalb handlungsfähig, weil sie sprachlich verständlich oder technisch ausführbar ist. Sie muss an einen exakten Gegenstand und Zustand gebunden sein, ihre Bedeutung muss im jeweiligen Kontext bestimmt werden, die zuständige Autorität muss feststehen, die Evidenz muss zurechenbar sein und die behauptete Wirkung muss nach der Ausführung erneut beobachtet werden.

## Bindungsform

```text
BEDEUTUNG
= ABSICHT
+ BINDUNG
+ KONTEXT
+ AUTORITÄT
+ EVIDENZ
+ ZUSTAND
+ KAUSALORDNUNG
+ WIRKUNG
+ NACHWEIS
```

## Nicht-Gleichsetzungen

```text
REQUESTED     ≠ EXECUTED
EXECUTED      ≠ OBSERVED
OBSERVED      ≠ ACKNOWLEDGED
TRANSPORT_ACK ≠ EFFECT_ACK
RELATION      ≠ KAUSALITÄT
KAUSALITÄT    ≠ SEQUENZ
ABBILD         ≠ URSPRUNG
BEOBACHTUNG    ≠ GEGENSTAND
```

## Operative Priorisierung

Die richtige nächste Aktion ist nicht automatisch die leichteste Aufgabe und nicht automatisch die fernste Architekturvision.

```text
PRIORITÄT
= gegenwärtiger kausaler Engpass
× erreichbare Wirkung
× architektonische Anschlussfähigkeit
× überprüfbare Reversibilität
```

Daraus folgt:

> **Führe die kleinste gegenwärtig mögliche, kausal hinreichende und history-preserving Handlung aus, die den größten nachweisbaren Fortschritt in Richtung des tragenden Zielzustands erzeugt.**

Ein leicht erreichbarer Repair ist nur dann prioritär, wenn er einen aktuellen Blocker beseitigt, eine wiederkehrende Fehlerklasse schließt, eine Invariante stärkt, Beobachtbarkeit erhöht oder den nächsten größeren Schritt ermöglicht.

Eine langfristige Architektur ist nur dann operativ relevant, wenn sie die gegenwärtige Handlung bindet, ohne aktuelle Defekte liegen zu lassen.

## Fail-closed

Fehlen exakte Bindung, passende Autorität oder zurechenbare Evidenz, darf keine produktive Wirkung erfunden werden. Zulässige Fortsetzungen sind:

```text
NOOP
HOLD
REOBSERVE
REQUEST_AUTHORITY
```

## Spiegel-Invariante

Ein Spiegel erzeugt keine zweite Lichtquelle. Er erzeugt eine beobachtergebundene Projektion derselben kausal verbundenen Wirklichkeit.

```text
Lichtquelle
→ Ausbreitung
→ Reflexion
→ Beobachtung
→ Interpretation
```

Daraus folgt:

```text
Abbild ≠ Ursprung
Reflexion ≠ zweite Wirklichkeit
Kontext + Autorität + Bedeutung → verantwortbares Verstehen
```

## Geltungsgrenze

Diese Invariante verleiht keine unabhängige Review-Autorität und begründet weder `PASS`, `FINAL_PASS` noch `EFFECT_ACK_DONE`. Sie ersetzt keine fachliche Evidenz. Sie bindet lediglich die Bedingungen, unter denen eine Aussage oder Wirkung verantwortbar weiterverarbeitet werden darf.

## Repository-Anwendung

Jede geeignete Repository-Schicht soll diese Invariante entweder ausdrücken, maschinenlesbar referenzieren oder prüfen:

- Dokumentation erklärt Bedeutung und Grenze.
- Policy bindet die normativen Felder.
- Validator prüft Struktur und Pflichtinvarianten.
- Tests verhindern stilles Entfernen oder Umdeuten.
- CI macht Verletzungen sichtbar.
- Reviews und Effektpfade behalten ihre eigene Autorität und Exact-Head-Bindung.

Unterschiede erhalten. Anschlussfähig machen. Wirkung verantworten.
