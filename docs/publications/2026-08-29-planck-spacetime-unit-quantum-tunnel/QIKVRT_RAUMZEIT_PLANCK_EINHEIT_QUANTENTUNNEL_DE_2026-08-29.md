# Der Zollstock, die Uhr und der mögliche Tunnel

## Ingolf Lohmanns Vorschlag einer eigenen Raumzeit-Einheit – zwischen Planck-Normalform, gravitativer Dualität und prüfbarer neuer Physik

Autor und Product Owner: Ingolf Lohmann  
Technische Ausarbeitung und kritische Evidenzprüfung: OpenAI Codex  
Stand: 29. August 2026  
Status: repository-gebundener Veröffentlichungskandidat 0.2 – keine Zenodo- oder Fachpublikation, nicht peer-reviewed

---

## Kurzfassung

Wir vermessen die Welt mit zwei sehr verschiedenen Werkzeugen. Für den Raum nehmen wir einen Zollstock. Für die Zeit eine Uhr. Ein Gegenstand liegt drei Meter entfernt; ein Vorgang dauert drei Sekunden. Diese Trennung ist so vertraut, dass sie wie eine unverrückbare Eigenschaft der Natur erscheint.

Doch schon ein Lichtstrahl verbindet beide Maßstäbe. Die Lichtgeschwindigkeit im Vakuum ist im Internationalen Einheitensystem exakt auf 299.792.458 Meter pro Sekunde festgelegt. Damit lässt sich eine Zeitspanne als Lichtweg und eine Strecke als Lichtlaufzeit ausdrücken. In der Relativitätstheorie werden Raum und Zeit nicht mehr als zwei getrennte Bühnen behandelt, sondern als Komponenten einer gemeinsamen Raumzeit.

Ingolf Lohmann setzt genau an dieser Nahtstelle an. Sein Vorschlag lautet, die Raumzeit nicht weiter nur mit zwei getrennten Einheiten – Meter und Sekunde – zu beschreiben, sondern ihr einen gemeinsamen, an der Planckskala kalibrierten Maßrahmen zu geben. Er spricht dabei von drei Vektoren der Planckskala und vermutet, dass eine solche Darstellung physikalische Abkürzungen sichtbar machen könnte, die in der herkömmlichen Buchführung verborgen bleiben. Für einen solchen Übergang schlägt er den anschaulichen Namen *Quantentunnel* vor.

Der Vorschlag berührt mehrere reale und tiefe Strukturen der Physik:

- Die Wahl der SI-Basiseinheiten ist historisch gewachsen und nicht mathematisch einzigartig.
- Meter und Sekunde sind schon heute durch die exakt festgelegte Lichtgeschwindigkeit verbunden.
- Aus Lichtgeschwindigkeit `c`, reduziertem Planckschen Wirkungsquantum `ħ` und Gravitationskonstante `G` entstehen natürliche Planckskalen für Länge, Zeit und Masse.
- Die quellenfreien Maxwell-Gleichungen besitzen eine elektrische-magnetische Dualität.
- Eine entsprechende Dualitätsstruktur existiert auch für linearisierte Gravitation und in besonderen Sektoren, aber nicht als allgemeine Symmetrie der vollständigen nichtlinearen Einsteinschen Gravitation.
- QIK-VRT enthält bereits maschinengeprüfte symbolische Planck-Identitäten und ein Lean-Modell, das physikalische Dimensionen aus Kalibrierungswirkungen ableitet.

Der entscheidende Befund lautet jedoch ebenso klar:

*Eine neue Einheit kann Formeln verkürzen, Darstellungen vereinheitlichen und Berechnungen vereinfachen. Sie erzeugt allein noch keinen neuen Weg durch die Natur.*

Eine physische Abkürzung oder ein echter Quantentunnel benötigt zusätzliche Dynamik: einen Zustandsraum, eine Wirkung oder einen Hamiltonoperator, eine Barriere beziehungsweise vorher ausgeschlossene Verbindung, eine Übergangsamplitude und eine messbare Vorhersage. Dieser Schritt ist in der neuen Audioskizze noch nicht definiert.

Die Idee ist deshalb weder als Unsinn abzutun noch bereits als neue Naturtheorie auszugeben. Ihre stärkste wissenschaftliche Fassung ist ein konkretes Forschungsprogramm: eine kanonische Planck-Raumzeit-Kalibrierung formal definieren, den verlustfreien Rückweg zu SI beweisen, bekannte Physik rekonstruieren und anschließend genau die dimensionslose Beobachtungsgröße benennen, bei der die neue Struktur von der alten Beschreibung abweicht.

---

## 1. Für Kinder und alle anderen: Warum haben wir eine Uhr und einen Zollstock?

Stell dir vor, du möchtest einem Freund sagen, wo und wann ein Zug ankommt.

Du brauchst zwei Angaben:

- Der Zug hält 300 Meter von dir entfernt.
- Er kommt in 60 Sekunden an.

Die Meter beantworten die Frage *wo?* Die Sekunden beantworten die Frage *wann?*

Jetzt stell dir einen Lichtblitz vor. Licht legt in jeder Sekunde im Vakuum exakt 299.792.458 Meter zurück. Mit diesem festen Verhältnis kannst du die Zeitangabe in eine Wegangabe übersetzen:

```text
eine Sekunde Lichtlaufzeit
= 299.792.458 Meter Lichtweg
```

Umgekehrt kannst du eine Strecke als die Zeit angeben, die Licht dafür benötigt. Astronomen machen das ständig. Ein Lichtjahr ist keine Zeit, sondern die Strecke, die Licht in einem Jahr zurücklegt.

Damit entsteht eine überraschende Möglichkeit: Man kann für Raum und Zeit denselben Maßstab benutzen. Man könnte zum Beispiel die Zeitkoordinate nicht als `t`, sondern als `ct` schreiben. Dann haben `ct`, `x`, `y` und `z` alle die Einheit einer Länge.

Aber Vorsicht: Eine neue Beschriftung baut noch keinen Tunnel.

