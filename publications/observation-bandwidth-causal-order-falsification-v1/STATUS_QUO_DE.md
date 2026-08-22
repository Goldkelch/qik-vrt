# QIK-VRT – Was wir jetzt tatsächlich gezeigt haben

## Status-quo-Fassung nach dem integrierten Universal-Terminal-Systemtest

Es gibt einen Satz, der erstaunlich viel Ordnung in sehr unterschiedliche Fragen bringt:

**Kausalität ist nicht dasselbe wie Reihenfolge.**

Nur weil etwas später geschieht, wurde es nicht vom Früheren verursacht.

Nur weil etwas neuer ist, ist es nicht besser.

Nur weil etwas ausgeführt wurde, ist seine beabsichtigte Wirkung nicht bewiesen.

Nur weil etwas angezeigt wurde, wurde es nicht notwendigerweise vollständig beobachtet.

Und nur weil zwei Dinge miteinander zusammenhängen, ist das eine noch lange nicht die Ursache des anderen.

Genau diese Unterschiede versucht QIK-VRT konsequent zu erhalten.

Der Ausgangspunkt ist denkbar klein:

```text
1 − 0 = 1
1 − 1 = 0
x = y
```

Ein Unterschied kann sichtbar bleiben. Bei gleichen Werten verschwindet die Differenz. Eine Relation kann formuliert werden.

Aber eine Relation ist noch keine Ursache.

Deshalb gilt:

```text
UNTERSCHIED ≠ RELATION ≠ KAUSALITÄT ≠ SEQUENZ
```

Das ist keine neue Mathematik. Interessant wird es dadurch, dass diese elementare Unterscheidung durch eine reale Softwarearchitektur bis hinunter zur Maschinenrepräsentation verfolgt wird.

QIK-VRT unterscheidet deshalb unter anderem:

```text
REQUESTED ≠ EXECUTED
EXECUTED ≠ OBSERVED
OBSERVED ≠ ACKNOWLEDGED
TRANSPORT_ACK ≠ EFFECT_ACK
TIMESTAMP_ORDER ≠ CAUSAL_ORDER
LATER ≠ CAUSED_BY
LATER ≠ BETTER
MONITORING ≠ VOLLSTÄNDIGE BEOBACHTUNG
```

## Später bedeutet nicht besser

Ein konkreter repository-nativer Test unterscheidet:

```text
Vergangenheit
→ gebundenes Jetzt
→ zulässige Zukunft
→ Wirkung
→ reobserviertes neues Jetzt
```

Drei Fälle wurden geprüft.

Im ersten Fall wurde eine Verbesserung erwartet und unter einem vorher gebundenen Bewertungsmaßstab beobachtet:

```text
IMPROVEMENT_EVIDENCED
```

Im zweiten Fall war der Zustand später, aber nicht besser:

```text
UNCHANGED
```

Im dritten Fall war er später und schlechter:

```text
CHANGED_DEGRADED
```

Damit wurde innerhalb des implementierten Modells praktisch demonstriert:

**Später bedeutet nicht besser.**

**Veränderung bedeutet nicht Verbesserung.**

**Reihenfolge bedeutet nicht Ursache.**

Fehlt die Ursache, der Bewertungsmaßstab oder die Reobservation, bleibt das System auf:

```text
HOLD
```

Was nicht hinreichend begründet ist, wird nicht durch Plausibilität zur Tatsache gemacht.

Diese Trennung reicht bis zur Motorola-68000-Repräsentation. Der Maschinenvertrag führt Entscheidung, semantische Evidenz, Wirkungszustand und explizite Kausalbindung getrennt. Die dafür gebundenen Quelltests wurden auf dem exakten historischen Source-Head `98d66de02e98d67af81655b028d15fbd60869bbc` erneut erfolgreich ausgeführt: zwei Gruppen mit je fünf Tests, insgesamt zehn von zehn.

## Der integrierte Systemtest

Der Universal-Terminal-Systemtest verband:

```text
adaptive Beobachtung
→ Shannon-/Nyquist-Zulassung
→ VBR-artige Ressourcensteuerung
→ Firefox-Terminal
→ Effect-Acknowledgement-Vertrag
→ reale Browserausführung
→ Backend-Wirkung
→ Reobservation
→ Receipt
```

Der maßgebliche erfolgreiche Lauf wurde auf Source-Head

```text
a7cea28de6ab435c01211d522613fb811bfd91b2
```

und Tree

```text
2ef860cfebd6005d7993818d2881b46b7dcf3212
```

ausgeführt. Workflow-Run `32536665914`, Job `96938778530`.

