<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QCE formalization roadmap

Der vorhandene `Std`-Kern ist ein endlicher Modell- und Anspruchsvertrag. Die
vollständige mathematisch-physikalische Formalisierung verlangt additive,
getrennt reviewbare Module. Kein Modul darf durch einen Bool-Zeugen ersetzt und
danach als physikalische Herleitung ausgegeben werden.

## F0 - endlicher Modellvertrag

**Vorhanden:** `VRTCore_QCE_Model.lean`

- Zweischrittordnung
- Identitäts- und Paarrecord-Erhaltung
- Unsicherheitskomponenten
- klassisches-Kegel-Gate
- monotone finite Netzwerkerweiterung
- fail-closed physikalische Closure
- Kernel/Empirie-Trennung

## F1 - Zustandsraum und Observablen

Vorgesehene Datei: `QCE_StateSpace.lean`

Erforderliche Gegenstände:

- komplexer Hilbertraum oder präzise algebraische Zustandsstruktur,
- normierte Zustände und Dichtematrizen,
- Observablen und Spektralprojektoren,
- Erwartungswerte, Varianzen und Domänenbedingungen,
- explizite Trennung von Modellzeit und emergenter Zeit.

Schließung: alle verwendeten Operatoren sind wohldefiniert; keine
klassische Zielmetrik wird vorausgesetzt.

## F2 - Heisenberg-/Robertson-Bilanz

Vorgesehene Datei: `QCE_Uncertainty.lean`

- Nichtkommutativität,
- Robertson-Schrödinger-Relation,
- Kovarianzmatrizen,
- instrumentelle und modellbedingte Unsicherheit als getrennte Daten,
- Beweis, dass Rekonstruktion die irreduzible Schranke nicht entfernt.

Schließung: die im Fachartikel verwendete Unsicherheitszerlegung ist als
klar begrenztes Modell oder als allgemeinerer Kovarianzsatz formalisiert.

## F3 - Zweischrittisometrie

Vorgesehene Datei: `QCE_TwoStepIsometry.lean`

- Zustandsräume vor, zwischen und nach den beiden Schritten,
- lineare Operatoren für beide Übergänge,
- Isometrie oder unitäre Dilatation,
- Komposition und Normerhaltung,
- Energie-Impuls-Bilanz im angegebenen Modell.

Schließung: die Zwei-Schritt-Reihenfolge ist nicht nur ein Indexrecord,
sondern eine wohldefinierte Dynamik.

## F4 - physikalische Paarverschränkung

Vorgesehene Datei: `QCE_EntangledPair.lean`

- Tensorproduktstruktur,
- Schmidt-Zerlegung im endlichen Scope,
- Separabilitätsdefinition,
- Verschränkungszeuge,
- Monogamie- und Purifikationsgrenzen.

Schließung: ein erzeugter Zustand ist im mathematischen Sinn nachweislich
nicht separabel.

## F5 - globale Informationsintegration

Vorgesehene Datei: `QCE_GlobalNetwork.lean`

- induktive Netzwerkerweiterung,
- globale Zustandskonsistenz,
- Nichtfaktorisierung zum Altbestand,
- Informations- und Entropieinvarianten,
- keine unabhängige-Paar-Falle.

Schließung: neue Paare werden beweisbar an die bestehende Gesamtstruktur
gebunden.

## F6 - quantische Kausalstruktur

Vorgesehene Datei: `QCE_QuantumCausality.lean`

- operationale Ereignisse,
- zulässige Signalisierungsrelationen,
- partielle oder unbestimmte Kausalordnung,
- Projektoren oder Prozessobjekte für kausale Klassifikation,
- Ausschluss widersprüchlicher Zyklen im erklärten Scope.

Schließung: Kausalität wird nicht aus Dateireihenfolge oder klassischer
Koordinate abgeleitet.

## F7 - Grobkörnung und klassischer Lichtkegel

Vorgesehene Datei: `QCE_ClassicalConeLimit.lean`

- Grobkörnungsabbildung,
- effektive Metrik,
- Stabilität der Nullgrenze,
- Skalierung der Fluktuationen,
- Lorentzkorrespondenz,
- Mikrokausalität beziehungsweise äquivalente Signalisierungsgrenze.

Schließung: ein kontrollierter Grenzsatz liefert die klassische
Lichtkegelstruktur.

## F8 - Einstein- und Quantenfeldgrenzfall

Vorgesehene Dateien:

- `QCE_EinsteinLimit.lean`
- `QCE_QuantumFieldLimit.lean`

Schließung:

- bekannte niederenergetische Observablen werden reproduziert,
- die Zielgleichungen werden nicht als Annahmen versteckt,
- Korrekturterme und Geltungsbereich sind explizit.

## F9 - Schwarzes Loch, Page-Kurve und Rückgewinnung

Vorgesehene Datei: `QCE_BlackHoleInformation.lean`

- semiklassischer Außenbereich,
- Horizont- und Kernabbildung,
- globale reine Entwicklung oder wohldefinierte Dilatation,
- Strahlungsentropie,
- Page-Zeit und qualitative Page-Kurve,
- keine Verletzung der deklarierten Kausal- und Energiebedingungen.

## F10 - unterscheidende Vorhersage

Vorgesehene Datei: `QCE_PredictionContract.lean`

- beobachtbare Größe,
- Parameterbereich,
- Null- und Alternativmodelle,
- Messabbildung,
- Unsicherheitsbudget,
- vor Datenzugriff eingefrorenes Falsifikationskriterium.

## F11 - Korrespondenz und unabhängige Reproduktion

Vorgesehene Dateien:

- `QCE_EmpiricalCorrespondence.lean`
- `QCE_IndependentReproduction.lean`

Lean kann hier die Struktur des Korrespondenzvertrags prüfen. Die
Messwerte, Kalibrationen und unabhängige Ausführung müssen als externe,
digestgebundene Evidenz eingebracht werden.

## Abschlussregel

`QCE_PHYSICAL_CLOSURE` ist erst zulässig, wenn F1 bis F11 mit ausgeführten
Kernel-Receipts, Quellenbindungen und empirischen Belegen geschlossen sind.
F0 allein bleibt `FORMAL_MODEL_CHECKED`.