Wenn du auf einer Landkarte alle Kilometer in Lichtsekunden umrechnest, wird die Straße dadurch weder kürzer noch schneller. Die neue Karte kann Zusammenhänge klarer zeigen. Ein neuer Weg entsteht erst, wenn die Geometrie oder die Dynamik selbst etwas erlaubt, was vorher nicht erlaubt war.

Genau zwischen diesen beiden Möglichkeiten liegt die Frage dieses Artikels:

*Ist Lohmanns Raumzeit-Einheit eine besonders klare Karte – oder enthält sie den Ansatz zu einem neuen Weg?*

---

## 2. Der Auftrag aus der Audioaufnahme

Die am 29. August 2026 lokal verarbeitete Audioaufnahme hat eine Dauer von rund 142,87 Sekunden und den SHA-256-Digest:

`2c9512a1ce79c9ea75f669b4e68e748076dcabfad8164d639a424578786b61dd`

Zwei lokale Erkennungspässe ergeben denselben konservativen semantischen Kern:

- Die getrennte Verwendung von Meter und Sekunde soll erneut grundlegend geprüft werden.
- Gravitation soll im Zusammenhang mit einer Dualität betrachtet werden, die der elektromagnetischen Dualität ähnelt.
- Raumzeit soll eine eigene Einheit erhalten, nicht lediglich zwei getrennte Einheiten für Raum und Zeit.
- Diese Einheit soll durch „drei Vektoren der Planckskala“ beschrieben werden.
- Dadurch könnten physikalische Abkürzungen sichtbar werden, die in der bisherigen Darstellung fehlen.
- Der Begriff „Quantentunnel“ wird als möglicher Name für diese Abkürzung angeboten.
- Der Zusammenhang soll in einem ausführlichen Artikel für Fachwelt und Allgemeinheit erklärt werden.

Die automatische Transkription ist kein menschlich verifiziertes Wortlautprotokoll. Besonders die grammatische Zuordnung des Dualitätssatzes und die genaue Bedeutung der „drei Vektoren“ bleiben aus dem Audio allein unterbestimmt. Der Artikel gibt deshalb keine fehlende Definition als bereits gesprochen aus. Er entwickelt stattdessen die mathematisch stärkste faire Lesart und kennzeichnet jede zusätzliche Präzisierung als Rekonstruktion.

---

## 3. Vier Ebenen, die nicht verwechselt werden dürfen

Damit eine kühne Idee weder kleingeredet noch vorschnell zur Entdeckung erklärt wird, trennt dieser Artikel vier Ebenen.

### Ebene A – etablierte Physik

Hierzu gehören beispielsweise:

- die SI-Definitionen von Meter und Sekunde,
- die spezielle und allgemeine Relativitätstheorie in ihrem geprüften Bereich,
- die Planckgrößen als dimensionsrichtige Naturgrößen,
- elektromagnetische Dualität in ihrem definierten Gültigkeitsbereich,
- beobachtete Gravitationswellen,
- gewöhnliches quantenmechanisches Tunneln.

### Ebene B – mathematische Neudarstellung

Hier wird dieselbe Physik durch andere Einheiten, Koordinaten oder normalisierte Variablen beschrieben. Eine bijektive Umrechnung kann Formeln radikal verkürzen. Solange alle dimensionslosen Beobachtungsgrößen gleich bleiben, ist das noch keine neue Naturwirkung.

### Ebene C – Lohmanns Hypothese

Die Hypothese beginnt dort, wo die Planckskalierung nicht nur als bequemes Einheitensystem verstanden wird, sondern als Hinweis auf eine fundamentalere relationale Struktur, die neue Übergänge sichtbar oder möglich machen könnte.

### Ebene D – empirisch bestätigte neue Physik

Diese Ebene ist erst erreicht, wenn die Hypothese:

- vollständig definiert ist,
- bekannte Grenzfälle reproduziert,
- mindestens eine unterscheidende dimensionslose Vorhersage liefert,
- vorab ein Widerlegungskriterium benennt,
- experimentell gemessen und unabhängig reproduziert wird.

Diese Trennung ist keine Höflichkeitsformel. Sie ist selbst eine Anwendung des QIK-VRT-Prinzips:

```text
FORMALISIERT
!= PHYSISCH REALISIERT
!= EMPIRISCH BESTÄTIGT
```

---

## 4. Meter und Sekunde sind schon heute enger verbunden, als sie aussehen

Das moderne SI wird durch sieben festgelegte Natur- und Referenzkonstanten definiert. Dazu gehören die Cäsium-Hyperfeinstrukturfrequenz, die Lichtgeschwindigkeit und die Planck-Konstante. Das Internationale Büro für Maß und Gewicht weist ausdrücklich darauf hin, dass die historische Wahl der Basiseinheiten nicht einzigartig ist.

Die Sekunde wird über eine festgelegte Frequenz des Cäsium-133-Atoms realisiert. Die Lichtgeschwindigkeit besitzt im SI den exakten Zahlenwert:

```text
c = 299.792.458 m/s
```

Der Meter ist dadurch bereits an die Sekunde und an `c` gebunden. Die BIPM-Broschüre formuliert den historischen Weg besonders anschaulich: Ein Meter entspricht der Strecke, die Licht im Vakuum in `1/299.792.458` Sekunde zurücklegt.

Ingolf Lohmanns Ausgangsintuition trifft deshalb eine echte metrologische Entwicklung: Die moderne Physik hat Zollstock und Uhr längst über Konstanten der Natur miteinander verschaltet.

Aber daraus folgen zwei verschiedene Aussagen:

1. *Metrologisch:* Meter und Sekunde können über `c` ineinander umgerechnet werden.
2. *Physikalisch-geometrisch:* Raum und Zeit sind Komponenten einer Raumzeit mit einer nicht-euklidischen Signatur und einer kausalen Lichtkegelstruktur.

Die erste Aussage erlaubt einen gemeinsamen Maßstab. Die zweite verhindert, dass Raum und Zeit einfach wie vier gewöhnliche räumliche Achsen behandelt werden.

Für eine Ereignisdifferenz in flacher Raumzeit kann man bei einer verbreiteten Vorzeichenkonvention schreiben:

