<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Abschlusspfad ohne stille Eskalation

Der neue Zenodo-Record darf erst erzeugt werden, wenn sämtliche folgenden
Schritte auf den **identischen finalen Bytes** geschlossen sind:

1. **Erledigt:** `FROZEN_UPLOAD_CANDIDATE.json` gegen die Arbeitskopie geprüft.
2. **Erledigt:** Hauptfassung, damaligen sichtbaren Änderungsvermerk und vollständige
   17-Datei-Kandidatenliste am `2026-08-13T19:49:33Z` in ChatGPT Work an
   Ingolf Lohmann zurückgegeben.
3. **Erledigt:** Den repositoryinternen
   `CHANGE_NOTICE.md` um exakte maschinengebundene Gründe für `ORRZ-001` bis
   `ORRZ-010` vervollständigen und diese exakten Notice-Bytes samt SHA-256 und
   Git-Blob-ID am `2026-08-13T20:13:42Z` erneut sichtbar an Ingolf Lohmann
   zurückgeben.
4. **Erledigt:** Die sieben exakten Vorgängerdateien aus Git-Commit
   `47510c8569f56ecf3d2e22fb5ed846fa32208b86` repositoryseitig materialisieren
   und die v2-`PREPUBLICATION_RETURN_RECEIPT.json` mit tatsächlichem neuen
   Rückgabekanal, Zeitstempel, Kandidatenhashs,
   `content_changed: true`, `candidate_returned_to_owner: true` und
   `visible_change_notice_returned: true` erzeugen.
5. **Erledigt:** Den vollständigen `MACHINE_PROOF_BUNDLE.json` samt
   `BOUNDARY_TEST_REPORT.json` nach der aktiven
   v2-Spezifikation erzeugen und lokal durch
   `tools/qikvrt_zenodo_machine_proof.py` gegen exakt 21 Uploadpfade validieren.
   Aussagen ohne
   Lean-Kernel-Receipt bleiben quellgebunden, interpretativ, normativ oder
   offen; sie werden nicht als Kernel-Theoreme etikettiert.
6. Ingolf Lohmanns kanonische Einzeilenfreigabe einholen:

   ```text
   AUTHORIZE_EXACT_UPLOAD authorization_id=<id> publication_id=qikvrt-observer-relative-retrocausality-current-synthesis-v2 return_sha256=<sha256> metadata_sha256=<sha256> machine_proof_sha256=<sha256>
   ```

7. Erst jetzt den finalen v2-`publish-request.json` und die
   `OWNER_ZENODO_AUTHORIZATION.json` materialisieren. `source_head` ist dabei
   der commitierte, remote vorhandene Vorautorisierungs-Commit; der
   Ausführungs-Commit ist ein Nachfolger, der Manifest und Autorisierung trägt.
8. Frisch prüfen: `GITHUB_TOKEN`, `ZENODO_ACCESS_TOKEN`, `GITHUB_REPOSITORY`,
   Remote-Ref, source head und das Fehlen eines zuvor verbrauchten
   Consumption-Refs.
9. Den generischen Publisher genau einmal aus dem gebundenen
   Ausführungskontext starten, öffentliche Metadaten und sämtliche Uploadbytes
   erneut herunterladen und die Resultatquittung persistieren.

Ein fehlender Schritt ist ein konkreter Block, keine stillschweigende
Ermächtigung zur Abkürzung.
