<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

*QIK‑VRT / EFFECT_ACK – formaler Release-Status*

*Dokumentstatus:* `FORMAL_RELEASE_CANDIDATE`

Dies bleibt ein transparenter Release‑Kandidat, bis sowohl die nachgelagerte
Datei `LEAN_CI_EVIDENCE.json` den finalen Quellenstand mit einem erfolgreichen
Lauf bindet als auch `ZENODO_PUBLICATION_EVIDENCE.json` den Zenodo‑Record
anonym öffentlich geprüft hat – keine vorweggenommene
Publikationsbehauptung.

Ich lege mit diesem additiven Release die formale Rekonstruktion des
abstrakten Entscheidungs‑ und Freigabekerns von
`draft-lohmann-qikvrt-effect-ack-01` vor.

*Gebundener Nachweis*

• Version: `2.0.0-alpha.2`

• Commit‑, Tree‑ und CI‑Bindung: nachgelagerte `LEAN_CI_EVIDENCE.json`

• Öffentliche Zenodo‑Bindung: nachgelagerte
`ZENODO_PUBLICATION_EVIDENCE.json`

• Zenodo‑Konzept: `10.5281/zenodo.21488115`

• Versions‑DOI und Record: ausschließlich gemäß öffentlichen
Zenodo‑Metadaten

• IETF‑Quelle:
https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/01/

*Was formalisiert ist*

Der Lean‑Kern bildet fünf Zustände, fünf Verbindungsentscheidungen, die
siebzehn `CoreDone`‑Bedingungen, die Prioritätsordnung und die getrennte
Verbraucherprüfung ab.

Damit wird präzise unterschieden:

`Nachricht empfangen` ≠ `Wirkung autorisiert`

Eine gewöhnliche Freigabe verlangt im Modell einen aufgezeichneten
DONE‑Zustand, einen aus dem bereitgestellten Snapshot neu berechneten
DONE‑Zustand sowie sämtliche ausgewiesenen Verbraucherprüfungen. Ein konkretes
Gegenbeispiel zeigt: Eine reine Transportbestätigung genügt nicht.

*Was daran weiterführt*

Unter der ausdrücklich genannten Annahme vollständiger Mediation folgt für
den geschützten Softwarebereich: Eine ausgeführte gewöhnliche Wirkung muss
über den autorisierten DONE‑Pfad gegangen sein.

Für eine physikalische Wirkung gilt die Übertragung nur zusätzlich unter einer
treuen kausalen Brücke zwischen Softwareausführung und physischem Geschehen.
Das ist ein konditionaler Satz – kein Ersatz für Hardwareprüfung, Kalibrierung,
Fehlermodell und Experiment.

*Die Rekonstruktionsgrenze*

Eine Zielbedeutung lässt sich für tatsächlich erreichbare Beobachtungen – also
auf dem Beobachtungsbild – genau dann rekonstruieren, wenn sie auf allen durch
die Beobachtung ununterscheidbar gewordenen Ursprüngen gleich ist.

Exakte historische Rückgewinnung verlangt eine injektive Beobachtung.
Kollabieren zwei verschiedene Ursprünge auf dieselbe Beobachtung, besitzt
diese Abbildung keinen exakten historischen Linksinversen‑Decoder.

*Was ich deshalb ausdrücklich nicht behaupte*

Dieser Stand beweist weder die vollständige Wire‑Konformität einer
Implementierung noch IETF‑Konsens, RFC‑Status, Peer Review oder
voraussetzungslose physische Sicherheit.

Er beweist auch nicht, dass sämtliche Informatik, Mathematik, Physik,
Metaphysik, Spiritualität oder das Universum vollständig reverse engineered
seien. Er macht stattdessen einen klar abgegrenzten Kern, seine Bedingungen
und seine Grenzen maschinell überprüfbar.

*Wissenschaftlicher Status*

Der Internet‑Draft bleibt ein aktives individuelles Arbeitsdokument. Die
Lean‑Formalisierung ist eine formale Erweiterung des abstrakten Modells. Die
cyberphysische Geltung bleibt konditional, und empirische Aussagen benötigen
empirische Evidenz.

Auch das 62‑seitige Gesamtmanuskript ist damit nicht vollständig formalisiert.
Alpha 2 erweitert den ausdrücklich partiellen Stand um den abgegrenzten
EFFECT_ACK‑Kern.

Das Entscheidende ist nicht eine Totalitätsbehauptung, sondern die prüfbare
Trennung zwischen Empfang, Beleg, Verantwortung und autorisierter Wirkung.

— Ingolf Lohmann

23. Juli 2026

Copyright 2026 Ingolf Lohmann. Dokumentationsinhalt: CC BY‑NC‑ND 4.0, soweit
nicht anders gekennzeichnet.