```text
Δs² = c²Δt² − Δx² − Δy² − Δz²
```

Durch `cΔt` besitzen alle vier Terme dieselbe Längeneinheit. Dennoch bleiben vier Komponenten und die Lorentz-Metrik erforderlich. Ein einzelner Zahlenwert `Δs²` enthält nicht die gesamte Richtungsinformation des Vierervektors. Verschiedene lichtartige Verschiebungen besitzen beispielsweise alle `Δs² = 0`.

*Eine gemeinsame Raumzeit-Einheit ist also möglich. Eine Reduktion der gesamten Raumzeit auf eine einzige skalare Zahl ist damit nicht erreicht.*

---

## 5. Die drei Planckskalen

Aus drei Konstanten lassen sich drei natürliche mechanische Skalen bilden:

```text
Plancklänge:  ℓ_P = √(ħG/c³)
Planckzeit:   t_P = √(ħG/c⁵) = ℓ_P/c
Planckmasse:  m_P = √(ħc/G)
```

Aktuelle CODATA-Werte lauten ungefähr:

```text
ℓ_P = 1,616255 × 10⁻³⁵ m
t_P = 5,391247 × 10⁻⁴⁴ s
m_P = 2,176434 × 10⁻⁸ kg
```

Daraus folgt anschaulich:

```text
1 Meter   ≈ 6,18714 × 10³⁴ Plancklängen
1 Sekunde ≈ 1,85486 × 10⁴³ Planckzeiten
1 Kilogramm ≈ 4,59467 × 10⁷ Planckmassen
```

Diese Zahlen sind keine drei nachgewiesenen Atome der Wirklichkeit. Insbesondere ist die Plancklänge nicht experimentell als kleinste mögliche Länge bestätigt und die Planckzeit nicht als Taktfrequenz des Universums beobachtet. Die Größen entstehen zunächst durch dimensionsrichtige Kombinationen von `ħ`, `G` und `c`. Weil `G` gemessen werden muss, tragen die abgeleiteten Planckwerte außerdem eine Messunsicherheit.

Ihre besondere Bedeutung liegt darin, dass sie Quantenwirkung, Relativität und Gravitation in einer gemeinsamen Normalform zusammenführen. Das macht sie zu natürlichen Kandidaten für die Suche nach Quantengravitation. Es beweist noch nicht, dass neue Physik exakt an dieser Skala einsetzt.

---

## 6. Was könnten „drei Vektoren der Planckskala“ präzise bedeuten?

Einheit, Skala und Vektor sind verschiedene mathematische Kategorien:

- Eine *Einheit* ist eine Referenz für eine physikalische Größe.
- Eine *Skala* bezeichnet eine charakteristische Größenordnung.
- Ein *Vektor* lebt in einem definierten Raum, besitzt Komponenten und eine Transformationsregel.

Die Audioaufnahme benennt die drei Vektoren, definiert aber ihren Vektorraum und ihre Transformation nicht. Es wäre daher falsch, eine einzige Lesart als bereits ausgesprochene Theorie auszugeben.

Es gibt jedoch eine besonders starke und anschlussfähige Rekonstruktion.

### Die Planckbasis im Dimensionsraum

Jede rein mechanische physikalische Größe besitzt einen Dimensionsvektor:

```text
[q] = Mᵃ Lᵇ Tʳ
d(q) = (a, b, r)
```

Die Konstanten `c`, `ħ` und `G` besitzen in der Reihenfolge Masse, Länge, Zeit die Dimensionsvektoren:

```text
d(c) = ( 0, 1, −1)
d(ħ) = ( 1, 2, −1)
d(G) = (−1, 3, −2)
```

Diese drei Vektoren sind linear unabhängig. Die Determinante ihrer Dimensionsmatrix beträgt `−2` und ist damit ungleich null. Sie bilden also tatsächlich eine Basis des dreidimensionalen mechanischen Dimensionsraums `M, L, T`.

Aus derselben Basis entstehen Planckmasse, Plancklänge und Planckzeit. Deshalb lässt sich die geordnete Struktur

```text
B_P = (m_P, ℓ_P, t_P)
```

als *Planck-Kalibrierbasis* bezeichnen.

Das ist eine mathematisch präzise Bedeutung von „drei Vektoren der Planckskala“: nicht drei Pfeile im gewöhnlichen Raum, sondern drei unabhängige Richtungen im Dimensions- und Kalibrierungsraum.

### Was diese Lesart nicht bedeutet

Sie bedeutet nicht, dass drei Vektoren die physische vierdimensionale Raumzeit vollständig aufspannen. Für lokale `3+1`-Raumzeit benötigt man vier Komponenten beziehungsweise ein Vierbein. In einer gekrümmten Raumzeit gibt es im Allgemeinen keine ausgezeichnete globale Basis; lokale Basen müssen sich unter Koordinatenwechseln und lokalen Lorentztransformationen korrekt verhalten.

Die Planck-Kalibrierbasis und eine Raumzeitbasis erfüllen also verschiedene Aufgaben:

- `B_P` ordnet physikalische Dimensionen und Skalen.
- `X^μ` beschreibt ein Ereignis oder eine Ereignisdifferenz in der Raumzeit.

Beides kann miteinander verbunden werden, darf aber nicht still gleichgesetzt werden.

---

## 7. Eine konkrete gemeinsame Raumzeit-Einheit

Die stärkste konservative Definition einer Planck-Raumzeit-Einheit lautet:

```text
1 σ_P := ℓ_P := c · t_P
```

Eine Ereignisdifferenz erhält dann dimensionslose Planck-Komponenten:

```text
X⁰ = cΔt/ℓ_P = Δt/t_P
X¹ = Δx/ℓ_P
X² = Δy/ℓ_P
X³ = Δz/ℓ_P
```

Das normierte Intervall ist:

```text
Δs²/ℓ_P² = (Δt/t_P)²
            − (Δx/ℓ_P)²
            − (Δy/ℓ_P)²
            − (Δz/ℓ_P)²
```

