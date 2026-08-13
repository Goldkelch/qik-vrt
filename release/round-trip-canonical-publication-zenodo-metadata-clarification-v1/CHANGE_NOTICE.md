<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Sichtbarer Änderungsvermerk: Zenodo-Metadaten des Round-Trip-Zwischenstands

## Gegenstand

Vorbereitet wird ausschließlich eine Metadatenkorrektur des veröffentlichten
Zenodo-Records `21888130` mit der DOI `10.5281/zenodo.21888130`.

Der Titel bleibt bytegenau:

> Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP

## Warum die Korrektur erforderlich ist

Die gegenwärtigen öffentlichen Metadaten tragen noch die Sprache des
Vorveröffentlichungs-Freezes. Insbesondere wirken die Marker
`ZENODO_EFFECT_NOT_EXECUTED` und `OWNER_SINGLE_USE_AUTHORIZATION_ABSENT` so,
als sei der Datensatz nicht veröffentlicht. Der Record ist jedoch
`published/public_verified`.

Zusätzlich fehlen Suchbegriffe für Themen, die im Proof-Corpus behandelt
werden: Retrokausalität, relationale Zeit, Eigenzeit,
Beobachterperspektive, verteilte Systeme, Informationsfluss,
Delayed Choice, Quantenradierer und die virtuelle Testapparatur.

## Exakte Wirkung des Kandidaten

- Der historische Dateisatz bleibt unverändert: 54 Dateien,
  66.147.275 Bytes.
- Der gebundene Aggregate-SHA-256 bleibt
  `8db8780bff6644b6b895afc6924393c977c14ef649449510d4d523ecd6993ce1`.
- Es wird keine Datei entfernt, ersetzt oder hinzugefügt.
- Es wird keine neue Zenodo-Version angelegt.
- Titel, Autor, Lizenz, Publikationsdatum und Versionsbezeichnung bleiben
  unverändert.
- Beschreibung, Stichworte und Notes werden berichtigt.

## Wissenschaftliche Grenze

Diese Metadatenkorrektur stuft keinen wissenschaftlichen Claim um. Sie macht
sichtbar, dass die herunterladbaren No-Effect-Marker einen historischen
Freeze-Zwischenstand beschreiben. Zugleich benennt sie die vom Autor
verwendete beobachterrelative Bedeutung von Retrokausalität als eigenes
Thema und trennt sie von einem frei steuerbaren globalen Rückwärtskanal.

Eine neue Schlussfolgerung gegenüber dem eingefrorenen Primärtext muss in
einer verknüpften neuen Zenodo-Version mit aktualisiertem Primärtext,
Claim-Matrix und Beweisbindung veröffentlicht werden. Sie darf nicht durch
eine reine Metadatenänderung in den alten Dateisatz hineingedeutet werden.

## Maschinengebundene Korrekturgründe

- `META-REMOTE-STATE-001`: The public metadata still describes a no-effect freeze although the exact record is published and publicly verified.
- `META-HISTORICAL-MARKERS-001`: The embedded prepublication markers need an explicit historical-snapshot qualifier without altering the frozen files.
- `META-KEYWORDS-001`: The German and English search terms required to find the treated time, observer, distributed-system and experiment topics are absent.

## Ausführungsstatus

`PREPARED_NOT_AUTHORIZED`

Es ist noch kein Zenodo-Effekt ausgeführt worden. Die frühere
Einzelautorisierung ist verbraucht und gilt nicht für diese Korrektur.
