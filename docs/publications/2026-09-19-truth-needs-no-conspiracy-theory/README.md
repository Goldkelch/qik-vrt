# Reproduzierbarer Publikationskandidat PR #1128

Originalessay unverändert; Begleitdateien von ChatGPT erstellt. Der Geltungsbereich ist Quellenbindung und vollständige maschinenlesbare Disposition, nicht der Beweis sämtlicher natürlicher Aussagen.

Aus dem Repository-Root ausführen:

```sh
python3 -B docs/publications/2026-09-19-truth-needs-no-conspiracy-theory/verify_publication_scope.py
python3 -B tools/qikvrt_zenodo_machine_proof.py --proof-bundle docs/publications/2026-09-19-truth-needs-no-conspiracy-theory/MACHINE_PROOF_BUNDLE.json
python3 -B tools/qikvrt_integrity.py verify
```

Der erste Befehl verifiziert Byte- und Zeilenvollständigkeit und die negativen Grenzfälle. Der zweite prüft das unveränderte aktive v2-Proof-Gate. Dessen schemafestes `zenodo_upload_authorized` ist allein die Freigabe dieses Teil-Gates: `tools/qikvrt_zenodo_publish.py` verlangt zusätzlich die separate repositorygebundene Owner-Autorisierung. Diese ist hier ausdrücklich NICHT materialisiert. Kein Zenodo-POST und keine Freigabe-/Verbrauchsref wurden erzeugt.

`PUBLICATION_CONTROL_PENDING.json`, `AUTHORIZE_EXACT_UPLOAD.txt` und spätere Validator-Receipts sind Kontrollmaterial, nicht Bestandteil des beabsichtigten Upload-Dateisatzes. Die Exact-HEAD/TREE-Ausführungsbelege liegen außerhalb des Prüfbündels, damit keine Selbstreferenz entsteht. Frühere Workflow-, Review- oder Readback-Ergebnisse werden nicht auf einen neuen Commit übertragen.