Hier werden Meter und Sekunden tatsächlich in einem gemeinsamen Raumzeitmaß dargestellt. Die Lichtgeschwindigkeit verschwindet aus der sichtbaren Formel, weil sie bereits in der Wahl der Einheit steckt.

Genau das ist die erste reale „Abkürzung“: eine *algebraische Abkürzung*. Ein Konversionsfaktor muss nicht in jeder Zeile erneut mitgeführt werden.

Doch die Formel beschreibt weiterhin dieselbe Lorentzgeometrie. Der Lichtkegel wird nicht geöffnet, keine Weltlinie verkürzt und keine Nachricht überlichtschnell.

---

## 8. Der verlustfreie Rückweg zu SI

Ein wissenschaftlich und informatisch brauchbares Einheitensystem benötigt beide Richtungen:

```text
SI → Planckdarstellung → SI
```

Für eine SI-Größe

```text
q = n_SI · kgᵃ mᵇ sʳ
```

sei der Dimensionsvektor `d = (a,b,r)`. Dann lautet der Planck-Zahlenwert:

```text
n_P = n_SI /
      ((m_P/kg)ᵃ · (ℓ_P/m)ᵇ · (t_P/s)ʳ)
```

Der Rückweg ist:

```text
n_SI = n_P ·
       ((m_P/kg)ᵃ · (ℓ_P/m)ᵇ · (t_P/s)ʳ)
```

Diese Abbildung ist bijektiv, solange:

- der Dimensionsvektor erhalten bleibt,
- der physikalische Typ erhalten bleibt,
- dieselbe Konstanten- und Kalibrierungsversion verwendet wird,
- Offset-Einheiten vorher in absolute Einheiten überführt werden,
- numerische Genauigkeit und Messunsicherheit nicht abgeschnitten werden.

Würde man die Dimensionsinformation wegwerfen, verlöre man Bedeutung: Planckmasse, Plancklänge und Planckzeit hätten dann alle nur noch den nackten Zahlenwert `1`. Eine Zahl ohne Typ ist keine vollständige physikalische Größe.

Die Dreierbasis deckt außerdem nur den mechanischen Dimensionsraum `M, L, T` ab. Temperatur, elektrische Stromstärke, Stoffmenge und Lichtstärke benötigen zusätzliche Skalen oder ausdrücklich dokumentierte Ableitungsregeln.

Damit erscheint der „Rückweg“, der in früheren QIK-VRT-Arbeiten immer wieder gefordert wurde, hier in besonders klarer Form:

```text
DARSTELLUNGSABKÜRZUNG
+ TYPERHALT
+ DIMENSIONSERHALT
+ KALIBRIERUNGSBINDUNG
+ UNSICHERHEITSERHALT
= VERLUSTFREIER EINHEITEN-ROUNDTRIP
```

---

## 9. Was QIK-VRT dazu bereits formal enthält

Der neue Vorschlag trifft im Repository nicht auf ein leeres Blatt.

### Die H5-Planck-Brücke

Das Bündel `VRTCore SMG H5` enthält einen mit Lean 4.19.0 geprüften endlichen Modellkern. Darin werden die Exponenten von `ħ`, `G` und `c` als exakte ganzzahlige Halbexponenten dargestellt. Sechs symbolische Planck-Identitäten wurden kernelakzeptiert:

```text
ħ/(m_P c) = ℓ_P
G m_P/c² = ℓ_P
ℓ_P p_P = ħ
t_P E_P = ħ
ℓ_P/t_P = c
E_P/p_P = c
```

Dabei bezeichnet `Gm/c²` den Gravitationsradius. Der Schwarzschild-Radius enthält den zusätzlichen Faktor zwei; das Modell blockiert eine stille Verwechslung.

Diese sechs Identitäten sind exakt im symbolischen Dimensionsmodell. Sie zeigen, dass Quantenwirkung, Gravitation, Masse, Energie, Impuls, Länge und Zeit am Planck-Normalpunkt ineinandergreifen.

Sie beweisen nicht:

- eine neue Raumzeitdynamik,
- einen Gravitonnachweis,
- eine kleinste Länge,
- eine physische Tunnelverbindung,
- eine vereinheitlichte Theorie der Natur.

Das H5-Bündel selbst hält die physikalische Vereinheitlichung deshalb korrekt auf `OPEN_CANDIDATE`.

### Messungsabgeleitete Dimensionen

Ein weiteres Lean-Modul modelliert Dimensionen nicht als frei wählbare ontische Etiketten, sondern als aus Kalibrierungsaktionen abgeleitete Signaturen. Elf benannte Sätze zeigen im definierten Modell unter anderem:

- Eine deklarierte Kalibrierungsaktion bestimmt genau eine Dimensionssignatur.
- Eine abweichende Signatur kann nicht mit allen Basisreaktionen übereinstimmen.
- Eine Änderung der Messkalibrierung überschreibt nicht die prämetrische Ontologie.
- Länge und Zeit erscheinen als abgeleitete Messdarstellungen.

Das ist eine starke formale Anschlussstelle für Lohmanns Idee. Es erlaubt, eine neue Raumzeit-Einheit als explizite Kalibrierungsabbildung zu behandeln, statt sie sprachlich mit der Natur selbst gleichzusetzen.

Aber auch dieses Modell sagt ausdrücklich: Es beweist nicht, dass die Natur genau diese Kalibrierungsaktion verwendet.

### Der neue Ringschluss

Zusammen ergeben beide Bestände bereits eine klare Forschungsarchitektur:

```text
prämetrische Relation
→ deklarierte Kalibrierungswirkung
→ abgeleitete Dimension
→ Planck-Normalform
→ kanonische Raumzeitdarstellung
→ inverse Rekonstruktion
→ empirischer Vergleich
```

Der nun fehlende Satz ist nicht noch eine Identität derselben Art. Es fehlt eine zusätzliche Dynamik, die aus dieser Darstellung eine unterscheidende physikalische Vorhersage ableitet.

---

## 10. Gravitation und Elektromagnetismus: Welche Dualität ist gemeint?

Das Wort *Dualität* kann hier mindestens zwei verschiedene physikalische Gedanken bezeichnen.

