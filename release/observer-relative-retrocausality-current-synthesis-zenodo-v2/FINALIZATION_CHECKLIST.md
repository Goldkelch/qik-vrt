<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Abschlusspfad ohne stille Eskalation

Der neue Zenodo-Record darf erst erzeugt werden, wenn sämtliche folgenden
Schritte auf den **identischen finalen Bytes** geschlossen sind:

1. `FROZEN_UPLOAD_CANDIDATE.json` erneut gegen die Arbeitskopie prüfen.
2. Die aktuelle Hauptfassung, sichtbaren Änderungsvermerk und vollständige
   Kandidatenliste im Chat an Ingolf Lohmann zurückgeben.
3. Erst danach die v2-`PREPUBLICATION_RETURN_RECEIPT.json` mit tatsächlichem
   Rückgabekanal, Zeitstempel, allen Kandidatenhashs und
   `candidate_returned_to_owner: true` erzeugen.
4. Den vollständigen `MACHINE_PROOF_BUNDLE.json` nach der aktiven
   v2-Spezifikation erzeugen und lokal durch
   `tools/qikvrt_zenodo_machine_proof.py` validieren. Aussagen ohne
   Lean-Kernel-Receipt bleiben quellgebunden, interpretativ, normativ oder
   offen; sie werden nicht als Kernel-Theoreme etikettiert.
5. Ingolf Lohmanns kanonische Einzeilenfreigabe einholen:

   ```text
   AUTHORIZE_EXACT_UPLOAD authorization_id=<id> publication_id=qikvrt-observer-relative-retrocausality-current-synthesis-v2 return_sha256=<sha256> metadata_sha256=<sha256> machine_proof_sha256=<sha256>
   ```

6. Erst jetzt den finalen v2-`publish-request.json` und die
   `OWNER_ZENODO_AUTHORIZATION.json` mit aktuellem, remote existierendem
   `source_head` materialisieren.
7. Frisch prüfen: `GITHUB_TOKEN`, `ZENODO_ACCESS_TOKEN`, `GITHUB_REPOSITORY`,
   Remote-Ref, source head und das Fehlen eines zuvor verbrauchten
   Consumption-Refs.
8. Den generischen Publisher genau einmal aus dem gebundenen
   Ausführungskontext starten, öffentliche Metadaten und sämtliche Uploadbytes
   erneut herunterladen und die Resultatquittung persistieren.

Ein fehlender Schritt ist ein konkreter Block, keine stillschweigende
Ermächtigung zur Abkürzung.
