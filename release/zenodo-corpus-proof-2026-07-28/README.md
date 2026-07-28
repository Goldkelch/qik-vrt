<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Retrospektiver Zenodo-Korpusbeweis

Dieser Transaktionsbereich erfasst sämtliche über das verbundene Zenodo-Konto veröffentlichten und Ingolf Lohmann zuordenbaren Records.

## Ziel

Für jeden Record werden folgende Relationen maschinenlesbar gebunden:

```text
Record-ID
→ DOI / Concept-DOI
→ öffentliche Metadaten
→ vollständiger Dateisatz
→ öffentlicher Redownload
→ MD5 / SHA-256
→ Repository-Provenienz
→ vorhandene Claim-/Proof-/Evidence-Artefakte
→ tatsächlicher Coverage-Status
→ erforderlicher Korrektur- oder Review-Schritt
```

## Wahrheitsgrenze

Der Korpusbeweis darf die Existenz eines Artefakts, seine öffentlichen Bytes und vorhandene Repository-Nachweise beweisen. Er darf fehlende Claim-Analysen nicht in einen fiktiven mathematischen Beweis umdeuten. Solche Records erhalten einen expliziten Review- und gegebenenfalls Versionierungsauftrag.

## Geplante persistente Artefakte

- `ZENODO_CORPUS_INVENTORY.json`
- `ZENODO_CORPUS_PROOF_INDEX.json`
- `CORPUS_PROOF_REPORT_DE.md`
- `proof-envelopes/zenodo-<record-id>.json`
- `CORPUS_CLAIM_MATRIX.json`
- `MACHINE_PROOF_BUNDLE.json`
- `PREPUBLICATION_RETURN_RECEIPT.json`
- `publish-request.json`
- `zenodo-publication.json`

## Status

```text
AUTHENTICATED_CORPUS_INVENTORY = VERIFIED
PUBLIC_BYTE_REDOWNLOAD         = VERIFIED
PROOF_ENVELOPES                = MATERIALIZED
PREPUBLICATION_RETURN          = NOT_EXECUTED
ZENODO_PROOF_PUBLICATION       = NOT_EXECUTED
MIRROR_PERSISTENCE             = NOT_EXECUTED
FINAL_PAIR_EQUALITY            = NOT_EXECUTED
```

Kein `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` wird durch diese Ausgangsdatei behauptet.

## Wiederholungs-Inventur-Receipt v4

- observed_at: `2026-07-28T10:53:00Z`
- records: `11`
- public byte verifications: `11`
- existing machine claim dispositions: `1`
- content reviews still required: `10`
- historical minimum records present: `False`
- missing historical minimum record IDs: `[20712301, 21244412, 21245282, 21245951, 21247297, 21247388, 21252415, 21252649, 21266670, 21488116, 21498774, 21501365, 21518464]`
- Zenodo proof-corpus publication: `NOT_EXECUTED`
- Mirror synchronization: `NOT_EXECUTED`
- completion: `EFFECT_ACK_CONTINUE`