### Möglichkeit A – Welle und Quant

Elektromagnetische Strahlung besitzt eine klassische Feldbeschreibung und eine Quantenbeschreibung mit Photonen. Gravitative Strahlung wurde als klassische Raumzeitwelle direkt beobachtet. Eine Quantisierung schwacher Gravitationsstörungen führt theoretisch zum Begriff des Gravitons.

Die Analogie lautet dann:

```text
elektromagnetische Welle ↔ Photon
gravitative Welle       ↔ hypothetisches Graviton
```

Der linke gravitative Teil – Gravitationswellen – ist empirisch beobachtet. Ein einzelnes Graviton beziehungsweise eine eindeutig quantisierte Gravitation ist nicht entsprechend direkt beobachtet. Die Analogie darf deshalb nicht als abgeschlossener empirischer Gleichstand ausgegeben werden.

### Möglichkeit B – elektrische und magnetische Feldanteile

In der quellenfreien Maxwell-Theorie können elektrisches und magnetisches Feld durch eine kontinuierliche Dualitätsrotation ineinander gemischt werden. In Formensprache rotiert der Feldstärketensor `F` in seine Hodge-Duale `*F`.

Auch die Raumzeitkrümmung kann relativ zu einem Beobachter in elektrische und magnetische Teile des Weyl-Tensors zerlegt werden. In der linearisierten Gravitation lässt sich eine echte, verdrehte elektrische-magnetische Dualitätsstruktur formulieren.

Das ist eine tiefe mathematische Verwandtschaft. Sie besitzt jedoch eine harte Grenze: Die vollständige nichtlineare Einsteinsche Gravitation hat im Allgemeinen nicht dieselbe globale `U(1)`-Dualität wie die quellenfreie Maxwell-Theorie. Neuere Analysen zeigen, dass die gravitative Dualität durch die nichtlinearen Wechselwirkungen gebrochen wird, auch wenn sie in linearisierter Theorie und besonderen Lösungssektoren erhalten bleibt.

Die wissenschaftlich belastbare Formulierung lautet deshalb:

*Gravitation und Elektromagnetismus besitzen in genau benannten Grenz- und Darstellungsbereichen strukturell verwandte Dualitäten. Daraus folgt keine vollständige Identität beider Wechselwirkungen.*

Diese begrenzte, aber reale Verwandtschaft reicht aus, um Lohmanns Frage wissenschaftlich interessant zu machen. Sie reicht nicht aus, um den fehlenden Dynamiksatz zu überspringen.

---

## 11. Vier Arten von Abkürzung

Der Begriff *Abkürzung* muss präzisiert werden. Er kann vier sehr verschiedene Dinge meinen.

### 1. Notationelle Abkürzung

Durch `c = ħ = G = 1` verschwinden Konstanten aus vielen Formeln. Aus

```text
E² = p²c² + m²c⁴
```

wird in passenden Planckvariablen:

```text
ε² = π² + μ²
```

Das ist kürzer und kann Strukturen sichtbar machen.

### 2. Rechnerische Abkürzung

Eine kanonische Normalform kann Konvertierungen, Einheitenfehler und wiederholte symbolische Arbeit vermeiden. Für Software, formale Beweise und Hardware-Festkommadarstellungen kann das einen realen technischen Vorteil erzeugen.

### 3. Dynamische Abkürzung

Ein System erhält durch ein neues Gesetz einen Übergang, der in der bisherigen Dynamik nicht existierte. Dafür braucht man eine neue Wirkung, einen Hamiltonoperator, Kopplungsterm oder Übergangsregel.

### 4. Kausale oder geometrische Abkürzung

Zwei Ereignisse werden durch eine neue Geometrie oder Kausalstruktur anders verbunden. Dafür wären beispielsweise eine veränderte Metrik, ein topologischer Kanal oder eine nichtlokale Dynamik nötig. Ein Einheitenwechsel genügt nicht.

Die Planck-Raumzeit-Einheit liefert nach dem heutigen Stand sicher die erste und möglicherweise die zweite Art. Die dritte und vierte Art sind Lohmanns offene Hypothese.

---

## 12. Warum der Name „Quantentunnel“ reizvoll ist

Beim gewöhnlichen quantenmechanischen Tunneln besitzt ein Zustand eine von null verschiedene Wahrscheinlichkeit, eine klassisch verbotene Potentialbarriere zu durchdringen.

In der WKB-Näherung lautet eine typische Transmissionswahrscheinlichkeit:

```text
T ≈ exp(
     −2 ∫[x₁,x₂]
        √(2m(V(x)−E))/ħ · dx
    )
```

Setzt man

```text
X = x/ℓ_P
μ = m/m_P
v = V/E_P
ε = E/E_P
```

so wird daraus:

```text
T ≈ exp(
     −2 ∫[X₁,X₂]
        √(2μ(v(X)−ε)) · dX
    )
```

Die Naturkonstanten sind aus der sichtbaren Formel verschwunden. Die Tunnelwahrscheinlichkeit ist jedoch dieselbe. Die Planckdarstellung hat die Gleichung normalisiert, nicht den physikalischen Vorgang verändert.

Der Begriff „Quantentunnel“ passt deshalb auf drei verschiedenen Stufen unterschiedlich gut.

### Stufe Q0 – Planck-Brücke

```text
SI ↔ Planckdarstellung
```

Das ist ein reversibler Basiswechsel. „Tunnel“ ist eine Metapher; „Quanten-“ verweist nur auf `ħ` in der Kalibrierung.

### Stufe Q1 – informatischer Tunnel

Eine kanonische QIK-VRT-Kodierung könnte komplexe Einheiten- und Provenienzpfade durch eine kompakte, typisierte Normalform ersetzen und anschließend verlustfrei zurückkehren. Das wäre eine reale rechnerische Abkürzung, aber noch keine neue Quantenwirkung.

### Stufe Q2 – physischer Quantentunnel

Eine neue Theorie müsste zwei physische Zustände, eine klassisch ausgeschlossene Region, eine Wirkung oder einen Hamiltonoperator, Randbedingungen und eine nichtverschwindende Übergangsamplitude definieren. Erst dann wäre „Quantentunnel“ ein physikalischer Fachbegriff des neuen Modells.

