<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

*QIK‑VRT / EFFECT_ACK – Release 2.0.0-alpha.2 veröffentlicht*

Der formal geprüfte Alpha‑2‑Stand ist veröffentlicht:

https://doi.org/10.5281/zenodo.21518464

*Was jetzt zweifelsfrei vorliegt*

• Ein reproduzierbares Software‑Release mit 19 öffentlich abrufbaren Dateien.

• Das Release‑Archiv
`QIKVRT_Formalization_v2.0-alpha.2.zip` mit SHA‑256
`3ce079746f55545a5b5f89f736338882727f911ed1d67db5f2b5688c0e27910c`.

• Ein erfolgreicher, an Commit und Tree gebundener Repository‑Prüflauf.

• Eine unabhängige anonyme Zenodo‑Prüfung von Metadaten, DOI, Versionslinie,
Dateimenge, Größen, MD5 und SHA‑256 sämtlicher 19 Dateien.

• Der öffentliche Record `21518464`, Version `2.0.0-alpha.2`, im Konzept
`10.5281/zenodo.21488115`.

*Was maschinell geprüft ist*

Der Lean‑Kern formalisiert den abgegrenzten Entscheidungs‑ und
Freigabemechanismus von `EFFECT_ACK`: fünf Zustände, fünf
Verbindungsentscheidungen, siebzehn `CoreDone`‑Bedingungen,
Prioritätsordnung und getrennte Verbraucherprüfung.

Die zentrale Trennung lautet:

`Nachricht empfangen` ≠ `Wirkung autorisiert`

Eine gewöhnliche Wirkung ist im Modell nur über den ausgewiesenen
DONE‑Pfad zulässig. Ein konkretes Gegenbeispiel zeigt, weshalb eine reine
Transportbestätigung dafür nicht genügt.

Zusätzlich sind präzise Rekonstruktionsgrenzen formalisiert: Exakte
historische Rückgewinnung verlangt eine injektive Beobachtung. Werden
verschiedene Ursprünge ununterscheidbar, existiert kein exakter historischer
Linksinversen‑Decoder.

*Was daraus nicht folgt*

Dieses Release beweist nicht die vollständige Formalisierung des
62‑seitigen Manuskripts. Es beweist ebenso wenig, dass sämtliche Mathematik,
Physik, Logik, Metaphysik, Spiritualität oder das Universum vollständig
reverse engineered seien.

Cyberphysische Aussagen bleiben an eine ausdrücklich benannte treue
kausale Brücke gebunden. Empirische Aussagen benötigen weiterhin Messung,
Kalibrierung, Fehlermodelle und reproduzierbare Experimente.

*Der nächste belastbare Schritt*

Das Gesamtmanuskript wird in kleine, typisierte Behauptungen zerlegt:
Definitionen, Voraussetzungen, Lemmata, Sätze, Gegenbeispiele,
Beweisverpflichtungen und empirische Hypothesen. Nur mathematisch
formulierbare Aussagen werden mechanisiert; physikalische Aussagen werden
mit ihren Mess‑ und Brückenannahmen getrennt ausgewiesen.

Das Ziel ist kein rhetorischer Totalitätsanspruch, sondern eine wachsende,
prüfbare Beweiskette mit klaren Grenzen.

— Ingolf Lohmann

23. Juli 2026

Copyright 2026 Ingolf Lohmann. Dokumentationsinhalt: CC BY‑NC‑ND 4.0,
soweit nicht anders gekennzeichnet.
