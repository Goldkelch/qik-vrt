# Formale Geltungsgrenze

## 1. Was „vollständig“ hier bedeutet

Vollständig ist die Formalisierung im prüfmethodischen Sinn: Jede tragende
Aussage des 62-seitigen Dokuments ist in der Claim-Matrix auffindbar,
klassifiziert, mit Seitenbezug, Annahmen, Evidenz, Falsifikationskriterium und
gegebenenfalls einem auflösbaren Lean-Namen versehen. Kein Claim darf seinen
Typ wechseln, ohne dass Zod, Python oder ein Negativtest die Änderung erkennt.

Vollständig bedeutet nicht, dass offene Naturfragen durch Deklaration zu
Theoremen werden. Ein Proof Assistant kann einen Schluss aus formalisierten
Annahmen prüfen; er kann nicht selbst bestätigen, dass eine frei gewählte
Korrespondenz die reale Raumzeit beschreibt.

## 2. Drei Ebenen des Wortes „Universum“

1. **Grundbereich:** Für einen ausdrücklich gewählten Bereich `U` bilden eine
   Klasse und ihr relatives Komplement eine disjunkte vollständige Partition.
2. **Modelluniversum:** Eine totale Korrespondenz kann diese Partition auf einen
   Modellbereich zurückziehen. Dafür sind Totalität und Bereichstreue Annahmen.
3. **Empirischer Kosmos:** Die Identifikation des Modelluniversums mit der
   physischen Raumzeit ist eine Korrespondenzhypothese und benötigt
   dimensionsrichtige Observablen, Messprotokolle und neue Vorhersagen.

Nur Ebene 1 ist ohne Zusatzannahmen ein mengentheoretisches Theorem.

## 3. Quantisierbar ist nicht quantisiert

Das Lean-Modul `Quantizability.lean` konstruiert einen Raum unendlicher
Bitströme. Für jede endliche Präzision gibt es eine endliche Präfixcodierung;
gleichzeitig bestimmt keine endliche Präzision den ganzen Zustand. Damit ist
der Schluss von beliebig feiner endlicher Darstellung auf ontische endliche
Auflösung widerlegt.

Die Planck-Länge ist eine natürliche dimensionsrichtige Skala. Daraus folgt
ohne weitere Theorie und Messung kein kleinstes Raumzeitpixel.

## 4. Retrokausalität

Formal getrennt werden:

- Retrodiktion: spätere Daten verbessern eine Aussage über Früheres;
- semantische Rückbestimmung: spätere Ordnung ändert ein früheres Label;
- Zeitumkehrsymmetrie: Gleichungen besitzen zeitgespiegelte Lösungen;
- Zwei-Randbedingungen-Modelle: Lösungen hängen von Anfangs- und Enddaten ab;
- ontische Retrokausalität: spätere physische Bedingungen stehen in einer
  wirklichen Abhängigkeitsrelation zu Früherem;
- operative Rückwärtssignalisierung: eine frei wählbare spätere Intervention
  verändert eine früher lokal auslesbare Statistik;
- geschlossene zeitartige Kurven: globale Raumzeitstruktur mit eigener
  Konsistenzproblematik.

Das formalisierte autonome Vorwärtsmodell besitzt keinen Rückwärtskanal:
Zustand `n` hängt nur vom Eingabepräfix vor `n` ab. Semantische
Reklassifikation überschreibt den früheren Record nicht. Das widerlegt keine
denkbare alternative Physik mit Endrandbedingungen; es zeigt präzise, welche
zusätzliche Struktur ein retrokausales Modell definieren müsste.

## 5. Einheiten und Physik

`Dimensions.lean` modelliert jede Größe als Exponentenvektor der sieben
SI-Basisdimensionen. Geprüft werden die Dimensionen der Einstein-Kopplung, der
Planck-Längen-, Planck-Zeit- und Planck-Massenkombination sowie des normierten
Bekenstein-Hawking-Faktors.

Dimensionshomogenität ist eine notwendige Zulässigkeitsbedingung. Sie liefert
weder Zahlenwerte noch Dynamik, keine Fehlerrechnung und keinen empirischen
Beleg. Die kausale Reihenfolge lautet deshalb:

```text
Definitionen → mathematische Konsistenz → Dimensionshomogenität
→ Korrespondenzregeln → quantitative Vorhersage → Experiment → Replikation
```

## 6. Prüfschutz gegen Überhöhung

Die Prüfer blockieren insbesondere:

- Korrelation ⇒ Kausalität;
- Visualisierung ⇒ physikalische Entdeckung;
- Modellstruktur ⇒ Identität mit der Realität;
- Quantisierbarkeit ⇒ fundamentale Quantisierung;
- spätere Interpretation ⇒ frühere Zustandsänderung;
- KI-Erklärung ⇒ Beweis;
- mathematische Anschlussfähigkeit ⇒ empirische Bestätigung;
- ontologische oder normative Aussage ⇒ Naturtheorem.