Auch ein echter Quantentunnel ist nicht automatisch eine steuerbare überlichtschnelle Verbindung. Eine relativistische Analyse mit der Dirac-Gleichung zeigt, dass Teilchen und Information beim Tunneln innerhalb des zukünftigen Lichtkegels bleiben. Ein Wurmloch wiederum wäre eine geometrische Verbindung und ist nicht synonym mit Quantentunneln.

Der Name ist also als Arbeitstitel stark, wenn die Stufe mitgesagt wird:

```text
QIK-VRT PLANCK-BRÜCKE = DEFINIERTES FORSCHUNGSMOTIV
PHYSISCHER QUANTENTUNNEL = NOCH OFFENE DYNAMIK
```

---

## 13. Wann aus der neuen Darstellung neue Physik wird

Eine reine Einheitenabbildung `Φ` verändert keine Physik, wenn jede Gleichung nur umgeschrieben wird:

```text
E_P = Φ ∘ E_SI ∘ Φ⁻¹
```

Alle dimensionslosen Observablen bleiben dann identisch. Genau sie sind der entscheidende Prüfstein.

Die relativistische Dispersionsrelation wird beispielsweise lediglich von

```text
E² = p²c² + m²c⁴
```

zu

```text
ε² = π² + μ²
```

Das ist eine elegante Normalform, aber keine neue Vorhersage.

Eine illustrative – nicht vom Product Owner behauptete – Erweiterung könnte dagegen lauten:

```text
ε² = π² + μ² + ηπ³
```

mit einer dimensionslosen Konstanten `η`. So ein Zusatz wäre nur dann neue Physik, wenn er nicht durch eine invertierbare Variablenumdefinition verschwindet, eine konsistente Symmetrie und Dynamik besitzt und eine messbare Abweichung erzeugt.

Die fünf entscheidenden Fragen lauten:

1. Welche neue dimensionslose Wahrscheinlichkeit, Phase oder Verhältnisgröße wird vorhergesagt?
2. Bleibt die Abweichung nach der Rückumrechnung zu SI erhalten?
3. Folgt sie aus einer expliziten Dynamik und nicht nur aus der Beschriftung?
4. Geht das Modell bei niedriger Energie beziehungsweise großer Skala kontrolliert in etablierte Physik über?
5. Welches Messergebnis würde die Hypothese widerlegen?

Erst wenn diese Fragen beantwortet sind, kann aus der mathematischen Abkürzung eine physikalische Abkürzung werden.

---

## 14. Eine repository-native QIK-VRT-Darstellung

Die Idee lässt sich bereits heute informatisch geschlossen spezifizieren, ohne physikalische Bestätigung vorzutäuschen.

Ein kanonischer Messdatensatz könnte mindestens enthalten:

```text
schema
quantity_kind
dimension_vector
si_value
si_unit
planck_value
planck_basis_version
constants_version
coordinate_frame
metric_signature
uncertainty
calibration_reference
source
observation_time
previous_record_hash
record_hash
physical_correspondence_status
```

Die Serialisierung muss folgende Invarianten erfüllen:

```text
decode_SI(encode_Planck(q)) = q

dimension_before = dimension_after
quantity_kind_before = quantity_kind_after
uncertainty_not_reduced_without_measurement
calibration_version_bound = true
```

Dabei bedeutet „gleich“ nicht zwangsläufig bitgleiche Gleitkommazahlen. Für eine genaue Spezifikation sind entweder exakte rationale beziehungsweise algebraische Repräsentationen oder ausdrücklich begrenzte Rundungsintervalle nötig.

QIK-VRT kann an dieser Stelle eine besondere Stärke ausspielen: Nicht nur der Zahlenwert, sondern auch Typ, Dimension, Kalibrierung, Unsicherheit, Bezugssystem und Herkunft werden an dieselben kanonischen Bytes gebunden. Dadurch lässt sich unterscheiden:

```text
GLEICHE ZAHL
!= GLEICHE PHYSIKALISCHE GRÖSSE

GLEICHE EINHEITENUMRECHNUNG
!= NEUE NATURWIRKUNG
```

Das wäre ein echter informatischer Beitrag zur Physik: eine maschinenprüfbare Grenze zwischen Darstellung, formaler Folgerung und empirischer Korrespondenz.

---

## 15. Warum das auch für Rechenmaschinen interessant ist

Natürliche Einheiten und dimensionslose Normalformen können Software und Hardware vereinfachen:

- weniger wiederholte Konversionsfaktoren,
- einheitliche Typregeln,
- früh erkennbare Dimensionsfehler,
- kompakte Exponentenvektoren,
- reproduzierbare kanonische Serialisierung,
- gemeinsame Testvektoren für Python, C, Lean und VHDL,
- mögliche Festkomma- oder Logarithmusdarstellungen über viele Größenordnungen.

Der mechanische Dimensionsvektor `(a,b,r)` besteht nur aus kleinen ganzen Zahlen. Die Exponenten von `ħ`, `G` und `c` können durch verdoppelte Ganzzahlen dargestellt werden, sodass auch Halbpotenzen exakt bleiben. Genau dieses Prinzip verwendet die vorhandene H5-Planck-Brücke.

Das ist hardwarefreundlich: Addieren und Subtrahieren von Exponenten ist wesentlich kleiner als eine allgemeine symbolische Algebra. Aber die Zahlenwerte physikalischer Größen über mehr als siebzig Größenordnungen, Unsicherheitsintervalle, Bezugssysteme und nichtmechanische SI-Dimensionen bleiben reale technische Aufgaben.

Ein Performancevorteil darf daher erst behauptet werden, wenn dieselbe vollständige Operation verglichen wird:

- SI-Eingang lesen,
- Typ und Dimension prüfen,
- Planck-Normalform bilden,
- Invarianten prüfen,
- Receipt erzeugen,
- zurückserialisieren,
- dieselbe numerische Fehlergrenze einhalten.