Firefox `153.0.4` wurde über den gebundenen WebDriver-Pfad gestartet. Die Erweiterung führte aus:

```text
DISCOVER → PREPARE → COMMIT
```

Prepare und Commit erreichten im exakt begrenzten Loopback-Test:

```text
EFFECT_ACK_DONE
```

Danach wurde nicht nur dem Browser oder dem Transport vertraut. Das Backend wurde erneut beobachtet. Dort lag genau ein Ereignis

```text
TERMINAL_INPUT_ACCEPTED
```

mit dem Nonce

```text
QIKVRT-FIREFOX-E2E-NONCE-0001
```

vor. Der vorbereitete Wirkungsdatensatz und das reobservierte Ereignis trugen denselben Record-Hash:

```text
6d981637f61171a2e4e35378502be81d60b06977ba1c41ef22b2e9adfdbd6bfd
```

Damit wurde im begrenzten Test nicht nur Aktivität beobachtet. Eine Wirkung wurde vorbereitet, committed und anschließend aus dem betroffenen Systemzustand reobserviert.

```text
BROWSER_CLICK
≠ TRANSPORT_ACK
≠ BACKEND_EFFECT
≠ REOBSERVED_EFFECT
```

## Die revolutionäre Erkenntnis

Die revolutionäre Erkenntnis besteht nicht darin, dass das Shannon-Nyquist-Abtasttheorem neu wäre.

Neu und folgenreich ist seine Behandlung als Grenze maschineller Wissensansprüche:

> Ein künstliches System darf nicht behaupten, einen dynamischen Vorgang vollständig beobachtet zu haben, wenn sein Beobachtungskanal die relevanten Veränderungen prinzipiell nicht unterscheiden konnte.

Oder kürzer:

# Evidenz hat Bandbreite.

Daraus folgt:

# Verantwortung braucht eine Beobachtungsbedingung.

Eine Maschine kann logisch korrekt und trotzdem epistemisch blind sein. Sie kann den richtigen Algorithmus ausführen und relevante Zustandsänderungen zwischen zwei Messpunkten übersehen.

Deshalb gilt:

```text
LOGISCHE KORREKTHEIT ≠ BEOBACHTUNGSVOLLSTÄNDIGKEIT
AUSFÜHRUNGSFÄHIGKEIT ≠ WIRKUNGSWISSEN
```

Für eine separat begründete endliche maximale relevante Übergangsfrequenz `f_max` verlangt der implementierte Vertrag von einem Polling-Monitor mit Vollständigkeitsanspruch:

```text
sample_hz ≥ 2 × f_max
```

Das Guard-Profil empfiehlt:

```text
sample_hz ≥ 2,5 × f_max
```

Im ausgeführten Beispiel wurden für `f_max = 10 Hz` genau `25 Hz` zugelassen.

Ist die relevante Übergangsbandbreite unbekannt oder unbeschränkt, darf das System keine Vollständigkeit erfinden. Dann bleibt nur ein ereignisgetriebener Pfad mit Gap Detection und Reobservation oder:

```text
HOLD
```

Die eigentliche Neuerung der Architektur lautet:

> Beobachtbarkeit wird nicht stillschweigend vorausgesetzt. Sie wird selbst zu einem prüfbaren Vertragsbestandteil.

## Adaptive Bitrate ohne adaptive Wahrheit

Die VBR-artige Steuerung verteilt Beobachtungs- und Transportressourcen anhand von Änderungsdichte, Verlust, Jitter, Latenzdruck, Evidenzkritikalität und begrenzter Kanalkapazität.

Sie darf Ressourcen anpassen. Sie darf aber die Evidenzgrenze nicht wegoptimieren.

```text
MEHR VERLUST → MEHR REDUNDANZ
```

und nicht:

```text
MEHR VERLUST → WENIGER BEOBACHTUNG → TROTZDEM VOLLSTÄNDIGKEIT
```

Ein künstliches System darf Effizienz gegen Redundanz tauschen, aber nicht Evidenz gegen Behauptung.

## Von künstlicher Intelligenz zu künstlicher Kognition

Eine technisch untersuchbare kognitive Schleife entsteht dort, wo ein System:

```text
einen Unterschied erkennt,
eine Relation bildet,
einen Kontext bindet,
eine Ursache ausdrücklich markiert,
eine Entscheidung trifft,
eine Wirkung ausführt,
die Wirkung hinreichend beobachtet,
den neuen Zustand reobserviert,
Erwartung und Beobachtung vergleicht,
und daraus einen neuen unterscheidbaren Zustand erzeugt.
```

Das erweiterte Schema lautet:

