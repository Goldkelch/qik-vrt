<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Kerninvariante: TRANSPORT_ACK ≠ EFFECT_ACK

Publication ID: `qikvrt-core-invariant-transport-effect-20260919-v1`
Publication Index State: `repository_candidate_exact_upload_authorization_pending`

Primärfassung: [KERNINVARIANTE_DE.md](KERNINVARIANTE_DE.md).

Dieses additive Publikationspaket hält die bestehende Invariante mit acht quellengebundenen bzw. ausdrücklich methodischen Aussagen fest. Es ändert weder den Referenzkern noch die Zustände, Berechtigungen oder Freigabebedingungen.

`CLAIM_MATRIX.json` und `MACHINE_PROOF_BUNDLE.json` verwenden den bestehenden v2-Publikationsvertrag. `SOURCE_BINDINGS.json` bindet unveränderte Quellenbytes und das untersuchte HEAD/TREE. `BOUNDARY_TEST_REPORT.json` bezeichnet ausschließlich den darin dokumentierten lokalen Prüflauf. Es ist kein Gesamt-Repository-PASS und kein Nachweis eines Zenodo-Effekts.

Die schemafeste Angabe `zenodo_upload_authorized=true` im maschinellen Proof-Bundle bezeichnet ausschließlich das erfüllte Maschinenprüf-Gate. Sie ersetzt nicht die getrennte, nach Rücklieferung erforderliche menschliche Exact-Upload-Erklärung. Deren Entwurf steht in `AUTHORIZE_EXACT_UPLOAD.txt`; `PUBLICATION_CONTROL_PENDING.json` hält sie ausdrücklich als ausstehend fest.

Prüfung mit vorhandenen Repository-Werkzeugen:

```sh
python3 -B -m unittest -v tests.test_effect_ack_conformance
python3 -B tools/qikvrt_zenodo_machine_proof.py --proof-bundle docs/publications/2026-09-19-core-invariant-transport-effect/MACHINE_PROOF_BUNDLE.json
python3 -B tools/qikvrt_integrity.py verify
```

Das vollständige Upload-Set steht in `PUBLICATION_CONTROL_PENDING.json`. Repository-seitige Autorisierungsdaten werden nicht hochgeladen. Vor einem Zenodo-Effekt sind das exakte Ausführungssubjekt, alle vorgeschriebenen Gates, die kanonische Owner-Erklärung und ihr einmaliger Git-Lock zu prüfen. Danach sind öffentliche Byte-Readbacks und getrennte Repository-Belege erforderlich.

Für diese eigenständige technische Notiz wird kein bestehender Zenodo-Datensatz geändert. Eine neue Hinterlegung darf erst nach der gebundenen Freigabe erfolgen. Der bestehende EFFECT_ACK-Arbeitspapier-Datensatz wird in den vorgesehenen Metadaten als verwandte Quelle referenziert; er ist keine Publikationsbestätigung dieses Pakets.

Beitragsherkunft: Ingolf Lohmann — Konzept, methodische Formulierung und Persistenzauftrag; OpenAI ChatGPT / Codex — Textausarbeitung, Quellenprüfung, Claim-Disposition und technische Paketierung. Native Review, Main-Promotion und Produkt-DONE werden nicht behauptet.