Ein kurzer Exponentenkern pro Takt ist nicht dasselbe wie ein vollständiger physikalischer Datensatz pro Takt.

---

## 16. Das formale Fertigstellungsprogramm

Aus dem heutigen Bestand ergibt sich ein klarer nächster Arbeitsplan.

### Schritt 1 – Begriffe einfrieren

`Planck-Raumzeit-Einheit`, `Planck-Kalibrierbasis`, `Raumzeitvektor` und `Quantentunnel` erhalten getrennte Definitionen.

### Schritt 2 – Dimensionsbasis beweisen

Die lineare Unabhängigkeit der Dimensionsvektoren von `c`, `ħ` und `G` sowie die eindeutige Abbildung jeder mechanischen Dimension werden in Lean formalisiert.

### Schritt 3 – Raumzeitabbildung definieren

`X^μ = (ct/ℓ_P, x/ℓ_P, y/ℓ_P, z/ℓ_P)` wird samt Lorentz-Metrik, Vorzeichenkonvention und inverser Abbildung spezifiziert.

### Schritt 4 – Typisierten Roundtrip beweisen

Für alle unterstützten Größen muss gelten:

```text
SI → PLANCK → SI = IDENTITÄT
```

unter expliziten Präzisions- und Kalibrierungsbedingungen.

### Schritt 5 – Bekannte Grenzfälle sichern

Spezielle Relativität, klassische Mechanik, Maxwell-Theorie und die bereits vorhandenen Planck-Identitäten dürfen durch die neue Darstellung nicht verändert werden.

### Schritt 6 – Dualitätsscope festlegen

Es wird eindeutig benannt, ob Welle/Quant, Maxwell-Dualität, Weyl-E/B-Zerlegung, linearisierte gravitative Dualität oder eine neue Dualität gemeint ist.

### Schritt 7 – Dynamik ergänzen

Für einen physischen Tunnel werden Zustandsraum, Wirkung oder Hamiltonoperator, Randbedingungen und Übergangsamplitude benötigt.

### Schritt 8 – neue Vorhersage einfrieren

Mindestens eine dimensionslose Abweichung mit erwarteter Größenordnung wird vor Einsicht in die Testdaten festgelegt.

### Schritt 9 – Experiment und Negativkontrollen

Das Experiment muss Standardtheorie, reine Einheitenumrechnung, numerische Artefakte und die neue Dynamik voneinander unterscheiden.

### Schritt 10 – unabhängige Replikation

Andere Gruppen erhalten Definition, Code, Rohdaten, Kalibrierung und Falsifikationskriterium. Erst unabhängige Übereinstimmung schließt den empirischen Rückweg.

---

## 17. Ein mögliches empirisches Prüfprogramm

Welche Experimente sinnvoll sind, hängt von der noch fehlenden Dynamik ab. Vor deren Definition existiert kein spezifischer Messwert, den man redlich als Bestätigung ausgeben könnte.

Mögliche Testklassen wären:

- *Bevorzugte Richtung:* Falls drei physische Vektoren eine reale Triade bilden, könnten richtungs- oder tageszeitabhängige Effekte entstehen. Dann müsste lokale Lorentzinvarianz extrem genau geprüft werden.
- *Veränderte Dispersion:* Ein Planck-unterdrückter Zusatz könnte Laufzeiten oder Energie-Impuls-Beziehungen beeinflussen.
- *Veränderte Tunnelrate:* Eine neue Dynamik könnte eine Abweichung von der Schrödinger-, Dirac- oder Feldtheorie vorhersagen.
- *Gravitationswellen:* Eine veränderte gravitative Dualität könnte Polarisation, Ausbreitung oder Kopplung modifizieren.
- *Atominterferometrie:* Eine neue Phase könnte in hochpräzisen Interferenzexperimenten gesucht werden.
- *Reine Darstellungsbaseline:* Die Planckkodierung muss zunächst exakt dieselben Resultate wie die SI-Rechnung liefern. Das ist die notwendige Nullhypothese.

Für jede Testklasse braucht man:

- Zielgröße,
- Einheit und dimensionslose Normalform,
- erwartete Effektgröße,
- Instrument und Kalibrierung,
- Fehlerbudget,
- Blind- oder Negativkontrolle,
- vorab festgelegte Ausschlussgrenze,
- unabhängige Wiederholung.

Ohne diese Angaben lautet der ehrliche Status:

```text
PHYSICALLY_CONNECTABLE = true
NEW_PHYSICAL_PREDICTION = NOT_YET_DEFINED
EMPIRICAL_CONFIRMATION = false
```

---

## 18. Was daran staunenswert ist – ohne das Staunen zu missbrauchen

Das Staunenswerte liegt zunächst in einer nüchternen Tatsache: Die scheinbar alltäglichen Einheiten Meter, Sekunde und Kilogramm lassen sich durch wenige Naturkonstanten in eine geschlossene algebraische Beziehung bringen.

Am Planckpunkt gelten unter den Standarddefinitionen gleichzeitig:

```text
Quantenlänge = Gravitationsradius
Länge × Impuls = Wirkung
Zeit × Energie = Wirkung
Länge / Zeit = Lichtgeschwindigkeit
Energie / Impuls = Lichtgeschwindigkeit
```

Das ist kein mystischer Zusatz. Es folgt aus den Definitionen. Und gerade deshalb ist es faszinierend: Drei große Säulen der Physik – Quantenwirkung, Relativität und Gravitation – treffen sich in derselben Dimensionsnormalform.

Man darf darin philosophische oder spirituelle Bedeutung sehen. Man darf es als Hinweis auf Einheit, Relation oder eine tiefere Ordnung der Natur lesen. Solche Deutungen können für Menschen wichtig sein und neue Fragen anregen.

Wissenschaftlich entscheidend bleibt jedoch die Trennung:

- Die Schönheit einer Identität ist kein Messwert.
- Eine spirituelle Deutung ist keine Übergangsamplitude.
- Eine mathematische Möglichkeit ist keine beobachtete Wirkung.
- Eine ungewöhnliche Frage ist noch keine bestätigte Entdeckung.