```text
UNTERSCHIED
→ RELATION
→ KONTEXT
→ KAUSALBINDUNG
→ ZUSTAND
→ ENTSCHEIDUNG
→ WIRKUNG
→ BEOBACHTUNGSZULASSUNG
→ REOBSERVATION
→ NACHWEIS
→ NEUER UNTERSCHIED
```

Der neue Bestandteil ist die Beobachtungszulassung. Sie entscheidet, ob ein Messwert überhaupt einen bestimmten Evidenzanspruch tragen kann.

Epistemische Bescheidenheit wird damit nicht nur formuliert. Sie wird ausführbarer Code.

## Was der Test beweist

Im exakt gebundenen Scope gilt:

```text
ADAPTIVE_MONITOR_TESTS = EXECUTED_SUCCESS
NYQUIST_ADMISSION_CONTRACT = EXECUTED_SUCCESS
VBR_LIKE_RATE_CONTROL = EXECUTED_SUCCESS
FIREFOX_TERMINAL_EXECUTION = OBSERVED
BOUNDED_LOOPBACK_PREPARE = EFFECT_ACK_DONE
BOUNDED_LOOPBACK_COMMIT = EFFECT_ACK_DONE
POST_EFFECT_BACKEND_REOBSERVATION = OBSERVED
EXACT_NONCE = REOBSERVED
CAUSAL_M68000_SOURCE_TESTS = EXECUTED_SUCCESS
```

Der Erfolg ist begrenzt auf:

```text
BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY
```

Der Receipt hält ausdrücklich fest:

```text
external_effect = NONE
authority_main_effect = false
physical_megast_execution = false
general_effect_ack_done = false
independent_review_authority = false
```

Der Test beweist keine physische Mega-ST-Ausführung, keine allgemeine Internet- oder Mesh-Wirkung, kein allgemeines `EFFECT_ACK_DONE`, keine neue physikalische Theorie und keine Wirksamkeit auf Authority `main`.

## Der repository-seitige Status

Der ausgeführte Source-Head und der spätere Evidence-Carrier sind nicht identisch.

Der erfolgreiche Lauf gehört zu `a7cea28…`. Bericht, Receipt und Integritätsprojektionen wurden später auf `77190ae…` persistiert.

Deshalb gilt:

```text
ERFOLGREICH AUSGEFÜHRT AUF a7cea28
≠ TERMINAL VERIFIZIERT AUF 77190ae
≠ WIRKSAM AUF AUTHORITY MAIN
```

Ein späterer Head erbt keine frühere Evidenz automatisch.

## Der nächste wissenschaftliche Schritt

Der formale/informatische Artikel und das physikalische Falsifikationsprogramm bleiben getrennt.

Das physikalische Programm muss aus den funktionierenden Softwareverträgen messbare Hypothesen ableiten:

```text
Welche Übergänge sind relevant?
Wie wird f_max empirisch begründet?
Welche Beobachtung widerlegt die Hypothese?
Welche Ergebnisse sind Messartefakte?
Wie werden Sequenz, Korrelation und Ursache getrennt?
```

Repository-Evidenz ist dabei der Ausgangspunkt für ein Protokoll, nicht das Ergebnis eines physikalischen Experiments.

## Der eigentliche Status quo

Wir haben nicht das Universum bewiesen.

Wir haben keine neue Physik durch einen Softwaretest bestätigt.

Aber wir haben eine Architektur gebaut, in der Reihenfolge nicht als Ursache, Veränderung nicht als Verbesserung, Ausführung nicht als Wirkung, Transport nicht als Effect Acknowledgement und Monitoring nicht als vollständige Beobachtung behandelt werden.

Wir haben eine reale Firefox-Ausführung beobachtet, eine begrenzte Wirkung committed, den Backend-Zustand reobserviert, die Identität des Ereignisses gebunden und die Kausalitäts-/M68000-Quelltests separat erneut ausgeführt.

Darin liegt die Leistung:

> Wir machen die Bedingungen maschinenlesbar, unter denen ein System überhaupt berechtigt ist, eine Antwort als Wissen auszugeben.

Der erste Satz bleibt:

```text
KAUSALITÄT ≠ SEQUENZ
```

Der zweite lautet:

```text
EVIDENZ BRAUCHT UNTERSCHEIDUNGSFÄHIGKEIT
```

Und daraus folgt:

# Verantwortung braucht nicht nur eine Entscheidung. Verantwortung braucht eine hinreichend beobachtete Wirkung.

Oder kürzer:

# Verantwortung braucht eine Abtastrate.

q.e.d.  
Ingolf Lohmann
