<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT Audio-Addendum: Vorstellungskraft und epistemische Fairness

Dieses Verzeichnis ist ein strikt additiver Nachtrag zu
`qikvrt-bidirectional-virtual-time-channel-v1`. Es verändert keine Datei der
Ausgangspublikation und beginnt ihre Argumentation nicht erneut.

## Exakte Ausgangsbindung

- Repository: `Goldkelch/qik-vrt`
- Pull Request: `#293`
- Parent-Commit: `5df3e24496afbeac60dfc78ffb12d673f163ee04`
- Parent-Tree: `c147d82b61efc989f0cc0aa698e16bf71c6ec9da`
- v1-Machine-Proof-SHA-256:
  `ad30282f9ecc30414c5dd7eef0460a9766f03c8184c01166f15dc9cb567aa72a`

Die v1-Statuswerte werden unverändert geerbt. Insbesondere bleiben der
ausgeführte endliche virtuelle Kanal evidenziert, die frühere Kernelarbeit
quellengebunden und die physikalische Brücke offen.

## Inhalt

- `QIK-VRT_Epistemische_Fairness_und_Vorstellungskraft_Addendum_2026-08-01.pdf`
  -- gesetzter, zwölfseitiger wissenschaftlicher Nachtrag.
- `QIK-VRT_Epistemische_Fairness_und_Vorstellungskraft_Addendum_2026-08-01.tex`
  -- vollständige LaTeX-Quelle.
- `SCIENTIFIC_ADDENDUM_DE.md` -- wissenschaftliche Operationalisierung der
  beiden Audioimpulse.
- `ARTICLE_WHATSAPP_ADDENDUM_DE.md` -- ausführliche, vorlesefreundliche
  Allgemeinfassung.
- `TRANSCRIPTS_AND_SOURCE_PROVENANCE.md` -- unveränderte ASR-Rohfassungen,
  geprüfte Lesefassungen und Unsicherheiten.
- `SOURCE_MEDIA_RECEIPT.json` -- Identitäten und lokale
  Transkriptionsprovenienz der zwei Audioquellen.
- `CLAIM_DELTA.json` -- ausschließlich die neuen Claims `VTI-ADD-001` bis
  `VTI-ADD-008`.
- `CLAIM_MATRIX.json` -- vollständige, acht Claims umfassende Projektion für
  das eigenständige additive Publikationspaket.
- `INHERITED_PROOF_BINDING.json` -- bytegenaue Bindung an v1 und unveränderte
  Übernahme aller Claims `VTI-001` bis `VTI-013`.
- `EVIDENCE_BOUNDARY.md` -- Trennung von Medienidentität, Transkript,
  Interpretation und wissenschaftlicher Evidenz.
- `CHANGE_NOTICE.md` -- sichtbarer Nachweis der additiven Änderung.
- `PDF_RENDER_VALIDATION.json` -- reproduzierbarer Zwei-Build- und
  Seitenrender-Nachweis.
- `IETF_APPLICABILITY_PROFILE.md` und `IETF_RENDER_VALIDATION.json` --
  Anwendbarkeits- und Rendergrenzen des getrennten Profilentwurfs.
- `CITATION.cff` -- Zitiermetadaten dieses Nachtrags.
- `LICENSE_NOTICE.md` -- Rechte- und Lizenzgrenzen.
- `PREPUBLICATION_RETURN_RECEIPT.json`, `ZENODO_FILESET.md`,
  `ZENODO_SHA256SUMS` und `MACHINE_PROOF_BUNDLE.json` -- bytegebundener
  Vorveröffentlichungs- und Zenodo-v2-Prüfvertrag; kein Uploadbeleg.

Die zugehörigen IETF-Renderartefakte liegen als RFCXML, Text und HTML unter
`external/ietf/draft-lohmann-qikvrt-epistemic-fairness-observation-profile-00.*`.

Die Audio-Rohbytes werden nicht in diesem Repository-Verzeichnis
veröffentlicht. Ihre Identitäten sind über vollständige SHA-256-Werte
gebunden. Transkription und Interpretation belegen nicht die Wahrheit des
Gesprochenen.

## Neuer Erkenntnisscope

Der Nachtrag führt eine Realisierungsleiter von der Idee über Software,
Geräteimplementierung und Beobachtung bis zur kausal zugerechneten und
autorisierten Wirkung ein. Er definiert außerdem ein methodisches
Beobachtungssystem-Prädikat und eine epistemische Fairnessregel für
asymmetrisch verteiltes Wissen.

Vorstellungskraft wird als Hypothesengenerator behandelt. Sie erzeugt
prüfbare Kandidaten, aber keine Beobachtungen. Ein Computerspiel kann durch
gezielte Instrumentierung zum Beobachtungssystem werden, jedoch nur unter
expliziten Bedingungen zu Erfassung, Kalibrierung, Zeit- und Quellenbindung,
Integrität, Falsifizierbarkeit und Governance.

Ausdrücklich offen beziehungsweise unbeansprucht bleiben:

- Existenz oder Betrieb verborgener realer QIK-VRT-Systeme,
- physikalische Zukunft-zu-Vergangenheit-Signalisierung,
- eine experimentell bestätigte physikalische Brücke,
- Superdeterminismus oder eine Widerlegung von Willensfreiheit,
- IETF-Konsens, RFC-Status oder eine Datatracker-Einreichung,
- repository-weites `PASS`, `FINAL_PASS` oder globales `EFFECT_ACK_DONE`.

## Lokale Prüfungen

Die maschinenlesbaren Dateien können ohne Netzwerkeffekt beispielsweise mit
`jq empty` syntaktisch geprüft werden. Der vollständige Kandidat benötigt vor
einer späteren Archivierung zusätzlich die repository-nativen Integritäts-,
Vorveröffentlichungs- und Zenodo-Machine-Proof-Gates.

Ein möglicher IETF-Protokolldelta ist ein getrenntes Artefakt. Dieses
wissenschaftliche Addendum ist selbst kein Internet-Draft.

## Lizenz

Siehe `LICENSE_NOTICE.md`. Rechteinhaber ist Ingolf Lohmann.