Umgekehrt gilt ebenso:

- Eine noch offene Hypothese ist nicht automatisch wertlos.
- Eine bekannte Gleichung kann in einer neuen Systemarchitektur produktiv neu verbunden werden.
- Eine formale Normalform kann technische und wissenschaftliche Fehler sichtbar machen.
- Eine präzise negative Grenze ist Erkenntnis und kein Scheitern.

Der Respekt vor einer großen Idee zeigt sich nicht darin, sie vorschnell wahr zu nennen. Er zeigt sich darin, ihr die stärkste Form zu geben, in der die Natur selbst antworten kann.

---

## 19. Das Urteil

Ingolf Lohmanns Vorschlag besitzt einen realen, mathematisch anschlussfähigen Kern:

- Raum und Zeit können über `c` in einem gemeinsamen Maßrahmen dargestellt werden.
- `c`, `ħ` und `G` bilden eine Basis des mechanischen Dimensionsraums.
- Plancklänge, Planckzeit und Planckmasse liefern eine natürliche Kalibrierbasis.
- Eine typisierte SI-Planck-Abbildung besitzt einen verlustfreien Rückweg.
- QIK-VRT enthält bereits maschinengeprüfte Bausteine dieser Normalform.
- Gravitation und Elektromagnetismus besitzen begrenzte, aber echte Dualitätsanalogien.

Der Vorschlag besitzt zugleich eine klar benennbare offene Stelle:

*Die neue Einheit und die drei Planckrichtungen definieren noch keine neue Dynamik.*

Deshalb ist heute bewiesen beziehungsweise ausführbar:

- die symbolische Planck-Normalform im deklarierten Lean-Modell,
- die dimensionsrichtige gemeinsame Raumzeitdarstellung,
- der algebraisch bijektive Einheiten-Roundtrip unter seinen Voraussetzungen,
- die Möglichkeit einer kanonischen QIK-VRT-Implementierung.

Heute nicht bewiesen ist:

- dass die Planckskala aus Raumzeitatomen besteht,
- dass drei physische Vektoren die vierdimensionale Raumzeit ersetzen,
- dass eine neue kausale Abkürzung existiert,
- dass Lohmanns „Quantentunnel“ bereits eine physische Übergangsamplitude besitzt,
- dass Gravitation und Elektromagnetismus vollständig dieselbe Dualität haben,
- dass Natur oder Hardware einen solchen Tunnel bereits ausgeführt haben.

Die wissenschaftlich stärkste Schlussform lautet daher:

*Vielleicht liegt die erste Abkürzung tatsächlich in der Darstellung: Meter, Sekunde und Kilogramm werden durch eine Planck-Kalibrierbasis in eine gemeinsame, maschinenprüfbare Normalform überführt. Ob daraus eine zweite, physische Abkürzung folgt, entscheidet nicht die Benennung, sondern die noch zu formulierende Dynamik und ihr Experiment.*

Der erste Tunnel, den die Idee erfolgreich durchquert, führt vom getrennten Maßstab zur kanonischen Relation. Der nächste muss von der Relation zur unterscheidenden Vorhersage führen. Erst danach darf die Natur entscheiden, ob aus dem möglichen Tunnel ein wirklicher geworden ist.

---

## Quellen und repository-interne Anschlussstellen

### Metrologie und Planckwerte

- BIPM, *The International System of Units (SI), 9th edition, version 4.01*: https://www.bipm.org/documents/20126/41483022/SI-Brochure-9-EN.pdf
- BIPM, *SI defining constants*: https://www.bipm.org/en/measurement-units/si-defining-constants
- NIST/CODATA, Planck length: https://physics.nist.gov/cgi-bin/cuu/Value?plkl
- NIST/CODATA, Planck time: https://physics.nist.gov/cgi-bin/cuu/Value?plkt
- NIST/CODATA, Planck mass: https://physics.nist.gov/cgi-bin/cuu/Value?plkm

### Dualität und Gravitation

- Bunster, Henneaux, Hörtner, *Gravitational Electric-Magnetic Duality, Gauge Invariance and Twisted Self-Duality*: https://arxiv.org/abs/1207.1840
- Monteiro, *No U(1) electric-magnetic duality in Einstein gravity*: https://arxiv.org/abs/2312.02351
- LIGO/Virgo, *Observation of Gravitational Waves from a Binary Black Hole Merger*: https://doi.org/10.1103/PhysRevLett.116.061102

### Quantentunneln und Kausalität

- Gavassino und Disconzi, *Subluminality of relativistic quantum tunneling*: https://doi.org/10.1103/PhysRevA.107.032209

### QIK-VRT-Artefakte

- `docs/publications/2026-08-02-vrtcore-smg-h5/VRTCore_SMG_PlanckBridge.lean`
- `docs/publications/2026-08-02-vrtcore-smg-h5/VRTCore_SMG_AxiomAudit.lean`
- `docs/publications/2026-08-02-vrtcore-smg-h5/CLAIM_MATRIX.json`
- `docs/publications/2026-08-07-measurement-derived-dimensions/MeasurementDerivedDimensions.lean`
- `docs/publications/2026-08-07-measurement-derived-dimensions/MeasurementDerivedDimensionsAxiomAudit.lean`

---

## Veröffentlichungs- und Wirkungsgrenze

Dieser Text ist ein repository-gebundener Veröffentlichungskandidat. Er ist keine Zenodo- oder Fachpublikation, nicht peer-reviewed und nicht als Patentanspruch geprüft. Die mathematische Präzisierung kann zusätzliche technische Offenlegung enthalten und muss deshalb vor jeder weitergehenden Veröffentlichung in ein Offenlegungsregister und eine Patentprüfung einbezogen werden.

```text
ARTICLE_PUBLISHED = false
PEER_REVIEWED = false
NEW_PHYSICS_ESTABLISHED = false
QUANTUM_TUNNEL_OBSERVED = false
HARDWARE_PROTOTYPE_OBSERVED = false
PATENTABILITY_ESTABLISHED = false
PASS = false
FINAL_PASS = false
GENERAL_EFFECT_ACK_DONE = false
```
